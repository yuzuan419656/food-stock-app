from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.recipe import Recipe
from app.crud.recipe import (
    RecipeIngredientInput,
    RecipeStepInput,
    create_recipe,
)
from app.models.ingredient import Ingredient


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


def test_recipe_list_links_to_create_page(
    client: TestClient,
):
    response = client.get("/recipes")

    assert response.status_code == 200
    assert (
        'href="/recipes/new"'
        in response.text
    )