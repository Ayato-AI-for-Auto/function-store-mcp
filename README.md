# Function Store MCP

AIエージェント（Cursor, Claude, Gemini等）が生成したPython関数を「再利用可能な資産」として蓄積・検索・管理するためのローカル・ミドルウェアです。

## 主な特徴

- **Local-First**: DuckDBを使用し、ローカル環境で高速・安全に動作します。
- **Semantic Search**: Google Gemini Embeddingを使用した自然言語による高度な関数検索。
- **Quality Gate**: Ruffを使用した高速なコード品質チェック（Lint & Format）。
- **Unified Interface**: 
    - **MCP Server**: FastMCPプロトコルに対応し、AIエージェントから直接利用可能。
    - **Dashboard**: Fletベースの直感的な管理UI。
    - **API**: 他のアプリケーションからアクセス可能なREST API (FastAPI)。

## クイックスタート

### 1. 準備

本プロジェクトは `uv` パッケージマネージャーを推奨しています。

```powershell
# 依存関係のインストールと編集可能モードでのセットアップ
uv pip install -e .
```

### 2. 環境変数の設定

`.env` ファイルを作成し、Google AI (Gemini) のAPIキーを設定してください。

```text
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. 起動

Windows環境では、ルートにある `FunctionStore.bat` を実行するのが最も簡単です。

- **Dashboard (UI) を起動**:
  ```powershell
  python main.py
  # または
  FunctionStore.bat
  ```

- **MCP Server を起動**:
  ```powershell
  python main.py --server
  ```

## プロジェクト構造

```text
.
├── backend/
│   └── mcp_core/          # コアロジック
│       ├── api/           # REST API 層
│       ├── core/          # DB, Security, Config 基盤層
│       ├── engine/        # Logic, QualityGate, Embedding エンジン層
│       ├── runtime/       # コード実行環境管理
│       └── server.py      # FastMCP サーバー
├── frontend/
│   └── dashboard.py       # Flet ダッシュボード UI
├── docs/                  # 詳細設計ドキュメント
├── dev_tools/             # テストおよび開発ツール
├── main.py                # 統合エントリポイント
└── FunctionStore.bat      # Windows用ランチャー
```

## 開発者向けコマンド

本プロジェクトでは `dev_tools/dev.py` への統合が進められています（Horiemon's Reform）。

```powershell
# 統合開発コマンド (Lint, Format, Test を一括実行)
python dev_tools/dev.py

# 個別実行も可能 (uv経由)
python dev_tools/dev.py --lint-only
python dev_tools/dev.py --test-only
```

## カスタマイズ

詳細な内部仕様については、[docs/システム詳細設計書.md](docs/システム詳細設計書.md) を参照してください。

---
Created by Ayato AI & Horiemon Persona.
