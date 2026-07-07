# Project Overview

## 1. プロジェクト概要

食材在庫管理を中心としたWebアプリケーション。

まずは食材の登録・編集・削除・在庫管理を行えるシステムを開発する。
その後、レシートOCRやレシピ提案などの機能を段階的に追加し、食材管理をより便利にすることを目指す。

---

## 2. 開発背景・目的

まずは食材の在庫を正確に管理できるシステムを開発する。
その後、OCRによる自動登録やレシピ提案機能を追加し、
献立決定の負担軽減と食品ロス削減を目指す。

---

## 3. 開発目標

### Phase1

- 自分一人が日常的に利用できる食材在庫管理システムを完成させる
- 食材マスタ・在庫管理・CRUD機能を実装する

### Phase2

- AWSへデプロイし、どこからでも利用できるようにする
- 家計簿機能・消費期限管理などの機能を追加する

### Phase3

- ユーザー認証機能を追加する
- 複数ユーザー対応
- スマートフォン対応
- レシピ推薦機能の高度化

---

## 4. 対象ユーザー

### 現在

- 開発者本人

### 将来

- 一人暮らしの方
- 家族で食材を管理したい方
- 日々の献立を考えることに負担を感じている方

---

## 5. スコープ

### Phase1（MVP）

実装する機能

- 食材マスタ
- 在庫管理
- 在庫一覧
- 在庫更新

### Phase2

- OCR
- 家計簿機能
- 消費期限管理
- AWSデプロイ
- Docker対応

### Phase3

- ログイン機能
- マルチユーザー対応
- スマホ対応
- レシピ推薦機能

---

## 6. システム概要

本システムはブラウザ上で利用するWebアプリケーションとして開発する。

利用者は食材を手動で登録・編集・削除できる。

登録した食材は在庫情報として保存され、
一覧画面から現在の在庫状況を確認できる。

将来的にはOCRによる自動登録、
レシピ提案、
調理履歴管理などを追加する予定である。

---

## 7. 使用技術

| 分野 | 使用技術 |
|------|---------|
| Language | Python |
| Framework | FastAPI |
| Database | SQLite（将来 PostgreSQL） |
| ORM | SQLAlchemy |
| Frontend | HTML / CSS / JavaScript |
| Version Control | Git / GitHub |
| OCR | （今後選定） |
| Deployment | AWS（予定） |

---

## 8. ディレクトリ構成

```
food-stock-app/

├── app/
├── docs/
├── tests/
├── scripts/
├── README.md
├── requirements.txt
└── .gitignore
```

---

## 9. ブランチ運用

GitHub Flowを採用する。

```
main
│
├── develop
│
├── feature/project-overview
├── feature/requirements
├── feature/er-diagram
├── feature/api-design
└── feature/・・・
```

機能ごとにfeatureブランチを作成し、Pull Requestによるレビュー後にdevelopへマージする。

各Stepの完成時にdevelopをmainへマージする。

---

## 10. 開発ルール

- GitHub Issueを作成してから開発を開始する
- 機能ごとにfeatureブランチを作成する
- Pull Requestを作成してからマージする
- 各StepでDefinition of Done（完成条件）を設定する
- 小さな単位でコミットする
- 設計書を最新の状態に保つ

---

## 11. ロードマップ

Step0：設計

↓

Step1：在庫管理

↓

Step2：レシートOCR

↓

Step3：レシピ検索

↓

Step4：調理による在庫更新

↓

Step5：不足食材表示

↓

Step6：消費期限管理

↓

Step7：調理履歴

↓

Step8：家計簿

↓

Step9：AWSデプロイ

↓

Step10：マルチユーザー対応

## 12. Design Principles

- 小さく作り、小さく改善する
- 実際に自分が使える品質を目指す
- 拡張性を考慮した設計を行う
- コードよりも設計を優先する
- 機能追加しやすいデータベース設計を意識する
- 各Stepで動作する成果物を完成させる

## Project Vision

食材管理をできるだけ自動化し、献立決定の負担を軽減することで、食品ロスの削減と日々の生活を少し便利にする。
