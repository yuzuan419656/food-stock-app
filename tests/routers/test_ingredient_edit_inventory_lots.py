from datetime import date

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    create_inventory_lot,
)

from app.models.inventory import Inventory


def test_edit_page_displays_inventory_lots(
    client,
    db_session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
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

    create_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        quantity=8,
        purchase_date=date(
            2026,
            8,
            5,
        ),
        expiration_date=date(
            2026,
            8,
            15,
        ),
    )

    response = client.get(
        f"/ingredients/{ingredient.id}/edit"
    )

    assert response.status_code == 200
    assert "在庫ロット" in response.text
    assert "合計在庫" in response.text
    assert "14" in response.text
    assert "2026-08-01" in response.text
    assert "2026-08-05" in response.text
    assert "2026-08-10" in response.text
    assert "2026-08-15" in response.text
    assert "新しいロットを追加" in (
        response.text
    )


def test_basic_info_update_does_not_change_inventory_lots(
    client,
    db_session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="たまご",
        category="卵・乳製品",
        default_unit="個",
        quantity=6,
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

    original_inventory = (
        ingredient.inventories[0]
    )

    original_inventory_id = (
        original_inventory.id
    )

    response = client.post(
        f"/ingredients/{ingredient.id}/edit",
        data={
            "name": "卵",
            "category_select": "卵",
            "category_other": "",
            "default_unit_select": "個",
            "default_unit_other": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.expire_all()

    updated_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert updated_ingredient is not None
    assert updated_ingredient.name == "卵"

    updated_inventory = db_session.get(
        type(original_inventory),
        original_inventory_id,
    )

    assert updated_inventory is not None
    assert updated_inventory.quantity == 6
    assert (
        updated_inventory.purchase_date
        == date(2026, 8, 1)
    )
    assert (
        updated_inventory.expiration_date
        == date(2026, 8, 10)
    )


def test_update_inventory_lot_route_updates_only_selected_lot(
    client,
    db_session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="たまご",
        category="卵",
        default_unit="個",
        quantity=6,
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

    first_lot_id = (
        ingredient.inventories[0].id
    )

    second_lot = create_inventory_lot(
        db=db_session,
        ingredient_id=ingredient.id,
        quantity=8,
        purchase_date=date(
            2026,
            8,
            5,
        ),
        expiration_date=date(
            2026,
            8,
            15,
        ),
    )

    response = client.post(
        (
            f"/inventories/"
            f"{second_lot.id}/edit"
        ),
        data={
            "quantity": "7.5",
            "purchase_date": "2026-08-06",
            "expiration_date": "2026-08-20",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        f"/ingredients/{ingredient.id}/edit"
        in response.headers["location"]
    )

    db_session.expire_all()

    first_lot = db_session.get(
        Inventory,
        first_lot_id,
    )

    updated_second_lot = db_session.get(
        Inventory,
        second_lot.id,
    )

    assert first_lot is not None
    assert updated_second_lot is not None

    assert first_lot.quantity == 6
    assert (
        first_lot.purchase_date
        == date(2026, 8, 1)
    )

    assert (
        updated_second_lot.quantity
        == 7.5
    )

    assert (
        updated_second_lot.purchase_date
        == date(2026, 8, 6)
    )

    assert (
        updated_second_lot.expiration_date
        == date(2026, 8, 20)
    )


def test_update_inventory_lot_route_rejects_invalid_step(
    client,
    db_session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="たまご",
        category="卵",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            1,
        ),
    )

    inventory_id = (
        ingredient.inventories[0].id
    )

    response = client.post(
        f"/inventories/{inventory_id}/edit",
        data={
            "quantity": "6.3",
            "purchase_date": "2026-08-01",
            "expiration_date": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "lot_error=" in (
        response.headers["location"]
    )

    db_session.expire_all()

    inventory = db_session.get(
        Inventory,
        inventory_id,
    )

    assert inventory is not None
    assert inventory.quantity == 6


def test_delete_inventory_lot_route_soft_deletes_lot(
    client,
    db_session,
):
    ingredient = create_ingredient(
        db=db_session,
        name="たまご",
        category="卵",
        default_unit="個",
        quantity=6,
        purchase_date=date(
            2026,
            8,
            1,
        ),
    )

    inventory_id = (
        ingredient.inventories[0].id
    )

    response = client.post(
        (
            f"/inventories/"
            f"{inventory_id}/delete"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        f"/ingredients/{ingredient.id}/edit"
        in response.headers["location"]
    )

    db_session.expire_all()

    inventory = db_session.get(
        Inventory,
        inventory_id,
    )

    assert inventory is not None
    assert inventory.deleted_at is not None