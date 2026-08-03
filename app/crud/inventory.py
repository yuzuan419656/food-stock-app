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