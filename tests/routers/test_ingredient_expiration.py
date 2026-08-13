from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    get_inventory_expiration_date,
)
from app.routers.ingredients import (
    build_expiration_display_by_ingredient_id,
)


def test_expiration_display_statuses(
    db_session: Session,
):
    today = date.today()

    unset = create_ingredient(
        db=db_session,
        name="塩",
        category="調味料",
        default_unit="袋",
        quantity=1,
        expiration_date=None,
    )

    expired = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=(
            today - timedelta(days=1)
        ),
    )

    soon = create_ingredient(
        db=db_session,
        name="卵",
        category="卵・乳製品",
        default_unit="個",
        quantity=1,
        expiration_date=(
            today + timedelta(days=3)
        ),
    )

    normal = create_ingredient(
        db=db_session,
        name="米",
        category="穀類",
        default_unit="kg",
        quantity=1,
        expiration_date=(
            today + timedelta(days=4)
        ),
    )

    result = (
        build_expiration_display_by_ingredient_id(
            [
                unset,
                expired,
                soon,
                normal,
            ]
        )
    )

    assert result[unset.id]["status"] == (
        "unset"
    )
    assert result[expired.id]["status"] == (
        "expired"
    )
    assert result[soon.id]["status"] == (
        "expiring-soon"
    )
    assert result[normal.id]["status"] == (
        "normal"
    )


def test_list_displays_representative_expiration_date(
    client: TestClient,
    db_session: Session,
):
    create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=date(2026, 8, 15),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "消費期限" in response.text
    assert "2026-08-15" in response.text
    assert (
        'class="expiration-date-input"'
        not in response.text
    )


def test_auto_update_expiration_date(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=None,
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date/auto"
        ),
        data={
            "expiration_date": "2026-08-15",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["success"] is True
    assert (
        response_data["expiration_date"]
        == "2026-08-15"
    )

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
        == date(2026, 8, 15)
    )


def test_auto_update_can_clear_date(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="ヨーグルト",
        category="乳製品",
        default_unit="個",
        quantity=1,
        expiration_date=date(2026, 8, 15),
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date/auto"
        ),
        data={
            "expiration_date": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == (
        "unset"
    )

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


def test_auto_update_rejects_invalid_date(
    client: TestClient,
    db_session: Session,
):
    original_date = date(2026, 8, 10)

    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=original_date,
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date/auto"
        ),
        data={
            "expiration_date": "invalid-date",
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
        get_inventory_expiration_date(
            saved_ingredient
        )
        == original_date
    )


def test_auto_update_missing_ingredient(
    client: TestClient,
):
    response = client.post(
        (
            "/ingredients/9999"
            "/expiration-date/auto"
        ),
        data={
            "expiration_date": "2026-08-15",
        },
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_list_displays_nearest_expiration_date_from_multiple_lots(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="卵",
        category="卵",
        default_unit="個",
        quantity=2,
        purchase_date=date(
            2026,
            8,
            1,
        ),
        expiration_date=date(
            2026,
            8,
            20,
        ),
    )

    later_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=3,
        purchase_date=date(
            2026,
            8,
            5,
        ),
        expiration_date=date(
            2026,
            8,
            25,
        ),
    )

    db_session.add(later_lot)
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert "2026-08-20" in response.text


def test_list_ignores_expiration_date_of_empty_lot(
    client: TestClient,
    db_session: Session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="牛肉",
        category="肉類",
        default_unit="g",
        quantity=0,
        purchase_date=date(
            2026,
            8,
            1,
        ),
        expiration_date=date(
            2026,
            8,
            10,
        ),
    )

    active_lot = Inventory(
        ingredient_id=ingredient.id,
        quantity=200,
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

    db_session.add(active_lot)
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert "2026-08-20" in response.text
    assert "2026-08-10" not in response.text