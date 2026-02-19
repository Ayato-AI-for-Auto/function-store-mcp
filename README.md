# Function Store MCP

AIエージェント（Cursor, Cline, Antigravity等）が生成したPython関数を「再利用可能な資産」として蓄積・検索・管理するためのローカルMCPサーバーです。

## 主な特徴

- **Local-First**: DuckDB + FastEmbed (ONNX) でローカル完結。外部APIキー不要。
- **Semantic Search**: Jina Embeddings v2 による自然言語関数検索。
- **Quality Gate**: Ruff Lint + AST静的解析による自動品質チェック。
- **GitHub Sync**: GitHub Public Repositoryへの自動バックアップ＆共有。
- **Unified Interface**: MCP Server (stdio) / Dashboard (Flet) / REST API (FastAPI)

---

## クイックスタート

```powershell
git clone https://github.com/Ayato-AI-for-Auto/function-store-mcp.git
cd function-store-mcp
setup.bat        # 環境構築 + MCP自動登録
FunctionStore.bat  # Dashboard起動
```

`setup.bat` を実行すると、依存関係のインストールに加えて **Cursor / Antigravity / Claude Desktop への MCP サーバー登録が自動的に行われます。**

---

## MCP サーバー登録

### 自動登録（推奨）

| クライアント | 方式 | 操作 |
|---|---|---|
| **Cursor** | ワークスペース自動検出 | クローン後、プロジェクトを開くだけ |
| **Claude Desktop** | `setup.bat` で自動登録 | `setup.bat` 実行後、Claude Desktop を再起動 |
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

# Claude Desktop のみ登録
python register_mcp.py --claude

# 全クライアントから登録解除
python register_mcp.py --unregister
```

---

## 利用可能な MCP Tools

登録後、AIエージェントから以下のツールが利用できます：

| Tool | 説明 |
|---|---|
| `search_functions` | 自然言語で関数をセマンティック検索 |
| `save_function` | Python関数を保存（自動品質チェック付き） |
| `get_function` | 関数のソースコードを取得 |
| `get_function_details` | 関数の全メタデータを取得 |
| `delete_function` | 関数を削除 |
| `list_functions` | 関数一覧を取得（フィルタリング対応） |
| `get_function_history` | バージョン履歴を取得 |
| `get_dashboard_stats` | データベース統計を取得 |
| `import_function_pack` | JSON形式で一括インポート |

---

## トラブルシューティング

| 症状 | 対策 |
|---|---|
| `ModuleNotFoundError` | `--project` フラグのパスを確認。`uv pip install -e .` が実行済みか確認 |
| `connection refused` | stdio モードに切り替え（デフォルト） |
| 初回起動が遅い | Jina Embeddings モデル（約260MB）の初回ダウンロード中 |
| サーバーが応答しない | `python main.py --server` を手動実行してエラーを確認 |

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

Created by Ayato AI & Horiemon Persona.
