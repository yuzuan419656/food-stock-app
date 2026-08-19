from datetime import date
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)
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
from app.crud.shopping_item import (
    add_ingredients_to_shopping_list,
)
from app.database import get_db
from app.services.ingredient_form import (
    SHOPPING_LIST_SOURCE,
    build_duplicate_context,
    build_new_form_data,
    get_option_form_values,
    normalize_registration_source,
    parse_optional_date,
    parse_required_date,
)
from app.utils.ingredient_name import (
    normalize_ingredient_name,
)
from app.utils.quantity import (
    is_valid_quantity_step,
)


router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)


def build_shopping_add_url(
    message: str,
) -> str:
    """買うもの追加画面のURLを作る。"""
    return (
        "/shopping-list/add?"
        + urlencode(
            {
                "message": message,
            }
        )
    )


def redirect_after_duplicate_action(
    db: Session,
    ingredient_id: int,
    ingredient_name: str,
    source: str,
    action_message: str,
) -> RedirectResponse:
    """
    重複食材への処理後に適切な画面へ戻す。

    買うもの追加画面から遷移した場合は、
    対象食材を買うものリストにも追加する。
    """
    if source == SHOPPING_LIST_SOURCE:
        added_count = (
            add_ingredients_to_shopping_list(
                db=db,
                ingredient_ids=[
                    ingredient_id
                ],
            )
        )

        if added_count == 0:
            message = (
                f"{ingredient_name}の"
                f"{action_message}。"
                "買うものリストには"
                "すでに追加されています"
            )
        else:
            message = (
                f"{ingredient_name}の"
                f"{action_message}、"
                "買うものリストへ追加しました"
            )

        return RedirectResponse(
            url=build_shopping_add_url(
                message=message
            ),
            status_code=303,
        )

    return RedirectResponse(
        url=(
            f"/#ingredient-{ingredient_id}"
        ),
        status_code=303,
    )


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
            "category_options": (
                CATEGORY_OPTIONS
            ),
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
        existing_ingredient=(
            existing_ingredient
        ),
        existing_quantity=(
            get_inventory_quantity(
                existing_ingredient
            )
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
        name=(
            "ingredients/"
            "duplicate_confirm.html"
        ),
        context=context,
        status_code=status_code,
    )


@router.post(
    "/ingredients/resolve-duplicate"
)
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
    source: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """
    重複食材に対する上書き・数量加算・
    キャンセルを処理する。
    """
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

    category = category.strip()
    default_unit = default_unit.strip()

    category_select, category_other = (
        get_option_form_values(
            current_value=category,
            allowed_options=(
                CATEGORY_OPTIONS
            ),
        )
    )

    unit_select, unit_other = (
        get_option_form_values(
            current_value=default_unit,
            allowed_options=UNIT_OPTIONS,
        )
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
        source=normalized_source,
    )

    existing_ingredient = (
        get_ingredient_by_id(
            db=db,
            ingredient_id=(
                existing_ingredient_id
            ),
        )
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
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=date.today(),
            expiration_date=None,
            error_message=(
                purchase_date_error
            ),
            status_code=400,
            source=normalized_source,
        )

    assert parsed_purchase_date is not None

    (
        parsed_expiration_date,
        expiration_date_error,
    ) = parse_optional_date(
        expiration_date
    )

    if expiration_date_error:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=None,
            error_message=(
                expiration_date_error
            ),
            status_code=400,
            source=normalized_source,
        )

    if not normalized_name:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=(
                parsed_expiration_date
            ),
            error_message=(
                "食材名を入力してください。"
            ),
            status_code=400,
            source=normalized_source,
        )

    if not category:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=(
                parsed_expiration_date
            ),
            error_message=(
                "カテゴリを入力してください。"
            ),
            status_code=400,
            source=normalized_source,
        )

    if not default_unit:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=(
                parsed_expiration_date
            ),
            error_message=(
                "単位を入力してください。"
            ),
            status_code=400,
            source=normalized_source,
        )

    if quantity < 0:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=(
                parsed_expiration_date
            ),
            error_message=(
                "在庫数量は0以上で"
                "入力してください。"
            ),
            status_code=400,
            source=normalized_source,
        )

    if not is_valid_quantity_step(
        quantity
    ):
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=(
                existing_ingredient
            ),
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=(
                parsed_expiration_date
            ),
            error_message=(
                "在庫数量は0.5刻みで"
                "入力してください。"
            ),
            status_code=400,
            source=normalized_source,
        )

    duplicate_ingredient = (
        get_ingredient_by_name(
            db=db,
            name=normalized_name,
        )
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
                "重複する食材の状態が"
                "変更されました。"
                "もう一度登録内容を"
                "確認してください。"
            ),
            status_code=409,
        )

    if action == "cancel":
        if (
            normalized_source
            == SHOPPING_LIST_SOURCE
        ):
            return RedirectResponse(
                url=build_shopping_add_url(
                    message=(
                        "食材の登録を"
                        "キャンセルしました"
                    )
                ),
                status_code=303,
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
                ingredient_id=(
                    existing_ingredient_id
                ),
                name=normalized_name,
                category=category,
                default_unit=default_unit,
                quantity=quantity,
                purchase_date=(
                    parsed_purchase_date
                ),
                expiration_date=(
                    parsed_expiration_date
                ),
            )

        except IntegrityError:
            db.rollback()

            return render_duplicate_confirmation(
                request=request,
                existing_ingredient=(
                    existing_ingredient
                ),
                name=normalized_name,
                category=category,
                quantity=quantity,
                default_unit=default_unit,
                purchase_date=(
                    parsed_purchase_date
                ),
                expiration_date=(
                    parsed_expiration_date
                ),
                error_message=(
                    "食材の上書き中に"
                    "エラーが発生しました。"
                ),
                status_code=400,
                source=normalized_source,
            )

        return redirect_after_duplicate_action(
            db=db,
            ingredient_id=(
                existing_ingredient_id
            ),
            ingredient_name=normalized_name,
            source=normalized_source,
            action_message=(
                "登録内容を上書きしました"
            ),
        )

    if action == "add":
        if (
            existing_ingredient.default_unit
            != default_unit
        ):
            return render_duplicate_confirmation(
                request=request,
                existing_ingredient=(
                    existing_ingredient
                ),
                name=normalized_name,
                category=category,
                quantity=quantity,
                default_unit=default_unit,
                purchase_date=(
                    parsed_purchase_date
                ),
                expiration_date=(
                    parsed_expiration_date
                ),
                error_message=(
                    "既存の単位と今回入力した"
                    "単位が異なるため、"
                    "数量を加算できません。"
                ),
                status_code=400,
                source=normalized_source,
            )

        add_inventory_quantity(
            db=db,
            ingredient_id=(
                existing_ingredient_id
            ),
            amount=quantity,
            purchase_date=(
                parsed_purchase_date
            ),
            expiration_date=(
                parsed_expiration_date
            ),
        )

        return redirect_after_duplicate_action(
            db=db,
            ingredient_id=(
                existing_ingredient_id
            ),
            ingredient_name=(
                existing_ingredient.name
            ),
            source=normalized_source,
            action_message=(
                "在庫数量を加算しました"
            ),
        )

    return render_duplicate_confirmation(
        request=request,
        existing_ingredient=(
            existing_ingredient
        ),
        name=normalized_name,
        category=category,
        quantity=quantity,
        default_unit=default_unit,
        purchase_date=(
            parsed_purchase_date
        ),
        expiration_date=(
            parsed_expiration_date
        ),
        error_message=(
            "選択された処理が"
            "正しくありません。"
        ),
        status_code=400,
        source=normalized_source,
    )