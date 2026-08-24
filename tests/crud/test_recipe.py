from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.crud.recipe import (
    RecipeIngredientInput,
    RecipeStepInput,
    create_recipe,
    get_recipe_by_id,
    get_recipes,
)
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.recipe_ingredient import (
    RecipeIngredient,
)
from app.models.recipe_step import RecipeStep


def _create_recipe(
    name: str,
    is_active: bool = True,
) -> Recipe:
    return Recipe(
        name=name,
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        is_active=is_active,
        deleted_at=(
            None
            if is_active
            else datetime.now()
        ),
    )


def test_get_recipes_returns_only_active_recipes(
    db_session,
):
    active_recipe = _create_recipe(
        name="肉じゃが",
    )
    inactive_recipe = _create_recipe(
        name="削除済みカレー",
        is_active=False,
    )

    db_session.add_all([
        active_recipe,
        inactive_recipe,
    ])
    db_session.commit()

    recipes = get_recipes(
        db=db_session,
    )

    assert [
        recipe.id
        for recipe in recipes
    ] == [active_recipe.id]


def test_get_recipes_can_include_inactive_recipes(
    db_session,
):
    active_recipe = _create_recipe(
        name="肉じゃが",
    )
    inactive_recipe = _create_recipe(
        name="削除済みカレー",
        is_active=False,
    )

    db_session.add_all([
        active_recipe,
        inactive_recipe,
    ])
    db_session.commit()

    recipes = get_recipes(
        db=db_session,
        include_inactive=True,
    )

    assert [
        recipe.id
        for recipe in recipes
    ] == [
        active_recipe.id,
        inactive_recipe.id,
    ]


def test_get_recipe_by_id_loads_relations_in_order(
    db_session,
):
    onion = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    potato = Ingredient(
        name="じゃがいも",
        category="野菜",
        default_unit="個",
    )

    recipe = _create_recipe(
        name="野菜スープ",
    )

    recipe.ingredients = [
        RecipeIngredient(
            ingredient=onion,
            quantity=1,
            unit="個",
            display_order=2,
        ),
        RecipeIngredient(
            ingredient=potato,
            quantity=2,
            unit="個",
            display_order=1,
        ),
    ]

    recipe.steps = [
        RecipeStep(
            step_number=2,
            description="鍋で煮る。",
        ),
        RecipeStep(
            step_number=1,
            description="材料を切る。",
        ),
    ]

    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    # セッション上のキャッシュを消し、
    # CRUDから改めて読み込ませる。
    db_session.expunge_all()

    loaded_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
    )

    assert loaded_recipe is not None

    assert [
        item.ingredient.name
        for item in loaded_recipe.ingredients
    ] == [
        "じゃがいも",
        "玉ねぎ",
    ]

    assert [
        step.step_number
        for step in loaded_recipe.steps
    ] == [1, 2]


def test_get_recipe_by_id_hides_inactive_recipe(
    db_session,
):
    recipe = _create_recipe(
        name="削除済みレシピ",
        is_active=False,
    )

    db_session.add(recipe)
    db_session.commit()

    assert (
        get_recipe_by_id(
            db=db_session,
            recipe_id=recipe.id,
        )
        is None
    )

    assert (
        get_recipe_by_id(
            db=db_session,
            recipe_id=recipe.id,
            include_inactive=True,
        )
        is not None
    )


def test_get_recipe_by_id_returns_none_for_missing_id(
    db_session,
):
    recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=9999,
    )

    assert recipe is None


def test_create_recipe_with_ingredients_and_steps(
    db_session,
):
    flour = Ingredient(
        name="薄力粉",
        category="粉類",
        default_unit="g",
    )
    salt = Ingredient(
        name="塩",
        category="調味料",
        default_unit="g",
    )

    db_session.add_all([
        flour,
        salt,
    ])
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name=" クッキー ",
        cooking_time_minutes=40,
        cuisine_type=" 洋食 ",
        dish_category=" お菓子 ",
        yield_type="fixed",
        base_servings=None,
        fixed_yield_text=" 12枚 ",
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=salt.id,
                quantity_text=" 少々 ",
                unit=None,
                is_seasoning=True,
                is_inventory_consumed=False,
                display_order=2,
            ),
            RecipeIngredientInput(
                ingredient_id=flour.id,
                quantity=120,
                unit=" g ",
                display_order=1,
            ),
        ],
        steps=[
            RecipeStepInput(
                step_number=2,
                description=" オーブンで焼く。 ",
            ),
            RecipeStepInput(
                step_number=1,
                description=" 材料を混ぜる。 ",
            ),
        ],
        is_favorite=True,
    )

    recipe_id = recipe.id
    db_session.expunge_all()

    loaded_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
    )

    assert loaded_recipe is not None
    assert loaded_recipe.name == "クッキー"
    assert loaded_recipe.cuisine_type == "洋食"
    assert loaded_recipe.dish_category == "お菓子"
    assert loaded_recipe.yield_type == "fixed"
    assert loaded_recipe.base_servings is None
    assert loaded_recipe.fixed_yield_text == "12枚"
    assert loaded_recipe.is_favorite is True

    assert [
        item.ingredient.name
        for item in loaded_recipe.ingredients
    ] == [
        "薄力粉",
        "塩",
    ]

    assert (
        loaded_recipe.ingredients[0].unit
        == "g"
    )
    assert (
        loaded_recipe.ingredients[1]
        .quantity_text
        == "少々"
    )

    assert [
        step.step_number
        for step in loaded_recipe.steps
    ] == [1, 2]

    assert [
        step.description
        for step in loaded_recipe.steps
    ] == [
        "材料を混ぜる。",
        "オーブンで焼く。",
    ]


