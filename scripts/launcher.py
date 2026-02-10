import flet as ft
import subprocess
import os
import signal
import threading
import queue
from pathlib import Path
import json
import duckdb
import time
import asyncio
import logging
import traceback
import torch

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Paths
BASE_DIR = Path(__file__).parent.parent
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
SERVER_SCRIPT = BASE_DIR / "function_store_mcp" / "server.py"
TRANSLATOR_SCRIPT = BASE_DIR / "scripts" / "translator.py"
ENV_PATH = BASE_DIR / ".env"
DB_PATH = BASE_DIR / "data" / "functions.duckdb"
SETTINGS_PATH = BASE_DIR / "data" / "settings.json"
TRANS_QUEUE_PATH = BASE_DIR / "data" / "translation_queue.json"
TRANS_RESULTS_PATH = BASE_DIR / "data" / "translation_results.jsonl"
LOG_PATH = BASE_DIR / "data" / "app.log"

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
        "agent_config": "AI Agent Configuration (JSON)",
        "agent_config_desc": "Copy this to your AI agent's config file (e.g., mcp_config.json)",
        "copy_config": "Copy Snippet",
        "translating": "Translating...",
        "search_hint": "Search functions...",
        "bulk_actions": "Bulk Actions",
        "delete": "Delete",
        "verify": "Verify",
        "details_title": "Function Details",
        "close": "Close",
        "code": "Code",
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
        "agent_config": "AIエージェント設定 (JSON)",
        "agent_config_desc": "このスニペットをAIエージェントの設定ファイルに追加してください",
        "copy_config": "コピーする",
        "translating": "翻訳中...",
        "search_hint": "関数を検索...",
        "bulk_actions": "一括操作",
        "delete": "削除",
        "verify": "検証",
        "details_title": "関数の詳細",
        "close": "閉じる",
        "code": "ソースコード",
    }
}

class FunctionStoreApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Function Store MCP - Dashboard"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 1100
        self.page.window_height = 800
        self.page.padding = 0
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
        
        # State
        self.lang = "en"
        self.hf_token_value = ""
        self.embedding_model_value = "BAAI/bge-m3"
        self.t = LOCALIZATION[self.lang]
        self.process = None
        self.is_running = False
        self.is_translating = False # Track background translation status
        self.logs = []
        self.selected_index = 0
        self.translation_indicator_ref = ft.Ref[ft.Container]()
        self.selected_functions = set() # Track selected function names
        
        # Initial Load Settings (to set lang and state)
        self.load_settings(initial=True)
        logging.info(f"Initialized with language: {self.lang}")
        
        # UI Component Container
        self.main_layout = ft.Row(expand=True)
        self.page.add(self.main_layout)
        
        # Initial Build
        self.build_ui()
        
        # Start background check
        self.page.run_task(self.update_ui_loop)
        self.load_functions()

    def build_ui(self):
        logging.info(f"Building UI for language: {self.lang}")
        self.t = LOCALIZATION[self.lang]
        self.page.title = self.t["title"]
        
        # Sidebar
        self.rail = ft.NavigationRail(
            selected_index=self.selected_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            leading=ft.Container(
                content=ft.Icon(ft.Icons.BOLT_ROUNDED, size=40, color=ft.Colors.BLUE_600),
                padding=20
            ),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label=self.t["dashboard"],
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CODE_OUTLINED,
                    selected_icon=ft.Icons.CODE,
                    label=self.t["functions"],
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label=self.t["settings"],
                ),
            ],
            on_change=self.handle_rail_change,
        )

        # Content Areas
        self.content_dashboard = self.create_dashboard_view()
        self.content_functions = self.create_functions_view()
        self.content_settings = self.create_settings_view()
        
        # Visibility based on state
        self.content_dashboard.visible = (self.selected_index == 0)
        self.content_functions.visible = (self.selected_index == 1)
        self.content_settings.visible = (self.selected_index == 2)
        
        self.view_container = ft.Stack(
            [self.content_dashboard, self.content_functions, self.content_settings],
            expand=True
        )
        
        self.main_content = ft.Container(
            content=self.view_container,
            expand=True,
            padding=30,
            bgcolor=ft.Colors.GREY_50,
        )

        # Clear and rebuild layout
        self.main_layout.controls.clear()
        self.main_layout.controls.extend([
            self.rail,
            ft.VerticalDivider(width=1),
            self.main_content
        ])
        self.page.update()

    def create_dashboard_view(self):
        # Persistent stateful components
        self.status_text = ft.Text(
            self.t["running"] if self.is_running else self.t["stopped"], 
            size=14, weight=ft.FontWeight.BOLD, 
            color=ft.Colors.GREEN_600 if self.is_running else ft.Colors.RED_600
        )
        self.status_icon = ft.Icon(
            ft.Icons.CIRCLE, 
            color=ft.Colors.GREEN_600 if self.is_running else ft.Colors.RED_600, 
            size=16
        )
        self.start_stop_btn = ft.ElevatedButton(
            self.t["stop_server"] if self.is_running else self.t["start_server"],
            icon=ft.Icons.STOP if self.is_running else ft.Icons.PLAY_ARROW,
            on_click=self.toggle_server,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600 if self.is_running else ft.Colors.BLUE_600,
                padding=20
            )
        )
        self.copy_logs_btn = ft.IconButton(
            icon=ft.Icons.COPY,
            tooltip="Copy Logs / ログをコピー",
            on_click=self.copy_logs_to_clipboard
        )
        self.log_list = ft.ListView(expand=True, spacing=2, padding=10, auto_scroll=True)
        # Add existing logs back to the view
        for lText, lColor in self.logs:
            self.log_list.controls.append(ft.Text(lText, color=lColor, font_family="Consolas", size=12, selectable=True))

        return ft.Column([
            ft.Text(self.t["server_control"], size=28, weight=ft.FontWeight.BOLD),
            ft.Text(self.t["server_desc"], color=ft.Colors.GREY_600),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Row([self.status_icon, self.status_text]),
                        ft.Text(self.t["mcp_status"], size=12, color=ft.Colors.GREY_500),
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
            
            # Agent Config Card
            ft.Text(self.t["agent_config"], size=16, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.Text(self.t["agent_config_desc"], size=12, color=ft.Colors.GREY_600),
                    ft.Row([
                        ft.TextField(
                            value=self.get_mcp_config_json(),
                            multiline=True,
                            min_lines=5,
                            max_lines=8,
                            read_only=True,
                            text_size=11,
                            text_style=ft.TextStyle(font_family="Consolas"),
                            bgcolor=ft.Colors.GREY_50,
                            border_color=ft.Colors.GREY_300,
                            expand=True
                        ),
                        ft.IconButton(
                            ft.Icons.COPY_ALL_ROUNDED, 
                            on_click=lambda _: self.copy_to_clipboard(self.get_mcp_config_json()),
                            tooltip=self.t["copy_config"]
                        )
                    ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True)
                ], spacing=5),
                padding=15,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            ),

            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Row([
                ft.Text(self.t["activity_logs"], size=16, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                self.copy_logs_btn,
                ft.ElevatedButton(self.t["clear_logs"], icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e: self.clear_logs())
            ]),
            ft.Container(
                content=self.log_list, 
                height=300,  # Fixed height for logs
                bgcolor=ft.Colors.BLACK87, 
                border_radius=10, 
                padding=5,
            ),
        ], scroll=ft.ScrollMode.AUTO, expand=True)  # Enable scrolling for the whole page

    def create_functions_view(self):
        self.func_list_view = ft.ListView(expand=True, spacing=10, padding=10)
        
        self.search_field = ft.TextField(
            hint_text=self.t["search_hint"],
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda _: self.load_functions(),
            expand=True,
            height=45,
            text_size=14,
            border_radius=10,
        )

        self.bulk_actions_bar = ft.Row([
            ft.Text(self.t["bulk_actions"], size=12, color=ft.Colors.GREY_600),
            ft.TextButton(
                self.t["delete"], 
                icon=ft.Icons.DELETE_OUTLINE, 
                icon_color=ft.Colors.RED_400,
                on_click=self.handle_bulk_delete
            ),
            ft.TextButton(
                self.t["verify"], 
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE, 
                icon_color=ft.Colors.GREEN_400,
                on_click=self.handle_bulk_verify
            ),
        ], visible=False, alignment=ft.MainAxisAlignment.START)

        return ft.Column([
            ft.Row([
                ft.Text(self.t["func_explorer"], size=28, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Container(
                        content=ft.ProgressRing(width=16, height=16, stroke_width=2),
                        visible=False,
                        ref=self.translation_indicator_ref
                    ),
                    ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self.load_functions())
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(self.t["func_desc"], color=ft.Colors.GREY_600),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Row([self.search_field]),
            self.bulk_actions_bar,
            ft.Container(
                content=self.func_list_view, expand=True, bgcolor=ft.Colors.WHITE, border_radius=15, border=ft.Border.all(1, ft.Colors.GREY_200),
            )
        ], visible=False, expand=True)

    def create_settings_view(self):
        self.model_dropdown = ft.Dropdown(
            label=self.t["embedding_model"],
            value=self.embedding_model_value,
            options=[
                ft.dropdown.Option("BAAI/bge-m3"),
                ft.dropdown.Option("intfloat/multilingual-e5-large"),
                ft.dropdown.Option("sentence-transformers/all-MiniLM-L6-v2"),
            ],
            width=400,
        )
        self.lang_dropdown = ft.Dropdown(
            label=self.t["language"],
            value=self.lang,
            options=[
                ft.dropdown.Option("en", self.t["lang_en"]),
                ft.dropdown.Option("jp", self.t["lang_jp"]),
            ],
            width=400,
        )
        self.lang_dropdown.on_change = self.handle_lang_change
        
        self.hf_token_input = ft.TextField(
            label="Hugging Face Token (HF_TOKEN)",
            value=self.hf_token_value,
            password=True,
            can_reveal_password=True,
            hint_text="Required for gated models (TranslateGemma)",
            width=400,
            text_size=12,
        )

        return ft.Column([
            ft.Text(self.t["settings"], size=28, weight=ft.FontWeight.BOLD),
            ft.Text(self.t["server_desc"], color=ft.Colors.GREY_600),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=ft.Column([
                    ft.Text(self.t["model_config"], size=16, weight=ft.FontWeight.BOLD),
                    self.model_dropdown,
                    ft.Text(self.t["restart_hint"], size=12, color=ft.Colors.GREY_500),
                    ft.Divider(height=10),
                    ft.Text(self.t["language"], size=16, weight=ft.FontWeight.BOLD),
                    self.lang_dropdown,
                    ft.Divider(height=10),
                    ft.Text("External Services", size=16, weight=ft.FontWeight.BOLD),
                    self.hf_token_input,
                    ft.Divider(height=10),
                    ft.ElevatedButton(self.t["save_settings"], icon=ft.Icons.SAVE, on_click=self.save_settings)
                ], spacing=10),
                padding=30, bgcolor=ft.Colors.WHITE, border_radius=15, border=ft.Border.all(1, ft.Colors.GREY_200),
            )
        ], visible=False, expand=True)

    def handle_rail_change(self, e):
        self.selected_index = e.control.selected_index
        self.content_dashboard.visible = (self.selected_index == 0)
        self.content_functions.visible = (self.selected_index == 1)
        self.content_settings.visible = (self.selected_index == 2)
        if self.selected_index == 1: self.load_functions()
        self.page.update()

    def handle_lang_change(self, e):
        logging.info(f"Language change event triggered. New value: {self.lang_dropdown.value}")
        if self.lang_dropdown.value:
            self.lang = self.lang_dropdown.value
            self.build_ui()
            self.load_functions()
        else:
             logging.warning("Dropdown value was None, skipping update.")

    def get_mcp_config_json(self):
        # Dynamically get current model
        current_model = "BAAI/bge-m3"
        if hasattr(self, 'model_dropdown') and self.model_dropdown.value:
            current_model = self.model_dropdown.value
            
        config = {
            "mcpServers": {
                "function-store": {
                    "command": str(VENV_PYTHON),
                    "args": [str(SERVER_SCRIPT)],
                    "env": {
                        "EMBEDDING_MODEL": current_model
                    }
                }
            }
        }
        return json.dumps(config, indent=2)

    def copy_to_clipboard(self, text):
        try:
            if hasattr(self.page, "set_clipboard"):
                self.page.set_clipboard(text)
            else:
                # Fallback for newer/different Flet versions
                self.page.clipboard = text
            
            self.page.snack_bar = ft.SnackBar(ft.Text("Copied to clipboard! / クリップボードにコピーしました！"))
        except Exception as e:
            logging.error(f"Clipboard Error: {e}")
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Copy failed: {e}"), bgcolor=ft.Colors.RED_400)
            
        self.page.snack_bar.open = True
        self.page.update()

    # --- Logic ---

    def log(self, text, color=ft.Colors.WHITE):
        now = time.strftime("%H:%M:%S")
        log_entry = (f"[{now}] {text}", color)
        self.logs.append(log_entry)
        
        # Write to file
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
        except: pass

        if hasattr(self, 'log_list'):
            self.log_list.controls.append(ft.Text(log_entry[0], color=color, font_family="Consolas", size=12, selectable=True))
            try:
                self.page.update()
            except: pass

    def copy_logs_to_clipboard(self, e):
        full_log = "\n".join([entry[0] for entry in self.logs])
        self.copy_to_clipboard(full_log)

    def clear_logs(self):
        self.logs = []
        if hasattr(self, 'log_list'):
            self.log_list.controls.clear()
            self.page.update()

    def toggle_server(self, e):
        if self.is_running: self.stop_server()
        else: self.start_server()

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
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, startupinfo=startupinfo
            )
            self.is_running = True
            self.update_status()
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


    def trigger_auto_translation(self):
        """Starts the translator script in background if not already running."""
        if self.is_translating: return
        
        # 1. Export Pending Tasks to Queue File
        try:
            conn = self.get_read_connection()
            pending = conn.execute("""
                SELECT name, description, description_en, description_jp 
                FROM functions 
                WHERE description_en IS NULL OR description_jp IS NULL
            """).fetchall()
            conn.close()
            
            if not pending:
                return # Nothing to do

            # Pre-filter (naive check for source text)
            queue_data = []
            for name, original, en, jp in pending:
                src_text = original if original else (en if en else jp)
                if not src_text: continue
                
                queue_data.append({
                    "name": name,
                    "original": original,
                    "description_en": en,
                    "description_jp": jp,
                    "source": src_text
                })
            
            if not queue_data: return

            with open(TRANS_QUEUE_PATH, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Exported {len(queue_data)} tasks to {TRANS_QUEUE_PATH}")

        except Exception as qe:
            self.log(f"Queue Export Error: {qe}", ft.Colors.RED_400)
            return

        # 2. Start Background Thread
        self.is_translating = True
        if hasattr(self, 'translation_indicator_ref') and self.translation_indicator_ref.current:
            self.translation_indicator_ref.current.visible = True
            self.page.update()

        self.log(f"Auto-Translation started...", ft.Colors.BLUE_200)

        def run_translate():
            try:
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                
                hf_token = self.hf_token_value if hasattr(self, 'hf_token_value') else os.environ.get("HF_TOKEN")
                
                if not hf_token:
                    self.log("Skipping auto-translation: HF_TOKEN not set.", ft.Colors.ORANGE_400)
                    return
                env["HF_TOKEN"] = hf_token

                # Remove results if exists before starting to avoid stale data
                if TRANS_RESULTS_PATH.exists():
                    try: TRANS_RESULTS_PATH.unlink()
                    except: pass

                process = subprocess.Popen(
                    [str(VENV_PYTHON), str(TRANSLATOR_SCRIPT)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    startupinfo=startupinfo
                )
                
                for line in process.stdout:
                    if line: self.log(line.strip(), ft.Colors.BLUE_100)
                
                for line in process.stderr:
                    if line: self.log(f"[Translator Error] {line.strip()}", ft.Colors.RED_400)
                
                process.wait()
                
                if process.returncode == 0:
                    self.log(f"Auto-Translation batch complete.", ft.Colors.GREEN_400)
                else:
                    self.log(f"Auto-Translation FAILED with code {process.returncode}", ft.Colors.RED_400)
            except Exception as ex:
                self.log(f"Translator Exception: {ex}", ft.Colors.RED_600)
            finally:
                self.is_translating = False
                self.last_translation_time = time.time()
                # Instead of update_translation_status, we will rely on ingest_translation_results
                # which will be called by periodic loop or here.
                # Let's call it once manually here to be sure.
                self.page.run_task(self.ingest_translation_results)
                self.page.run_task(self.update_translation_status)

        threading.Thread(target=run_translate, daemon=True).start()

    async def ingest_translation_results(self):
        """Checks for translation results file and updates the DB if found."""
        if not TRANS_RESULTS_PATH.exists(): return
        
        logging.info(f"Checking for results in {TRANS_RESULTS_PATH}")
        results = []
        try:
            with open(TRANS_RESULTS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        results.append(json.loads(line))
            
            if not results:
                TRANS_RESULTS_PATH.unlink()
                return

            self.log(f"Ingesting {len(results)} translations...", ft.Colors.BLUE_200)
            
            conn = duckdb.connect(str(DB_PATH))
            try:
                updates = []
                for res in results:
                    name = res.get("name")
                    en = res.get("description_en")
                    jp = res.get("description_jp")
                    if name and (en or jp):
                        updates.append((en, jp, name))
                
                if updates:
                    conn.executemany("""
                        UPDATE functions 
                        SET description_en = ?, description_jp = ? 
                        WHERE name = ?
                    """, updates)
                    conn.commit()
                    self.log(f"Successfully integrated {len(updates)} translations.", ft.Colors.GREEN_400)
            finally:
                conn.close()
                
            # Cleanup
            try: TRANS_RESULTS_PATH.unlink()
            except: pass
            
            # Refresh UI
            self.load_functions()

        except Exception as ie:
            logging.error(f"Ingest Error: {ie}")
            self.log(f"Translation Ingest Error: {ie}", ft.Colors.RED_400)

    async def update_translation_status(self):
        if hasattr(self, 'translation_indicator_ref') and self.translation_indicator_ref.current:
            self.translation_indicator_ref.current.visible = False
        self.load_functions() # Refresh list to show new translations
        self.page.update()

    def read_stream(self, stream):
        for line in stream:
            line = line.strip()
            if not line: continue
            color = ft.Colors.WHITE
            if "[ERROR]" in line or "Traceback" in line: color = ft.Colors.RED_400
            elif "[WARNING]" in line: color = ft.Colors.ORANGE_400
            elif "[INFO]" in line: color = ft.Colors.BLUE_100
            self.log(line, color)
        if self.is_running:
            self.is_running = False
            self.update_status()
            self.log(self.t["unexpected_stop"], ft.Colors.RED_600)

    async def update_status(self):
        """Update basic status indicators."""
        if not hasattr(self, 'status_text'): return
        self.status_text.value = self.t["running"] if self.is_running else self.t["stopped"]
        self.status_text.color = ft.Colors.GREEN_600 if self.is_running else ft.Colors.RED_600
        self.status_icon.color = ft.Colors.GREEN_600 if self.is_running else ft.Colors.RED_600
        self.start_stop_btn.text = self.t["stop_server"] if self.is_running else self.t["start_server"]
        self.start_stop_btn.icon = ft.Icons.STOP if self.is_running else ft.Icons.PLAY_ARROW
        self.start_stop_btn.style.bgcolor = ft.Colors.RED_600 if self.is_running else ft.Colors.BLUE_600
        try: self.page.update()
        except: pass

    async def update_ui_loop(self):
        """Periodic UI updates and background task ingestion."""
        while True:
            try:
                # 1. Check for translation results (Queue System)
                await self.ingest_translation_results()
                
                # 2. Update server status
                await self.update_status()

                # 3. Handle Running state animations/updates
                if self.is_running:
                    if hasattr(self, 'status_icon'):
                        self.status_icon.opacity = 0.5 if self.status_icon.opacity == 1.0 else 1.0
                    try:
                        # self.update_mcp_config_ui() # This method is not defined
                        self.page.update()
                    except: pass
            except Exception as e:
                logging.debug(f"UI Loop Error: {e}")
            
            await asyncio.sleep(5)

    def load_functions(self):
        if not hasattr(self, 'func_list_view'): return
        self.func_list_view.controls.clear()
        
        query = ""
        if hasattr(self, 'search_field'):
            query = self.search_field.value.lower()

        if not DB_PATH.exists():
            self.func_list_view.controls.append(ft.Text(self.t["no_functions"], color=ft.Colors.GREY_500))
            self.page.update()
            return
            
        try:
            conn = self.get_read_connection()
            # Fetch functions
            rows = conn.execute("SELECT id, name, status, version, description, description_en, description_jp FROM functions ORDER BY name ASC").fetchall()
            conn.close()
            
            if not rows:
                self.func_list_view.controls.append(ft.Text(self.t["no_functions"], color=ft.Colors.GREY_500))
            else:
                any_needs_translation = False
                
                for r in rows:
                    fid, name, status, ver, desc, desc_en, desc_jp = r
                    
                    # Filtering
                    match = True
                    if query:
                        match = False
                        if query in name.lower(): match = True
                        elif desc and query in desc.lower(): match = True
                        elif desc_en and query in desc_en.lower(): match = True
                        elif desc_jp and query in desc_jp.lower(): match = True
                    
                    if not match: continue

                    display_desc = desc
                    needs_translation = False
                    
                    if self.lang == "jp":
                        if desc_jp: display_desc = desc_jp
                        elif desc_en:
                            display_desc = desc_en
                            needs_translation = True
                    else:
                        if desc_en: display_desc = desc_en
                        elif desc_jp:
                            display_desc = desc_jp
                            needs_translation = True
                    
                    if not display_desc: display_desc = "..."

                    # Status Colors/Labels
                    status_label = status.upper()
                    status_color = ft.Colors.GREY_600
                    if status in ["verified", "active"]:
                        status_label = "ACTIVE" if self.lang == "en" else "稼働中"
                        status_color = ft.Colors.GREEN_600
                    elif status == "broken":
                        status_label = "BROKEN" if self.lang == "en" else "不具合"
                        status_color = ft.Colors.RED_600
                    elif status == "unverified":
                        status_label = "UNVERIFIED" if self.lang == "en" else "未検証"
                        status_color = ft.Colors.ORANGE_600
                    
                    if needs_translation:
                        any_needs_translation = True

                    # Checkbox logic
                    def on_check(e, n=name):
                        if e.control.value: self.selected_functions.add(n)
                        else: self.selected_functions.discard(n)
                        self.bulk_actions_bar.visible = len(self.selected_functions) > 0
                        self.page.update()

                    func_item = ft.Container(
                        content=ft.Row([
                            ft.Checkbox(
                                value=(name in self.selected_functions),
                                on_change=on_check
                            ),
                            ft.Icon(ft.Icons.CODE_ROUNDED, color=ft.Colors.BLUE_600, size=20),
                            ft.Column([
                                ft.Text(f"{name} (v{ver})", weight=ft.FontWeight.BOLD, size=14),
                                ft.Text(display_desc, size=12, color=ft.Colors.GREY_700, selectable=True),
                            ], expand=True, spacing=2),
                            ft.Container(
                                content=ft.Text(status_label, size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                padding=ft.Padding(8, 2, 8, 2), bgcolor=status_color, border_radius=10
                            ),
                            ft.IconButton(
                                ft.Icons.CHEVRON_RIGHT, 
                                on_click=lambda _, n=name: self.show_function_details(n)
                            )
                        ]),
                        padding=10,
                        border_radius=10,
                        on_hover=lambda e: setattr(e.control, "bgcolor", ft.Colors.GREY_100 if e.data == "true" else ft.Colors.TRANSPARENT) or e.control.update(),
                        on_click=lambda _, n=name: self.show_function_details(n),
                    )
                    self.func_list_view.controls.append(func_item)
                
                if any_needs_translation:
                    # Cooldown: Don't auto-trigger more than once every 2 minutes 
                    # unless manually triggered or it's been a while.
                    now = time.time()
                    last = getattr(self, 'last_translation_time', 0)
                    if now - last > 120:  # 120 seconds cooldown
                        self.trigger_auto_translation()
                    else:
                        logging.info("Auto-translation skipped due to cooldown.")

        except Exception as ex:
            logging.error(f"Load Error: {ex}")
            self.func_list_view.controls.append(ft.Text(f"Error loading functions: {ex}", color=ft.Colors.RED_400))
        self.page.update()

    def get_read_connection(self):
        """Helper to get read-only connection with retries to avoid lock errors."""
        for i in range(10):
            try:
                return duckdb.connect(str(DB_PATH), read_only=True)
            except Exception as e:
                time.sleep(0.2)
                if i == 9: raise e

    def show_function_details(self, name):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Loading details for {name}..."))
            self.page.snack_bar.open = True
            self.page.update()

            logging.info(f"Fetching details for function: {name}")
            conn = self.get_read_connection()
            row = conn.execute("SELECT code, description, tags, metadata, version, description_en, description_jp FROM functions WHERE name = ?", (name,)).fetchone()
            conn.close()
            
            if not row:
                logging.warning(f"Function {name} not found in DB.")
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Function {name} not found!"), bgcolor=ft.Colors.RED_400)
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            code, desc, tags, meta, ver, en, jp = row
            logging.info(f"Row data fetched. Version: {ver}")
            
            # Safe handling of None/Empty fields
            code_text = code if code else "# No code available"
            
            # Robust JSON parsing for tags
            tags_list = []
            if tags:
                try:
                    tags_list = json.loads(tags)
                except Exception as je:
                    logging.error(f"JSON Parse Error (tags): {je}")

            # Robust JSON parsing for metadata
            meta_dict = {}
            if meta:
                try:
                    meta_dict = json.loads(meta)
                except Exception as je:
                    logging.error(f"JSON Parse Error (meta): {je}")
            
            # Modal content
            content = ft.Column([
                ft.Text(f"{name} (v{ver})", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([ft.Chip(label=str(t)) for t in tags_list], wrap=True) if tags_list else ft.Text("No tags", italic=True, size=12),
                ft.Divider(),
                ft.Text(self.t["code"], weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text(code_text, font_family="Consolas", size=11, selectable=True),
                    padding=10, bgcolor=ft.Colors.GREY_50, border_radius=5, border=ft.Border.all(1, ft.Colors.GREY_200)
                ),
                ft.Divider(),
                ft.Text("Metadata", weight=ft.FontWeight.BOLD),
                ft.Text(json.dumps(meta_dict, indent=2, ensure_ascii=False), font_family="Consolas", size=10, color=ft.Colors.GREY_700, selectable=True),
            ], scroll=ft.ScrollMode.AUTO, tight=True, spacing=10)

            def close_dlg(e):
                # Use the direct reference instead of self.page.dialog for better compatibility
                self.dialog.open = False
                self.page.update()

            content_container = ft.Container(content, width=700, height=600)
            
            # Use Overlay method which is more robust across versions
            self.dialog = ft.AlertDialog(
                title=ft.Text(self.t["details_title"]),
                content=content_container,
                actions=[ft.TextButton(self.t["close"], on_click=close_dlg)],
            )
            
            # Fallback for different Flet versions: try open() first, then overlay
            try:
                 self.page.open(self.dialog)
            except:
                self.page.overlay.append(self.dialog)
                self.dialog.open = True
                self.page.update()
            
            logging.info(f"Detail modal opened for: {name}")
            
        except Exception as ex:
            error_trace = traceback.format_exc()
            logging.error(f"Detail Error: {ex}\n{error_trace}")
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error opening details: {ex}"), bgcolor=ft.Colors.RED_400)
            self.page.snack_bar.open = True
            self.page.update()

    def handle_bulk_delete(self, e):
        count = len(self.selected_functions)
        if count == 0: return
        
        self.log(f"Deleting {count} functions...", ft.Colors.RED_200)
        try:
            conn = duckdb.connect(str(DB_PATH))
            for name in list(self.selected_functions):
                row = conn.execute("SELECT id FROM functions WHERE name = ?", (name,)).fetchone()
                if row:
                    fid = row[0]
                    conn.execute("DELETE FROM function_versions WHERE function_id = ?", (fid,))
                    conn.execute("DELETE FROM embeddings WHERE function_id = ?", (fid,))
                    conn.execute("DELETE FROM functions WHERE id = ?", (fid,))
            conn.commit()
            conn.close()
            
            self.selected_functions.clear()
            self.bulk_actions_bar.visible = False
            self.load_functions()
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Deleted {count} functions."))
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.log(f"Bulk Delete Error: {ex}", ft.Colors.RED_600)

    def handle_bulk_verify(self, e):
        count = len(self.selected_functions)
        if count == 0: return
        if not self.is_running:
            self.page.snack_bar = ft.SnackBar(ft.Text("Start server first!"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.log(f"Triggering verification for {count} functions...", ft.Colors.BLUE_200)
        try:
            conn = duckdb.connect(str(DB_PATH))
            for name in self.selected_functions:
                 conn.execute("UPDATE functions SET status = 'pending' WHERE name = ?", (name,))
            conn.commit()
            conn.close()
            
            self.selected_functions.clear()
            self.bulk_actions_bar.visible = False
            self.load_functions()
            self.page.update()
        except Exception as ex:
            self.log(f"Bulk Verify Error: {ex}", ft.Colors.RED_600)

    def load_settings(self, initial=False):
        # 1. Load from legacy .env (for backward compatibility)
        if ENV_PATH.exists():
            logging.info("Loading settings from .env")
            try:
                with open(ENV_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        if "EMBEDDING_MODEL" in line:
                            parts = line.split("=", 1)
                            if len(parts) == 2 and hasattr(self, 'model_dropdown'):
                                self.model_dropdown.value = parts[1].strip()
                        if "UI_LANG" in line:
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                self.lang = parts[1].strip()
            except Exception as e:
                logging.error(f"Error loading .env: {e}")
        
        # 2. Load from data/settings.json (Preferred for distribution)
        if SETTINGS_PATH.exists():
            logging.info(f"Loading settings from {SETTINGS_PATH}")
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "hf_token" in data:
                        self.hf_token_value = data["hf_token"]
                        if hasattr(self, 'hf_token_input'):
                            self.hf_token_input.value = data["hf_token"]
                    if "ui_lang" in data:
                        self.lang = data["ui_lang"]
                    if "embedding_model" in data:
                        self.embedding_model_value = data["embedding_model"]
                        if hasattr(self, 'model_dropdown'):
                            self.model_dropdown.value = data["embedding_model"]
            except Exception as e:
                logging.error(f"Error loading settings.json: {e}")

        # Apply language to dropdown
        if hasattr(self, 'lang_dropdown'): self.lang_dropdown.value = self.lang
        
        if not initial: self.page.update()

    def save_settings(self, e):
        # Update state from UI
        self.embedding_model_value = self.model_dropdown.value
        self.hf_token_value = self.hf_token_input.value if hasattr(self, 'hf_token_input') else self.hf_token_value
        new_lang = self.lang_dropdown.value
        
        logging.info(f"Saving settings. Model: {self.embedding_model_value}, Lang: {new_lang}")
        
        # Check if language changed via save button
        lang_changed = False
        if new_lang and new_lang != self.lang:
            lang_changed = True
            self.lang = new_lang
            
        # 1. Save critical server config to .env (Server legacy support)
        content = f"# Function Store MCP Config\nEMBEDDING_MODEL={self.embedding_model_value}\nFORCE_CPU=0\nUI_LANG={self.lang}\n"
        try:
            with open(ENV_PATH, "w", encoding="utf-8") as f: f.write(content)
        except Exception as ex:
            logging.error(f"Failed to write .env: {ex}")

        # 2. Save user credentials to data/settings.json (Distributable)
        settings_data = {
            "hf_token": self.hf_token_value,
            "ui_lang": self.lang,
            "embedding_model": self.embedding_model_value
        }
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=2)
            self.page.snack_bar = ft.SnackBar(ft.Text(self.t["settings_saved"]), bgcolor=ft.Colors.GREEN_600)
        except Exception as ex:
             logging.error(f"Failed to write settings.json: {ex}")
             self.page.snack_bar = ft.SnackBar(ft.Text(f"{self.t['settings_fail']}{ex}"), bgcolor=ft.Colors.RED_400)
        
        self.page.snack_bar.open = True
        
        if lang_changed:
            logging.info("Language mismatch detected in save. Triggering rebuild.")
            self.build_ui()
            self.load_functions()
        else:
            self.page.update()


def main(page: ft.Page):
    app = FunctionStoreApp(page)

if __name__ == "__main__":
    ft.app(target=main)