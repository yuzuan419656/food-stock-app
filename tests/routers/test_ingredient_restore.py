from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    delete_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    get_inventory_quantity,
)
from app.crud.shopping_item import (
    get_shopping_items,
)
from app.constants.ingredient_options import (
    OTHER_OPTION,
)


def create_deleted_ingredient(
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="キャベツ",
        category="野菜",
        default_unit="玉",
        quantity=2,
        purchase_date=date(
            2026,
            8,
            1,
        ),
        expiration_date=date(
            2026,
            8,
            10,
        ),
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    return ingredient


def test_registering_deleted_name_shows_restore_confirmation(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_deleted_ingredient(
        db_session=db_session,
    )

    response = client.post(
        "/ingredients",
        data={
            "name": "キャベツ",
            "category_select": "野菜",
            "category_other": "",
            "default_unit_select": OTHER_OPTION,
            "default_unit_other": "玉",
            "quantity": "1",
            "purchase_date": "2026-08-20",
            "expiration_date": "2026-08-28",
            "source": "",
        },
    )

    assert response.status_code == 409
    assert "削除済み食材の復元確認" in response.text
    assert 'value="restore"' in response.text
    assert (
        str(ingredient.id)
        in response.text
    )


def test_restore_action_reactivates_same_ingredient(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_deleted_ingredient(
        db_session=db_session,
    )

    ingredient_id = ingredient.id

    response = client.post(
        "/ingredients/resolve-duplicate",
        data={
            "existing_ingredient_id": (
                str(ingredient_id)
            ),
            "action": "restore",
            "name": "キャベツ",
            "category": "葉物野菜",
            "quantity": "1",
            "default_unit": "玉",
            "purchase_date": "2026-08-20",
            "expiration_date": "2026-08-28",
            "source": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    restored_ingredient = (
        get_ingredient_by_id(
            db=db_session,
            ingredient_id=ingredient_id,
            include_inactive=True,
        )
    )

    assert restored_ingredient is not None
    assert restored_ingredient.is_active is True
    assert restored_ingredient.deleted_at is None
    assert restored_ingredient.id == ingredient_id
    assert (
        restored_ingredient.category
        == "葉物野菜"
    )
    assert (
        get_inventory_quantity(
            restored_ingredient
        )
        == 3
    )


def test_restore_from_shopping_list_adds_shopping_item(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_deleted_ingredient(
        db_session=db_session,
    )

    response = client.post(
        "/ingredients/resolve-duplicate",
        data={
            "existing_ingredient_id": (
                str(ingredient.id)
            ),
            "action": "restore",
            "name": "キャベツ",
            "category": "野菜",
            "quantity": "0",
            "default_unit": "玉",
            "purchase_date": "2026-08-20",
            "expiration_date": "",
            "source": "shopping_list",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith(
        "/shopping-list/add?"
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert len(shopping_items) == 1
    assert (
        shopping_items[0].ingredient_id
        == ingredient.id
    )


def test_restore_rejects_different_unit(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_deleted_ingredient(
        db_session=db_session,
    )

    response = client.post(
        "/ingredients/resolve-duplicate",
        data={
            "existing_ingredient_id": (
                str(ingredient.id)
            ),
            "action": "restore",
            "name": "キャベツ",
            "category": "野菜",
            "quantity": "1",
            "default_unit": "個",
            "purchase_date": "2026-08-20",
            "expiration_date": "",
            "source": "",
        },
    )

    assert response.status_code == 400
    assert "単位が異なるため" in response.text

    inactive_ingredient = (
        get_ingredient_by_id(
            db=db_session,
            ingredient_id=ingredient.id,
            include_inactive=True,
        )
    )

    assert inactive_ingredient is not None
    assert inactive_ingredient.is_active is False