from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.recipe_ingredient import (
    RecipeIngredient,
)
from app.models.recipe_step import RecipeStep
from app.utils.ingredient_name import (
    create_search_keywords,
)


@dataclass(frozen=True)
class RecipeIngredientInput:
    """レシピ材料の登録内容。"""

    ingredient_id: int
    quantity: float | None = None
    quantity_text: str | None = None
    unit: str | None = None
    is_seasoning: bool = False
    is_inventory_consumed: bool = True
    notes: str | None = None
    display_order: int = 1


@dataclass(frozen=True)
class RecipeStepInput:
    """レシピ手順の登録内容。"""

    step_number: int
    description: str


def get_recipes(
    db: Session,
    include_inactive: bool = False,
    favorite_only: bool = False,
    cuisine_type: str = "",
    dish_category: str = "",
    ingredient_keyword: str = "",
    name_keyword: str = "",
) -> list[Recipe]:
    """
    レシピ一覧を材料・食材・手順と一緒に取得する。

    通常は有効なレシピだけを取得する。
    指定された条件はANDで適用する。
    """
    query = (
        db.query(Recipe)
        .options(
            selectinload(
                Recipe.ingredients
            ).joinedload(
                RecipeIngredient.ingredient
            ),
            selectinload(
                Recipe.steps
            ),
        )
    )

    if not include_inactive:
        query = query.filter(
            Recipe.is_active.is_(True)
        )

    if favorite_only:
        query = query.filter(
            Recipe.is_favorite.is_(True)
        )

    normalized_name_keyword = name_keyword.strip()
    if normalized_name_keyword:
        query = query.filter(
            Recipe.name.contains(normalized_name_keyword)
        )

    normalized_cuisine_type = (
        cuisine_type.strip()
    )

    if normalized_cuisine_type:
        query = query.filter(
            Recipe.cuisine_type
            == normalized_cuisine_type
        )

    normalized_dish_category = (
        dish_category.strip()
    )

    if normalized_dish_category:
        query = query.filter(
            Recipe.dish_category
            == normalized_dish_category
        )

    ingredient_keywords = (
        create_search_keywords(
            ingredient_keyword
        )
    )

    if ingredient_keywords:
        query = query.filter(
            Recipe.ingredients.any(
                RecipeIngredient
                .ingredient.has(
                    or_(
                        *[
                            Ingredient.name.contains(
                                keyword
                            )
                            for keyword
                            in ingredient_keywords
                        ]
                    )
                )
            )
        )

    return (
        query
        .order_by(Recipe.id)
        .all()
    )


def get_recipe_by_id(
    db: Session,
    recipe_id: int,
    include_inactive: bool = False,
) -> Recipe | None:
    """
    IDを指定してレシピを取得する。

    材料、材料の食材情報、手順も読み込む。
    通常は論理削除済みレシピを取得しない。
    """
    query = (
        db.query(Recipe)
        .options(
            selectinload(
                Recipe.ingredients
            ).joinedload(
                RecipeIngredient.ingredient
            ),
            selectinload(
                Recipe.steps
            ),
        )
        .filter(
            Recipe.id == recipe_id
        )
    )

    if not include_inactive:
        query = query.filter(
            Recipe.is_active.is_(True)
        )

    return query.first()


def create_recipe(
    db: Session,
    name: str,
    cooking_time_minutes: int,
    cuisine_type: str,
    dish_category: str,
    yield_type: str,
    base_servings: int | None,
    fixed_yield_text: str | None,
    ingredients: list[RecipeIngredientInput],
    steps: list[RecipeStepInput],
    is_favorite: bool = False,
) -> Recipe:
    """
    材料と手順を含むレシピを登録する。

    すべてのレコードを1回のcommitで登録し、
    失敗した場合は全体をrollbackする。
    """
    if not ingredients:
        raise ValueError(
            "レシピ材料を1件以上指定してください。"
        )

    if not steps:
        raise ValueError(
            "調理手順を1件以上指定してください。"
        )

    ingredient_ids = [
        item.ingredient_id
        for item in ingredients
    ]

    if len(ingredient_ids) != len(
        set(ingredient_ids)
    ):
        raise ValueError(
            "同じ食材を重複して指定できません。"
        )

    active_ingredient_ids = {
        ingredient_id
        for (ingredient_id,) in (
            db.query(Ingredient.id)
            .filter(
                Ingredient.id.in_(
                    ingredient_ids
                ),
                Ingredient.is_active.is_(
                    True
                ),
            )
            .all()
        )
    }

    missing_ingredient_ids = sorted(
        set(ingredient_ids)
        - active_ingredient_ids
    )

    if missing_ingredient_ids:
        raise ValueError(
            "有効な食材が見つかりません。"
            f"対象ID: {missing_ingredient_ids}"
        )

    recipe = Recipe(
        name=name.strip(),
        cooking_time_minutes=(
            cooking_time_minutes
        ),
        cuisine_type=cuisine_type.strip(),
        dish_category=dish_category.strip(),
        yield_type=yield_type,
        base_servings=base_servings,
        fixed_yield_text=(
            fixed_yield_text.strip()
            if fixed_yield_text is not None
            else None
        ),
        is_favorite=is_favorite,
    )

    recipe.ingredients = [
        RecipeIngredient(
            ingredient_id=(
                item.ingredient_id
            ),
            quantity=item.quantity,
            quantity_text=(
                item.quantity_text.strip()
                if item.quantity_text
                is not None
                else None
            ),
            unit=(
                item.unit.strip()
                if item.unit is not None
                else None
            ),
            is_seasoning=(
                item.is_seasoning
            ),
            is_inventory_consumed=(
                item.is_inventory_consumed
            ),
            notes=(
                item.notes.strip()
                if item.notes is not None
                else None
            ),
            display_order=(
                item.display_order
            ),
        )
        for item in ingredients
    ]

    recipe.steps = [
        RecipeStep(
            step_number=step.step_number,
            description=(
                step.description.strip()
            ),
        )
        for step in steps
    ]

    try:
        db.add(recipe)
        db.commit()
        db.refresh(recipe)

    except Exception:
        db.rollback()
        raise

    return recipe


