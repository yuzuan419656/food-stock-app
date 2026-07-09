# Food Stock App

食材在庫管理を中心としたWebアプリケーション

---

# 概要

Food Stock App は、食材の在庫を簡単に管理するためのWebアプリケーションです。

まずは食材の登録・編集・削除・在庫管理ができるシステムを開発し、その後、レシートOCRやレシピ提案などの機能を段階的に追加していくことを予定しています。

本プロジェクトは、Python・FastAPI・データベース設計・AWSなどの技術を学習・実践することを目的とした個人開発プロジェクトです。

---

# 開発背景

日々の買い物では、

- 冷蔵庫にあることを忘れて同じ食材を購入してしまう
- 在庫状況を把握できず食品ロスが発生する
- 買い物前に冷蔵庫の中身を確認する手間がかかる

といった課題があります。

まずは食材の在庫を正確に管理できるシステムを開発し、その後、レシートOCRやレシピ提案機能を追加することで、より便利な食材管理アプリへ発展させることを目指します。

---

# 開発目標

## Phase1（MVP）

- 食材マスタ管理
- 在庫管理
- 食材CRUD機能
- 在庫一覧表示

## Phase2

- レシートOCR
- 消費期限管理
- 家計簿機能
- Docker対応
- AWSデプロイ

## Phase3

- レシピ提案
- 調理履歴
- ユーザー認証
- マルチユーザー対応
- スマートフォン対応

---

# 主な機能（Phase1）

- 食材登録
- 食材編集
- 食材削除
- 食材検索
- 在庫一覧表示
- 在庫数量更新

---

# 使用技術

| 分野 | 技術 |
|------|------|
| Language | Python |
| Framework | FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Frontend | HTML / CSS / JavaScript |
| Version Control | Git / GitHub |
| Deployment | AWS（予定） |

---

# データベース

現在は以下の2テーブルで構成しています。

- ingredients（食材マスタ）
- inventories（在庫）

将来的には以下のテーブルを追加予定です。

- recipes
- recipe_ingredients
- cooking_history
- receipts
- receipt_items

---

# プロジェクト構成

```text
food-stock-app/
│
├── app/                # アプリケーション
├── docs/               # 設計書
├── tests/              # テストコード
├── scripts/            # 補助スクリプト
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 設計書

設計書は `docs/` ディレクトリで管理しています。

| ドキュメント | 内容 |
|--------------|------|
| 00_ProjectOverview.md | プロジェクト概要 |
| 01_Requirements.md | 要件定義 |
| 02_Diagram.md | ER図 |
| 03_DBDesign.md | データベース設計 |
| 04_FunctionList.md | 機能一覧（作成予定） |

---

# 開発フロー

GitHub Flow を採用しています。

```text
main
│
└── develop
     │
     └── feature/xxxx
```

開発ルール

- GitHub Issueを作成してから開発を開始
- 機能ごとにfeatureブランチを作成
- Pull Requestを経由してdevelopへマージ
- 各開発ステップ完了後にmainへ反映

---

# 開発ロードマップ

## Step0

- [x] Project Overview
- [x] Requirements
- [x] ER Diagram
- [x] Database Design
- [ ] Function List
- [ ] API Design

## Step1

- [ ] FastAPI環境構築
- [ ] SQLite接続
- [ ] SQLAlchemy導入
- [ ] 食材CRUD
- [ ] 在庫一覧画面

## Step2以降

- [ ] レシートOCR
- [ ] レシピ提案
- [ ] 調理履歴
- [ ] 消費期限管理
- [ ] 家計簿機能
- [ ] AWSデプロイ

---

# 今後の拡張予定

- レシートOCRによる自動登録
- レシピ提案機能
- 調理履歴管理
- PostgreSQLへの移行
- Docker対応
- AWSデプロイ
- マルチユーザー対応
- スマートフォン対応

---

# Project Vision

まずは自分一人が日常的に利用できる食材在庫管理システムを完成させることを目標としています。

その後、レシートOCRやレシピ提案などの機能を段階的に追加し、食材管理をより便利にするWebアプリケーションへ発展させる予定です。

本プロジェクトを通して、設計・実装・テスト・デプロイまで一連のWebアプリケーション開発を経験し、実践的なバックエンド開発スキルを身に付けることを目指します。