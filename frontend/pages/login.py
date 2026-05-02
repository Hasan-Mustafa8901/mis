import httpx
from nicegui import ui, app
from auth.auth import get_token, set_user
from utils.constants import BASE_URL, HEAD_HTML

@ui.page("/login")
def login_page():
    if get_token():
        ui.navigate.to("/")
        return

    ui.add_head_html(HEAD_HTML)
    
    with ui.column().classes("absolute-center items-center w-full"):
        # Header/Branding
        with ui.column().classes("items-center gap-0 mb-8"):
            ui.label("🚗 AutoAudit MIS").classes("text-3xl font-bold text-gray-900 tracking-tight")
            ui.label("Automobile Sales Audit System").classes("text-[10px] text-gray-400 uppercase tracking-[2px]")

        with ui.card().classes("w-96 p-8 rounded-2xl shadow-xl border-none"):
            ui.label("Sign In").classes("text-xl font-bold text-gray-800 mb-6")

            username = ui.input("Username").props("outlined label-slot").classes("w-full mb-4")
            with username:
                ui.icon("person").props("slot=prepend")

            password = ui.input("Password", password=True, password_toggle_button=True).props("outlined label-slot").classes("w-full mb-8")
            with password:
                ui.icon("lock").props("slot=prepend")

            async def handle_login():
                if not username.value or not password.value:
                    ui.notify("Please enter both username and password", type="warning")
                    return

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

                    set_user(data)
                    ui.notify(f"Welcome back, {data.get('name')}!", type="positive")
                    ui.navigate.to("/")

                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 401:
                        ui.notify("Invalid username or password", type="negative")
                    else:
                        ui.notify(f"Login failed: {exc.response.text}", type="negative")
                except Exception as exc:
                    ui.notify(f"Connection error: {str(exc)}", type="negative")

            ui.button("Login", on_click=handle_login).classes("w-full py-2.5 rounded-lg bg-[#E8402A] text-white font-bold shadow-lg shadow-red-500/20 hover:bg-[#D4351F] transition-all")

            with ui.row().classes("w-full justify-center mt-6"):
                ui.label("Need help?").classes("text-gray-400 text-sm")
                ui.link("Contact Support", "#").classes("text-[#E8402A] text-sm font-semibold ml-1 no-underline hover:underline")

    # Bottom pattern/decoration
    ui.element("div").classes("fixed-bottom w-full h-1 bg-[#E8402A]")
