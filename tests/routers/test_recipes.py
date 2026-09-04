from datetime import date, datetime
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.cooking_history import CookingHistory
from app.models.recipe import Recipe
from app.models.shopping_item import ShoppingItem
from app.crud.recipe import (
    RecipeIngredientInput,
    RecipeStepInput,
    create_recipe,
)
from app.models.ingredient import Ingredient
from app.models.recipe_ingredient import (
    RecipeIngredient,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

def _create_recipe(
    name: str,
    yield_type: str = "servings",
    base_servings: int | None = 2,
    fixed_yield_text: str | None = None,
    is_favorite: bool = False,
    is_active: bool = True,
) -> Recipe:
    return Recipe(
        name=name,
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type=yield_type,
        base_servings=base_servings,
        fixed_yield_text=fixed_yield_text,
        is_favorite=is_favorite,
        is_active=is_active,
        deleted_at=(
            None
            if is_active
            else datetime.now()
        ),
    )


def _build_recipe_registration_form(
    ingredient_name: str,
    ingredient_id: str = "",
    category: str = "野菜",
    quantity: str = "1",
    unit: str = "個",
) -> dict[str, str]:
    return {
        "name": "登録テストレシピ",
        "cooking_time_minutes": "20",
        "cuisine_type": "和食",
        "dish_category": "主菜",
        "yield_type": "servings",
        "base_servings": "2",
        "fixed_yield_text": "",
        "is_favorite": "true",
        "ingredient_0_name": ingredient_name,
        "ingredient_0_id": ingredient_id,
        "ingredient_0_category_select": (
            category
        ),
        "ingredient_0_category_other": "",
        "ingredient_0_quantity_input": (
            quantity
        ),
        "ingredient_0_unit": unit,
        "ingredient_0_notes": "テスト用",
        "step_0_description": (
            "材料を準備する。"
        ),
        "step_1_description": (
            "材料を調理する。"
        ),
    }


def test_recipe_list_displays_active_recipes(
    client: TestClient,
    db_session: Session,
):
    favorite_recipe = _create_recipe(
        name="肉じゃが",
        is_favorite=True,
    )
    fixed_yield_recipe = _create_recipe(
        name="クッキー",
        yield_type="fixed",
        base_servings=None,
        fixed_yield_text="12枚",
    )
    inactive_recipe = _create_recipe(
        name="削除済みレシピ",
        is_active=False,
    )

    db_session.add_all([
        favorite_recipe,
        fixed_yield_recipe,
        inactive_recipe,
    ])
    db_session.commit()

    response = client.get("/recipes")

    assert response.status_code == 200
    assert "<title>" in response.text
    assert "レシピ一覧" in response.text
    assert 'href="/"' in response.text
    assert 'href="/recipes"' in response.text
    assert (
        'href="/shopping-list"'
        in response.text
    )
    assert "肉じゃが" in response.text
    assert "クッキー" in response.text
    assert "2人分" in response.text
    assert "12枚" in response.text
    assert "★" in response.text
    assert "削除済みレシピ" not in response.text
    assert (
        f'href="/recipes/{favorite_recipe.id}"'
        in response.text
    )
    assert (
        f'href="/recipes/{favorite_recipe.id}/edit"'
        in response.text
    )
    assert (
        f'href="/recipes/{favorite_recipe.id}/delete?return_to=/recipes"'
        in response.text
    )
    assert (
        f'action="/recipes/{favorite_recipe.id}/favorite"'
        in response.text
    )
    assert "お気に入りを解除" in response.text
    assert "お気に入りに追加" in response.text


def test_recipe_list_filters_by_name_with_other_conditions(
    client: TestClient,
    db_session: Session,
):
    target = _create_recipe(name="名前検索カレー")
    target.cuisine_type = "洋食"
    target.dish_category = "主菜"
    other = _create_recipe(name="別のカレー")
    other.cuisine_type = "洋食"
    other.dish_category = "主菜"
    db_session.add_all([target, other])
    db_session.commit()

    response = client.get(
        "/recipes?name_keyword=名前検索&cuisine_type=洋食&dish_category=主菜"
    )

    assert response.status_code == 200
    assert target.name in response.text
    assert other.name not in response.text
    assert 'name="name_keyword"' in response.text


def test_recipe_list_displays_empty_state(
    client: TestClient,
):
    response = client.get("/recipes")

    assert response.status_code == 200
    assert (
        "登録されているレシピはありません。"
        in response.text
    )


def test_recipe_detail_displays_recipe_relations(
    client: TestClient,
    db_session: Session,
):
    potato = Ingredient(
        name="じゃがいも",
        category="野菜",
        default_unit="個",
    )
    salt = Ingredient(
        name="塩",
        category="調味料",
        default_unit="g",
    )
    db_session.add_all([
        potato,
        salt,
    ])
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="じゃがいもの塩煮",
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="副菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=salt.id,
                quantity_text="少々",
                is_seasoning=True,
                is_inventory_consumed=False,
                notes="お好みで",
                display_order=2,
            ),
            RecipeIngredientInput(
                ingredient_id=potato.id,
                quantity=2,
                unit="個",
                display_order=1,
            ),
        ],
        steps=[
            RecipeStepInput(
                step_number=2,
                description="鍋で煮る。",
            ),
            RecipeStepInput(
                step_number=1,
                description="じゃがいもを切る。",
            ),
        ],
        is_favorite=True,
    )

    response = client.get(
        f"/recipes/{recipe.id}"
    )

    assert response.status_code == 200
    assert "じゃがいもの塩煮" in response.text
    assert "和食" in response.text
    assert "副菜" in response.text
    assert "20分" in response.text
    assert "2人分" in response.text
    assert "じゃがいも" in response.text
    assert "2" in response.text
    assert "個" in response.text
    assert "塩" in response.text
    assert "少々" in response.text
    assert "調味料" in response.text
    assert "お好みで" in response.text
    assert "★" in response.text

    assert (
        response.text.index("じゃがいも")
        < response.text.index("塩")
    )
    assert (
        response.text.index("じゃがいもを切る。")
        < response.text.index("鍋で煮る。")
    )


