from datetime import date, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.ingredient_options import (
    CATEGORY_OPTIONS,
    OTHER_OPTION,
    UNIT_OPTIONS,
)
from app.crud.ingredient import (
    create_ingredient,
    delete_ingredient,
    get_categories,
    get_filtered_ingredients,
    get_ingredient_by_id,
    get_ingredient_by_name,
    update_ingredient,
    update_ingredient_basic_info,
)
from app.crud.inventory import (
    get_inventory_expiration_date,
    get_inventory_purchase_date,
    get_inventory_quantity,
    update_inventory_expiration_date,
    update_inventory_purchase_date,
    get_inventory_lots,
)
from app.crud.shopping_item import (
    add_ingredients_to_shopping_list,
)
from app.database import get_db
from app.services.ingredient_form import (
    SHOPPING_LIST_SOURCE,
    build_duplicate_context,
    build_new_form_data,
    date_to_form_value,
    get_option_form_values,
    normalize_registration_source,
    parse_optional_date,
    parse_required_date,
    resolve_selected_option,
)
from app.utils.ingredient_name import normalize_ingredient_name
from app.utils.quantity import is_valid_quantity_step


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


EXPIRATION_WARNING_DAYS = 3


def build_expiration_display_by_ingredient_id(
    ingredients,
) -> dict[int, dict[str, str]]:
    """一覧画面用の消費期限表示情報を食材IDごとに作成する。"""
    today = date.today()
    warning_limit = today + timedelta(
        days=EXPIRATION_WARNING_DAYS
    )

    expiration_display_by_ingredient_id = {}

    for ingredient in ingredients:
        expiration_date = get_inventory_expiration_date(
            ingredient
        )

        if expiration_date is None:
            expiration_display = {
                "date": "未設定",
                "status": "unset",
                "label": "",
            }

        elif expiration_date < today:
            expiration_display = {
                "date": date_to_form_value(expiration_date),
                "status": "expired",
                "label": "期限切れ",
            }

        elif expiration_date <= warning_limit:
            expiration_display = {
                "date": date_to_form_value(expiration_date),
                "status": "expiring-soon",
                "label": "期限間近",
            }

        else:
            expiration_display = {
                "date": date_to_form_value(expiration_date),
                "status": "normal",
                "label": "",
            }

        expiration_display_by_ingredient_id[
            ingredient.id
        ] = expiration_display

    return expiration_display_by_ingredient_id


def build_ingredient_list_redirect_url(
    ingredient_id: int | None = None,
    keyword: str | None = None,
    category_filters: list[str] | None = None,
    sort: str = "category",
    out_of_stock_first: bool = False,
    expiration_message: str | None = None,
    expiration_error: str | None = None,
) -> str:
    """一覧条件を維持したリダイレクトURLを作成する。"""
    query_params: list[tuple[str, str]] = []

    if keyword:
        query_params.append(
            ("keyword", keyword)
        )

    for category in category_filters:
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

    if expiration_message:
        query_params.append(
            (
                "expiration_message",
                expiration_message,
            )
        )

    if expiration_error:
        query_params.append(
            (
                "expiration_error",
                expiration_error,
            )
        )

    query_string = urlencode(
        query_params,
        doseq=True,
    )

    url = "/"

    if query_string:
        url = f"/?{query_string}"

    if ingredient_id is not None:
        url += f"#ingredient-{ingredient_id}"

    return url


def render_new_ingredient_error(
    request: Request,
    form_data: dict,
    error_message: str,
    status_code: int = 400,
):
    """食材登録画面へエラーメッセージを表示する。"""
    return templates.TemplateResponse(
        request=request,
        name="ingredients/new.html",
        context={
            "category_options": CATEGORY_OPTIONS,
            "unit_options": UNIT_OPTIONS,
            "other_option": OTHER_OPTION,
            "form_data": form_data,
            "error_message": error_message,
        },
        status_code=status_code,
    )


