from datetime import date

import pytest

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory


def test_decrement_consumes_earliest_expiration_lot(
    client,
    db_session,
):
    ingredient = Ingredient(
        name="卵",
        category="卵",
        default_unit="個",
    )

    db_session.add(ingredient)
    db_session.flush()

    later_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=2.0,
        purchase_date=date(
            2026,
            8,
            10,
        ),
        expiration_date=date(
            2026,
            8,
            25,
        ),
    )

    earlier_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=1.0,
        purchase_date=date(
            2026,
            8,
            5,
        ),
        expiration_date=date(
            2026,
            8,
            20,
        ),
    )

    # 登録順に依存せず、期限によって
    # 消費対象が選ばれることを確認するため、
    # 期限が遠いロットを先に追加する。
    db_session.add_all(
        [
            later_lot,
            earlier_lot,
        ]
    )
    db_session.commit()

    response = client.post(
        (
            f"/ingredients/"
            f"{ingredient.id}/decrement"
        ),
        data={
            "sort": "expiration_asc",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/?sort=expiration_asc"
    )

    db_session.refresh(earlier_lot)
    db_session.refresh(later_lot)

    assert earlier_lot.quantity == pytest.approx(
        0.5
    )
    assert later_lot.quantity == pytest.approx(
        2.0
    )


def test_decrement_does_not_make_stock_negative(
    client,
    db_session,
):
    ingredient = Ingredient(
        name="牛乳",
        category="乳製品",
        default_unit="L",
    )

    db_session.add(ingredient)
    db_session.flush()

    inventory = Inventory(
        ingredient_id=ingredient.id,
        quantity=0.25,
        purchase_date=date(
            2026,
            8,
            10,
        ),
        expiration_date=date(
            2026,
            8,
            20,
        ),
    )

    db_session.add(inventory)
    db_session.commit()

    response = client.post(
        (
            f"/ingredients/"
            f"{ingredient.id}/decrement"
        ),
        data={
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.refresh(inventory)

    # 0.5の減算要求に対して在庫が0.25だけなので、
    # 存在する0.25だけを消費する。
    assert inventory.quantity == pytest.approx(
        0.0
    )


def test_decrement_empty_stock_keeps_zero(
    client,
    db_session,
):
    ingredient = Ingredient(
        name="キャベツ",
        category="野菜",
        default_unit="玉",
    )

    db_session.add(ingredient)
    db_session.flush()

    inventory = Inventory(
        ingredient_id=ingredient.id,
        quantity=0.0,
        purchase_date=date(
            2026,
            8,
            10,
        ),
        expiration_date=date(
            2026,
            8,
            20,
        ),
    )

    db_session.add(inventory)
    db_session.commit()

    response = client.post(
        (
            f"/ingredients/"
            f"{ingredient.id}/decrement"
        ),
        data={
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.refresh(inventory)

    assert inventory.quantity == pytest.approx(
        0.0
    )