# Function Store MCP - System Design Document (Ver 4.0)

## 1. プロダクトコンセプト (Concept)

### 1.1 目的：チーム開発における「車輪の再開発」の撤廃
AIエージェントによるプログラミングにおける「同じようなロジックを何度もゼロから書き直す」無駄を、**チーム資産（Team Assets）** として共有管理することで解消する。

### 1.2 コアバリュー：Team Developerのための「集合知」
コードを単なるテキストではなく、**「Solo-MCP」** が保証する「動作検証済みのスキル（Ability）」として永続化し、チーム全体で共有する。
AIエージェントにとっての **「信頼できる共有長期記憶（Shared Hippocampus）」** を提供する。

---

## 2. システムアーキテクチャ (Architecture)

**Public-First / Local-Compute Architecture**
「重い処理はローカル（ユーザーのエッジ）」、「データはクラウド（Supabase）」に特化した構成。

```mermaid
graph TD
    User[User / AI Agent]
    
    subgraph "Frontend Layer"
        CLI[MCP Server (CLI)]
        Dashboard[Web Dashboard]
    end
    
    subgraph "Core-Logic Layer (mcp_core/)"
        Manager[Function Manager]
        Sync[Sync Engine]
        Exec[Local Runtime (venv)]
    end
    
    subgraph "Public Cloud (Supabase)"
        PublicDB[(Public Functions)]
        Auth[Supabase Auth]
    end
    
    subgraph "AI Services"
        Gemini[Gemini Embeddings API]
    end

    User <-->|JSON-RPC| CLI
    CLI --> Manager
    
    Manager -->|Save/Search| DuckDB[(Local Cache)]
    Manager -->|Sync| Sync
    
    Sync <-->|Public Sync| PublicDB
    
    Manager -->|Execute (Optional)| Exec
    Exec -->|Subprocess| UserEnv[User's Python Env]
```

---

## 3. 品質保証ポリシー (The "Fast-Pass" Policy)

**ユーザーの思考を止めない。**
保存は「0.1秒」で完了させる。品質チェックはあくまで「事後監査」または「任意実行」。

### 3.1 非同期監査 (Async Audit)
*   `save_function` は検証を待たずに完了する。
*   品質チェック（Lint/Type/Review）は、ユーザーが明示的に `verify_function` を呼んだ時、またはバックグラウンドで空き時間に実行される。

### 3.2 ランタイム (Local Runtime)
*   **Docker廃止**: Windows環境での互換性と速度を最優先。
*   **Standard Process**: Python標準の `venv` と `subprocess` を使用して、ユーザーのローカル環境でコードを実行する。
*   **Sandboxなし**: 「自分の書いたコードを自分のPCで動かす」原則。セキュリティはユーザーの責任範囲とする（プロンプトで警告）。

---

## 4. 機能要件 (Functional Requirements)

### 4.1 MCPツール (AI Agent Interface)
| ツール名 | 目的 | 入力 | 挙動概要 |
|:---|:---|:---|:---|
| **`save_function`** | **資産化** | `name`, `code`, `dependencies`, `test_cases` 等 | 品質ゲートを通過させ、結果（成功/失敗ログ）を返す。<br>**実行用ではない**ことをAIに明示。 |
| **`search_functions`** | **再利用** | `query` (自然言語) | ベクトル検索により、意図に合致する関数を検索する。<br>「車輪の再開発禁止」をAIに指示。 |
| **`get_function`** | **統合** | `name` | 関数のソースコード全文を返す。<br>AIはこのコードを自身のコンテキストに展開して使用する。 |

### 4.2 ダッシュボード (User Interface)
| 機能 | 詳細 |
|:---|:---|
| **Server Control** | サーバープロセスの起動・停止・ステータス監視。 |
| **Function Explorer** | 保存済み関数のリスト表示、詳細確認、削除機能。DuckDB直接参照。 |
| **Team Management** | **[New]** チーム作成・参加、同期状況の確認。 |
| **Settings** | Embeddingモデル (`gemini-embedding-001`) 、Quality Gateモデル、**[New] Supabase接続情報**の設定。 |

---

## 5. データモデル (Database Schema)

### 5.1 Local: DuckDB (`data/mcp.db`)
メタデータとベクトルを効率的に管理するローカルキャッシュ。

| Table | カラム構成 (抜粋) | 説明 |
|:---|:---|:---|
| `functions` | `id`, `name`, `code`, `description`, `version`, `updated_at` | 関数本体 |
| `embeddings` | `function_id`, `vector` | ベクトルデータ |

### 5.2 Cloud: Supabase (PostgreSQL)
チーム共有のための正規化されたデータベース (Phase 1 MVP)。
Supabaseの **New API Keys (Opaque Keys)** に完全準拠する。
- **sb_publishable_...**: クライアント側（参照用）。
- **sb_secret_...**: サーバー側（管理者権限用）。MCPサーバーではこちらを推奨。

#### Table: `teams`
| カラム名 | 型 | 説明 |
|:---|:---|:---|
| `id` | UUID | PK |
| `name` | TEXT | チーム名 |
| `created_at` | TIMESTAMPTZ | 作成日時 |

#### Table: `team_members`
| カラム名 | 型 | 説明 |
|:---|:---|:---|
| `team_id` | UUID | FK -> teams.id |
| `user_id` | UUID | FK -> auth.users.id |
| `role` | TEXT | 'admin', 'member' |

#### Table: `functions` (Shared)
| カラム名 | 型 | 説明 |
|:---|:---|:---|
| `id` | UUID | PK |
| `team_id` | UUID | FK -> teams.id |
| `name` | TEXT | 関数名 (Team内でUnique) |
| `version` | INTEGER | バージョン番号 |
| `code` | TEXT | ソースコード |
| `description` | TEXT | 説明 |
| `metadata` | JSONB | 依存関係、タグなど |
| `author_id` | UUID | 作成者 |
| `updated_at` | TIMESTAMPTZ | 更新日時 |

---

## 6. 非機能要件 (Non-Functional Requirements)

*   **Robustness (堅牢性):**
    *   ログ出力は `stderr` に限定し、MCPの `stdout` 通信を阻害しない。
    *   `uv` のインストールエラー、実行タイムアウト、構文エラーを明確に区別してハンドリングする。
*   **Performance (性能):**
    *   Gemini APIを使用することでローカルGPU/CPU負荷を排除し、安定した埋め込み生成を実現。
    *   2回目以降の実行は環境キャッシュにより **1秒以内** の検証完了を目指す。
*   **Usability (使いやすさ):**
    *   `FunctionStore.bat` という単一のエントリーポイント。
    *   黒い画面（コンソール）を見せない GUI ランチャー。
    *   BYOK (Bring Your Own Key) モデル。`GOOGLE_API_KEY` の設定が必要。

---

## 7. 同期戦略 (Sync Strategy)

**Sync Engine** は以下のポリシーでデータの整合性を保つ。

1.  **Trigger**:
    *   ユーザーが手動で「Sync」ボタンを押した時。
    *   `save_function` が成功した時（Auto-Sync有効時）。
    *   アプリ起動時。
2.  **Direction**:
    *   **Push**: ローカルの `created_at` がクラウドより新しい場合、クラウドを上書き (Version up)。
    *   **Pull**: クラウドに新しい関数がある、またはクラウドの `version` がローカルより大きい場合、ローカルに取り込む。
3.  **Conflict Resolution**:
    *   **Last Write Wins (LWW)**: タイムスタンプが新しい方を正とする。
    *   Phase 1では複雑なマージ競合解決は行わない。
