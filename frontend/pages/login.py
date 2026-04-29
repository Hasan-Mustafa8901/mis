import httpx
from nicegui import ui
from auth.auth import set_token, get_token
from components.layout import render_topbar
from utils.constants import BASE_URL

@ui.page("/login")
def login_page():
    if get_token():
        ui.navigate.to("/")
    
    render_topbar("Login Page")
    
    with ui.column().classes("absolute-center items-center gap-4 w-80"):
        with ui.card().classes("shadow-md w-full"):
            ui.label("Login").classes("text-2xl font-bold")

            username = ui.input("Username").props("outlined").classes("w-full")
            password = (
                ui.input("Password", password=True, password_toggle_button=True)
                .props("outlined")
                .classes("w-full")
            )

            async def handle_login():
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.post(
                            f"{BASE_URL}/auth/login",
                            json={
                                "name": username.value,
                                "password": password.value,
                            },
                            timeout=10,
                        )
                        r.raise_for_status()
                        data = r.json()

                    set_token(data["access_token"])
                    ui.notify("Login successful", type="positive")
                    ui.navigate.to("/")

                except Exception:
                    ui.notify("Invalid credentials", type="negative")

            ui.button("Login", on_click=handle_login).classes("w-full rounded-md")
