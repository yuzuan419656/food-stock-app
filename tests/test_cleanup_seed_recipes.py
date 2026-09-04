from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cooking_history import CookingHistory
from app.models.cooking_history_ingredient import CookingHistoryIngredient
from app.models.cooking_history_inventory_consumption import (
    CookingHistoryInventoryConsumption,
)
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.shopping_item import ShoppingItem
from scripts.cleanup_seed_recipes import (
    build_cleanup_summary,
    cleanup_seed_recipes,
)
from scripts.seed_recipes import seed_recipes


def test_cleanup_seed_recipes_preserves_existing_data_and_inventory(
    db_session: Session,
):
    existing = Recipe(
        name="既存レシピ",
        cooking_time_minutes=10,
        cuisine_type="既存系統",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        is_favorite=False,
    )
    existing_inactive = Recipe(
        name="既存の削除済みレシピ",
        cooking_time_minutes=10,
        cuisine_type="既存系統",
        dish_category="副菜",
        yield_type="servings",
        base_servings=2,
        is_favorite=False,
        is_active=False,
        deleted_at=datetime.now(),
    )
    db_session.add_all([existing, existing_inactive])
    db_session.commit()

    assert seed_recipes(db_session) == 180
    db_session.commit()
    seed_recipe = (
        db_session.query(Recipe)
        .filter(Recipe.name == "鶏の照り焼き")
        .one()
    )
    recipe_ingredient = seed_recipe.ingredients[0]
    ingredient = recipe_ingredient.ingredient
    inventory = Inventory(ingredient_id=ingredient.id, quantity=7)
    shopping_item = ShoppingItem(ingredient_id=ingredient.id)
    db_session.add_all([inventory, shopping_item])
    db_session.flush()

    existing_history = CookingHistory(
        recipe_id=existing.id,
        recipe_name=existing.name,
        yield_type="servings",
        servings=2,
    )
    seed_history = CookingHistory(
        recipe_id=seed_recipe.id,
        recipe_name=seed_recipe.name,
        yield_type="servings",
        servings=2,
    )
    history_ingredient = CookingHistoryIngredient(
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name,
        required_quantity=1,
        consumed_quantity=1,
        shortage_quantity=0,
        unit=recipe_ingredient.unit,
        inventory_consumed=True,
        status="sufficient",
    )
    history_ingredient.inventory_consumptions.append(
        CookingHistoryInventoryConsumption(
            inventory_id=inventory.id,
            consumed_quantity=1,
        )
    )
    seed_history.ingredients.append(history_ingredient)
    db_session.add_all([existing_history, seed_history])
    db_session.commit()

    dry_run = cleanup_seed_recipes(db_session, dry_run=True)
    assert dry_run.recipe_count == 180
    assert dry_run.cooking_history_count == 1
    assert dry_run.cooking_history_ids == (seed_history.id,)
    assert db_session.query(Recipe).count() == 182
    assert db_session.query(CookingHistory).count() == 2
    assert db_session.get(Inventory, inventory.id).quantity == 7

    cleanup_seed_recipes(db_session)
    assert db_session.get(Recipe, existing.id) is not None
    assert db_session.get(Recipe, existing_inactive.id) is not None
    assert db_session.query(Recipe).filter(Recipe.name == "鶏の照り焼き").count() == 0
    assert db_session.get(CookingHistory, existing_history.id) is not None
    assert db_session.get(CookingHistory, seed_history.id) is None
    assert db_session.get(Inventory, inventory.id).quantity == 7
    assert db_session.get(ShoppingItem, shopping_item.id) is not None
    assert db_session.get(Ingredient, ingredient.id) is not None
    assert db_session.query(CookingHistoryIngredient).count() == 0
    assert db_session.query(CookingHistoryInventoryConsumption).count() == 0

    second = cleanup_seed_recipes(db_session)
    assert second.recipe_count == 0
    assert second.cooking_history_count == 0
    assert build_cleanup_summary(db_session).preserved_recipe_count == 2
