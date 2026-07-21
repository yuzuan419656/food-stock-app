from sqlalchemy.orm import Session, joinedload

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory


def get_ingredients(db: Session)-> list[Ingredient]:
    return (
        db.query(Ingredient)
        .options(joinedload(Ingredient.inventories))
        .order_by(Ingredient.id)
        .all()
        )
        
def get_ingredient_by_id(db: Session, ingredient_id: int)-> Ingredient | None:
    return(
        db.query(Ingredient)
        .options(joinedload(Ingredient.inventories))
        .filter(Ingredient.id == ingredient_id)
        .first()
    )

def get_ingredient_by_name(db: Session, name: str)-> Ingredient | None:
    return(
        db.query(Ingredient)
        .filter(Ingredient.name == name)
        .first()
    )

def create_ingredient(
    db: Session,
    name: str,
    category: str | None = None,
    default_unit: str | None = None,
    quantity: float = 0,
) -> Ingredient:
    """食材と在庫情報を登録する。"""
    ingredient = Ingredient(
        name=name,
        category=category,
        default_unit=default_unit,
    )

    db.add(ingredient)
    db.flush()

    inventory = Inventory(
        ingredient_id=ingredient.id,
        quantity=quantity,
    )

    db.add(inventory)
    db.commit()
    db.refresh(ingredient)

    return ingredient

def update_ingredient(
        db: Session,
        ingredient_id: int,
        name: str | None = None,
        category: str | None = None,
        default_unit: str | None = None,
        quantity: float | None = None,
) -> Ingredient | None:
    ingredient = get_ingredient_by_id(db, ingredient_id)
    if ingredient is None:
        return None
    
    ingredient.name = name
    ingredient.category = category
    ingredient.default_unit = default_unit

    if ingredient.inventories:
        ingredient.inventories[0].quantity = quantity
    else:
        inventory = Inventory(
            ingredient_id=ingredient.id,
            quantity=quantity,
        )
        db.add(inventory)

    db.commit()
    db.refresh(ingredient)

    return ingredient

def delete_ingredient(db: Session, ingredient_id: int) -> bool:
    ingredient = get_ingredient_by_id(db, ingredient_id)
    if ingredient is None:
        return False
    
    db.delete(ingredient)
    db.commit()
    return True
