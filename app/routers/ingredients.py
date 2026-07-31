from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    change_inventory_quantity,
    create_ingredient,
    delete_ingredient,
    get_categories,
    get_default_units,
    get_filtered_ingredients,
    get_ingredient_by_id,
    update_ingredient,
)
from app.database import get_db

from app.constants.ingredient_options import (
    CATEGORY_OPTIONS,
    OTHER_OPTION,
    UNIT_OPTIONS,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def is_valid_quantity_step(quantity: float) -> bool:
    """数量が0.5刻みかどうかを判定する。"""
    return abs(quantity * 2 - round(quantity * 2)) < 1e-9


def resolve_selected_option(
    selected_value: str,
    other_value: str | None,
    allowed_options: list[str],
    field_label: str,
) -> tuple[str | None, str | None]:
    """
    プルダウンと「その他」の入力値から、
    データベースへ保存する値を決定する。
    """
    selected_value = selected_value.strip()
    other_value = (other_value or "").strip()

    if not selected_value:
        return None, f"{field_label}を選択してください。"

    if selected_value == OTHER_OPTION:
        if not other_value:
            return None, f"{field_label}を入力してください。"

        return other_value, None

    if selected_value not in allowed_options:
        return None, f"{field_label}の選択内容が正しくありません。"

    return selected_value, None


def get_option_form_values(
        current_value: str | None,
        allowed_options: list[str],
) -> tuple[str, str]:
    """
    登録済みの値から、プルダウンと「その他」入力欄の初期値を決定する。
    """
    normalized_value = (current_value or "").strip()

    if not normalized_value:
        return "", ""
    
    if normalized_value in allowed_options:
        return normalized_value, ""

    return OTHER_OPTION, normalized_value

def build_list_redirect_url(
    keyword: str | None = None,
    category_filters: list[str] | None = None,
    sort: str = "id",
    out_of_stock_first: bool = False,
) -> str:
    """一覧画面の表示条件を維持したリダイレクトURLを作成する。"""
    query_params: list[tuple[str, str]] = []

    if keyword:
        query_params.append(("keyword", keyword))

    if category_filters:
        for category in category_filters:
            query_params.append(("category_filters", category))

    if sort in ["id", "name", "category"]:
        query_params.append(("sort", sort))

    if out_of_stock_first:
        query_params.append(("out_of_stock_first", "true"))

    if not query_params:
        return "/"

    return f"/?{urlencode(query_params)}"


@router.get("/")
def list_ingredients(
    request: Request,
    keyword: str | None = Query(None),
    category_filters: list[str] = Query(default=[]),
    sort: str = Query("id"),
    out_of_stock_first: bool = Query(False),
    db: Session = Depends(get_db),
):
    """食材一覧画面を表示する。"""
    if sort not in ["id", "name", "category"]:
        sort = "id"

    categories = get_categories(db)

    ingredients = get_filtered_ingredients(
        db=db,
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/list.html",
        context={
            "ingredients": ingredients,
            "keyword": keyword or "",
            "category_filters": category_filters,
            "categories": categories,
            "sort": sort,
            "out_of_stock_first": out_of_stock_first,
        },
    )


@router.get("/ingredients/new")
def new_ingredient(
    request: Request,
):
    """食材登録画面を表示する。"""
    return templates.TemplateResponse(
        request=request,
        name="ingredients/new.html",
        context={
            "category_options": CATEGORY_OPTIONS,
            "unit_options": UNIT_OPTIONS,
            "other_option": OTHER_OPTION,
            "form_data": {
                "name": "",
                "category_select": "",
                "category_other": "",
                "default_unit_select": "",
                "default_unit_other": "",
                "quantity": 0,
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
    db: Session = Depends(get_db),
):
    """食材を新規登録する。"""
    name = name.strip()

    form_data = {
        "name": name,
        "category_select": category_select,
        "category_other": category_other or "",
        "default_unit_select": default_unit_select,
        "default_unit_other": default_unit_other or "",
        "quantity": quantity,
    }

    if not name:
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": "食材名を入力してください。",
            },
            status_code=400,
        )

    category, category_error = resolve_selected_option(
        selected_value=category_select,
        other_value=category_other,
        allowed_options=CATEGORY_OPTIONS,
        field_label="カテゴリ",
    )

    if category_error:
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": category_error,
            },
            status_code=400,
        )

    default_unit, unit_error = resolve_selected_option(
        selected_value=default_unit_select,
        other_value=default_unit_other,
        allowed_options=UNIT_OPTIONS,
        field_label="単位",
    )

    if unit_error:
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": unit_error,
            },
            status_code=400,
        )

    if quantity < 0:
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": "在庫数量は0以上で入力してください。",
            },
            status_code=400,
        )

    if not is_valid_quantity_step(quantity):
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": "在庫数量は0.5刻みで入力してください。",
            },
            status_code=400,
        )

    try:
        create_ingredient(
            db=db,
            name=name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
        )
    except IntegrityError:
        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": "同じ名前の食材は登録できません。",
            },
            status_code=400,
        )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@router.get("/ingredients/{ingredient_id}/edit")
