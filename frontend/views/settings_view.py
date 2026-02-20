import flet as ft


class SettingsView(ft.Column):
    def __init__(self, app):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, visible=False)
        self.app = app
        self.t = app.t

        self.settings_title = ft.Text(
            self.t["settings"], size=28, weight=ft.FontWeight.BOLD
        )
        self.model_config_title = ft.Text(
            self.t["model_config"], size=16, weight=ft.FontWeight.BOLD
        )
        self.restart_hint_text = ft.Text(
            self.t["restart_hint"], size=12, color=ft.Colors.AMBER_700
        )
        self.save_settings_btn_text = ft.Text(self.t["save_settings"])

        # UI Elements
        self.model_dropdown = ft.Dropdown(
            label=self.t["embedding_model"],
            value="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            options=[
                ft.dropdown.Option(
                    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                    "Multilingual MPNet (768D, Local)",
                ),
            ],
            width=400,
        )

        self.lang_dropdown = ft.Dropdown(
            label=self.t["language"],
            value=self.app.lang,
            options=[
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("jp", "日本語"),
            ],
            width=400,
        )
        self.lang_dropdown.on_change = self.app.switch_language

        # --- Gemini Config ---
        self.gemini_title = ft.Text(
            self.t.get("gemini_config_title", "Google AI Configuration"),
            size=16,
            weight=ft.FontWeight.BOLD,
        )
        self.gemini_desc = ft.Text(
            self.t.get(
                "gemini_config_desc", "Configure Gemini API for 1536D embeddings."
            ),
            color=ft.Colors.GREY_600,
        )
        self.gemini_api_key_field = ft.TextField(
            label=self.t.get("gemini_api_key", "Gemini API Key"),
            password=True,
            can_reveal_password=True,
            width=400,
            hint_text="Enter your Google AI Studio API Key",
        )
        self.verify_btn = ft.ElevatedButton(
            self.t.get("verify_key", "Verify"),
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            on_click=self.app.verify_gemini_key,
        )
        self.get_key_btn = ft.TextButton(
            self.t.get("get_google_key", "Get Key from Google AI Studio"),
            icon=ft.Icons.OPEN_IN_NEW,
            on_click=lambda _: self.app.page.launch_url(
                "https://aistudio.google.com/api-keys"
            ),
        )
        self.team_id_field = ft.TextField(
            label=self.t["team_id"],
            hint_text="e.g. My-Awesome-MCP",
            width=400,
        )

        self.mcp_config_title_text = ft.Text(
            self.t.get("mcp_config_title", "AI Client Integration"),
            size=16,
            weight=ft.FontWeight.BOLD,
        )
        self.mcp_config_desc_text = ft.Text(
            self.t.get(
                "mcp_config_desc",
                "Enable the Function Store in your favorite AI coding tools:",
            ),
            color=ft.Colors.GREY_600,
        )

        # Registration Buttons
        self.cursor_btn = ft.ElevatedButton(
            "Cursor",
            icon=ft.Icons.AUTO_AWESOME_OUTLINED,
            on_click=lambda _: self.app.handle_registration("cursor"),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREY_900 if False else ft.Colors.BLUE_50
            ),
            color=ft.Colors.BLUE_900,
        )
        self.claude_btn = ft.ElevatedButton(
            "Claude Desktop",
            icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
            on_click=lambda _: self.app.handle_registration("claude"),
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_50),
            color=ft.Colors.BLUE_900,
        )
        self.antigravity_btn = ft.ElevatedButton(
            "Antigravity",
            icon=ft.Icons.ELECTRIC_BOLT,
            on_click=lambda _: self.app.handle_registration("antigravity"),
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_50),
            color=ft.Colors.BLUE_900,
        )

        self.save_btn = ft.ElevatedButton(
            content=self.save_settings_btn_text,
            on_click=self.app.save_settings_to_file,
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_600),
        )

        self.controls = [
            self.settings_title,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            self.model_config_title,
            self.model_dropdown,
            self.restart_hint_text,
            ft.Divider(height=20),
            ft.Text(self.app.t["language"], size=16, weight=ft.FontWeight.BOLD),
            self.lang_dropdown,
            ft.Divider(height=20),
            self.gemini_title,
            self.gemini_desc,
            self.gemini_api_key_field,
            ft.Row([self.verify_btn, self.get_key_btn]),
            ft.Divider(height=20),
            self.mcp_config_title_text,
            self.mcp_config_desc_text,
            ft.Container(
                content=ft.Row(
                    [
                        self.cursor_btn,
                        self.claude_btn,
                        self.antigravity_btn,
                    ],
                    spacing=10,
                ),
                padding=ft.Padding(0, 10, 0, 10),
            ),
            ft.Text(
                "Note: Registering will point these clients to this executable.",
                size=11,
                color=ft.Colors.GREY_500,
            ),
            ft.Divider(height=20),
            self.save_btn,
        ]

    def update_localization(self):
        self.t = self.app.t
        self.settings_title.value = self.t["settings"]
        self.model_config_title.value = self.t["model_config"]
        self.model_dropdown.label = self.t["embedding_model"]
        self.restart_hint_text.value = self.t["restart_hint"]
        self.save_settings_btn_text.value = self.t["save_settings"]
        self.lang_dropdown.label = self.t["language"]

        self.team_id_field.label = self.t["team_id"]

        self.mcp_config_desc_text.value = self.t.get(
            "mcp_config_desc", "Copy this JSON to share..."
        )
        # Update Gemini fields
        self.gemini_title.value = self.t.get(
            "gemini_config_title", "Google AI Configuration"
        )
        self.gemini_desc.value = self.t.get(
            "gemini_config_desc", "Configure Gemini API..."
        )
        self.gemini_api_key_field.label = self.t.get("gemini_api_key", "Gemini API Key")
        self.verify_btn.text = self.t.get("verify_key", "Verify")
        self.get_key_btn.text = self.t.get("get_google_key", "Get Key...")
        self.update()
