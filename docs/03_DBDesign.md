# Database Design

## 1. 目的

本書では、本システムで使用するデータベースの詳細設計を定義する。

ER図で定義したテーブルについて、各カラムのデータ型・制約・初期値などを定義する。

---

# 2. DBMS

| 項目 | 内容 |
|------|------|
| DBMS | SQLite 3 |
| ORM | SQLAlchemy 2.x |
| 将来 | PostgreSQLへ移行可能な設計とする |

---

# 3. テーブル一覧

| テーブル名 | 説明 |
|------------|------|
| ingredients | 食材マスタ |
| inventories | 在庫 |

---

# 4. ingredients

## テーブル概要

食材の基本情報を管理する。

### カラム定義

| カラム | 型 | PK | NOT NULL | UNIQUE | 初期値 | 制約 | 説明 |
|--------|----|----|----------|--------|--------|------|------|
| id | INTEGER | ○ | - | - | - | PRIMARY KEY AUTOINCREMENT | 食材ID |
| name | TEXT | - | ○ | ○ | - | - | 食材名 |
| category | TEXT | - | - | - | - | - | カテゴリ |
| default_unit | TEXT | - | - | - | - | - | 基本単位 |
| created_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | - | 登録日時 |
| updated_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | - | 更新日時 |

---

# 5. inventories

## テーブル概要

現在保有している食材の在庫を管理する。

### カラム定義

| カラム | 型 | PK | NOT NULL | FK | 初期値 | 制約 | 説明 |
|--------|----|----|----------|----|--------|------|------|
| id | INTEGER | ○ | - | - | - | PRIMARY KEY AUTOINCREMENT | 在庫ID |
| ingredient_id | INTEGER | - | ○ | ingredients.id | - | - | 食材ID |
| quantity | REAL | - | ○ | - | 0 | CHECK(quantity >= 0) | 現在の数量 |
| created_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | - | 登録日時 |
| updated_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | - | 更新日時 |

---

# 6. インデックス

| テーブル | 対象カラム | 目的 |
|----------|------------|------|
| ingredients | name | 食材検索の高速化 |
| inventories | ingredient_id | テーブル結合（JOIN）の高速化 |

---

# 7. 制約

## ingredients

- `name` は一意とする（UNIQUE）
- 食材名は必須項目とする

## inventories

- `ingredient_id` は `ingredients.id` を参照する外部キーとする
- 親データ削除時は **RESTRICT** とする
- `quantity` は **0以上** とする（CHECK制約）
- `quantity` の初期値は **0** とする

---

# 8. 設計方針

- SQLiteを利用する
- SQLAlchemyでORM管理する
- 将来的なPostgreSQL移行を考慮する
- テーブル名は複数形・スネークケースを採用する
- 拡張性を考慮し、監査カラム（created_at・updated_at）を各テーブルへ追加する
- updated_at はSQLAlchemy側で更新時に自動更新する。

---

# 9. 将来拡張

Phase2以降では以下のテーブルを追加予定。

- categories
- recipes
- recipe_ingredients
- cooking_history
- receipts
- receipt_items

---

# 10. 命名規則

| 項目 | ルール |
|------|--------|
| テーブル名 | 複数形・スネークケース（例：`ingredients`） |
| カラム名 | スネークケース（例：`created_at`） |
| 主キー | `id` |
| 外部キー | `<テーブル名の単数形>_id`（例：`ingredient_id`） |

---

# 11. Definition of Done

本設計書は以下を満たした時点で完成とする。

- テーブル一覧が定義されている
- 各テーブルのカラム定義が整理されている
- データ型・制約・初期値が定義されている
- インデックスが整理されている
- 将来拡張を考慮した設計となっている
- ER Diagramとの整合性が取れている
- SQLAlchemyのモデルクラスを実装できるレベルまで設計されている