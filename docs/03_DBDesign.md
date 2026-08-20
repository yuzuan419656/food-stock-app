# Database Design

## 1. 目的

本書では、Phase1で実装した食材管理、在庫管理、購入日・消費期限管理、買うものリストに関するデータベース詳細設計を定義する。

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
| inventories | 実装済み | 在庫数量・購入日・消費期限 |
| shopping_items | 実装済み | 買うものリスト |

---

## 4. ingredients

| カラム | 型 | PK | NOT NULL | UNIQUE | 初期値 | 説明 |
|---|---|:---:|:---:|:---:|---|---|
| id | INTEGER | ○ | ○ | - | - | 食材ID |
| name | TEXT | - | ○ | ○ | - | 食材名 |
| category | TEXT | - | - | - | NULL | カテゴリ |
| default_unit | TEXT | - | - | - | NULL | 基本単位 |
| created_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 登録日時 |
| is_active | BOOLEAN | - | ○ | - | true | 有効状態 |
| deleted_at | DATETIME | - | - | - | NULL | 論理削除日時 |

### 論理削除

- 通常登録時は`is_active = true`、`deleted_at = NULL`とする
- 削除時は`is_active = false`とし、`deleted_at`へ削除日時を保存する
- 食材レコードおよび関連する在庫ロットは物理削除しない
- 通常の一覧・検索・選択候補では`is_active = true`のみを対象とする
- 復元時は`is_active = true`、`deleted_at = NULL`へ戻す

---

## 5. inventories


| カラム | 型 | PK | NOT NULL | FK | 初期値 | 制約・説明 |
|---|---|:---:|:---:|---|---|---|
| id | INTEGER | ○ | ○ | - | - | 在庫ロットID |
| ingredient_id | INTEGER | - | ○ | ingredients.id | - | 食材ID |
| quantity | REAL | - | ○ | - | 0 | 0以上・0.5刻み |
| purchase_date | DATE | - | ○ | - | 登録日 | 購入日 |
| expiration_date | DATE | - | - | - | NULL | 消費期限 |
| deleted_at | DATETIME | - | - | - | NULL | ロットの論理削除日時 |
| created_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 登録日時 |
| updated_at | DATETIME | - | ○ | - | CURRENT_TIMESTAMP | 更新日時 |

1つの食材に対して、購入日・消費期限の異なる複数の在庫ロットを登録する。

在庫合計、代表購入日、代表消費期限の計算では、`deleted_at IS NULL`かつ数量が0より大きいロットを対象とする。

- 合計数量：対象ロットの数量合計
- 代表購入日：対象ロットの最も古い購入日
- 代表消費期限：期限設定済み対象ロットの最も近い期限
- 減算順序：消費期限、購入日、登録日時、IDの昇順

---

## 6. shopping_items

| カラム | 型 | PK | NOT NULL | FK | UNIQUE | 初期値 | 説明 |
|---|---|:---:|:---:|---|:---:|---|---|
| id | INTEGER | ○ | ○ | - | - | - | リスト項目ID |
| ingredient_id | INTEGER | - | - | ingredients.id | ○ | NULL | 食材マスタ由来の食材ID |
| custom_name | TEXT | - | - | - | - | NULL | 手入力項目名 |
| is_purchased | BOOLEAN | - | ○ | - | - | false | 購入済み状態 |
| created_at | DATETIME | - | ○ | - | - | CURRENT_TIMESTAMP | 追加日時 |
| updated_at | DATETIME | - | ○ | - | - | CURRENT_TIMESTAMP | 更新日時 |

### 制約

- `ingredient_id`と`custom_name`のどちらか一方だけを設定する
- 食材マスタ由来の項目では`ingredient_id`を設定する
- 手入力項目では`custom_name`を設定する
- 同じ食材を複数回追加しない
- 同じ手入力項目を表記揺れを含めて複数回追加しない
- 食材を論理削除しても既存の買うものリスト項目は保持する
- 購入済みに変更しても在庫数量は変更しない

---

## 7. リレーション

```text
ingredients
    1 ─── N inventories
    1 ─── 0..1 shopping_items
```

`ingredients`と`inventories`は1対多とし、購入単位ごとに在庫ロットを管理する。

`shopping_items`は、食材マスタ由来の場合は`ingredient_id`を参照し、手入力の場合は`custom_name`を保持する。

---

## 8. インデックス

| テーブル | カラム | 目的 |
|---|---|---|
| ingredients | name | 食材検索 |
| inventories | ingredient_id | JOIN |
| inventories | expiration_date | 期限順ソート |
| shopping_items | ingredient_id | JOIN・重複判定 |
| shopping_items | is_purchased | 購入状態による表示 |

---

## 9. 設計方針

- テーブル名は複数形・スネークケース
- 主キーは`id`
- 外部キーは`<単数形>_id`
- 日時カラムは`created_at`と`updated_at`
- DB変更はAlembicで管理する
- SQLite固有機能へ過度に依存しない
- 未使用の将来カラムは先に追加しない
- 在庫は購入日・消費期限別のロットとして管理する
- 履歴から参照される食材と在庫ロットは論理削除する

---

## 10. 適用済みマイグレーション

Phase1では、主に次の変更をAlembicで管理する。

- 消費期限カラムの追加
- 買うものリストテーブルの追加
- 購入日カラムの追加
- 既存在庫データへの購入日の補完

マイグレーション適用：

- 在庫ロットへの論理削除日時の追加
- 買うものリストの手入力項目対応
- 食材への有効状態・論理削除日時の追加

```bash
alembic upgrade head
```

現在の適用状況確認：

```bash
alembic current
```