def render_duplicate_confirmation(
    request: Request,
    existing_ingredient,
    name: str,
    category: str,
    quantity: float,
    default_unit: str,
    purchase_date: date,
    expiration_date: date | None,
    error_message: str | None = None,
    status_code: int = 409,
    source: str = "",
):
    """重複食材の確認画面を表示する。"""
    context = build_duplicate_context(
    existing_ingredient=existing_ingredient,
    existing_quantity=get_inventory_quantity(
        existing_ingredient
    ),
    existing_purchase_date=(
        get_inventory_purchase_date(
            existing_ingredient
        )
    ),
    existing_expiration_date=(
        get_inventory_expiration_date(
            existing_ingredient
        )
    ),
    name=name,
    category=category,
    quantity=quantity,
    default_unit=default_unit,
    purchase_date=purchase_date,
    expiration_date=expiration_date,
    error_message=error_message,
    source=source,
)
    
    return templates.TemplateResponse(
        request=request,
        name="ingredients/duplicate_confirm.html",
        context=context,
        status_code=status_code,
    )


@router.get("/")
def list_ingredients(
    request: Request,
    keyword: str | None = Query(None),
    category_filters: list[str] = Query(default=[]),
    sort: str = Query("category"),
    out_of_stock_first: bool = Query(False),
    expiration_message: str | None = Query(None),
    expiration_error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """食材一覧画面を表示する。"""

    allowed_sorts = [
        "id",
        "name",
        "category",
        "expiration_asc",
        "expiration_desc",
    ]

    if sort not in allowed_sorts:
        sort = "category"

    categories = get_categories(db)

    ingredients = get_filtered_ingredients(
        db=db,
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    quantity_by_ingredient_id = {
        ingredient.id: get_inventory_quantity(
            ingredient
        )
        for ingredient in ingredients
    }

    purchase_date_by_ingredient_id = {
        ingredient.id: date_to_form_value(
            get_inventory_purchase_date(ingredient)
        )
        for ingredient in ingredients
    }

    expiration_display_by_ingredient_id = (
        build_expiration_display_by_ingredient_id(
            ingredients
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/list.html",
        context={
            "ingredients": ingredients,
            "quantity_by_ingredient_id": (
                quantity_by_ingredient_id
            ),
            "keyword": keyword or "",
            "category_filters": category_filters,
            "categories": categories,
            "sort": sort,
            "out_of_stock_first": out_of_stock_first,
            "purchase_date_by_ingredient_id": (
                purchase_date_by_ingredient_id
            ),
            "expiration_display_by_ingredient_id": (
                expiration_display_by_ingredient_id
            ),
            "expiration_message": expiration_message,
            "expiration_error": expiration_error,
        },
    )


@router.get("/ingredients/new")
def new_ingredient(
    request: Request,
    source: str = Query(default=""),
):
    """食材登録画面を表示する。"""
    normalized_source = (
        normalize_registration_source(
            source
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/new.html",
        context={
            "category_options": (
                CATEGORY_OPTIONS
            ),
            "unit_options": UNIT_OPTIONS,
            "other_option": OTHER_OPTION,
            "form_data": {
                "name": "",
                "category_select": "",
                "category_other": "",
                "default_unit_select": "",
                "default_unit_other": "",
                "quantity": 0,
                "purchase_date": (
                    date.today().isoformat()
                ),
                "expiration_date": "",
                "source": normalized_source,
            },
        },
    )


@router.post("/ingredients")
def create_ingredient_route(
    request: Request,
    name: str = Form(...),
    category_select: str = Form(...),
    category_other: str | None = Form(None),
    default_unit_select: str = Form(...),
    default_unit_other: str | None = Form(None),
    quantity: float = Form(...),
    purchase_date: str = Form(...),
    expiration_date: str | None = Form(None),
    source: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """食材を新規登録する。"""
    normalized_source = (
        normalize_registration_source(
            source
        )
    )

    normalized_name = (
        normalize_ingredient_name(
            name
        )
    )

    form_data = build_new_form_data(
        name=normalized_name,
        category_select=category_select,
        category_other=category_other,
        default_unit_select=(
            default_unit_select
        ),
        default_unit_other=(
            default_unit_other
        ),
        quantity=quantity,
        purchase_date=purchase_date,
        expiration_date=expiration_date,
        source=normalized_source,
    )

    if not normalized_name:
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message="食材名を入力してください。",
        )

    category, category_error = resolve_selected_option(
        selected_value=category_select,
        other_value=category_other,
        allowed_options=CATEGORY_OPTIONS,
        field_label="カテゴリ",
    )

    if category_error:
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=category_error,
        )

    default_unit, unit_error = resolve_selected_option(
        selected_value=default_unit_select,
        other_value=default_unit_other,
        allowed_options=UNIT_OPTIONS,
        field_label="単位",
    )

    if unit_error:
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=unit_error,
        )

    if quantity < 0:
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=(
                "在庫数量は0以上で入力してください。"
            ),
        )

    if not is_valid_quantity_step(quantity):
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=(
                "在庫数量は0.5刻みで入力してください。"
            ),
        )

    parsed_purchase_date, purchase_date_error = (
        parse_required_date(
            purchase_date,
            field_label="購入日",
        )
    )

    if purchase_date_error:
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=purchase_date_error,
        )

    assert parsed_purchase_date is not None

    parsed_expiration_date, expiration_date_error = (
        parse_optional_date(expiration_date)
    )

    if expiration_date_error:
        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=expiration_date_error,
        )

    assert category is not None
    assert default_unit is not None

    existing_ingredient = get_ingredient_by_name(
        db=db,
        name=normalized_name,
    )

    if existing_ingredient is not None:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
            source=normalized_source,
        )

    try:
        created_ingredient = create_ingredient(
            db=db,
            name=normalized_name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
        )
    except IntegrityError:
        db.rollback()

        # 重複確認から登録までの間に、
        # 同名食材が登録された場合に備えて再確認する。
        existing_ingredient = get_ingredient_by_name(
            db=db,
            name=normalized_name,
        )

        if existing_ingredient is not None:
            return render_duplicate_confirmation(
                request=request,
                existing_ingredient=existing_ingredient,
                name=normalized_name,
                category=category,
                quantity=quantity,
                default_unit=default_unit,
                purchase_date=parsed_purchase_date,
                expiration_date=parsed_expiration_date,
                source=normalized_source,
            )

        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=(
                "食材の登録中にエラーが発生しました。"
            ),
        )

    if (
        normalized_source
        == SHOPPING_LIST_SOURCE
    ):
        added_count = (
            add_ingredients_to_shopping_list(
                db=db,
                ingredient_ids=[
                    created_ingredient.id
                ],
            )
        )

        if added_count == 0:
            message = (
                f"{created_ingredient.name}を"
                "登録しました。"
                "買うものリストには"
                "すでに追加されています"
            )
        else:
            message = (
                f"{created_ingredient.name}を"
                "新しい食材として登録し、"
                "買うものリストへ追加しました"
            )

        return RedirectResponse(
            url=(
                "/shopping-list/add?"
                + urlencode(
                    {
                        "message": message
                    }
                )
            ),
            status_code=303,
        )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@router.get("/ingredients/{ingredient_id}/edit")
