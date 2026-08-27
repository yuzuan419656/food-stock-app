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
from app.database import get_db


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