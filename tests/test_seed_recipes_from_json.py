import json

import pytest
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from scripts.seed_recipes_from_json import (
    SeedJSONValidationError,
    load_and_validate,
    seed_recipes_from_json,
)


JSON_PATH = "data/seed/food_stock_recipes_v1_30.json"


def test_seed_json_registers_30_recipes_and_relations(db_session: Session):
    definitions = load_and_validate(JSON_PATH)
    summary = seed_recipes_from_json(db_session, definitions)

    assert summary.new_recipe_count == 30
    assert db_session.query(Recipe).count() == 30
    assert db_session.query(RecipeIngredient).count() == 253
    assert db_session.query(RecipeStep).count() == 148
    assert {recipe.name for recipe in db_session.query(Recipe)} == {
        recipe["name"] for recipe in definitions
    }
    assert db_session.query(Ingredient).count() == 80

    meat = db_session.query(Recipe).filter(Recipe.name == "肉じゃが").one()
    oil = next(item for item in meat.ingredients if item.ingredient.name == "サラダ油")
    assert oil.is_seasoning is True
    assert oil.is_inventory_consumed is False
    assert oil.quantity == 5
    assert oil.unit == "ml"

    omelet = db_session.query(Recipe).filter(Recipe.name == "だし巻き卵").one()
    text_item = next(
        item for item in omelet.ingredients if item.quantity_text == "適量"
    )
    assert text_item.quantity is None


def test_seed_json_is_idempotent_and_reuses_ingredients(db_session: Session):
    definitions = load_and_validate(JSON_PATH)
    first = seed_recipes_from_json(db_session, definitions)
    second = seed_recipes_from_json(db_session, definitions)

    assert first.new_recipe_count == 30
    assert second.new_recipe_count == 0
    assert second.skipped_recipe_count == 30
    assert db_session.query(Recipe).count() == 30
    assert db_session.query(Ingredient).count() == 80


def test_seed_json_dry_run_does_not_change_db(db_session: Session):
    definitions = load_and_validate(JSON_PATH)
    summary = seed_recipes_from_json(db_session, definitions, dry_run=True)

    assert summary.new_recipe_count == 30
    assert summary.new_ingredient_count == 80
    assert db_session.query(Recipe).count() == 0
    assert db_session.query(Ingredient).count() == 0


def test_invalid_json_is_rejected_before_db_changes(tmp_path, db_session: Session):
    payload = json.loads(open(JSON_PATH, encoding="utf-8").read())
    payload["recipes"][0]["name"] = ""
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SeedJSONValidationError):
        definitions = load_and_validate(path)
        seed_recipes_from_json(db_session, definitions)

    assert db_session.query(Recipe).count() == 0
    assert db_session.query(Ingredient).count() == 0


def test_seed_json_rolls_back_when_commit_fails(db_session: Session, monkeypatch):
    definitions = load_and_validate(JSON_PATH)

    def fail_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="JSON seed登録に失敗しました"):
        seed_recipes_from_json(db_session, definitions)

    assert db_session.query(Recipe).count() == 0
    assert db_session.query(Ingredient).count() == 0
