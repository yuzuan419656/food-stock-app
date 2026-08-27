import pytest
from sqlalchemy.exc import IntegrityError

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep


def _create_base_recipe_and_ingredient(
    db_session,
) -> tuple[Recipe, Ingredient]:
    recipe = Recipe(
        name="野菜スープ",
        cooking_time_minutes=20,
        cuisine_type="洋食",
        dish_category="汁物",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
    )

    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )

    db_session.add_all([
        recipe,
        ingredient,
    ])
    db_session.commit()

    return recipe, ingredient


def test_create_servings_recipe_with_relations(
    db_session,
):
    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )

    recipe = Recipe(
        name="オニオンスープ",
        cooking_time_minutes=20,
        cuisine_type="洋食",
        dish_category="汁物",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredient(
                ingredient=ingredient,
                quantity=1,
                quantity_text=None,
                unit="個",
                is_seasoning=False,
                is_inventory_consumed=True,
                display_order=1,
            ),
        ],
        steps=[
            RecipeStep(
                step_number=1,
                description="玉ねぎを薄切りにする。",
            ),
            RecipeStep(
                step_number=2,
                description="鍋で玉ねぎを煮る。",
            ),
        ],
    )

    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)

    assert recipe.id is not None
    assert recipe.is_favorite is False
    assert recipe.is_active is True
    assert recipe.deleted_at is None

    assert len(recipe.ingredients) == 1
    assert (
        recipe.ingredients[0].ingredient.name
        == "玉ねぎ"
    )

    assert len(recipe.steps) == 2
    assert {
        step.step_number
        for step in recipe.steps
    } == {1, 2}


@pytest.mark.parametrize(
    (
        "yield_type",
        "base_servings",
        "fixed_yield_text",
    ),
    [
        ("servings", None, None),
        ("servings", 2, "2人分"),
        ("servings", 0, None),
        ("fixed", 2, "12個"),
        ("fixed", None, None),
        ("unknown", None, None),
    ],
)
def test_reject_invalid_yield_values(
    db_session,
    yield_type,
    base_servings,
    fixed_yield_text,
):
    recipe = Recipe(
        name="不正なレシピ",
        cooking_time_minutes=10,
        cuisine_type="その他",
        dish_category="主菜",
        yield_type=yield_type,
        base_servings=base_servings,
        fixed_yield_text=fixed_yield_text,
    )

    db_session.add(recipe)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    ("name", "cooking_time_minutes"),
    [
        ("", 10),
        ("   ", 10),
        ("テストレシピ", 0),
        ("テストレシピ", -1),
    ],
)
def test_reject_invalid_recipe_values(
    db_session,
    name,
    cooking_time_minutes,
):
    recipe = Recipe(
        name=name,
        cooking_time_minutes=cooking_time_minutes,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
    )

    db_session.add(recipe)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_reject_duplicate_recipe_ingredient(
    db_session,
):
    recipe, ingredient = (
        _create_base_recipe_and_ingredient(
            db_session
        )
    )

    db_session.add_all([
        RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=1,
            unit="個",
            is_inventory_consumed=True,
            display_order=1,
        ),
        RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=2,
            unit="個",
            is_inventory_consumed=True,
            display_order=2,
        ),
    ])

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    (
        "quantity",
        "quantity_text",
        "unit",
        "is_seasoning",
        "is_inventory_consumed",
    ),
    [
        (None, "適量", None, False, True),
        (1, None, "個", True, True),
        (1, "適量", "個", False, False),
        (None, None, None, False, False),
        (1, None, None, False, True),
    ],
)
def test_reject_invalid_ingredient_values(
    db_session,
    quantity,
    quantity_text,
    unit,
    is_seasoning,
    is_inventory_consumed,
):
    recipe, ingredient = (
        _create_base_recipe_and_ingredient(
            db_session
        )
    )

    recipe_ingredient = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=quantity,
        quantity_text=quantity_text,
        unit=unit,
        is_seasoning=is_seasoning,
        is_inventory_consumed=(
            is_inventory_consumed
        ),
        display_order=1,
    )

    db_session.add(recipe_ingredient)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_reject_duplicate_step_number(
    db_session,
):
    recipe, _ = (
        _create_base_recipe_and_ingredient(
            db_session
        )
    )

    db_session.add_all([
        RecipeStep(
            recipe_id=recipe.id,
            step_number=1,
            description="最初の手順",
        ),
        RecipeStep(
            recipe_id=recipe.id,
            step_number=1,
            description="重複した手順",
        ),
    ])

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()