from urllib.parse import urlencode
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
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
from app.constants.recipe_options import (
    RECIPE_CUISINE_OPTIONS,
    RECIPE_DISH_CATEGORY_OPTIONS,
)
from app.crud.ingredient import get_ingredients
from app.crud.cooking_history import (
    get_cooking_histories,
    get_cooking_history_by_id,
    get_latest_undoable_cooking_history,
)
from app.crud.recipe import (
    delete_recipe,
    get_recipe_by_id,
    get_recipes,
    update_recipe_favorite,
)
from app.database import get_db
from app.services.recipe_form import (
    RecipeFormValidationError,
    build_recipe_edit_form_data,
    build_recipe_form_data,
    parse_recipe_form,
)
from app.services.recipe_registration import (
    RecipeRegistrationError,
    register_recipe,
    update_registered_recipe,
)
from app.services.recipe_serving import (
    build_scaled_recipe_ingredients,
)
from app.services.recipe_inventory import (
    build_recipe_inventory_statuses,
)
from app.services.recipe_consumption import (
    build_recipe_consumption_plan,
    consume_recipe_inventory,
)
from app.services.cooking_undo import (
    CookingUndoError,
    build_cooking_undo_plan,
    undo_latest_cooking,
)
from app.services.recipe_shopping_list import (
    add_recipe_shortages_to_shopping_list,
    build_recipe_shopping_list_candidates,
    select_recipe_shopping_list_candidates,
)
from app.services.recipe_recommendation import (
    DEFAULT_RECOMMENDATION_WEIGHTS,
    RecommendationWeights,
    recommend_recipes,
)


router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


def build_recipe_list_url(
    message: str | None = None,
    favorite_only: bool = False,
    cuisine_type: str = "",
    dish_category: str = "",
    ingredient_keyword: str = "",
) -> str:
    """レシピ一覧の検索条件を含むURLを作成する。"""
    parameters: list[
        tuple[str, str]
    ] = []

    if message:
        parameters.append(
            ("message", message)
        )

    if favorite_only:
        parameters.append(
            ("favorite_only", "true")
        )

    cleaned_cuisine_type = (
        cuisine_type.strip()
    )

    if cleaned_cuisine_type:
        parameters.append(
            (
                "cuisine_type",
                cleaned_cuisine_type,
            )
        )

    cleaned_dish_category = (
        dish_category.strip()
    )

    if cleaned_dish_category:
        parameters.append(
            (
                "dish_category",
                cleaned_dish_category,
            )
        )

    cleaned_ingredient_keyword = (
        ingredient_keyword.strip()
    )

    if cleaned_ingredient_keyword:
        parameters.append(
            (
                "ingredient_keyword",
                cleaned_ingredient_keyword,
            )
        )

    if not parameters:
        return "/recipes"

    return (
        "/recipes?"
        + urlencode(parameters)
    )


def render_recipe_form(
    request: Request,
    db: Session,
    form_data: dict,
    error_message: str | None = None,
    status_code: int = 200,
    recipe_id: int | None = None,
):
    """レシピの登録・編集画面を表示する。"""
    ingredients = get_ingredients(
        db=db,
        sort="name",
    )

    is_edit = recipe_id is not None

    if is_edit:
        page_title = "レシピ編集"
        form_description = (
            "レシピの基本情報、材料、"
            "調理手順を編集します。"
        )
        form_action = (
            f"/recipes/{recipe_id}/edit"
        )
        submit_label = "変更を保存"
        cancel_url = f"/recipes/{recipe_id}"
        back_label = "レシピ詳細へ戻る"

    else:
        page_title = "レシピ登録"
        form_description = (
            "レシピの基本情報、材料、"
            "調理手順を入力します。"
        )
        form_action = "/recipes"
        submit_label = "レシピを登録"
        cancel_url = "/recipes"
        back_label = "レシピ一覧へ戻る"

    return templates.TemplateResponse(
        request=request,
        name="recipes/new.html",
        context={
            "ingredients": ingredients,
            "cuisine_options": (
                RECIPE_CUISINE_OPTIONS
            ),
            "dish_category_options": (
                RECIPE_DISH_CATEGORY_OPTIONS
            ),
            "category_options": CATEGORY_OPTIONS,
            "unit_options": UNIT_OPTIONS,
            "other_option": OTHER_OPTION,
            "form_data": form_data,
            "error_message": error_message,
            "page_title": page_title,
            "form_description": (
                form_description
            ),
            "form_action": form_action,
            "submit_label": submit_label,
            "cancel_url": cancel_url,
            "back_label": back_label,
            "is_edit": is_edit,
        },
        status_code=status_code,
    )


