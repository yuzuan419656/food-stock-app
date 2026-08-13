from datetime import date

import pytest

from app.crud.inventory import (
    get_inventory_expiration_date,
    get_inventory_purchase_date,
    get_inventory_quantity,
)
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory


def create_ingredient_with_lots(
    db_session,
    lots: list[dict],
) -> Ingredient:
    """テスト用の食材と在庫ロットを作成する。"""
    ingredient = Ingredient(
        name="テスト食材",
        category="野菜",
        default_unit="個",
    )

    db_session.add(ingredient)
    db_session.flush()

    for lot in lots:
        db_session.add(
            Inventory(
                ingredient_id=ingredient.id,
                quantity=lot["quantity"],
                purchase_date=lot["purchase_date"],
                expiration_date=lot.get(
                    "expiration_date"
                ),
            )
        )

    db_session.commit()
    db_session.refresh(ingredient)

    return ingredient


def test_get_inventory_quantity_sums_all_lots(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 2.5,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    10,
                ),
            },
            {
                "quantity": 3.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    15,
                ),
            },
        ],
    )

    result = get_inventory_quantity(ingredient)

    assert result == pytest.approx(5.5)


def test_get_inventory_quantity_returns_zero_without_lots(
    db_session,
):
    ingredient = Ingredient(
        name="在庫なし食材",
        category="野菜",
        default_unit="個",
    )

    db_session.add(ingredient)
    db_session.commit()
    db_session.refresh(ingredient)

    result = get_inventory_quantity(ingredient)

    assert result == 0.0


def test_get_inventory_expiration_date_returns_nearest_date(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 2.0,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    20,
                ),
            },
            {
                "quantity": 3.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    15,
                ),
            },
        ],
    )

    result = get_inventory_expiration_date(
        ingredient
    )

    assert result == date(2026, 8, 15)


def test_get_inventory_expiration_date_ignores_empty_lot(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 0,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    10,
                ),
            },
            {
                "quantity": 3.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    20,
                ),
            },
        ],
    )

    result = get_inventory_expiration_date(
        ingredient
    )

    assert result == date(2026, 8, 20)


def test_get_inventory_expiration_date_ignores_unset_date(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 2.0,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": None,
            },
            {
                "quantity": 3.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    20,
                ),
            },
        ],
    )

    result = get_inventory_expiration_date(
        ingredient
    )

    assert result == date(2026, 8, 20)


def test_get_inventory_expiration_date_returns_none_without_active_date(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 0,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    10,
                ),
            },
            {
                "quantity": 2.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": None,
            },
        ],
    )

    result = get_inventory_expiration_date(
        ingredient
    )

    assert result is None


def test_get_inventory_purchase_date_returns_oldest_active_date(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 0,
                "purchase_date": date(
                    2026,
                    7,
                    1,
                ),
                "expiration_date": None,
            },
            {
                "quantity": 2.0,
                "purchase_date": date(
                    2026,
                    8,
                    10,
                ),
                "expiration_date": None,
            },
            {
                "quantity": 3.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": None,
            },
        ],
    )

    result = get_inventory_purchase_date(
        ingredient
    )

    assert result == date(2026, 8, 5)


def test_get_inventory_purchase_date_returns_today_without_active_lots(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 0,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": None,
            },
        ],
    )

    result = get_inventory_purchase_date(
        ingredient
    )

    assert result == date.today()