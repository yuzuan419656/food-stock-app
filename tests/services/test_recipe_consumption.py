from datetime import date, datetime

import pytest

from app.models.cooking_history import CookingHistory
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import (
    RecipeIngredient,
)
from app.models.recipe_step import RecipeStep
from app.services import recipe_consumption
from app.services.recipe_consumption import (
    build_recipe_consumption_plan,
    consume_recipe_inventory,
)


def _lot(
    quantity: float,
    *,
    expiration_date: date | None = date(
        2026, 9, 20
    ),
    deleted: bool = False,
) -> Inventory:
    return Inventory(
        quantity=quantity,
        purchase_date=date(2026, 9, 1),
        expiration_date=expiration_date,
        deleted_at=(
            datetime(2026, 9, 2)
            if deleted
            else None
        ),
    )


def _ingredient_item(
    name: str,
    *,
    quantity: float | None = 2,
    quantity_text: str | None = None,
    recipe_unit: str | None = "個",
    inventory_unit: str | None = "個",
    lots: list[Inventory] | None = None,
    is_seasoning: bool = False,
    is_inventory_consumed: bool = True,
    display_order: int = 1,
) -> RecipeIngredient:
    ingredient = Ingredient(
        name=name,
        category="野菜",
        default_unit=inventory_unit,
        inventories=lots or [],
    )
    return RecipeIngredient(
        ingredient=ingredient,
        quantity=quantity,
        quantity_text=quantity_text,
        unit=recipe_unit,
        is_seasoning=is_seasoning,
        is_inventory_consumed=(
            is_inventory_consumed
        ),
        display_order=display_order,
    )


def _recipe(
    db_session,
    items: list[RecipeIngredient],
    *,
    yield_type: str = "servings",
    base_servings: int | None = 2,
) -> Recipe:
    recipe = Recipe(
        name="調理テスト",
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type=yield_type,
        base_servings=base_servings,
        fixed_yield_text=(
            "4個"
            if yield_type == "fixed"
            else None
        ),
        ingredients=items,
        steps=[
            RecipeStep(
                step_number=1,
                description="調理する。",
            )
        ],
    )
    db_session.add(recipe)
    db_session.commit()
    return recipe


def test_plan_reuses_inventory_status_for_sufficient_stock(
    db_session,
):
    recipe = _recipe(
        db_session,
        [_ingredient_item("じゃがいも", lots=[_lot(3)])],
    )

    plan = build_recipe_consumption_plan(recipe)

    assert plan[0].inventory_status.status == "sufficient"
    assert plan[0].planned_consumption_quantity == 2


def test_consumes_available_stock_and_reports_shortage(
    db_session,
):
    item = _ingredient_item("牛乳", lots=[_lot(1)])
    recipe = _recipe(db_session, [item])

    result = consume_recipe_inventory(db_session, recipe)

    assert result.has_shortage
    assert result.inventory_results[0].consumed_quantity == 1
    assert result.inventory_results[0].shortage_quantity == 1
    assert item.ingredient.inventories[0].quantity == 0
    history_item = result.cooking_history.ingredients[0]
    assert history_item.required_quantity == 2
    assert history_item.consumed_quantity == 1
    assert history_item.shortage_quantity == 1
    assert history_item.unit == "個"


def test_zero_stock_is_not_decreased(
    db_session,
):
    item = _ingredient_item("たまねぎ", lots=[])
    recipe = _recipe(db_session, [item])

    result = consume_recipe_inventory(db_session, recipe)

    assert result.inventory_results[0].consumed_quantity == 0
    assert result.inventory_results[0].shortage_quantity == 2
    assert result.cooking_history.ingredients[0].consumed_quantity == 0
    assert result.cooking_history.ingredients[0].shortage_quantity == 2


def test_consumes_multiple_lots_in_expiration_order(
    db_session,
):
    no_expiration = _lot(2, expiration_date=None)
    later = _lot(
        1,
        expiration_date=date(2026, 9, 20),
    )
    earlier = _lot(
        1,
        expiration_date=date(2026, 9, 10),
    )
    deleted = _lot(
        10,
        expiration_date=date(2026, 9, 5),
        deleted=True,
    )
    item = _ingredient_item(
        "にんじん",
        quantity=2.5,
        lots=[no_expiration, later, earlier, deleted],
    )
    recipe = _recipe(db_session, [item])

    result = consume_recipe_inventory(db_session, recipe)

    assert earlier.quantity == 0
    assert later.quantity == 0
    assert no_expiration.quantity == pytest.approx(1.5)
    assert deleted.quantity == 10
    allocations = (
        result.cooking_history.ingredients[0]
        .inventory_consumptions
    )
    assert [item.inventory_id for item in allocations] == [
        earlier.id,
        later.id,
        no_expiration.id,
    ]
    assert [item.consumed_quantity for item in allocations] == [
        1,
        1,
        0.5,
    ]


