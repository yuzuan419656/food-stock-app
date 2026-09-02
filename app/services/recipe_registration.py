from sqlalchemy.orm import Session

from app.crud.ingredient import (
    get_ingredient_by_id,
    get_ingredient_by_name,
)
from app.crud.recipe import (
    RecipeIngredientInput,
    RecipeStepInput,
    create_recipe,
    get_recipe_by_id,
    update_recipe,
)
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.services.recipe_form import (
    ParsedRecipeForm,
    RecipeFormIngredient,
)
from app.utils.ingredient_name import (
    normalize_ingredient_name,
)


class RecipeRegistrationError(ValueError):
    """レシピ登録・更新時の食材解決エラー。"""


def _normalized_name_key(
    name: str,
) -> str:
    return normalize_ingredient_name(
        name
    ).casefold()


def _resolve_existing_ingredient(
    db: Session,
    form_ingredient: RecipeFormIngredient,
) -> Ingredient:
    assert (
        form_ingredient.ingredient_id
        is not None
    )

    ingredient = get_ingredient_by_id(
        db=db,
        ingredient_id=(
            form_ingredient.ingredient_id
        ),
    )

    if ingredient is None:
        raise RecipeRegistrationError(
            "選択された食材が見つかりません。"
        )

    if (
        _normalized_name_key(
            ingredient.name
        )
        != _normalized_name_key(
            form_ingredient.name
        )
    ):
        raise RecipeRegistrationError(
            "食材の選択内容が正しくありません。"
        )

    return ingredient


def _resolve_new_ingredient(
    db: Session,
    form_ingredient: RecipeFormIngredient,
) -> Ingredient:
    existing_ingredient = (
        get_ingredient_by_name(
            db=db,
            name=form_ingredient.name,
            include_inactive=True,
        )
    )

    if existing_ingredient is not None:
        if not existing_ingredient.is_active:
            raise RecipeRegistrationError(
                f"「{form_ingredient.name}」は"
                "削除済み食材として登録されています。"
            )

        return existing_ingredient

    if form_ingredient.category is None:
        raise RecipeRegistrationError(
            "新しい食材のカテゴリを"
            "指定してください。"
        )

    ingredient = Ingredient(
        name=form_ingredient.name,
        category=form_ingredient.category,
        default_unit=form_ingredient.unit,
    )

    db.add(ingredient)

    # レシピ材料へingredient_idを渡すため、
    # commitせずにIDだけ確定させる。
    db.flush()

    return ingredient


def _resolve_ingredient(
    db: Session,
    form_ingredient: RecipeFormIngredient,
) -> Ingredient:
    if form_ingredient.ingredient_id is not None:
        return _resolve_existing_ingredient(
            db=db,
            form_ingredient=form_ingredient,
        )

    return _resolve_new_ingredient(
        db=db,
        form_ingredient=form_ingredient,
    )


def _build_recipe_inputs(
    db: Session,
    parsed_form: ParsedRecipeForm,
) -> tuple[
    list[RecipeIngredientInput],
    list[RecipeStepInput],
]:
    """
    解析済みフォームからCRUDへ渡す
    材料・手順データを作成する。

    新しい食材が含まれる場合は、
    commitせずに食材IDだけ確定する。
    """
    recipe_ingredients: list[
        RecipeIngredientInput
    ] = []

    resolved_ingredient_ids: set[int] = set()

    for form_ingredient in (
        parsed_form.ingredients
    ):
        ingredient = _resolve_ingredient(
            db=db,
            form_ingredient=form_ingredient,
        )

        if ingredient.id in resolved_ingredient_ids:
            raise RecipeRegistrationError(
                "同じ食材を重複して"
                "指定できません。"
            )

        resolved_ingredient_ids.add(
            ingredient.id
        )

        is_seasoning = (
            ingredient.category == "調味料"
        )

        is_inventory_consumed = (
            form_ingredient.quantity
            is not None
            and not is_seasoning
        )

        recipe_ingredients.append(
            RecipeIngredientInput(
                ingredient_id=ingredient.id,
                quantity=(
                    form_ingredient.quantity
                ),
                quantity_text=(
                    form_ingredient.quantity_text
                ),
                unit=form_ingredient.unit,
                is_seasoning=is_seasoning,
                is_inventory_consumed=(
                    is_inventory_consumed
                ),
                notes=form_ingredient.notes,
                display_order=(
                    form_ingredient.display_order
                ),
            )
        )

    recipe_steps = [
        RecipeStepInput(
            step_number=step.step_number,
            description=step.description,
        )
        for step in parsed_form.steps
    ]

    return recipe_ingredients, recipe_steps


def register_recipe(
    db: Session,
    parsed_form: ParsedRecipeForm,
) -> Recipe:
    """
    新規食材を含むレシピを一括登録する。

    途中で失敗した場合は、
    新規食材を含むすべてをrollbackする。
    """
    try:
        (
            recipe_ingredients,
            recipe_steps,
        ) = _build_recipe_inputs(
            db=db,
            parsed_form=parsed_form,
        )

        return create_recipe(
            db=db,
            name=parsed_form.name,
            cooking_time_minutes=(
                parsed_form.cooking_time_minutes
            ),
            cuisine_type=(
                parsed_form.cuisine_type
            ),
            dish_category=(
                parsed_form.dish_category
            ),
            yield_type=parsed_form.yield_type,
            base_servings=(
                parsed_form.base_servings
            ),
            fixed_yield_text=(
                parsed_form.fixed_yield_text
            ),
            ingredients=recipe_ingredients,
            steps=recipe_steps,
            is_favorite=(
                parsed_form.is_favorite
            ),
        )

    except Exception:
        db.rollback()
        raise


def update_registered_recipe(
    db: Session,
    recipe_id: int,
    parsed_form: ParsedRecipeForm,
) -> Recipe | None:
    """
    新規食材を含むレシピ編集内容を一括更新する。

    存在しないレシピまたは論理削除済みの
    レシピは更新しない。

    途中で失敗した場合は、
    新規食材を含むすべてをrollbackする。
    """
    existing_recipe = get_recipe_by_id(
        db=db,
        recipe_id=recipe_id,
    )

    if existing_recipe is None:
        return None

    try:
        (
            recipe_ingredients,
            recipe_steps,
        ) = _build_recipe_inputs(
            db=db,
            parsed_form=parsed_form,
        )

        updated_recipe = update_recipe(
            db=db,
            recipe_id=recipe_id,
            name=parsed_form.name,
            cooking_time_minutes=(
                parsed_form.cooking_time_minutes
            ),
            cuisine_type=(
                parsed_form.cuisine_type
            ),
            dish_category=(
                parsed_form.dish_category
            ),
            yield_type=parsed_form.yield_type,
            base_servings=(
                parsed_form.base_servings
            ),
            fixed_yield_text=(
                parsed_form.fixed_yield_text
            ),
            ingredients=recipe_ingredients,
            steps=recipe_steps,
            is_favorite=(
                parsed_form.is_favorite
            ),
        )

        if updated_recipe is None:
            db.rollback()

        return updated_recipe

    except Exception:
        db.rollback()
        raise