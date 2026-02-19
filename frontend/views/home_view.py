import flet as ft


class HomeView(ft.Column):
    def __init__(self, app):
        super().__init__(expand=True, visible=True)
        self.app = app
        self.t = app.t

        # UI Elements
        self.status_icon = ft.Icon(
            ft.Icons.RADIO_BUTTON_CHECKED, color=ft.Colors.GREY_400
        )
        self.status_text = ft.Text(self.t["stopped"], color=ft.Colors.GREY_600)
        self.status_header = ft.Text(
            self.t["mcp_status"], size=16, weight=ft.FontWeight.BOLD
        )

        self.start_stop_btn = ft.ElevatedButton(
            self.t["start_server"],
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.app.toggle_server,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600,
            ),
        )

        self.log_list = ft.ListView(
            expand=True, spacing=2, padding=10, auto_scroll=True
        )
        self.clear_logs_btn_text = ft.Text(self.t["clear_logs"])
        self.clear_logs_btn = ft.TextButton(
            content=self.clear_logs_btn_text,
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self.app.clear_logs,
        )

        self.title_text = ft.Text(
            self.t["server_control"], size=28, weight=ft.FontWeight.BOLD
        )
        self.desc_text = ft.Text(self.t["server_desc"], color=ft.Colors.GREY_600)

        self.controls = [
            self.title_text,
            self.desc_text,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            # Status Card
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row([self.status_icon, self.status_text]),
                                self.status_header,
                            ],
                            expand=True,
                        ),
                        self.start_stop_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
                shadow=ft.BoxShadow(
                    blur_radius=5, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)
                ),
            ),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            # Logs Area
            ft.Text(self.t["activity_logs"], size=16, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.SelectionArea(content=self.log_list),
                expand=True,
                bgcolor=ft.Colors.BLACK87,
                border_radius=10,
                padding=5,
            ),
            self.clear_logs_btn,
        ]

    def log(self, message, color=ft.Colors.WHITE):
        self.log_list.controls.append(
            ft.Text(message, color=color, font_family="Consolas", size=12)
        )
        self.page.update() if self.page else None

    def update_localization(self):
        self.t = self.app.t
        self.title_text.value = self.t["server_control"]
        self.desc_text.value = self.t["server_desc"]
        self.status_header.value = self.t["mcp_status"]
        self.clear_logs_btn_text.value = self.t["clear_logs"]
        self.start_stop_btn.text = (
            self.t["start_server"] if not self.app.is_running else self.t["stop_server"]
        )
        self.update()
