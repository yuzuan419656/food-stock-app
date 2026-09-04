"""seed_recipes.py が追加したレシピと動作確認用履歴を削除する。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.cooking_history import CookingHistory
from app.models.cooking_history_ingredient import CookingHistoryIngredient
from app.models.cooking_history_inventory_consumption import (
    CookingHistoryInventoryConsumption,
)
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from scripts.seed_recipes import RECIPE_NAMES


SEED_RECIPE_NAMES = frozenset(
    name
    for names in RECIPE_NAMES.values()
    for name in names
)


@dataclass(frozen=True)
class CleanupSummary:
    seed_definition_recipe_count: int
    existing_seed_recipe_count: int
    recipe_count: int
    recipe_ingredient_count: int
    recipe_step_count: int
    cooking_history_count: int
    cooking_history_ingredient_count: int
    cooking_history_inventory_consumption_count: int
    preserved_recipe_count: int
    preserved_cooking_history_count: int
    missing_recipe_names: tuple[str, ...]
    cooking_history_ids: tuple[int, ...]


def _seed_recipes(db: Session) -> list[Recipe]:
    """seedスクリプトの名前allowlistに一致するレシピだけを取得する。"""
    return (
        db.query(Recipe)
        .filter(Recipe.name.in_(SEED_RECIPE_NAMES))
        .order_by(Recipe.id)
        .all()
    )


def build_cleanup_summary(db: Session) -> CleanupSummary:
    """削除対象を集計する。DBへの変更は行わない。"""
    recipes = _seed_recipes(db)
    recipe_ids = {recipe.id for recipe in recipes}
    histories = (
        db.query(CookingHistory)
        .filter(CookingHistory.recipe_id.in_(recipe_ids))
        .order_by(CookingHistory.id)
        .all()
        if recipe_ids
        else []
    )

    history_ids = {history.id for history in histories}
    history_ingredients = (
        db.query(CookingHistoryIngredient)
        .filter(CookingHistoryIngredient.cooking_history_id.in_(history_ids))
        .all()
        if history_ids
        else []
    )
    history_ingredient_ids = {item.id for item in history_ingredients}
    allocations = (
        db.query(CookingHistoryInventoryConsumption)
        .filter(
            CookingHistoryInventoryConsumption.cooking_history_ingredient_id.in_(
                history_ingredient_ids
            )
        )
        .all()
        if history_ingredient_ids
        else []
    )

    return CleanupSummary(
        seed_definition_recipe_count=len(SEED_RECIPE_NAMES),
        existing_seed_recipe_count=len(recipes),
        recipe_count=len(recipes),
        recipe_ingredient_count=sum(len(recipe.ingredients) for recipe in recipes),
        recipe_step_count=sum(len(recipe.steps) for recipe in recipes),
        cooking_history_count=len(histories),
        cooking_history_ingredient_count=len(history_ingredients),
        cooking_history_inventory_consumption_count=len(allocations),
        preserved_recipe_count=db.query(Recipe).filter(~Recipe.id.in_(recipe_ids)).count()
        if recipe_ids
        else db.query(Recipe).count(),
        preserved_cooking_history_count=(
            db.query(CookingHistory)
            .filter(~CookingHistory.id.in_(history_ids)).count()
            if history_ids
            else db.query(CookingHistory).count()
        ),
        missing_recipe_names=tuple(sorted(SEED_RECIPE_NAMES - {recipe.name for recipe in recipes})),
        cooking_history_ids=tuple(history.id for history in histories),
    )


def _validate_targets(
    db: Session,
    recipes: list[Recipe],
    histories: list[CookingHistory],
) -> None:
    """対象外の履歴や予期しない参照を削除しないことを確認する。"""
    recipe_ids = {recipe.id for recipe in recipes}
    if any(history.recipe_id not in recipe_ids for history in histories):
        raise RuntimeError("seed対象外RecipeのCookingHistoryが削除対象に含まれています。")

    # Inventoryは復元・削除とも行わない。履歴のロット割当は履歴削除に
    # 伴って消えるだけで、Inventory本体の数量や行には触れない。
    for history in histories:
        for ingredient in history.ingredients:
            for allocation in ingredient.inventory_consumptions:
                if allocation.inventory_id is None or allocation.consumed_quantity <= 0:
                    raise RuntimeError(
                        "不正なロット消費履歴があるためcleanupを中止します。"
                    )


def cleanup_seed_recipes(db: Session, *, dry_run: bool = False) -> CleanupSummary:
    """seed対象のRecipeと履歴だけを1トランザクションで物理削除する。"""
    summary = build_cleanup_summary(db)
    recipes = _seed_recipes(db)
    histories = (
        db.query(CookingHistory)
        .filter(CookingHistory.recipe_id.in_({recipe.id for recipe in recipes}))
        .order_by(CookingHistory.id)
        .all()
        if recipes
        else []
    )
    _validate_targets(db, recipes, histories)

    if dry_run:
        return summary

    try:
        # FK RESTRICTを維持したまま、履歴側を先に削除する。
        for history in histories:
            for ingredient in history.ingredients:
                for allocation in ingredient.inventory_consumptions:
                    db.delete(allocation)
            for ingredient in history.ingredients:
                db.delete(ingredient)
            db.delete(history)

        # Recipe側の子も明示的に削除し、cascade設定に依存しすぎない。
        for recipe in recipes:
            for ingredient in recipe.ingredients:
                db.delete(ingredient)
            for step in recipe.steps:
                db.delete(step)
            db.delete(recipe)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return summary


def _print_summary(summary: CleanupSummary, *, dry_run: bool) -> None:
    prefix = "削除予定" if dry_run else "削除"
    print(f"seed定義Recipe: {summary.seed_definition_recipe_count}件")
    print(f"DB内seed対象Recipe: {summary.existing_seed_recipe_count}件")
    print(f"{prefix}Recipe: {summary.recipe_count}件")
    print(f"{prefix}RecipeIngredient: {summary.recipe_ingredient_count}件")
    print(f"{prefix}RecipeStep: {summary.recipe_step_count}件")
    print(f"{prefix}CookingHistory: {summary.cooking_history_count}件")
    print(
        f"{prefix}CookingHistoryIngredient: "
        f"{summary.cooking_history_ingredient_count}件"
    )
    print(
        f"{prefix}CookingHistoryInventoryConsumption: "
        f"{summary.cooking_history_inventory_consumption_count}件"
    )
    print(f"保持Recipe: {summary.preserved_recipe_count}件")
    print(f"保持CookingHistory: {summary.preserved_cooking_history_count}件")
    print(
        "DBに存在しないseed定義Recipe: "
        f"{', '.join(summary.missing_recipe_names) or 'なし'}"
    )
    print(
        "削除対象CookingHistory ID: "
        f"{', '.join(map(str, summary.cooking_history_ids)) or 'なし'}"
    )
    print("Inventory数量・ロット・Ingredient・ShoppingItemは変更しません。")
    if dry_run:
        print("dry-runのためDBは変更していません。")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        summary = cleanup_seed_recipes(db, dry_run=args.dry_run)
        _print_summary(summary, dry_run=args.dry_run)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
