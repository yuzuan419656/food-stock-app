from urllib.parse import urlencode

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
    change_inventory_quantity,
    get_inventory_quantity,
)

from app.database import get_db
from app.utils.ingredient_name import normalize_ingredient_name


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
    登録済みの値から、
    プルダウンと「その他」入力欄の初期値を決定する。
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
            query_params.append(
                ("category_filters", category)
            )

    if sort in ["id", "name", "category"]:
        query_params.append(("sort", sort))

    if out_of_stock_first:
        query_params.append(
            ("out_of_stock_first", "true")
        )

    if not query_params:
        return "/"

    return f"/?{urlencode(query_params)}"


def build_duplicate_form_data(
    name: str,
    category: str,
    quantity: float,
    default_unit: str,
) -> dict:
    """
    重複確認画面から確定処理へ引き継ぐ入力値を作成する。
    """
    return {
        "name": name,
        "category": category,
        "quantity": quantity,
        "default_unit": default_unit,
    }


def build_new_form_data(
    name: str,
    category_select: str,
    category_other: str | None,
    default_unit_select: str,
    default_unit_other: str | None,
    quantity: float,
) -> dict:
    """新規登録画面へ再表示するフォーム値を作成する。"""
    return {
        "name": name,
        "category_select": category_select,
        "category_other": category_other or "",
        "default_unit_select": default_unit_select,
        "default_unit_other": default_unit_other or "",
        "quantity": quantity,
    }


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
    error_message: str | None = None,
    status_code: int = 409,
):
    """重複食材の確認画面を表示する。"""
    existing_quantity = get_inventory_quantity(
        existing_ingredient
    )

    duplicate_form_data = build_duplicate_form_data(
        name=name,
        category=category,
        quantity=quantity,
        default_unit=default_unit,
    )

    return templates.TemplateResponse(
        request=request,
        name="ingredients/duplicate_confirm.html",
        context={
            "existing_ingredient": existing_ingredient,
            "existing_quantity": existing_quantity,
            "form_data": duplicate_form_data,
            "can_add_quantity": (
                existing_ingredient.default_unit
                == default_unit
            ),
            "error_message": error_message,
        },
        status_code=status_code,
    )


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
    normalized_name = normalize_ingredient_name(name)

    form_data = build_new_form_data(
        name=normalized_name,
        category_select=category_select,
        category_other=category_other,
        default_unit_select=default_unit_select,
        default_unit_other=default_unit_other,
        quantity=quantity,
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

    # ここまで正常に進んだ場合、
    # categoryとdefault_unitには必ず文字列が入っている。
    assert category is not None
    assert default_unit is not None

    # 食材を新規作成する前に、同名食材を検索する。
    existing_ingredient = get_ingredient_by_name(
        db=db,
        name=normalized_name,
    )

    # 同名食材が存在する場合は登録せず、
    # 上書き・数量加算・キャンセルの確認画面を表示する。
    if existing_ingredient is not None:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
        )

    try:
        create_ingredient(
            db=db,
            name=normalized_name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
        )
    except IntegrityError:
        db.rollback()

        # 重複確認後から登録までの間に、
        # 同名食材が登録された場合に備えた再確認。
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


@router.post("/ingredients/resolve-duplicate")
def resolve_duplicate_ingredient_route(
    request: Request,
    existing_ingredient_id: int = Form(...),
    action: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    quantity: float = Form(...),
    default_unit: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    重複食材に対する上書き・数量加算・キャンセルを処理する。
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

    if not normalized_name:
        return render_duplicate_confirmation(
            request=request,
            existing_ingredient=existing_ingredient,
            name=normalized_name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
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
            error_message=(
                "在庫数量は0.5刻みで入力してください。"
            ),
            status_code=400,
        )

    # hiddenフィールドのIDが書き換えられていないか確認する。
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
                error_message=(
                    "食材の上書き中にエラーが発生しました。"
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
                error_message=(
                    "既存の単位と今回入力した単位が"
                    "異なるため、数量を加算できません。"
                ),
                status_code=400,
            )

        change_inventory_quantity(
            db=db,
            ingredient_id=existing_ingredient_id,
            amount=quantity,
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
        error_message=(
            "選択された処理が正しくありません。"
        ),
        status_code=400,
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

    category_select, category_other = (
        get_option_form_values(
            current_value=ingredient.category,
            allowed_options=CATEGORY_OPTIONS,
        )
    )

    unit_select, unit_other = get_option_form_values(
        current_value=ingredient.default_unit,
        allowed_options=UNIT_OPTIONS,
    )

    quantity = get_inventory_quantity(ingredient)

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

    normalized_name = normalize_ingredient_name(name)

    form_data = build_new_form_data(
        name=normalized_name,
        category_select=category_select,
        category_other=category_other,
        default_unit_select=default_unit_select,
        default_unit_other=default_unit_other,
        quantity=quantity,
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