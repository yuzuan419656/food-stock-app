# Design Documents

## 1. 概要

本ディレクトリでは、食材在庫管理Webアプリケーションの設計書を管理する。

設計書は、現在の実装内容と次の開発予定が一致するように更新する。

---

## 2. 設計書一覧

| No. | ファイル | 内容 | 状態 |
|---|---|---|---|
| 00 | `00_ProjectOverview.md` | 概要・ロードマップ・進捗 | 更新済み |
| 01 | `01_Requirements.md` | 機能・非機能要件 | 更新済み |
| 02 | `02_Diagram.md` | ER図 | Step10設計反映 |
| 03 | `03_DBDesign.md` | DB詳細設計 | Step10設計反映 |
| 04 | `04_ScreenDesign.md` | 画面・遷移・URL | Step10設計反映 |
| 05 | `05_DirectoryStructure.md` | ディレクトリ構成 | 更新済み |
| 06 | `06_CodingRule.md` | 実装・テスト・Gitルール | 更新済み |

---

## 3. 現在地

### 完了

- 基本CRUD
- 検索・カテゴリ絞り込み・並び替え
- 在庫数量増減
- カテゴリ・単位候補
- 重複登録処理
- Alembic
- 消費期限管理
- 消費期限の常時入力・自動保存
- 期限状態表示
- 期限順ソート
- 必要最小限の自動テスト

### 次のStep

```text
Step10：買うものリスト
```

実装予定：

- 在庫一覧から複数選択
- 買うものリストへ追加
- 重複追加防止
- 購入済み切替
- 項目削除

---

## 4. 開発フェーズ

1. Phase1：在庫管理・買うものリスト
2. Phase2：レシピ管理・在庫照合
3. Phase3：レシートOCR
4. Phase4：外部API・AI
5. Phase5：Docker・PostgreSQL・AWS・ログイン等

家計簿は対象外とする。

---

## 5. 開発フロー

```text
設計書更新
    ↓
Issue作成
    ↓
featureブランチ作成
    ↓
実装・手動確認
    ↓
必要最小限のテスト
    ↓
Commit / Push
    ↓
Pull Request（base: develop）
    ↓
developへマージ
```

---

## 6. 更新ルール

- 実装変更時は関連する設計書も更新する
- DB変更時はDiagramとDBDesignを更新する
- 画面・URL変更時はScreenDesignを更新する
- ファイル追加時はDirectoryStructureを更新する
- Pull Request前に設計書と実装の整合性を確認する
