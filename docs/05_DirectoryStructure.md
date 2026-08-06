# Directory Structure

## 1. 目的

本書では、現在の実装とStep10で追加予定の買うものリストを含むディレクトリ構成を定義する。

---

## 2. 構成

```text
food-stock-app/
├── alembic/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── constants/
│   │   └── ingredient_options.py
│   ├── models/
│   │   ├── ingredient.py
│   │   ├── inventory.py
│   │   └── shopping_item.py          # Step10
│   ├── routers/
│   │   ├── ingredients.py
│   │   └── shopping_list.py          # Step10
│   ├── schemas/
│   │   ├── ingredient.py
│   │   └── shopping_item.py          # 必要に応じてStep10
│   ├── crud/
│   │   ├── ingredient.py
│   │   ├── inventory.py
│   │   └── shopping_item.py          # Step10
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
│   │       └── list.html              # Step10
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
│   ├── routers/
│   ├── services/
│   └── utils/
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
| `app/crud` | DB操作 |
| `app/schemas` | 入出力スキーマ |
| `app/services` | 複数処理を組み合わせるサービス |
| `app/utils` | 小さな共通処理 |
| `app/templates` | Jinja2テンプレート |
| `app/static` | CSS・JavaScript・画像 |
| `alembic` | DBマイグレーション |
| `tests` | 必要最小限の自動テスト |
| `docs` | 設計書 |

---

## 4. Step10で追加するファイル

| ファイル | 役割 |
|---|---|
| `app/models/shopping_item.py` | 買うものリストモデル |
| `app/crud/shopping_item.py` | 追加・取得・状態変更・削除 |
| `app/routers/shopping_list.py` | 買うものリストのルーティング |
| `app/templates/shopping_list/list.html` | 買うものリスト画面 |
| `tests/crud/test_shopping_item.py` | CRUDの主要テスト |
| `tests/routers/test_shopping_list.py` | 画面・ルートの主要テスト |

Pydanticスキーマが不要な単純フォーム処理の場合、`shopping_item.py`スキーマは無理に作成しない。

---

## 5. ルーティングの分割方針

- 食材・在庫一覧・消費期限：`app/routers/ingredients.py`
- 買うものリスト：`app/routers/shopping_list.py`
- 今後のレシピ：`app/routers/recipes.py`

機能が増えたため、すべてを`ingredients.py`へ詰め込まない。

---

## 6. テスト方針

- 既存機能をすべて細かく網羅することは目的としない
- 壊れると困る主要処理をテストする
- 画面レイアウトは手動確認する
- Step10では重複防止、状態変更、削除を優先する
