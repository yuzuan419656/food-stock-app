from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
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
)
from app.crud.inventory import (
    get_inventory_expiration_date,
    get_inventory_quantity,
)
from app.database import get_db
from app.services.ingredient_form import (
    build_duplicate_context,
    build_new_form_data,
    date_to_form_value,
    get_option_form_values,
    parse_optional_date,
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
    expiration_date: date | None,
    error_message: str | None = None,
    status_code: int = 409,
):
    """重複食材の確認画面を表示する。"""
    context = build_duplicate_context(
        existing_ingredient=existing_ingredient,
        existing_quantity=get_inventory_quantity(
            existing_ingredient
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
        expiration_date=expiration_date,
        error_message=error_message,
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
    db: Session = Depends(get_db),
):
    """食材一覧画面を表示する。"""
    if sort not in ["id", "name", "category"]:
        sort = "category"

    categories = get_categories(db)

    ingredients = get_filtered_ingredients(
        db=db,
        keyword=keyword,
        category_filters=category_filters,
        sort=sort,
        out_of_stock_first=out_of_stock_first,
    )

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
            "keyword": keyword or "",
            "category_filters": category_filters,
            "categories": categories,
            "sort": sort,
            "out_of_stock_first": out_of_stock_first,
            "expiration_display_by_ingredient_id": (
                expiration_display_by_ingredient_id
            ),
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
                "expiration_date": "",
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
    expiration_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """食材を新規登録する。"""
    normalized_name = normalize_ingredient_name(name)

    form_data = build_new_form_data(
        name=normalized_name,
        category_select=category_select,
        category_other=category_other,
        default_unit_select=default_unit_select,
        default_unit_other=default_unit_other,
        quantity=quantity,
        expiration_date=expiration_date,
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
            expiration_date=parsed_expiration_date,
        )

    try:
        create_ingredient(
            db=db,
            name=normalized_name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
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
                expiration_date=parsed_expiration_date,
            )

        return render_new_ingredient_error(
            request=request,
            form_data=form_data,
            error_message=(
                "食材の登録中にエラーが発生しました。"
            ),
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

    quantity = get_inventory_quantity(ingredient)

    expiration_date = get_inventory_expiration_date(
        ingredient
    )

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
                "expiration_date": date_to_form_value(
                    expiration_date
                ),
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
    expiration_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """食材情報・在庫数量・消費期限を更新する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    normalized_name = normalize_ingredient_name(name)

    form_data = build_new_form_data(
        name=normalized_name,
        category_select=category_select,
        category_other=category_other,
        default_unit_select=default_unit_select,
        default_unit_other=default_unit_other,
        quantity=quantity,
        expiration_date=expiration_date,
    )

    def render_edit_error(
        error_message: str,
        status_code: int = 400,
    ):
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
            status_code=status_code,
        )

    if not normalized_name:
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

    parsed_expiration_date, expiration_date_error = (
        parse_optional_date(expiration_date)
    )

    if expiration_date_error:
        return render_edit_error(
            expiration_date_error
        )

    assert category is not None
    assert default_unit is not None

    duplicate_ingredient = get_ingredient_by_name(
        db=db,
        name=normalized_name,
        exclude_ingredient_id=ingredient_id,
    )

    if duplicate_ingredient is not None:
        return render_edit_error(
            (
                f"「{normalized_name}」はすでに"
                "別の食材として登録されています。"
            ),
            status_code=409,
        )

    try:
        update_ingredient(
            db=db,
            ingredient_id=ingredient_id,
            name=normalized_name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
            expiration_date=parsed_expiration_date,
        )

    except IntegrityError:
        db.rollback()

        return render_edit_error(
            "同じ名前の食材は登録できません。"
        )

    return RedirectResponse(
        url=f"/#ingredient-{ingredient_id}",
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