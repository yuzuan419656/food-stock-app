from datetime import date

from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    delete_ingredient,
    get_ingredient_by_id,
    get_ingredient_by_name,
    get_ingredients,
    restore_ingredient,
    search_ingredients,
)
from app.crud.inventory import (
    get_inventory_lot_by_id,
    get_inventory_quantity,
    soft_delete_inventory_lot,
    update_inventory_lot,
)
from app.models.inventory import Inventory
from app.crud.shopping_item import (
    add_ingredients_to_shopping_list,
    get_shopping_ingredient_candidates,
    get_shopping_items,
)


def create_test_ingredient(
    db_session: Session,
    name: str = "キャベツ",
):
    return create_ingredient(
        db=db_session,
        name=name,
        category="野菜",
        default_unit="玉",
        quantity=2,
        purchase_date=date(
            2026,
            8,
            20,
        ),
        expiration_date=date(
            2026,
            8,
            27,
        ),
    )


def test_delete_ingredient_marks_it_inactive(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
    )

    result = delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert result is True

    deleted_ingredient = (
        get_ingredient_by_id(
            db=db_session,
            ingredient_id=ingredient.id,
            include_inactive=True,
        )
    )

    assert deleted_ingredient is not None
    assert deleted_ingredient.is_active is False
    assert (
        deleted_ingredient.deleted_at
        is not None
    )


def test_deleted_ingredient_is_excluded_from_normal_get(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    result = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert result is None


def test_delete_ingredient_keeps_inventory_lots(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
    )

    ingredient_id = ingredient.id

    inventory_count_before = (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient_id
        )
        .count()
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient_id,
    )

    inventory_count_after = (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient_id
        )
        .count()
    )

    assert inventory_count_before == 1
    assert inventory_count_after == 1


def test_deleted_ingredient_is_excluded_from_list(
    db_session: Session,
):
    active_ingredient = (
        create_test_ingredient(
            db_session=db_session,
            name="にんじん",
        )
    )

    deleted_ingredient = (
        create_test_ingredient(
            db_session=db_session,
            name="キャベツ",
        )
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=(
            deleted_ingredient.id
        ),
    )

    results = get_ingredients(
        db=db_session
    )

    result_ids = {
        ingredient.id
        for ingredient in results
    }

    assert (
        active_ingredient.id
        in result_ids
    )

    assert (
        deleted_ingredient.id
        not in result_ids
    )


