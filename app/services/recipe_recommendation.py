"""説明可能なルールベースのレシピ推薦。"""

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.recipe import get_recipes
from app.models.cooking_history import CookingHistory
from app.services.recipe_inventory import (
    RecipeInventoryStatus,
    build_recipe_inventory_statuses,
)


RECOMMENDATION_MODES = {
    "balanced",
    "expiring",
    "quick",
    "in_stock",
}


@dataclass(frozen=True)
class RecommendationWeights:
    expiration: float = 1.0
    inventory: float = 1.0
    favorite: float = 1.0
    history: float = 1.0
    recency: float = 1.0
    cooking_time: float = 1.0
    shortage: float = 1.0


DEFAULT_RECOMMENDATION_WEIGHTS = RecommendationWeights()


@dataclass(frozen=True)
class RecipeHistorySummary:
    cooking_count: int = 0
    last_cooked_at: datetime | None = None


@dataclass(frozen=True)
class ExpirationScore:
    score: float
    expired_count: int
    within_one_day_count: int
    within_three_days_count: int
    within_seven_days_count: int
    reasons: tuple[str, ...]

    @property
    def urgent_ingredient_count(self) -> int:
        return (
            self.expired_count
            + self.within_one_day_count
            + self.within_three_days_count
            + self.within_seven_days_count
        )


@dataclass(frozen=True)
class RecommendationResult:
    recipe: object
    total_score: float
    inventory_score: float
    expiration_score: float
    favorite_score: float
    history_score: float
    recency_score: float
    cooking_time_score: float
    shortage_penalty: float
    recommendation_reasons: tuple[str, ...]
    inventory_statuses: tuple[RecipeInventoryStatus, ...]
    cooking_count: int
    last_cooked_at: datetime | None
    shortage_ingredient_count: int
    urgent_ingredient_count: int
    selected_servings: int | None


MODE_WEIGHTS = {
    "balanced": DEFAULT_RECOMMENDATION_WEIGHTS,
    "expiring": RecommendationWeights(
        expiration=2.0,
        cooking_time=0.5,
    ),
    "quick": RecommendationWeights(
        expiration=0.5,
        cooking_time=3.0,
    ),
    "in_stock": RecommendationWeights(
        inventory=2.0,
        shortage=3.0,
    ),
}


def validate_recommendation_weights(
    weights: RecommendationWeights,
) -> None:
    """UIから受け取る倍率が有限かつ0.0～3.0か検証する。"""
    values = (
        weights.expiration,
        weights.inventory,
        weights.favorite,
        weights.history,
        weights.recency,
        weights.cooking_time,
        weights.shortage,
    )
    if any(
        not isfinite(value) or not 0.0 <= value <= 3.0
        for value in values
    ):
        raise ValueError(
            "推薦の重みは0.0から3.0の有限値で指定してください。"
        )


def combine_recommendation_weights(
    mode: str,
    custom_weights: RecommendationWeights | None,
) -> RecommendationWeights:
    """mode別の重みとユーザー指定倍率を掛け合わせる。"""
    mode_weights = MODE_WEIGHTS[mode]
    if custom_weights is None:
        return mode_weights

    validate_recommendation_weights(custom_weights)
    return RecommendationWeights(
        expiration=mode_weights.expiration * custom_weights.expiration,
        inventory=mode_weights.inventory * custom_weights.inventory,
        favorite=mode_weights.favorite * custom_weights.favorite,
        history=mode_weights.history * custom_weights.history,
        recency=mode_weights.recency * custom_weights.recency,
        cooking_time=(
            mode_weights.cooking_time * custom_weights.cooking_time
        ),
        shortage=mode_weights.shortage * custom_weights.shortage,
    )


