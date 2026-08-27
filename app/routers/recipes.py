from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.recipe import (
    get_recipe_by_id,
    get_recipes,
)
from app.crud.ingredient import get_ingredients
from app.database import get_db

from app.constants.ingredient_options import (
    CATEGORY_OPTIONS,
    OTHER_OPTION,
    UNIT_OPTIONS,
)
from app.constants.recipe_options import (
    RECIPE_CUISINE_OPTIONS,
    RECIPE_DISH_CATEGORY_OPTIONS,
)



router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


@router.get("")
def list_recipes(
    request: Request,
    db: Session = Depends(get_db),
):
    """有効なレシピの一覧を表示する。"""
    recipes = get_recipes(db=db)

    return templates.TemplateResponse(
        request=request,
        name="recipes/list.html",
        context={
            "recipes": recipes,
        },
    )


@router.get("/new")
def show_recipe_create_form(
    request: Request,
    db: Session = Depends(get_db),
):
    """レシピ登録画面を表示する。"""
    ingredients = get_ingredients(
        db=db,
        sort="name",
    )

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
        },
    )


@router.get("/{recipe_id}")
def show_recipe_detail(
    recipe_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """レシピの詳細を表示する。"""
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
        name="recipes/detail.html",
        context={
            "recipe": recipe,
        },
    )