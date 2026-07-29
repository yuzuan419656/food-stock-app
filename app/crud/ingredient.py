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

def search_ingredients(db: Session, keyword: str) -> list[Ingredient]:
    """食材名で部分一致検索する。"""
    return (
        db.query(Ingredient)
        .options(joinedload(Ingredient.inventories))
        .filter(Ingredient.name.contains(keyword))
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

def get_categories(db: Session) -> list[str]:
    """登録済み食材からカテゴリ一覧を取得する。"""
    results = (
        db.query(Ingredient.category)
        .filter(Ingredient.category.isnot(None))
        .filter(Ingredient.category != "")
        .distinct()
        .order_by(Ingredient.category)
        .all()
    )

    return [result[0] for result in results]


def get_default_units(db: Session) -> list[str]:
    """登録済み食材から単位一覧を取得する。"""
    results = (
        db.query(Ingredient.default_unit)
        .filter(Ingredient.default_unit.isnot(None))
        .filter(Ingredient.default_unit != "")
        .distinct()
        .order_by(Ingredient.default_unit)
        .all()
    )

    return [result[0] for result in results]