def edit_ingredient(
    ingredient_id: int,
    request: Request,
    lot_message: str | None = Query(None),
    lot_error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    食材基本情報と在庫ロットを表示する。
    """
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    category_select, category_other = (
        get_option_form_values(
            current_value=ingredient.category,
            allowed_options=CATEGORY_OPTIONS,
        )
    )

    unit_select, unit_other = (
        get_option_form_values(
            current_value=(
                ingredient.default_unit
            ),
            allowed_options=UNIT_OPTIONS,
        )
    )

    inventory_lots = get_inventory_lots(
        db=db,
        ingredient_id=ingredient_id,
    )

    total_quantity = sum(
        float(inventory.quantity or 0)
        for inventory in inventory_lots
    )

    active_lot_count = sum(
        1
        for inventory in inventory_lots
        if float(inventory.quantity or 0) > 0
    )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/edit.html",
        context={
            "ingredient": ingredient,
            "category_options": (
                CATEGORY_OPTIONS
            ),
            "unit_options": UNIT_OPTIONS,
            "other_option": OTHER_OPTION,
            "form_data": {
                "name": ingredient.name,
                "category_select": (
                    category_select
                ),
                "category_other": (
                    category_other
                ),
                "default_unit_select": (
                    unit_select
                ),
                "default_unit_other": (
                    unit_other
                ),
            },
            "inventory_lots": inventory_lots,
            "total_quantity": total_quantity,
            "active_lot_count": (
                active_lot_count
            ),
            "today": date.today(),
            "new_lot_form": {
                "quantity": 0.5,
                "purchase_date": (
                    date.today().isoformat()
                ),
                "expiration_date": "",
            },
            "lot_message": lot_message,
            "lot_error": lot_error,
        },
    )


@router.post("/ingredients/{ingredient_id}/edit")
def update_ingredient_route(
    ingredient_id: int,
    request: Request,
    name: str = Form(...),
    category_select: str = Form(...),
    category_other: str | None = Form(None),
    default_unit_select: str = Form(...),
    default_unit_other: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """食材の基本情報だけを更新する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    normalized_name = normalize_ingredient_name(
        name
    )

    form_data = {
        "name": normalized_name,
        "category_select": category_select,
        "category_other": (
            category_other or ""
        ),
        "default_unit_select": (
            default_unit_select
        ),
        "default_unit_other": (
            default_unit_other or ""
        ),
    }

    def render_edit_error(
        error_message: str,
        status_code: int = 400,
    ):
        inventory_lots = get_inventory_lots(
            db=db,
            ingredient_id=ingredient_id,
        )

        return templates.TemplateResponse(
            request=request,
            name="ingredients/edit.html",
            context={
                "ingredient": ingredient,
                "category_options": (
                    CATEGORY_OPTIONS
                ),
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "inventory_lots": (
                    inventory_lots
                ),
                "total_quantity": sum(
                    float(
                        inventory.quantity or 0
                    )
                    for inventory
                    in inventory_lots
                ),
                "active_lot_count": sum(
                    1
                    for inventory
                    in inventory_lots
                    if float(
                        inventory.quantity or 0
                    ) > 0
                ),
                "today": date.today(),
                "new_lot_form": {
                    "quantity": 0.5,
                    "purchase_date": (
                        date.today().isoformat()
                    ),
                    "expiration_date": "",
                },
                "error_message": (
                    error_message
                ),
            },
            status_code=status_code,
        )

    if not normalized_name:
        return render_edit_error(
            "食材名を入力してください。"
        )

    category, category_error = (
        resolve_selected_option(
            selected_value=category_select,
            other_value=category_other,
            allowed_options=CATEGORY_OPTIONS,
            field_label="カテゴリ",
        )
    )

    if category_error:
        return render_edit_error(
            category_error
        )

    default_unit, unit_error = (
        resolve_selected_option(
            selected_value=(
                default_unit_select
            ),
            other_value=default_unit_other,
            allowed_options=UNIT_OPTIONS,
            field_label="単位",
        )
    )

    if unit_error:
        return render_edit_error(
            unit_error
        )

    duplicate_ingredient = (
        get_ingredient_by_name(
            db=db,
            name=normalized_name,
            exclude_ingredient_id=(
                ingredient_id
            ),
        )
    )

    if duplicate_ingredient is not None:
        return render_edit_error(
            (
                f"「{normalized_name}」は"
                "すでに別の食材として"
                "登録されています。"
            ),
            status_code=409,
        )

    assert category is not None
    assert default_unit is not None

    try:
        update_ingredient_basic_info(
            db=db,
            ingredient_id=ingredient_id,
            name=normalized_name,
            category=category,
            default_unit=default_unit,
        )

    except IntegrityError:
        db.rollback()

        return render_edit_error(
            "同じ名前の食材は登録できません。"
        )

    return RedirectResponse(
        url=(
            f"/ingredients/{ingredient_id}"
            "/edit#ingredient-basic-info"
        ),
        status_code=303,
    )


@router.get("/ingredients/{ingredient_id}/delete")
def confirm_delete_ingredient(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """食材削除確認画面を表示する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/delete.html",
        context={
            "ingredient": ingredient,
        },
    )


@router.post("/ingredients/{ingredient_id}/delete")
def delete_ingredient_route(
    ingredient_id: int,
    db: Session = Depends(get_db),
):
    """食材を削除する。"""
    delete_ingredient(
        db=db,
        ingredient_id=ingredient_id,
    )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@router.post(
    "/ingredients/{ingredient_id}/purchase-date/auto"
)
def auto_update_purchase_date_route(
    ingredient_id: int,
    purchase_date: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    一覧画面から最古ロットの購入日を更新する。
    """
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": (
                    "更新対象の食材が"
                    "見つかりません。"
                ),
            },
        )

    parsed_purchase_date, error_message = (
        parse_required_date(
            purchase_date,
            field_label="購入日",
        )
    )

    if error_message:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": error_message,
            },
        )

    assert parsed_purchase_date is not None

    try:
        updated_inventory = (
            update_inventory_purchase_date(
                db=db,
                ingredient_id=ingredient_id,
                purchase_date=(
                    parsed_purchase_date
                ),
            )
        )

    except Exception:
        db.rollback()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "購入日の保存に"
                    "失敗しました。"
                ),
            },
        )

    if updated_inventory is None:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": (
                    "在庫のあるロットがありません。"
                    "新しいロットを追加してください。"
                ),
            },
        )

    updated_ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    assert updated_ingredient is not None

    representative_purchase_date = (
        get_inventory_purchase_date(
            updated_ingredient
        )
    )

    return {
        "success": True,
        "message": "保存しました。",
        "purchase_date": date_to_form_value(
            representative_purchase_date
        ),
    }


