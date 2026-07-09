# Directory Structure

## 1. 目的

本書では、食材在庫管理Webアプリケーションのディレクトリ構成を定義する。

実装時にファイルの配置場所や役割で迷わないようにし、保守しやすく拡張しやすい構成を目指す。

---

## 2. 前提・対象範囲

本設計書では、Phase1（MVP）で実装する食材在庫管理機能を対象とする。

Phase1では、以下の機能を実装する。

* 食材一覧表示
* 食材登録
* 食材編集
* 食材削除
* 在庫数量管理

将来的にレシートOCR、レシピ提案、家計簿、ログイン機能などを追加する可能性があるため、機能ごとに拡張しやすい構成とする。

---

## 3. ディレクトリ構成

Phase1では、以下のディレクトリ構成を基本とする。

```text
food-stock-app/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ingredient.py
│   │   └── inventory.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── ingredients.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── ingredient.py
│   ├── crud/
│   │   ├── __init__.py
│   │   └── ingredient.py
│   ├── templates/
│   │   ├── base.html
│   │   └── ingredients/
│   │       ├── list.html
│   │       ├── new.html
│   │       ├── edit.html
│   │       └── delete.html
│   └── static/
│       └── css/
│           └── style.css
├── docs/
│   ├── 00_ProjectOverview.md
│   ├── 01_Requirements.md
│   ├── 02_Diagram.md
│   ├── 03_DBDesign.md
│   ├── 04_ScreenDesign.md
│   └── 05_DirectoryStructure.md
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 4. 各ディレクトリの役割

| ディレクトリ           | 役割                     |
| ---------------- | ---------------------- |
| `app/`           | アプリケーション本体のコードを配置する    |
| `app/models/`    | SQLAlchemyのモデルクラスを配置する |
| `app/routers/`   | FastAPIのルーティング処理を配置する  |
| `app/schemas/`   | Pydanticスキーマを配置する      |
| `app/crud/`      | データベース操作処理を配置する        |
| `app/templates/` | HTMLテンプレートを配置する        |
| `app/static/`    | CSSや画像などの静的ファイルを配置する   |
| `docs/`          | 設計書を配置する               |
| `tests/`         | テストコードを配置する            |

---

## 5. 各ファイルの役割

## 5.1 app配下

| ファイル              | 役割                       |
| ----------------- | ------------------------ |
| `app/main.py`     | FastAPIアプリケーションの起動ポイント   |
| `app/database.py` | DB接続設定、Session、Baseを定義する |

---

## 5.2 models配下

| ファイル                       | 役割                                   |
| -------------------------- | ------------------------------------ |
| `app/models/__init__.py`   | modelsディレクトリをPythonパッケージとして扱うためのファイル |
| `app/models/ingredient.py` | 食材マスタのSQLAlchemyモデルを定義する             |
| `app/models/inventory.py`  | 在庫のSQLAlchemyモデルを定義する                |

---

## 5.3 routers配下

| ファイル                         | 役割                                    |
| ---------------------------- | ------------------------------------- |
| `app/routers/__init__.py`    | routersディレクトリをPythonパッケージとして扱うためのファイル |
| `app/routers/ingredients.py` | 食材一覧・登録・編集・削除に関するルーティングを定義する          |

---

## 5.4 schemas配下

| ファイル                        | 役割                                    |
| --------------------------- | ------------------------------------- |
| `app/schemas/__init__.py`   | schemasディレクトリをPythonパッケージとして扱うためのファイル |
| `app/schemas/ingredient.py` | 食材登録・更新時に使用するPydanticスキーマを定義する        |

---

## 5.5 crud配下

| ファイル                     | 役割                                 |
| ------------------------ | ---------------------------------- |
| `app/crud/__init__.py`   | crudディレクトリをPythonパッケージとして扱うためのファイル |
| `app/crud/ingredient.py` | 食材・在庫に関するDB操作処理を定義する               |

---

## 5.6 templates配下

| ファイル                                    | 対応画面     | 役割                 |
| --------------------------------------- | -------- | ------------------ |
| `app/templates/base.html`               | 共通       | 各HTMLで共通利用するレイアウト  |
| `app/templates/ingredients/list.html`   | 食材一覧画面   | 食材と在庫数量を一覧表示する     |
| `app/templates/ingredients/new.html`    | 食材登録画面   | 新しい食材を登録するフォーム     |
| `app/templates/ingredients/edit.html`   | 食材編集画面   | 食材情報と在庫数量を編集するフォーム |
| `app/templates/ingredients/delete.html` | 食材削除確認画面 | 食材削除前の確認画面         |

---

## 5.7 static配下

| ファイル                       | 役割             |
| -------------------------- | -------------- |
| `app/static/css/style.css` | 画面の見た目を調整するCSS |

---

## 6. ScreenDesignとの対応

`04_ScreenDesign.md` で定義した画面とテンプレートファイルの対応は以下とする。

| 画面ID | 画面名      | URL                        | テンプレート                                  |
| ---- | -------- | -------------------------- | --------------------------------------- |
| S001 | 食材一覧画面   | `/`                        | `app/templates/ingredients/list.html`   |
| S002 | 食材登録画面   | `/ingredients/new`         | `app/templates/ingredients/new.html`    |
| S003 | 食材編集画面   | `/ingredients/{id}/edit`   | `app/templates/ingredients/edit.html`   |
| S004 | 食材削除確認画面 | `/ingredients/{id}/delete` | `app/templates/ingredients/delete.html` |

---

## 7. DBDesignとの対応

`03_DBDesign.md` で定義したテーブルとモデルファイルの対応は以下とする。

| テーブル          | モデルファイル                    | 役割         |
| ------------- | -------------------------- | ---------- |
| `ingredients` | `app/models/ingredient.py` | 食材マスタを管理する |
| `inventories` | `app/models/inventory.py`  | 在庫数量を管理する  |

---

## 8. ルーティング構成

Phase1では、食材管理に関するルーティングを `app/routers/ingredients.py` にまとめる。

| HTTPメソッド | URL                        | 処理内容           | 配置ファイル                       |
| -------- | -------------------------- | -------------- | ---------------------------- |
| GET      | `/`                        | 食材一覧画面を表示する    | `app/routers/ingredients.py` |
| GET      | `/ingredients/new`         | 食材登録画面を表示する    | `app/routers/ingredients.py` |
| POST     | `/ingredients`             | 食材を登録する        | `app/routers/ingredients.py` |
| GET      | `/ingredients/{id}/edit`   | 食材編集画面を表示する    | `app/routers/ingredients.py` |
| POST     | `/ingredients/{id}/edit`   | 食材情報・在庫数量を更新する | `app/routers/ingredients.py` |
| GET      | `/ingredients/{id}/delete` | 食材削除確認画面を表示する  | `app/routers/ingredients.py` |
| POST     | `/ingredients/{id}/delete` | 食材を削除する        | `app/routers/ingredients.py` |

---

## 9. 設計方針

本プロジェクトでは、以下の方針でディレクトリ構成を設計する。

* アプリケーション本体は `app/` 配下にまとめる
* DBモデルは `models/` に配置する
* ルーティングは `routers/` に配置する
* DB操作処理は `crud/` に配置する
* 入力データの検証用スキーマは `schemas/` に配置する
* HTMLテンプレートは `templates/` に配置する
* CSSなどの静的ファイルは `static/` に配置する
* 設計書は `docs/` に配置する
* 将来機能を追加しやすいよう、役割ごとにファイルを分離する

---

## 10. 将来拡張

Phase2以降で機能を追加する場合は、以下のようにディレクトリ・ファイルを追加する想定とする。

```text
app/
├── routers/
│   ├── receipts.py
│   ├── recipes.py
│   └── users.py
├── models/
│   ├── receipt.py
│   ├── recipe.py
│   └── user.py
├── schemas/
│   ├── receipt.py
│   ├── recipe.py
│   └── user.py
├── crud/
│   ├── receipt.py
│   ├── recipe.py
│   └── user.py
└── templates/
    ├── receipts/
    ├── recipes/
    └── users/
```

将来機能を追加する場合も、機能ごとに `routers`、`models`、`schemas`、`crud`、`templates` を分けることで、保守しやすい構成を維持する。

---

## 11. Definition of Done

本設計書は以下を満たした時点で完成とする。

* Phase1で必要なディレクトリ構成が定義されている
* 各ディレクトリの役割が整理されている
* 各主要ファイルの役割が整理されている
* ScreenDesignで定義した画面とテンプレート構成の整合性が取れている
* DBDesignで定義したテーブルとモデルファイルの対応が整理されている
* 将来拡張を考慮した構成になっている