@pytest.mark.parametrize(
    (
        "include_ingredients",
        "include_steps",
        "expected_message",
    ),
    [
        (False, True, "レシピ材料"),
        (True, False, "調理手順"),
    ],
)
def test_create_recipe_requires_relations(
    db_session,
    include_ingredients,
    include_steps,
    expected_message,
):
    ingredient = Ingredient(
        name="卵",
        category="卵類",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    ingredients = (
        [
            RecipeIngredientInput(
                ingredient_id=ingredient.id,
                quantity=2,
                unit="個",
            )
        ]
        if include_ingredients
        else []
    )

    steps = (
        [
            RecipeStepInput(
                step_number=1,
                description="調理する。",
            )
        ]
        if include_steps
        else []
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        create_recipe(
            db=db_session,
            name="テストレシピ",
            cooking_time_minutes=10,
            cuisine_type="和食",
            dish_category="主菜",
            yield_type="servings",
            base_servings=2,
            fixed_yield_text=None,
            ingredients=ingredients,
            steps=steps,
        )


def test_create_recipe_rejects_unavailable_ingredient(
    db_session,
):
    inactive_ingredient = Ingredient(
        name="削除済み食材",
        category="その他",
        default_unit="個",
        is_active=False,
        deleted_at=datetime.now(),
    )
    db_session.add(inactive_ingredient)
    db_session.commit()

    common_arguments = {
        "db": db_session,
        "name": "テストレシピ",
        "cooking_time_minutes": 10,
        "cuisine_type": "和食",
        "dish_category": "主菜",
        "yield_type": "servings",
        "base_servings": 2,
        "fixed_yield_text": None,
        "steps": [
            RecipeStepInput(
                step_number=1,
                description="調理する。",
            )
        ],
    }

    with pytest.raises(
        ValueError,
        match="有効な食材",
    ):
        create_recipe(
            **common_arguments,
            ingredients=[
                RecipeIngredientInput(
                    ingredient_id=(
                        inactive_ingredient.id
                    ),
                    quantity=1,
                    unit="個",
                )
            ],
        )

    with pytest.raises(
        ValueError,
        match="有効な食材",
    ):
        create_recipe(
            **common_arguments,
            ingredients=[
                RecipeIngredientInput(
                    ingredient_id=9999,
                    quantity=1,
                    unit="個",
                )
            ],
        )

    assert (
        db_session.query(Recipe).count()
        == 0
    )


def test_create_recipe_rejects_duplicate_ingredient(
    db_session,
):
    ingredient = Ingredient(
        name="にんじん",
        category="野菜",
        default_unit="本",
    )
    db_session.add(ingredient)
    db_session.commit()

    duplicated_ingredients = [
        RecipeIngredientInput(
            ingredient_id=ingredient.id,
            quantity=1,
            unit="本",
            display_order=1,
        ),
        RecipeIngredientInput(
            ingredient_id=ingredient.id,
            quantity=2,
            unit="本",
            display_order=2,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="重複",
    ):
        create_recipe(
            db=db_session,
            name="にんじん料理",
            cooking_time_minutes=15,
            cuisine_type="和食",
            dish_category="副菜",
            yield_type="servings",
            base_servings=2,
            fixed_yield_text=None,
            ingredients=(
                duplicated_ingredients
            ),
            steps=[
                RecipeStepInput(
                    step_number=1,
                    description="調理する。",
                )
            ],
        )


def test_create_recipe_rolls_back_all_records(
    db_session,
):
    ingredient = Ingredient(
        name="キャベツ",
        category="野菜",
        default_unit="枚",
    )
    db_session.add(ingredient)
    db_session.commit()

    with pytest.raises(IntegrityError):
        create_recipe(
            db=db_session,
            name="ロールバック確認",
            cooking_time_minutes=10,
            cuisine_type="和食",
            dish_category="副菜",
            yield_type="servings",
            base_servings=2,
            fixed_yield_text=None,
            ingredients=[
                RecipeIngredientInput(
                    ingredient_id=ingredient.id,
                    quantity=2,
                    unit="枚",
                )
            ],
            steps=[
                RecipeStepInput(
                    step_number=1,
                    description="材料を切る。",
                ),
                RecipeStepInput(
                    step_number=1,
                    description="重複した手順。",
                ),
            ],
        )

    assert (
        db_session.query(Recipe)
        .filter(
            Recipe.name
            == "ロールバック確認"
        )
        .count()
        == 0
    )

    # rollback後もセッションを利用できる。
    assert (
        db_session.query(Ingredient)
        .filter(
            Ingredient.id == ingredient.id
        )
        .count()
        == 1
    )