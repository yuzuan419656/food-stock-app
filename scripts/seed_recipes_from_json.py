"""JSON定義を唯一の入力としてレシピを一括seedする。"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.crud.ingredient import get_ingredient_by_name
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from app.utils.ingredient_name import normalize_ingredient_name


class SeedJSONValidationError(ValueError):
    """JSON定義がアプリの制約を満たさない。"""


@dataclass(frozen=True)
class SeedSummary:
    json_recipe_count: int
    new_recipe_count: int
    skipped_recipe_count: int
    new_ingredient_count: int
    reused_ingredient_count: int
    unit_warning_count: int
    recipe_ingredient_count: int
    recipe_step_count: int
    new_ingredient_names: tuple[str, ...]
    unit_warnings: tuple[str, ...]


def load_and_validate(path: str | Path) -> list[dict[str, Any]]:
    """JSON全体を検証し、DBへ触れる前に不正入力を拒否する。"""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SeedJSONValidationError(f"JSONを読み込めません: {error}") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("recipes"), list):
        raise SeedJSONValidationError("recipes配列を含むJSONオブジェクトが必要です。")
    recipes = payload["recipes"]
    if len(recipes) != 30 or payload.get("recipe_count") != 30:
        raise SeedJSONValidationError("JSONのRecipe数は30件である必要があります。")

    names: set[str] = set()
    for index, recipe in enumerate(recipes, start=1):
        if not isinstance(recipe, dict):
            raise SeedJSONValidationError(f"Recipe {index}: オブジェクトではありません。")
        name = recipe.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SeedJSONValidationError(f"Recipe {index}: nameが空です。")
        name_key = normalize_ingredient_name(name).casefold()
        if name_key in names:
            raise SeedJSONValidationError(f"Recipe名が重複しています: {name}")
        names.add(name_key)
        if (
            type(recipe.get("cooking_time_minutes")) is not int
            or recipe["cooking_time_minutes"] <= 0
        ):
            raise SeedJSONValidationError(f"{name}: cooking_time_minutesが不正です。")
        if recipe.get("yield_type") != "servings" or recipe.get("base_servings") != 2:
            raise SeedJSONValidationError(f"{name}: yield_type/base_servingsが不正です。")
        if not isinstance(recipe.get("ingredients"), list) or not recipe["ingredients"]:
            raise SeedJSONValidationError(f"{name}: 材料がありません。")
        if not isinstance(recipe.get("steps"), list) or not recipe["steps"]:
            raise SeedJSONValidationError(f"{name}: 手順がありません。")

        orders: set[int] = set()
        for item in recipe["ingredients"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                raise SeedJSONValidationError(f"{name}: 材料名が不正です。")
            order = item.get("display_order")
            if type(order) is not int or order < 1 or order in orders:
                raise SeedJSONValidationError(f"{name}: display_orderが不正または重複しています。")
            orders.add(order)
            quantity = item.get("quantity")
            quantity_text = item.get("quantity_text")
            if quantity is not None and quantity_text is not None:
                raise SeedJSONValidationError(f"{name}/{item['name']}: quantityとquantity_textが同時指定です。")
            if quantity is None and (not isinstance(quantity_text, str) or not quantity_text.strip()):
                raise SeedJSONValidationError(f"{name}/{item['name']}: quantityがありません。")
            if quantity is not None and (
                isinstance(quantity, bool)
                or not isinstance(quantity, (int, float))
                or not math.isfinite(float(quantity))
                or quantity <= 0
            ):
                raise SeedJSONValidationError(f"{name}/{item['name']}: quantityが不正です。")
            if quantity is not None and (not isinstance(item.get("unit"), str) or not item["unit"].strip()):
                raise SeedJSONValidationError(f"{name}/{item['name']}: 数値quantityにはunitが必要です。")
            is_seasoning = item.get("is_seasoning", False)
            is_inventory_consumed = item.get("is_inventory_consumed", True)
            if not isinstance(is_seasoning, bool) or not isinstance(is_inventory_consumed, bool):
                raise SeedJSONValidationError(f"{name}/{item['name']}: フラグが不正です。")
            if is_inventory_consumed and (
                is_seasoning or quantity is None or quantity_text is not None
            ):
                raise SeedJSONValidationError(f"{name}/{item['name']}: 在庫消費フラグがモデル制約に反します。")

        step_numbers: set[int] = set()
        for step in recipe["steps"]:
            number = step.get("step_number") if isinstance(step, dict) else None
            description = step.get("description") if isinstance(step, dict) else None
            if type(number) is not int or number < 1 or number in step_numbers:
                raise SeedJSONValidationError(f"{name}: step_numberが不正または重複しています。")
            if not isinstance(description, str) or not description.strip():
                raise SeedJSONValidationError(f"{name}: 手順文章が空です。")
            step_numbers.add(number)
    return recipes


def _active_recipe_keys(db: Session) -> set[str]:
    return {
        normalize_ingredient_name(recipe.name).casefold()
        for recipe in db.query(Recipe).filter(Recipe.is_active.is_(True)).all()
    }


def _plan(db: Session, recipes: list[dict[str, Any]]) -> SeedSummary:
    active_names = _active_recipe_keys(db)
    new_recipe_defs = [
        recipe
        for recipe in recipes
        if normalize_ingredient_name(recipe["name"]).casefold() not in active_names
    ]
    new_ingredients: set[str] = set()
    reused = 0
    warnings: list[str] = []
    ingredient_count = 0
    step_count = 0
    for recipe in new_recipe_defs:
        ingredient_count += len(recipe["ingredients"])
        step_count += len(recipe["steps"])
        for item in recipe["ingredients"]:
            existing = get_ingredient_by_name(db, item["name"], include_inactive=True)
            if existing is None:
                new_ingredients.add(item["name"])
            else:
                reused += 1
                if existing.default_unit != item.get("default_unit"):
                    warnings.append(
                        f"{item['name']}: DB={existing.default_unit!r}, JSON={item.get('default_unit')!r}"
                    )
    return SeedSummary(
        json_recipe_count=len(recipes),
        new_recipe_count=len(new_recipe_defs),
        skipped_recipe_count=len(recipes) - len(new_recipe_defs),
        new_ingredient_count=len(new_ingredients),
        reused_ingredient_count=reused,
        unit_warning_count=len(warnings),
        recipe_ingredient_count=ingredient_count,
        recipe_step_count=step_count,
        new_ingredient_names=tuple(sorted(new_ingredients)),
        unit_warnings=tuple(warnings),
    )


def seed_recipes_from_json(
    db: Session,
    recipes: list[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> SeedSummary:
    """JSON定義を1トランザクションで登録する。"""
    summary = _plan(db, recipes)
    if dry_run:
        return summary

    active_names = _active_recipe_keys(db)
    try:
        for recipe_data in recipes:
            recipe_key = normalize_ingredient_name(recipe_data["name"]).casefold()
            if recipe_key in active_names:
                print(f"SKIP: {recipe_data['name']} - 既存Recipeあり")
                continue

            resolved: list[tuple[dict[str, Any], Ingredient]] = []
            resolved_ids: set[int] = set()
            for item in recipe_data["ingredients"]:
                ingredient = get_ingredient_by_name(db, item["name"], include_inactive=True)
                if ingredient is not None and not ingredient.is_active:
                    raise SeedJSONValidationError(
                        f"{recipe_data['name']}/{item['name']}: inactive Ingredientは利用できません。"
                    )
                if ingredient is None:
                    ingredient = Ingredient(
                        name=item["name"],
                        category=item.get("category"),
                        default_unit=item.get("default_unit"),
                    )
                    db.add(ingredient)
                    db.flush()
                    print(f"ADD Ingredient: {ingredient.name}")
                if ingredient.id in resolved_ids:
                    raise SeedJSONValidationError(
                        f"{recipe_data['name']}: 同じIngredientが重複しています。"
                    )
                resolved_ids.add(ingredient.id)
                resolved.append((item, ingredient))

            recipe = Recipe(
                name=recipe_data["name"],
                cooking_time_minutes=recipe_data["cooking_time_minutes"],
                cuisine_type=recipe_data["cuisine_type"],
                dish_category=recipe_data["dish_category"],
                yield_type=recipe_data["yield_type"],
                base_servings=recipe_data["base_servings"],
                fixed_yield_text=recipe_data.get("fixed_yield_text"),
                is_favorite=False,
            )
            recipe.ingredients = [
                RecipeIngredient(
                    ingredient_id=ingredient.id,
                    quantity=item.get("quantity"),
                    quantity_text=item.get("quantity_text"),
                    unit=item.get("unit"),
                    is_seasoning=item.get("is_seasoning", False),
                    is_inventory_consumed=item.get("is_inventory_consumed", True),
                    notes=item.get("notes"),
                    display_order=item["display_order"],
                )
                for item, ingredient in resolved
            ]
            recipe.steps = [
                RecipeStep(
                    step_number=step["step_number"],
                    description=step["description"],
                )
                for step in recipe_data["steps"]
            ]
            db.add(recipe)
            db.flush()
            active_names.add(recipe_key)
        db.commit()
    except Exception as error:
        db.rollback()
        raise RuntimeError(f"JSON seed登録に失敗しました: {error}") from error
    return summary


def _print_summary(summary: SeedSummary, *, dry_run: bool) -> None:
    print(f"JSON内Recipe数: {summary.json_recipe_count}件")
    print(f"新規登録{'予定' if dry_run else ''}Recipe数: {summary.new_recipe_count}件")
    print(f"スキップ{'予定' if dry_run else ''}Recipe数: {summary.skipped_recipe_count}件")
    print(f"新規作成{'予定' if dry_run else ''}Ingredient数: {summary.new_ingredient_count}件")
    print(f"再利用{'予定' if dry_run else ''}Ingredient数: {summary.reused_ingredient_count}件")
    print(f"Ingredient単位不一致警告数: {summary.unit_warning_count}件")
    print(f"RecipeIngredient登録{'予定' if dry_run else ''}数: {summary.recipe_ingredient_count}件")
    print(f"RecipeStep登録{'予定' if dry_run else ''}数: {summary.recipe_step_count}件")
    if summary.new_ingredient_names:
        print("新規Ingredient: " + ", ".join(summary.new_ingredient_names))
    for warning in summary.unit_warnings:
        print("WARNING: " + warning)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="安全な履歴保護付き置換処理がないため現在は使用できません",
    )
    args = parser.parse_args()
    if args.replace_existing:
        raise RuntimeError("--replace-existingは既存Recipe/CookingHistory保護のため未実装です。")
    recipes = load_and_validate(args.json_path)
    db = SessionLocal()
    try:
        summary = seed_recipes_from_json(db, recipes, dry_run=args.dry_run)
        _print_summary(summary, dry_run=args.dry_run)
        if args.dry_run:
            print("dry-runのためDBは変更していません。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
