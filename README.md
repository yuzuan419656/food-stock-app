# food-stock-app

## 概要

食材在庫管理を中心としたWebアプリケーションです。

まずは食材の登録・編集・削除・在庫管理を行えるシステムを開発します。
その後、レシートOCR・レシピ提案・家計簿などの機能を段階的に追加し、
日々の食材管理を支援するアプリケーションへ発展させる予定です。

## 開発目的

日常生活では、現在の在庫を正確に把握できず、
同じ食材を重複して購入したり、使い切れず廃棄してしまうことがあります。

本アプリでは、食材の在庫を簡単に管理できる仕組みを作ることで、
買い忘れ・重複購入・食品ロスの削減を目指します。

また、本プロジェクトを通して、FastAPI・SQLAlchemy・データベース設計・Git/GitHubを用いた
Webアプリケーション開発の流れを学ぶことも目的としています。

## 主な機能

### Phase1

* 食材マスタ管理
* 在庫管理
* 食材登録
* 食材編集
* 食材削除
* 在庫一覧表示
* 在庫数量更新

## 現在の実装状況

Step1として、食材在庫管理の基本機能を実装した。

- 食材一覧表示
- 食材新規登録
- 食材編集
- 食材削除
- 在庫数量の登録・更新
- 数量の0.5刻み入力
- カテゴリ・単位の入力候補表示
- 食材名検索
- 並び替え
- カテゴリによる絞り込み

### Phase2以降

* レシートOCR
* レシピマスタ
* レシピ検索
* 調理履歴
* 不足食材表示
* 家計簿
* 消費期限管理
* AWSデプロイ
* Docker対応
* ログイン機能
* マルチユーザー対応
* スマートフォン対応

## 使用技術

| 分野      | 使用技術                    |
| ------- | ----------------------- |
| 言語      | Python                  |
| フレームワーク | FastAPI                 |
| データベース  | SQLite                  |
| ORM     | SQLAlchemy              |
| フロントエンド | HTML / CSS / JavaScript |
| バージョン管理 | Git / GitHub            |
| デプロイ    | AWS（予定）                 |

## ローカルでの起動方法

### 1. リポジトリをクローンする

```bash
git clone git@github.com:yuzuan419656/food-stock-app.git
cd food-stock-app
```

### 2. 仮想環境を作成する

```bash
python -m venv .venv
```

### 3. 仮想環境を有効化する

WSL / Linux / macOS の場合：

```bash
source .venv/bin/activate
```

Windows PowerShell の場合：

```powershell
.venv\Scripts\Activate.ps1
```

### 4. 必要なライブラリをインストールする

```bash
pip install -r requirements.txt
```

### 5. FastAPIアプリケーションを起動する

```bash
uvicorn app.main:app --reload
```

### 6. ブラウザで確認する

以下のURLにアクセスする。

```text
http://127.0.0.1:8000
```

以下のようなレスポンスが表示されれば起動成功です。

```json
{"message":"Hello, food-stock-app!"}
```

## ドキュメント

設計書は `docs/` ディレクトリで管理します。

| ファイル                            | 内容       |
| ------------------------------- | -------- |
| `docs/00_ProjectOverview.md`    | プロジェクト概要 |
| `docs/01_Requirements.md`       | 要件定義     |
| `docs/02_Diagram.md`            | ER図      |
| `docs/03_DBDesign.md`           | データベース設計 |
| `docs/04_ScreenDesign.md`       | 画面設計     |
| `docs/05_DirectoryStructure.md` | ディレクトリ構成 |
| `docs/06_CodingRule.md`         | コーディング規約 |

## 開発方針

* 小さく作る
* まずは動くものを完成させる
* Phase1では食材在庫管理に集中する
* 設計書と実装内容の整合性を保つ
* featureブランチを作成して開発する

## ブランチ運用

本プロジェクトでは GitHub Flow を採用します。

```text
main
 └── develop
      └── feature/*
```

基本的な流れは以下の通りです。

```text
Issue作成
↓
featureブランチ作成
↓
設計・実装
↓
commit
↓
push
↓
Pull Request
↓
developへマージ
↓
区切りのよいタイミングでmainへマージ
```

## 今後の予定

1. DB接続設定の作成
2. SQLAlchemyモデルの作成
3. CRUD処理の作成
4. 食材一覧画面の実装
5. 食材登録機能の実装
6. 食材編集機能の実装
7. 食材削除機能の実装