def test_recipe_detail_returns_404_when_unavailable(
    client: TestClient,
    db_session: Session,
):
    inactive_recipe = _create_recipe(
        name="削除済みレシピ",
        is_active=False,
    )
    db_session.add(inactive_recipe)
    db_session.commit()

    inactive_response = client.get(
        f"/recipes/{inactive_recipe.id}"
    )
    missing_response = client.get(
        "/recipes/9999"
    )

    assert inactive_response.status_code == 404
    assert missing_response.status_code == 404


def test_recipe_create_page_displays_form_options(
    client: TestClient,
    db_session: Session,
):
    active_ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
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
        active_ingredient,
        inactive_ingredient,
    ])
    db_session.commit()

    response = client.get("/recipes/new")

    assert response.status_code == 200
    assert "レシピ登録" in response.text
    assert 'name="name"' in response.text
    assert (
        'name="cooking_time_minutes"'
        in response.text
    )
    assert 'name="cuisine_type"' in response.text
    assert 'name="dish_category"' in response.text
    assert 'value="servings"' in response.text
    assert 'value="fixed"' in response.text
    assert "和食" in response.text
    assert "洋食" in response.text
    assert "主菜" in response.text
    assert "副菜" in response.text
    assert "玉ねぎ" in response.text
    assert "削除済み食材" not in response.text
    assert (
        'name="ingredient_0_id"'
        in response.text
    )
    assert (
        'name="step_0_description"'
        in response.text
    )
    assert (
        'name="ingredient_0_name"'
        in response.text
    )
    assert (
        'name="ingredient_0_category_select"'
        in response.text
    )
    assert (
        'name="ingredient_0_unit"'
        in response.text
    )
    assert (
        'list="unit-options-0"'
        in response.text
    )
    assert 'value="個"' in response.text
    assert 'value="g"' in response.text
    assert "製菓材料" in response.text
    assert 'value="kg"' in response.text
    assert 'value="その他"' in response.text
    assert (
        "js/recipe_form.js"
        in response.text
    )
    assert (
        'name="ingredient_0_quantity_input"'
        in response.text
    )
    assert (
        'id="add-ingredient-row"'
        in response.text
    )
    assert (
        'id="recipe-ingredient-rows"'
        in response.text
    )
    assert (
        "data-delete-ingredient-row"
        in response.text
    )
    assert (
        'id="add-step-row"'
        in response.text
    )
    assert (
        'id="recipe-step-rows"'
        in response.text
    )
    assert (
        "data-delete-step-row"
        in response.text
    )
    assert (
        "data-step-description"
        in response.text
    )
    assert (
        "data-move-ingredient-up"
        in response.text
    )
    assert (
        "data-move-ingredient-down"
        in response.text
    )
    assert (
        "data-move-step-up"
        in response.text
    )
    assert (
        "data-move-step-down"
        in response.text
    )


def test_recipe_list_links_to_create_page(
    client: TestClient,
):
    response = client.get("/recipes")

    assert response.status_code == 200
    assert (
        'href="/recipes/new"'
        in response.text
    )


def test_recipe_can_be_registered_with_existing_ingredient(
    client: TestClient,
    db_session: Session,
):
    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    response = client.post(
        "/recipes",
        data=_build_recipe_registration_form(
            ingredient_name="玉ねぎ",
            ingredient_id=str(ingredient.id),
            quantity="1.5",
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    recipe = (
        db_session.query(Recipe)
        .filter(
            Recipe.name
            == "登録テストレシピ"
        )
        .one()
    )

    assert response.headers[
        "location"
    ].startswith(
        f"/recipes/{recipe.id}?"
    )

    assert recipe.is_favorite is True
    assert len(recipe.ingredients) == 1
    assert len(recipe.steps) == 2

    recipe_ingredient = (
        recipe.ingredients[0]
    )

    assert (
        recipe_ingredient.ingredient_id
        == ingredient.id
    )
    assert (
        recipe_ingredient.quantity
        == 1.5
    )
    assert (
        recipe_ingredient.quantity_text
        is None
    )
    assert (
        recipe_ingredient
        .is_inventory_consumed
        is True
    )


def test_recipe_registration_creates_new_ingredient(
    client: TestClient,
    db_session: Session,
):
    response = client.post(
        "/recipes",
        data=_build_recipe_registration_form(
            ingredient_name="クミン",
            category="調味料",
            quantity="少々",
            unit="g",
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    ingredient = (
        db_session.query(Ingredient)
        .filter(
            Ingredient.name == "クミン"
        )
        .one()
    )

    assert ingredient.category == "調味料"
    assert ingredient.default_unit == "g"

    assert (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient.id
        )
        .count()
        == 0
    )

    recipe = (
        db_session.query(Recipe)
        .filter(
            Recipe.name
            == "登録テストレシピ"
        )
        .one()
    )

    recipe_ingredient = (
        recipe.ingredients[0]
    )

    assert (
        recipe_ingredient.quantity
        is None
    )
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


def test_recipe_registration_error_preserves_inputs(
    client: TestClient,
    db_session: Session,
):
    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    form = _build_recipe_registration_form(
        ingredient_name="玉ねぎ",
        ingredient_id=str(ingredient.id),
    )

    form["cooking_time_minutes"] = "abc"

    form.update({
        "ingredient_1_name": "塩",
        "ingredient_1_id": "",
        "ingredient_1_category_select": (
            "調味料"
        ),
        "ingredient_1_category_other": "",
        "ingredient_1_quantity_input": (
            "少々"
        ),
        "ingredient_1_unit": "g",
        "ingredient_1_notes": "",
    })

    response = client.post(
        "/recipes",
        data=form,
    )

    assert response.status_code == 400
    assert "所要時間は整数" in response.text
    assert (
        'value="登録テストレシピ"'
        in response.text
    )
    assert 'value="abc"' in response.text
    assert 'value="玉ねぎ"' in response.text
    assert 'value="塩"' in response.text
    assert "材料を準備する。" in response.text
    assert "材料を調理する。" in response.text

    assert (
        db_session.query(Recipe).count()
        == 0
    )


def test_recipe_edit_page_displays_current_values(
    client: TestClient,
    db_session: Session,
):
    ingredient = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(ingredient)
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="玉ねぎスープ",
        cooking_time_minutes=25,
        cuisine_type="洋食",
        dish_category="汁物",
        yield_type="servings",
        base_servings=3,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=ingredient.id,
                quantity=1.5,
                unit="個",
                notes="薄切り",
            )
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="玉ねぎを切る。",
            ),
            RecipeStepInput(
                step_number=2,
                description="鍋で煮る。",
            ),
        ],
        is_favorite=True,
    )

    response = client.get(
        f"/recipes/{recipe.id}/edit"
    )

    assert response.status_code == 200
    assert "レシピ編集" in response.text
    assert (
        f'action="/recipes/{recipe.id}/edit"'
        in response.text
    )
    assert 'value="玉ねぎスープ"' in response.text
    assert 'value="25"' in response.text
    assert 'value="洋食"' in response.text
    assert 'value="汁物"' in response.text
    assert 'value="3"' in response.text
    assert 'value="玉ねぎ"' in response.text
    assert 'value="1.5"' in response.text
    assert 'value="個"' in response.text
    assert 'value="薄切り"' in response.text
    assert "玉ねぎを切る。" in response.text
    assert "鍋で煮る。" in response.text
    assert "変更を保存" in response.text