def test_consumption_uses_scaled_servings(
    db_session,
):
    item = _ingredient_item("肉", lots=[_lot(5)])
    recipe = _recipe(db_session, [item])

    result = consume_recipe_inventory(
        db_session,
        recipe,
        target_servings=4,
    )

    assert item.ingredient.inventories[0].quantity == 1
    assert result.cooking_history.servings == 4
    assert result.cooking_history.ingredients[0].required_quantity == 4


def test_fixed_yield_uses_registered_quantity(
    db_session,
):
    item = _ingredient_item("卵", lots=[_lot(3)])
    recipe = _recipe(
        db_session,
        [item],
        yield_type="fixed",
        base_servings=None,
    )

    result = consume_recipe_inventory(db_session, recipe)

    assert item.ingredient.inventories[0].quantity == 1
    assert result.cooking_history.servings is None
    assert result.cooking_history.fixed_yield_text == "4個"


def test_non_automatic_items_are_not_consumed(
    db_session,
):
    mismatch = _ingredient_item(
        "単位不一致",
        recipe_unit="g",
        inventory_unit="個",
        lots=[_lot(3)],
    )
    seasoning = _ingredient_item(
        "調味料",
        lots=[_lot(3)],
        is_seasoning=True,
        is_inventory_consumed=False,
        display_order=2,
    )
    not_consumed = _ingredient_item(
        "減算対象外",
        lots=[_lot(3)],
        is_inventory_consumed=False,
        display_order=3,
    )
    text_quantity = _ingredient_item(
        "適量材料",
        quantity=None,
        quantity_text="適量",
        recipe_unit=None,
        lots=[_lot(3)],
        is_inventory_consumed=False,
        display_order=4,
    )
    recipe = _recipe(
        db_session,
        [mismatch, seasoning, not_consumed, text_quantity],
    )

    result = consume_recipe_inventory(db_session, recipe)

    assert result.inventory_results == ()
    assert len(result.cooking_history.ingredients) == 4
    assert {
        item.status
        for item in result.cooking_history.ingredients
    } == {"unit_mismatch", "not_applicable"}
    assert all(
        item.consumed_quantity == 0
        for item in result.cooking_history.ingredients
    )
    for item in recipe.ingredients:
        assert item.ingredient.inventories[0].quantity == 3


def test_multiple_ingredients_are_consumed(
    db_session,
):
    first = _ingredient_item("材料A", lots=[_lot(3)])
    second = _ingredient_item(
        "材料B",
        quantity=1,
        lots=[_lot(2)],
        display_order=2,
    )
    recipe = _recipe(db_session, [first, second])

    result = consume_recipe_inventory(db_session, recipe)

    assert len(result.inventory_results) == 2
    assert first.ingredient.inventories[0].quantity == 1
    assert second.ingredient.inventories[0].quantity == 1


def test_all_ingredients_are_committed_once(
    db_session,
    monkeypatch,
):
    recipe = _recipe(
        db_session,
        [
            _ingredient_item("材料A", lots=[_lot(3)]),
            _ingredient_item(
                "材料B",
                lots=[_lot(3)],
                display_order=2,
            ),
        ],
    )
    original_commit = db_session.commit
    commit_count = 0

    def count_commit():
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(db_session, "commit", count_commit)

    consume_recipe_inventory(db_session, recipe)

    assert commit_count == 1
    assert db_session.query(CookingHistory).count() == 1


def test_exception_rolls_back_all_ingredients(
    db_session,
    monkeypatch,
):
    first = _ingredient_item("材料A", lots=[_lot(3)])
    second = _ingredient_item(
        "材料B",
        lots=[_lot(3)],
        display_order=2,
    )
    recipe = _recipe(db_session, [first, second])
    original_consume = (
        recipe_consumption
        .consume_inventory_quantity_without_commit
    )
    call_count = 0

    def fail_on_second_call(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("テスト用例外")
        return original_consume(**kwargs)

    monkeypatch.setattr(
        recipe_consumption,
        "consume_inventory_quantity_without_commit",
        fail_on_second_call,
    )

    with pytest.raises(RuntimeError, match="テスト用例外"):
        consume_recipe_inventory(db_session, recipe)

    db_session.expire_all()
    assert first.ingredient.inventories[0].quantity == 3
    assert second.ingredient.inventories[0].quantity == 3
    assert db_session.query(CookingHistory).count() == 0


def test_history_failure_rolls_back_inventory(
    db_session,
    monkeypatch,
):
    item = _ingredient_item("材料A", lots=[_lot(3)])
    recipe = _recipe(db_session, [item])

    def fail_history(**_kwargs):
        raise RuntimeError("履歴保存失敗")

    monkeypatch.setattr(
        recipe_consumption,
        "add_cooking_history",
        fail_history,
    )

    with pytest.raises(RuntimeError, match="履歴保存失敗"):
        consume_recipe_inventory(db_session, recipe)

    db_session.expire_all()
    assert item.ingredient.inventories[0].quantity == 3
    assert db_session.query(CookingHistory).count() == 0
