"""seed_recipes.pyが作成したレシピだけを安全に削除する。"""

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
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from app.models.shopping_item import ShoppingItem
from scripts.seed_recipes import RECIPE_NAMES


SEED_RECIPE_NAMES = frozenset(
    name
    for names in RECIPE_NAMES.values()
    for name in names
)


@dataclass(frozen=True)
class RollbackSummary:
    recipe_count: int
    recipe_ingredient_count: int
    recipe_step_count: int
    ingredient_delete_count: int
    protected_ingredient_count: int
    history_reference_count: int


def _seed_recipes(db: Session) -> list[Recipe]:
    """名前allowlistに一致するレシピだけを取得する。"""
    return (
        db.query(Recipe)
        .filter(Recipe.name.in_(SEED_RECIPE_NAMES))
        .order_by(Recipe.id)
        .all()
    )


def _referenced_ingredient_ids(
    db: Session,
    excluded_recipe_ids: set[int] | None = None,
) -> set[int]:
    """Recipe以外に残るIngredient参照をまとめて取得する。"""
    referenced: set[int] = set()
    recipe_ingredient_query = db.query(
        RecipeIngredient.ingredient_id
    )
    if excluded_recipe_ids:
        recipe_ingredient_query = recipe_ingredient_query.filter(
            ~RecipeIngredient.recipe_id.in_(excluded_recipe_ids)
        )
    referenced.update(
        ingredient_id
        for (ingredient_id,) in recipe_ingredient_query.all()
        if ingredient_id is not None
    )
    referenced.update(
        ingredient_id
        for (ingredient_id,) in db.query(
            Inventory.ingredient_id
        ).all()
        if ingredient_id is not None
    )
    referenced.update(
        ingredient_id
        for (ingredient_id,) in db.query(
            ShoppingItem.ingredient_id
        ).all()
        if ingredient_id is not None
    )
    referenced.update(
        ingredient_id
        for (ingredient_id,) in db.query(
            CookingHistoryIngredient.ingredient_id
        ).all()
        if ingredient_id is not None
    )
    return referenced


def rollback_seed_recipes(
    db: Session,
    *,
    dry_run: bool = False,
) -> RollbackSummary:
    """seedレシピだけを1トランザクションで削除する。"""
    recipes = _seed_recipes(db)
    history_count = (
        db.query(CookingHistory)
        .filter(
            CookingHistory.recipe_id.in_(
                [recipe.id for recipe in recipes]
            )
        )
        .count()
        if recipes
        else 0
    )
    if history_count:
        raise RuntimeError(
            "seed対象レシピに調理履歴があるため、"
            "安全のためrollbackを中止しました。"
        )

    ingredient_ids = {
        ingredient_id
        for recipe in recipes
        for ingredient_id in (
            item.ingredient_id
            for item in recipe.ingredients
        )
        if ingredient_id is not None
    }
    recipe_ingredient_count = sum(
        len(recipe.ingredients) for recipe in recipes
    )
    recipe_step_count = sum(
        len(recipe.steps) for recipe in recipes
    )

    if dry_run:
        referenced = _referenced_ingredient_ids(
            db,
            excluded_recipe_ids={recipe.id for recipe in recipes},
        )
        deletable = ingredient_ids - referenced
        return RollbackSummary(
            recipe_count=len(recipes),
            recipe_ingredient_count=recipe_ingredient_count,
            recipe_step_count=recipe_step_count,
            ingredient_delete_count=len(deletable),
            protected_ingredient_count=len(ingredient_ids & referenced),
            history_reference_count=history_count,
        )

    try:
        for recipe in recipes:
            db.delete(recipe)
        db.flush()

        referenced = _referenced_ingredient_ids(db)
        deletable = ingredient_ids - referenced
        for ingredient_id in deletable:
            ingredient = db.get(Ingredient, ingredient_id)
            if ingredient is not None:
                db.delete(ingredient)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RollbackSummary(
        recipe_count=len(recipes),
        recipe_ingredient_count=recipe_ingredient_count,
        recipe_step_count=recipe_step_count,
        ingredient_delete_count=len(deletable),
        protected_ingredient_count=len(ingredient_ids & referenced),
        history_reference_count=history_count,
    )


def _print_summary(summary: RollbackSummary, *, dry_run: bool) -> None:
    prefix = "削除予定" if dry_run else "削除"
    print(f"{prefix}Recipe: {summary.recipe_count}件")
    print(f"{prefix}RecipeIngredient: {summary.recipe_ingredient_count}件")
    print(f"{prefix}RecipeStep: {summary.recipe_step_count}件")
    print(f"Ingredient削除候補: {summary.ingredient_delete_count}件")
    print(f"Ingredient保護: {summary.protected_ingredient_count}件")
    print(f"CookingHistory参照: {summary.history_reference_count}件")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除せず、対象件数だけ表示する",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        summary = rollback_seed_recipes(
            db,
            dry_run=args.dry_run,
        )
        _print_summary(summary, dry_run=args.dry_run)
        if args.dry_run:
            print("dry-runのためDBは変更していません。")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