@router.get("")
def list_recipes(
    request: Request,
    message: str | None = Query(
        default=None,
        max_length=200,
    ),
    favorite_only: bool = Query(
        default=False,
    ),
    cuisine_type: str = Query(
        default="",
        max_length=50,
    ),
    dish_category: str = Query(
        default="",
        max_length=50,
    ),
    ingredient_keyword: str = Query(
        default="",
        max_length=100,
    ),
    db: Session = Depends(get_db),
):
    """有効なレシピの一覧を表示する。"""
    cleaned_cuisine_type = (
        cuisine_type.strip()
    )

    cleaned_dish_category = (
        dish_category.strip()
    )
    cleaned_ingredient_keyword = (
        ingredient_keyword.strip()
    )

    recipes = get_recipes(
        db=db,
        favorite_only=favorite_only,
        cuisine_type=cleaned_cuisine_type,
        dish_category=cleaned_dish_category,
        ingredient_keyword=(
            cleaned_ingredient_keyword
        ),
    )

    ingredient_candidates = get_ingredients(
        db=db,
        sort="name",
    )

    has_filters = bool(
        favorite_only
        or cleaned_cuisine_type
        or cleaned_dish_category
        or cleaned_ingredient_keyword
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/list.html",
        context={
            "recipes": recipes,
            "message": message,
            "favorite_only": favorite_only,
            "selected_cuisine_type": (
                cleaned_cuisine_type
            ),
            "selected_dish_category": (
                cleaned_dish_category
            ),
            "ingredient_keyword": (
                cleaned_ingredient_keyword
            ),
            "cuisine_options": (
                RECIPE_CUISINE_OPTIONS
            ),
            "dish_category_options": (
                RECIPE_DISH_CATEGORY_OPTIONS
            ),
            "ingredient_candidates": (
                ingredient_candidates
            ),
            "has_filters": has_filters,
        },
    )


@router.get("/recommendations")
def show_recipe_recommendations(
    request: Request,
    servings: int = Query(
        default=2,
        ge=1,
        le=100,
    ),
    mode: Literal[
        "balanced",
        "expiring",
        "quick",
        "in_stock",
    ] = Query(default="balanced"),
    max_cooking_time: Literal[
        "",
        "10",
        "20",
        "30",
    ] = Query(default=""),
    expiration_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.expiration,
        ge=0.0,
        le=3.0,
    ),
    inventory_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.inventory,
        ge=0.0,
        le=3.0,
    ),
    favorite_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.favorite,
        ge=0.0,
        le=3.0,
    ),
    history_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.history,
        ge=0.0,
        le=3.0,
    ),
    recency_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.recency,
        ge=0.0,
        le=3.0,
    ),
    cooking_time_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.cooking_time,
        ge=0.0,
        le=3.0,
    ),
    shortage_weight: float = Query(
        default=DEFAULT_RECOMMENDATION_WEIGHTS.shortage,
        ge=0.0,
        le=3.0,
    ),
    db: Session = Depends(get_db),
):
    """指定条件で採点したおすすめレシピを表示する。"""
    selected_max_cooking_time = (
        int(max_cooking_time)
        if max_cooking_time
        else None
    )
    custom_weights = RecommendationWeights(
        expiration=expiration_weight,
        inventory=inventory_weight,
        favorite=favorite_weight,
        history=history_weight,
        recency=recency_weight,
        cooking_time=cooking_time_weight,
        shortage=shortage_weight,
    )
    recommendations = recommend_recipes(
        db=db,
        target_servings=servings,
        mode=mode,
        max_cooking_time=selected_max_cooking_time,
        weights=custom_weights,
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/recommendations.html",
        context={
            "recommendations": recommendations,
            "selected_servings": servings,
            "selected_mode": mode,
            "selected_max_cooking_time": (
                selected_max_cooking_time
            ),
            "recommendation_weights": custom_weights,
        },
    )


