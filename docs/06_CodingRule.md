# Coding Rule

## 1. 目的

Python、FastAPI、SQLAlchemy、Jinja2、JavaScript、CSS、テスト、Git運用の基本ルールを定義する。

---

## 2. 基本方針

- シンプルで読みやすいコードを書く
- 1つの関数へ責務を詰め込みすぎない
- 設計書と実装内容を一致させる
- 過度に抽象化しない
- 未使用コード・importは削除する
- 個人利用・学習用途に合った実装量とする

---

## 3. Python

### 命名

| 対象 | ルール | 例 |
|---|---|---|
| ファイル | スネークケース | `shopping_item.py` |
| 関数・変数 | スネークケース | `get_shopping_items` |
| クラス | パスカルケース | `ShoppingItem` |
| 定数 | 大文字スネークケース | `EXPIRATION_WARNING_DAYS` |

### 書き方

- インデントはスペース4つ
- 型ヒントを可能な範囲で付ける
- コメントは「なぜ」を補足する
- 例外時は必要に応じてrollbackする
- 長い処理はCRUDやサービスへ分ける

---

## 4. FastAPI

### 配置

- 食材関連：`app/routers/ingredients.py`
- 買うものリスト：`app/routers/shopping_list.py`

### 役割

ルーターでは次を担当する。

- パラメータの受け取り
- 入力検証
- CRUD呼び出し
- TemplateResponse、RedirectResponse、JSONレスポンス

DB操作は原則として`app/crud`へ分ける。

### URL

| Method | URL | 処理 |
|---|---|---|
| GET | `/` | 在庫一覧 |
| POST | `/ingredients/{id}/expiration-date/auto` | 消費期限自動保存 |
| GET | `/shopping-list` | 買うものリスト |
| POST | `/shopping-list` | 食材追加 |
| POST | `/shopping-list/{id}/toggle` | 購入状態切替 |
| POST | `/shopping-list/{id}/delete` | 削除 |

非同期保存ではJSONを返し、通常のフォーム処理ではPOST後にリダイレクトする。

---

## 5. SQLAlchemy・Alembic

- モデルは`app/models`へ配置する
- テーブル名は複数形・スネークケース
- 主キーは`id`
- 外部キーは`<単数形>_id`
- DB変更はAlembicで管理する
- 自動生成されたマイグレーションを確認してから適用する
- 複数更新が必要な処理ではcommit単位を明確にする

---

## 6. CRUD

- 食材：`app/crud/ingredient.py`
- 在庫・期限：`app/crud/inventory.py`
- 買うものリスト：`app/crud/shopping_item.py`

関数名の例：

```python
get_shopping_items()
add_ingredients_to_shopping_list()
toggle_shopping_item()
delete_shopping_item()
```

ルーター内で直接複雑なqueryを書かない。

---

## 7. Jinja2・JavaScript

### Jinja2

- 共通部分は`base.html`
- 表示ロジックを複雑にしすぎない
- フォームの入れ子を作らない
- hidden入力で必要な一覧条件を保持する

### JavaScript

- 消費期限は`change`イベントで自動保存する
- `fetch`の成功・失敗を画面へ表示する
- 通信中は対象入力を一時的に無効化する
- 失敗時は保存前の値へ戻す
- JavaScriptが必須の機能には最低限のエラー表示を用意する

---

## 8. CSS

- クラス名は役割が分かる名前にする
- 既存クラスと重複する定義を増やさない
- 状態クラスを利用する

例：

```text
expiration-expired
expiration-expiring-soon
expiration-normal
expiration-unset
shopping-item-purchased
```

---

## 9. テスト

個人利用・学習用途のため、次を優先する。

- CRUDの重要処理
- 消費期限の判定・保存
- 消費期限順ソート
- 買うものリストの重複防止
- 購入状態切替
- 削除

細かなHTML配置やCSSは手動確認を中心とする。

実行：

```bash
python -m compileall app tests
pytest -v
```

---

## 10. Git運用

- `main`：安定版
- `develop`：開発統合
- `feature/*`：機能開発

例：

```text
feature/add-shopping-list
```

コミット例：

```text
feat: add shopping list
fix: prevent duplicate shopping items
docs: update phase1 design documents
test: add shopping list tests
```

Pull Requestは`develop`をbaseとする。Step完了後に必要に応じて`main`へ反映する。