def test_recipe_edit_page_returns_404_when_unavailable(
    client: TestClient,
    db_session: Session,
):
    inactive_recipe = _create_recipe(
        name="削除済みレシピ",
        is_active=False,
    )
    db_session.add(inactive_recipe)
    db_session.commit()

    inactive_response = client.get(
        f"/recipes/{inactive_recipe.id}/edit"
    )
    missing_response = client.get(
        "/recipes/9999/edit"
    )

    assert inactive_response.status_code == 404
    assert missing_response.status_code == 404


def test_recipe_can_be_updated_from_form(
    client: TestClient,
    db_session: Session,
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

    db_session.add_all([
        onion,
        potato,
    ])
    db_session.commit()

    onion_id = onion.id
    potato_id = potato.id

    recipe = create_recipe(
        db=db_session,
        name="変更前レシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=onion_id,
                quantity=1,
                unit="個",
            )
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="玉ねぎを切る。",
            )
        ],
    )

    recipe_id = recipe.id

    form = _build_recipe_registration_form(
        ingredient_name="じゃがいも",
        ingredient_id=str(potato_id),
        quantity="2.5",
        unit="個",
    )

    form.update({
        "name": "変更後レシピ",
        "cooking_time_minutes": "30",
        "cuisine_type": "洋食",
        "dish_category": "副菜",
        "base_servings": "3",
        "step_0_description": (
            "じゃがいもを切る。"
        ),
        "step_1_description": (
            "鍋で煮る。"
        ),
    })

    response = client.post(
        f"/recipes/{recipe_id}/edit",
        data=form,
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert response.headers[
        "location"
    ].startswith(
        f"/recipes/{recipe_id}?"
    )

    # セッション上のキャッシュを消し、
    # 更新後の内容をDBから読み直す。
    db_session.expunge_all()

    updated_recipe = (
        db_session.query(Recipe)
        .filter(
            Recipe.id == recipe_id
        )
        .one()
    )

    assert (
        updated_recipe.name
        == "変更後レシピ"
    )
    assert (
        updated_recipe.cooking_time_minutes
        == 30
    )
    assert (
        updated_recipe.cuisine_type
        == "洋食"
    )
    assert (
        updated_recipe.dish_category
        == "副菜"
    )
    assert updated_recipe.base_servings == 3

    assert len(updated_recipe.ingredients) == 1

    recipe_ingredient = (
        updated_recipe.ingredients[0]
    )

    assert (
        recipe_ingredient.ingredient_id
        == potato_id
    )
    assert (
        recipe_ingredient.quantity
        == 2.5
    )
    assert (
        recipe_ingredient.quantity_text
        is None
    )

    assert [
        step.description
        for step in updated_recipe.steps
    ] == [
        "じゃがいもを切る。",
        "鍋で煮る。",
    ]


def test_recipe_update_creates_new_ingredient(
    client: TestClient,
    db_session: Session,
):
    onion = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(onion)
    db_session.commit()

    onion_id = onion.id

    recipe = create_recipe(
        db=db_session,
        name="変更前レシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=onion_id,
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

    form = _build_recipe_registration_form(
        ingredient_name="バジル",
        category="野菜",
        quantity="少々",
        unit="枚",
    )

    form["name"] = "バジル料理"

    response = client.post(
        f"/recipes/{recipe_id}/edit",
        data=form,
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert response.headers[
        "location"
    ].startswith(
        f"/recipes/{recipe_id}?"
    )

    basil = (
        db_session.query(Ingredient)
        .filter(
            Ingredient.name == "バジル"
        )
        .one()
    )

    basil_id = basil.id

    assert basil.category == "野菜"
    assert basil.default_unit == "枚"

    # レシピ編集による食材登録では、
    # 在庫ロットを自動作成しない。
    assert (
        db_session.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == basil_id
        )
        .count()
        == 0
    )

    # 更新後の内容をDBから読み直す。
    db_session.expunge_all()

    updated_recipe = (
        db_session.query(Recipe)
        .filter(
            Recipe.id == recipe_id
        )
        .one()
    )

    assert updated_recipe.name == "バジル料理"
    assert len(updated_recipe.ingredients) == 1

    recipe_ingredient = (
        updated_recipe.ingredients[0]
    )

    assert (
        recipe_ingredient.ingredient_id
        == basil_id
    )
    assert (
        recipe_ingredient.quantity
        is None
    )
    assert (
        recipe_ingredient.quantity_text
        == "少々"
    )
    assert (
        recipe_ingredient.is_seasoning
        is False
    )
    assert (
        recipe_ingredient
        .is_inventory_consumed
        is False
    )


def test_recipe_update_error_preserves_inputs(
    client: TestClient,
    db_session: Session,
):
    onion = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )
    db_session.add(onion)
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="変更前レシピ",
        cooking_time_minutes=10,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=onion.id,
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

    form = _build_recipe_registration_form(
        ingredient_name="玉ねぎ",
        ingredient_id=str(onion.id),
    )

    form["name"] = "入力保持レシピ"
    form["cooking_time_minutes"] = "abc"

    response = client.post(
        f"/recipes/{recipe.id}/edit",
        data=form,
    )

    assert response.status_code == 400
    assert "所要時間は整数" in response.text
    assert "レシピ編集" in response.text
    assert (
        f'action="/recipes/{recipe.id}/edit"'
        in response.text
    )
    assert (
        'value="入力保持レシピ"'
        in response.text
    )
    assert 'value="abc"' in response.text
    assert 'value="玉ねぎ"' in response.text

    db_session.refresh(recipe)

    assert recipe.name == "変更前レシピ"
    assert (
        recipe.cooking_time_minutes
        == 10
    )


def test_recipe_update_returns_404_when_missing(
    client: TestClient,
):
    response = client.post(
        "/recipes/9999/edit",
        data=_build_recipe_registration_form(
            ingredient_name="玉ねぎ",
        ),
    )

    assert response.status_code == 404


def test_recipe_favorite_can_be_toggled_from_list(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(
        name="お気に入り確認",
        is_favorite=False,
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    add_response = client.post(
        f"/recipes/{recipe_id}/favorite",
        data={
            "is_favorite": "true",
        },
        follow_redirects=False,
    )

    assert add_response.status_code == 303
    assert add_response.headers[
        "location"
    ].startswith("/recipes?")

    db_session.refresh(recipe)

    assert recipe.is_favorite is True

    remove_response = client.post(
        f"/recipes/{recipe_id}/favorite",
        data={
            "is_favorite": "false",
        },
        follow_redirects=False,
    )

    assert remove_response.status_code == 303

    db_session.refresh(recipe)

    assert recipe.is_favorite is False


def test_recipe_favorite_update_returns_404_when_missing(
    client: TestClient,
):
    response = client.post(
        "/recipes/9999/favorite",
        data={
            "is_favorite": "true",
        },
    )

    assert response.status_code == 404


def test_recipe_delete_confirmation_is_displayed(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(
        name="削除対象レシピ",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    response = client.get(
        f"/recipes/{recipe_id}/delete"
    )

    assert response.status_code == 200
    assert "レシピ削除確認" in response.text
    assert "削除対象レシピ" in response.text
    assert (
        f'action="/recipes/{recipe_id}/delete"'
        in response.text
    )
    assert 'href="/recipes"' in response.text
    assert "レシピを削除する" in response.text


def test_recipe_delete_cancel_returns_to_detail(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(name="詳細から削除するレシピ")
    db_session.add(recipe)
    db_session.commit()

    response = client.get(f"/recipes/{recipe.id}/delete?return_to=/recipes/{recipe.id}")

    assert response.status_code == 200
    assert f'href="/recipes/{recipe.id}"' in response.text


def test_recipe_delete_cancel_from_list_returns_to_list(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(name="一覧から削除するレシピ")
    db_session.add(recipe)
    db_session.commit()

    response = client.get(f"/recipes/{recipe.id}/delete?return_to=/recipes")

    assert response.status_code == 200
    assert 'href="/recipes"' in response.text


def test_recipe_can_be_logically_deleted(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(
        name="削除対象レシピ",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    response = client.post(
        f"/recipes/{recipe_id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith("/recipes?")

    db_session.refresh(recipe)

    assert recipe.is_active is False
    assert recipe.deleted_at is not None

    detail_response = client.get(
        f"/recipes/{recipe_id}"
    )

    assert detail_response.status_code == 404

    list_response = client.get("/recipes")

    assert "削除対象レシピ" not in (
        list_response.text
    )


def test_recipe_delete_redirect_displays_message(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(
        name="削除対象レシピ",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    response = client.post(
        f"/recipes/{recipe_id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "レシピを削除しました。" in (
        response.text
    )


def test_recipe_delete_returns_404_when_unavailable(
    client: TestClient,
    db_session: Session,
):
    inactive_recipe = _create_recipe(
        name="削除済みレシピ",
        is_active=False,
    )
    db_session.add(inactive_recipe)
    db_session.commit()

    inactive_recipe_id = inactive_recipe.id

    get_inactive_response = client.get(
        f"/recipes/{inactive_recipe_id}/delete"
    )
    post_inactive_response = client.post(
        f"/recipes/{inactive_recipe_id}/delete"
    )
    get_missing_response = client.get(
        "/recipes/9999/delete"
    )
    post_missing_response = client.post(
        "/recipes/9999/delete"
    )

    assert (
        get_inactive_response.status_code
        == 404
    )
    assert (
        post_inactive_response.status_code
        == 404
    )
    assert (
        get_missing_response.status_code
        == 404
    )
    assert (
        post_missing_response.status_code
        == 404
    )


def test_recipe_list_can_be_filtered(
    client: TestClient,
    db_session: Session,
):
    onion = Ingredient(
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
    )

    matching_recipe = _create_recipe(
        name="条件一致レシピ",
        is_favorite=True,
    )
    matching_recipe.ingredients = [
        RecipeIngredient(
            ingredient=onion,
            quantity=1,
            unit="個",
        )
    ]

    not_favorite_recipe = _create_recipe(
        name="お気に入りではないレシピ",
    )
    not_favorite_recipe.ingredients = [
        RecipeIngredient(
            ingredient=onion,
            quantity=1,
            unit="個",
        )
    ]

    western_recipe = _create_recipe(
        name="洋食レシピ",
        is_favorite=True,
    )
    western_recipe.cuisine_type = "洋食"
    western_recipe.ingredients = [
        RecipeIngredient(
            ingredient=onion,
            quantity=1,
            unit="個",
        )
    ]

    db_session.add_all([
        matching_recipe,
        not_favorite_recipe,
        western_recipe,
    ])
    db_session.commit()

    response = client.get(
        "/recipes",
        params={
            "favorite_only": "true",
            "cuisine_type": "和食",
            "dish_category": "主菜",
            "ingredient_keyword": "玉ねぎ",
        },
    )

    assert response.status_code == 200
    assert "条件一致レシピ" in response.text
    assert (
        "お気に入りではないレシピ"
        not in response.text
    )
    assert "洋食レシピ" not in response.text

    assert "適用中の条件" in response.text
    assert "お気に入りのみ" in response.text
    assert "料理系統：" in response.text
    assert "使用材料：" in response.text


def test_recipe_list_displays_no_filter_results(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(
        name="登録済みレシピ",
    )
    db_session.add(recipe)
    db_session.commit()

    response = client.get(
        "/recipes",
        params={
            "ingredient_keyword": (
                "存在しない食材"
            ),
        },
    )

    assert response.status_code == 200
    assert (
        "条件に一致するレシピはありません。"
        in response.text
    )
    assert (
        "登録されているレシピはありません。"
        not in response.text
    )


def test_favorite_toggle_preserves_recipe_filters(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_recipe(
        name="お気に入り確認",
    )
    db_session.add(recipe)
    db_session.commit()

    recipe_id = recipe.id

    response = client.post(
        f"/recipes/{recipe_id}/favorite",
        data={
            "is_favorite": "true",
            "favorite_only": "true",
            "cuisine_type": "和食",
            "dish_category": "主菜",
            "ingredient_keyword": "玉ねぎ",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    parsed_url = urlparse(
        response.headers["location"]
    )
    parameters = parse_qs(
        parsed_url.query
    )

    assert parsed_url.path == "/recipes"
    assert parameters["favorite_only"] == [
        "true"
    ]
    assert parameters["cuisine_type"] == [
        "和食"
    ]
    assert parameters["dish_category"] == [
        "主菜"
    ]
    assert parameters[
        "ingredient_keyword"
    ] == [
        "玉ねぎ"
    ]


def test_recipe_detail_adjusts_ingredient_quantity_by_servings(
    client: TestClient,
    db_session: Session,
):
    potato = Ingredient(
        name="じゃがいも",
        category="野菜",
        default_unit="個",
    )
    salt = Ingredient(
        name="塩",
        category="調味料",
        default_unit="g",
    )

    db_session.add_all([
        potato,
        salt,
    ])
    db_session.commit()

    recipe = create_recipe(
        db=db_session,
        name="人数換算テスト",
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=potato.id,
                quantity=2,
                unit="個",
            ),
            RecipeIngredientInput(
                ingredient_id=salt.id,
                quantity_text="少々",
                is_seasoning=True,
                is_inventory_consumed=False,
            ),
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="調理する。",
            ),
        ],
    )

    response = client.get(
        f"/recipes/{recipe.id}?servings=3"
    )

    assert response.status_code == 200

    assert "3人分" in response.text
    assert "3" in response.text
    assert "個" in response.text
    assert "少々" in response.text


def _create_inventory_check_recipe(
    db_session: Session,
    *,
    recipe_unit: str = "個",
    inventory_unit: str = "個",
    quantity: float | None = 2,
    quantity_text: str | None = None,
    is_seasoning: bool = False,
    is_inventory_consumed: bool = True,
    inventory_quantity: float | None = 3,
) -> Recipe:
    ingredient = (
        db_session.query(Ingredient)
        .filter(
            Ingredient.name == "在庫判定用食材",
            Ingredient.default_unit == inventory_unit,
        )
        .first()
    )
    if ingredient is None:
        ingredient_name = "在庫判定用食材"
        if db_session.query(Ingredient).filter(
            Ingredient.name == ingredient_name,
        ).first() is not None:
            ingredient_name = f"在庫判定用食材_{inventory_unit}"
        ingredient = Ingredient(
            name=ingredient_name,
            category="野菜",
            default_unit=inventory_unit,
        )
        db_session.add(ingredient)
        db_session.commit()

    if inventory_quantity is not None:
        db_session.add(
            Inventory(
                ingredient_id=ingredient.id,
                quantity=inventory_quantity,
                purchase_date=date(2026, 9, 1),
                expiration_date=date(2026, 9, 10),
            )
        )
        db_session.commit()

    return create_recipe(
        db=db_session,
        name="在庫判定テスト",
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type="servings",
        base_servings=2,
        fixed_yield_text=None,
        ingredients=[
            RecipeIngredientInput(
                ingredient_id=ingredient.id,
                quantity=quantity,
                quantity_text=quantity_text,
                unit=(
                    recipe_unit
                    if quantity is not None
                    else None
                ),
                is_seasoning=is_seasoning,
                is_inventory_consumed=(
                    is_inventory_consumed
                ),
            ),
        ],
        steps=[
            RecipeStepInput(
                step_number=1,
                description="調理する。",
            ),
        ],
    )


def test_recipe_detail_displays_inventory_status(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )

    response = client.get(f"/recipes/{recipe.id}")

    assert response.status_code == 200
    assert "在庫状況" in response.text
    for heading in (
        "材料名",
        "必要量",
        "在庫",
        "不足",
        "単位",
        "状態",
    ):
        assert f"<th>{heading}</th>" in response.text
    assert "2個" in response.text
    assert "3個" in response.text
    assert "在庫あり" in response.text


def test_recipe_detail_updates_inventory_status_by_servings(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )

    response = client.get(
        f"/recipes/{recipe.id}?servings=4"
    )

    assert response.status_code == 200
    assert "4個" in response.text
    assert "3個" in response.text
    assert "1個" in response.text
    assert "不足" in response.text


def test_recipe_detail_displays_unit_mismatch(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        recipe_unit="g",
        inventory_unit="個",
    )

    response = client.get(f"/recipes/{recipe.id}")

    assert response.status_code == 200
    assert "不一致（レシピ：g／在庫：個）" in (
        response.text
    )
    assert "自動判定不可" in response.text


def test_recipe_detail_displays_not_applicable(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        quantity=None,
        quantity_text="適量",
        is_seasoning=True,
        is_inventory_consumed=False,
        inventory_quantity=None,
    )

    response = client.get(f"/recipes/{recipe.id}")

    assert response.status_code == 200
    assert "適量" in response.text
    assert "在庫判定対象外" in response.text


def test_recipe_cook_confirmation_displays_plan_without_consuming(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]

    response = client.get(
        f"/recipes/{recipe.id}/cook?servings=2"
    )

    assert response.status_code == 200
    assert "調理確認" in response.text
    assert "在庫消費予定" in response.text
    assert "2人分" in response.text
    assert "消費予定量" in response.text
    assert "2個" in response.text
    db_session.refresh(inventory)
    assert inventory.quantity == 3


def test_recipe_cook_confirmation_keeps_selected_servings(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=5,
    )

    response = client.get(
        f"/recipes/{recipe.id}/cook?servings=4"
    )

    assert response.status_code == 200
    assert "4人分" in response.text
    assert 'name="servings"' in response.text
    assert 'value="4"' in response.text
    assert "4個" in response.text


def test_cook_recipe_consumes_inventory_and_redirects(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]

    response = client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith(
        f"/recipes/{recipe.id}?"
    )
    assert "servings=2" in response.headers["location"]
    assert "%E5%9C%A8%E5%BA%AB" in (
        response.headers["location"]
    )
    db_session.refresh(inventory)
    assert inventory.quantity == 1


def test_cook_recipe_partially_consumes_shortage(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=1,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]

    response = client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "%E4%B8%80%E9%83%A8%E6%9D%90%E6%96%99" in (
        response.headers["location"]
    )
    db_session.refresh(inventory)
    assert inventory.quantity == 0


def test_cook_recipe_does_not_consume_unit_mismatch(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        recipe_unit="g",
        inventory_unit="個",
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]

    confirmation = client.get(
        f"/recipes/{recipe.id}/cook?servings=2"
    )
    response = client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )

    assert "自動判定不可" in confirmation.text
    assert response.status_code == 303
    db_session.refresh(inventory)
    assert inventory.quantity == 3


def test_cook_recipe_does_not_consume_not_applicable_item(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        quantity=None,
        quantity_text="適量",
        is_seasoning=True,
        is_inventory_consumed=False,
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]

    confirmation = client.get(
        f"/recipes/{recipe.id}/cook?servings=2"
    )
    response = client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )

    assert "自動減算対象外" in confirmation.text
    assert response.status_code == 303
    db_session.refresh(inventory)
    assert inventory.quantity == 3


def test_cook_recipe_creates_cooking_history(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )

    response = client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "4"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    history = db_session.query(CookingHistory).one()
    assert history.recipe_id == recipe.id
    assert history.recipe_name == recipe.name
    assert history.servings == 4
    assert history.ingredients[0].required_quantity == 4
    assert history.ingredients[0].consumed_quantity == 3
    assert history.ingredients[0].shortage_quantity == 1


def test_cooking_history_list_is_displayed(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )

    response = client.get("/recipes/history")

    assert response.status_code == 200
    assert "調理履歴" in response.text
    assert recipe.name in response.text
    assert "2人分" in response.text
    history = db_session.query(CookingHistory).one()
    assert f'/recipes/history/{history.id}' in response.text


def test_cooking_history_detail_is_displayed(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=1,
    )
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )
    history = db_session.query(CookingHistory).one()

    response = client.get(
        f"/recipes/history/{history.id}"
    )

    assert response.status_code == 200
    assert recipe.name in response.text
    assert "2人分" in response.text
    assert "必要量" in response.text
    assert "実消費量" in response.text
    assert "不足量" in response.text
    assert "2個" in response.text
    assert "1個" in response.text


def test_only_latest_history_displays_undo_action(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=5,
    )
    for _ in range(2):
        client.post(
            f"/recipes/{recipe.id}/cook",
            data={"servings": "2"},
            follow_redirects=False,
        )
    histories = (
        db_session.query(CookingHistory)
        .order_by(CookingHistory.id)
        .all()
    )

    old_detail = client.get(
        f"/recipes/history/{histories[0].id}"
    )
    latest_detail = client.get(
        f"/recipes/history/{histories[1].id}"
    )
    history_list = client.get("/recipes/history")

    assert "この調理を取り消す" not in old_detail.text
    assert "この調理を取り消す" in latest_detail.text
    assert history_list.text.count("この調理を取り消す") == 1


def test_cooking_undo_confirmation_does_not_restore_inventory(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )
    history = db_session.query(CookingHistory).one()

    response = client.get(
        f"/recipes/history/{history.id}/undo"
    )

    assert response.status_code == 200
    assert "調理取り消し確認" in response.text
    assert recipe.name in response.text
    assert "2人分" in response.text
    assert "復元数量" in response.text
    assert "2個" in response.text
    db_session.refresh(inventory)
    assert inventory.quantity == 1


def test_cooking_undo_post_restores_inventory_and_redirects(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )
    history = db_session.query(CookingHistory).one()

    response = client.post(
        f"/recipes/history/{history.id}/undo",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith(
        f"/recipes/history/{history.id}?"
    )
    db_session.refresh(inventory)
    db_session.refresh(history)
    assert inventory.quantity == 3
    assert history.undone_at is not None


def test_undone_history_does_not_display_undo_action(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )
    history = db_session.query(CookingHistory).one()
    client.post(
        f"/recipes/history/{history.id}/undo",
        follow_redirects=False,
    )

    detail = client.get(f"/recipes/history/{history.id}")
    history_list = client.get("/recipes/history")

    assert "取り消し済み" in detail.text
    assert "取り消し日時" in detail.text
    assert "この調理を取り消す" not in detail.text
    assert "取り消し済み" in history_list.text
    assert "この調理を取り消す" not in history_list.text


def test_repeated_undo_post_does_not_restore_twice(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )
    history = db_session.query(CookingHistory).one()
    client.post(
        f"/recipes/history/{history.id}/undo",
        follow_redirects=False,
    )

    response = client.post(
        f"/recipes/history/{history.id}/undo",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "error_message=" in response.headers["location"]
    db_session.refresh(inventory)
    assert inventory.quantity == 3


def test_recipe_detail_displays_shopping_list_button_only_for_shortage(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session, inventory_quantity=1
    )
    inventory = recipe.ingredients[0].ingredient.inventories[0]
    shortage_response = client.get(f"/recipes/{recipe.id}")

    inventory.quantity = 3
    db_session.commit()
    sufficient_response = client.get(f"/recipes/{recipe.id}")

    assert (
        "不足食材を買うものリストへ追加"
        in shortage_response.text
    )
    assert (
        "不足食材を買うものリストへ追加"
        not in sufficient_response.text
    )


def test_recipe_shopping_list_confirmation_keeps_servings_without_writing(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session, inventory_quantity=1
    )

    response = client.get(
        f"/recipes/{recipe.id}/shopping-list?servings=4"
    )

    assert response.status_code == 200
    assert "不足食材の追加確認" in response.text
    assert "4人分" in response.text
    assert "3" in response.text
    assert 'name="servings"' in response.text
    assert 'value="4"' in response.text
    assert db_session.query(ShoppingItem).count() == 0


def test_recipe_shopping_list_post_adds_and_redirects(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session, inventory_quantity=0
    )

    response = client.post(
        f"/recipes/{recipe.id}/shopping-list",
        data={"servings": "2"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith(
        f"/recipes/{recipe.id}?"
    )
    assert "message=" in response.headers["location"]
    item = db_session.query(ShoppingItem).one()
    assert item.ingredient_id == recipe.ingredients[0].ingredient_id
    assert item.is_purchased is False


def test_recipe_shopping_list_post_recalculates_current_shortage(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session, inventory_quantity=0
    )
    confirmation = client.get(
        f"/recipes/{recipe.id}/shopping-list?servings=2"
    )
    assert "追加対象の不足食材はありません" not in confirmation.text

    db_session.add(
        Inventory(
            ingredient_id=recipe.ingredients[0].ingredient_id,
            quantity=2,
            purchase_date=date(2026, 9, 2),
        )
    )
    db_session.commit()

    response = client.post(
        f"/recipes/{recipe.id}/shopping-list",
        data={"servings": "2"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert db_session.query(ShoppingItem).count() == 0


def test_recipe_recommendations_page_displays_results(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )

    response = client.get("/recipes/recommendations")

    assert response.status_code == 200
    assert "おすすめレシピ" in response.text
    assert recipe.name in response.text
    assert "1位" in response.text
    assert "合計スコア" in response.text
    assert "必要な食材がすべて在庫にあります" in response.text
    assert "不足食材" in response.text
    assert "期限切迫食材" in response.text
    assert "調理回数" in response.text
    assert "最終調理日" in response.text
    assert 'name="cuisine_type"' in response.text
    assert 'name="dish_category"' in response.text


def test_recipe_recommendations_filters_by_cuisine_and_category(
    client: TestClient,
    db_session: Session,
):
    japanese = _create_inventory_check_recipe(db_session, inventory_quantity=3)
    western = _create_inventory_check_recipe(db_session, inventory_quantity=3)
    western.name = "洋食副菜候補"
    western.cuisine_type = "洋食"
    western.dish_category = "副菜"
    db_session.commit()

    response = client.get(
        "/recipes/recommendations?cuisine_type=洋食&dish_category=副菜"
    )

    assert response.status_code == 200
    assert western.name in response.text
    assert japanese.name not in response.text


@pytest.mark.parametrize(
    ("mode", "label"),
    [
        ("balanced", "バランス"),
        ("expiring", "期限が近い食材を優先"),
        ("quick", "すぐ作れる"),
        ("in_stock", "在庫だけで作れる"),
    ],
)
def test_recipe_recommendation_modes_are_selected(
    client: TestClient,
    mode: str,
    label: str,
):
    response = client.get(
        f"/recipes/recommendations?mode={mode}"
    )

    assert response.status_code == 200
    assert label in response.text
    assert f'value="{mode}"' in response.text


def test_recipe_recommendations_passes_servings_and_detail_link(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )

    response = client.get(
        "/recipes/recommendations?servings=4"
    )

    assert response.status_code == 200
    assert 'value="4"' in response.text
    assert "1種類" in response.text
    assert (
        f'/recipes/{recipe.id}?servings=4'
        in response.text
    )


@pytest.mark.parametrize(
    "max_cooking_time",
    [10, 20, 30],
)
def test_recipe_recommendations_filters_cooking_time(
    client: TestClient,
    db_session: Session,
    max_cooking_time: int,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )

    response = client.get(
        "/recipes/recommendations"
        f"?max_cooking_time={max_cooking_time}"
    )

    assert response.status_code == 200
    if max_cooking_time < recipe.cooking_time_minutes:
        assert recipe.name not in response.text
        assert "条件に合うレシピがありません" in response.text
    else:
        assert recipe.name in response.text


def test_recipe_recommendations_without_time_filter(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    response = client.get("/recipes/recommendations")
    assert recipe.name in response.text
    assert "指定なし" in response.text


def test_recipe_recommendations_displays_history_values(
    client: TestClient,
    db_session: Session,
):
    recipe = _create_inventory_check_recipe(
        db_session,
        inventory_quantity=3,
    )
    client.post(
        f"/recipes/{recipe.id}/cook",
        data={"servings": "2"},
        follow_redirects=False,
    )

    response = client.get("/recipes/recommendations")

    assert "1回" in response.text
    assert datetime.now().strftime("%Y-%m-%d") in response.text


def test_recipe_recommendations_empty_state(client: TestClient):
    response = client.get("/recipes/recommendations")
    assert response.status_code == 200
    assert "条件に合うレシピがありません" in response.text


def test_recipe_recommendations_rejects_invalid_mode(
    client: TestClient,
):
    response = client.get(
        "/recipes/recommendations?mode=invalid"
    )
    assert response.status_code == 422


def test_navigation_links_to_recipe_recommendations(
    client: TestClient,
):
    response = client.get("/recipes")
    assert 'href="/recipes/recommendations"' in response.text
    assert "おすすめレシピ" in response.text


def test_recipe_recommendations_displays_weight_controls(
    client: TestClient,
):
    response = client.get("/recipes/recommendations")

    assert response.status_code == 200
    assert "重みを調整" in response.text
    for name in (
        "expiration_weight",
        "inventory_weight",
        "favorite_weight",
        "history_weight",
        "recency_weight",
        "cooking_time_weight",
        "shortage_weight",
    ):
        assert f'name="{name}"' in response.text
    assert 'min="0"' in response.text
    assert 'max="3"' in response.text
    assert 'step="0.1"' in response.text
    assert 'value="1.0"' in response.text


def test_recipe_recommendations_keeps_custom_weights(
    client: TestClient,
):
    response = client.get(
        "/recipes/recommendations"
        "?expiration_weight=0.5"
        "&inventory_weight=1.2"
        "&favorite_weight=1.3"
        "&history_weight=1.4"
        "&recency_weight=1.5"
        "&cooking_time_weight=1.6"
        "&shortage_weight=1.7"
    )

    assert response.status_code == 200
    for value in ("0.5", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"):
        assert f'value="{value}"' in response.text


@pytest.mark.parametrize(
    "query",
    [
        "expiration_weight=-0.1",
        "inventory_weight=3.1",
        "favorite_weight=abc",
        "history_weight=nan",
        "recency_weight=inf",
    ],
)
def test_recipe_recommendations_rejects_invalid_weights(
    client: TestClient,
    query: str,
):
    response = client.get(
        f"/recipes/recommendations?{query}"
    )
    assert response.status_code == 422


def test_recipe_recommendation_weight_reset_keeps_basic_conditions(
    client: TestClient,
):
    response = client.get(
        "/recipes/recommendations"
        "?servings=4&mode=quick&max_cooking_time=20"
        "&expiration_weight=2"
    )

    assert response.status_code == 200
    assert "標準に戻す" in response.text
    reset_link = re.search(
        r'href="([^"]+)"[^>]*class="[^"]*recipe-weight-reset',
        response.text,
    )
    assert reset_link is not None
    reset_url = urlparse(reset_link.group(1))
    assert reset_url.path == "/recipes/recommendations"
    assert parse_qs(reset_url.query) == {
        "servings": ["4"],
        "mode": ["quick"],
        "max_cooking_time": ["20"],
    }


def test_custom_weight_changes_recommendation_order(
    client: TestClient,
    db_session: Session,
):
    standard = _create_recipe("標準レシピ")
    favorite = _create_recipe(
        "お気に入りレシピ",
        is_favorite=True,
    )
    db_session.add_all([standard, favorite])
    db_session.commit()

    default_response = client.get(
        "/recipes/recommendations"
    )
    zero_favorite_response = client.get(
        "/recipes/recommendations?favorite_weight=0"
    )

    assert default_response.text.index("お気に入りレシピ") < (
        default_response.text.index("標準レシピ")
    )
    assert zero_favorite_response.text.index("標準レシピ") < (
        zero_favorite_response.text.index("お気に入りレシピ")
    )


def test_custom_weights_combine_with_other_recommendation_conditions(
    client: TestClient,
):
    response = client.get(
        "/recipes/recommendations"
        "?servings=3&mode=expiring&max_cooking_time=30"
        "&expiration_weight=2.5"
    )

    assert response.status_code == 200
    assert 'value="3"' in response.text
    assert 'value="expiring"' in response.text
    assert 'value="30"' in response.text
    assert 'value="2.5"' in response.text
