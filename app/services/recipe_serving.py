"""レシピの人数換算に関する処理。"""


def calculate_scaled_quantity(
    base_quantity: float,
    base_servings: int,
    target_servings: int,
) -> float:
    """
    基準人数と今回人数から材料量を換算する。

    例:
        基準2人分・じゃがいも2個
        今回3人分

        2 × 3 ÷ 2 = 3
    """
    if base_quantity < 0:
        raise ValueError(
            "基準材料量は0以上である必要があります。"
        )

    if base_servings <= 0:
        raise ValueError(
            "基準人数は1以上である必要があります。"
        )

    if target_servings <= 0:
        raise ValueError(
            "人数は1以上である必要があります。"
        )

    return (
        base_quantity
        * target_servings
        / base_servings
    )


def format_recipe_quantity(
    quantity: float,
) -> str:
    """
    材料量を画面表示用の文字列に変換する。

    3.0 -> "3"
    1.5 -> "1.5"
    0.75 -> "0.75"
    """
    if quantity.is_integer():
        return str(int(quantity))

    return str(quantity)


from dataclasses import dataclass


@dataclass(frozen=True)
class ScaledRecipeIngredient:
    """人数換算後のレシピ材料。"""

    recipe_ingredient: object
    display_quantity: str


def build_scaled_recipe_ingredients(
    recipe,
    target_servings: int,
) -> list[ScaledRecipeIngredient]:
    """
    人数換算後の材料一覧を生成する。

    quantityを持つ材料は人数に応じて換算し、
    quantity_textを持つ材料はそのまま表示する。
    """
    if recipe.yield_type != "servings":
        raise ValueError(
            "人数換算型レシピではありません。"
        )

    if recipe.base_servings is None:
        raise ValueError(
            "基準人数が設定されていません。"
        )

    if target_servings <= 0:
        raise ValueError(
            "人数は1以上である必要があります。"
        )

    result: list[
        ScaledRecipeIngredient
    ] = []

    for item in recipe.ingredients:
        if item.quantity is not None:
            scaled_quantity = (
                calculate_scaled_quantity(
                    base_quantity=item.quantity,
                    base_servings=(
                        recipe.base_servings
                    ),
                    target_servings=(
                        target_servings
                    ),
                )
            )

            display_quantity = (
                format_recipe_quantity(
                    scaled_quantity
                )
            )

        else:
            display_quantity = (
                item.quantity_text or ""
            )

        result.append(
            ScaledRecipeIngredient(
                recipe_ingredient=item,
                display_quantity=(
                    display_quantity
                ),
            )
        )

    return result