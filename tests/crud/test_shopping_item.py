from datetime import date
import pytest

from sqlalchemy.orm import Session

from app.crud.ingredient import create_ingredient
from app.crud.shopping_item import (
    add_custom_shopping_item,
    add_ingredients_to_shopping_list,
    delete_purchased_shopping_items,
    get_shopping_ingredient_candidates,
    get_shopping_ingredient_categories,
    get_shopping_items,
    toggle_shopping_item,
)

def test_add_ingredients_to_shopping_list(
    db_session: Session,
):
    milk = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    egg = create_ingredient(
        db=db_session,
        name="卵",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(2026, 8, 6),
    )

    added_count = add_ingredients_to_shopping_list(
        db=db_session,
        ingredient_ids=[milk.id, egg.id],
    )

    assert added_count == 2

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert {
        item.ingredient.name
        for item in shopping_items
    } == {
        "牛乳",
        "卵",
    }


def test_duplicate_ingredient_is_not_added(
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    first_added_count = (
        add_ingredients_to_shopping_list(
            db=db_session,
            ingredient_ids=[ingredient.id],
        )
    )

    second_added_count = (
        add_ingredients_to_shopping_list(
            db=db_session,
            ingredient_ids=[ingredient.id],
        )
    )

    assert first_added_count == 1
    assert second_added_count == 0
    assert len(
        get_shopping_items(db=db_session)
    ) == 1


def test_toggle_shopping_item(
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    add_ingredients_to_shopping_list(
        db=db_session,
        ingredient_ids=[ingredient.id],
    )

    shopping_item = get_shopping_items(
        db=db_session
    )[0]

    assert shopping_item.is_purchased is False

    updated_item = toggle_shopping_item(
        db=db_session,
        shopping_item_id=shopping_item.id,
    )

    assert updated_item is not None
    assert updated_item.is_purchased is True


def test_delete_only_purchased_shopping_items(
    db_session: Session,
):
    milk = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(2026, 8, 6),
    )

    egg = create_ingredient(
        db=db_session,
        name="卵",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(2026, 8, 6),
    )

    add_ingredients_to_shopping_list(
        db=db_session,
        ingredient_ids=[milk.id, egg.id],
    )

    shopping_items = get_shopping_items(
        db=db_session
    )

    purchased_item = next(
        item
        for item in shopping_items
        if item.ingredient.name == "牛乳"
    )

    toggle_shopping_item(
        db=db_session,
        shopping_item_id=purchased_item.id,
    )

    deleted_count = (
        delete_purchased_shopping_items(
            db=db_session
        )
    )

    remaining_items = get_shopping_items(
        db=db_session
    )

    assert deleted_count == 1
    assert len(remaining_items) == 1
    assert (
        remaining_items[0].ingredient.name
        == "卵"
    )
    assert (
        remaining_items[0].is_purchased
        is False
    )


def test_add_custom_shopping_item(
    db_session: Session,
):
    shopping_item = add_custom_shopping_item(
        db=db_session,
        custom_name="キッチンペーパー",
    )

    assert shopping_item is not None
    assert shopping_item.ingredient_id is None
    assert (
        shopping_item.custom_name
        == "キッチンペーパー"
    )
    assert (
        shopping_item.display_name
        == "キッチンペーパー"
    )
    assert shopping_item.is_purchased is False


def test_add_custom_shopping_item_trims_name(
    db_session: Session,
):
    shopping_item = add_custom_shopping_item(
        db=db_session,
        custom_name="  食品用ラップ  ",
    )

    assert shopping_item is not None
    assert (
        shopping_item.custom_name
        == "食品用ラップ"
    )


def test_duplicate_custom_shopping_item_is_not_added(
    db_session: Session,
):
    first_item = add_custom_shopping_item(
        db=db_session,
        custom_name="キッチンペーパー",
    )

    second_item = add_custom_shopping_item(
        db=db_session,
        custom_name="キッチンペーパー",
    )

    assert first_item is not None
    assert second_item is None

    shopping_items = get_shopping_items(
        db=db_session
    )

    assert len(shopping_items) == 1


def test_duplicate_custom_name_uses_normalized_name(
    db_session: Session,
):
    first_item = add_custom_shopping_item(
        db=db_session,
        custom_name="きっちんぺーぱー",
    )

    second_item = add_custom_shopping_item(
        db=db_session,
        custom_name="キッチンペーパー",
    )

    assert first_item is not None
    assert second_item is None


@pytest.mark.parametrize(
    "custom_name",
    [
        "",
        "   ",
    ],
)
def test_add_custom_shopping_item_rejects_blank_name(
    db_session: Session,
    custom_name: str,
):
    with pytest.raises(
        ValueError,
        match="名称を入力してください",
    ):
        add_custom_shopping_item(
            db=db_session,
            custom_name=custom_name,
        )


def test_add_custom_shopping_item_rejects_long_name(
    db_session: Session,
):
    with pytest.raises(
        ValueError,
        match="100文字以内",
    ):
        add_custom_shopping_item(
            db=db_session,
            custom_name="あ" * 101,
        )


def test_custom_name_matching_ingredient_is_rejected(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    with pytest.raises(
        ValueError,
        match="食材マスタに登録されています",
    ):
        add_custom_shopping_item(
            db=db_session,
            custom_name="タマゴ",
        )

    assert (
        get_shopping_items(
            db=db_session
        )
        == []
    )


def test_custom_shopping_item_can_be_toggled(
    db_session: Session,
):
    shopping_item = add_custom_shopping_item(
        db=db_session,
        custom_name="食品用ラップ",
    )

    assert shopping_item is not None

    updated_item = toggle_shopping_item(
        db=db_session,
        shopping_item_id=shopping_item.id,
    )

    assert updated_item is not None
    assert updated_item.is_purchased is True
    assert (
        updated_item.display_name
        == "食品用ラップ"
    )


def test_get_shopping_ingredient_candidates_filters_by_category(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    create_ingredient(
        db=db_session,
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
        quantity=2,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    results = (
        get_shopping_ingredient_candidates(
            db=db_session,
            categories=["野菜"],
        )
    )

    assert [
        ingredient.name
        for ingredient in results
    ] == [
        "玉ねぎ",
    ]


def test_get_shopping_ingredient_candidates_searches_by_partial_name(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    create_ingredient(
        db=db_session,
        name="牛乳",
        category="卵・乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    results = (
        get_shopping_ingredient_candidates(
            db=db_session,
            keyword="たま",
        )
    )

    assert [
        ingredient.name
        for ingredient in results
    ] == [
        "たまご",
    ]


def test_get_shopping_ingredient_candidates_supports_kana_difference(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    results = (
        get_shopping_ingredient_candidates(
            db=db_session,
            keyword="タマ",
        )
    )

    assert [
        ingredient.name
        for ingredient in results
    ] == [
        "たまご",
    ]


def test_get_shopping_ingredient_categories(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    create_ingredient(
        db=db_session,
        name="牛乳",
        category="卵・乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    create_ingredient(
        db=db_session,
        name="玉ねぎ",
        category="野菜",
        default_unit="個",
        quantity=2,
        purchase_date=date(
            2026,
            8,
            19,
        ),
    )

    categories = (
        get_shopping_ingredient_categories(
            db=db_session
        )
    )

    assert set(categories) == {
        "卵・乳製品",
        "野菜",
    }


def test_get_shopping_ingredient_candidates_filters_by_multiple_categories(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="キャベツ",
        category="野菜",
        default_unit="玉",
        quantity=1,
        purchase_date=date(2026, 8, 19),
    )

    create_ingredient(
        db=db_session,
        name="牛肉",
        category="肉類",
        default_unit="g",
        quantity=100,
        purchase_date=date(2026, 8, 19),
    )

    create_ingredient(
        db=db_session,
        name="鮭",
        category="魚介類",
        default_unit="切れ",
        quantity=1,
        purchase_date=date(2026, 8, 19),
    )

    results = (
        get_shopping_ingredient_candidates(
            db=db_session,
            categories=[
                "野菜",
                "肉類",
            ],
        )
    )

    assert {
        ingredient.name
        for ingredient in results
    } == {
        "キャベツ",
        "牛肉",
    }