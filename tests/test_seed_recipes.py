from collections import Counter

from sqlalchemy.orm import Session

from app.constants.recipe_options import (
    RECIPE_CUISINE_OPTIONS,
    RECIPE_DISH_CATEGORY_OPTIONS,
)
from app.models.recipe import Recipe
from scripts.seed_recipes import seed_recipes


def test_seed_recipes_fills_all_combinations_and_is_idempotent(
    db_session: Session,
):
    first_added = seed_recipes(db_session)
    first_count = db_session.query(Recipe).filter(Recipe.is_active.is_(True)).count()
    second_added = seed_recipes(db_session)
    second_count = db_session.query(Recipe).filter(Recipe.is_active.is_(True)).count()

    assert first_added == 180
    assert second_added == 0
    assert first_count == 36 * 5
    assert second_count == first_count

    counts = Counter(
        (recipe.cuisine_type, recipe.dish_category)
        for recipe in db_session.query(Recipe)
        .filter(Recipe.is_active.is_(True))
        .all()
    )
    assert all(
        counts[(cuisine, category)] >= 5
        for cuisine in RECIPE_CUISINE_OPTIONS
        for category in RECIPE_DISH_CATEGORY_OPTIONS
    )


def test_seed_recipes_has_valid_relations_and_unique_names(
    db_session: Session,
):
    seed_recipes(db_session)
    recipes = db_session.query(Recipe).filter(Recipe.is_active.is_(True)).all()

    assert len({recipe.name for recipe in recipes}) == len(recipes)
    assert all(recipe.ingredients for recipe in recipes)
    assert all(recipe.steps for recipe in recipes)
    assert all(recipe.cooking_time_minutes > 0 for recipe in recipes)
    assert all(
        recipe.yield_type == "fixed"
        or (recipe.base_servings is not None and recipe.base_servings >= 1)
        for recipe in recipes
    )
    assert all(
        item.ingredient is not None
        for recipe in recipes
        for item in recipe.ingredients
    )
