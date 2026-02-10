# Solo-MCP - UI Design Document (Ver 1.1)

## 1. 概要

Flet (Flutter for Python) を使用した個人開発者向けダッシュボード。
`solo_mcp` サーバーの起動・停止、登録済み関数の閲覧、設定変更を提供する。

---

## 2. 画面構成

```
+-------------------+--------------------------------------+
|  NavigationRail   |          Main Content Area           |
|                   |                                      |
|  [Dashboard]      |  (Dashboard / Functions / Settings)  |
|  [Functions]      |                                      |
|  [Settings]       |                                      |
+-------------------+--------------------------------------+
```

| タブ | 説明 |
|:---|:---|
| **Dashboard** | サーバー制御とアクティビティログ表示 |
| **Functions** | 登録済み関数の一覧表示 |
| **Settings** | モデル選択、APIキー設定、言語切り替え |

---

## 3. コンポーネント階層

```
FunctionStoreApp (ft.Page)
├── NavigationRail
│   ├── dest_dashboard (Dashboard)
│   ├── dest_functions (Functions)
│   └── dest_settings (Settings)
│
└── main_content (ft.Container)
    └── ft.Stack
        ├── content_dashboard (ft.Column, visible=True/False)
        │   ├── dashboard_title
        │   ├── Status Card (status_icon, status_text, start_stop_btn)
        │   ├── logs_title
        │   └── log_list (ft.ListView)
        │
        ├── content_functions (ft.Column, visible=True/False)
        │   ├── functions_title
        │   ├── Refresh Button
        │   └── func_list_view (ft.ListView)
        │       └── ft.ListTile (per function)
        │
        └── content_settings (ft.Column, visible=True/False)
            ├── settings_title
            ├── model_dropdown (Embedding Model)
            ├── quality_gate_model_dropdown (Reviewer Model)
            ├── api_key_field (Google API Key)
            ├── lang_dropdown (Language)
            └── save_btn
```

---

## 4. 状態管理 (State)

| 変数名 | 型 | 説明 | 更新タイミング |
|:---|:---|:---|:---|
| `lang` | `str` | 現在の言語コード (`en` / `jp`) | 言語ドロップダウン変更時 |
| `t` | `dict` | 現在のローカライズ辞書 | `lang` 変更時に連動 |
| `process` | `subprocess.Popen` | サーバープロセスオブジェクト | 起動/停止時 |
| `is_running` | `bool` | サーバー稼働状態 | 起動/停止/異常終了時 |

---

## 5. 主要メソッド

| メソッド | 役割 |
|:---|:---|
| `build_ui()` | 全UIコンポーネントを構築 |
| `handle_rail_change(e)` | タブ切り替え処理。`visible` を制御 |
| `toggle_server(e)` | サーバー起動/停止のトグル |
| `start_server()` | `subprocess.Popen` でサーバー起動 |
| `stop_server()` | `process.terminate()` でサーバー停止 |
| `read_stream(stream)` | stderr/stdout をログに表示 (スレッド) |
| `load_functions()` | `dashboard.parquet` から関数一覧を取得 |
| `load_settings()` | `.env` から設定を読み込み |
| `save_settings(e)` | `.env` に設定を書き込み |
| `switch_language(e)` | UI全体のローカライゼーション更新 |

---

## 6. ローカライゼーション

`LOCALIZATION` 辞書で `en` (英語) と `jp` (日本語) をサポート。

**主要キー:**
- `title`, `dashboard`, `functions`, `settings`
- `server_control`, `start_server`, `stop_server`
- `running`, `stopped`
- `model_config`, `embedding_model`, `quality_gate_model`
- `save_settings`, `settings_saved`, `settings_fail`

---

## 7. データフロー

### 7.1 関数一覧の読み込み
```
[DashboardExporter (server.py)]
    │
    │ (2秒ごとにParquet出力)
    ▼
[data/dashboard.parquet]
    │
    │ (duckdb.query)
    ▼
[load_functions()]
    │
    ▼
[func_list_view (ListView)]
```

### 7.2 設定の保存
```
[Settings Tab]
    │
    │ (save_settings)
    ▼
[.env ファイル]
    │
    │ (サーバー再起動で反映)
    ▼
[server.py config.py]
```

---

## 8. 今後の拡張ポイント

- [ ] 関数の削除機能
- [ ] 関数詳細ダイアログ (コード表示、バージョン履歴)
- [ ] MCP設定JSONのエクスポート機能
- [ ] ダークモード対応
