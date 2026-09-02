from urllib.parse import urlencode

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