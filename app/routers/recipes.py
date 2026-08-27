from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
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
    get_recipe_by_id,
    get_recipes,
)
from app.database import get_db
from app.services.recipe_form import (
    RecipeFormValidationError,
    build_recipe_form_data,
    parse_recipe_form,
)
from app.services.recipe_registration import (
    RecipeRegistrationError,
    register_recipe,
)


router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


def render_recipe_form(
    request: Request,
    db: Session,
    form_data: dict,
    error_message: str | None = None,
    status_code: int = 200,
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
            "form_data": form_data,
            "error_message": error_message,
        },
        status_code=status_code,
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
    return render_recipe_form(
        request=request,
        db=db,
        form_data=build_recipe_form_data(),
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


@router.get("/{recipe_id}")
def show_recipe_detail(
    recipe_id: int,
    request: Request,
    message: str | None = Query(
        default=None,
        max_length=200,
    ),
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
            "message": message,
        },
    )