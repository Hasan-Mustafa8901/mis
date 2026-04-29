from nicegui import ui
from utils.constants import HEAD_HTML

def render_topbar(page_label: str) -> None:
    """Injects sticky top header. page_label is shown as breadcrumb."""
    ui.add_head_html(HEAD_HTML)
    with ui.header().classes(
        "bg-[#0F1623] border-b-2 border-[#E8402A] px-7 py-0 h-[52px] flex items-center justify-between shadow-lg"
    ):
        with ui.row().classes("items-center gap-4"):
            with ui.column().classes("gap-0"):
                ui.label("🚗 AutoAudit MIS").classes(
                    "text-[15px] font-bold text-white tracking-tight leading-tight"
                )
                ui.label("Automobile Sales Audit System").classes(
                    "text-[9px] text-white/30 tracking-[1.1px] uppercase mt-0.5 leading-none"
                )

            ui.element("div").classes("w-[1px] h-[22px] bg-white/10 mx-1")

            with ui.row().classes("text-[12px] text-white/40 items-center"):
                ui.label(page_label).classes("text-white/80 font-semibold")

        ui.label("AUDIT PORTAL").classes(
            "bg-[#E8402A] text-white text-[10px] font-bold tracking-[0.6px] px-2.5 py-0.5 rounded-full"
        )

def sidebar():
    from auth.auth import clear_token
    with ui.column().classes("h-full justify-between w-full p-4 bg-white shadow"):
        with ui.column().classes("mt-auto items-center"):
            def handle_logout():
                clear_token()
                ui.navigate.to("/login")
            ui.button("Logout", on_click=handle_logout).props(
                "color=red outline"
            ).classes("w-full")
