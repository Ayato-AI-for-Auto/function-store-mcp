import flet as ft


class DetailsDialog(ft.AlertDialog):
    def __init__(self, app, name, code, desc, tags, version, is_public=False):
        self.app = app
        self.t = app.t

        def close_dlg(_):
            self.open = False
            self.app.page.update()

        def copy_code_to_clipboard(_):
            self.app.page.set_clipboard(code)
            self.app.page.snack_bar = ft.SnackBar(
                ft.Text(self.t["copied"]), duration=1000
            )
            self.app.page.snack_bar.open = True
            self.app.page.update()

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CODE_ROUNDED, color=ft.Colors.BLUE_400),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(name, weight=ft.FontWeight.BOLD),
                                    ft.Container(
                                        content=ft.Text(
                                            f"v{version}",
                                            size=10,
                                            color=ft.Colors.GREY_700,
                                        ),
                                        bgcolor=ft.Colors.GREY_100,
                                        padding=ft.Padding.symmetric(
                                            horizontal=6, vertical=2
                                        ),
                                        border_radius=4,
                                    ),
                                ],
                                tight=True,
                            ),
                            ft.Text(
                                "Cloud Preview"
                                if is_public
                                else "Local Implementation",
                                size=10,
                                color=ft.Colors.GREY_500,
                            ),
                        ],
                        spacing=0,
                        tight=True,
                    ),
                ],
                spacing=10,
            ),
            content=ft.Column(
                [
                    ft.Text(
                        desc if desc else self.t["no_description"],
                        size=14,
                        color=ft.Colors.BLUE_GREY_800,
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        [
                            ft.Chip(
                                label=ft.Text(t, size=10),
                                bgcolor=ft.Colors.BLUE_50,
                                border_side=ft.BorderSide(1, ft.Colors.BLUE_100),
                            )
                            for t in tags
                        ],
                        wrap=True,
                    ),
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.Text(self.t["code_label"], weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                ft.Icons.COPY_ROUNDED,
                                icon_size=18,
                                tooltip=self.t["copy_code"],
                                on_click=copy_code_to_clipboard,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=ft.Text(
                            code, font_family="Consolas", size=12, color=ft.Colors.WHITE
                        ),
                        bgcolor=ft.Colors.BLACK,
                        padding=15,
                        border_radius=10,
                        expand=True,
                    ),
                ],
                width=800,
                height=650,
                scroll="auto",
                tight=True,
            ),
            actions=[ft.TextButton("Close", on_click=close_dlg)],
        )
