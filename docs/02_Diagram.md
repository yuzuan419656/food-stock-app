# ER Diagram

## 1. 目的

本ドキュメントでは、Phase1で実装する食材在庫管理システムのデータ構造を定義する。

ER図を作成することで、テーブル間の関係を整理し、今後のDB設計・API設計・実装の土台とする。

---

# 2. テーブル一覧

## Ingredient（食材マスタ）

| カラム名 | 型（仮） | 説明 | Phase1 |
|----------|----------|------|:------:|
| id | INTEGER | 食材ID（PK） | ○ |
| name | TEXT | 食材名 | ○ |
| category | TEXT | 食材カテゴリ（野菜・肉・魚など） | ○ |
| default_unit | TEXT | 基本単位（個・g・本など） | ○ |
| created_at | DATETIME | 作成日時 | ○ |
| updated_at | DATETIME | 更新日時 | ○ |

---

## Inventory（在庫）

| カラム名 | 型（仮） | 説明 | Phase1 |
|----------|----------|------|:------:|
| id | INTEGER | 在庫ID（PK） | ○ |
| ingredient_id | INTEGER | 食材ID（FK） | ○ |
| quantity | REAL | 現在の在庫数量 | ○ |
| created_at | DATETIME | 作成日時 | ○ |
| updated_at | DATETIME | 更新日時 | ○ |

---

# 3. ER図

```text
Ingredient
-------------------------
id (PK)
name
category
default_unit
created_at
updated_at

        1
        │
        │
        │
        N

Inventory
-------------------------
id (PK)
ingredient_id (FK)
quantity
created_at
updated_at
```

---

# 4. テーブル概要

## Ingredient（食材マスタ）

食材の基本情報を管理するテーブル。

食材名・カテゴリ・基本単位など、頻繁には変更されない情報を保持する。

---

## Inventory（在庫）

現在保有している食材の在庫数量を管理するテーブル。

Ingredientテーブルと関連付けることで、各食材の現在の在庫数を管理する。

---

# 5. リレーション

- Ingredient.id を主キー（PK）とする
- Inventory.ingredient_id を外部キー（FK）として Ingredient.id を参照する
- Ingredient：Inventory = 1：N のリレーションとする

Phase1では同一食材の在庫を1件として扱う。
将来的に購入日・消費期限単位で在庫を分ける可能性を考慮し、Ingredient と Inventory は 1:N とする。

---

# 6. 設計方針

Phase1では、食材在庫管理システムとして必要最低限のテーブル構成とする。

将来的なOCR・レシピ提案・家計簿機能などの追加を考慮しつつ、まずはシンプルで保守しやすいデータベース設計を採用する。

また、変更されにくい情報（食材情報）と変更されやすい情報（在庫数量）を分離することで、拡張性と保守性を高める。

---

# 7. 将来拡張

Phase2以降では、以下のテーブルを追加予定である。

- Receipt（レシート）
- Recipe（レシピ）
- RecipeIngredient（レシピ食材）
- CookingHistory（調理履歴）
- HouseholdAccount（家計簿）
- User（ユーザー）
- Category（カテゴリマスタ）

また、Inventoryには将来的に以下の項目を追加する予定である。

- expiration_date（消費期限）
- purchase_date（購入日）