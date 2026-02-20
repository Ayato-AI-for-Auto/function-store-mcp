# Function Store MCP

AIエージェント（Cursor, Cline, Antigravity等）を通じて、**誰でも**プログラミング資産を蓄積・検索・再利用できるローカルMCPサーバーです。
エンジニアだけでなく、マーケター・デザイナー・ビジネスパーソンがAIと協働する時代の「**コード資産インフラ**」として設計されています。

> **設計思想**: **Hybrid Intelligence**。Local-First によるプライバシー保護と、Gemini API による高い精度を選択可能。`setup.bat` 一発で動く「Zero Friction」体験を維持します。

## 主な特徴

- **Hybrid Intelligence**: FastEmbed (768D) によるオフライン動作と、Gemini 1536D 埋め込みによる高精度検索を切り替え可能。
- **Smart Get & Cognitive Logic**: `smart_search_and_get` ツールにより、検索・選別・プロジェクトへの自動配置を1回で完結。Qwen (Local) と Gemini (Cloud) を使い分けるインテリジェント・ルーティング搭載。
- **Draft First UX**: 構文エラーや説明文の欠如を許容。AIが生成した不完全な「コードの種」を即座に保存・蓄積し、必要な時に呼び出して磨き上げる「下書き優先」のワークフローをサポート。使えない関数を受付拒否することで提供価値を上げるのではなく、検索システムを工夫して悪い関数の検索順位が落ちるようにすることで対応。
- **Invisible Master Architecture**: 複数プロセス間でのDBロック競合を自動回避。リーダー選挙により常に1つのプロセスがDBを安全に管理。
- **Quality Gate & Security**: Ruff Lint + Bandit による静的解析。APIキーなどの機密情報の自動スキャン。
- **Supported Languages**: Python (.py) and JavaScript (.js) (Future support for more).

## 対象ユーザー

| ペルソナ | 利用シナリオ |
|---|---|
| **非エンジニア** | AIエージェントが生成したスクリプトを自動保存・再利用 |
| **個人開発者** | 自作関数ライブラリの構築・車輪の再発明防止 |
| **AIエージェント** | MCPプロトコル経由で`save`/`search`を自律実行 |

---

## インストール方法

### A. ワンクリック実行 (.exe) - 推奨
Python のインストールや環境構築は不要です。最もシンプルに開始できます。

