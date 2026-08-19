from datetime import date
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    get_ingredient_by_id,
)
from app.crud.inventory import (
    consume_inventory_quantity,
    create_inventory_lot,
    increment_latest_inventory_lot,
    get_inventory_lot_by_id,
    soft_delete_inventory_lot,
    update_inventory_lot,
)
from app.database import get_db
from app.services.ingredient_form import (
    parse_optional_date,
    parse_required_date,
)
from app.utils.list_url import (
    build_list_redirect_url,
)
from app.utils.quantity import (
    is_valid_quantity_step,
)

from urllib.parse import urlencode


router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)


def build_new_inventory_lot_url(
    ingredient_id: int,
    keyword: str | None = None,
    category_filters: list[str] | None = None,
    sort: str = "category",
    out_of_stock_first: bool = False,
) -> str:
    """一覧条件を引き継いだ新規ロット登録URLを作る。"""
    query_params: list[tuple[str, str]] = []

    if keyword:
        query_params.append(
            ("keyword", keyword)
        )

    for category in category_filters or []:
        query_params.append(
            ("category_filters", category)
        )

    query_params.append(
        ("sort", sort)
    )

    if out_of_stock_first:
        query_params.append(
            ("out_of_stock_first", "true")
        )

    query_string = urlencode(
        query_params,
        doseq=True,
    )

    url = (
        f"/ingredients/{ingredient_id}"
        "/inventories/new"
    )

    if query_string:
        url = f"{url}?{query_string}"

    return url



def build_ingredient_edit_url(
    ingredient_id: int,
    lot_message: str | None = None,
    lot_error: str | None = None,
) -> str:
    """
    ロット編集結果を含む食材編集画面の
    URLを作成する。
    """
    query_params: dict[str, str] = {}

    if lot_message:
        query_params["lot_message"] = (
            lot_message
        )

    if lot_error:
        query_params["lot_error"] = lot_error

    url = (
        f"/ingredients/{ingredient_id}/edit"
    )

    if query_params:
        url = (
            f"{url}?"
            f"{urlencode(query_params)}"
        )

    return f"{url}#inventory-lots"



