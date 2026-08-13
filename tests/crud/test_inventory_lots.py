from datetime import date

import pytest

from app.crud.inventory import (
    consume_inventory_quantity,
    create_inventory_lot,
    get_inventory_expiration_date,
    get_inventory_purchase_date,
    get_inventory_quantity,
    get_latest_active_inventory_lot,
    increment_latest_inventory_lot,
    sort_inventory_lots_for_consumption,
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


def get_inventory_lot(
    db_session,
    inventory_id: int,
) -> Inventory:
    """IDを指定してテスト対象の在庫ロットを取得する。"""
    inventory = db_session.get(
        Inventory,
        inventory_id,
    )

    assert inventory is not None

    return inventory


def test_consume_inventory_uses_earliest_expiration_first(
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
                "quantity": 1.0,
                "purchase_date": date(
                    2026,
                    8,
                    5,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    10,
                ),
            },
        ],
    )

    lot_by_expiration = {
        inventory.expiration_date: inventory.id
        for inventory in ingredient.inventories
    }

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None
    assert result.consumed_quantity == pytest.approx(
        0.5
    )
    assert result.shortage_quantity == pytest.approx(
        0.0
    )

    earlier_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=lot_by_expiration[
            date(2026, 8, 10)
        ],
    )
    later_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=lot_by_expiration[
            date(2026, 8, 20)
        ],
    )

    assert earlier_lot.quantity == pytest.approx(
        0.5
    )
    assert later_lot.quantity == pytest.approx(
        2.0
    )


def test_consume_inventory_uses_oldest_purchase_date_when_expiration_is_same(
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
                    5,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    20,
                ),
            },
            {
                "quantity": 1.0,
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
        ],
    )

    lot_by_purchase_date = {
        inventory.purchase_date: inventory.id
        for inventory in ingredient.inventories
    }

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None

    older_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=lot_by_purchase_date[
            date(2026, 8, 1)
        ],
    )
    newer_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=lot_by_purchase_date[
            date(2026, 8, 5)
        ],
    )

    assert older_lot.quantity == pytest.approx(
        0.5
    )
    assert newer_lot.quantity == pytest.approx(
        2.0
    )


def test_consume_inventory_uses_unset_expiration_last(
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
                "quantity": 1.0,
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

    dated_lot = next(
        inventory
        for inventory in ingredient.inventories
        if inventory.expiration_date is not None
    )
    unset_lot = next(
        inventory
        for inventory in ingredient.inventories
        if inventory.expiration_date is None
    )

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None

    db_session.refresh(dated_lot)
    db_session.refresh(unset_lot)

    assert dated_lot.quantity == pytest.approx(
        0.5
    )
    assert unset_lot.quantity == pytest.approx(
        2.0
    )


def test_consume_inventory_across_multiple_lots(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 1.0,
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

    lot_by_expiration = {
        inventory.expiration_date: inventory.id
        for inventory in ingredient.inventories
    }

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=2.5,
    )

    assert result is not None
    assert result.requested_quantity == pytest.approx(
        2.5
    )
    assert result.consumed_quantity == pytest.approx(
        2.5
    )
    assert result.shortage_quantity == pytest.approx(
        0.0
    )

    earlier_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=lot_by_expiration[
            date(2026, 8, 10)
        ],
    )
    later_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=lot_by_expiration[
            date(2026, 8, 20)
        ],
    )

    assert earlier_lot.quantity == pytest.approx(
        0.0
    )
    assert later_lot.quantity == pytest.approx(
        1.5
    )

    assert len(result.allocations) == 2

    assert (
        result.allocations[0].inventory_id
        == earlier_lot.id
    )
    assert result.allocations[
        0
    ].quantity == pytest.approx(1.0)

    assert (
        result.allocations[1].inventory_id
        == later_lot.id
    )
    assert result.allocations[
        1
    ].quantity == pytest.approx(1.5)


def test_consume_inventory_returns_shortage_when_stock_is_insufficient(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 1.0,
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
                "quantity": 0.5,
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

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=3.0,
    )

    assert result is not None
    assert result.requested_quantity == pytest.approx(
        3.0
    )
    assert result.consumed_quantity == pytest.approx(
        1.5
    )
    assert result.shortage_quantity == pytest.approx(
        1.5
    )

    for inventory in ingredient.inventories:
        db_session.refresh(inventory)

        assert inventory.quantity == pytest.approx(
            0.0
        )