def get_recipe_history_summaries(
    db: Session,
) -> dict[int, RecipeHistorySummary]:
    """取り消されていない履歴だけをレシピ別に集計する。"""
    rows = (
        db.query(
            CookingHistory.recipe_id,
            func.count(CookingHistory.id),
            func.max(CookingHistory.cooked_at),
        )
        .filter(CookingHistory.undone_at.is_(None))
        .group_by(CookingHistory.recipe_id)
        .all()
    )
    return {
        recipe_id: RecipeHistorySummary(
            cooking_count=int(cooking_count),
            last_cooked_at=last_cooked_at,
        )
        for recipe_id, cooking_count, last_cooked_at in rows
    }


def calculate_expiration_score(
    statuses: list[RecipeInventoryStatus],
    today: date,
) -> ExpirationScore:
    """使用対象食材ごとに、最も近い有効期限を評価する。"""
    expired = 0
    one_day = 0
    three_days = 0
    seven_days = 0

    for status in statuses:
        if not status.is_automatically_checkable:
            continue

        active_dates = [
            lot.expiration_date
            for lot in status.recipe_ingredient.ingredient.inventories
            if lot.deleted_at is None
            and lot.quantity > 0
            and lot.expiration_date is not None
        ]
        if not active_dates:
            continue

        days = (min(active_dates) - today).days
        if days < 0:
            expired += 1
        elif days <= 1:
            one_day += 1
        elif days <= 3:
            three_days += 1
        elif days <= 7:
            seven_days += 1

    reasons: list[str] = []
    if expired:
        reasons.append(f"期限を過ぎた食材を{expired}種類使用")
    if one_day:
        reasons.append(f"1日以内に期限が来る食材を{one_day}種類使用")
    if three_days:
        reasons.append(f"3日以内に期限が来る食材を{three_days}種類使用")
    if seven_days:
        reasons.append(f"7日以内に期限が来る食材を{seven_days}種類使用")

    return ExpirationScore(
        score=(expired * 8 + one_day * 6 + three_days * 4 + seven_days * 2),
        expired_count=expired,
        within_one_day_count=one_day,
        within_three_days_count=three_days,
        within_seven_days_count=seven_days,
        reasons=tuple(reasons),
    )


def calculate_inventory_scores(
    statuses: list[RecipeInventoryStatus],
) -> tuple[float, float, int, tuple[str, ...]]:
    """充足割合と、不足種類数・不足割合による減点を返す。"""
    automatic = [
        status
        for status in statuses
        if status.is_automatically_checkable
    ]
    shortages = [
        status
        for status in automatic
        if status.status == "shortage"
    ]

    if not automatic:
        return 0.0, 0.0, 0, ()

    sufficient_count = len(automatic) - len(shortages)
    inventory_score = 10.0 if not shortages else 6.0 * sufficient_count / len(automatic)
    shortage_penalty = sum(
        4.0
        + 6.0
        * min(
            (status.shortage_quantity or 0.0)
            / (status.required_quantity or 1.0),
            1.0,
        )
        for status in shortages
    )

    reasons: list[str] = []
    if not shortages:
        reasons.append("必要な食材がすべて在庫にあります")
    else:
        reasons.append(f"不足している食材が{len(shortages)}種類あります")

    return inventory_score, shortage_penalty, len(shortages), tuple(reasons)


def calculate_history_score(cooking_count: int) -> float:
    """常連レシピが独占しないよう、5回で加点を頭打ちにする。"""
    return min(cooking_count, 5) * 0.5


def calculate_recency_score(
    last_cooked_at: datetime | None,
    now: datetime,
) -> tuple[float, str | None]:
    if last_cooked_at is None:
        return 2.0, "まだ作ったことのないレシピです"

    days = max((now.date() - last_cooked_at.date()).days, 0)
    if days >= 30:
        return 4.0, "最近30日以上作っていません"
    if days >= 14:
        return 2.0, "最近14日以上作っていません"
    if days >= 7:
        return 1.0, "最近7日以上作っていません"
    return 0.0, None


def calculate_cooking_time_score(minutes: int) -> tuple[float, str | None]:
    if minutes <= 10:
        return 4.0, "10分以内で作れます"
    if minutes <= 20:
        return 3.0, "20分以内で作れます"
    if minutes <= 30:
        return 2.0, "30分以内で作れます"
    return 0.0, None


