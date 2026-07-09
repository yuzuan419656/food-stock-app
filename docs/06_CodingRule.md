# Coding Rule

## 1. 目的

本書では、食材在庫管理Webアプリケーションを実装する際のコーディング規約を定義する。

Python、FastAPI、SQLAlchemy、Jinja2テンプレート、CSS、Git運用に関する基本ルールを整理し、実装時の書き方を統一することを目的とする。

---

## 2. 対象範囲

本規約は、Phase1（MVP）で実装する以下の範囲を対象とする。

* Pythonコード
* FastAPIのルーティング
* SQLAlchemyモデル
* Pydanticスキーマ
* CRUD処理
* Jinja2テンプレート
* CSS
* Gitブランチ運用
* コミットメッセージ

---

## 3. 基本方針

本プロジェクトでは、以下の方針で実装を行う。

* シンプルで読みやすいコードを書く
* 1つのファイル・関数に責務を詰め込みすぎない
* 設計書と実装内容の整合性を保つ
* まずはPhase1の完成を優先する
* 将来拡張しやすい構成を意識する
* 過度に複雑な実装は避ける

---

## 4. Pythonコーディング規約

### 4.1 命名規則

| 対象    | 命名ルール      | 例                 |
| ----- | ---------- | ----------------- |
| ファイル名 | スネークケース    | `ingredient.py`   |
| 変数名   | スネークケース    | `ingredient_name` |
| 関数名   | スネークケース    | `get_ingredients` |
| クラス名  | パスカルケース    | `Ingredient`      |
| 定数    | 大文字スネークケース | `DATABASE_URL`    |

---

### 4.2 コードの書き方

* インデントはスペース4つとする
* 変数名・関数名は意味が分かる名前にする
* 不要なコメントは書かない
* 処理が複雑な場合のみコメントを追加する
* 1つの関数に複数の役割を持たせすぎない
* 使用していないimportは削除する

---

### 4.3 コメントの方針

コメントは「何をしているか」よりも「なぜそうしているか」を補足する目的で書く。

悪い例：

```python
# 食材を取得する
ingredients = get_ingredients()
```

良い例：

```python
# 一覧画面で在庫数量も表示するため、IngredientとInventoryを結合して取得する
ingredients = get_ingredients_with_inventory()
```

---

## 5. FastAPI実装ルール

### 5.1 ルーティングの配置

FastAPIのルーティングは、機能ごとに `app/routers/` 配下へ配置する。

Phase1では、食材管理に関する処理を以下のファイルにまとめる。

```text
app/routers/ingredients.py
```

---

### 5.2 ルーティング命名

ルーティング関数は、処理内容が分かる名前にする。

| 処理         | 関数名の例                       |
| ---------- | --------------------------- |
| 食材一覧表示     | `list_ingredients`          |
| 食材登録画面表示   | `new_ingredient`            |
| 食材登録処理     | `create_ingredient`         |
| 食材編集画面表示   | `edit_ingredient`           |
| 食材更新処理     | `update_ingredient`         |
| 食材削除確認画面表示 | `confirm_delete_ingredient` |
| 食材削除処理     | `delete_ingredient`         |

---

### 5.3 URL設計

`04_ScreenDesign.md` で定義したURLと整合性を取る。

| HTTPメソッド | URL                        | 処理             |
| -------- | -------------------------- | -------------- |
| GET      | `/`                        | 食材一覧画面を表示する    |
| GET      | `/ingredients/new`         | 食材登録画面を表示する    |
| POST     | `/ingredients`             | 食材を登録する        |
| GET      | `/ingredients/{id}/edit`   | 食材編集画面を表示する    |
| POST     | `/ingredients/{id}/edit`   | 食材情報・在庫数量を更新する |
| GET      | `/ingredients/{id}/delete` | 食材削除確認画面を表示する  |
| POST     | `/ingredients/{id}/delete` | 食材を削除する        |

---

### 5.4 画面遷移の方針

登録・更新・削除が完了した場合は、食材一覧画面 `/` にリダイレクトする。

フォーム入力にエラーがある場合は、同じ画面にエラーメッセージを表示する。

---

## 6. SQLAlchemy実装ルール

### 6.1 モデルの配置

SQLAlchemyモデルは `app/models/` 配下へ配置する。

| テーブル          | モデルファイル                    | クラス名         |
| ------------- | -------------------------- | ------------ |
| `ingredients` | `app/models/ingredient.py` | `Ingredient` |
| `inventories` | `app/models/inventory.py`  | `Inventory`  |

---

### 6.2 モデル定義の方針

* テーブル名は複数形・スネークケースとする
* モデルクラス名は単数形・パスカルケースとする
* 主キーは `id` とする
* 外部キーは `<参照先の単数形>_id` とする
* `created_at` と `updated_at` を定義する
* `updated_at` は更新時に自動更新されるようにする

---

### 6.3 リレーション

`Ingredient` と `Inventory` は1:Nの関係とする。

Phase1では同一食材の在庫を1件として扱うが、将来的に購入日・消費期限単位で在庫を分ける可能性を考慮し、1:Nの構成を維持する。

---

## 7. Pydanticスキーマ実装ルール

### 7.1 スキーマの配置

Pydanticスキーマは `app/schemas/` 配下へ配置する。

```text
app/schemas/ingredient.py
```

---

### 7.2 スキーマ命名

