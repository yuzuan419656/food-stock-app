from datetime import date

from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    get_inventory_expiration_date,
    get_inventory_quantity,
    update_inventory_expiration_date,
)


def test_update_inventory_expiration_date(
    db_session: Session,
):
    """既存の消費期限を別の日付へ更新できる。"""
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=2,
        expiration_date=date(2026, 8, 10),
    )

    updated_ingredient = (
        update_inventory_expiration_date(
            db=db_session,
            ingredient_id=ingredient.id,
            expiration_date=date(2026, 8, 15),
        )
    )

    assert updated_ingredient is not None

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert get_inventory_expiration_date(
        saved_ingredient
    ) == date(2026, 8, 15)


def test_clear_inventory_expiration_date(
    db_session: Session,
):
    """消費期限をNoneへ戻せる。"""
    ingredient = create_ingredient(
        db=db_session,
        name="ヨーグルト",
        category="乳製品",
        default_unit="個",
        quantity=3,
        expiration_date=date(2026, 8, 12),
    )

    updated_ingredient = (
        update_inventory_expiration_date(
            db=db_session,
            ingredient_id=ingredient.id,
            expiration_date=None,
        )
    )

    assert updated_ingredient is not None

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert (
        get_inventory_expiration_date(
            saved_ingredient
        )
        is None
    )


def test_update_expiration_date_does_not_change_quantity(
    db_session: Session,
):
    """期限更新時に数量が変わらない。"""
    ingredient = create_ingredient(
        db=db_session,
        name="卵",
        category="食品",
        default_unit="個",
        quantity=6,
        expiration_date=date(2026, 8, 8),
    )

    update_inventory_expiration_date(
        db=db_session,
        ingredient_id=ingredient.id,
        expiration_date=date(2026, 8, 20),
    )

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert get_inventory_quantity(
        saved_ingredient
    ) == 6
    assert get_inventory_expiration_date(
        saved_ingredient
    ) == date(2026, 8, 20)


def test_update_expiration_date_does_not_change_ingredient(
    db_session: Session,
):
    """期限更新時に食材情報が変わらない。"""
    ingredient = create_ingredient(
        db=db_session,
        name="豆腐",
        category="大豆製品",
        default_unit="丁",
        quantity=1,
        expiration_date=None,
    )

    update_inventory_expiration_date(
        db=db_session,
        ingredient_id=ingredient.id,
        expiration_date=date(2026, 8, 9),
    )

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert saved_ingredient.name == "豆腐"
    assert saved_ingredient.category == "大豆製品"
    assert saved_ingredient.default_unit == "丁"
    assert get_inventory_quantity(
        saved_ingredient
    ) == 1


def test_update_expiration_date_for_missing_ingredient(
    db_session: Session,
):
    """存在しない食材IDではNoneを返す。"""
    result = update_inventory_expiration_date(
        db=db_session,
        ingredient_id=9999,
        expiration_date=date(2026, 8, 10),
    )

    assert result is None
    