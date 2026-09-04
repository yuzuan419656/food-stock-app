"""レシピの不足食材と買うものリストの連携。"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.crud.shopping_item import (
    add_or_reactivate_ingredients_without_commit,
)
from app.services.recipe_inventory import (
    RecipeInventoryStatus,
    build_recipe_inventory_statuses,
)


@dataclass(frozen=True)
class RecipeShoppingListCandidate:
    """安全に買うものリストへ追加できる不足食材。"""

    inventory_status: RecipeInventoryStatus

    @property
    def ingredient(self):
        return self.inventory_status.recipe_ingredient.ingredient

    @property
    def shortage_quantity(self) -> float:
        return self.inventory_status.shortage_quantity or 0.0

    @property
    def display_shortage_quantity(self) -> str:
        return self.inventory_status.display_shortage_quantity or "0"

    @property
    def unit(self) -> str:
        return self.inventory_status.recipe_ingredient.unit


@dataclass(frozen=True)
class RecipeShoppingListResult:
    candidate_count: int
    added_count: int


def build_recipe_shopping_list_candidates(
    recipe,
    target_servings: int | None = None,
) -> list[RecipeShoppingListCandidate]:
    """Step 2の判定結果から、自動追加可能な不足だけを返す。"""
    statuses = build_recipe_inventory_statuses(
        recipe=recipe,
        target_servings=target_servings,
    )

    return select_recipe_shopping_list_candidates(statuses)


def select_recipe_shopping_list_candidates(
    statuses: list[RecipeInventoryStatus],
) -> list[RecipeShoppingListCandidate]:
    """計算済みの在庫判定から追加候補を抽出する。"""
    return [
        RecipeShoppingListCandidate(inventory_status=status)
        for status in statuses
        if status.status == "shortage"
        and status.is_automatically_checkable
        and (status.shortage_quantity or 0) > 0
    ]


def add_recipe_shortages_to_shopping_list(
    db: Session,
    recipe,
    target_servings: int | None = None,
) -> RecipeShoppingListResult:
    """現在庫で不足を再判定し、全候補を1トランザクションで追加する。"""
    candidates = build_recipe_shopping_list_candidates(
        recipe=recipe,
        target_servings=target_servings,
    )

    try:
        added_count = add_or_reactivate_ingredients_without_commit(
            db=db,
            ingredient_ids=[
                candidate.ingredient.id
                for candidate in candidates
            ],
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RecipeShoppingListResult(
        candidate_count=len(candidates),
        added_count=added_count,
    )
