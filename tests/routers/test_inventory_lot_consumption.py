from datetime import date

import pytest

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory


def test_decrement_consumes_earliest_expiration_lot(
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

    later_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=2.0,
        purchase_date=date(
            2026,
            8,
            10,
        ),
        expiration_date=date(
            2026,
            8,
            25,
        ),
    )
    earlier_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=1.0,
        purchase_date=date(
            2026,
            8,
            5,
        ),
        expiration_date=date(
            2026,
            8,
            20,
        ),
    )

    db_session.add_all(
        [
            later_lot,
            earlier_lot,
        ]
    )
    db_session.commit()

    response = client.post(
        f"/ingredients/{ingredient.id}/decrement",
        data={
            "sort": "expiration_asc",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/?sort=expiration_asc"
    )

    db_session.refresh(earlier_lot)
    db_session.refresh(later_lot)

    assert earlier_lot.quantity == pytest.approx(
        0.5
    )
    assert later_lot.quantity == pytest.approx(
        2.0
    )