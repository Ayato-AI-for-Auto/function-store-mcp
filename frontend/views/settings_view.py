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
            value="models/gemini-embedding-001",
            options=[
                ft.dropdown.Option(
                    "models/gemini-embedding-001", "Gemini Embedding (v001)"
                ),
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

        self.api_key_field = ft.TextField(
            label="Google API Key",
            password=True,
            can_reveal_password=True,
            width=400,
            hint_text="Enter your Gemini API key",
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

        self.team_id_field = ft.TextField(
            label=self.t["team_id"],
            hint_text="e.g. My-Awesome-MCP",
            width=400,
        )

        self.mcp_config_title_text = ft.Text(
            self.t.get("mcp_config_title", "MCP Configuration"),
            size=16,
            weight=ft.FontWeight.BOLD,
        )
        self.mcp_config_desc_text = ft.Text(
            self.t.get("mcp_config_desc", "Copy this JSON to share..."),
            color=ft.Colors.GREY_600,
        )
        self.mcp_config_box = ft.TextField(
            label="MCP Configuration JSON",
            multiline=True,
            read_only=True,
            min_lines=3,
            max_lines=10,
            text_size=12,
            width=600,
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
            self.quality_gate_model_dropdown,
            self.api_key_field,
            self.restart_hint_text,
            ft.Divider(height=20),
            ft.Text(self.app.t["language"], size=16, weight=ft.FontWeight.BOLD),
            self.lang_dropdown,
            self.lang_dropdown,
            ft.Divider(height=20),
            ft.Text(
                "Cloud Sync & Monetization (Local View Only)",
                size=16,
                weight=ft.FontWeight.BOLD,
            ),
            self.team_id_field,
            ft.Divider(height=20),
            self.mcp_config_title_text,
            self.mcp_config_desc_text,
            ft.Row(
                [
                    self.mcp_config_box,
                    ft.Column(
                        [
                            ft.IconButton(
                                ft.Icons.COPY,
                                on_click=self.app.copy_mcp_config,
                                tooltip=self.t.get("copy_config", "Copy"),
                            ),
                            ft.IconButton(
                                ft.Icons.REFRESH,
                                on_click=self.app.refresh_mcp_config,
                                tooltip="Refresh JSON",
                            ),
                        ]
                    ),
                ]
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

        self.mcp_config_title_text.value = self.t.get(
            "mcp_config_title", "MCP Configuration"
        )
        self.mcp_config_desc_text.value = self.t.get(
            "mcp_config_desc", "Copy this JSON to share..."
        )
        self.update()
