from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.crud.recipe import (
    RecipeIngredientInput,
    RecipeStepInput,
    create_recipe,
    delete_recipe,
    get_recipe_by_id,
    get_recipes,
    update_recipe,
    update_recipe_favorite,
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


def test_update_recipe_replaces_all_recipe_data(
    db_session,
):
    egg = Ingredient(
        name="卵",
        category="卵類",
        default_unit="個",
    )
    onion = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add_all([
        egg,
        onion,
    ])
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="卵料理",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=1,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=egg.id,
                quantity=1,
                unit="個",
            )
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="卵を焼く。",
            )
        ],
    )

    recipe_id = recipe.id

    updated_recipe = update_recipe(
        db=db_session,
        recipe_id=recipe_id,
        name=" 野菜入り卵焼き ",
        cooking_time_minutes=15,
        cuisine_type=" 和食 ",
        dish_category=" 副菜 ",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=onion.id,
                quantity=0.5,
                unit=" 個 ",
                display_order=2,
            ),
            RecipeIngredientInput(
                ingredient_id=egg.id,
                quantity=2,
                unit=" 個 ",
                display_order=1,
            ),
        ],
        steps=[
            RecipeStepInput(
                step_number=2,
                description=" フライパンで焼く。 ",
            ),
            RecipeStepInput(
                step_number=1,
                description=" 材料を混ぜる。 ",
            ),
        ],
        is_favorite=True,
    )

    assert updated_recipe is not None

    db_session.expunge_all()

    loaded_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
    )

    assert loaded_recipe is not None
    assert (
        loaded_recipe.name
        == "野菜入り卵焼き"
    )
    assert (
        loaded_recipe.cooking_time_minutes
        == 15
    )
    assert loaded_recipe.cuisine_type == "和食"
    assert loaded_recipe.dish_category == "副菜"
    assert loaded_recipe.base_servings == 2
    assert loaded_recipe.is_favorite is True

    assert [
        item.ingredient.name
        for item in loaded_recipe.ingredients
    ] == [
        "卵",
        "玉ねぎ",
    ]

    assert [
        item.quantity
        for item in loaded_recipe.ingredients
    ] == [
        2,
        0.5,
    ]

    assert [
        item.unit
        for item in loaded_recipe.ingredients
    ] == [
        "個",
        "個",
    ]

    assert [
        step.description
        for step in loaded_recipe.steps
    ] == [
        "材料を混ぜる。",
        "フライパンで焼く。",
    ]

    assert len(loaded_recipe.ingredients) == 2
    assert len(loaded_recipe.steps) == 2

    assert (
        db_session.query(RecipeIngredient)
        .filter(
            RecipeIngredient.recipe_id
            == recipe_id
        )
        .count()
        == 2
    )

    assert (
        db_session.query(RecipeStep)
        .filter(
            RecipeStep.recipe_id
            == recipe_id
        )
        .count()
        == 2
    )


def test_update_recipe_rejects_unavailable_ingredient(
    db_session,
):
    egg = Ingredient(
        name="卵",
        category="卵類",
        default_unit="個",
    )
    inactive_ingredient = Ingredient(
        name="削除済み食材",
        category="その他",
        default_unit="個",
        is_active=False,
        deleted_at=datetime.now(),
    )
    db_session.add_all([
        egg,
        inactive_ingredient,
    ])
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="元のレシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=1,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=egg.id,
                quantity=1,
                unit="個",
            )
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="調理する。",
            )
        ],
    )

    recipe_id = recipe.id

    with pytest.raises(
        ValueError,
        match="有効な食材",
    ):
        update_recipe(
            db=db_session,
            recipe_id=recipe_id,
            name="変更後のレシピ",
            cooking_time_minutes=20,
            cuisine_type="洋食",
            dish_category="副菜",
            yield_type="servings",
            base_servings=2,
            fixed_yield_text=None,
            ingredients=[
                RecipeIngredientInput(
                    ingredient_id=(
                        inactive_ingredient.id
                    ),
                    quantity=1,
                    unit="個",
                )
            ],
            steps=[
                RecipeStepInput(
                    step_number=1,
                    description="変更後の手順。",
                )
            ],
            is_favorite=False,
        )

    db_session.expunge_all()

    loaded_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
    )

    assert loaded_recipe is not None
    assert loaded_recipe.name == "元のレシピ"
    assert [
        item.ingredient.name
        for item in loaded_recipe.ingredients
    ] == ["卵"]
    assert [
        step.description
        for step in loaded_recipe.steps
    ] == ["調理する。"]


