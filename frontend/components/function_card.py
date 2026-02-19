import flet as ft


class FunctionCard(ft.Container):
    def __init__(self, r, app, on_click_details, on_delete):
        self.app = app
        self.r = r
        self.on_click_details = on_click_details
        self.on_delete = on_delete
        self.t = app.t

        name = r.get("name")
        status = r.get("status")
        ver = r.get("version")
        desc = r.get("description")
        desc_en = r.get("description_en")
        desc_jp = r.get("description_jp")
        calls = r.get("call_count")

        # Localization
        display_desc = desc
        if app.lang == "jp":
            display_desc = desc_jp or desc
        elif app.lang == "en":
            display_desc = desc_en or desc

        status_color = ft.Colors.BLUE_400
        if status == "verified":
            status_color = ft.Colors.GREEN_600
        elif status == "pending":
            status_color = ft.Colors.ORANGE_400
        elif status == "error":
            status_color = ft.Colors.RED_400

        super().__init__(
            content=ft.Row(
                [
                    ft.Checkbox(
                        value=name in app.selected_functions,
                        on_change=lambda e, n=name: app.handle_selection_change(e, n),
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.CODE_ROUNDED,
                                        color=ft.Colors.BLUE_600,
                                        size=20,
                                    ),
                                    ft.Text(
                                        f"{name}", weight=ft.FontWeight.BOLD, size=16
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            f"v{ver}", size=10, color=ft.Colors.GREY_700
                                        ),
                                        bgcolor=ft.Colors.GREY_100,
                                        padding=ft.Padding.symmetric(
                                            horizontal=6, vertical=2
                                        ),
                                        border_radius=4,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Text(
                                display_desc
                                if display_desc
                                else self.t["no_description"],
                                max_lines=1,
                                size=13,
                                color=ft.Colors.GREY_700,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.CALL_RECEIVED_ROUNDED,
                                        color=ft.Colors.GREY_400,
                                        size=12,
                                    ),
                                    ft.Text(
                                        f"{calls or 0} {self.t['calls']}",
                                        size=11,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    # Actions Area
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(
                                        (self.t.get(status) or status or "N/A").upper(),
                                        size=9,
                                        color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    padding=ft.Padding.symmetric(
                                        horizontal=10, vertical=4
                                    ),
                                    bgcolor=status_color,
                                    border_radius=20,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                    icon_color=ft.Colors.RED_400,
                                    on_click=lambda _: self.on_delete(name),
                                    tooltip="Delete",
                                ),
                            ],
                            tight=True,
                        ),
                        padding=ft.Padding.only(right=10),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            margin=ft.Margin(0, 0, 0, 4),
            padding=10,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_100),
            on_click=lambda _: self.on_click_details(name),
            on_hover=self.on_item_hover,
        )

    def on_item_hover(self, e):
        e.control.bgcolor = ft.Colors.GREY_50 if e.data == "true" else ft.Colors.WHITE
        e.control.border = ft.Border.all(
            1, ft.Colors.BLUE_200 if e.data == "true" else ft.Colors.GREY_100
        )
        e.control.update()
