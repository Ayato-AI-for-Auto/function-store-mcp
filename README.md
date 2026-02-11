# Function Store MCP (Core Edition)

AIエージェント（Cursor, Claude, Gemini CLI 等）のための、個人開発特化型 **関数資産管理システム**。

## 概要

**Solo-MCP** は、AIエージェントが生成したPythonコードを「再利用可能な資産」として保存・検索・管理するためのMCPサーバーです。セマンティック検索、自動品質チェック、REST API、CI/CDパイプラインを備えた、プロダクションレベルの開発基盤を提供します。

## 主要機能

| 機能 | 説明 |
|:---|:---|
| **セマンティック検索** | Gemini Embedding API によるベクトル検索で、自然言語から関数を発見 |
| **Auto-Heal** | 説明文が低品質な場合、LLMが自動的に最適化された説明文を生成・適用 |
| **Quality Gate** | Ruff（Linter）+ Mypy（型チェック）+ AIコードレビューで登録前に品質を担保 |
| **Data Sanitizer** | 絵文字・全角スペースなど、ターミナル互換性を阻害する文字を自動除去 |
| **REST API** | FastAPI ベースの REST エンドポイント。APIキー認証によるセキュアなアクセス |
| **多言語説明生成** | Google GenAI (Gemma 3) による日英自動翻訳 |
| **バックグラウンド検証** | 登録後に自動でテストケースを実行し、ステータスを更新 |
| **バージョン管理** | 関数の更新履歴を自動保存。過去のバージョンにロールバック可能 |
| **ローカル実行環境** | `venv` + `subprocess` を使用した軽量・高速なテスト実行 |

## 🌍 公開ストア革命に参加せよ (Join the Revolution)

コードは自由であるべきだ。あなたの関数を世界に解放しよう。

1.  **起動:** `FunctionStore.bat` でダッシュボードを開く。
2.  **作成:** 便利な関数を作ってローカルに保存する。
3.  **同期:** ダッシュボードの **"Sync to Global"** ボタンを押す。
4.  **共有:** たったこれだけで、あなたのコードは世界中のエージェントから利用可能になる。

## クイックスタート

### 前提条件

- Windows 10/11
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)（推奨。未インストールの場合、起動時に案内が表示されます）

### 1. ワンクリック起動（推奨）

`FunctionStore.bat` をダブルクリックするだけで、以下がすべて自動実行されます：

1. 仮想環境の作成（初回のみ）
2. 依存関係のインストール（初回のみ）
3. ダッシュボードの起動

```bash
# または、コマンドラインから
./FunctionStore.bat
```

### 2. UIダッシュボードで初期設定

ダッシュボードの「Settings」タブで以下を入力:

1. **Google API Key**: [Google AI Studio](https://aistudio.google.com/app/apikey) で取得
2. **HuggingFace Token**（オプション）: TranslateGemma によるローカル翻訳機能を使用する場合に必要
3. **Quality Gate Model**: 品質チェック用LLM（デフォルト: `gemma-3-27b-it`）
4. **言語**: 日本語 / English

設定は `data/settings.json` に自動保存されます。

### 3. サーバー起動

```bash
# Stdioモード（Claude Desktop / Gemini CLI 等のMCPクライアント向け）
uv run python -m mcp_core.server

# SSEモード（HTTP APIサーバーとして利用）
uv run python -m mcp_core.server --transport sse --port 8001
```

### 4. REST API サーバー起動

```bash
# APIキーの生成
uv run python scripts/manage_keys.py generate --name "my-app"

# REST APIサーバー起動
uv run uvicorn mcp_core.api:app --host 0.0.0.0 --port 8000
```

### 5. MCP クライアントへの登録

`claude_desktop_config.json` に以下を追加:

```json
{
  "mcpServers": {
    "function-store": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_core.server"],
      "cwd": "/path/to/function-store-mcp"
    }
  }
}
```

> **Note**: API Key は `data/settings.json` から自動的に読み込まれるため、`env` セクションは不要です。

## 設定

すべての設定はUIダッシュボード経由で `data/settings.json` に保存されます。

| 設定項目 | 説明 | デフォルト |
|:---|:---|:---|
| `GOOGLE_API_KEY` | Gemini API Key（必須） | - |
| `FS_MODEL_NAME` | Embedding モデル | `models/gemini-embedding-001` |
| `FS_QUALITY_GATE_MODEL` | 品質チェック用LLMモデル | `gemma-3-27b-it` |
| `UI_LANG` | UIの言語 | `en` |

環境変数での上書きも可能ですが、基本的にはUIからの設定を推奨します。

## アーキテクチャ

```
mcp-core/
  mcp_core/           # コアロジック
    server.py         #   MCPサーバー (FastMCP)
    api.py            #   REST API (FastAPI)
    auth.py           #   APIキー認証
    logic.py          #   ビジネスロジック (CRUD)
    database.py       #   DuckDB データベース管理
    embedding.py      #   Gemini Embedding サービス
    quality_gate.py   #   品質チェック (Ruff + Mypy + AI Review)
    sanitizer.py      #   データサニタイズ
    translation.py    #   TranslateGemma 翻訳
    workers.py        #   バックグラウンドワーカー
    runtime_docker.py #   Docker実行環境
    config.py         #   設定管理
  frontend/           # Flet UIダッシュボード
  scripts/            # ユーティリティスクリプト
    manage_keys.py    #   APIキー管理CLI
    translator.py     #   翻訳バッチ処理
  cicd/               # CI/CD ツール
    local_ci.ps1      #   ローカルCI + Auto-Push
  .github/workflows/  # GitHub Actions
    ci.yml            #   CI (Lint / Type Check / Test)
    cd.yml            #   CD (Auto-Release EXE)
  tests/              # テストスイート (23項目)
  data/               # DBファイル、設定、モデルキャッシュ
  docs/               # 設計ドキュメント
```

詳細は [docs/DESIGN_DOC.md](docs/DESIGN_DOC.md) を参照してください。

## 開発

### ローカルCI

```powershell
# Lint + Type Check + Test を一括実行（全パスで自動 git push）
.\cicd\local_ci.ps1
```

### テスト

```bash
# 全テスト実行
uv run python -m pytest

# 特定のテストファイルを実行
uv run python -m pytest tests/test_integration.py -vv
```

### コード品質

```bash
# Linter
uv run ruff check mcp_core/

# Type Check
uv run mypy mcp_core/
```

## REST API リファレンス

| メソッド | エンドポイント | 説明 |
|:---|:---|:---|
| `POST` | `/functions/` | 関数を登録 |
| `GET` | `/functions/{name}` | 関数を取得 |
| `DELETE` | `/functions/{name}` | 関数を削除 |
| `POST` | `/search/` | セマンティック検索 |
| `GET` | `/functions/{name}/history` | バージョン履歴を取得 |

すべてのエンドポイントは `X-API-Key` ヘッダーによるAPIキー認証が必要です。

## トラブルシューティング

### `context deadline exceeded` エラー

MCPクライアント（Claude Desktop 等）がサーバーからの応答を待ちきれずにタイムアウトした場合に発生します。

**最も多い原因**: サーバーの通信モードとクライアントの期待するモードが不一致。

| 接続方法 | 期待される Transport |
|:---|:---|
| Claude Desktop（`command` 指定） | `stdio`（標準入出力） |
| HTTP API / ブラウザ | `sse`（Server-Sent Events） |

**解決策**: 起動時に `--transport stdio` を明示的に指定してください。

### DuckDB 関連のエラー

データベースファイルが破損した場合、`data/functions.db` を削除して再起動すると初期化されます。

## ライセンス

MIT License
