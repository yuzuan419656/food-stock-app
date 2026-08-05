from datetime import date

from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_filtered_ingredients,
)


def test_sort_by_expiration_date_ascending(
    db_session: Session,
):
    """消費期限が近い順に並べられる。"""
    create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=date(2026, 8, 10),
    )

    create_ingredient(
        db=db_session,
        name="卵",
        category="食品",
        default_unit="個",
        quantity=6,
        expiration_date=date(2026, 8, 8),
    )

    create_ingredient(
        db=db_session,
        name="チーズ",
        category="乳製品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 20),
    )

    ingredients = get_filtered_ingredients(
        db=db_session,
        sort="expiration_asc",
    )

    assert [
        ingredient.name
        for ingredient in ingredients
    ] == [
        "卵",
        "牛乳",
        "チーズ",
    ]


def test_sort_by_expiration_date_descending(
    db_session: Session,
):
    """消費期限が遠い順に並べられる。"""
    create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=date(2026, 8, 10),
    )

    create_ingredient(
        db=db_session,
        name="卵",
        category="食品",
        default_unit="個",
        quantity=6,
        expiration_date=date(2026, 8, 8),
    )

    create_ingredient(
        db=db_session,
        name="チーズ",
        category="乳製品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 20),
    )

    ingredients = get_filtered_ingredients(
        db=db_session,
        sort="expiration_desc",
    )

    assert [
        ingredient.name
        for ingredient in ingredients
    ] == [
        "チーズ",
        "牛乳",
        "卵",
    ]


def test_expiration_date_unset_is_last_when_ascending(
    db_session: Session,
):
    """近い順でも期限未設定は最後になる。"""
    create_ingredient(
        db=db_session,
        name="期限なし",
        category="その他",
        default_unit="個",
        quantity=1,
        expiration_date=None,
    )

    create_ingredient(
        db=db_session,
        name="期限あり",
        category="食品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 10),
    )

    ingredients = get_filtered_ingredients(
        db=db_session,
        sort="expiration_asc",
    )

    assert [
        ingredient.name
        for ingredient in ingredients
    ] == [
        "期限あり",
        "期限なし",
    ]


def test_expiration_date_unset_is_last_when_descending(
    db_session: Session,
):
    """遠い順でも期限未設定は最後になる。"""
    create_ingredient(
        db=db_session,
        name="期限なし",
        category="その他",
        default_unit="個",
        quantity=1,
        expiration_date=None,
    )

    create_ingredient(
        db=db_session,
        name="期限あり",
        category="食品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 10),
    )

    ingredients = get_filtered_ingredients(
        db=db_session,
        sort="expiration_desc",
    )

    assert [
        ingredient.name
        for ingredient in ingredients
    ] == [
        "期限あり",
        "期限なし",
    ]