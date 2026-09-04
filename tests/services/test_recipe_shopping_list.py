from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.shopping_item import ShoppingItem
from app.services.recipe_shopping_list import (
    add_recipe_shortages_to_shopping_list,
    build_recipe_shopping_list_candidates,
)


def _recipe(
    db: Session,
    *,
    required: float | None = 2,
    stock: float = 0,
    recipe_unit: str | None = "個",
    inventory_unit: str | None = "個",
    yield_type: str = "servings",
    is_seasoning: bool = False,
    is_inventory_consumed: bool = True,
    name: str = "じゃがいも",
) -> Recipe:
    ingredient = Ingredient(
        name=name,
        category="野菜",
        default_unit=inventory_unit,
    )
    if stock:
        ingredient.inventories = [
            Inventory(
                quantity=stock,
                purchase_date=date(2026, 9, 1),
            )
        ]
    item = RecipeIngredient(
        ingredient=ingredient,
        quantity=required,
        quantity_text=None if required is not None else "適量",
        unit=recipe_unit if required is not None else None,
        is_seasoning=is_seasoning,
        is_inventory_consumed=is_inventory_consumed,
        display_order=1,
    )
    recipe = Recipe(
        name=f"{name}レシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type=yield_type,
        base_servings=2 if yield_type == "servings" else None,
        fixed_yield_text=None if yield_type == "servings" else "1皿",
        ingredients=[item],
    )
    db.add(recipe)
    db.commit()
    return recipe


@pytest.mark.parametrize(
    ("stock", "shortage"),
    [(0, 2), (1, 1)],
)
def test_build_candidates_for_zero_and_partial_stock(
    db_session: Session,
    stock: float,
    shortage: float,
):
    candidates = build_recipe_shopping_list_candidates(
        _recipe(db_session, stock=stock)
    )

    assert len(candidates) == 1
    assert candidates[0].shortage_quantity == shortage


def test_build_candidates_scales_selected_servings(db_session: Session):
    candidates = build_recipe_shopping_list_candidates(
        _recipe(db_session, stock=1),
        target_servings=4,
    )

    assert candidates[0].shortage_quantity == 3


def test_fixed_yield_keeps_registered_quantity(db_session: Session):
    candidates = build_recipe_shopping_list_candidates(
        _recipe(db_session, required=3, stock=1, yield_type="fixed")
    )

    assert candidates[0].shortage_quantity == 2


@pytest.mark.parametrize(
    "recipe_kwargs",
    [
        {"stock": 2},
        {"recipe_unit": "g", "inventory_unit": "個"},
        {"is_seasoning": True, "is_inventory_consumed": False},
        {"required": None, "is_inventory_consumed": False},
        {"is_inventory_consumed": False},
    ],
)
def test_non_actionable_statuses_are_excluded(
    db_session: Session,
    recipe_kwargs: dict,
):
    recipe = _recipe(db_session, **recipe_kwargs)

    assert build_recipe_shopping_list_candidates(recipe) == []


def test_adds_multiple_shortages_with_one_commit(db_session: Session, monkeypatch):
    recipe = _recipe(db_session, name="玉ねぎ")
    second = _recipe(db_session, name="牛肉")
    recipe.ingredients.append(second.ingredients[0])
    db_session.commit()

    original_commit = db_session.commit
    commit_count = 0

    def counted_commit():
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(db_session, "commit", counted_commit)
    result = add_recipe_shortages_to_shopping_list(db_session, recipe)

    assert result.candidate_count == 2
    assert result.added_count == 2
    assert commit_count == 1
    assert db_session.query(ShoppingItem).count() == 2


def test_post_time_recalculation_uses_current_inventory(db_session: Session):
    recipe = _recipe(db_session, required=2, stock=0)
    assert build_recipe_shopping_list_candidates(recipe)[0].shortage_quantity == 2

    recipe.ingredients[0].ingredient.inventories.append(
        Inventory(quantity=2, purchase_date=date(2026, 9, 2))
    )
    db_session.commit()

    result = add_recipe_shortages_to_shopping_list(db_session, recipe)
    assert result.candidate_count == 0
    assert db_session.query(ShoppingItem).count() == 0


def test_failure_rolls_back_all_items(db_session: Session, monkeypatch):
    recipe = _recipe(db_session)

    def fail_after_add(db, ingredient_ids):
        db.add(ShoppingItem(ingredient_id=ingredient_ids[0]))
        db.flush()
        raise RuntimeError("追加失敗")

    monkeypatch.setattr(
        "app.services.recipe_shopping_list."
        "add_or_reactivate_ingredients_without_commit",
        fail_after_add,
    )

    with pytest.raises(RuntimeError, match="追加失敗"):
        add_recipe_shortages_to_shopping_list(db_session, recipe)

    assert db_session.query(ShoppingItem).count() == 0
