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
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    get_ingredient_by_id,
)
from app.crud.shopping_item import (
    add_custom_shopping_item,
    add_ingredients_to_shopping_list,
    delete_purchased_shopping_items,
    delete_shopping_item,
    get_shopping_ingredient_candidates,
    get_shopping_ingredient_categories,
    get_shopping_items,
    toggle_shopping_item,
)
from app.database import get_db


router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)


def build_shopping_list_url(
    message: str | None = None,
) -> str:
    parameters: dict[str, str] = {}

    if message:
        parameters["message"] = message

    if not parameters:
        return "/shopping-list"

    return (
        "/shopping-list?"
        + urlencode(parameters)
    )


def build_shopping_add_url(
    message: str | None = None,
    ingredient_keyword: str = "",
    ingredient_categories: (
        list[str] | None
    ) = None,
) -> str:
    parameters: list[
        tuple[str, str]
    ] = []

    if message:
        parameters.append(
            ("message", message)
        )

    cleaned_keyword = (
        ingredient_keyword.strip()
    )

    if cleaned_keyword:
        parameters.append(
            (
                "ingredient_keyword",
                cleaned_keyword,
            )
        )

    for category in (
        ingredient_categories or []
    ):
        cleaned_category = category.strip()

        if cleaned_category:
            parameters.append(
                (
                    "ingredient_categories",
                    cleaned_category,
                )
            )

    if not parameters:
        return "/shopping-list/add"

    return (
        "/shopping-list/add?"
        + urlencode(
            parameters,
            doseq=True,
        )
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


@router.get("/shopping-list/add")
def show_shopping_item_add_page(
    request: Request,
    message: str | None = Query(
        default=None
    ),
    ingredient_keyword: str = Query(
        default="",
        max_length=100,
    ),
    ingredient_categories: list[str] = (
        Query(default=[])
    ),
    db: Session = Depends(get_db),
):
    shopping_items = get_shopping_items(
        db=db
    )

    available_categories = (
        get_shopping_ingredient_categories(
            db=db
        )
    )

    selected_categories = [
        category.strip()
        for category in ingredient_categories
        if category.strip()
    ]

    has_ingredient_search = bool(
        ingredient_keyword.strip()
        or selected_categories
    )

    if has_ingredient_search:
        ingredient_candidates = (
            get_shopping_ingredient_candidates(
                db=db,
                keyword=ingredient_keyword,
                categories=(
                    selected_categories
                ),
            )
        )
    else:
        ingredient_candidates = []

    registered_ingredient_ids = {
        item.ingredient_id
        for item in shopping_items
        if item.ingredient_id is not None
    }

    return templates.TemplateResponse(
        request=request,
        name="shopping_list/add.html",
        context={
            "message": message,
            "ingredient_keyword": (
                ingredient_keyword
            ),
            "ingredient_categories": (
                selected_categories
            ),
            "available_categories": (
                available_categories
            ),
            "ingredient_candidates": (
                ingredient_candidates
            ),
            "registered_ingredient_ids": (
                registered_ingredient_ids
            ),
            "has_ingredient_search": (
                has_ingredient_search
            ),
        },
    )


@router.post("/shopping-list")
def add_shopping_items(
    ingredient_ids: list[int] = Form(
        default=[]
    ),
    db: Session = Depends(get_db),
):
    """
    在庫一覧から選択した食材を追加する。
    """
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
        url=build_shopping_list_url(
            message=message
        ),
        status_code=303,
    )


@router.post(
    "/shopping-list/add-ingredients"
)
def add_ingredients_directly(
    ingredient_ids: list[int] = Form(
        default=[]
    ),
    ingredient_keyword: str = Form(
        default=""
    ),
    ingredient_categories: list[str] = (
        Form(default=[])
    ),
    db: Session = Depends(get_db),
):
    if not ingredient_ids:
        return RedirectResponse(
            url=build_shopping_add_url(
                message=(
                    "追加する食材を"
                    "選択してください"
                ),
                ingredient_keyword=(
                    ingredient_keyword
                ),
                ingredient_categories=(
                    ingredient_categories
                ),
            ),
            status_code=303,
        )

    unique_ingredient_ids = list(
        dict.fromkeys(ingredient_ids)
    )

    for ingredient_id in (
        unique_ingredient_ids
    ):
        ingredient = get_ingredient_by_id(
            db=db,
            ingredient_id=ingredient_id,
        )

        if ingredient is None:
            raise HTTPException(
                status_code=404,
                detail="食材が見つかりません",
            )

    added_count = (
        add_ingredients_to_shopping_list(
            db=db,
            ingredient_ids=(
                unique_ingredient_ids
            ),
        )
    )

    if added_count == 0:
        message = (
            "選択した食材はすべて"
            "追加済みです"
        )
    else:
        message = (
            f"{added_count}件を"
            "買うものリストへ追加しました"
        )

    return RedirectResponse(
        url=build_shopping_add_url(
            message=message,
            ingredient_keyword=(
                ingredient_keyword
            ),
            ingredient_categories=(
                ingredient_categories
            ),
        ),
        status_code=303,
    )


@router.post(
    "/shopping-list/add-custom"
)
def add_custom_item_directly(
    custom_name: str = Form(
        default=""
    ),
    db: Session = Depends(get_db),
):
    try:
        shopping_item = (
            add_custom_shopping_item(
                db=db,
                custom_name=custom_name,
            )
        )

    except ValueError as error:
        return RedirectResponse(
            url=build_shopping_add_url(
                message=str(error)
            ),
            status_code=303,
        )

    if shopping_item is None:
        message = (
            "同じ項目はすでに"
            "買うものリストに"
            "追加されています"
        )
    else:
        message = (
            f"{shopping_item.display_name}を"
            "買うものリストへ"
            "追加しました"
        )

    return RedirectResponse(
        url=build_shopping_add_url(
            message=message
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
            "購入済みの項目はありません"
        )
    else:
        message = (
            f"購入済みの項目を"
            f"{deleted_count}件削除しました"
        )

    return RedirectResponse(
        url=build_shopping_list_url(
            message=message
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