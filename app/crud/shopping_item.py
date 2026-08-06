from sqlalchemy.orm import Session, joinedload

from app.models.ingredient import Ingredient
from app.models.shopping_item import ShoppingItem


def get_shopping_items(
    db: Session,
) -> list[ShoppingItem]:
    """買うものリストを取得する。"""
    return (
        db.query(ShoppingItem)
        .options(
            joinedload(
                ShoppingItem.ingredient
            )
        )
        .order_by(
            ShoppingItem.is_purchased.asc(),
            ShoppingItem.created_at.asc(),
        )
        .all()
    )


def get_shopping_item_by_id(
    db: Session,
    shopping_item_id: int,
) -> ShoppingItem | None:
    """買うものリスト項目をIDで取得する。"""
    return (
        db.query(ShoppingItem)
        .filter(
            ShoppingItem.id
            == shopping_item_id
        )
        .first()
    )


def add_ingredients_to_shopping_list(
    db: Session,
    ingredient_ids: list[int],
) -> int:
    """
    複数の食材を買うものリストへ追加する。

    すでに追加済みの食材は重複登録しない。
    戻り値は新しく追加した件数。
    """
    unique_ingredient_ids = set(
        ingredient_ids
    )

    if not unique_ingredient_ids:
        return 0

    existing_ingredient_ids = {
        ingredient_id
        for (ingredient_id,) in (
            db.query(
                Ingredient.id
            )
            .filter(
                Ingredient.id.in_(
                    unique_ingredient_ids
                )
            )
            .all()
        )
    }

    registered_ingredient_ids = {
        ingredient_id
        for (ingredient_id,) in (
            db.query(
                ShoppingItem.ingredient_id
            )
            .filter(
                ShoppingItem.ingredient_id.in_(
                    existing_ingredient_ids
                )
            )
            .all()
        )
    }

    new_ingredient_ids = (
        existing_ingredient_ids
        - registered_ingredient_ids
    )

    for ingredient_id in new_ingredient_ids:
        db.add(
            ShoppingItem(
                ingredient_id=ingredient_id,
                is_purchased=False,
            )
        )

    db.commit()

    return len(new_ingredient_ids)


def toggle_shopping_item(
    db: Session,
    shopping_item_id: int,
) -> ShoppingItem | None:
    """未購入・購入済みを切り替える。"""
    shopping_item = (
        get_shopping_item_by_id(
            db=db,
            shopping_item_id=shopping_item_id,
        )
    )

    if shopping_item is None:
        return None

    shopping_item.is_purchased = (
        not shopping_item.is_purchased
    )

    db.commit()
    db.refresh(shopping_item)

    return shopping_item


def delete_shopping_item(
    db: Session,
    shopping_item_id: int,
) -> bool:
    """買うものリスト項目を1件削除する。"""
    shopping_item = (
        get_shopping_item_by_id(
            db=db,
            shopping_item_id=shopping_item_id,
        )
    )

    if shopping_item is None:
        return False

    db.delete(shopping_item)
    db.commit()

    return True


def delete_purchased_shopping_items(
    db: Session,
) -> int:
    """購入済み項目をすべて削除する。"""
    deleted_count = (
        db.query(ShoppingItem)
        .filter(
            ShoppingItem.is_purchased.is_(
                True
            )
        )
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return deleted_count