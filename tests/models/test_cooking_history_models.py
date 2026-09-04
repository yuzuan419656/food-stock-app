from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.cooking_history import CookingHistory
from app.models.cooking_history_ingredient import (
    CookingHistoryIngredient,
)
from app.models.cooking_history_inventory_consumption import (
    CookingHistoryInventoryConsumption,
)
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe


def _masters(db_session):
    recipe = Recipe(
        name="肉じゃが",
        cooking_time_minutes=30,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
    )
    ingredient = Ingredient(
        name="じゃがいも",
        category="野菜",
        default_unit="個",
    )
    inventory = Inventory(
        ingredient=ingredient,
        quantity=3,
        purchase_date=date(2026, 9, 1),
    )
    db_session.add_all([recipe, ingredient, inventory])
    db_session.commit()
    return recipe, ingredient, inventory


def test_create_cooking_history_with_relationships(
    db_session,
):
    recipe, ingredient, inventory = _masters(db_session)
    history = CookingHistory(
        recipe=recipe,
        recipe_name="肉じゃが",
        cooked_at=datetime(2026, 9, 4, 18, 30),
        yield_type="servings",
        servings=2,
        ingredients=[
            CookingHistoryIngredient(
                ingredient=ingredient,
                ingredient_name="じゃがいも",
                required_quantity=2,
                consumed_quantity=2,
                shortage_quantity=0,
                unit="個",
                inventory_consumed=True,
                status="sufficient",
                inventory_consumptions=[
                    CookingHistoryInventoryConsumption(
                        inventory=inventory,
                        consumed_quantity=2,
                    )
                ],
            )
        ],
    )

    db_session.add(history)
    db_session.commit()

    assert history.id is not None
    assert history.undone_at is None
    assert history.recipe is recipe
    assert len(history.ingredients) == 1
    assert len(history.ingredients[0].inventory_consumptions) == 1
    assert (
        history.ingredients[0]
        .inventory_consumptions[0].inventory_id
        == inventory.id
    )

    undone_at = datetime(2026, 9, 4, 19, 0)
    history.undone_at = undone_at
    db_session.commit()
    db_session.refresh(history)
    assert history.undone_at == undone_at


def test_cooking_history_rejects_missing_required_value(
    db_session,
):
    recipe, _, _ = _masters(db_session)
    history = CookingHistory(
        recipe_id=recipe.id,
        recipe_name=None,
        cooked_at=datetime.now(),
        yield_type="servings",
        servings=2,
    )
    db_session.add(history)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    ("required", "consumed", "shortage"),
    [
        (0, 0, 0),
        (1, -0.5, 0),
        (1, 0, -0.5),
    ],
)
def test_cooking_history_ingredient_rejects_invalid_quantity(
    db_session,
    required,
    consumed,
    shortage,
):
    recipe, ingredient, _ = _masters(db_session)
    history = CookingHistory(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        cooked_at=datetime.now(),
        yield_type="servings",
        servings=2,
        ingredients=[
            CookingHistoryIngredient(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                required_quantity=required,
                consumed_quantity=consumed,
                shortage_quantity=shortage,
                unit="個",
                inventory_consumed=True,
                status="shortage",
            )
        ],
    )
    db_session.add(history)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_lot_consumption_rejects_non_positive_quantity(
    db_session,
):
    recipe, ingredient, inventory = _masters(db_session)
    history = CookingHistory(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        cooked_at=datetime.now(),
        yield_type="servings",
        servings=2,
        ingredients=[
            CookingHistoryIngredient(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                required_quantity=1,
                consumed_quantity=0,
                shortage_quantity=1,
                unit="個",
                inventory_consumed=True,
                status="shortage",
                inventory_consumptions=[
                    CookingHistoryInventoryConsumption(
                        inventory_id=inventory.id,
                        consumed_quantity=0,
                    )
                ],
            )
        ],
    )
    db_session.add(history)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
