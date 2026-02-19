import flet as ft


class PublicStoreView(ft.Column):
    def __init__(self, app):
        super().__init__(expand=True, visible=False)
        self.app = app
        self.t = app.t

        self.public_title_text = ft.Text(
            "Global Store", size=28, weight=ft.FontWeight.BOLD
        )
        self.public_desc_text = ft.Text(self.t["team_desc"], color=ft.Colors.GREY_600)

        self.public_search_field = ft.TextField(
            hint_text=self.t["public_search_hint"],
            expand=True,
            on_submit=self.app.handle_public_search,
            border_radius=10,
        )

        self.public_list_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
        )

        self.public_store_header = ft.Text(
            self.t["public_store_title"], weight=ft.FontWeight.BOLD
        )

        self.sync_btn = ft.FilledButton(
            self.t["sync_now"],
            icon=ft.Icons.SYNC,
            on_click=self.app.handle_sync,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE),
        )

        self.trending_title = ft.Text(
            "Trending Public Functions", size=16, weight=ft.FontWeight.BOLD
        )

        self.controls = [
            ft.Row(
                [
                    self.public_title_text,
                    ft.IconButton(
                        ft.Icons.REFRESH,
                        on_click=lambda _: self.app.load_public_functions(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            self.public_desc_text,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.PUBLIC, color=ft.Colors.GREEN_400),
                        self.public_store_header,
                        self.sync_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            ),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            # Public Search Bar
            ft.Row(
                [
                    self.public_search_field,
                    ft.IconButton(
                        ft.Icons.SEARCH, on_click=self.app.handle_public_search
                    ),
                ]
            ),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            self.trending_title,
            ft.Container(
                content=self.public_list_view,
                expand=True,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.Border.all(1, ft.Colors.GREY_200),
            ),
        ]

    def update_localization(self):
        self.t = self.app.t
        self.public_desc_text.value = self.t["team_desc"]
        self.public_search_field.hint_text = self.t["public_search_hint"]
        self.public_store_header.value = self.t["public_store_title"]
        self.sync_btn.text = self.t["sync_now"]
        self.update()
