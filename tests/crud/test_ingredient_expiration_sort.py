from datetime import date

from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_filtered_ingredients,
)


def test_expiration_sort_ascending_and_unset_last(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="未設定",
        category="その他",
        default_unit="個",
        quantity=1,
        expiration_date=None,
    )
    create_ingredient(
        db=db_session,
        name="期限が遠い",
        category="食品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 20),
    )
    create_ingredient(
        db=db_session,
        name="期限が近い",
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
        "期限が近い",
        "期限が遠い",
        "未設定",
    ]


def test_expiration_sort_descending_and_unset_last(
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="未設定",
        category="その他",
        default_unit="個",
        quantity=1,
        expiration_date=None,
    )
    create_ingredient(
        db=db_session,
        name="期限が遠い",
        category="食品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 20),
    )
    create_ingredient(
        db=db_session,
        name="期限が近い",
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
        "期限が遠い",
        "期限が近い",
        "未設定",
    ]
