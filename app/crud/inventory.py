from datetime import date

from sqlalchemy.orm import Session, joinedload

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


def get_inventory_purchase_date(
    ingredient: Ingredient,
) -> date:
    """食材の現在庫に設定された購入日を取得する。"""
    if not ingredient.inventories:
        return date.today()

    purchase_date = (
        ingredient.inventories[0].purchase_date
    )

    if purchase_date is None:
        return date.today()

    return purchase_date


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


def get_earlier_purchase_date(
    current_purchase_date: date | None,
    new_purchase_date: date | None,
) -> date:
    """
    2つの購入日から早い方を返す。

    片方が未設定の場合は、
    設定されている方を使用する。
    両方未設定の場合は当日を返す。
    """
    if current_purchase_date is None:
        return new_purchase_date or date.today()

    if new_purchase_date is None:
        return current_purchase_date

    return min(
        current_purchase_date,
        new_purchase_date,
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
            purchase_date=date.today(),
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
    purchase_date: date,
    expiration_date: date | None,
) -> Ingredient | None:
    """
    指定した食材の在庫数量を加算する。

    購入日は、既存分と追加分を比較し、
    早い方を代表購入日として保存する。

    消費期限も、既存期限と追加分を比較し、
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
            purchase_date=purchase_date,
            expiration_date=None,
        )

        db.add(inventory)

    current_quantity = float(
        inventory.quantity or 0
    )

    inventory.quantity = current_quantity + amount

    inventory.purchase_date = (
        get_earlier_purchase_date(
            current_purchase_date=(
                inventory.purchase_date
            ),
            new_purchase_date=purchase_date,
        )
    )

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
            purchase_date=date.today(),
            expiration_date=expiration_date,
        )

        db.add(inventory)

    db.commit()
    db.refresh(ingredient)

    return ingredient


def update_inventory_purchase_date(
    db: Session,
    ingredient_id: int,
    purchase_date: date,
) -> Ingredient | None:
    """指定した食材の購入日だけを更新する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    if ingredient.inventories:
        inventory = ingredient.inventories[0]
        inventory.purchase_date = purchase_date

    else:
        inventory = Inventory(
            ingredient_id=ingredient.id,
            quantity=0,
            purchase_date=purchase_date,
            expiration_date=None,
        )

        db.add(inventory)

    db.commit()
    db.refresh(ingredient)

    return ingredient


def update_inventory_expiration_dates(
    db: Session,
    expiration_updates: list[
        tuple[int, date | None]
    ],
) -> int:
    """
    複数の食材の消費期限を一括更新する。

    すべての更新に成功した場合だけcommitする。
    """
    if not expiration_updates:
        return 0

    ingredient_ids = [
        ingredient_id
        for ingredient_id, _ in expiration_updates
    ]

    ingredients = (
        db.query(Ingredient)
        .options(
            joinedload(Ingredient.inventories)
        )
        .filter(
            Ingredient.id.in_(ingredient_ids)
        )
        .all()
    )

    ingredient_by_id = {
        ingredient.id: ingredient
        for ingredient in ingredients
    }

    missing_ingredient_ids = [
        ingredient_id
        for ingredient_id in ingredient_ids
        if ingredient_id not in ingredient_by_id
    ]

    if missing_ingredient_ids:
        raise ValueError(
            "更新対象の食材が見つかりません。"
        )

    try:
        for (
            ingredient_id,
            expiration_date,
        ) in expiration_updates:
            ingredient = ingredient_by_id[
                ingredient_id
            ]

            if ingredient.inventories:
                inventory = (
                    ingredient.inventories[0]
                )

                inventory.expiration_date = (
                    expiration_date
                )

            else:
                inventory = Inventory(
                    ingredient_id=ingredient.id,
                    quantity=0,
                    purchase_date=date.today(),
                    expiration_date=(
                        expiration_date
                    ),
                )

                db.add(inventory)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return len(expiration_updates)