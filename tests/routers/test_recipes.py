from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.recipe import Recipe


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
    assert "レシピ一覧" in response.text
    assert "肉じゃが" in response.text
    assert "クッキー" in response.text
    assert "2人分" in response.text
    assert "12枚" in response.text
    assert "★" in response.text
    assert "削除済みレシピ" not in response.text


def test_recipe_list_displays_empty_state(
    client: TestClient,
):
    response = client.get("/recipes")

    assert response.status_code == 200
    assert (
        "登録されているレシピはありません。"
        in response.text
    )