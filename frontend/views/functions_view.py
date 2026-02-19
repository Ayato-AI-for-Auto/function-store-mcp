import flet as ft


class FunctionsView(ft.Column):
    def __init__(self, app):
        super().__init__(expand=True, visible=False)
        self.app = app
        self.t = app.t

        # UI Elements
        self.functions_title = ft.Text(
            self.t["func_explorer"], size=28, weight=ft.FontWeight.BOLD
        )
        self.functions_desc = ft.Text(self.t["func_desc"], color=ft.Colors.GREY_600)

        self.search_field = ft.TextField(
            hint_text=self.t["search_hint"],
            expand=True,
            on_submit=self.app.handle_search,
            border_radius=10,
        )
        self.func_list_view = ft.ListView(expand=True, spacing=10, padding=10)

        self.tag_cloud_view = ft.Row(wrap=True, spacing=5)
        self.search_history_list = ft.ListView(height=100, spacing=5)

        self.batch_delete_btn = ft.IconButton(
            ft.Icons.DELETE_SWEEP,
            visible=False,
            on_click=self.app.handle_batch_delete,
            icon_color=ft.Colors.RED_600,
        )

        self.search_history_title = ft.Text(
            self.t["search_history"], size=12, weight=ft.FontWeight.BOLD
        )
        self.search_history_container = ft.Container(
            content=ft.Column([self.search_history_title, self.search_history_list]),
            visible=False,
            padding=10,
            bgcolor=ft.Colors.GREY_100,
            border_radius=10,
        )

        self.tag_cloud_title = ft.Text(
            self.t["tag_cloud"],
            size=14,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_700,
        )

        self.controls = [
            ft.Row(
                [
                    self.functions_title,
                    ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.HISTORY, on_click=self.toggle_search_history
                            ),
                            self.batch_delete_btn,
                            ft.IconButton(
                                ft.Icons.REFRESH,
                                on_click=lambda _: self.app.load_functions(),
                            ),
                        ]
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            self.functions_desc,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            # Tag Cloud
            self.tag_cloud_title,
            self.tag_cloud_view,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            self.search_history_container,
            # Search Bar
            ft.Row(
                [
                    self.search_field,
                    ft.IconButton(ft.Icons.SEARCH, on_click=self.app.handle_search),
                ]
            ),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=self.func_list_view,
                expand=True,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            ),
        ]

    def toggle_search_history(self, e):
        self.search_history_container.visible = (
            not self.search_history_container.visible
        )
        self.update()

    def update_localization(self):
        self.t = self.app.t
        self.functions_title.value = self.t["func_explorer"]
        self.functions_desc.value = self.t["func_desc"]
        self.search_field.hint_text = self.t["search_hint"]
        self.tag_cloud_title.value = self.t["tag_cloud"]
        self.search_history_title.value = self.t["search_history"]
        self.update()
