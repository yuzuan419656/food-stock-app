from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    delete_ingredient, 
    get_ingredients, 
    get_ingredient_by_id, 
    update_ingredient,
)
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
            "ingredients": ingredients
        },
    )


@router.get("/ingredients/new")
def new_ingredient(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ingredients/new.html",
        context={},
    )


@router.post("/ingredients")
def create_ingredient_route(
    request: Request,
    name: str = Form(...),
    category: str | None = Form(None),
    default_unit: str | None = Form(None),
    quantity: float | None = Form(None),
    db: Session = Depends(get_db),
):
    if quantity < 0:
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "error_message": "在庫数量は0以上で入力してください"
            },
        )
    
    try: 
        create_ingredient(
            db=db,
            name=name,
            category=category,
            default_unit=default_unit,
            quantity=quantity
        )
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="ingredients/new.html",
            context={
                "error_message": "その食材は既に存在します。"
            },
        )

    return RedirectResponse(url="/", status_code=303)


@router.get("/ingredients/{ingredient_id}/edit")
def edit_ingredient(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ingredient = get_ingredient_by_id(db, ingredient_id)

    if ingredient is None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="ingredients/edit.html",
        context={
            "ingredient": ingredient,
        },
    )


@router.post("/ingredients/{ingredient_id}/edit")
def update_ingredient_route(
    ingredient_id: int,
    request: Request,
    name: str = Form(...),
    category: str | None = Form(None),
    default_unit: str | None = Form(None),
    quantity: float = Form(...),
    db: Session = Depends(get_db),
):
    ingredient = get_ingredient_by_id(db, ingredient_id)

    if ingredient is None:
        return RedirectResponse(url="/", status_code=303)

    if quantity < 0:
        return templates.TemplateResponse(
            request=request,
            name="ingredients/edit.html",
            context={
                "ingredient": ingredient,
                "error_message": "在庫数量は0以上で入力してください。",
            },
        )

    try:
        update_ingredient(
            db=db,
            ingredient_id=ingredient_id,
            name=name,
            category=category,
            default_unit=default_unit,
            quantity=quantity,
        )
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="ingredients/edit.html",
            context={
                "ingredient": ingredient,
                "error_message": "同じ名前の食材は登録できません。",
            },
        )

    return RedirectResponse(url="/", status_code=303)


@router.get("/ingredients/{ingredient_id}/delete")
def confirm_delete_ingredient(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ingredient = get_ingredient_by_id(db, ingredient_id)

    if ingredient is None:
        return RedirectResponse(url="/", status_code=303)

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
    delete_ingredient(db=db, ingredient_id=ingredient_id)

    return RedirectResponse(url="/", status_code=303)