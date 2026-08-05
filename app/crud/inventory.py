from datetime import date

from sqlalchemy.orm import Session

from app.crud.ingredient import get_ingredient_by_id
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory


def get_inventory_quantity(
    ingredient: Ingredient,
) -> float:
    """食材の現在庫数量を取得する。"""
    if not ingredient.inventories:
        return 0.0

    quantity = ingredient.inventories[0].quantity

    if quantity is None:
        return 0.0

    return float(quantity)


def get_inventory_expiration_date(
    ingredient: Ingredient,
) -> date | None:
    """食材の現在庫に設定された消費期限を取得する。"""
    if not ingredient.inventories:
        return None

    return ingredient.inventories[0].expiration_date


def get_earlier_expiration_date(
    current_expiration_date: date | None,
    new_expiration_date: date | None,
) -> date | None:
    """
    2つの消費期限から早い方を返す。

    片方が未設定の場合は、
    設定されている方を使用する。
    """
    if current_expiration_date is None:
        return new_expiration_date

    if new_expiration_date is None:
        return current_expiration_date

    return min(
        current_expiration_date,
        new_expiration_date,
    )


def change_inventory_quantity(
    db: Session,
    ingredient_id: int,
    amount: float,
) -> Ingredient | None:
    """指定した食材の在庫数量を増減する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    if ingredient.inventories:
        inventory = ingredient.inventories[0]

    else:
        inventory = Inventory(
            ingredient_id=ingredient.id,
            quantity=0,
            expiration_date=None,
        )
        db.add(inventory)

    current_quantity = float(
        inventory.quantity or 0
    )

    new_quantity = current_quantity + amount

    inventory.quantity = max(
        0,
        new_quantity,
    )

    db.commit()
    db.refresh(ingredient)

    return ingredient


def add_inventory_quantity(
    db: Session,
    ingredient_id: int,
    amount: float,
    expiration_date: date | None,
) -> Ingredient | None:
    """
    指定した食材の在庫数量を加算する。

    消費期限は、既存期限と追加分の期限を比較し、
    早い方を代表期限として保存する。
    """
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    if ingredient.inventories:
        inventory = ingredient.inventories[0]

    else:
        inventory = Inventory(
            ingredient_id=ingredient.id,
            quantity=0,
            expiration_date=None,
        )
        db.add(inventory)

    current_quantity = float(
        inventory.quantity or 0
    )

    inventory.quantity = current_quantity + amount

    inventory.expiration_date = (
        get_earlier_expiration_date(
            current_expiration_date=(
                inventory.expiration_date
            ),
            new_expiration_date=expiration_date,
        )
    )

    db.commit()
    db.refresh(ingredient)

    return ingredient


def update_inventory_expiration_date(
    db: Session,
    ingredient_id: int,
    expiration_date: date | None,
) -> Ingredient | None:
    """指定した食材の消費期限だけを更新する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    if ingredient.inventories:
        inventory = ingredient.inventories[0]
        inventory.expiration_date = expiration_date

    else:
        inventory = Inventory(
            ingredient_id=ingredient.id,
            quantity=0,
            expiration_date=expiration_date,
        )

        db.add(inventory)

    db.commit()
    db.refresh(ingredient)

    return ingredient