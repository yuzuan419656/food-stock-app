from datetime import datetime

from app.crud.cooking_history import (
    get_latest_cooking_history,
    get_latest_undoable_cooking_history,
    mark_latest_cooking_history_undone,
)
from app.models.cooking_history import CookingHistory
from app.models.recipe import Recipe


def _history(db_session, recipe, cooked_at):
    history = CookingHistory(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        cooked_at=cooked_at,
        yield_type="servings",
        servings=2,
    )
    db_session.add(history)
    db_session.commit()
    return history


def test_latest_undoable_history_is_absolute_latest(
    db_session,
):
    recipe = Recipe(
        name="履歴テスト",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
    )
    db_session.add(recipe)
    db_session.commit()
    first = _history(
        db_session, recipe, datetime(2026, 9, 1)
    )
    latest = _history(
        db_session, recipe, datetime(2026, 9, 2)
    )

    assert get_latest_cooking_history(db_session).id == latest.id
    assert (
        get_latest_undoable_cooking_history(db_session).id
        == latest.id
    )

    assert mark_latest_cooking_history_undone(
        db_session,
        cooking_history_id=latest.id,
        undone_at=datetime(2026, 9, 3),
    )
    db_session.commit()

    assert latest.undone_at is not None
    assert get_latest_undoable_cooking_history(db_session) is None
    assert not mark_latest_cooking_history_undone(
        db_session,
        cooking_history_id=first.id,
        undone_at=datetime(2026, 9, 3),
    )