def edit_ingredient(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """食材編集画面を表示する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    category_select, category_other = get_option_form_values(
        current_value=ingredient.category,
        allowed_options=CATEGORY_OPTIONS,
    )

    unit_select, unit_other = get_option_form_values(
        current_value=ingredient.default_unit,
        allowed_options=UNIT_OPTIONS,
    )

    if ingredient.inventories:
        quantity = ingredient.inventories[0].quantity
    else:
        quantity = 0

    return templates.TemplateResponse(
        request=request,
        name="ingredients/edit.html",
        context={
            "ingredient": ingredient,
            "category_options": CATEGORY_OPTIONS,
            "unit_options": UNIT_OPTIONS,
            "other_option": OTHER_OPTION,
            "form_data": {
                "name": ingredient.name,
                "category_select": category_select,
                "category_other": category_other,
                "default_unit_select": unit_select,
                "default_unit_other": unit_other,
                "quantity": quantity,
            },
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
    quantity: float = Form(...),
    db: Session = Depends(get_db),
):
    """食材情報と在庫数量を更新する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    name = name.strip()

    form_data = {
        "name": name,
        "category_select": category_select,
        "category_other": category_other or "",
        "default_unit_select": default_unit_select,
        "default_unit_other": default_unit_other or "",
        "quantity": quantity,
    }

    def render_edit_error(error_message: str):
        return templates.TemplateResponse(
            request=request,
            name="ingredients/edit.html",
            context={
                "ingredient": ingredient,
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": form_data,
                "error_message": error_message,
            },
            status_code=400,
        )

    if not name:
        return render_edit_error(
            "食材名を入力してください。"
        )

    category, category_error = resolve_selected_option(
        selected_value=category_select,
        other_value=category_other,
        allowed_options=CATEGORY_OPTIONS,
        field_label="カテゴリ",
    )

    if category_error:
        return render_edit_error(category_error)

    default_unit, unit_error = resolve_selected_option(
        selected_value=default_unit_select,
        other_value=default_unit_other,
        allowed_options=UNIT_OPTIONS,
        field_label="単位",
    )

    if unit_error:
        return render_edit_error(unit_error)

    if quantity < 0:
        return render_edit_error(
            "在庫数量は0以上で入力してください。"
        )

    if not is_valid_quantity_step(quantity):
        return render_edit_error(
            "在庫数量は0.5刻みで入力してください。"
        )

    try:
        update_ingredient(
            db=db,
            ingredient_id=ingredient_id,
            name=name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
        )
    except IntegrityError:
        db.rollback()

        return render_edit_error(
            "同じ名前の食材は登録できません。"
        )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@router.post("/ingredients/{ingredient_id}/increment")
def increment_inventory_quantity(
    ingredient_id: int,
    keyword: str | None = Form(None),
    category_filters: list[str] = Form(default=[]),
    sort: str = Form("id"),
    out_of_stock_first: bool = Form(False),
    db: Session = Depends(get_db),
):
    """対象食材の在庫数量を0.5増やす。"""
    change_inventory_quantity(
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

    redirect_url = (
        f"{redirect_url}#ingredient-{ingredient_id}"
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=303,
    )


@router.post("/ingredients/{ingredient_id}/decrement")
def decrement_inventory_quantity(
    ingredient_id: int,
    keyword: str | None = Form(None),
    category_filters: list[str] = Form(default=[]),
    sort: str = Form("id"),
    out_of_stock_first: bool = Form(False),
    db: Session = Depends(get_db),
):
    """対象食材の在庫数量を0.5減らす。"""
    change_inventory_quantity(
        db=db,
        ingredient_id=ingredient_id,
        amount=-0.5,
    )

    redirect_url = build_list_redirect_url(
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

    redirect_url = (
        f"{redirect_url}#ingredient-{ingredient_id}"
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=303,
    )


@router.get("/ingredients/{ingredient_id}/delete")
def confirm_delete_ingredient(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """食材削除確認画面を表示する。"""
    ingredient = get_ingredient_by_id(db, ingredient_id)

    if ingredient is None:
        return RedirectResponse(url="/", status_code=303)

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

    return RedirectResponse(url="/", status_code=303)