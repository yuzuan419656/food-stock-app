from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    create_inventory_lot,
)
from app.models.inventory import Inventory


def create_ingredient_with_two_lots(
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

    create_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        quantity=3,
        purchase_date=date(
            2026,
            8,
            20,
        ),
        expiration_date=date(
            2026,
            8,
            28,
        ),
    )

    db_session.refresh(ingredient)

    return ingredient


def test_delete_confirmation_explains_soft_delete(
    client: TestClient,
    db_session: Session,
):
    ingredient = (
        create_ingredient_with_two_lots(
            db_session=db_session,
        )
    )

    response = client.get(
        f"/ingredients/{ingredient.id}/delete"
    )

    assert response.status_code == 200
    assert "一覧から削除" in response.text
    assert "データベース上に残ります" in (
        response.text
    )
    assert "復元できます" in response.text
    assert "合計在庫数量" in response.text
    assert "5" in response.text
    assert "在庫ロット数" in response.text
    assert "2" in response.text


def test_delete_route_keeps_ingredient_and_inventory_lots(
    client: TestClient,
    db_session: Session,
):
    ingredient = (
        create_ingredient_with_two_lots(
            db_session=db_session,
        )
    )

    ingredient_id = ingredient.id

    inventory_ids = {
        inventory.id
        for inventory
        in ingredient.inventories
    }

    response = client.post(
        f"/ingredients/{ingredient_id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 303

    normal_result = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient_id,
    )

    deleted_ingredient = (
        get_ingredient_by_id(
            db=db_session,
            ingredient_id=ingredient_id,
            include_inactive=True,
        )
    )

    remaining_inventory_ids = {
        inventory_id
        for (inventory_id,) in (
            db_session.query(
                Inventory.id
            )
            .filter(
                Inventory.ingredient_id
                == ingredient_id
            )
            .all()
        )
    }

    assert normal_result is None
    assert deleted_ingredient is not None
    assert deleted_ingredient.is_active is False
    assert (
        deleted_ingredient.deleted_at
        is not None
    )
    assert (
        remaining_inventory_ids
        == inventory_ids
    )