def test_update_recipe_rolls_back_all_changes(
    db_session,
):
    cabbage = Ingredient(
        name="キャベツ",
        category="野菜",
        default_unit="枚",
    )
    db_session.add(cabbage)
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="元のレシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="副菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=cabbage.id,
                quantity=2,
                unit="枚",
            )
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="材料を切る。",
            )
        ],
    )

    recipe_id = recipe.id

    with pytest.raises(IntegrityError):
        update_recipe(
            db=db_session,
            recipe_id=recipe_id,
            name="変更後のレシピ",
            cooking_time_minutes=30,
            cuisine_type="洋食",
            dish_category="主菜",
            yield_type="servings",
            base_servings=4,
            fixed_yield_text=None,
            ingredients=[
                RecipeIngredientInput(
                    ingredient_id=cabbage.id,
                    quantity=4,
                    unit="枚",
                )
            ],
            steps=[
                RecipeStepInput(
                    step_number=1,
                    description="最初の手順。",
                ),
                RecipeStepInput(
                    step_number=1,
                    description="重複した手順。",
                ),
            ],
            is_favorite=True,
        )

    db_session.expunge_all()

    loaded_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
    )

    assert loaded_recipe is not None
    assert loaded_recipe.name == "元のレシピ"
    assert (
        loaded_recipe.cooking_time_minutes
        == 10
    )
    assert loaded_recipe.is_favorite is False
    assert len(loaded_recipe.ingredients) == 1
    assert (
        loaded_recipe.ingredients[0].quantity
        == 2
    )
    assert [
        step.description
        for step in loaded_recipe.steps
    ] == ["材料を切る。"]


def test_update_recipe_returns_none_for_missing_id(
    db_session,
):
    updated_recipe = update_recipe(
        db=db_session,
        recipe_id=9999,
        name="存在しないレシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[],
        steps=[],
        is_favorite=False,
    )

    assert updated_recipe is None


def test_delete_recipe_logically_deletes_recipe(
    db_session,
):
    ingredient = Ingredient(
        name="じゃがいも",
        category="野菜",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="じゃがいも料理",
        cooking_time_minutes=20,
        cuisine_type="洋食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=ingredient.id,
                quantity=2,
                unit="個",
            )
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="じゃがいもを調理する。",
            )
        ],
    )

    recipe_id = recipe.id

    result = delete_recipe(
        db=db_session,
        recipe_id=recipe_id,
    )

    assert result is True

    db_session.expunge_all()

    assert (
        get_recipe_by_id(
            db=db_session,
            recipe_id=recipe_id,
        )
        is None
    )

    deleted_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
        include_inactive=True,
    )

    assert deleted_recipe is not None
    assert deleted_recipe.is_active is False
    assert deleted_recipe.deleted_at is not None

    # 論理削除なので材料と手順は残る。
    assert len(deleted_recipe.ingredients) == 1
    assert len(deleted_recipe.steps) == 1


def test_delete_recipe_returns_false_when_unavailable(
    db_session,
):
    recipe = _create_recipe(
        name="削除対象",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    assert (
        delete_recipe(
            db=db_session,
            recipe_id=recipe_id,
        )
        is True
    )

    # すでに削除済みの場合。
    assert (
        delete_recipe(
            db=db_session,
            recipe_id=recipe_id,
        )
        is False
    )

    # 存在しない場合。
    assert (
        delete_recipe(
            db=db_session,
            recipe_id=9999,
        )
        is False
    )


def test_deleted_recipe_cannot_be_updated(
    db_session,
):
    recipe = _create_recipe(
        name="削除されるレシピ",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    delete_recipe(
        db=db_session,
        recipe_id=recipe_id,
    )

    updated_recipe = update_recipe(
        db=db_session,
        recipe_id=recipe_id,
        name="変更後の名前",
        cooking_time_minutes=30,
        cuisine_type="洋食",
        dish_category="副菜",
        yield_type="servings",
        base_servings=4,
        fixed_yield_text=None,
        ingredients=[],
        steps=[],
        is_favorite=True,
    )

    favorite_result = update_recipe_favorite(
        db=db_session,
        recipe_id=recipe_id,
        is_favorite=True,
    )

    assert updated_recipe is None
    assert favorite_result is None

    db_session.expunge_all()

    deleted_recipe = get_recipe_by_id(
        db=db_session,
        recipe_id=recipe_id,
        include_inactive=True,
    )

    assert deleted_recipe is not None
    assert (
        deleted_recipe.name
        == "削除されるレシピ"
    )
    assert deleted_recipe.is_favorite is False
    assert deleted_recipe.is_active is False


def test_update_recipe_favorite(
    db_session,
):
    recipe = _create_recipe(
        name="お気に入り対象",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    favorite_recipe = update_recipe_favorite(
        db=db_session,
        recipe_id=recipe_id,
        is_favorite=True,
    )

    assert favorite_recipe is not None
    assert favorite_recipe.is_favorite is True

    unfavorite_recipe = update_recipe_favorite(
        db=db_session,
        recipe_id=recipe_id,
        is_favorite=False,
    )

    assert unfavorite_recipe is not None
    assert unfavorite_recipe.is_favorite is False

    assert (
        update_recipe_favorite(
            db=db_session,
            recipe_id=9999,
            is_favorite=True,
        )
        is None
    )