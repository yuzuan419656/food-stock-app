from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload

from app.crud.ingredient import get_ingredient_by_id
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.utils.quantity import (
    is_valid_quantity_step,
)



@dataclass(frozen=True)
class LotAllocation:
    """1つの在庫ロットから消費した数量。"""

    inventory_id: int
    quantity: float


@dataclass(frozen=True)
class InventoryConsumptionResult:
    """在庫ロットの減算結果。"""

    requested_quantity: float
    consumed_quantity: float
    shortage_quantity: float
    allocations: tuple[LotAllocation, ...]


def sort_inventory_lots_for_consumption(
    inventories: list[Inventory],
) -> list[Inventory]:
    """
    在庫ロットを消費する優先順に並べる。

    優先順位:
    1. 消費期限が設定されている
    2. 消費期限が早い
    3. 購入日が古い
    4. 登録日時が古い
    5. IDが小さい
    """
    return sorted(
        inventories,
        key=lambda inventory: (
            inventory.expiration_date is None,
            (
                inventory.expiration_date
                or date.max
            ),
            (
                inventory.purchase_date
                or date.max
            ),
            inventory.created_at,
            inventory.id,
        ),
    )


def consume_inventory_quantity(
    db: Session,
    ingredient_id: int,
    amount: float,
) -> InventoryConsumptionResult | None:
    result = consume_inventory_quantity_without_commit(
        db=db,
        ingredient_id=ingredient_id,
        amount=amount,
    )

    if result is not None:
        db.commit()

    return result


def consume_inventory_quantity_without_commit(
    db: Session,
    ingredient_id: int,
    amount: float,
) -> InventoryConsumptionResult | None:
    """
    在庫を期限順に減算し、commitせず結果を返す。

    複数材料を1トランザクションで扱う処理向け。
    呼び出し側がcommitまたはrollbackを行う。
    """
    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    if amount <= 0:
        raise ValueError(
            "減算量は0より大きい値にしてください。"
        )

    active_inventories = (
        get_active_inventory_lots(
            ingredient
        )
    )

    sorted_inventories = (
        sort_inventory_lots_for_consumption(
            active_inventories
        )
    )

    remaining_quantity = amount
    allocations: list[LotAllocation] = []

    for inventory in sorted_inventories:
        if remaining_quantity <= 0:
            break

        current_quantity = float(
            inventory.quantity or 0
        )

        consumed_quantity = min(
            current_quantity,
            remaining_quantity,
        )

        if consumed_quantity <= 0:
            continue

        inventory.quantity = (
            current_quantity
            - consumed_quantity
        )

        allocations.append(
            LotAllocation(
                inventory_id=inventory.id,
                quantity=consumed_quantity,
            )
        )

        remaining_quantity -= (
            consumed_quantity
        )

    consumed_quantity = (
        amount - remaining_quantity
    )

    return InventoryConsumptionResult(
        requested_quantity=amount,
        consumed_quantity=consumed_quantity,
        shortage_quantity=remaining_quantity,
        allocations=allocations,
    )


def restore_inventory_lot_quantity_without_commit(
    db: Session,
    inventory_id: int,
    amount: float,
) -> Inventory | None:
    """有効な元在庫ロットへ数量を戻し、commitは行わない。"""
    if amount <= 0:
        raise ValueError(
            "復元量は0より大きい値にしてください。"
        )

    inventory = (
        db.query(Inventory)
        .join(Ingredient)
        .filter(
            Inventory.id == inventory_id,
            Inventory.deleted_at.is_(None),
            Ingredient.is_active.is_(True),
        )
        .first()
    )

    if inventory is None:
        return None

    inventory.quantity = (
        float(inventory.quantity or 0) + amount
    )

    return inventory


def get_active_inventory_lots(
    ingredient: Ingredient,
) -> list[Inventory]:
    """
    論理削除されておらず、
    数量が0より大きい在庫ロットを取得する。
    """
    return [
        inventory
        for inventory in ingredient.inventories
        if (
            inventory.deleted_at is None
            and float(inventory.quantity or 0) > 0
        )
    ]


