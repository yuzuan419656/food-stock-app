from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.ingredient import get_ingredients
from app.database import get_db

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def list_ingredients(request: Request, db: Session = Depends(get_db)):
    ingredients = get_ingredients(db)

    return templates.TemplateResponse(
        request=request,
        name="ingredients/list.html",
        context={
            "ingredients": ingredients,
        },
    )