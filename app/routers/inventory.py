from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.crud.inventory import change_inventory_quantity
from app.database import get_db
from app.utils.list_url import build_list_redirect_url


router = APIRouter()


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