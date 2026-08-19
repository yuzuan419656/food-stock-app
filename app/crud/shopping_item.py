from sqlalchemy.orm import Session, joinedload

from app.models.ingredient import Ingredient
from app.models.shopping_item import ShoppingItem
from app.utils.ingredient_name import (
    normalize_ingredient_name,
    create_search_keywords,
)


def _shopping_item_names_match(
    first_name: str,
    second_name: str,
) -> bool:
    """
    2つの名称が検索上同じものか判定する。

    既存の食材検索と同じく、
    ひらがな・カタカナの違いも吸収する。
    """
    first_keywords = set(
        create_search_keywords(
            first_name
        )
    )

    second_keywords = set(
        create_search_keywords(
            second_name
        )
    )

    return bool(
        first_keywords
        & second_keywords
    )

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


def add_custom_shopping_item(
    db: Session,
    custom_name: str,
) -> ShoppingItem | None:
    """
    手入力項目を買うものリストへ追加する。

    戻り値:
    - 追加成功: 作成したShoppingItem
    - 同じ手入力項目が存在する: None

    食材マスタと同名の場合や空文字の場合は
    ValueErrorを送出する。
    """
    cleaned_name = custom_name.strip()

    if not cleaned_name:
        raise ValueError(
            "名称を入力してください。"
        )

    if len(cleaned_name) > 100:
        raise ValueError(
            "名称は100文字以内で入力してください。"
        )

    ingredients = (
        db.query(Ingredient)
        .all()
    )

    matching_ingredient = next(
        (
            ingredient
            for ingredient in ingredients
            if _shopping_item_names_match(
                ingredient.name,
                cleaned_name,
            )
        ),
        None,
    )

    if matching_ingredient is not None:
        raise ValueError(
            "同じ名称の食材が"
            "食材マスタに登録されています。"
            "登録済み食材から選択してください。"
        )

    existing_custom_items = (
        db.query(ShoppingItem)
        .filter(
            ShoppingItem.custom_name.is_not(
                None
            )
        )
        .all()
    )

    duplicate_item = next(
        (
            shopping_item
            for shopping_item
            in existing_custom_items
            if _shopping_item_names_match(
                shopping_item.custom_name or "",
                cleaned_name,
            )
        ),
        None,
    )

    if duplicate_item is not None:
        return None

    shopping_item = ShoppingItem(
        ingredient_id=None,
        custom_name=cleaned_name,
        is_purchased=False,
    )

    db.add(shopping_item)
    db.commit()
    db.refresh(shopping_item)

    return shopping_item


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


def _shopping_item_name_contains(
    ingredient_name: str,
    keyword: str,
) -> bool:
    """
    食材名に検索キーワードが含まれるか判定する。

    ひらがな・カタカナの違いも吸収する。
    """
    cleaned_keyword = keyword.strip()

    if not cleaned_keyword:
        return True

    name_keywords = create_search_keywords(
        ingredient_name
    )

    search_keywords = create_search_keywords(
        cleaned_keyword
    )

    return any(
        search_keyword in name_keyword
        for name_keyword in name_keywords
        for search_keyword in search_keywords
    )


def get_shopping_ingredient_candidates(
    db: Session,
    keyword: str = "",
    categories: list[str] | None = None,
    limit: int = 50,
) -> list[Ingredient]:
    """
    買うものリストへ追加する食材候補を取得する。

    複数カテゴリはOR条件、
    食材名は仮名を考慮した部分一致で検索する。
    """
    query = db.query(Ingredient)

    cleaned_categories = {
        category.strip()
        for category in (categories or [])
        if category.strip()
    }

    if cleaned_categories:
        query = query.filter(
            Ingredient.category.in_(
                cleaned_categories
            )
        )

    ingredients = (
        query
        .order_by(
            Ingredient.category.asc(),
            Ingredient.name.asc(),
            Ingredient.id.asc(),
        )
        .all()
    )

    cleaned_keyword = keyword.strip()

    if cleaned_keyword:
        ingredients = [
            ingredient
            for ingredient in ingredients
            if _shopping_item_name_contains(
                ingredient.name,
                cleaned_keyword,
            )
        ]

    return ingredients[:limit]


def get_shopping_ingredient_categories(
    db: Session,
) -> list[str]:
    """
    買うものリストの食材検索に使用する
    カテゴリ一覧を取得する。
    """
    rows = (
        db.query(Ingredient.category)
        .filter(
            Ingredient.category.is_not(None),
            Ingredient.category != "",
        )
        .distinct()
        .order_by(
            Ingredient.category.asc()
        )
        .all()
    )

    return [
        category
        for (category,) in rows
    ]