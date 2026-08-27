from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.recipe import get_recipes
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