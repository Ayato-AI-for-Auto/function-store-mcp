import flet as ft
import subprocess
import os
import threading
import asyncio
import json
import duckdb
import time
from mcp_core.database import init_db, Database
from mcp_core.config import DB_PATH, SETTINGS_PATH, BASE_DIR, DATA_DIR
from mcp_core.sync_engine import SyncEngine

# Derived Paths
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
SERVER_SCRIPT = BASE_DIR / "mcp_core" / "server.py"

# Localization
LOCALIZATION = {
    "en": {
        "title": "Function Store MCP - Dashboard",
        "dashboard": "Dashboard",
        "functions": "Functions",
        "settings": "Settings",
        "server_control": "Server Control",
        "server_desc": "Manage your Function Store MCP instance",
        "mcp_status": "MCP Server Status",
        "start_server": "Start Server",
        "stop_server": "Stop Server",
        "stopped": "Stopped",
        "running": "Running",
        "activity_logs": "Recent Activity Logs",
        "clear_logs": "Clear Logs",
        "func_explorer": "Function Explorer",
        "func_desc": "Browse and manage verified skills",
        "no_functions": "No functions found.",
        "model_config": "Model Configuration",
        "embedding_model": "Embedding Model",
        "quality_gate_model": "Quality Gate Model (Reviewer)",
        "restart_hint": "* Changes require server restart to take effect.",
        "save_settings": "Save Settings",
        "language": "Language",
        "lang_en": "English",
        "lang_jp": "Japanese",
        "settings_saved": "Settings saved successfully!",
        "settings_fail": "Failed to save: ",
        "unexpected_stop": "Server stopped unexpectedly.",
        "starting_mcp": "Starting MCP server...",
        "env_not_found": "ERROR: Virtual environment not found!",
        "mcp_config_title": "MCP Configuration for Sharing",
        "mcp_config_desc": "Copy this JSON to share with others or add to your MCP client config.",
        "copy_config": "Copy Configuration",
        "config_copied": "Configuration copied to clipboard!",
        "search_hint": "Search functions...",
        "usage_stats": "Usage Statistics",
        "tag_cloud": "Popular Tags",
        "search_history": "Recent Searches",
        "calls": "calls",
        "last_called": "Last called",
        "no_description": "No description",
        "code_label": "Code",
        "team_tab": "Public Store",
        "supabase_url": "Supabase URL (Override)",
        "supabase_key": "Supabase API Key (Override)",
        "team_id": "Public Project Name",
        "sync_now": "Sync to Global",
        "team_desc": "Share your best functions with the world",
        "sync_success": "Public synchronization complete!",
        "sync_error": "Sync failed: ",
        "enable_translation": "Enable Background Translation (Local LLM)",
    },
    "jp": {
        "title": "Function Store MCP - ダッシュボード",
        "dashboard": "ダッシュボード",
        "functions": "関数エクスプローラー",
        "settings": "設定",
        "server_control": "サーバー制御",
        "server_desc": "Function Store MCP インスタンスの管理",
        "mcp_status": "MCPサーバーの状態",
        "start_server": "サーバー起動",
        "stop_server": "サーバー停止",
        "stopped": "停止中",
        "running": "稼働中",
        "activity_logs": "アクティビティログ",
        "clear_logs": "ログをクリア",
        "func_explorer": "関数エクスプローラー",
        "func_desc": "検証済みスキルの閲覧と管理",
        "no_functions": "関数が見つかりません。",
        "model_config": "モデル設定",
        "embedding_model": "埋め込みモデル",
        "restart_hint": "* 変更を反映するにはサーバーの再起動が必要です。",
        "save_settings": "設定を保存",
        "language": "言語 (Language)",
        "lang_en": "英語 (English)",
        "lang_jp": "日本語 (Japanese)",
        "settings_saved": "設定を保存しました！",
        "settings_fail": "保存に失敗しました: ",
        "unexpected_stop": "サーバーが予期せず停止しました。",
        "starting_mcp": "MCPサーバーを起動中...",
        "env_not_found": "エラー: 仮想環境が見つかりません！",
        "mcp_config_title": "MCP設定 (共有用)",
        "mcp_config_desc": "このJSONをコピーして他の人と共有、またはMCPクライアント設定に追加してください。",
        "copy_config": "設定をコピー",
        "config_copied": "設定がクリップボードにコピーされました！",
        "search_hint": "関数を検索...",
        "usage_stats": "利用統計",
        "tag_cloud": "人気のタグ",
        "search_history": "最近の検索",
        "calls": "回呼び出し",
        "last_called": "最終呼び出し",
        "no_description": "説明がありません",
        "code_label": "コード",
        "team_tab": "パブリック共有",
        "supabase_url": "Supabase URL (上書き用)",
        "supabase_key": "Supabase API Key (上書き用)",
        "team_id": "共有プロジェクト名",
        "sync_now": "世界に公開する",
        "team_desc": "あなたの最高の関数を世界中のユーザーと共有します",
        "sync_success": "パブリック同期が完了しました！",
        "sync_error": "同期に失敗しました: ",
        "enable_translation": "バックグラウンド翻訳を有効にする (ローカルLLM)",
    }
}

class SoloDashboardApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Function Store MCP - Dashboard"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 1100
        self.page.window_height = 800
        self.page.padding = 0
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
        
        # Localization State
        self.lang = "en"
        self.t = LOCALIZATION[self.lang]
        
        # State
        self.process = None
        self.is_running = False
        self.logs = []
        self.functions = []
        self.search_history = []
        self.search_history_path = DATA_DIR / "search_history.json"
        self.selected_functions = set()
        
        # Sync Engine
        self.sync_engine = SyncEngine(Database())
        
        # Components
        self.status_text = ft.Text(self.t["stopped"], size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600)
        self.status_icon = ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.RED_600, size=16)
        self.start_stop_btn = ft.FilledButton(
            content=ft.Text(self.t["start_server"]), 
            icon=ft.Icons.PLAY_ARROW, 
            on_click=self.toggle_server,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=20
            )
        )
        
        self.batch_delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_FOREVER,
            icon_color=ft.Colors.RED_400,
            tooltip="Batch Delete",
            on_click=self.confirm_batch_delete,
            disabled=True
        )
        
        # Sidebar Destination Labels
        self.dest_dashboard = ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label=self.t["dashboard"],
                )
        self.dest_functions = ft.NavigationRailDestination(
                    icon=ft.Icons.CODE_OUTLINED,
                    selected_icon=ft.Icons.CODE,
                    label=self.t["functions"],
                )
        self.dest_settings = ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label=self.t["settings"],
                )
        self.dest_team = ft.NavigationRailDestination(
                    icon=ft.Icons.PUBLIC_OUTLINED,
                    selected_icon=ft.Icons.PUBLIC,
                    label=self.t.get("team_tab", "Public Store"),
                )
        
        self.log_list = ft.ListView(expand=True, spacing=2, padding=10, auto_scroll=True)
        self.func_list_view = ft.ListView(expand=True, spacing=10, padding=10)
        self.tag_cloud_view = ft.Row(wrap=True, spacing=5)
        self.search_history_list = ft.ListView(expand=False, height=150, spacing=2)
        self.search_field = ft.TextField(
            hint_text=self.t["search_hint"],
            expand=True,
            on_submit=self.handle_search
        )
        
        # Build UI first (before any log calls or load_settings)
        self.build_ui()
        
        # Start background check
        self.page.run_task(self.update_ui_loop)

        # Initial Load
        init_db() # Ensure schema is up to date
        
        # Clear parquet cache to force fresh DB read with new schema
        parquet_path = DB_PATH.with_name("dashboard.parquet")
        if parquet_path.exists():
            try:
                parquet_path.unlink()
            except Exception:
                pass
        
        # Now it's safe to log
        self.log(f"Dashboard initialized. Flet version: {ft.__version__}", ft.Colors.BLUE_400)
        self.log(f"Initial language: {self.lang}", ft.Colors.BLUE_400)
            
        self.load_settings()
        self.load_search_history()
        self.load_functions()

    def build_ui(self):
        # Sidebar
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            leading=ft.Container(
                content=ft.Icon(ft.Icons.BOLT_ROUNDED, size=40, color=ft.Colors.BLUE_600),
                padding=20
            ),
            group_alignment=-0.9,
            destinations=[
                self.dest_dashboard,
                self.dest_functions,
                self.dest_team,
                self.dest_settings,
            ],
            on_change=self.handle_rail_change,
        )

        # Dynamic Text Elements
        self.dashboard_title = ft.Text(self.t["server_control"], size=28, weight=ft.FontWeight.BOLD)
        self.dashboard_desc = ft.Text(self.t["server_desc"], color=ft.Colors.GREY_600)
        self.status_header = ft.Text(self.t["mcp_status"], size=12, color=ft.Colors.GREY_500)
        self.logs_title = ft.Text(self.t["activity_logs"], size=16, weight=ft.FontWeight.BOLD)
        self.clear_logs_btn_text = ft.Text(self.t["clear_logs"])
        self.clear_logs_btn = ft.OutlinedButton(content=self.clear_logs_btn_text, icon=ft.Icons.DELETE_SWEEP, on_click=lambda _: self.clear_logs())

        self.functions_title = ft.Text(self.t["func_explorer"], size=28, weight=ft.FontWeight.BOLD)
        self.functions_desc = ft.Text(self.t["func_desc"], color=ft.Colors.GREY_600)

        self.settings_title = ft.Text(self.t["settings"], size=28, weight=ft.FontWeight.BOLD)
        self.model_label = ft.Text(self.t["model_config"], size=16, weight=ft.FontWeight.BOLD)
        self.restart_hint_text = ft.Text(self.t["restart_hint"], size=12, color=ft.Colors.GREY_500)
        self.save_btn_text = ft.Text(self.t["save_settings"])
        self.save_btn = ft.Button(content=self.save_btn_text, icon=ft.Icons.SAVE, on_click=self.save_settings)

        # Content Areas
        self.content_dashboard = self.create_dashboard_view()
        self.content_functions = self.create_functions_view()
        self.content_team = self.create_team_view()
        self.content_settings = self.create_settings_view()
        
        self.main_content = ft.Container(
            content=ft.Stack([
                self.content_dashboard,
                self.content_functions,
                self.content_team,
                self.content_settings,
            ]),
            expand=True,
            padding=30,
            bgcolor=ft.Colors.GREY_50,
        )

        self.page.add(
            ft.Row(
                [
                    self.rail,
                    ft.VerticalDivider(width=1),
                    self.main_content,
                ],
                expand=True,
            )
        )

    def create_dashboard_view(self):
        return ft.Column([
            self.dashboard_title,
            self.dashboard_desc,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            
            # Status Card
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Row([self.status_icon, self.status_text]),
                        self.status_header,
                    ], expand=True),
                    self.start_stop_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
                shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            ),
            
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            
            # Logs Area
            self.logs_title,
            ft.Container(
                content=ft.SelectionArea(content=self.log_list),
                expand=True,
                bgcolor=ft.Colors.BLACK87,
                border_radius=10,
                padding=5,
            ),
            self.clear_logs_btn
        ], expand=True)

    def create_functions_view(self):
        # Define collapsible container first
        self.search_history_title = ft.Text(self.t["search_history"], size=12, weight=ft.FontWeight.BOLD)
        self.search_history_container = ft.Container(
            content=ft.Column([
                self.search_history_title,
                self.search_history_list
            ]),
            visible=False,
            padding=10,
            bgcolor=ft.Colors.GREY_100,
            border_radius=10
        )
        
        # Tag Cloud
        self.tag_cloud_title = ft.Text(self.t["tag_cloud"], size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700)
        
        return ft.Column([
            ft.Row([
                self.functions_title,
                ft.Row([
                    ft.IconButton(ft.Icons.HISTORY, on_click=self.toggle_search_history),
                    self.batch_delete_btn,
                    ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self.load_functions())
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.functions_desc,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            
            # Tag Cloud
            self.tag_cloud_title,
            self.tag_cloud_view,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            
            # Search Bar
            ft.Row([
                self.search_field,
                ft.IconButton(ft.Icons.SEARCH, on_click=self.handle_search)
            ]),
            
            # Search History (Collapsible)
            self.search_history_container,
            
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            
            ft.Container(
                content=ft.SelectionArea(content=self.func_list_view),
                expand=True,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            )
        ], visible=False, expand=True)

    def create_team_view(self):
        self.sync_btn = ft.FilledButton(
            self.t["sync_now"],
            icon=ft.Icons.SYNC,
            on_click=self.handle_sync,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE
            )
        )
        
        return ft.Column([
            self.functions_title,
            ft.Text(self.t["team_desc"], color=ft.Colors.GREY_600),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CLOUD_DONE, color=ft.Colors.GREEN_400),
                    ft.Text("Global Public Store: Active", weight=ft.FontWeight.BOLD),
                    self.sync_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            ),
            
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            # In Phase 1, we just provide the Sync button.
            # Cloud function list visualization will be added in Phase 2.
            ft.Text("Cloud Asset Library (Shared)", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Text("Synchronization will merge cloud assets into your local library.", size=12, italic=True),
                padding=20,
                expand=True,
                bgcolor=ft.Colors.GREY_100,
                border_radius=10
            )
        ], visible=False, expand=True)

    def handle_sync(self, e):
        if not self.sync_engine.is_connected():
            self.page.snack_bar = ft.SnackBar(ft.Text("Supabase not connected. check settings."), bgcolor=ft.Colors.RED_600)
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        self.sync_btn.disabled = True
        self.log("Starting synchronization...", ft.Colors.BLUE_400)
        self.page.update()
        
        try:
            self.sync_engine.sync_all()
            self.log(self.t["sync_success"], ft.Colors.GREEN_400)
            self.page.snack_bar = ft.SnackBar(ft.Text(self.t["sync_success"]), bgcolor=ft.Colors.GREEN_600)
            self.load_functions() # Refresh list
        except Exception as ex:
            self.log(f"{self.t['sync_error']}{ex}", ft.Colors.RED_400)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"{self.t['sync_error']}{ex}"), bgcolor=ft.Colors.RED_600)
        
        self.sync_btn.disabled = False
        self.page.snack_bar.open = True
        self.page.update()

    def create_settings_view(self):
        # Settings Inputs
        self.model_dropdown = ft.Dropdown(
            label=self.t["embedding_model"],
            value="models/gemini-embedding-001",
            options=[
                ft.dropdown.Option("models/gemini-embedding-001", "Gemini Embedding (v001)"),
            ],
            width=400,
        )

        self.quality_gate_model_dropdown = ft.Dropdown(
            label=self.t.get("quality_gate_model", "Quality Gate Model"),
            value="gemma-3-27b-it",
            options=[
                ft.dropdown.Option("gemma-3-27b-it"),
                ft.dropdown.Option("gemini-2.5-flash-lite"),
                ft.dropdown.Option("gemini-2.5-flash"),
                ft.dropdown.Option("gemini-2.5-pro"),
                ft.dropdown.Option("gemini-3-flash-preview"),
                ft.dropdown.Option("gemini-3-pro-preview"),
            ],
            width=400,
        )

        self.lang_dropdown = ft.Dropdown(
            label=self.t["language"],
            value=self.lang,
            options=[
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("jp", "日本語"),
            ],
            width=400,
        )
        self.lang_dropdown.on_change = self.switch_language

        self.enable_translation_switch = ft.Switch(
            label=self.t["enable_translation"],
            value=False
        )

        self.api_key_field = ft.TextField(
            label="Google API Key",
            password=True,
            can_reveal_password=True,
            width=400,
            hint_text="AIzaSy..."
        )


        self.supabase_url_field = ft.TextField(
            label=self.t["supabase_url"],
            width=400,
            hint_text="https://xxxx.supabase.co"
        )

        self.supabase_key_field = ft.TextField(
            label=self.t["supabase_key"],
            password=True,
            can_reveal_password=True,
            width=400,
            hint_text="eyJhbG..."
        )
        
        self.team_id_field = ft.TextField(
            label=self.t["team_id"],
            width=400,
            hint_text="uuid-..."
        )

        # MCP Configuration for Sharing
        mcp_config = {
            "function-store": {
                "command": str(VENV_PYTHON),
                "args": [str(SERVER_SCRIPT)],
                "env": {}
            }
        }
        mcp_config_json = json.dumps(mcp_config, indent=2, ensure_ascii=False)
        
        self.mcp_config_field = ft.TextField(
            value=mcp_config_json,
            multiline=True,
            min_lines=8,
            max_lines=12,
            read_only=True,
            width=500,
            text_style=ft.TextStyle(font_family="Consolas", size=12),
            border_color=ft.Colors.GREY_400,
        )
        

        
        # MCP Configuration Section
        self.mcp_config_title_text = ft.Text(self.t.get("mcp_config_title", "MCP Configuration for Sharing"), size=16, weight=ft.FontWeight.BOLD)
        self.mcp_config_desc_text = ft.Text(self.t.get("mcp_config_desc", "Copy this JSON to share with others or add to your MCP client config."), size=12, color=ft.Colors.GREY_600)
        
        return ft.Column([
            self.settings_title,
            ft.Text(self.t["server_desc"], color=ft.Colors.GREY_600),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=ft.Column([
                    self.model_label,
                    self.model_dropdown,
                    self.quality_gate_model_dropdown,
                    self.api_key_field,
                    ft.Divider(height=10),
                    ft.Text("Supabase / Team Sync", size=16, weight=ft.FontWeight.BOLD),
                    self.supabase_url_field,
                    self.supabase_key_field,
                    self.team_id_field,
                    self.restart_hint_text,
                    ft.Divider(height=10),
                    ft.Text("Translation Settings", size=16, weight=ft.FontWeight.BOLD),
                    self.enable_translation_switch,
                    ft.Divider(height=10),
                    ft.Text(self.t["language"], size=16, weight=ft.FontWeight.BOLD),
                    self.lang_dropdown,
                    ft.Divider(height=10),
                    self.save_btn
                ], spacing=10),
                padding=30,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            ),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            # MCP Configuration Section
            ft.Container(
                content=ft.Column([
                    self.mcp_config_title_text,
                    self.mcp_config_desc_text,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    self.mcp_config_field,
                ], spacing=5),
                padding=30,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            )
        ], visible=False, expand=True, scroll=ft.ScrollMode.AUTO)



    def handle_rail_change(self, e):
        idx = e.control.selected_index
        self.content_dashboard.visible = (idx == 0)
        self.content_functions.visible = (idx == 1)
        self.content_team.visible = (idx == 2)
        self.content_settings.visible = (idx == 3)
        
        if idx == 1:
            self.load_functions()
            
        self.page.update()

    def switch_language(self, e):
        old_lang = self.lang
        self.lang = self.lang_dropdown.value
        self.t = LOCALIZATION[self.lang]
        self.page.title = self.t["title"]
        self.log(f"Language switched: {old_lang} -> {self.lang}", ft.Colors.BLUE_400)
        
        # Update UI Elements
        self.dest_dashboard.label = self.t["dashboard"]
        self.dest_functions.label = self.t["functions"]
        self.dest_settings.label = self.t["settings"]
        
        self.dashboard_title.value = self.t["server_control"]
        self.dashboard_desc.value = self.t["server_desc"]
        self.status_header.value = self.t["mcp_status"]
        self.logs_title.value = self.t["activity_logs"]
        self.clear_logs_btn_text.value = self.t["clear_logs"]

        self.functions_title.value = self.t["func_explorer"]
        self.functions_desc.value = self.t["func_desc"]

        self.settings_title.value = self.t["settings"]
        self.model_label.value = self.t["model_config"]
        self.model_dropdown.label = self.t["embedding_model"]
        self.restart_hint_text.value = self.t["restart_hint"]
        self.lang_dropdown.label = self.t["language"]
        self.save_btn_text.value = self.t["save_settings"]
        
        self.mcp_config_title_text.value = self.t.get("mcp_config_title", "MCP Configuration for Sharing")
        self.mcp_config_desc_text.value = self.t.get("mcp_config_desc", "Copy this JSON to share with others or add to your MCP client config.")
        self.tag_cloud_title.value = self.t["tag_cloud"]
        self.search_history_title.value = self.t["search_history"]
        
        # Update Search & History Labels
        self.search_field.hint_text = self.t["search_hint"]
        
        # Re-trigger UI refresh for dynamic lists
        self.update_status()
        self.load_functions()
        self.load_search_history()
        
        self.page.update()

    # --- Logic ---

    def log(self, text, color=ft.Colors.WHITE):
        now = time.strftime("%H:%M:%S")
        self.log_list.controls.append(
            ft.Text(f"[{now}] {text}", color=color, font_family="Consolas", size=12)
        )
        self.page.update()

    def clear_logs(self):
        self.log_list.controls.clear()
        self.page.update()

    def toggle_server(self, e):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        if not VENV_PYTHON.exists():
            self.log(self.t["env_not_found"], ft.Colors.RED_400)
            return
            
        try:
            self.log(self.t["starting_mcp"], ft.Colors.BLUE_200)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            self.process = subprocess.Popen(
                [str(VENV_PYTHON), str(SERVER_SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                startupinfo=startupinfo
            )
            self.is_running = True
            self.update_status()
            
            # Threaded Log Reading
            threading.Thread(target=self.read_stream, args=(self.process.stdout,), daemon=True).start()
            threading.Thread(target=self.read_stream, args=(self.process.stderr,), daemon=True).start()
            
        except Exception as ex:
            self.log(f"CRITICAL ERROR: {ex}", ft.Colors.RED_600)

    def stop_server(self):
        if self.process:
            self.log(self.t["stop_server"] + "...", ft.Colors.YELLOW_400)
            self.process.terminate()
            self.process = None
        self.is_running = False
        self.update_status()

    def read_stream(self, stream):
        for line in stream:
            line = line.strip()
            if not line:
                continue
            color = ft.Colors.WHITE
            if "[ERROR]" in line or "Traceback" in line:
                color = ft.Colors.RED_400
            elif "[WARNING]" in line:
                color = ft.Colors.ORANGE_400
            elif "[INFO]" in line:
                color = ft.Colors.BLUE_100
            self.log(line, color)
        
        if self.is_running:
            self.is_running = False
            self.update_status()
            self.log(self.t["unexpected_stop"], ft.Colors.RED_600)

    def update_status(self):
        if self.is_running:
            self.status_text.value = self.t["running"]
            self.status_text.color = ft.Colors.GREEN_600
            self.status_icon.color = ft.Colors.GREEN_600
            self.start_stop_btn.text = self.t["stop_server"]
            self.start_stop_btn.icon = ft.Icons.STOP
            self.start_stop_btn.style.bgcolor = ft.Colors.RED_600
        else:
            self.status_text.value = self.t["stopped"]
            self.status_text.color = ft.Colors.RED_600
            self.status_icon.color = ft.Colors.RED_600
            self.start_stop_btn.text = self.t["start_server"]
            self.start_stop_btn.icon = ft.Icons.PLAY_ARROW
            self.start_stop_btn.style.bgcolor = ft.Colors.BLUE_600
        self.page.update()

    async def update_ui_loop(self):
        # Background pulse or status check if needed
        while True:
            if self.is_running:
                # Dynamic Pulse Effect
                self.status_icon.opacity = 0.5 if self.status_icon.opacity == 1.0 else 1.0
                self.page.update()
            await asyncio.sleep(1)

    def load_functions(self, query=None):
        self.func_list_view.controls.clear()
        
        # Lock-Free Read: Try to read from dashboard.parquet first
        parquet_path = DB_PATH.with_name("dashboard.parquet")
        
        try:
            rows = []
            if not query and parquet_path.exists():
                try:
                    # Direct query on Parquet file (No Locking!)
                    rows = duckdb.query(f"SELECT id, name, status, version, description, call_count, last_called_at FROM '{parquet_path}' ORDER BY id DESC").fetchall()
                except Exception as ex:
                    print(f"Parquet Read Error: {ex}")
                    return
            else:
                # If parquet doesn't exist, check standard DB but don't crash
                if not DB_PATH.exists():
                    self.func_list_view.controls.append(ft.Text(self.t["no_functions"], color=ft.Colors.GREY_500))
                    self.page.update()
                    return
                # If DB exists but no parquet, Server might be down or starting.
                try:
                    conn = duckdb.connect(str(DB_PATH), read_only=True)
                    # Fetch extra columns for stats, tags and localized descriptions
                    query_sql = "SELECT id, name, status, version, description, description_en, description_jp, tags, call_count, last_called_at FROM functions"
                    if locals().get('query'):
                        q = locals()['query']
                        if q.startswith("tag:"):
                            tag = q.replace("tag:", "")
                            query_sql += f" WHERE tags LIKE '%\"{tag}\"%' "
                        else:
                            query_sql += f" WHERE name LIKE '%{q}%' OR description LIKE '%{q}%' OR description_en LIKE '%{q}%' OR description_jp LIKE '%{q}%' "
                    
                    query_sql += " ORDER BY id DESC"
                    rows_full = conn.execute(query_sql).fetchall()
                    conn.close()
                    # Map back to simple rows for loop
                    # (id, name, status, ver, desc, desc_en, desc_jp, tags, calls, last_called)
                    rows = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[8], r[9]) for r in rows_full]
                    self.update_tag_cloud(rows_full)
                except Exception as ex:
                    print(f"DB Read Error: {ex}")
                    pass

            for r in rows:
                # Row format: (id, name, status, ver, desc, desc_en, desc_jp, calls, last_called)
                if len(r) == 9:
                    fid, name, status, ver, desc, desc_en, desc_jp, calls, last_called = r
                elif len(r) == 7:
                    # Legacy parquet format fallback
                    fid, name, status, ver, desc, calls, last_called = r
                    desc_en, desc_jp = None, None
                else:
                    fid, name, status, ver, desc = r[:5]
                    desc_en, desc_jp = None, None
                    calls, last_called = 0, None

                # Select localized description
                if self.lang == "jp":
                    display_desc = desc_jp if desc_jp else desc_en if desc_en else desc
                else:
                    display_desc = desc_en if desc_en else desc_jp if desc_jp else desc
                
                if not display_desc:
                    display_desc = self.t.get("no_description", "No description")

                status_color = ft.Colors.GREEN if status == "active" or status == "verified" else ft.Colors.ORANGE
                
                # Stats text
                stats_str = f"{calls} {self.t['calls']}"
                if last_called:
                    stats_str += f" | {self.t['last_called']}: {last_called[:16]}"

                self.func_list_view.controls.append(
                    ft.ListTile(
                        leading=ft.Checkbox(
                            value=name in self.selected_functions,
                            on_change=lambda e, n=name: self.handle_selection_change(e, n)
                        ),
                        title=ft.Row([
                            ft.Icon(ft.Icons.CODE, color=ft.Colors.BLUE_600, size=20),
                            ft.Text(f"{name} (v{ver})", weight=ft.FontWeight.BOLD),
                            ft.Text(stats_str, size=10, color=ft.Colors.GREY_600)
                        ], alignment=ft.MainAxisAlignment.START, spacing=10),
                        subtitle=ft.Text(display_desc, max_lines=2),
                        trailing=ft.Row([
                            ft.Container(
                                content=ft.Text(status.upper(), size=10, color=ft.Colors.WHITE),
                                padding=ft.Padding(8, 2, 8, 2),
                                bgcolor=status_color,
                                border_radius=10
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                tooltip="Delete this function",
                                on_click=lambda _, n=name: self.confirm_delete_single(n)
                            )
                        ], tight=True),
                        on_click=lambda _, n=name: self.show_function_details(n)
                    )
                )
        except Exception as ex:
            self.func_list_view.controls.append(ft.Text(f"Error loading functions: {ex}", color=ft.Colors.RED_400))
    
        self.page.update()

    def show_function_details(self, name):
        """Open a detailed dialog for the selected function."""
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            row = conn.execute(
                "SELECT id, name, code, description, description_en, description_jp, tags, status, call_count, last_called_at, created_at, updated_at, version FROM functions WHERE name = ?",
                [name]
            ).fetchone()
            conn.close()
            
            if not row:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Function '{name}' not found."), bgcolor=ft.Colors.RED_600)
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            fid, fname, code, desc, desc_en, desc_jp, tags_json, status, calls, last_called, created, updated, ver = row
            
            # Select description by language
            if self.lang == "jp":
                display_desc = desc_jp if desc_jp else desc_en if desc_en else desc
            else:
                display_desc = desc_en if desc_en else desc_jp if desc_jp else desc
            
            if not display_desc:
                display_desc = "No description available."
            
            # Parse tags
            tag_list = []
            if tags_json:
                try:
                    tag_list = json.loads(tags_json)
                except Exception:
                    pass
            
            # Build Dialog
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"{fname} (v{ver})", weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(display_desc, size=14, color=ft.Colors.GREY_700),
                        ft.Divider(height=10),
                        ft.Text(self.t.get("usage_stats", "Usage Statistics"), weight=ft.FontWeight.BOLD, size=12),
                        ft.Text(f"{calls} {self.t['calls']} | {self.t['last_called']}: {last_called if last_called else 'N/A'}", size=11, color=ft.Colors.GREY_600),
                        ft.Divider(height=10),
                        ft.Text(self.t.get("tag_cloud", "Tags"), weight=ft.FontWeight.BOLD, size=12),
                        ft.Row([ft.Chip(label=ft.Text(t), bgcolor=ft.Colors.BLUE_50) for t in tag_list[:5]], wrap=True) if tag_list else ft.Text("-", color=ft.Colors.GREY_400),
                        ft.Divider(height=10),
                        ft.Text("Code", weight=ft.FontWeight.BOLD, size=12),
                        ft.Container(
                            content=ft.SelectionArea(
                                content=ft.Text(code if code else "# No code", font_family="Consolas", size=11)
                            ),
                            bgcolor=ft.Colors.GREY_900,
                            padding=10,
                            border_radius=10,
                            width=500,
                            height=200,
                        ),
                    ], scroll=ft.ScrollMode.AUTO, width=520, height=400),
                    padding=10,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda _: self.close_dialog(dialog))
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            self.page.overlay.append(dialog)
            dialog.open = True
            self.page.update()
            
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error loading details: {ex}"), bgcolor=ft.Colors.RED_600)
            self.page.snack_bar.open = True
            self.page.update()

    def handle_selection_change(self, e, name):
        if e.control.value:
            self.selected_functions.add(name)
        else:
            self.selected_functions.discard(name)
        
        self.batch_delete_btn.disabled = len(self.selected_functions) == 0
        self.page.update()

    def confirm_delete_single(self, name):
        self.confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Are you sure you want to delete function '{name}'? This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(self.confirm_dialog)),
                ft.ElevatedButton("Delete", color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_600, 
                                 on_click=lambda _: self.execute_delete_single(name))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(self.confirm_dialog)
        self.confirm_dialog.open = True
        self.page.update()

    def confirm_batch_delete(self, e):
        count = len(self.selected_functions)
        self.batch_confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Batch Deletion"),
            content=ft.Text(f"Are you sure you want to delete {count} selected functions?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(self.batch_confirm_dialog)),
                ft.ElevatedButton("Delete All", color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_600, 
                                 on_click=self.execute_batch_delete)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(self.batch_confirm_dialog)
        self.batch_confirm_dialog.open = True
        self.page.update()

    def execute_delete_single(self, name):
        from mcp_core.server import delete_function
        self.close_dialog(self.confirm_dialog)
        self.log(f"Deleting function: {name}", ft.Colors.RED_400)
        delete_function(name)
        self.selected_functions.discard(name)
        self.load_functions()

    def execute_batch_delete(self, e):
        from mcp_core.server import delete_function
        self.close_dialog(self.batch_confirm_dialog)
        count = len(self.selected_functions)
        self.log(f"Batch deleting {count} functions...", ft.Colors.RED_400)
        
        for name in list(self.selected_functions):
            delete_function(name)
            self.selected_functions.discard(name)
            
        self.batch_delete_btn.disabled = True
        self.load_functions()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def load_settings(self):
        # Try settings.json first (new UI-first design)
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.model_dropdown.value = settings.get("FS_MODEL_NAME", "models/gemini-embedding-001")
                    self.quality_gate_model_dropdown.value = settings.get("FS_QUALITY_GATE_MODEL", "gemma-3-27b-it")
                    self.api_key_field.value = settings.get("GOOGLE_API_KEY", "")
                    self.supabase_url_field.value = settings.get("SUPABASE_URL", "")
                    self.supabase_key_field.value = settings.get("SUPABASE_KEY", "")
                    self.team_id_field.value = settings.get("TEAM_ID", "")
                    self.enable_translation_switch.value = settings.get("FS_ENABLE_TRANSLATION", False)
                    self.lang = settings.get("UI_LANG", "en")
                    self.lang_dropdown.value = self.lang
                    self.t = LOCALIZATION.get(self.lang, LOCALIZATION["en"])
                    self.log(f"Settings loaded. Language: {self.lang}", ft.Colors.BLUE_400)
                    self.switch_language(None) # Refresh UI with loaded language
                    self.page.update()
            except Exception as e:
                print(f"Error loading settings.json: {e}")
        self.page.update()

    def save_settings(self, e):
        settings = {
            "FS_MODEL_NAME": self.model_dropdown.value,
            "FS_QUALITY_GATE_MODEL": self.quality_gate_model_dropdown.value,
            "GOOGLE_API_KEY": self.api_key_field.value,
            "SUPABASE_URL": self.supabase_url_field.value,
            "SUPABASE_KEY": self.supabase_key_field.value,
            "TEAM_ID": self.team_id_field.value,
            "FS_ENABLE_TRANSLATION": self.enable_translation_switch.value,
            "UI_LANG": self.lang_dropdown.value
        }
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            self.page.snack_bar = ft.SnackBar(ft.Text(self.t["settings_saved"]), bgcolor=ft.Colors.GREEN_600)
            self.page.snack_bar.open = True
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"{self.t['settings_fail']}{ex}"), bgcolor=ft.Colors.RED_600)
            self.page.snack_bar.open = True
        self.page.update()

    def toggle_search_history(self, e):
        self.search_history_container.visible = not self.search_history_container.visible
        self.page.update()

    def handle_search(self, e):
        query = self.search_field.value.strip()
        if not query:
            self.load_functions()
            return
        
        # Update history
        if query in self.search_history:
            self.search_history.remove(query)
        self.search_history.insert(0, query)
        self.search_history = self.search_history[:10]
        self.save_search_history()
        self.update_search_history_ui()
        
        self.load_functions(query=query)
        self.page.update()

    def load_search_history(self):
        if self.search_history_path.exists():
            try:
                with open(self.search_history_path, "r", encoding="utf-8") as f:
                    self.search_history = json.load(f)
                self.update_search_history_ui()
            except Exception:
                pass

    def save_search_history(self):
        try:
            self.search_history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.search_history_path, "w", encoding="utf-8") as f:
                json.dump(self.search_history, f)
        except Exception:
            pass

    def update_search_history_ui(self):
        self.search_history_list.controls = [
            ft.TextButton(h, on_click=lambda _, q=h: self.apply_history_search(q)) 
            for h in self.search_history
        ]
        self.page.update()

    def apply_history_search(self, query):
        self.search_field.value = query
        self.handle_search(None)

    def update_tag_cloud(self, rows):
        tag_counts = {}
        for r in rows:
            if len(r) > 5:
                tags_json = r[5]
                if tags_json:
                    try:
                        tags = json.loads(tags_json)
                        for t in tags:
                            tag_counts[t] = tag_counts.get(t, 0) + 1
                    except Exception:
                        pass
        
        self.tag_cloud_view.controls = [
            ft.Chip(
                label=ft.Text(f"{tag} ({count})"),
                on_click=lambda _, t=tag: self.filter_by_tag(t),
                bgcolor=ft.Colors.BLUE_50
            ) for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        ]
        self.page.update()

    def filter_by_tag(self, tag):
        self.search_field.value = f"tag:{tag}"
        self.handle_search(None)

def main(page: ft.Page):
    SoloDashboardApp(page)

if __name__ == "__main__":
    ft.run(main)