def get_inventory_quantity(
    ingredient: Ingredient,
) -> float:
    """
    論理削除されていない在庫ありロットの
    合計数量を返す。
    """
    return sum(
        float(inventory.quantity or 0)
        for inventory in get_active_inventory_lots(
            ingredient
        )
    )


def get_inventory_expiration_date(
    ingredient: Ingredient,
) -> date | None:
    """
    数量が残っている在庫ロットのうち、
    最も早い消費期限を取得する。

    期限未設定ロットは比較対象外とする。
    """
    expiration_dates = [
        inventory.expiration_date
        for inventory in get_active_inventory_lots(
            ingredient
        )
        if inventory.expiration_date is not None
    ]

    if not expiration_dates:
        return None

    return min(expiration_dates)

def get_inventory_purchase_date(
    ingredient: Ingredient,
) -> date:
    """
    数量が残っている在庫ロットのうち、
    最も古い購入日を取得する。

    在庫がない場合は、既存画面との互換性を保つため
    当日を返す。
    """
    purchase_dates = [
        inventory.purchase_date
        for inventory in get_active_inventory_lots(
            ingredient
        )
        if inventory.purchase_date is not None
    ]

    if not purchase_dates:
        return date.today()

    return min(purchase_dates)


def get_oldest_active_inventory_lot(
    db: Session,
    ingredient_id: int,
) -> Inventory | None:
    return (
        db.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient_id,
            Inventory.quantity > 0,
            Inventory.deleted_at.is_(None),
        )
        .order_by(
            Inventory.purchase_date.asc(),
            Inventory.id.asc(),
        )
        .first()
    )


def get_nearest_expiration_inventory_lot(
    db: Session,
    ingredient_id: int,
) -> Inventory | None:
    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient_id,
            Inventory.quantity > 0,
            Inventory.deleted_at.is_(None),
            Inventory.expiration_date.is_not(
                None
            ),
        )
        .order_by(
            Inventory.expiration_date.asc(),
            Inventory.purchase_date.asc(),
            Inventory.id.asc(),
        )
        .first()
    )

    if inventory is not None:
        return inventory

    return get_oldest_active_inventory_lot(
        db=db,
        ingredient_id=ingredient_id,
    )


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


def update_inventory_purchase_date(
    db: Session,
    ingredient_id: int,
    purchase_date: date,
) -> Inventory | None:
    """
    在庫ありロットのうち、
    購入日が最も古いロットの購入日を更新する。
    """
    inventory = get_oldest_active_inventory_lot(
        db=db,
        ingredient_id=ingredient_id,
    )

    if inventory is None:
        return None

    inventory.purchase_date = purchase_date

    db.commit()
    db.refresh(inventory)

    return inventory


def update_inventory_expiration_date(
    db: Session,
    ingredient_id: int,
    expiration_date: date | None,
) -> Inventory | None:
    """
    最短期限の在庫ありロットについて、
    消費期限を更新する。

    期限設定済みロットがない場合は、
    最古購入日の在庫ありロットを更新する。
    """
    inventory = (
        get_nearest_expiration_inventory_lot(
            db=db,
            ingredient_id=ingredient_id,
        )
    )

    if inventory is None:
        return None

    inventory.expiration_date = expiration_date

    db.commit()
    db.refresh(inventory)

    return inventory


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


def create_inventory_lot(
    db: Session,
    ingredient_id: int,
    quantity: float,
    purchase_date: date,
    expiration_date: date | None,
) -> Inventory | None:
    """指定した食材へ新しい在庫ロットを追加する。"""
    if quantity <= 0:
        raise ValueError(
            "在庫数量は0より大きい値を指定してください。"
        )

    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=ingredient_id,
    )

    if ingredient is None:
        return None

    inventory = Inventory(
        ingredient_id=ingredient.id,
        quantity=quantity,
        purchase_date=purchase_date,
        expiration_date=expiration_date,
    )

    try:
        db.add(inventory)
        db.commit()
        db.refresh(inventory)

    except Exception:
        db.rollback()
        raise

    return inventory


