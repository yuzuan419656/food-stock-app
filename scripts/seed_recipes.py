"""レコメンド検証用の家庭料理レシピを冪等に投入する。"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.constants.recipe_options import (
    RECIPE_CUISINE_OPTIONS,
    RECIPE_DISH_CATEGORY_OPTIONS,
)
from app.crud.recipe import (
    RecipeIngredientInput,
    RecipeStepInput,
    create_recipe,
)
from app.database import SessionLocal
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.services.recipe_registration import (
    _normalized_name_key,
)


# 各分類5候補。既存レシピがある組み合わせは先頭から必要数だけ使う。
RECIPE_NAMES: dict[tuple[str, str], list[str]] = {
    ("和食", "主菜"): ["鶏の照り焼き", "豚の生姜焼き", "鮭の味噌焼き", "肉じゃが", "豆腐ハンバーグ"],
    ("和食", "副菜"): ["ほうれん草のおひたし", "きんぴらごぼう", "かぼちゃの煮物", "大根サラダ", "ひじきの炒め煮"],
    ("和食", "主食"): ["鮭のおにぎり", "きのこ炊き込みご飯", "親子丼", "焼きうどん", "梅しらすご飯"],
    ("和食", "汁物"): ["豆腐とわかめの味噌汁", "豚汁", "けんちん汁", "なめこの味噌汁", "白菜と鶏団子の汁物"],
    ("和食", "お菓子・デザート"): ["抹茶プリン", "みたらし団子", "さつまいも茶巾", "黒ごまアイス", "りんごの和風コンポート"],
    ("和食", "その他"): ["だし巻き卵", "茶碗蒸し", "おでん", "手巻き寿司", "焼きなす"],
    ("洋食", "主菜"): ["煮込みハンバーグ", "チキンソテー", "白身魚のムニエル", "ポークチャップ", "ミートボールのトマト煮"],
    ("洋食", "副菜"): ["ポテトサラダ", "ラタトゥイユ", "コールスロー", "ほうれん草のソテー", "きのこのマリネ"],
    ("洋食", "主食"): ["ナポリタン", "オムライス", "きのこクリームパスタ", "シーフードピラフ", "ミートソーススパゲッティ"],
    ("洋食", "汁物"): ["ミネストローネ", "コーンポタージュ", "オニオンスープ", "クラムチャウダー", "野菜コンソメスープ"],
    ("洋食", "お菓子・デザート"): ["りんごのパウンドケーキ", "ベイクドチーズケーキ", "カスタードプリン", "ガトーショコラ", "いちごヨーグルトムース"],
    ("洋食", "その他"): ["キッシュ", "カプレーゼ", "ブルスケッタ", "温野菜のチーズ焼き", "生ハムのサラダプレート"],
    ("中華", "主菜"): ["麻婆豆腐", "回鍋肉", "酢豚", "青椒肉絲", "八宝菜"],
    ("中華", "副菜"): ["中華風春雨サラダ", "もやしのナムル", "きゅうりの中華和え", "ザーサイと長ねぎの和え物", "白菜の中華炒め"],
    ("中華", "主食"): ["チャーハン", "天津飯", "中華あんかけ焼きそば", "担々麺", "五目おこわ"],
    ("中華", "汁物"): ["卵とコーンの中華スープ", "わかめと豆腐の中華スープ", "酸辣湯", "白菜と豚肉のスープ", "きのこの中華スープ"],
    ("中華", "お菓子・デザート"): ["杏仁豆腐", "ごま団子", "マンゴープリン", "中華風揚げパン", "ジャスミン茶ゼリー"],
    ("中華", "その他"): ["焼き餃子", "春巻き", "肉まん", "棒棒鶏", "海老蒸し餃子"],
    ("韓国料理", "主菜"): ["プルコギ", "ヤンニョムチキン", "豚キムチ炒め", "タッカルビ", "スンドゥブチゲ"],
    ("韓国料理", "副菜"): ["ほうれん草のナムル", "韓国風大根サラダ", "もやしナムル", "韓国風ポテトサラダ", "わかめの酢の物"],
    ("韓国料理", "主食"): ["石焼きビビンバ", "キンパ", "冷麺", "韓国風焼きうどん", "チーズキンパ"],
    ("韓国料理", "汁物"): ["わかめスープ", "ユッケジャンスープ", "韓国風大根スープ", "豆もやしのスープ", "キムチチゲ"],
    ("韓国料理", "お菓子・デザート"): ["ホットク", "韓国風きなこ餅", "ゆず茶ゼリー", "黒糖パッピンス", "米粉の薬菓風クッキー"],
    ("韓国料理", "その他"): ["チヂミ", "チャプチェ", "韓国風冷ややっこ", "トッポギ", "海鮮たっぷり韓国風蒸し料理"],
    ("エスニック", "主菜"): ["ガパオライス", "グリーンカレー", "ナシゴレン", "タンドリーチキン", "ココナッツ風味の白身魚煮"],
    ("エスニック", "副菜"): ["生春巻き", "タイ風春雨サラダ", "アボカドと豆のサラダ", "キャロットラペ", "スパイスひよこ豆サラダ"],
    ("エスニック", "主食"): ["フォー", "カオマンガイ", "トムヤムクン麺", "スパイス焼きそば", "ココナッツミルク粥"],
    ("エスニック", "汁物"): ["トムヤムクン", "ラクサ風スープ", "レンズ豆のスープ", "ココナッツ野菜スープ", "香草たっぷりチキンスープ"],
    ("エスニック", "お菓子・デザート"): ["マンゴーココナッツプリン", "チャイ風ミルクティーゼリー", "バナナ春巻き", "ココナッツ団子", "スパイス焼きバナナ"],
    ("エスニック", "その他"): ["サテ風串焼き", "スパイス焼き餃子", "ひよこ豆のディップ", "エスニック風オムレツ", "海老のハーブ蒸し"],
    ("その他", "主菜"): ["タコライス", "ロールキャベツ", "ジャンバラヤ", "スペイン風ミートボール", "フィッシュアンドチップス"],
    ("その他", "副菜"): ["豆とツナのサラダ", "焼き野菜のマリネ", "コブサラダ", "ピクルス盛り合わせ", "かぼちゃのスパイスサラダ"],
    ("その他", "主食"): ["タコス", "サンドイッチプレート", "パエリア", "バターライス", "野菜たっぷりラップサンド"],
    ("その他", "汁物"): ["豆と野菜のスープ", "クラムチャウダー風スープ", "具だくさんトマトスープ", "きのこと豆のポタージュ", "ハーブ香る野菜スープ"],
    ("その他", "お菓子・デザート"): ["フルーツタルト", "レモンケーキ", "チョコチップクッキー", "ヨーグルトパフェ", "シナモンアップル"],
    ("その他", "その他"): ["チーズフォンデュ", "フィンガーフード盛り合わせ", "野菜のグリルプレート", "自家製ピザ", "スモークサーモンのオードブル"],
}


INGREDIENTS: dict[str, tuple[str, str]] = {
    "鶏もも肉": ("肉類", "g"), "豚こま肉": ("肉類", "g"), "豚ひき肉": ("肉類", "g"),
    "合いびき肉": ("肉類", "g"), "牛こま肉": ("肉類", "g"), "鮭": ("魚介類", "g"),
    "白身魚": ("魚介類", "g"), "えび": ("魚介類", "g"), "あさり": ("魚介類", "g"),
    "豆腐": ("加工食品", "g"), "卵": ("卵", "個"), "牛乳": ("乳製品", "ml"),
    "ヨーグルト": ("乳製品", "g"), "じゃがいも": ("野菜", "個"), "玉ねぎ": ("野菜", "個"),
    "ひよこ豆": ("加工食品", "g"),
    "にんじん": ("野菜", "本"), "大根": ("野菜", "g"), "白菜": ("野菜", "g"),
    "キャベツ": ("野菜", "g"), "ほうれん草": ("野菜", "g"), "トマト": ("野菜", "個"),
    "なす": ("野菜", "個"), "きのこ": ("野菜", "g"), "長ねぎ": ("野菜", "本"),
    "きゅうり": ("野菜", "本"), "米": ("主食", "g"), "うどん": ("主食", "袋"),
    "パスタ": ("主食", "g"), "食パン": ("主食", "枚"), "春雨": ("加工食品", "g"),
    "小麦粉": ("製菓材料", "g"), "チーズ": ("乳製品", "g"), "バナナ": ("野菜", "本"),
    "りんご": ("野菜", "個"), "砂糖": ("調味料", "g"), "醤油": ("調味料", "ml"),
    "味噌": ("調味料", "g"), "塩": ("調味料", "g"), "こしょう": ("調味料", "g"),
    "サラダ油": ("調味料", "ml"), "ごま油": ("調味料", "ml"), "カレー粉": ("調味料", "g"),
}


CUISINE_POOLS = {
    "和食": ["鶏もも肉", "豚こま肉", "鮭", "豆腐", "大根", "にんじん", "長ねぎ", "きのこ", "米", "うどん"],
    "洋食": ["合いびき肉", "鶏もも肉", "白身魚", "卵", "じゃがいも", "玉ねぎ", "トマト", "キャベツ", "パスタ", "チーズ"],
    "中華": ["豚こま肉", "豚ひき肉", "えび", "豆腐", "白菜", "にんじん", "長ねぎ", "きゅうり", "米", "春雨"],
    "韓国料理": ["牛こま肉", "豚こま肉", "鶏もも肉", "豆腐", "白菜", "大根", "ほうれん草", "きゅうり", "米", "春雨"],
    "エスニック": ["鶏もも肉", "えび", "白身魚", "ひよこ豆", "トマト", "玉ねぎ", "にんじん", "きゅうり", "米", "パスタ"],
    "その他": ["豚ひき肉", "鶏もも肉", "鮭", "卵", "じゃがいも", "玉ねぎ", "キャベツ", "トマト", "食パン", "チーズ"],
}


def _ensure_ingredient(db: Session, name: str) -> Ingredient:
    key = _normalized_name_key(name)
    ingredient = next(
        (
            item
            for item in db.query(Ingredient).all()
            if _normalized_name_key(item.name) == key
        ),
        None,
    )
    if ingredient is not None:
        if not ingredient.is_active:
            raise ValueError(f"削除済み食材はseedに利用できません: {name}")
        return ingredient

    category, unit = INGREDIENTS[name]
    ingredient = Ingredient(
        name=name,
        category=category,
        default_unit=unit,
    )
    db.add(ingredient)
    db.flush()
    return ingredient


def _recipe_ingredients(
    db: Session,
    cuisine: str,
    category: str,
    variant: int,
) -> list[RecipeIngredientInput]:
    pool = CUISINE_POOLS[cuisine]
    if category == "主菜":
        count = 5
    elif category == "副菜":
        count = 4
    elif category == "汁物":
        count = 4
    elif category == "お菓子・デザート":
        count = 4
    else:
        count = 4
    selected = [pool[(variant + index) % len(pool)] for index in range(count)]
    # 料理ごとに調味料を1～2品添え、材料の役割を明示する。
    selected.append("塩")
    if category in {"主菜", "主食", "その他"}:
        selected.append("醤油")

    result: list[RecipeIngredientInput] = []
    for index, name in enumerate(dict.fromkeys(selected), start=1):
        ingredient = _ensure_ingredient(db, name)
        if ingredient.category == "調味料":
            result.append(
                RecipeIngredientInput(
                    ingredient_id=ingredient.id,
                    quantity=None,
                    quantity_text="適量",
                    unit=None,
                    is_seasoning=True,
                    is_inventory_consumed=False,
                    display_order=index,
                )
            )
        else:
            quantity = 120.0 if ingredient.default_unit == "g" else 1.0
            if ingredient.default_unit == "ml":
                quantity = 100.0
            result.append(
                RecipeIngredientInput(
                    ingredient_id=ingredient.id,
                    quantity=quantity,
                    unit=ingredient.default_unit,
                    is_seasoning=False,
                    is_inventory_consumed=True,
                    display_order=index,
                )
            )
    return result


def _steps(category: str) -> list[RecipeStepInput]:
    if category == "お菓子・デザート":
        descriptions = ["材料を計量して準備する。", "混ぜ合わせて形を整える。", "冷やすか焼いて仕上げる。", "食べやすく盛り付ける。"]
    elif category == "汁物":
        descriptions = ["材料を食べやすい大きさに切る。", "鍋でだしと材料を煮る。", "調味して火を止める。", "器に盛り付ける。"]
    elif category == "副菜":
        descriptions = ["材料を洗って切る。", "炒めるか和えて火を通す。", "調味料で味を整える。", "器に盛り付ける。"]
    else:
        descriptions = ["材料を食べやすい大きさに切る。", "フライパンまたは鍋で加熱する。", "調味料を加えて火を通す。", "器に盛り付ける。"]
    return [RecipeStepInput(step_number=i, description=text) for i, text in enumerate(descriptions, start=1)]


def seed_recipes(db: Session) -> int:
    """全分類を5件に揃え、追加件数を返す。"""
    existing_names = {
        _normalized_name_key(recipe.name)
        for recipe in db.query(Recipe).all()
    }
    counts = Counter(
        (recipe.cuisine_type, recipe.dish_category)
        for recipe in db.query(Recipe)
        .filter(Recipe.is_active.is_(True))
        .all()
    )
    added = 0
    for cuisine in RECIPE_CUISINE_OPTIONS:
        for category in RECIPE_DISH_CATEGORY_OPTIONS:
            needed = max(5 - counts[(cuisine, category)], 0)
            for variant, name in enumerate(
                RECIPE_NAMES[(cuisine, category)]
            ):
                if needed == 0:
                    break
                if _normalized_name_key(name) in existing_names:
                    continue
                ingredients = _recipe_ingredients(
                    db=db,
                    cuisine=cuisine,
                    category=category,
                    variant=variant,
                )
                fixed = category == "お菓子・デザート" and variant == 4
                create_recipe(
                    db=db,
                    name=name,
                    cooking_time_minutes=(
                        10 + ((variant + len(category)) % 4) * 10
                    ),
                    cuisine_type=cuisine,
                    dish_category=category,
                    yield_type="fixed" if fixed else "servings",
                    base_servings=None if fixed else (2 if variant % 2 == 0 else 4),
                    fixed_yield_text="12個" if fixed else None,
                    ingredients=ingredients,
                    steps=_steps(category),
                    is_favorite=False,
                )
                existing_names.add(_normalized_name_key(name))
                counts[(cuisine, category)] += 1
                needed -= 1
                added += 1
    return added


def main() -> None:
    db = SessionLocal()
    try:
        added = seed_recipes(db)
        db.commit()
        print(f"追加レシピ: {added}件")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