@router.post(
    "/ingredients/{ingredient_id}/expiration-date/auto"
)
def auto_update_expiration_date_route(
    ingredient_id: int,
    expiration_date: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    一覧画面から最短期限ロットの
    消費期限を更新する。
    """
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": (
                    "更新対象の食材が"
                    "見つかりません。"
                ),
            },
        )

    (
        parsed_expiration_date,
        error_message,
    ) = parse_optional_date(
        expiration_date
    )

    if error_message:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": error_message,
            },
        )

    try:
        updated_inventory = (
            update_inventory_expiration_date(
                db=db,
                ingredient_id=ingredient_id,
                expiration_date=(
                    parsed_expiration_date
                ),
            )
        )

    except Exception:
        db.rollback()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "消費期限の保存に"
                    "失敗しました。"
                ),
            },
        )

    if updated_inventory is None:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": (
                    "在庫のあるロットがありません。"
                    "新しいロットを追加してください。"
                ),
            },
        )

    updated_ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    assert updated_ingredient is not None

    expiration_display = (
        build_expiration_display_by_ingredient_id(
            [updated_ingredient]
        )[ingredient_id]
    )

    return {
        "success": True,
        "message": "保存しました。",
        "expiration_date": (
            expiration_display["date"]
        ),
        "status": expiration_display["status"],
        "label": expiration_display["label"],
    }