| 用途   | クラス名の例             |
| ---- | ------------------ |
| 食材登録 | `IngredientCreate` |
| 食材更新 | `IngredientUpdate` |
| 食材表示 | `IngredientRead`   |

---

### 7.3 バリデーション方針

以下のバリデーションを行う。

* 食材名は必須とする
* 在庫数量は0以上とする
* 同じ食材名は登録できない

---

## 8. CRUD処理実装ルール

### 8.1 CRUD処理の配置

DB操作処理は `app/crud/` 配下へ配置する。

```text
app/crud/ingredient.py
```

---

### 8.2 CRUD関数の命名

| 処理     | 関数名の例                  |
| ------ | ---------------------- |
| 食材一覧取得 | `get_ingredients`      |
| 食材1件取得 | `get_ingredient_by_id` |
| 食材登録   | `create_ingredient`    |
| 食材更新   | `update_ingredient`    |
| 食材削除   | `delete_ingredient`    |

---

### 8.3 責務分離

ルーティング関数内にDB操作処理を直接書きすぎない。

基本的には、ルーティングではリクエストの受け取りと画面表示を行い、DB操作は `crud` 配下の関数に分ける。

---

## 9. Jinja2テンプレート作成ルール

### 9.1 テンプレート配置

HTMLテンプレートは `app/templates/` 配下へ配置する。

| 画面       | テンプレート                                  |
| -------- | --------------------------------------- |
| 共通レイアウト  | `app/templates/base.html`               |
| 食材一覧画面   | `app/templates/ingredients/list.html`   |
| 食材登録画面   | `app/templates/ingredients/new.html`    |
| 食材編集画面   | `app/templates/ingredients/edit.html`   |
| 食材削除確認画面 | `app/templates/ingredients/delete.html` |

---

### 9.2 テンプレート方針

* 共通部分は `base.html` にまとめる
* 各画面は `base.html` を継承する
* HTML構造はできるだけシンプルにする
* 表示ロジックをテンプレートに書きすぎない
* 複雑な処理はPython側で行う

---

### 9.3 フォームの方針

* 登録画面と編集画面は同じ項目を使用する
* 入力項目名はDBカラム名とできるだけ対応させる
* 登録・更新・削除後は一覧画面 `/` に戻る

---

## 10. CSS作成ルール

### 10.1 CSS配置

CSSは以下のファイルに記述する。

```text
app/static/css/style.css
```

---

### 10.2 CSS方針

* Phase1ではシンプルな見た目を優先する
* 過度な装飾は行わない
* 一覧画面が見やすいことを重視する
* クラス名は意味が分かる名前にする
* 同じスタイルを何度も書かない

---

## 11. Git運用ルール

### 11.1 ブランチ運用

基本ブランチは以下とする。

| ブランチ        | 役割          |
| ----------- | ----------- |
| `main`      | 安定版         |
| `develop`   | 開発統合用       |
| `feature/*` | 機能追加・設計書作成用 |

---

### 11.2 作業開始時の流れ

作業開始時は、必ず `develop` を最新化してからfeatureブランチを作成する。

```bash
git switch develop
git pull origin develop
git switch -c feature/作業名
```

---

### 11.3 作業完了時の流れ

作業完了後は、commit、push、Pull Requestを行う。

```bash
git add .
git commit -m "コミットメッセージ"
git push origin feature/作業名
```

Pull Requestは `develop` 向けに作成する。

---

### 11.4 ブランチ削除

Pull Requestがマージされたfeatureブランチは削除する。

ローカルブランチを削除する場合は以下を実行する。

```bash
git switch develop
git pull origin develop
git branch -d feature/作業名
```

---

## 12. コミットメッセージルール

コミットメッセージは、何を変更したかが分かる内容にする。

### 12.1 基本形式

```text
動詞 + 変更内容
```

例：

```text
Add screen design document
Update database design
Fix README file names
Create ingredient model
```

---

### 12.2 よく使う動詞

| 動詞         | 用途          |
| ---------- | ----------- |
| `Add`      | 新規追加        |
| `Update`   | 内容更新        |
| `Fix`      | 不具合修正       |
| `Remove`   | 削除          |
| `Create`   | ファイル・機能作成   |
| `Refactor` | 振る舞いを変えない整理 |

---

## 13. 設計書更新ルール

実装中に設計変更が発生した場合は、関連する設計書も更新する。

例：

| 変更内容          | 更新する設計書                                       |
| ------------- | --------------------------------------------- |
| 画面を追加した       | `04_ScreenDesign.md`                          |
| テーブルやカラムを変更した | `02_Diagram.md`, `03_DBDesign.md`             |
| ディレクトリ構成を変更した | `05_DirectoryStructure.md`                    |
| 実装ルールを変更した    | `06_CodingRule.md`                            |
| 機能のスコープを変更した  | `00_ProjectOverview.md`, `01_Requirements.md` |

---

## 14. Definition of Done

本規約は以下を満たした時点で完成とする。

* Pythonコードの基本ルールが定義されている
* FastAPIの実装方針が整理されている
* SQLAlchemyの実装方針が整理されている
* Pydanticスキーマの方針が整理されている
* Jinja2テンプレートの作成ルールが整理されている
* CSSの基本ルールが整理されている
* Git運用ルールが整理されている
* コミットメッセージの方針が定義されている
* DirectoryStructureとの整合性が取れている
