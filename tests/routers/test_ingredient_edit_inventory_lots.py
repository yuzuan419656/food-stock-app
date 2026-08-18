from datetime import date

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    create_inventory_lot,
)


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