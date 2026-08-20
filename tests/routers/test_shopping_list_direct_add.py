import re
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_name,
)
from app.crud.shopping_item import (
    get_shopping_items,
)


def create_test_ingredient(
    db_session: Session,
    name: str,
    category: str,
    default_unit: str = "個",
):
    return create_ingredient(
        db=db_session,
        name=name,
        category=category,
        default_unit=default_unit,
        quantity=0,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )


def assert_shopping_list_source_is_hidden(
    response,
) -> None:
    """
    shopping_listへの遷移元情報が
    hidden入力として保持されていることを確認する。
    """
    hidden_source_pattern = re.compile(
        (
            r'<input'
            r'(?=[^>]*\bname="source")'
            r'(?=[^>]*\bvalue="shopping_list")'
            r'[^>]*>'
        ),
        re.DOTALL,
    )

    assert hidden_source_pattern.search(
        response.text
    )


def test_shopping_list_and_add_page_are_separated(
    client: TestClient,
):
    list_response = client.get(
        "/shopping-list"
    )

    assert list_response.status_code == 200
    assert "買うものリスト" in (
        list_response.text
    )
    assert (
        'href="/shopping-list/add"'
        in list_response.text
    )
    assert (
        "shopping-ingredient-search-form"
        not in list_response.text
    )

    add_response = client.get(
        "/shopping-list/add"
    )

    assert add_response.status_code == 200
    assert "買うものを追加" in (
        add_response.text
    )
    assert (
        "shopping-ingredient-search-form"
        in add_response.text
    )
    assert (
        'href="/shopping-list"'
        in add_response.text
    )


def test_add_page_filters_by_keyword_and_categories(
    client: TestClient,
    db_session: Session,
):
    create_test_ingredient(
        db_session=db_session,
        name="たまご",
        category="卵・乳製品",
    )

    create_test_ingredient(
        db_session=db_session,
        name="たまねぎ",
        category="野菜",
    )

    response = client.get(
        "/shopping-list/add",
        params=[
            (
                "ingredient_keyword",
                "タマ",
            ),
            (
                "ingredient_categories",
                "卵・乳製品",
            ),
            (
                "ingredient_categories",
                "野菜",
            ),
        ],
    )

    assert response.status_code == 200
    assert "たまご" in response.text
    assert "たまねぎ" in response.text



def test_multiple_ingredients_can_be_added_directly(
    client: TestClient,
    db_session: Session,
):
    cabbage = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
        category="野菜",
        default_unit="玉",
    )

    beef = create_test_ingredient(
        db_session=db_session,
        name="牛肉",
        category="肉類",
        default_unit="g",
    )

    response = client.post(
        "/shopping-list/add-ingredients",
        data={
            "ingredient_ids": [
                str(cabbage.id),
                str(beef.id),
            ],
            "ingredient_keyword": "",
            "ingredient_categories": [
                "野菜",
                "肉類",
            ],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith(
        "/shopping-list/add?"
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert {
        item.display_name
        for item in shopping_items
    } == {
        "キャベツ",
        "牛肉",
    }


def test_direct_add_rejects_unknown_ingredient(
    client: TestClient,
):
    response = client.post(
        "/shopping-list/add-ingredients",
        data={
            "ingredient_ids": [
                "999999",
            ],
        },
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_custom_item_can_be_added_from_add_page(
    client: TestClient,
    db_session: Session,
):
    response = client.post(
        "/shopping-list/add-custom",
        data={
            "custom_name": (
                "キッチンペーパー"
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith(
        "/shopping-list/add?"
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert len(shopping_items) == 1
    assert (
        shopping_items[0].display_name
        == "キッチンペーパー"
    )
    assert (
        shopping_items[0].ingredient_id
        is None
    )


def test_new_ingredient_source_is_preserved_on_error(
    client: TestClient,
):
    response = client.post(
        "/ingredients",
        data={
            "name": "   ",
            "category_select": "野菜",
            "category_other": "",
            "default_unit_select": "個",
            "default_unit_other": "",
            "quantity": "0",
            "purchase_date": "2026-08-19",
            "expiration_date": "",
            "source": "shopping_list",
        },
    )

    assert response.status_code == 400
    assert (
        "食材名を入力してください"
        in response.text
    )

    assert_shopping_list_source_is_hidden(
        response
    )


def test_new_ingredient_is_added_to_shopping_list(
    client: TestClient,
    db_session: Session,
):
    response = client.post(
        "/ingredients",
        data={
            "name": "ズッキーニ",
            "category_select": "野菜",
            "category_other": "",
            "default_unit_select": "本",
            "default_unit_other": "",
            "quantity": "0",
            "purchase_date": "2026-08-19",
            "expiration_date": "",
            "source": "shopping_list",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith(
        "/shopping-list/add?"
    )

    ingredient = get_ingredient_by_name(
        db=db_session,
        name="ズッキーニ",
    )

    assert ingredient is not None

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert len(shopping_items) == 1
    assert (
        shopping_items[0].ingredient_id
        == ingredient.id
    )


def test_duplicate_confirmation_preserves_source(
    client: TestClient,
    db_session: Session,
):
    create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
        category="野菜",
        default_unit="個",
    )

    response = client.post(
        "/ingredients",
        data={
            "name": "キャベツ",
            "category_select": "野菜",
            "category_other": "",
            "default_unit_select": "個",
            "default_unit_other": "",
            "quantity": "1",
            "purchase_date": "2026-08-19",
            "expiration_date": "",
            "source": "shopping_list",
        },
    )

    assert response.status_code == 409
    assert "重複" in response.text

    assert_shopping_list_source_is_hidden(
        response
    )


def test_duplicate_add_action_adds_item_to_shopping_list(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
        category="野菜",
        default_unit="玉",
    )

    response = client.post(
        "/ingredients/resolve-duplicate",
        data={
            "existing_ingredient_id": (
                str(ingredient.id)
            ),
            "action": "add",
            "name": "キャベツ",
            "category": "野菜",
            "quantity": "1",
            "default_unit": "玉",
            "purchase_date": "2026-08-19",
            "expiration_date": "",
            "source": "shopping_list",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith(
        "/shopping-list/add?"
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert len(shopping_items) == 1
    assert (
        shopping_items[0].ingredient_id
        == ingredient.id
    )


def test_duplicate_cancel_does_not_add_shopping_item(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_test_ingredient(
        db_session=db_session,
        name="キャベツ",
        category="野菜",
        default_unit="玉",
    )

    response = client.post(
        "/ingredients/resolve-duplicate",
        data={
            "existing_ingredient_id": (
                str(ingredient.id)
            ),
            "action": "cancel",
            "name": "キャベツ",
            "category": "野菜",
            "quantity": "1",
            "default_unit": "玉",
            "purchase_date": "2026-08-19",
            "expiration_date": "",
            "source": "shopping_list",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers[
        "location"
    ].startswith(
        "/shopping-list/add?"
    )

    assert (
        get_shopping_items(
            db=db_session
        )
        == []
    )