@router.get("/new")
def show_recipe_create_form(
    request: Request,
    db: Session = Depends(get_db),
):
    """レシピ登録画面を表示する。"""
    return render_recipe_form(
        request=request,
        db=db,
        form_data=build_recipe_form_data(),
    )


@router.get("/{recipe_id}/edit")
def show_recipe_edit_form(
    recipe_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """レシピ編集画面を表示する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    return render_recipe_form(
        request=request,
        db=db,
        form_data=(
            build_recipe_edit_form_data(
                recipe
            )
        ),
        recipe_id=recipe.id,
    )


@router.post("/{recipe_id}/edit")
async def update_recipe_from_form(
    recipe_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """フォームからレシピを更新する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    submitted_form = await request.form()

    submitted_values = {
        key: str(value)
        for key, value
        in submitted_form.items()
    }

    form_data = build_recipe_form_data(
        submitted_values
    )

    try:
        parsed_form = parse_recipe_form(
            submitted_values
        )

        updated_recipe = (
            update_registered_recipe(
                db=db,
                recipe_id=recipe_id,
                parsed_form=parsed_form,
            )
        )

    except (
        RecipeFormValidationError,
        RecipeRegistrationError,
    ) as error:
        return render_recipe_form(
            request=request,
            db=db,
            form_data=form_data,
            error_message=str(error),
            status_code=400,
            recipe_id=recipe_id,
        )

    except IntegrityError:
        db.rollback()

        return render_recipe_form(
            request=request,
            db=db,
            form_data=form_data,
            error_message=(
                "レシピの更新に失敗しました。"
                "入力内容を確認してください。"
            ),
            status_code=400,
            recipe_id=recipe_id,
        )

    if updated_recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    parameters = urlencode({
        "message": "レシピを更新しました。",
    })

    return RedirectResponse(
        url=(
            f"/recipes/{updated_recipe.id}"
            f"?{parameters}"
        ),
        status_code=303,
    )


@router.post("")
async def create_recipe_from_form(
    request: Request,
    db: Session = Depends(get_db),
):
    """フォームからレシピを登録する。"""
    submitted_form = await request.form()

    submitted_values = {
        key: str(value)
        for key, value
        in submitted_form.items()
    }

    form_data = build_recipe_form_data(
        submitted_values
    )

    try:
        parsed_form = parse_recipe_form(
            submitted_values
        )

        recipe = register_recipe(
            db=db,
            parsed_form=parsed_form,
        )

    except (
        RecipeFormValidationError,
        RecipeRegistrationError,
    ) as error:
        return render_recipe_form(
            request=request,
            db=db,
            form_data=form_data,
            error_message=str(error),
            status_code=400,
        )

    except IntegrityError:
        db.rollback()

        return render_recipe_form(
            request=request,
            db=db,
            form_data=form_data,
            error_message=(
                "レシピの登録に失敗しました。"
                "入力内容を確認してください。"
            ),
            status_code=400,
        )

    parameters = urlencode({
        "message": "レシピを登録しました。",
    })

    return RedirectResponse(
        url=(
            f"/recipes/{recipe.id}"
            f"?{parameters}"
        ),
        status_code=303,
    )


@router.get("/{recipe_id}/delete")
def show_recipe_delete_confirmation(
    recipe_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """レシピ削除確認画面を表示する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    return templates.TemplateResponse(
        request=request,
        name="recipes/delete.html",
        context={
            "recipe": recipe,
        },
    )


@router.post("/{recipe_id}/delete")
def delete_recipe_from_form(
    recipe_id: int,
    db: Session = Depends(get_db),
):
    """レシピを論理削除する。"""
    deleted = delete_recipe(
        db=db,
        recipe_id=recipe_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    parameters = urlencode({
        "message": "レシピを削除しました。",
    })

    return RedirectResponse(
        url=f"/recipes?{parameters}",
        status_code=303,
    )


@router.get("/history")
def list_cooking_histories(
    request: Request,
    db: Session = Depends(get_db),
):
    """調理履歴を新しい順に表示する。"""
    histories = get_cooking_histories(db=db)
    undoable_history = (
        get_latest_undoable_cooking_history(db=db)
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/history_list.html",
        context={
            "histories": histories,
            "undoable_history_id": (
                undoable_history.id
                if undoable_history is not None
                else None
            ),
        },
    )


@router.get("/history/{cooking_history_id}")
def show_cooking_history_detail(
    cooking_history_id: int,
    request: Request,
    message: str | None = Query(
        default=None,
        max_length=200,
    ),
    error_message: str | None = Query(
        default=None,
        max_length=200,
    ),
    db: Session = Depends(get_db),
):
    """材料ごとの調理履歴を表示する。"""
    history = get_cooking_history_by_id(
        db=db,
        cooking_history_id=cooking_history_id,
    )

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="調理履歴が見つかりません。",
        )

    undoable_history = (
        get_latest_undoable_cooking_history(db=db)
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/history_detail.html",
        context={
            "history": history,
            "message": message,
            "error_message": error_message,
            "is_undoable": (
                undoable_history is not None
                and undoable_history.id == history.id
            ),
        },
    )


@router.get("/history/{cooking_history_id}/undo")
def show_cooking_undo_confirmation(
    cooking_history_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """直前の調理取り消し確認画面を表示する。"""
    try:
        result = build_cooking_undo_plan(
            db=db,
            cooking_history_id=cooking_history_id,
        )
    except CookingUndoError as error:
        parameters = urlencode({
            "error_message": str(error),
        })
        return RedirectResponse(
            url=(
                f"/recipes/history/{cooking_history_id}"
                f"?{parameters}"
            ),
            status_code=303,
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="調理履歴が見つかりません。",
        )

    history, undo_plan = result

    return templates.TemplateResponse(
        request=request,
        name="recipes/undo_confirm.html",
        context={
            "history": history,
            "undo_plan": undo_plan,
        },
    )


@router.post("/history/{cooking_history_id}/undo")
def undo_cooking(
    cooking_history_id: int,
    db: Session = Depends(get_db),
):
    """直前の調理を取り消して元ロットへ在庫を戻す。"""
    try:
        history = undo_latest_cooking(
            db=db,
            cooking_history_id=cooking_history_id,
        )
    except CookingUndoError as error:
        parameters = urlencode({
            "error_message": str(error),
        })
        return RedirectResponse(
            url=(
                f"/recipes/history/{cooking_history_id}"
                f"?{parameters}"
            ),
            status_code=303,
        )

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="調理履歴が見つかりません。",
        )

    parameters = urlencode({
        "message": "調理を取り消し、在庫を元に戻しました。",
    })

    return RedirectResponse(
        url=(
            f"/recipes/history/{history.id}"
            f"?{parameters}"
        ),
        status_code=303,
    )


@router.get("/{recipe_id}/cook")
def show_recipe_cook_confirmation(
    recipe_id: int,
    request: Request,
    servings: int | None = Query(
        default=None,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    """調理前の在庫消費内容を表示する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    selected_servings = None

    if recipe.yield_type == "servings":
        selected_servings = (
            servings
            if servings is not None
            else recipe.base_servings
        )

    consumption_plan = (
        build_recipe_consumption_plan(
            recipe=recipe,
            target_servings=selected_servings,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/cook_confirm.html",
        context={
            "recipe": recipe,
            "selected_servings": selected_servings,
            "consumption_plan": consumption_plan,
        },
    )


@router.post("/{recipe_id}/cook")
def cook_recipe(
    recipe_id: int,
    servings: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """確認済みのレシピ材料を在庫から消費する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    selected_servings = None

    if recipe.yield_type == "servings":
        selected_servings = (
            servings
            if servings is not None
            else recipe.base_servings
        )

        if (
            selected_servings is None
            or not 1 <= selected_servings <= 100
        ):
            raise HTTPException(
                status_code=422,
                detail="人数は1から100で指定してください。",
            )

    result = consume_recipe_inventory(
        db=db,
        recipe=recipe,
        target_servings=selected_servings,
    )

    message = "在庫を更新しました。"

    if result.has_shortage:
        message = (
            "一部材料が不足していたため、"
            "在庫にある分だけ消費しました。"
        )

    parameters: dict[str, str | int] = {
        "message": message,
    }

    if selected_servings is not None:
        parameters["servings"] = selected_servings

    return RedirectResponse(
        url=(
            f"/recipes/{recipe.id}?"
            f"{urlencode(parameters)}"
        ),
        status_code=303,
    )


@router.get("/{recipe_id}/shopping-list")
def show_recipe_shopping_list_confirmation(
    recipe_id: int,
    request: Request,
    servings: int | None = Query(
        default=None,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    """不足食材を買うものリストへ追加する前に表示する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    selected_servings = None
    if recipe.yield_type == "servings":
        selected_servings = (
            servings
            if servings is not None
            else recipe.base_servings
        )

    candidates = build_recipe_shopping_list_candidates(
        recipe=recipe,
        target_servings=selected_servings,
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/shopping_list_confirm.html",
        context={
            "recipe": recipe,
            "selected_servings": selected_servings,
            "candidates": candidates,
        },
    )


@router.post("/{recipe_id}/shopping-list")
def add_recipe_shortages(
    recipe_id: int,
    servings: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """現在庫で不足を再判定し、買うものリストへ追加する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    selected_servings = None
    if recipe.yield_type == "servings":
        selected_servings = (
            servings
            if servings is not None
            else recipe.base_servings
        )
        if (
            selected_servings is None
            or not 1 <= selected_servings <= 100
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "人数は1から100で指定してください。"
                ),
            )

    result = add_recipe_shortages_to_shopping_list(
        db=db,
        recipe=recipe,
        target_servings=selected_servings,
    )

    if result.candidate_count == 0:
        message = "追加対象の不足食材はありません。"
    elif result.added_count == 0:
        message = (
            "不足食材はすでに"
            "買うものリストへ追加されています。"
        )
    else:
        message = (
            f"不足食材{result.added_count}件を"
            "買うものリストへ追加しました。"
        )

    parameters: dict[str, str | int] = {"message": message}
    if selected_servings is not None:
        parameters["servings"] = selected_servings

    return RedirectResponse(
        url=f"/recipes/{recipe.id}?{urlencode(parameters)}",
        status_code=303,
    )


@router.get("/{recipe_id}")
def show_recipe_detail(
    recipe_id: int,
    request: Request,
    servings: int | None = Query(
        default=None,
        ge=1,
        le=100,
    ),
    message: str | None = Query(
        default=None,
        max_length=200,
    ),
    db: Session = Depends(get_db),
):
    """レシピ詳細を表示する。"""
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    selected_servings = None
    display_ingredients = None

    if recipe.yield_type == "servings":
        selected_servings = (
            servings
            if servings is not None
            else recipe.base_servings
        )

        display_ingredients = (
            build_scaled_recipe_ingredients(
                recipe=recipe,
                target_servings=(
                    selected_servings
                ),
            )
        )

    inventory_statuses = (
        build_recipe_inventory_statuses(
            recipe=recipe,
            target_servings=selected_servings,
        )
    )
    shopping_list_candidates = (
        select_recipe_shopping_list_candidates(
            inventory_statuses
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="recipes/detail.html",
        context={
            "recipe": recipe,
            "message": message,
            "selected_servings": (
                selected_servings
            ),
            "display_ingredients": (
                display_ingredients
            ),
            "inventory_statuses": (
                inventory_statuses
            ),
            "has_shopping_list_candidates": bool(
                shopping_list_candidates
            ),
        },
    )


@router.post("/{recipe_id}/favorite")
def update_recipe_favorite_from_list(
    recipe_id: int,
    is_favorite: bool = Form(...),
    favorite_only: bool = Form(False),
    cuisine_type: str = Form(""),
    dish_category: str = Form(""),
    ingredient_keyword: str = Form(""),
    db: Session = Depends(get_db),
):
    """一覧画面からお気に入り状態を更新する。"""
    updated_recipe = update_recipe_favorite(
        db=db,
        recipe_id=recipe_id,
        is_favorite=is_favorite,
    )

    if updated_recipe is None:
        raise HTTPException(
            status_code=404,
            detail="レシピが見つかりません。",
        )

    if is_favorite:
        message = (
            "お気に入りに登録しました。"
        )
    else:
        message = (
            "お気に入りを解除しました。"
        )

    return RedirectResponse(
        url=build_recipe_list_url(
            message=message,
            favorite_only=favorite_only,
            cuisine_type=cuisine_type,
            dish_category=dish_category,
            ingredient_keyword=(
                ingredient_keyword
            ),
        ),
        status_code=303,
    )
