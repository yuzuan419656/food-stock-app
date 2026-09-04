from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cooking_history import CookingHistory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from scripts.rollback_seed_recipes import rollback_seed_recipes
from scripts.seed_recipes import seed_recipes


def _existing_recipe() -> Recipe:
    return Recipe(
        name="既存ユーザーレシピ",
        cooking_time_minutes=15,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
    )


def test_rollback_seed_preserves_existing_and_is_idempotent(
    db_session: Session,
):
    existing = _existing_recipe()
    inactive = Recipe(
        name="既存inactive",
        cooking_time_minutes=15,
        cuisine_type="和食",
        dish_category="副菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        is_active=False,
        deleted_at=datetime.now(),
    )
    db_session.add_all([existing, inactive])
    db_session.commit()
    seed_recipes(db_session)

    summary = rollback_seed_recipes(db_session)
    assert summary.recipe_count == 179
    assert db_session.get(Recipe, existing.id) is not None
    assert db_session.get(Recipe, inactive.id) is not None
    assert db_session.query(Recipe).filter(Recipe.is_active.is_(True)).count() == 1
    assert db_session.query(RecipeIngredient).count() == 0
    assert db_session.query(RecipeStep).count() == 0

    second = rollback_seed_recipes(db_session)
    assert second.recipe_count == 0


def test_rollback_dry_run_does_not_change_database(db_session: Session):
    existing = _existing_recipe()
    db_session.add(existing)
    db_session.commit()
    seed_recipes(db_session)
    before = db_session.query(Recipe).count()

    summary = rollback_seed_recipes(db_session, dry_run=True)

    assert summary.recipe_count == 179
    assert db_session.query(Recipe).count() == before


def test_rollback_stops_when_history_references_seed_recipe(
    db_session: Session,
):
    seed_recipes(db_session)
    target = (
        db_session.query(Recipe)
        .filter(Recipe.name == "鶏の照り焼き")
        .one()
    )
    db_session.add(
        CookingHistory(
            recipe_id=target.id,
            recipe_name=target.name,
            yield_type="servings",
            servings=2,
            fixed_yield_text=None,
        )
    )
    db_session.commit()

    try:
        rollback_seed_recipes(db_session)
    except RuntimeError as error:
        assert "調理履歴" in str(error)
    else:
        raise AssertionError("履歴参照時にrollbackされました")

    assert db_session.query(Recipe).count() == 180
