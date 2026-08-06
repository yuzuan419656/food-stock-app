# ER Diagram

## 1. 目的

本ドキュメントでは、現在の在庫管理機能とStep10で追加予定の買うものリストを含むデータ構造を定義する。

---

## 2. テーブル一覧

### Ingredient（食材マスタ）

| カラム | 型 | 説明 |
|---|---|---|
| id | INTEGER | 食材ID（PK） |
| name | TEXT | 食材名 |
| category | TEXT | カテゴリ |
| default_unit | TEXT | 基本単位 |
| created_at | DATETIME | 登録日時 |
| updated_at | DATETIME | 更新日時 |

### Inventory（在庫）

| カラム | 型 | 説明 |
|---|---|---|
| id | INTEGER | 在庫ID（PK） |
| ingredient_id | INTEGER | 食材ID（FK） |
| quantity | REAL | 現在の在庫数量 |
| expiration_date | DATE | 消費期限。未設定可 |
| created_at | DATETIME | 登録日時 |
| updated_at | DATETIME | 更新日時 |

### ShoppingItem（買うものリスト・Step10）

| カラム | 型 | 説明 |
|---|---|---|
| id | INTEGER | 買うものリストID（PK） |
| ingredient_id | INTEGER | 食材ID（FK、UNIQUE） |
| is_purchased | BOOLEAN | 購入済みか |
| created_at | DATETIME | 追加日時 |
| updated_at | DATETIME | 更新日時 |

---

## 3. ER図

```text
Ingredient
-------------------------
id (PK)
name (UNIQUE)
category
default_unit
created_at
updated_at

        1
        │
        ├─────────────── N

Inventory
-------------------------
id (PK)
ingredient_id (FK)
quantity
expiration_date
created_at
updated_at


Ingredient
        1
        │
        └────────────── 0..1

ShoppingItem
-------------------------
id (PK)
ingredient_id (FK, UNIQUE)
is_purchased
created_at
updated_at
```

---

## 4. リレーション

### IngredientとInventory

- `Inventory.ingredient_id` は `Ingredient.id` を参照する
- モデル上は1:Nを維持する
- 現在のPhase1では、1食材につき在庫レコード1件として扱う
- 購入日・期限別のロット管理は将来拡張とする

### IngredientとShoppingItem

- `ShoppingItem.ingredient_id` は `Ingredient.id` を参照する
- 1食材につき買うものリスト項目は最大1件とする
- `ingredient_id` にUNIQUE制約を付けて重複追加を防ぐ
- 食材削除時は関連する買うものリスト項目も削除する

---

## 5. 将来拡張

Phase2以降で次のテーブル追加を検討する。

- recipes
- recipe_ingredients
- cooking_histories
- receipts
- receipt_items
- users
- categories

購入日・期限単位の在庫管理を実装する場合は、Inventoryを在庫ロットとして再設計する。
