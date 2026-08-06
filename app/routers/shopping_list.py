
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
from sqlalchemy.orm import Session

from app.crud.shopping_item import (
    add_ingredients_to_shopping_list,
    delete_purchased_shopping_items,
    delete_shopping_item,
    get_shopping_items,
    toggle_shopping_item,
)
from app.database import get_db


router = APIRouter()
templates = Jinja2Templates(
    directory="app/templates"
)


@router.get("/shopping-list")
def list_shopping_items(
    request: Request,
    message: str | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):
    shopping_items = get_shopping_items(
        db=db
    )

    has_purchased_items = any(
        item.is_purchased
        for item in shopping_items
    )

    return templates.TemplateResponse(
        request=request,
        name="shopping_list/list.html",
        context={
            "shopping_items": shopping_items,
            "has_purchased_items": (
                has_purchased_items
            ),
            "message": message,
        },
    )


@router.post("/shopping-list")
def add_shopping_items(
    ingredient_ids: list[int] = Form(
        default=[]
    ),
    db: Session = Depends(get_db),
):
    if not ingredient_ids:
        return RedirectResponse(
            url=(
                "/?"
                "message=食材を選択してください"
            ),
            status_code=303,
        )

    added_count = (
        add_ingredients_to_shopping_list(
            db=db,
            ingredient_ids=ingredient_ids,
        )
    )

    if added_count == 0:
        message = (
            "選択した食材はすでに"
            "追加されています"
        )
    else:
        message = (
            f"{added_count}件を"
            "買うものリストへ追加しました"
        )

    return RedirectResponse(
        url=(
            "/shopping-list"
            f"?message={message}"
        ),
        status_code=303,
    )


@router.post(
    "/shopping-list/delete-purchased"
)
def delete_purchased_items(
    db: Session = Depends(get_db),
):
    deleted_count = (
        delete_purchased_shopping_items(
            db=db
        )
    )

    if deleted_count == 0:
        message = (
            "購入済みの食材はありません"
        )
    else:
        message = (
            f"購入済みの食材を"
            f"{deleted_count}件削除しました"
        )

    return RedirectResponse(
        url=(
            "/shopping-list"
            f"?message={message}"
        ),
        status_code=303,
    )


@router.post(
    "/shopping-list/{shopping_item_id}/toggle"
)
def toggle_shopping_item_route(
    shopping_item_id: int,
    db: Session = Depends(get_db),
):
    shopping_item = toggle_shopping_item(
        db=db,
        shopping_item_id=shopping_item_id,
    )

    if shopping_item is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "買うものリストの項目が"
                "見つかりません"
            ),
        )

    return RedirectResponse(
        url="/shopping-list",
        status_code=303,
    )


@router.post(
    "/shopping-list/{shopping_item_id}/delete"
)
def delete_shopping_item_route(
    shopping_item_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_shopping_item(
        db=db,
        shopping_item_id=shopping_item_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=(
                "買うものリストの項目が"
                "見つかりません"
            ),
        )

    return RedirectResponse(
        url="/shopping-list",
        status_code=303,
    )