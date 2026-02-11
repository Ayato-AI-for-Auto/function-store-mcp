# Solo-MCP UI Design (Flet Dashboard)

## Design Philosophy (Horiemon Style)
**「Speed & Simplicity」**
ユーザーが迷う時間を1秒でも減らす。
直感的に「自分の資産」と「世界の資産」を行き来できるインターフェース。

## 1. Application Structure
Flet (Flutter for Python) を採用し、シングルバイナリ感覚で起動するデスクトップアプリライクなWeb UI。

### Navigation (Sidebar)
左側のナビゲーションレールで以下の主要機能にアクセス。

1.  **⚡ Dashboard (Server Control)**
    - MCPサーバーのステータス確認。
    - ログの閲覧と消去。
    - サーバーの再起動（設定変更後など）。

2.  **📂 Functions (Explore)**
    - ローカルに保存された関数のリスト表示。
    - **Search Bar:** リアルタイムフィルタリング。
    - **Function Card:**
        - 関数名、説明文（日英）、タグ。
        - **Copy Code:** ワンクリックでクリップボードへ。
        - **Delete:** 不要な関数の削除。

3.  **🌍 Public Store (Global Sync)**
    - **Sync Button:** 「Sync to Global」でローカルの関数を公開。
    - **Status Indicator:** 現在の公開状態を表示。
    - (Future): 世界中の関数を検索・インポートするインターフェース。

4.  **⚙️ Settings**
    - **Google API Key:** Gemini APIキーの設定。
    - **Model Selection:** Embeddingモデル、Quality Gateモデルの選択。
    - **Language:** 日本語 / English 切り替え。
    - **Supabase Overrides:** 上級者向け接続設定。

## 2. Visual Style
- **Framework:** Flet (Material Design 3 base).
- **Color Palette:**
    - Primary: `Blue 600` (信頼、知性)
    - Accents: `Green 400` (成功、Sync完了), `Red 400` (エラー、削除)
    - Background: `Grey 50` (清潔感、モダン)
- **Typography:**
    - Headings: Bold, Sans-serif.
    - Code: Monospace (Consolas/JetBrains Mono).

## 3. Key Interactions
- **Instant Search:** 入力と同時にリストが絞り込まれる。
- **SnackBar Notifications:** アクションの結果（保存、同期、エラー）を画面下部に控えめに通知。
- **Dialogs:** 削除などの破壊的操作には確認ダイアログを表示。

## 4. Future Roadmap (UI)
- [ ] **Dark Mode:** エンジニア向けの目に優しいテーマ。
- [ ] **Drag & Drop Import:** Pythonファイルを画面に落として登録。
- [ ] **Visual Graph:** 関数間の依存関係を可視化。