@router.post(
    "/ingredients/{ingredient_id}/increment"
)
def increment_inventory_quantity(
    ingredient_id: int,
    keyword: str | None = Form(None),
    category_filters: list[str] = Form(default=[]),
    sort: str = Form("category"),
    out_of_stock_first: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    最も新しく購入した在庫ありロットへ
    0.5追加する。
    """
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    redirect_url = build_list_redirect_url(
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    if ingredient is None:
        return RedirectResponse(
            url=redirect_url,
            status_code=303,
        )

    updated_inventory = (
        increment_latest_inventory_lot(
            db=db,
            ingredient_id=ingredient_id,
            amount=0.5,
        )
    )

    if updated_inventory is None:
        new_lot_url = build_new_inventory_lot_url(
            ingredient_id=ingredient_id,
            keyword=keyword,
            category_filters=category_filters,
            sort=sort,
            out_of_stock_first=(
                out_of_stock_first
            ),
        )

        return RedirectResponse(
            url=new_lot_url,
            status_code=303,
        )

    return RedirectResponse(
        url=redirect_url,
        status_code=303,
    )


@router.post(
    "/ingredients/{ingredient_id}/decrement"
)
def decrement_inventory_quantity(
    ingredient_id: int,
    keyword: str | None = Form(None),
    category_filters: list[str] = Form(
        default=[]
    ),
    sort: str = Form("category"),
    out_of_stock_first: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    期限が近い在庫ロットから
    在庫数量を0.5減らす。
    """
    consume_inventory_quantity(
        db=db,
        ingredient_id=ingredient_id,
        amount=0.5,
    )

    redirect_url = build_list_redirect_url(
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=303,
    )


def render_new_inventory_lot(
    request: Request,
    ingredient,
    form_data: dict,
    list_url: str,
    error_message: str | None = None,
    status_code: int = 200,
):
    """在庫ロット追加画面を表示する。"""
    return templates.TemplateResponse(
        request=request,
        name="inventory_lots/new.html",
        context={
            "ingredient": ingredient,
            "form_data": form_data,
            "list_url": list_url,
            "error_message": error_message,
        },
        status_code=status_code,
    )


@router.get(
    "/ingredients/{ingredient_id}/inventories/new"
)
def new_inventory_lot(
    request: Request,
    ingredient_id: int,
    keyword: str | None = Query(None),
    category_filters: list[str] = Query(
        default=[]
    ),
    sort: str = Query("category"),
    out_of_stock_first: bool = Query(False),
    db: Session = Depends(get_db),
):
    """在庫ロット追加画面を表示する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        raise HTTPException(
            status_code=404,
            detail="食材が見つかりません。",
        )

    list_url = build_list_redirect_url(
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    return render_new_inventory_lot(
        request=request,
        ingredient=ingredient,
        form_data={
            "quantity": 0.5,
            "purchase_date": (
                date.today().isoformat()
            ),
            "expiration_date": "",
            "keyword": keyword or "",
            "category_filters": category_filters,
            "sort": sort,
            "out_of_stock_first": (
                out_of_stock_first
            ),
        },
        list_url=list_url,
    )


@router.post(
    "/ingredients/{ingredient_id}/inventories"
)
def create_inventory_lot_route(
    request: Request,
    ingredient_id: int,
    quantity: float = Form(...),
    purchase_date: str = Form(...),
    expiration_date: str | None = Form(None),
    keyword: str | None = Form(None),
    category_filters: list[str] = Form(
        default=[]
    ),
    sort: str = Form("category"),
    out_of_stock_first: bool = Form(False),
    redirect_to_edit: bool = Form(False),
    db: Session = Depends(get_db),
):
    """新しい在庫ロットを登録する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        raise HTTPException(
            status_code=404,
            detail="食材が見つかりません。",
        )

    list_url = build_list_redirect_url(
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    form_data = {
        "quantity": quantity,
        "purchase_date": purchase_date,
        "expiration_date": (
            expiration_date or ""
        ),
        "keyword": keyword or "",
        "category_filters": category_filters,
        "sort": sort,
        "out_of_stock_first": (
            out_of_stock_first
        ),
    }

    if quantity <= 0:
        return render_new_inventory_lot(
            request=request,
            ingredient=ingredient,
            form_data=form_data,
            list_url=list_url,
            error_message=(
                "在庫数量は0より大きい値を"
                "入力してください。"
            ),
            status_code=400,
        )

    if not is_valid_quantity_step(quantity):
        return render_new_inventory_lot(
            request=request,
            ingredient=ingredient,
            form_data=form_data,
            list_url=list_url,
            error_message=(
                "在庫数量は0.5刻みで"
                "入力してください。"
            ),
            status_code=400,
        )

    (
        parsed_purchase_date,
        purchase_date_error,
    ) = parse_required_date(
        purchase_date,
        field_label="購入日",
    )

    if purchase_date_error:
        return render_new_inventory_lot(
            request=request,
            ingredient=ingredient,
            form_data=form_data,
            list_url=list_url,
            error_message=purchase_date_error,
            status_code=400,
        )

    (
        parsed_expiration_date,
        expiration_date_error,
    ) = parse_optional_date(
        expiration_date
    )

    if expiration_date_error:
        return render_new_inventory_lot(
            request=request,
            ingredient=ingredient,
            form_data=form_data,
            list_url=list_url,
            error_message=expiration_date_error,
            status_code=400,
        )

    assert parsed_purchase_date is not None

    create_inventory_lot(
        db=db,
        ingredient_id=ingredient.id,
        quantity=quantity,
        purchase_date=parsed_purchase_date,
        expiration_date=(
            parsed_expiration_date
        ),
    )

    if redirect_to_edit:
        return RedirectResponse(
            url=(
                f"/ingredients/{ingredient_id}"
                "/edit#inventory-lots"
            ),
            status_code=303,
        )

    separator = "&" if "?" in list_url else "?"

    redirect_url = (
        f"{list_url}{separator}"
        "inventory_message="
        "在庫を追加しました。"
        f"#ingredient-{ingredient.id}"
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=303,
    )


@router.post(
    "/inventories/{inventory_id}/edit"
)
def update_inventory_lot_route(
    inventory_id: int,
    quantity: float = Form(...),
    purchase_date: str = Form(...),
    expiration_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """在庫ロットを個別に更新する。"""
    inventory = get_inventory_lot_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    ingredient_id = inventory.ingredient_id

    if quantity < 0:
        return RedirectResponse(
            url=build_ingredient_edit_url(
                ingredient_id=ingredient_id,
                lot_error=(
                    "在庫数量は0以上で"
                    "入力してください。"
                ),
            ),
            status_code=303,
        )

    if not is_valid_quantity_step(quantity):
        return RedirectResponse(
            url=build_ingredient_edit_url(
                ingredient_id=ingredient_id,
                lot_error=(
                    "在庫数量は0.5刻みで"
                    "入力してください。"
                ),
            ),
            status_code=303,
        )

    (
        parsed_purchase_date,
        purchase_date_error,
    ) = parse_required_date(
        purchase_date,
        field_label="購入日",
    )

    if purchase_date_error:
        return RedirectResponse(
            url=build_ingredient_edit_url(
                ingredient_id=ingredient_id,
                lot_error=purchase_date_error,
            ),
            status_code=303,
        )

    assert parsed_purchase_date is not None

    (
        parsed_expiration_date,
        expiration_date_error,
    ) = parse_optional_date(
        expiration_date
    )

    if expiration_date_error:
        return RedirectResponse(
            url=build_ingredient_edit_url(
                ingredient_id=ingredient_id,
                lot_error=(
                    expiration_date_error
                ),
            ),
            status_code=303,
        )

    try:
        updated_inventory = (
            update_inventory_lot(
                db=db,
                inventory_id=inventory_id,
                quantity=quantity,
                purchase_date=(
                    parsed_purchase_date
                ),
                expiration_date=(
                    parsed_expiration_date
                ),
            )
        )

    except ValueError as error:
        db.rollback()

        return RedirectResponse(
            url=build_ingredient_edit_url(
                ingredient_id=ingredient_id,
                lot_error=str(error),
            ),
            status_code=303,
        )

    except Exception:
        db.rollback()

        return RedirectResponse(
            url=build_ingredient_edit_url(
                ingredient_id=ingredient_id,
                lot_error=(
                    "在庫ロットの更新に"
                    "失敗しました。"
                ),
            ),
            status_code=303,
        )

    if updated_inventory is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    return RedirectResponse(
        url=build_ingredient_edit_url(
            ingredient_id=ingredient_id,
            lot_message=(
                "在庫ロットを更新しました。"
            ),
        ),
        status_code=303,
    )

@router.post(
    "/inventories/{inventory_id}/delete"
)
def delete_inventory_lot_route(
    inventory_id: int,
    db: Session = Depends(get_db),
):
    inventory = get_inventory_lot_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="在庫ロットが見つかりません。",
        )

    ingredient_id = inventory.ingredient_id

    deleted_inventory = soft_delete_inventory_lot(
        db=db,
        inventory_id=inventory_id,
    )

    if deleted_inventory is None:
        raise HTTPException(
            status_code=404,
            detail="在庫ロットが見つかりません。",
        )

    return RedirectResponse(
        url=(
            f"/ingredients/{ingredient_id}/edit"
            "#inventory-lots"
        ),
        status_code=303,
    )


@router.get(
    "/inventories/{inventory_id}/delete",
    response_class=HTMLResponse,
)
def show_inventory_lot_delete_confirmation(
    request: Request,
    inventory_id: int,
    db: Session = Depends(get_db),
):
    inventory = get_inventory_lot_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="在庫ロットが見つかりません。",
        )

    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=inventory.ingredient_id,
    )

    if ingredient is None:
        raise HTTPException(
            status_code=404,
            detail="食材が見つかりません。",
        )

    return templates.TemplateResponse(
        request=request,
        name=(
            "ingredients/"
            "inventory_lot_delete.html"
        ),
        context={
            "ingredient": ingredient,
            "inventory": inventory,
        },
    )