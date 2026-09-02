from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.recipe import Recipe
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
        f'action="/recipes/{favorite_recipe.id}/favorite"'
        in response.text
    )
    assert "お気に入りを解除" in response.text
    assert "お気に入りに追加" in response.text


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
    assert "レシピを削除する" in response.text


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