from datetime import date

import pytest

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory


def test_create_inventory_lot_route(
    client,
    db_session,
):
    ingredient = Ingredient(
        name="卵",
        category="卵",
        default_unit="個",
    )

    db_session.add(ingredient)
    db_session.flush()

    original_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=2.0,
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

    db_session.add(original_lot)
    db_session.commit()

    response = client.post(
        f"/ingredients/{ingredient.id}/inventories",
        data={
            "quantity": "3.0",
            "purchase_date": "2026-08-05",
            "expiration_date": "2026-08-20",
            "sort": "expiration_asc",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "sort=expiration_asc" in (
        response.headers["location"]
    )

    inventories = (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient.id
        )
        .order_by(Inventory.id)
        .all()
    )

    assert len(inventories) == 2
    assert inventories[0].quantity == pytest.approx(
        2.0
    )
    assert inventories[1].quantity == pytest.approx(
        3.0
    )
    assert inventories[
        1
    ].purchase_date == date(2026, 8, 5)
    assert inventories[
        1
    ].expiration_date == date(
        2026,
        8,
        20,
    )


def test_create_inventory_lot_route_rejects_zero(
    client,
    db_session,
):
    ingredient = Ingredient(
        name="牛乳",
        category="乳製品",
        default_unit="L",
    )

    db_session.add(ingredient)
    db_session.commit()

    response = client.post(
        f"/ingredients/{ingredient.id}/inventories",
        data={
            "quantity": "0",
            "purchase_date": "2026-08-13",
            "expiration_date": "",
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400

    inventory_count = (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient.id
        )
        .count()
    )

    assert inventory_count == 0