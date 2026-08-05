from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload
from datetime import date

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.utils.ingredient_name import normalize_ingredient_name


def get_ingredients(
    db: Session,
    sort: str = "id",
) -> list[Ingredient]:
    """食材一覧を在庫情報と一緒に取得する。"""
    query = db.query(Ingredient).options(
        joinedload(Ingredient.inventories)
    )

    if sort == "name":
        query = query.order_by(Ingredient.name)

    elif sort == "category":
        query = query.order_by(
            Ingredient.category,
            Ingredient.name,
        )

    else:
        query = query.order_by(Ingredient.id)

    return query.all()


def search_ingredients(
    db: Session,
    keyword: str,
    sort: str = "id",
) -> list[Ingredient]:
    """食材名で部分一致検索する。"""
    query = (
        db.query(Ingredient)
        .options(
            joinedload(Ingredient.inventories)
        )
        .filter(
            Ingredient.name.contains(keyword)
        )
    )

    if sort == "name":
        query = query.order_by(Ingredient.name)

    elif sort == "category":
        query = query.order_by(
            Ingredient.category,
            Ingredient.name,
        )

    else:
        query = query.order_by(Ingredient.id)

    return query.all()


def get_ingredient_by_id(
    db: Session,
    ingredient_id: int,
) -> Ingredient | None:
    """IDを指定して食材と在庫情報を取得する。"""
    return (
        db.query(Ingredient)
        .options(
            joinedload(Ingredient.inventories)
        )
        .filter(
            Ingredient.id == ingredient_id
        )
        .first()
    )


def get_ingredient_by_name(
    db: Session,
    name: str,
    exclude_ingredient_id: int | None = None,
) -> Ingredient | None:
    """
    指定された名前と一致する食材を取得する。

    英字の大文字・小文字は区別しない。

    編集時はexclude_ingredient_idを指定することで、
    編集対象自身を検索結果から除外する。
    """
    normalized_name = normalize_ingredient_name(name)

    query = (
        db.query(Ingredient)
        .options(
            joinedload(Ingredient.inventories)
        )
        .filter(
            func.lower(
                func.trim(Ingredient.name)
            )
            == normalized_name.lower()
        )
    )

    if exclude_ingredient_id is not None:
        query = query.filter(
            Ingredient.id != exclude_ingredient_id
        )

    return query.first()


def create_ingredient(
    db: Session,
    name: str,
    category: str | None = None,
    default_unit: str | None = None,
    quantity: float = 0,
    expiration_date: date | None = None,
) -> Ingredient:
    """食材と在庫情報を登録する。"""
    ingredient = Ingredient(
        name=name,
        category=category,
        default_unit=default_unit,
    )

    db.add(ingredient)

    # ingredient.idを確定させるため、
    # commit前にINSERTを実行する。
    db.flush()

    inventory = Inventory(
        ingredient_id=ingredient.id,
        quantity=quantity,
        expiration_date=expiration_date,
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
    expiration_date: date | None = None,
) -> Ingredient | None:
    """食材情報・在庫数量・消費期限を更新する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    ingredient.name = name
    ingredient.category = category
    ingredient.default_unit = default_unit

    if ingredient.inventories:
        inventory = ingredient.inventories[0]
        inventory.quantity = quantity
        inventory.expiration_date = expiration_date

    else:
        inventory = Inventory(
            ingredient_id=ingredient.id,
            quantity=quantity,
            expiration_date=expiration_date,
        )

        db.add(inventory)

    db.commit()
    db.refresh(ingredient)

    return ingredient


def delete_ingredient(
    db: Session,
    ingredient_id: int,
) -> bool:
    """指定した食材を削除する。"""
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return False

    db.delete(ingredient)
    db.commit()

    return True


def get_categories(
    db: Session,
) -> list[str]:
    """登録済み食材からカテゴリ一覧を取得する。"""
    results = (
        db.query(Ingredient.category)
        .filter(
            Ingredient.category.isnot(None)
        )
        .filter(
            Ingredient.category != ""
        )
        .distinct()
        .order_by(Ingredient.category)
        .all()
    )

    return [
        result[0]
        for result in results
    ]


def get_default_units(
    db: Session,
) -> list[str]:
    """登録済み食材から単位一覧を取得する。"""
    results = (
        db.query(Ingredient.default_unit)
        .filter(
            Ingredient.default_unit.isnot(None)
        )
        .filter(
            Ingredient.default_unit != ""
        )
        .distinct()
        .order_by(Ingredient.default_unit)
        .all()
    )

    return [
        result[0]
        for result in results
    ]


def get_filtered_ingredients(
    db: Session,
    keyword: str | None = None,
    category_filters: list[str] | None = None,
    sort: str = "id",
    out_of_stock_first: bool = False,
) -> list[Ingredient]:
    """
    検索・絞り込み・並び替え条件付きで
    食材一覧を取得する。
    """
    query = db.query(Ingredient).options(
        joinedload(Ingredient.inventories)
    )

    if keyword:
        query = query.filter(
            Ingredient.name.contains(keyword)
        )

    if category_filters:
        query = query.filter(
            Ingredient.category.in_(
                category_filters
            )
        )

    order_conditions = []

    needs_inventory_join = (
        out_of_stock_first
        or sort in [
            "expiration_asc",
            "expiration_desc",
        ]
    )

    if needs_inventory_join:
        query = query.outerjoin(Inventory)

    if out_of_stock_first:
        order_conditions.append(
            case(
                (
                    (
                        Inventory.quantity.is_(None)
                    )
                    | (
                        Inventory.quantity <= 0
                    ),
                    0,
                ),
                else_=1,
            )
        )

    if sort == "name":
        order_conditions.append(
            Ingredient.name
        )

    elif sort == "category":
        order_conditions.extend(
            [
                Ingredient.category,
                Ingredient.name,
            ]
        )

    elif sort == "expiration_asc":
        # 消費期限未設定を最後にする。
        order_conditions.extend(
            [
                case(
                    (
                        Inventory.expiration_date.is_(
                            None
                        ),
                        1,
                    ),
                    else_=0,
                ),
                Inventory.expiration_date.asc(),
                Ingredient.name,
            ]
        )

    elif sort == "expiration_desc":
        # 消費期限未設定を最後にする。
        order_conditions.extend(
            [
                case(
                    (
                        Inventory.expiration_date.is_(
                            None
                        ),
                        1,
                    ),
                    else_=0,
                ),
                Inventory.expiration_date.desc(),
                Ingredient.name,
            ]
        )

    else:
        order_conditions.append(
            Ingredient.id
        )

    query = query.order_by(
        *order_conditions
    )

    return query.all()