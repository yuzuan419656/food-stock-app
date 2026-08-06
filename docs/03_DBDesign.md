# Database Design

## 1. 目的

本書では、現在の在庫管理機能とStep10で追加予定の買うものリストに関するデータベース詳細設計を定義する。

---

## 2. DBMS

| 項目 | 内容 |
|---|---|
| DBMS | SQLite 3 |
| ORM | SQLAlchemy 2.x |
| マイグレーション | Alembic |
| 将来 | PostgreSQLへ移行可能な設計とする |

---

## 3. テーブル一覧

| テーブル | 状態 | 説明 |
|---|---|---|
| ingredients | 実装済み | 食材マスタ |
| inventories | 実装済み | 在庫数量・消費期限 |
| shopping_items | Step10で追加 | 買うものリスト |

---

## 4. ingredients

| カラム | 型 | PK | NOT NULL | UNIQUE | 初期値 | 説明 |
|---|---|:---:|:---:|:---:|---|---|
| id | INTEGER | ○ | ○ | - | - | 食材ID |
| name | TEXT | - | ○ | ○ | - | 食材名 |
| category | TEXT | - | - | - | NULL | カテゴリ |
| default_unit | TEXT | - | - | - | NULL | 基本単位 |
| created_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 登録日時 |
| updated_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 更新日時 |

---

## 5. inventories

| カラム | 型 | PK | NOT NULL | FK | 初期値 | 制約・説明 |
|---|---|:---:|:---:|---|---|---|
| id | INTEGER | ○ | ○ | - | - | 在庫ID |
| ingredient_id | INTEGER | - | ○ | ingredients.id | - | 食材ID |
| quantity | REAL | - | ○ | - | 0 | 0以上 |
| expiration_date | DATE | - | - | - | NULL | 消費期限 |
| created_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 登録日時 |
| updated_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 更新日時 |

現在は1食材につき在庫レコード1件として利用する。モデル上は将来のロット管理を考慮して1:Nを維持する。

---

## 6. shopping_items（Step10）

| カラム | 型 | PK | NOT NULL | FK | UNIQUE | 初期値 | 説明 |
|---|---|:---:|:---:|---|:---:|---|---|
| id | INTEGER | ○ | ○ | - | - | - | リスト項目ID |
| ingredient_id | INTEGER | - | ○ | ingredients.id | ○ | - | 対象食材 |
| is_purchased | BOOLEAN | - | ○ | - | - | false | 購入済み状態 |
| created_at | DATETIME | - | ○ | - | - | CURRENT_TIMESTAMP | 追加日時 |
| updated_at | DATETIME | - | ○ | - | - | CURRENT_TIMESTAMP | 更新日時 |

### 制約

- `ingredient_id`はUNIQUEとする
- 同じ食材を複数回追加しない
- 食材削除時は関連項目を削除する
- 購入済みに変更してもInventory.quantityは変更しない

---

## 7. インデックス

| テーブル | カラム | 目的 |
|---|---|---|
| ingredients | name | 食材検索 |
| inventories | ingredient_id | JOIN |
| inventories | expiration_date | 期限順ソート |
| shopping_items | ingredient_id | JOIN・重複判定 |
| shopping_items | is_purchased | 購入状態による表示 |

---

## 8. 設計方針

- テーブル名は複数形・スネークケース
- 主キーは`id`
- 外部キーは`<単数形>_id`
- 日時カラムは`created_at`と`updated_at`
- DB変更はAlembicで管理する
- SQLite固有機能へ過度に依存しない
- 未使用の将来カラムは先に追加しない

---

## 9. Step10マイグレーション予定

```bash
alembic revision --autogenerate -m "create shopping items table"
alembic upgrade head
```

自動生成後は、UNIQUE制約、外部キー、削除時動作を必ず確認する。