def recommend_recipes(
    db: Session,
    target_servings: int | None = None,
    mode: str = "balanced",
    max_cooking_time: int | None = None,
    weights: RecommendationWeights | None = None,
    now: datetime | None = None,
) -> list[RecommendationResult]:
    """有効レシピを採点し、スコア降順・ID昇順で返す。"""
    if mode not in RECOMMENDATION_MODES:
        raise ValueError(f"未対応の推薦モードです: {mode}")
    if target_servings is not None and not 1 <= target_servings <= 100:
        raise ValueError("人数は1から100で指定してください。")
    if max_cooking_time not in {None, 10, 20, 30}:
        raise ValueError(
            "調理時間は10分、20分、30分のいずれかで指定してください。"
        )

    selected_weights = combine_recommendation_weights(
        mode=mode,
        custom_weights=weights,
    )
    evaluated_at = now or datetime.now()
    histories = get_recipe_history_summaries(db)
    results: list[RecommendationResult] = []

    recipes = get_recipes(db=db)
    if max_cooking_time is not None:
        recipes = [
            recipe
            for recipe in recipes
            if recipe.cooking_time_minutes <= max_cooking_time
        ]

    for recipe in recipes:
        selected_servings = None
        if recipe.yield_type == "servings":
            selected_servings = (
                target_servings
                if target_servings is not None
                else recipe.base_servings
            )
        statuses = build_recipe_inventory_statuses(
            recipe=recipe,
            target_servings=selected_servings,
        )
        expiration = calculate_expiration_score(statuses, evaluated_at.date())
        inventory_raw, shortage_raw, shortage_count, inventory_reasons = (
            calculate_inventory_scores(statuses)
        )
        history = histories.get(recipe.id, RecipeHistorySummary())
        history_raw = calculate_history_score(history.cooking_count)
        recency_raw, recency_reason = calculate_recency_score(
            history.last_cooked_at, evaluated_at
        )
        time_raw, time_reason = calculate_cooking_time_score(
            recipe.cooking_time_minutes
        )
        favorite_raw = 3.0 if recipe.is_favorite else 0.0

        expiration_score = expiration.score * selected_weights.expiration
        inventory_score = inventory_raw * selected_weights.inventory
        favorite_score = favorite_raw * selected_weights.favorite
        history_score = history_raw * selected_weights.history
        recency_score = recency_raw * selected_weights.recency
        cooking_time_score = time_raw * selected_weights.cooking_time
        shortage_penalty = shortage_raw * selected_weights.shortage
        reasons: list[str] = []
        if expiration_score:
            reasons.extend(expiration.reasons)
        if (
            inventory_score
            or shortage_penalty
        ):
            reasons.extend(inventory_reasons)
        if favorite_score:
            reasons.append("お気に入りのレシピです")
        if history_score:
            reasons.append(f"これまでに{history.cooking_count}回作っています")
        if recency_score and recency_reason:
            reasons.append(recency_reason)
        if cooking_time_score and time_reason:
            reasons.append(time_reason)

        results.append(
            RecommendationResult(
                recipe=recipe,
                total_score=(
                    expiration_score
                    + inventory_score
                    + favorite_score
                    + history_score
                    + recency_score
                    + cooking_time_score
                    - shortage_penalty
                ),
                inventory_score=inventory_score,
                expiration_score=expiration_score,
                favorite_score=favorite_score,
                history_score=history_score,
                recency_score=recency_score,
                cooking_time_score=cooking_time_score,
                shortage_penalty=shortage_penalty,
                recommendation_reasons=tuple(reasons),
                inventory_statuses=tuple(statuses),
                cooking_count=history.cooking_count,
                last_cooked_at=history.last_cooked_at,
                shortage_ingredient_count=shortage_count,
                urgent_ingredient_count=expiration.urgent_ingredient_count,
                selected_servings=selected_servings,
            )
        )

    return sorted(
        results,
        key=lambda result: (-result.total_score, result.recipe.id),
    )
