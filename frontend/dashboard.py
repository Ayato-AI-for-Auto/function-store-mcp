import asyncio
import json
import threading
from pathlib import Path

import flet as ft
from google import genai
from mcp_core.config import BASE_DIR, DATA_DIR, DB_PATH, SETTINGS_PATH
from mcp_core.core.mcp_manager import (
    get_registration_status,
    register_with_client,
)
from mcp_core.engine.sync_engine import sync_engine

from frontend.client import SoloClient
from frontend.components.details_dialog import DetailsDialog
from frontend.components.function_card import FunctionCard
from frontend.views.functions_view import FunctionsView

# Views
from frontend.views.home_view import HomeView
from frontend.views.public_store_view import PublicStoreView
from frontend.views.settings_view import SettingsView

# Derived Paths
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
SERVER_SCRIPT = BASE_DIR / "backend" / "mcp_core" / "server.py"


class SoloDashboardApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Function Store MCP - Dashboard"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 1200
        self.page.window_height = 850
        self.page.padding = 0
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE_900,
            visual_density=ft.VisualDensity.COMFORTABLE,
            font_family="Segoe UI, Roboto, Helvetica, Arial, sans-serif",
        )

        # Localization State
        self.lang = "en"
        self.localization_data = self.load_localization()
        self.t = self.localization_data[self.lang]

        # Global State
        self.process = None
        self.is_running = False
        self.functions = []
        self.search_history = []
        self.search_history_path = DATA_DIR / "search_history.json"
        self.selected_functions = set()
        self.public_functions = []

        # Client (Architecture Unification)
        self.client = SoloClient(str(VENV_PYTHON), str(SERVER_SCRIPT))
        self.is_syncing = False

        # Build UI
        self.build_ui()

        # Start background check loop
        self.page.run_task(self.update_ui_loop)

        # Initial Database/Settings Loading
        self.cleanup_parquet_cache()

        self.log(
            f"Dashboard modularized. Flet version: {ft.__version__}", ft.Colors.BLUE_400
        )
        self.load_settings()
        self.load_search_history()
        self.load_functions()

        # Trigger background sync (Push & Pull)
        threading.Thread(target=self._safe_bg_sync, daemon=True).start()

    def _safe_bg_sync(self):
        """Thread-safe background sync via direct function call."""
        if self.is_syncing:
            return

        self.is_syncing = True
        self.log("Background Sync: Initializing...", ft.Colors.GREY_500)

        try:
            count = sync_engine.pull()
            self.log(
                f"Background Sync: Complete! Updated {count} functions.",
                ft.Colors.GREEN_400,
            )
            self.load_functions()
        except Exception as e:
            self.log(f"Sync Error: {e}", ft.Colors.RED_400)
        finally:
            self.is_syncing = False

    def load_localization(self):
        i18n_path = Path(__file__).parent / "i18n.json"
        if i18n_path.exists():
            with open(i18n_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Fallback (minimum set)
            return {
                "en": {"title": "Error: i18n.json missing"},
                "jp": {"title": "Error: i18n.json missing"},
            }

    def build_ui(self):
        # Instantiate Views
        self.home_view = HomeView(self)
        self.home_view.visible = False  # Home is now index 1
        self.functions_view = FunctionsView(self)
        self.functions_view.visible = True  # Functions is now index 0 (Home)
        self.public_view = PublicStoreView(self)

        self.settings_view = SettingsView(self)

        # Sidebar Destinations
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
        self.dest_team = ft.NavigationRailDestination(
            icon=ft.Icons.PUBLIC_OUTLINED,
            selected_icon=ft.Icons.PUBLIC,
            label=self.t.get("team_tab", "Public Store"),
        )

        self.dest_settings = ft.NavigationRailDestination(
            icon=ft.Icons.SETTINGS_OUTLINED,
            selected_icon=ft.Icons.SETTINGS,
            label=self.t["settings"],
        )

        # Sidebar
        self.rail = ft.NavigationRail(
            selected_index=0,  # Functions Explorer as default
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=110,
            min_extended_width=200,
            leading=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.BOLT_ROUNDED, size=48, color=ft.Colors.BLUE_900
                        ),
                        ft.Text(
                            "AYATO",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_900,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                margin=ft.Margin(0, 40, 0, 40),
                alignment=ft.Alignment(0, 0),
            ),
            group_alignment=-0.8,
            destinations=[
                self.dest_team,
                self.dest_settings,
            ],
            on_change=self.handle_rail_change,
            bgcolor=ft.Colors.GREY_50,
        )

        # Main Layout
        self.page.add(
            ft.Row(
                [
                    self.rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(
                        content=ft.Stack(
                            [
                                self.home_view,
                                self.functions_view,
                                self.public_view,
                                self.settings_view,
                            ]
                        ),
                        expand=True,
                        padding=20,
                    ),
                ],
                expand=True,
            )
        )

    def handle_rail_change(self, e):
        idx = e.control.selected_index
        # New order: Functions(0), Dashboard(1), Team(2), Galaxy(3), Settings(4)
        self.functions_view.visible = idx == 0
        self.home_view.visible = idx == 1
        self.public_view.visible = idx == 2
        self.settings_view.visible = idx == 4

        if idx == 0:
            self.load_functions()
        elif idx == 2:
            self.load_public_functions()
        self.page.update()

    def switch_language(self, e):
        self.lang = self.settings_view.lang_dropdown.value
        self.t = self.localization_data[self.lang]
        self.page.title = self.t["title"]

        # Update Rail Labels
        self.dest_dashboard.label = self.t["dashboard"]
        self.dest_functions.label = self.t["functions"]
        self.dest_team.label = self.t.get("team_tab", "Public")
        self.dest_settings.label = self.t["settings"]

        # Update Views Localization
        self.home_view.update_localization()
        self.functions_view.update_localization()
        self.public_view.update_localization()
        self.settings_view.update_localization()

        self.page.update()
        self.log(f"Language switched to {self.lang}", ft.Colors.BLUE_400)

    def log(self, message, color=ft.Colors.WHITE):
        self.home_view.log(message, color)

    def clear_logs(self, e):
        self.home_view.log_list.controls.clear()
        self.home_view.log_list.update()

    def cleanup_parquet_cache(self):
        parquet_path = DB_PATH.with_name("dashboard.parquet")
        if parquet_path.exists():
            try:
                parquet_path.unlink()
            except Exception:
                pass

    # --- Server Management ---
    def toggle_server(self, e):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        if not VENV_PYTHON.exists():
            self.log(self.t["env_not_found"], ft.Colors.RED_400)
            return

        self.log(self.t["starting_mcp"], ft.Colors.BLUE_400)
        try:
            self.client.start()
            self.is_running = True

            # Start output reading threads (STDERR still useful for logs)
            if self.client.process:
                threading.Thread(
                    target=self.read_output,
                    args=(self.client.process.stderr, "STDERR"),
                    daemon=True,
                ).start()

            self.update_status()
        except Exception as e:
            self.log(f"Failed to start server: {e}", ft.Colors.RED_400)

    def stop_server(self):
        self.client.stop()
        self.is_running = False
        self.update_status()

    def read_output(self, stream, prefix):
        for line in iter(stream.readline, ""):
            if line:
                # Default to white for INFO as requested
                color = ft.Colors.WHITE
                l_upper = line.upper()
                if (
                    "[ERROR]" in l_upper
                    or "CRITICAL" in l_upper
                    or "TRACEBACK" in l_upper
                ):
                    color = ft.Colors.RED_400
                elif "[WARNING]" in l_upper or "[WARN]" in l_upper:
                    color = ft.Colors.ORANGE_400
                elif "[INFO]" in l_upper:
                    color = ft.Colors.WHITE

                self.log(f"[{prefix}] {line.strip()}", color)

    async def update_ui_loop(self):
        counter = 0
        while True:
            if self.is_running and self.client.process:
                if self.client.process.poll() is not None:
                    self.is_running = False
                    self.log(self.t["unexpected_stop"], ft.Colors.RED_600)
                    self.update_status()

            # Every 30 seconds, try to sync pending functions
            if counter % 15 == 0:
                try:
                    # Offload to thread to avoid blocking async loop if network is slow
                    threading.Thread(target=self._safe_bg_sync, daemon=True).start()
                except Exception:
                    pass

            counter += 1
            await asyncio.sleep(2)

    def update_status(self):
        if self.is_running:
            self.home_view.status_text.value = self.t["running"]
            self.home_view.status_text.color = ft.Colors.GREEN_600
            self.home_view.status_icon.color = ft.Colors.GREEN_600
            self.home_view.start_stop_btn.text = self.t["stop_server"]
            self.home_view.start_stop_btn.bgcolor = ft.Colors.RED_600
        else:
            self.home_view.status_text.value = self.t["stopped"]
            self.home_view.status_text.color = ft.Colors.GREY_600
            self.home_view.status_icon.color = ft.Colors.GREY_400
            self.home_view.start_stop_btn.text = self.t["start_server"]
            self.home_view.start_stop_btn.bgcolor = ft.Colors.GREEN_600
        self.home_view.update()

    # --- Functions Management ---
    def load_functions(self, query=None):
        self.functions_view.func_list_view.controls.clear()
        try:
            if not self.is_running:
                return  # Can't fetch if server is down

            if query:
                if query.startswith("tag:"):
                    tag = query.split(":", 1)[1]
                    rows = self.client.list_functions(tag=tag)
                else:
                    rows = self.client.list_functions(query=query)
            else:
                rows = self.client.list_functions()

            # Update Tag Cloud (restored)
            self.update_tag_cloud(rows)

            for r in rows:
                # Use the new FunctionCard component
                self.functions_view.func_list_view.controls.append(
                    FunctionCard(
                        r=r,
                        app=self,
                        on_click_details=self.show_function_details,
                        on_delete=self.confirm_delete_single,
                    )
                )
        except Exception as e:
            self.log(f"Error loading functions: {e}", ft.Colors.RED_400)
        self.functions_view.update()

    # create_func_item and on_item_hover removed (moved to components/function_card.py)

    def handle_selection_change(self, e, name):
        if e.control.value:
            self.selected_functions.add(name)
        else:
            self.selected_functions.discard(name)
        self.functions_view.batch_delete_btn.visible = len(self.selected_functions) > 0
        self.functions_view.update()

    def handle_search(self, e):
        query = self.functions_view.search_field.value.strip()
        if query:
            if query not in self.search_history:
                self.search_history.insert(0, query)
                self.search_history = self.search_history[:10]
                self.save_search_history()
                self.update_search_history_ui()
        self.load_functions(query)

    def update_tag_cloud(self, rows):
        tag_counts = {}
        for r in rows:
            tags = r.get("tags", [])
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1

        # We need to update the HomeView's tag cloud
        # For simplicity, if we have the view, update it
        if hasattr(self, "home_view") and hasattr(self.home_view, "tag_cloud"):
            self.home_view.update_tags(tag_counts)

    def show_function_details(self, name=None, public_data=None):
        try:
            target_name = name or (
                public_data.get("name") if public_data else "Unknown"
            )
            self.log(
                f"[DEBUG] show_function_details called for: {target_name}",
                ft.Colors.BLUE_200,
            )

            # Immediate feedback
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Opening details for {target_name}..."), duration=1000
            )
            self.page.snack_bar.open = True
            self.page.update()

            if public_data:
                self.log(
                    f"[DEBUG] Using public_data for {target_name}", ft.Colors.GREY_400
                )
                code = (
                    public_data.get("code") or "# No source code available in preview"
                )
                desc = public_data.get("description") or self.t["no_description"]
                tags_json = public_data.get("tags")
                tag_list = (
                    tags_json
                    if isinstance(tags_json, list)
                    else json.loads(tags_json)
                    if tags_json
                    else []
                )
                name = public_data.get("name", "Unknown Public Function")
                is_public = True
            else:
                self.log(
                    f"[DEBUG] Fetching local data for {target_name} via MCP Client",
                    ft.Colors.GREY_400,
                )
                func_data = self.client.get_function_details(target_name)

                if not func_data:
                    self.log(
                        f"[ERROR] Function {target_name} not found", ft.Colors.RED_400
                    )
                    return

                code = func_data.get("code", "")
                # We might need more fields from the client, for now let's assume it's basically the same
                desc = func_data.get("description", "")
                tag_list = func_data.get("tags", [])
                is_public = False

            # Use the new DetailsDialog component
            dialog = DetailsDialog(
                app=self,
                name=target_name,
                code=code,
                desc=desc,
                tags=tag_list,
                is_public=is_public,
            )

            self.page.overlay.append(dialog)
            dialog.open = True
            self.page.update()
            self.log(f"[SUCCESS] Displayed {target_name}", ft.Colors.GREEN_400)
        except Exception as ex:
            self.log(f"[CRITICAL ERROR] show_function_details: {ex}", ft.Colors.RED_400)

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def confirm_delete_single(self, name):
        def on_confirm(_):
            res = self.client.delete_function(name)
            self.log(res, ft.Colors.RED_400 if "Error" in res else ft.Colors.GREEN_400)
            self.close_dialog(dialog)
            self.load_functions()

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Function?"),
            content=ft.Text(f"Are you sure you want to delete {name}?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.FilledButton(
                    "Delete",
                    bgcolor=ft.Colors.RED_600,
                    color=ft.Colors.WHITE,
                    on_click=on_confirm,
                ),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def handle_batch_delete(self, e):
        def on_confirm(_):
            count = 0
            for name in list(self.selected_functions):
                res = self.client.delete_function(name)
                if "SUCCESS" in res:
                    count += 1
            self.log(f"Deleted {count} functions", ft.Colors.RED_400)
            self.selected_functions.clear()
            self.functions_view.batch_delete_btn.visible = False
            self.close_dialog(dialog)
            self.load_functions()

        dialog = ft.AlertDialog(
            title=ft.Text("Batch Delete?"),
            content=ft.Text(
                f"Delete {len(self.selected_functions)} selected functions?"
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.FilledButton(
                    "Delete All",
                    bgcolor=ft.Colors.RED_600,
                    color=ft.Colors.WHITE,
                    on_click=on_confirm,
                ),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def render_public_functions(self):
        self.public_view.public_list_view.controls.clear()
        if not self.public_functions:
            self.public_view.public_list_view.controls.append(
                ft.Text("No public functions found.", color=ft.Colors.GREY_500)
            )
        else:
            for func in self.public_functions:
                self.public_view.public_list_view.controls.append(
                    self.create_public_func_item(func)
                )
        self.public_view.update()

    def create_public_func_item(self, func):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.LANGUAGE_ROUNDED,
                                        color=ft.Colors.GREEN_600,
                                        size=18,
                                    ),
                                    ft.Text(
                                        func["name"], size=16, weight=ft.FontWeight.BOLD
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Text(
                                func.get("description", self.t["no_description"]),
                                size=13,
                                max_lines=1,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.PERSON_OUTLINE,
                                        size=12,
                                        color=ft.Colors.GREY_400,
                                    ),
                                    ft.Text(
                                        "Cloud Community",
                                        size=10,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        expand=True,
                    ),
                    ft.FilledButton(
                        self.t["import"],
                        icon=ft.Icons.DOWNLOAD_ROUNDED,
                        on_click=lambda _: self.handle_import(func),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_900),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_100),
            on_click=lambda _, f=func: self.show_function_details(
                name=f["name"], public_data=f
            ),
            on_hover=lambda e: self.on_item_hover(e),  # Reuse hover effect
        )

    def handle_import(self, func):
        self.log(f"Importing '{func['name']}'...", ft.Colors.BLUE_400)
        # Import is also handled via save_function with skip_test=True
        # Or we can add an import_function tool
        res = self.client.save_function(
            name=func["name"],
            code=func["code"],
            description=func.get("description", ""),
            tags=func.get("tags", []),
            skip_test=True,
        )
        if "SUCCESS" in res:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(self.t["import_success"]), bgcolor=ft.Colors.GREEN_600
            )
            self.load_functions()
        else:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Import failed: {res}"), bgcolor=ft.Colors.RED_600
            )
        self.page.snack_bar.open = True
        self.page.update()

    def handle_sync(self, e):
        self.log("Syncing...", ft.Colors.BLUE_400)
        try:
            count = sync_engine.pull()
            self.log(f"Sync complete! Updated {count} functions.", ft.Colors.GREEN_400)
        except Exception as ex:
            self.log(f"Sync Error: {ex}", ft.Colors.RED_400)

    # --- Settings ---
    def load_settings(self):
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                s = json.load(f)
                self.settings_view.model_dropdown.value = s.get(
                    "FS_MODEL_NAME",
                    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                )
                self.settings_view.gemini_api_key_field.value = s.get(
                    "FS_GEMINI_API_KEY", ""
                )
                self.lang = s.get("UI_LANG", "en")

                self.settings_view.lang_dropdown.value = self.lang
                self.t = self.localization_data.get(
                    self.lang, self.localization_data["en"]
                )
                self.switch_language(None)
        self.refresh_registration_status()

    def save_settings_to_file(self, e):
        s = {
            "FS_MODEL_NAME": self.settings_view.model_dropdown.value,
            "FS_GEMINI_API_KEY": self.settings_view.gemini_api_key_field.value,
            "UI_LANG": self.settings_view.lang_dropdown.value,
        }

        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
        self.page.snack_bar = ft.SnackBar(
            ft.Text(self.t["settings_saved"]), bgcolor=ft.Colors.GREEN_600
        )
        self.page.snack_bar.open = True
        self.page.update()

    def verify_gemini_key(self, e):
        api_key = self.settings_view.gemini_api_key_field.value.strip()
        if not api_key:
            return

        self.log("Verifying Gemini API Key...", ft.Colors.BLUE_400)
        self.settings_view.verify_btn.disabled = True
        self.page.update()

        def _verify():
            try:
                client = genai.Client(api_key=api_key)
                # Try to list models as a connection test
                client.models.list()

                self.page.run_task(self._verify_success)
            except Exception as ex:
                self.log(f"Verification Failed: {ex}", ft.Colors.RED_400)
                self.page.run_task(self._verify_failure)

        threading.Thread(target=_verify, daemon=True).start()

    async def _verify_success(self, _=None):
        self.settings_view.verify_btn.disabled = False
        self.settings_view.verify_btn.icon = ft.Icons.CHECK_CIRCLE
        self.settings_view.verify_btn.color = ft.Colors.GREEN_600
        self.log(self.t["api_key_valid"], ft.Colors.GREEN_400)
        self.page.snack_bar = ft.SnackBar(
            ft.Text(self.t["api_key_valid"]), bgcolor=ft.Colors.GREEN_600
        )
        self.page.snack_bar.open = True
        self.page.update()

    async def _verify_failure(self, _=None):
        self.settings_view.verify_btn.disabled = False
        self.settings_view.verify_btn.icon = ft.Icons.ERROR_OUTLINE
        self.settings_view.verify_btn.color = ft.Colors.RED_600
        self.page.snack_bar = ft.SnackBar(
            ft.Text(self.t["api_key_invalid"]), bgcolor=ft.Colors.RED_600
        )
        self.page.snack_bar.open = True
        self.page.update()

    def handle_registration(self, client_name: str):

        self.log(f"Registering with {client_name}...", ft.Colors.BLUE_400)
        try:
            res = register_with_client(client_name)
            if "SUCCESS" in res:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Successfully registered with {client_name}!"),
                    bgcolor=ft.Colors.GREEN_600,
                )
            else:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Registration failed: {res}"), bgcolor=ft.Colors.RED_600
                )
            self.page.snack_bar.open = True
            self.page.update()
            self.refresh_registration_status()
        except Exception as e:
            self.log(f"Registration Error: {e}", ft.Colors.RED_400)

    def refresh_registration_status(self):
        try:
            status = get_registration_status()
            self.settings_view.cursor_btn.style.bgcolor = (
                ft.Colors.GREEN_100 if status.get("cursor") else ft.Colors.BLUE_50
            )
            self.settings_view.claude_btn.style.bgcolor = (
                ft.Colors.GREEN_100 if status.get("claude") else ft.Colors.BLUE_50
            )
            self.settings_view.antigravity_btn.style.bgcolor = (
                ft.Colors.GREEN_100 if status.get("antigravity") else ft.Colors.BLUE_50
            )
            self.settings_view.update()
        except Exception:
            pass

    def load_search_history(self):
        if self.search_history_path.exists():
            with open(self.search_history_path, "r", encoding="utf-8") as f:
                self.search_history = json.load(f)
                self.update_search_history_ui()

    def save_search_history(self):
        with open(self.search_history_path, "w", encoding="utf-8") as f:
            json.dump(self.search_history, f)

    def update_search_history_ui(self):
        self.functions_view.search_history_list.controls = [
            ft.TextButton(h, on_click=lambda _, q=h: self.apply_history_search(q))
            for h in self.search_history
        ]
        self.functions_view.update()

    def apply_history_search(self, q):
        self.functions_view.search_field.value = q
        self.load_functions(q)


def main(page: ft.Page):
    SoloDashboardApp(page)


if __name__ == "__main__":
    ft.run(main)