def test_consume_inventory_skips_empty_lots(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 0.0,
                "purchase_date": date(
                    2026,
                    8,
                    1,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    5,
                ),
            },
            {
                "quantity": 2.0,
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

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None
    assert len(result.allocations) == 1

    allocated_lot = get_inventory_lot(
        db_session=db_session,
        inventory_id=(
            result.allocations[0].inventory_id
        ),
    )

    assert allocated_lot.expiration_date == date(
        2026,
        8,
        20,
    )
    assert allocated_lot.quantity == pytest.approx(
        1.5
    )


@pytest.mark.parametrize(
    "amount",
    [
        0,
        -0.5,
    ],
)
def test_consume_inventory_rejects_non_positive_amount(
    db_session,
    amount,
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
        ],
    )

    with pytest.raises(
        ValueError,
        match="減算量は0より大きい値",
    ):
        consume_inventory_quantity(
            db=db_session,
            ingredient_id=ingredient.id,
            amount=amount,
        )


def test_consume_inventory_returns_none_for_unknown_ingredient(
    db_session,
):
    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=999999,
        amount=0.5,
    )

    assert result is None


def test_create_inventory_lot_adds_new_lot(
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
                    10,
                ),
            },
        ],
    )

    inventory = create_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        quantity=3.0,
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

    assert inventory is not None

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
    assert sum(
        lot.quantity
        for lot in inventories
    ) == pytest.approx(5.0)


def test_create_inventory_lot_returns_none_for_unknown_ingredient(
    db_session,
):
    result = create_inventory_lot(
        db=db_session,
        ingredient_id=999999,
        quantity=1.0,
        purchase_date=date(
            2026,
            8,
            13,
        ),
        expiration_date=None,
    )

    assert result is None


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.5,
    ],
)
def test_create_inventory_lot_rejects_non_positive_quantity(
    db_session,
    quantity,
):
    with pytest.raises(
        ValueError,
        match="在庫数量は0より大きい値",
    ):
        create_inventory_lot(
            db=db_session,
            ingredient_id=1,
            quantity=quantity,
            purchase_date=date(
                2026,
                8,
                13,
            ),
            expiration_date=None,
        )


def test_increment_latest_inventory_lot(
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
                    10,
                ),
            },
            {
                "quantity": 3.0,
                "purchase_date": date(
                    2026,
                    8,
                    10,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    20,
                ),
            },
        ],
    )

    lot_by_purchase_date = {
        inventory.purchase_date: inventory.id
        for inventory in ingredient.inventories
    }

    result = increment_latest_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None

    db_session.expire_all()

    older_lot = db_session.get(
        Inventory,
        lot_by_purchase_date[
            date(2026, 8, 1)
        ],
    )

    latest_lot = db_session.get(
        Inventory,
        lot_by_purchase_date[
            date(2026, 8, 10)
        ],
    )

    assert older_lot is not None
    assert latest_lot is not None

    assert older_lot.quantity == pytest.approx(
        2.0
    )
    assert latest_lot.quantity == pytest.approx(
        3.5
    )


def test_increment_ignores_empty_latest_lot(
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
                "quantity": 0,
                "purchase_date": date(
                    2026,
                    8,
                    10,
                ),
                "expiration_date": None,
            },
        ],
    )

    lot_by_purchase_date = {
        inventory.purchase_date: inventory.id
        for inventory in ingredient.inventories
    }

    result = increment_latest_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None

    db_session.expire_all()

    active_lot = db_session.get(
        Inventory,
        lot_by_purchase_date[
            date(2026, 8, 1)
        ],
    )

    empty_lot = db_session.get(
        Inventory,
        lot_by_purchase_date[
            date(2026, 8, 10)
        ],
    )

    assert active_lot is not None
    assert empty_lot is not None

    assert active_lot.quantity == pytest.approx(
        2.5
    )
    assert empty_lot.quantity == pytest.approx(
        0
    )


def test_increment_returns_none_without_active_lot(
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
                    10,
                ),
                "expiration_date": None,
            },
        ],
    )

    result = increment_latest_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is None


def test_latest_lot_uses_larger_id_when_purchase_dates_are_same(
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
                    10,
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
                    10,
                ),
                "expiration_date": date(
                    2026,
                    8,
                    25,
                ),
            },
        ],
    )

    expected_inventory_id = max(
        inventory.id
        for inventory in ingredient.inventories
    )

    result = get_latest_active_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert result is not None
    assert result.id == expected_inventory_id