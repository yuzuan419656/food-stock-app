from datetime import date

import pytest

from app.crud.inventory import (
    consume_inventory_quantity,
    consume_inventory_quantity_without_commit,
    create_inventory_lot,
    get_inventory_expiration_date,
    get_inventory_purchase_date,
    get_inventory_quantity,
    get_latest_active_inventory_lot,
    increment_latest_inventory_lot,
    get_nearest_expiration_inventory_lot,
    get_oldest_active_inventory_lot,
    update_inventory_expiration_date,
    update_inventory_purchase_date,
    soft_delete_inventory_lot,
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


def test_consume_without_commit_can_be_rolled_back(
    db_session,
):
    ingredient = create_ingredient_with_lots(
        db_session=db_session,
        lots=[
            {
                "quantity": 2.0,
                "purchase_date": date(2026, 8, 1),
                "expiration_date": date(2026, 8, 10),
            },
        ],
    )
    inventory_id = ingredient.inventories[0].id

    result = consume_inventory_quantity_without_commit(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=1.0,
    )

    assert result is not None
    assert result.consumed_quantity == 1.0

    db_session.rollback()
    inventory = db_session.get(Inventory, inventory_id)

    assert inventory is not None
    assert inventory.quantity == 2.0


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


def test_update_purchase_date_updates_oldest_active_lot(
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

    result = update_inventory_purchase_date(
        db=db_session,
        ingredient_id=ingredient.id,
        purchase_date=date(
            2026,
            8,
            5,
        ),
    )

    assert result is not None

    db_session.expire_all()

    oldest_lot = db_session.get(
        Inventory,
        lot_by_purchase_date[
            date(2026, 8, 1)
        ],
    )

    newer_lot = db_session.get(
        Inventory,
        lot_by_purchase_date[
            date(2026, 8, 10)
        ],
    )

    assert oldest_lot is not None
    assert newer_lot is not None

    assert oldest_lot.purchase_date == date(
        2026,
        8,
        5,
    )

    assert newer_lot.purchase_date == date(
        2026,
        8,
        10,
    )


def test_update_expiration_date_updates_nearest_lot(
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
                    15,
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

    lot_by_expiration_date = {
        inventory.expiration_date: inventory.id
        for inventory in ingredient.inventories
    }

    result = update_inventory_expiration_date(
        db=db_session,
        ingredient_id=ingredient.id,
        expiration_date=date(
            2026,
            8,
            25,
        ),
    )

    assert result is not None

    db_session.expire_all()

    updated_lot = db_session.get(
        Inventory,
        lot_by_expiration_date[
            date(2026, 8, 15)
        ],
    )

    untouched_lot = db_session.get(
        Inventory,
        lot_by_expiration_date[
            date(2026, 8, 20)
        ],
    )

    assert updated_lot is not None
    assert untouched_lot is not None

    assert updated_lot.expiration_date == date(
        2026,
        8,
        25,
    )

    assert untouched_lot.expiration_date == date(
        2026,
        8,
        20,
    )


def test_update_expiration_uses_oldest_lot_when_all_dates_unset(
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
                "expiration_date": None,
            },
        ],
    )

    oldest_lot_id = min(
        ingredient.inventories,
        key=lambda inventory: (
            inventory.purchase_date,
            inventory.id,
        ),
    ).id

    result = update_inventory_expiration_date(
        db=db_session,
        ingredient_id=ingredient.id,
        expiration_date=date(
            2026,
            8,
            15,
        ),
    )

    assert result is not None

    db_session.expire_all()

    oldest_lot = db_session.get(
        Inventory,
        oldest_lot_id,
    )

    assert oldest_lot is not None
    assert oldest_lot.expiration_date == date(
        2026,
        8,
        15,
    )


def test_representative_date_update_ignores_empty_lots(
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
                "expiration_date": date(
                    2026,
                    7,
                    10,
                ),
            },
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

    result = get_oldest_active_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert result is not None
    assert result.quantity == pytest.approx(2.0)
    assert result.purchase_date == date(
        2026,
        8,
        1,
    )


def test_soft_deleted_lot_is_excluded_from_total_quantity(
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

    first_lot_id = min(
        inventory.id
        for inventory in ingredient.inventories
    )

    deleted_inventory = (
        soft_delete_inventory_lot(
            db=db_session,
            inventory_id=first_lot_id,
        )
    )

    assert deleted_inventory is not None
    assert (
        deleted_inventory.deleted_at
        is not None
    )

    db_session.expire_all()

    updated_ingredient = (
        db_session.get(
            Ingredient,
            ingredient.id,
        )
    )

    assert updated_ingredient is not None

    assert get_inventory_quantity(
        updated_ingredient
    ) == pytest.approx(3.0)


def test_consumption_ignores_soft_deleted_lot(
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

    lot_by_expiration = {
        inventory.expiration_date:
            inventory.id
        for inventory
        in ingredient.inventories
    }

    deleted_lot_id = lot_by_expiration[
        date(2026, 8, 10)
    ]

    soft_delete_inventory_lot(
        db=db_session,
        inventory_id=deleted_lot_id,
    )

    result = consume_inventory_quantity(
        db=db_session,
        ingredient_id=ingredient.id,
        amount=0.5,
    )

    assert result is not None

    db_session.expire_all()

    deleted_lot = db_session.get(
        Inventory,
        deleted_lot_id,
    )

    active_lot = db_session.get(
        Inventory,
        lot_by_expiration[
            date(2026, 8, 15)
        ],
    )

    assert deleted_lot is not None
    assert active_lot is not None

    assert deleted_lot.quantity == pytest.approx(
        2.0
    )

    assert active_lot.quantity == pytest.approx(
        2.5
    )
