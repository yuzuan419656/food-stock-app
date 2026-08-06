# Directory Structure

## 1. 目的

本書では、Phase1完成時点の実装を含むディレクトリ構成を定義する。

---

## 2. 構成

```text
food-stock-app/
├── alembic/
│   ├── versions/
│   └── env.py
├── app/
│   ├── main.py
│   ├── database.py
│   ├── constants/
│   │   └── ingredient_options.py
│   ├── models/
│   │   ├── ingredient.py
│   │   ├── inventory.py
│   │   └── shopping_item.py
│   ├── routers/
│   │   ├── ingredients.py
│   │   ├── ingredient_duplicates.py
│   │   ├── inventory.py
│   │   └── shopping_list.py
│   ├── schemas/
│   │   └── ingredient.py
│   ├── crud/
│   │   ├── ingredient.py
│   │   ├── inventory.py
│   │   └── shopping_item.py
│   ├── services/
│   │   └── ingredient_form.py
│   ├── utils/
│   │   ├── ingredient_name.py
│   │   └── quantity.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── ingredients/
│   │   │   ├── list.html
│   │   │   ├── new.html
│   │   │   ├── edit.html
│   │   │   ├── delete.html
│   │   │   └── duplicate_confirm.html
│   │   └── shopping_list/
│   │       └── list.html
│   └── static/
│       └── css/
│           └── style.css
├── docs/
│   ├── 00_ProjectOverview.md
│   ├── 01_Requirements.md
│   ├── 02_Diagram.md
│   ├── 03_DBDesign.md
│   ├── 04_ScreenDesign.md
│   ├── 05_DirectoryStructure.md
│   ├── 06_CodingRule.md
│   └── README.md
├── tests/
│   ├── conftest.py
│   ├── crud/
│   │   ├── test_ingredient_expiration_sort.py
│   │   └── test_shopping_item.py
│   └── routers/
│       ├── test_ingredient_expiration.py
│       └── test_ingredient_purchase_date.py
├── alembic.ini
├── pytest.ini
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 3. 各ディレクトリの役割

| ディレクトリ | 役割 |
|---|---|
| `app/models` | SQLAlchemyモデル |
| `app/routers` | FastAPIルーティング |
| `app/crud` | データベース操作 |
| `app/schemas` | 入出力スキーマ |
| `app/services` | 複数処理を組み合わせるサービス |
| `app/utils` | 小さな共通処理 |
| `app/templates` | Jinja2テンプレート |
| `app/static` | CSS・JavaScript・画像 |
| `alembic` | DBマイグレーション |
| `tests` | 必要最小限の自動テスト |
| `docs` | 設計書 |

---

## 4. 主要ファイル

### モデル

| ファイル | 役割 |
|---|---|
| `app/models/ingredient.py` | 食材マスタ |
| `app/models/inventory.py` | 在庫数量・購入日・消費期限 |
| `app/models/shopping_item.py` | 買うものリスト |

### CRUD

| ファイル | 役割 |
|---|---|
| `app/crud/ingredient.py` | 食材の登録・取得・更新・削除・検索・並び替え |
| `app/crud/inventory.py` | 在庫数量・購入日・消費期限の操作 |
| `app/crud/shopping_item.py` | 買うものリストの追加・取得・状態変更・削除 |

### ルーター

| ファイル | 役割 |
|---|---|
| `app/routers/ingredients.py` | 食材一覧・登録・編集・削除・日付自動保存 |
| `app/routers/ingredient_duplicates.py` | 重複食材の上書き・数量追加・キャンセル |
| `app/routers/inventory.py` | 一覧画面からの在庫数量増減 |
| `app/routers/shopping_list.py` | 買うものリストの表示・追加・状態変更・削除 |

### テンプレート

| ファイル | 役割 |
|---|---|
| `app/templates/ingredients/list.html` | 在庫一覧 |
| `app/templates/ingredients/new.html` | 食材登録 |
| `app/templates/ingredients/edit.html` | 食材編集 |
| `app/templates/ingredients/delete.html` | 食材削除確認 |
| `app/templates/ingredients/duplicate_confirm.html` | 重複食材確認 |
| `app/templates/shopping_list/list.html` | 買うものリスト |

### テスト

| ファイル | 役割 |
|---|---|
| `tests/crud/test_ingredient_expiration_sort.py` | 消費期限順ソート |
| `tests/crud/test_shopping_item.py` | 買うものリストCRUD |
| `tests/routers/test_ingredient_expiration.py` | 消費期限表示・自動保存 |
| `tests/routers/test_ingredient_purchase_date.py` | 購入日保存・自動保存 |

---

## 5. ルーティングの分割方針

- 食材一覧・登録・編集・削除・日付自動保存：`app/routers/ingredients.py`
- 重複食材処理：`app/routers/ingredient_duplicates.py`
- 在庫数量の増減：`app/routers/inventory.py`
- 買うものリスト：`app/routers/shopping_list.py`
- 今後のレシピ：`app/routers/recipes.py`

機能ごとにルーターを分割し、`ingredients.py`へすべての処理を集中させない。

---

## 6. スキーマ方針

現在はHTMLフォームとJinja2テンプレートを中心に利用している。

単純なフォーム処理については、Pydanticスキーマを無理に作成せず、必要性が生じた時点で追加する。

---

## 7. テスト方針

- 既存機能をすべて細かく網羅することは目的としない
- 壊れると困る主要処理をテストする
- 画面レイアウトは手動確認する
- 消費期限、購入日、買うものリストの主要処理を優先する
