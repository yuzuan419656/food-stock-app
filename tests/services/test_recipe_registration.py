from dataclasses import replace

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.services.recipe_form import (
    parse_recipe_form,
)
from app.services.recipe_registration import (
    RecipeRegistrationError,
    register_recipe,
)


def _build_form(
    ingredient_name: str,
    ingredient_id: str = "",
    category: str = "野菜",
    quantity: str = "1",
    unit: str = "個",
) -> dict[str, str]:
    return {
        "name": "登録テスト",
        "cooking_time_minutes": "20",
        "cuisine_type": "和食",
        "dish_category": "主菜",
        "yield_type": "servings",
        "base_servings": "2",
        "fixed_yield_text": "",
        "ingredient_0_name": (
            ingredient_name
        ),
        "ingredient_0_id": ingredient_id,
        "ingredient_0_category_select": (
            category
        ),
        "ingredient_0_category_other": "",
        "ingredient_0_quantity_input": (
            quantity
        ),
        "ingredient_0_unit": unit,
        "ingredient_0_notes": "",
        "step_0_description": "調理する。",
    }


def test_register_recipe_with_existing_ingredient(
    db_session,
):
    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    parsed_form = parse_recipe_form(
        _build_form(
            ingredient_name="玉ねぎ",
            ingredient_id=str(ingredient.id),
            quantity="1.5",
        )
    )

    recipe = register_recipe(
        db=db_session,
        parsed_form=parsed_form,
    )

    assert recipe.id is not None
    assert recipe.name == "登録テスト"
    assert len(recipe.ingredients) == 1
    assert (
        recipe.ingredients[0].ingredient_id
        == ingredient.id
    )
    assert (
        recipe.ingredients[0].quantity
        == 1.5
    )
    assert (
        recipe.ingredients[0]
        .is_inventory_consumed
        is True
    )


def test_register_recipe_creates_new_ingredient(
    db_session,
):
    parsed_form = parse_recipe_form(
        _build_form(
            ingredient_name="クミン",
            category="調味料",
            quantity="少々",
            unit="g",
        )
    )

    recipe = register_recipe(
        db=db_session,
        parsed_form=parsed_form,
    )

    ingredient = (
        db_session.query(Ingredient)
        .filter(
            Ingredient.name == "クミン"
        )
        .one()
    )

    assert ingredient.category == "調味料"
    assert ingredient.default_unit == "g"

    # レシピ登録だけでは在庫ロットを作らない。
    assert (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient.id
        )
        .count()
        == 0
    )

    recipe_ingredient = (
        recipe.ingredients[0]
    )

    assert recipe_ingredient.quantity is None
    assert (
        recipe_ingredient.quantity_text
        == "少々"
    )
    assert (
        recipe_ingredient.is_seasoning
        is True
    )
    assert (
        recipe_ingredient
        .is_inventory_consumed
        is False
    )


def test_register_recipe_rejects_mismatched_id_and_name(
    db_session,
):
    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    parsed_form = parse_recipe_form(
        _build_form(
            ingredient_name="じゃがいも",
            ingredient_id=str(ingredient.id),
        )
    )

    with pytest.raises(
        RecipeRegistrationError,
        match="正しくありません",
    ):
        register_recipe(
            db=db_session,
            parsed_form=parsed_form,
        )

    assert (
        db_session.query(Recipe).count()
        == 0
    )


def test_register_recipe_rejects_inactive_ingredient(
    db_session,
):
    ingredient = Ingredient(
        name="削除済み食材",
        category="野菜",
        default_unit="個",
        is_active=False,
    )
    db_session.add(ingredient)
    db_session.commit()

    parsed_form = parse_recipe_form(
        _build_form(
            ingredient_name="削除済み食材",
        )
    )

    with pytest.raises(
        RecipeRegistrationError,
        match="削除済み",
    ):
        register_recipe(
            db=db_session,
            parsed_form=parsed_form,
        )


def test_register_recipe_rolls_back_new_ingredient(
    db_session,
):
    parsed_form = parse_recipe_form(
        _build_form(
            ingredient_name="新しい食材",
        )
    )

    invalid_form = replace(
        parsed_form,
        name=" ",
    )

    with pytest.raises(IntegrityError):
        register_recipe(
            db=db_session,
            parsed_form=invalid_form,
        )

    assert (
        db_session.query(Ingredient)
        .filter(
            Ingredient.name == "新しい食材"
        )
        .count()
        == 0
    )
    assert (
        db_session.query(Recipe).count()
        == 0
    )