from datetime import date, datetime

import pytest

from app.models.cooking_history import CookingHistory
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from app.services import cooking_undo
from app.services.cooking_undo import (
    CookingUndoInventoryUnavailableError,
    CookingUndoNotAllowedError,
    build_cooking_undo_plan,
    undo_latest_cooking,
)
from app.services.recipe_consumption import consume_recipe_inventory


def _lot(quantity, expiration, deleted_at=None):
    return Inventory(
        quantity=quantity,
        purchase_date=date(2026, 9, 1),
        expiration_date=expiration,
        deleted_at=deleted_at,
    )


def _recipe(db_session, lot_groups):
    items = []
    for index, lots in enumerate(lot_groups, start=1):
        ingredient = Ingredient(
            name=f"材料{index}",
            category="野菜",
            default_unit="個",
            inventories=lots,
        )
        items.append(
            RecipeIngredient(
                ingredient=ingredient,
                quantity=2,
                unit="個",
                is_inventory_consumed=True,
                display_order=index,
            )
        )

    recipe = Recipe(
        name="取り消しテスト",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        ingredients=items,
        steps=[RecipeStep(step_number=1, description="調理")],
    )
    db_session.add(recipe)
    db_session.commit()
    return recipe


def _cook(db_session, recipe):
    return consume_recipe_inventory(
        db=db_session,
        recipe=recipe,
        target_servings=2,
    ).cooking_history


def test_undo_restores_single_lot_and_sets_undone_at(
    db_session,
):
    lot = _lot(3, date(2026, 9, 10))
    history = _cook(db_session, _recipe(db_session, [[lot]]))
    undo_time = datetime(2026, 9, 4, 20, 0)

    result = undo_latest_cooking(
        db_session, history.id, undone_at=undo_time
    )

    assert result.undone_at == undo_time
    assert lot.quantity == 3


def test_undo_restores_multiple_original_lots(
    db_session,
):
    first = _lot(1, date(2026, 9, 10))
    second = _lot(2, date(2026, 9, 20))
    history = _cook(
        db_session, _recipe(db_session, [[first, second]])
    )
    allocation_ids = {
        item.inventory_id
        for item in history.ingredients[0].inventory_consumptions
    }

    undo_latest_cooking(db_session, history.id)

    assert allocation_ids == {first.id, second.id}
    assert first.quantity == 1
    assert second.quantity == 2


def test_undo_restores_multiple_ingredients(
    db_session,
):
    first = _lot(3, date(2026, 9, 10))
    second = _lot(4, date(2026, 9, 10))
    history = _cook(
        db_session,
        _recipe(db_session, [[first], [second]]),
    )

    undo_latest_cooking(db_session, history.id)

    assert first.quantity == 3
    assert second.quantity == 4


def test_undo_restores_only_partially_consumed_quantity(
    db_session,
):
    lot = _lot(1, date(2026, 9, 10))
    history = _cook(db_session, _recipe(db_session, [[lot]]))

    undo_latest_cooking(db_session, history.id)

    assert lot.quantity == 1


def test_undo_with_zero_stock_marks_history_without_new_lot(
    db_session,
):
    recipe = _recipe(db_session, [[]])
    history = _cook(db_session, recipe)

    undo_latest_cooking(db_session, history.id)

    assert history.undone_at is not None
    assert recipe.ingredients[0].ingredient.inventories == []


def test_undo_plan_shows_restored_quantity(
    db_session,
):
    lot = _lot(3, date(2026, 9, 10))
    history = _cook(db_session, _recipe(db_session, [[lot]]))

    _, plan = build_cooking_undo_plan(db_session, history.id)

    assert len(plan) == 1
    assert plan[0].ingredient_name == "材料1"
    assert plan[0].restore_quantity == 2


def test_same_history_cannot_be_undone_twice(
    db_session,
):
    lot = _lot(3, date(2026, 9, 10))
    history = _cook(db_session, _recipe(db_session, [[lot]]))
    undo_latest_cooking(db_session, history.id)

    with pytest.raises(CookingUndoNotAllowedError):
        undo_latest_cooking(db_session, history.id)

    assert lot.quantity == 3


def test_non_latest_history_cannot_be_undone(
    db_session,
):
    lot = _lot(5, date(2026, 9, 10))
    recipe = _recipe(db_session, [[lot]])
    first = _cook(db_session, recipe)
    _cook(db_session, recipe)

    with pytest.raises(CookingUndoNotAllowedError):
        undo_latest_cooking(db_session, first.id)

    assert lot.quantity == 1


def test_previous_history_does_not_become_undoable(
    db_session,
):
    lot = _lot(5, date(2026, 9, 10))
    recipe = _recipe(db_session, [[lot]])
    first = _cook(db_session, recipe)
    latest = _cook(db_session, recipe)
    undo_latest_cooking(db_session, latest.id)

    with pytest.raises(CookingUndoNotAllowedError):
        undo_latest_cooking(db_session, first.id)

    assert lot.quantity == 3


def test_deleted_inventory_prevents_entire_undo(
    db_session,
):
    first = _lot(3, date(2026, 9, 10))
    second = _lot(3, date(2026, 9, 10))
    history = _cook(
        db_session,
        _recipe(db_session, [[first], [second]]),
    )
    first.deleted_at = datetime.now()
    db_session.commit()

    with pytest.raises(CookingUndoInventoryUnavailableError):
        undo_latest_cooking(db_session, history.id)

    assert second.quantity == 1
    assert history.undone_at is None


def test_restore_exception_rolls_back_all_lots(
    db_session,
    monkeypatch,
):
    first = _lot(3, date(2026, 9, 10))
    second = _lot(3, date(2026, 9, 10))
    history = _cook(
        db_session,
        _recipe(db_session, [[first], [second]]),
    )
    original_restore = (
        cooking_undo.restore_inventory_lot_quantity_without_commit
    )
    calls = 0

    def fail_second(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("復元失敗")
        return original_restore(**kwargs)

    monkeypatch.setattr(
        cooking_undo,
        "restore_inventory_lot_quantity_without_commit",
        fail_second,
    )

    with pytest.raises(RuntimeError, match="復元失敗"):
        undo_latest_cooking(db_session, history.id)

    db_session.expire_all()
    assert first.quantity == 1
    assert second.quantity == 1
    assert history.undone_at is None


def test_commit_failure_rolls_back_inventory_and_history(
    db_session,
    monkeypatch,
):
    lot = _lot(3, date(2026, 9, 10))
    history = _cook(db_session, _recipe(db_session, [[lot]]))

    def fail_commit():
        raise RuntimeError("履歴更新失敗")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="履歴更新失敗"):
        undo_latest_cooking(db_session, history.id)

    db_session.expire_all()
    assert lot.quantity == 1
    assert history.undone_at is None


def test_undo_commits_once(
    db_session,
    monkeypatch,
):
    lot = _lot(3, date(2026, 9, 10))
    history = _cook(db_session, _recipe(db_session, [[lot]]))
    original_commit = db_session.commit
    commit_count = 0

    def count_commit():
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(db_session, "commit", count_commit)

    undo_latest_cooking(db_session, history.id)

    assert commit_count == 1
