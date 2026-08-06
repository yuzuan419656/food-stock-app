from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    get_inventory_purchase_date,
    update_inventory_purchase_date,
)


def test_create_ingredient_saves_purchase_date(
    db_session: Session,
):
    purchase_date = date(2026, 8, 5)

    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=purchase_date,
    )

    assert (
        get_inventory_purchase_date(
            ingredient
        )
        == purchase_date
    )


def test_update_inventory_purchase_date(
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="卵",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
        purchase_date=date(2026, 8, 1),
    )

    updated_ingredient = (
        update_inventory_purchase_date(
            db=db_session,
            ingredient_id=ingredient.id,
            purchase_date=date(2026, 8, 6),
        )
    )

    assert updated_ingredient is not None
    assert (
        get_inventory_purchase_date(
            updated_ingredient
        )
        == date(2026, 8, 6)
    )


def test_auto_update_purchase_date(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="ヨーグルト",
        category="乳製品",
        default_unit="個",
        quantity=1,
        purchase_date=date(2026, 8, 1),
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/purchase-date/auto"
        ),
        data={
            "purchase_date": "2026-08-06",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["success"] is True
    assert (
        response_data["purchase_date"]
        == "2026-08-06"
    )

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert (
        get_inventory_purchase_date(
            saved_ingredient
        )
        == date(2026, 8, 6)
    )


def test_auto_update_purchase_date_rejects_empty_value(
    client: TestClient,
    db_session: Session,
):
    original_date = date(2026, 8, 1)

    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        purchase_date=original_date,
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/purchase-date/auto"
        ),
        data={
            "purchase_date": "",
        },
    )

    assert response.status_code == 400
    assert response.json()["success"] is False

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert (
        get_inventory_purchase_date(
            saved_ingredient
        )
        == original_date
    )