1.  [Releases](https://github.com/Ayato-AI-for-Auto/function-store-mcp/releases) から最新の `FunctionStore.exe` をダウンロード。
2.  実行するだけで Dashboard が起動します。
3.  Settings 画面から、お使いの AI エージェント（Cursor, Claude Desktop 等）へワンクリックで MCP 登録が可能です。

### B. ソースコードから実行 (開発者向け)
Python 3.12+ と `uv` が必要です。

```powershell
git clone https://github.com/Ayato-AI-for-Auto/function-store-mcp.git
cd function-store-mcp
setup.bat          # 環境構築 + MCP自動登録
FunctionStore.bat  # Dashboard起動
```

`setup.bat` を実行すると、依存関係のインストールに加えて **対話形式で MCP サーバーの登録先を選択できます（Cursor / Antigravity / Claude Desktop / Gemini CLI / 全部）。**

---

## MCP サーバー登録

### 自動登録（推奨）

| クライアント | 方式 | 操作 |
|---|---|---|
| **Cursor** | ワークスペース自動検出 | クローン後、プロジェクトを開くだけ |
| **Claude Desktop** | `setup.bat` で選択登録 | `setup.bat` 実行後、Claude Desktop を再起動 |
| **Gemini CLI** | `setup.bat` で選択登録 | `setup.bat` 実行後、`gemini` コマンドで `/mcp` を確認 |
| **Antigravity** | 手動登録 | 下記の JSON を設定 UI から追加 |
| **Cline** | 手動登録 | 下記の JSON を設定ファイルに追加 |

- Cursor はリポジトリに同梱された `.cursor/mcp.json` を自動検出します。
- Claude Desktop は `setup.bat` 内で `register_mcp.py` が実行され、`%APPDATA%\Claude\claude_desktop_config.json` に登録されます。

> **注意**: CursorとAntigravityは独自にグローバル設定ファイルを管理しており、外部スクリプトからの書き換えは上書きされます。Cursorはワークスペース設定で対応し、Antigravityは設定 UI からの添加が必要です。

### 手動登録（Cline / その他）

Cline やその他のクライアントは、以下の JSON を設定ファイルに追加してください。

```json
{
  "mcpServers": {
    "function-store": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:/Users/<YourUser>/path/to/function_store_mcp",
        "--no-sync",
        "python",
        "main.py",
        "--server"
      ]
    }
  }
}
```

| クライアント | 設定ファイルの場所 |
|---|---|
| Cline | VS Code サイドバー → Cline → 歯車 → MCP Servers → Edit MCP Settings |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` |
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| Cursor (グローバル) | `~/.cursor/mcp.json` |

> **重要**: `--project` フラグは必須です。これがないと `uv` が正しい仮想環境を見つけられず `ModuleNotFoundError` が発生します。パスは必ず自分の環境の絶対パスに書き換えてください。

### 登録の管理

```powershell
# 全クライアントに登録
python register_mcp.py

# Cursor グローバルのみ登録
python register_mcp.py --cursor

# Antigravity のみ登録
python register_mcp.py --antigravity

# Gemini CLI のみ登録
python register_mcp.py --gemini

# Claude Desktop のみ登録
python register_mcp.py --claude

# 全クライアントから登録解除
python register_mcp.py --unregister
```

---

## 利用可能な MCP Tools

登録後、AIエージェントから以下のツールが利用できます：

| Tool | 分類 | 説明 |
|---|---|---|
| `smart_search_and_get` | **メイン** | 自然言語で検索 -> 最適解の選別 -> プロジェクトへ自動配置を1発で実行 |
| `search_functions` | 探索用 | 既存の資産をセマンティック検索してブラウズ |
| `save_function` | 保存用 | 関数を保存（「下書き」保存対応。自動品質・セキュリティチェック付） |
| `get_function` | 取得用 | 関数のソースコード（依存関係の統合バンドル可）を取得 |
| `inject_local_package` | 配置用 | 指定した名前の関数を `local_pkg/` に物理エクスポート |
| `get_triage_list` | 診断用 | 修正の必要な下書きや低品質な関数をリストアップ |

-   **`smart_search_and_get(query, target_dir)`**: **推奨される唯一の入り口**。AIエージェントが「〜をするロジックが欲しい」と伝えるだけで、全ての工程を自動化します。
-   **`save_function(...)`**: 構文が不完全でも「下書き」として保存可能。説明文が空でもAIが補完します。

## スマート・アーキテクチャ (Invisible Master)

本システムは、複数のエディタやツールから同時に MCP が起動される「マルチプロセス環境」を前提に設計されています。

1.  **Leader (Master)**: 最初に起動した MCP プロセス。バックグラウンドサーバー（FastAPI）を立ち上げ、DBアクセスと重いタスク（Venv構築等）を一括管理。
2.  **Proxy**: 後から起動した別の MCP プロセス。マスターを自動検出し、リクエストを転送するプロキシとして動作。
3.  **Worker**: マスター内で動作する単一のタスクキュー。すべての書き込み操作を直列化し、DuckDB のロック競合を物理的に排除。
4.  **Idle Shutdown**: 30分間リクエストがない場合、マスタープロセスは自動的に終了し、リソースを解放します。
---

## ベストプラクティス：AIとの協働（Draft First）

本システムは、**「AIエージェントが生成した未完成の種を、いかに速く資産に変えるか」**、そして**「それをいかに楽に再利用するか」**に特化しています。

- **Draft First (下書き保存)**: 
    - 保存時に完璧なコードである必要はありません。構文エラーがあっても保存し、後で `smart_search_and_get` で呼び出した後に Cursor 等で修正する方が効率的です。
- **Smart Module Support**: 
    - 関数間の依存関係（同一プロジェクト内の別関数呼び出し）は自動で解決されます。`get_function` もしくは `smart_search_and_get` を使えば、必要な依存コードは全て統合された状態で提供されます。
- **外部ライブラリの明示**: 
    - `pip` でインストールが必要な外部ライブラリは `dependencies` に含めてください。導入時に自動検証・環境隔離が行われます。

## トラブルシューティング

| 症状 | 対策 |
|---|---|
| `ModuleNotFoundError` | `--project` フラグのパスを確認。`uv pip install -e .` が実行済みか確認 |
| `locked` (DuckDB lock) | **解決済み**: 自動リーダー選挙機能により、現在は複数プロセス起動でも発生しません。 |
| 初回起動が遅い | 多言語対応 Embeddings モデルの初回ダウンロード中、または初回 Venv 構築中。 |
| サーバーが応答しない | `mcp_core/infra/background_server.py` を手動実行してポート競合等を確認。 |

詳細: [MCP_CONNECTION_DIAGNOSIS_REPORT.md](docs/MCP_CONNECTION_DIAGNOSIS_REPORT.md)

---

## プロジェクト構造

```text
.
├── backend/mcp_core/      # コアロジック (DB, Engine, API, Server)
├── frontend/dashboard.py  # Flet UI
├── .vscode/mcp.json       # Antigravity 自動登録設定
├── .cursor/mcp.json       # Cursor 自動登録設定
├── register_mcp.py        # グローバル登録スクリプト
├── setup.bat              # 環境構築 + MCP自動登録
├── FunctionStore.bat      # Dashboard ランチャー
└── main.py                # 統合エントリポイント
```

## 開発者向け

```powershell
python dev_tools/dev.py              # Lint + Test 一括実行
./dev.bat --ship -m "commit message" # Lint + Test + Git Push
```

---

## Roadmap

| フェーズ | 目標 | 状態 |
|---|---|---|
| MVP | Local-First MCP Server + Dashboard | Done |
| Cognitive Logic | `smart_get` による完全自動化とAIルーティング | Done |
| Draft-First | 構文エラー・説明文なしの保存を許容するUX | Done |
| **Marketplace** | **Cursor / Antigravity マーケットプレイス登録** | Planned |

---

Created by Ayato AI & Horiemon Persona.
