from datetime import date

from sqlalchemy.orm import Session

from app.crud.ingredient import create_ingredient
from app.crud.shopping_item import (
    add_ingredients_to_shopping_list,
    delete_purchased_shopping_items,
    get_shopping_items,
    toggle_shopping_item,
)


def test_add_ingredients_to_shopping_list(
    db_session: Session,
):
    milk = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    egg = create_ingredient(
        db=db_session,
        name="卵",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(2026, 8, 6),
    )

    added_count = add_ingredients_to_shopping_list(
        db=db_session,
        ingredient_ids=[milk.id, egg.id],
    )

    assert added_count == 2

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert {
        item.ingredient.name
        for item in shopping_items
    } == {
        "牛乳",
        "卵",
    }


def test_duplicate_ingredient_is_not_added(
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    first_added_count = (
        add_ingredients_to_shopping_list(
            db=db_session,
            ingredient_ids=[ingredient.id],
        )
    )

    second_added_count = (
        add_ingredients_to_shopping_list(
            db=db_session,
            ingredient_ids=[ingredient.id],
        )
    )

    assert first_added_count == 1
    assert second_added_count == 0
    assert len(
        get_shopping_items(db=db_session)
    ) == 1


def test_toggle_shopping_item(
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    add_ingredients_to_shopping_list(
        db=db_session,
        ingredient_ids=[ingredient.id],
    )

    shopping_item = get_shopping_items(
        db=db_session
    )[0]

    assert shopping_item.is_purchased is False

    updated_item = toggle_shopping_item(
        db=db_session,
        shopping_item_id=shopping_item.id,
    )

    assert updated_item is not None
    assert updated_item.is_purchased is True


def test_delete_only_purchased_shopping_items(
    db_session: Session,
):
    milk = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    egg = create_ingredient(
        db=db_session,
        name="卵",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(2026, 8, 6),
    )

    add_ingredients_to_shopping_list(
        db=db_session,
        ingredient_ids=[milk.id, egg.id],
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    purchased_item = next(
        item
        for item in shopping_items
        if item.ingredient.name == "牛乳"
    )

    toggle_shopping_item(
        db=db_session,
        shopping_item_id=purchased_item.id,
    )

    deleted_count = (
        delete_purchased_shopping_items(
            db=db_session
        )
    )

    remaining_items = get_shopping_items(
        db=db_session
    )

    assert deleted_count == 1
    assert len(remaining_items) == 1
    assert (
        remaining_items[0].ingredient.name
        == "卵"
    )
    assert (
        remaining_items[0].is_purchased
        is False
    )