def test_deleted_ingredient_is_excluded_from_search(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    results = search_ingredients(
        db=db_session,
        keyword="キャベツ",
    )

    assert results == []


def test_get_ingredient_by_name_can_include_inactive(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    normal_result = (
        get_ingredient_by_name(
            db=db_session,
            name="キャベツ",
        )
    )

    inactive_result = (
        get_ingredient_by_name(
            db=db_session,
            name="キャベツ",
            include_inactive=True,
        )
    )

    assert normal_result is None
    assert inactive_result is not None
    assert inactive_result.id == ingredient.id
    assert inactive_result.is_active is False

def test_deleted_ingredient_is_excluded_from_shopping_candidates(
    db_session: Session,
):
    active_ingredient = create_test_ingredient(
        db_session=db_session,
        name="にんじん",
    )

    deleted_ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=deleted_ingredient.id,
    )

    results = (
        get_shopping_ingredient_candidates(
            db=db_session,
        )
    )

    result_ids = {
        ingredient.id
        for ingredient in results
    }

    assert active_ingredient.id in result_ids
    assert deleted_ingredient.id not in result_ids

def test_deleted_ingredient_cannot_be_added_to_shopping_list(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    added_count = (
        add_ingredients_to_shopping_list(
            db=db_session,
            ingredient_ids=[
                ingredient.id,
            ],
        )
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert added_count == 0
    assert shopping_items == []


def test_existing_shopping_item_is_kept_after_ingredient_deletion(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    added_count = (
        add_ingredients_to_shopping_list(
            db=db_session,
            ingredient_ids=[
                ingredient.id,
            ],
        )
    )

    assert added_count == 1

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert len(shopping_items) == 1
    assert (
        shopping_items[0].ingredient_id
        == ingredient.id
    )
    assert (
        shopping_items[0].ingredient
        is not None
    )
    assert (
        shopping_items[0]
        .ingredient
        .is_active
        is False
    )


def test_inventory_lot_of_deleted_ingredient_is_not_returned(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    inventory_id = (
        ingredient.inventories[0].id
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    normal_result = (
        get_inventory_lot_by_id(
            db=db_session,
            inventory_id=inventory_id,
        )
    )

    history_result = (
        get_inventory_lot_by_id(
            db=db_session,
            inventory_id=inventory_id,
            include_inactive_ingredient=True,
        )
    )

    assert normal_result is None
    assert history_result is not None
    assert history_result.id == inventory_id


def test_inventory_lot_of_deleted_ingredient_cannot_be_updated(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    inventory = ingredient.inventories[0]
    inventory_id = inventory.id
    original_quantity = float(
        inventory.quantity
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    result = update_inventory_lot(
        db=db_session,
        inventory_id=inventory_id,
        quantity=10,
        purchase_date=date(
            2026,
            8,
            20,
        ),
        expiration_date=date(
            2026,
            8,
            30,
        ),
    )

    history_inventory = (
        get_inventory_lot_by_id(
            db=db_session,
            inventory_id=inventory_id,
            include_inactive_ingredient=True,
        )
    )

    assert result is None
    assert history_inventory is not None
    assert (
        float(history_inventory.quantity)
        == original_quantity
    )


def test_inventory_lot_of_deleted_ingredient_cannot_be_deleted(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    inventory_id = (
        ingredient.inventories[0].id
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    result = soft_delete_inventory_lot(
        db=db_session,
        inventory_id=inventory_id,
    )

    history_inventory = (
        get_inventory_lot_by_id(
            db=db_session,
            inventory_id=inventory_id,
            include_inactive_ingredient=True,
        )
    )

    assert result is None
    assert history_inventory is not None
    assert (
        history_inventory.deleted_at
        is None
    )


def test_restore_ingredient_reactivates_same_record(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    ingredient_id = ingredient.id

    original_inventory_ids = {
        inventory.id
        for inventory
        in ingredient.inventories
    }

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient_id,
    )

    restored_ingredient = (
        restore_ingredient(
            db=db_session,
            ingredient_id=ingredient_id,
            category="葉物野菜",
            default_unit="玉",
            quantity=1,
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
    )

    assert restored_ingredient is not None
    assert restored_ingredient.id == ingredient_id
    assert restored_ingredient.is_active is True
    assert restored_ingredient.deleted_at is None
    assert (
        restored_ingredient.category
        == "葉物野菜"
    )

    restored_inventory_ids = {
        inventory.id
        for inventory
        in restored_ingredient.inventories
    }

    assert original_inventory_ids.issubset(
        restored_inventory_ids
    )

    assert (
        len(restored_inventory_ids)
        == len(original_inventory_ids) + 1
    )

    assert (
        get_inventory_quantity(
            restored_ingredient
        )
        == 3
    )


def test_restore_ingredient_with_zero_quantity_keeps_existing_lots_only(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    original_inventory_ids = {
        inventory.id
        for inventory
        in ingredient.inventories
    }

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    restored_ingredient = (
        restore_ingredient(
            db=db_session,
            ingredient_id=ingredient.id,
            category="野菜",
            default_unit="玉",
            quantity=0,
            purchase_date=date(
                2026,
                8,
                20,
            ),
            expiration_date=None,
        )
    )

    assert restored_ingredient is not None

    restored_inventory_ids = {
        inventory.id
        for inventory
        in restored_ingredient.inventories
    }

    assert (
        restored_inventory_ids
        == original_inventory_ids
    )


def test_restore_ingredient_rejects_different_unit(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    delete_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    try:
        restore_ingredient(
            db=db_session,
            ingredient_id=ingredient.id,
            category="野菜",
            default_unit="個",
            quantity=1,
            purchase_date=date(
                2026,
                8,
                20,
            ),
            expiration_date=None,
        )

    except ValueError as error:
        assert (
            "単位が異なるため"
            in str(error)
        )

    else:
        raise AssertionError(
            "ValueErrorが発生しませんでした。"
        )

    inactive_ingredient = (
        get_ingredient_by_id(
            db=db_session,
            ingredient_id=ingredient.id,
            include_inactive=True,
        )
    )

    assert inactive_ingredient is not None
    assert inactive_ingredient.is_active is False
    assert (
        inactive_ingredient.deleted_at
        is not None
    )


def test_restore_ingredient_returns_none_for_active_ingredient(
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
    )

    result = restore_ingredient(
        db=db_session,
        ingredient_id=ingredient.id,
        category="野菜",
        default_unit="玉",
        quantity=1,
        purchase_date=date(
            2026,
            8,
            20,
        ),
        expiration_date=None,
    )

    assert result is None