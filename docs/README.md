# Design Documents

## 1. 概要

本ディレクトリでは、本プロジェクトで使用する設計書を管理する。

本プロジェクトでは、まず **食材在庫管理Webアプリケーション** を完成させ、その後レシートOCRやレシピ提案などの機能を段階的に追加していく。

設計書は上位設計から順番に作成・更新し、各設計書の整合性を保ちながら開発を進める。

---

# 2. 設計書一覧

| No. | ファイル | 内容 | 状態 |
|----|----------|------|------|
| 00 | ProjectOverview.md | プロジェクト概要・開発方針 | ✅ |
| 01 | Requirements.md | 要件定義 | ✅ |
| 02 | Diagram.md | ER図・テーブル概要 | ✅ |
| 03 | DBDesign.md | データベース詳細設計 | ✅ |
| 04 | ScreenDesign.md | 画面設計 | ⬜ |
| 05 | DirectoryStructure.md | ディレクトリ構成 | ⬜ |
| 06 | CodingRule.md | コーディング規約 | ⬜ |

---

# 3. 設計書の依存関係

各設計書は以下の順序で作成する。

```text
ProjectOverview
        │
        ▼
Requirements
        │
        ▼
Diagram（ER図）
        │
        ▼
Database Design
        │
        ▼
Screen Design
        │
        ▼
Directory Structure
        │
        ▼
Coding Rule
        │
        ▼
Implementation（実装）
```

上位の設計書を変更した場合は、依存する設計書についても必要に応じて修正を行う。

---

# 4. 設計書の役割

## Project Overview

プロジェクト全体の目的・スコープ・ロードマップを定義する。

---

## Requirements

システムが満たすべき機能要件・非機能要件を定義する。

---

## Diagram

ER図およびテーブル間のリレーションを定義する。

---

## Database Design

テーブル・カラム・制約・インデックスなどのデータベース詳細設計を定義する。

---

## Screen Design

画面一覧・画面遷移・各画面の役割を定義する。

---

## Directory Structure

プロジェクトのディレクトリ構成および各ディレクトリの役割を定義する。

---

## Coding Rule

命名規則・コーディング規約・Git運用ルールなどを定義する。

---

# 5. 開発フロー

本プロジェクトでは、以下の開発フローを採用する。

```text
Issue作成
      │
      ▼
featureブランチ作成
      │
      ▼
設計・実装
      │
      ▼
Commit
      │
      ▼
Push
      │
      ▼
Pull Request
（base: develop）
      │
      ▼
developへマージ
      │
      ▼
Step完了時のみ
mainへマージ
```

---

# 6. 設計書更新ルール

- 設計変更時は関連する設計書も更新する
- 設計書と実装内容の整合性を保つ
- Pull Request作成前に設計書の整合性を確認する
- Phaseの変更があった場合は ProjectOverview と Requirements を優先して更新する

---

# 7. 実装方針

本プロジェクトでは、小さく実装し、段階的に機能を追加する。

## Phase1

食材在庫管理アプリを完成させる。

- 食材マスタ
- 在庫管理
- CRUD機能
- 一覧表示

## Phase2

在庫管理機能を拡張する。

- レシートOCR
- 消費期限管理
- 家計簿
- AWSデプロイ

## Phase3

アプリケーションをサービスとして拡張する。

- ログイン機能
- マルチユーザー対応
- スマートフォン対応
- レシピ提案機能
- AI推薦

---

# 8. Design Principles

本プロジェクトでは以下の方針で開発を行う。

- 小さく作り、小さく改善する
- まずは動くものを完成させる
- 設計を重視して実装する
- 拡張しやすい設計を意識する
- 設計書と実装を常に一致させる
- GitHub Flowに沿って開発する