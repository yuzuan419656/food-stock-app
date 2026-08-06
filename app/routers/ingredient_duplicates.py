from datetime import date

from fastapi import APIRouter, Depends, Form, Request
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
    get_ingredient_by_id,
    get_ingredient_by_name,
    update_ingredient,
)
from app.crud.inventory import (
    add_inventory_quantity,
    get_inventory_expiration_date,
    get_inventory_purchase_date,
    get_inventory_quantity,
)
from app.database import get_db
from app.services.ingredient_form import (
    build_duplicate_context,
    build_new_form_data,
    get_option_form_values,
    parse_optional_date,
    parse_required_date,
)
from app.utils.ingredient_name import normalize_ingredient_name
from app.utils.quantity import is_valid_quantity_step


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def render_new_ingredient_error(
    request: Request,
    form_data: dict,
    error_message: str,
    status_code: int = 400,
):
    """食材登録画面へエラーを表示する。"""
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
    )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/duplicate_confirm.html",
        context=context,
        status_code=status_code,
    )


@router.post("/ingredients/resolve-duplicate")
def resolve_duplicate_ingredient_route(
    request: Request,
    existing_ingredient_id: int = Form(...),
    action: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    quantity: float = Form(...),
    default_unit: str = Form(...),
    purchase_date: str = Form(...),
    expiration_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    重複食材に対する上書き・数量加算・
    キャンセルを処理する。
    """
    normalized_name = normalize_ingredient_name(name)
    category = category.strip()
    default_unit = default_unit.strip()

    category_select, category_other = (
        get_option_form_values(
            current_value=category,
            allowed_options=CATEGORY_OPTIONS,
        )
    )

    unit_select, unit_other = get_option_form_values(
        current_value=default_unit,
        allowed_options=UNIT_OPTIONS,
    )

    new_form_data = build_new_form_data(
        name=normalized_name,
        category_select=category_select,
        category_other=category_other,
        default_unit_select=unit_select,
        default_unit_other=unit_other,
        quantity=quantity,
        purchase_date=purchase_date,
        expiration_date=expiration_date,
    )

    existing_ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=existing_ingredient_id,
    )

    if existing_ingredient is None:
        return render_new_ingredient_error(
            request=request,
            form_data=new_form_data,
            error_message=(
                "対象の食材が見つかりません。"
                "もう一度登録してください。"
            ),
            status_code=404,
        )

    parsed_purchase_date, purchase_date_error = (
        parse_required_date(
            purchase_date,
            field_label="購入日",
        )
    )

    if purchase_date_error:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=date.today(),
            expiration_date=None,
            error_message=purchase_date_error,
            status_code=400,
        )

    assert parsed_purchase_date is not None

    parsed_expiration_date, expiration_date_error = (
        parse_optional_date(expiration_date)
    )

    if expiration_date_error:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=None,
            error_message=expiration_date_error,
            status_code=400,
        )

    if not normalized_name:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
            error_message="食材名を入力してください。",
            status_code=400,
        )

    if not category:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
            error_message="カテゴリを入力してください。",
            status_code=400,
        )

    if not default_unit:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
            error_message="単位を入力してください。",
            status_code=400,
        )

    if quantity < 0:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
            error_message=(
                "在庫数量は0以上で入力してください。"
            ),
            status_code=400,
        )

    if not is_valid_quantity_step(quantity):
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
            error_message=(
                "在庫数量は0.5刻みで入力してください。"
            ),
            status_code=400,
        )

    duplicate_ingredient = get_ingredient_by_name(
        db=db,
        name=normalized_name,
    )

    if (
        duplicate_ingredient is None
        or duplicate_ingredient.id
        != existing_ingredient_id
    ):
        return render_new_ingredient_error(
            request=request,
            form_data=new_form_data,
            error_message=(
                "重複する食材の状態が変更されました。"
                "もう一度登録内容を確認してください。"
            ),
            status_code=409,
        )

    if action == "cancel":
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "category_options": CATEGORY_OPTIONS,
                "unit_options": UNIT_OPTIONS,
                "other_option": OTHER_OPTION,
                "form_data": new_form_data,
                "error_message": (
                    "登録をキャンセルしました。"
                ),
            },
        )

    if action == "overwrite":
        try:
            update_ingredient(
                db=db,
                ingredient_id=existing_ingredient_id,
                name=normalized_name,
                category=category,
                default_unit=default_unit,
                quantity=quantity,
                purchase_date=parsed_purchase_date,
                expiration_date=parsed_expiration_date,
            )

        except IntegrityError:
            db.rollback()

            return render_duplicate_confirmation(
                request=request,
                existing_ingredient=existing_ingredient,
                name=normalized_name,
                category=category,
                quantity=quantity,
                default_unit=default_unit,
                expiration_date=parsed_expiration_date,
                error_message=(
                    "食材の上書き中に"
                    "エラーが発生しました。"
                ),
                status_code=400,
            )

        return RedirectResponse(
            url=(
                f"/#ingredient-{existing_ingredient_id}"
            ),
            status_code=303,
        )

    if action == "add":
        if (
            existing_ingredient.default_unit
            != default_unit
        ):
            return render_duplicate_confirmation(
                request=request,
                existing_ingredient=existing_ingredient,
                name=normalized_name,
                category=category,
                quantity=quantity,
                default_unit=default_unit,
                expiration_date=parsed_expiration_date,
                error_message=(
                    "既存の単位と今回入力した単位が"
                    "異なるため、数量を加算できません。"
                ),
                status_code=400,
            )

        add_inventory_quantity(
            db=db,
            ingredient_id=existing_ingredient_id,
            amount=quantity,
            purchase_date=parsed_purchase_date,
            expiration_date=parsed_expiration_date,
        )

        return RedirectResponse(
            url=(
                f"/#ingredient-{existing_ingredient_id}"
            ),
            status_code=303,
        )

    return render_duplicate_confirmation(
        request=request,
        existing_ingredient=existing_ingredient,
        name=normalized_name,
        category=category,
        quantity=quantity,
        default_unit=default_unit,
        expiration_date=parsed_expiration_date,
        error_message=(
            "選択された処理が正しくありません。"
        ),
        status_code=400,
    )