def update_recipe(
    db: Session,
    recipe_id: int,
    name: str,
    cooking_time_minutes: int,
    cuisine_type: str,
    dish_category: str,
    yield_type: str,
    base_servings: int | None,
    fixed_yield_text: str | None,
    ingredients: list[RecipeIngredientInput],
    steps: list[RecipeStepInput],
    is_favorite: bool,
) -> Recipe | None:
    """
    レシピの基本情報・材料・手順を一括更新する。

    存在しないレシピまたは論理削除済みの
    レシピは更新しない。
    """
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        return None

    if not ingredients:
        raise ValueError(
            "レシピ材料を1件以上指定してください。"
        )

    if not steps:
        raise ValueError(
            "調理手順を1件以上指定してください。"
        )

    ingredient_ids = [
        item.ingredient_id
        for item in ingredients
    ]

    if len(ingredient_ids) != len(
        set(ingredient_ids)
    ):
        raise ValueError(
            "同じ食材を重複して指定できません。"
        )

    active_ingredient_ids = {
        ingredient_id
        for (ingredient_id,) in (
            db.query(Ingredient.id)
            .filter(
                Ingredient.id.in_(
                    ingredient_ids
                ),
                Ingredient.is_active.is_(
                    True
                ),
            )
            .all()
        )
    }

    missing_ingredient_ids = sorted(
        set(ingredient_ids)
        - active_ingredient_ids
    )

    if missing_ingredient_ids:
        raise ValueError(
            "有効な食材が見つかりません。"
            f"対象ID: {missing_ingredient_ids}"
        )

    try:
        recipe.name = name.strip()
        recipe.cooking_time_minutes = (
            cooking_time_minutes
        )
        recipe.cuisine_type = (
            cuisine_type.strip()
        )
        recipe.dish_category = (
            dish_category.strip()
        )
        recipe.yield_type = yield_type
        recipe.base_servings = base_servings
        recipe.fixed_yield_text = (
            fixed_yield_text.strip()
            if fixed_yield_text is not None
            else None
        )
        recipe.is_favorite = is_favorite

        # 新しい関連レコードと一意制約が
        # 衝突しないよう、既存分を先に削除する。
        recipe.ingredients.clear()
        recipe.steps.clear()
        db.flush()

        recipe.ingredients = [
            RecipeIngredient(
                ingredient_id=(
                    item.ingredient_id
                ),
                quantity=item.quantity,
                quantity_text=(
                    item.quantity_text.strip()
                    if item.quantity_text
                    is not None
                    else None
                ),
                unit=(
                    item.unit.strip()
                    if item.unit is not None
                    else None
                ),
                is_seasoning=(
                    item.is_seasoning
                ),
                is_inventory_consumed=(
                    item.is_inventory_consumed
                ),
                notes=(
                    item.notes.strip()
                    if item.notes is not None
                    else None
                ),
                display_order=(
                    item.display_order
                ),
            )
            for item in ingredients
        ]

        recipe.steps = [
            RecipeStep(
                step_number=step.step_number,
                description=(
                    step.description.strip()
                ),
            )
            for step in steps
        ]

        db.commit()
        db.refresh(recipe)

    except Exception:
        db.rollback()
        raise

    return recipe


def delete_recipe(
    db: Session,
    recipe_id: int,
) -> bool:
    """
    レシピを論理削除する。

    存在しないレシピまたは削除済みの場合は
    Falseを返す。
    """
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        return False

    try:
        recipe.is_active = False
        recipe.deleted_at = datetime.now()

        db.commit()

    except Exception:
        db.rollback()
        raise

    return True


def update_recipe_favorite(
    db: Session,
    recipe_id: int,
    is_favorite: bool,
) -> Recipe | None:
    """
    レシピのお気に入り状態を更新する。

    存在しないレシピまたは論理削除済みの
    レシピは更新しない。
    """
    recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if recipe is None:
        return None

    try:
        recipe.is_favorite = is_favorite

        db.commit()
        db.refresh(recipe)

    except Exception:
        db.rollback()
        raise

    return recipe