def get_latest_active_inventory_lot(
    db: Session,
    ingredient_id: int,
) -> Inventory | None:
    return (
        db.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient_id,
            Inventory.quantity > 0,
            Inventory.deleted_at.is_(None),
        )
        .order_by(
            Inventory.purchase_date.is_(
                None
            ),
            Inventory.purchase_date.desc(),
            Inventory.id.desc(),
        )
        .first()
    )


def increment_latest_inventory_lot(
    db: Session,
    ingredient_id: int,
    amount: float = 0.5,
) -> Inventory | None:
    """
    購入日が最も新しい在庫ありロットへ数量を追加する。

    在庫のあるロットが存在しない場合はNoneを返す。
    """
    if amount <= 0:
        raise ValueError(
            "追加数量は0より大きい値にしてください。"
        )

    inventory = get_latest_active_inventory_lot(
        db=db,
        ingredient_id=ingredient_id,
    )

    if inventory is None:
        return None

    current_quantity = float(
        inventory.quantity or 0
    )

    inventory.quantity = (
        current_quantity + amount
    )

    db.commit()
    db.refresh(inventory)

    return inventory


def get_inventory_lots(
    db: Session,
    ingredient_id: int,
) -> list[Inventory]:
    """
    削除されていない在庫ロットを一覧取得する。
    """
    return (
        db.query(Inventory)
        .filter(
            Inventory.ingredient_id
            == ingredient_id,
            Inventory.deleted_at.is_(None),
        )
        .order_by(
            case(
                (
                    Inventory.quantity > 0,
                    0,
                ),
                else_=1,
            ),
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
            Inventory.purchase_date.asc(),
            Inventory.id.asc(),
        )
        .all()
    )


def get_inventory_lot_by_id(
    db: Session,
    inventory_id: int,
    include_inactive_ingredient: bool = False,
) -> Inventory | None:
    """
    在庫ロットをIDで取得する。

    通常は以下を除外する。

    - 論理削除済みの在庫ロット
    - 論理削除済み食材に属する在庫ロット

    履歴参照などで必要な場合は、
    include_inactive_ingredient=Trueを指定する。
    """
    query = (
        db.query(Inventory)
        .join(
            Ingredient,
            Inventory.ingredient_id
            == Ingredient.id,
        )
        .options(
            joinedload(
                Inventory.ingredient
            )
        )
        .filter(
            Inventory.id == inventory_id,
            Inventory.deleted_at.is_(None),
        )
    )

    if not include_inactive_ingredient:
        query = query.filter(
            Ingredient.is_active.is_(True)
        )

    return query.first()


def update_inventory_lot(
    db: Session,
    inventory_id: int,
    quantity: float,
    purchase_date: date,
    expiration_date: date | None,
) -> Inventory | None:
    """
    在庫ロットを個別に更新する。

    他のロットは変更しない。
    """
    if quantity < 0:
        raise ValueError(
            "在庫数量は0以上で入力してください。"
        )

    if not is_valid_quantity_step(quantity):
        raise ValueError(
            "在庫数量は0.5刻みで入力してください。"
        )

    inventory = get_inventory_lot_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        return None

    inventory.quantity = quantity
    inventory.purchase_date = purchase_date
    inventory.expiration_date = (
        expiration_date
    )

    db.commit()
    db.refresh(inventory)

    return inventory


def soft_delete_inventory_lot(
    db: Session,
    inventory_id: int,
) -> Inventory | None:
    """
    在庫ロットを論理削除する。

    DBからは削除せず、deleted_atへ
    削除日時を記録する。
    """
    inventory = get_inventory_lot_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        return None

    inventory.deleted_at = datetime.now()

    db.commit()
    db.refresh(inventory)

    return inventory
