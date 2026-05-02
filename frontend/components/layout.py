from nicegui import ui, app
from utils.constants import HEAD_HTML
from auth.auth import get_user, clear_token
from components.dialogs import open_new_entry_dialog

def render_topbar(page_label: str) -> None:
    """Injects sticky top header. page_label is shown as breadcrumb."""
    user = get_user()
    ui.add_head_html(HEAD_HTML)
    with ui.header().classes(
        "bg-[#0F1623] border-b-2 border-[#E8402A] px-7 py-0 h-[52px] flex items-center justify-between shadow-lg"
    ):
        with ui.row().classes("items-center gap-4 cursor-pointer"):
            with ui.column().on("click", lambda: ui.navigate.to("/")).classes("gap-0"):
                ui.label("🚗 AutoAudit MIS").classes(
                    "text-[15px] font-bold text-white tracking-tight leading-tight"
                )
                ui.label("Automobile Sales Audit System").classes(
                    "text-[9px] text-white/30 tracking-[1.1px] uppercase mt-0.5 leading-none"
                )

            ui.element("div").classes("w-[1px] h-[22px] bg-white/10 mx-1")

            with ui.row().classes("text-[12px] text-white/40 items-center"):
                ui.label(page_label).classes("text-white/80 font-semibold")

        with ui.row().classes(
            "items-center gap-3 hover:bg-white/5 px-3 py-1.5 rounded-lg transition"
        ):
            name = user.get("name") or "User"
            role = user.get("role") or "-"
            role_d = role.replace("_", " ").title() if isinstance(role, str) else str(role)

            # Avatar (initial)
            with ui.element("div").classes(
                "w-8 h-8 rounded-full bg-[#E8402A] flex items-center justify-center text-white font-bold text-sm shadow"
            ):
                initials = "".join([word[0].upper() for word in name.split()])
                ui.label(initials[:2] if len(initials) >= 2 else initials)

            # User details
            with ui.column().classes("gap-0"):
                ui.label(name).classes(
                    "text-[12.5px] text-white font-semibold leading-tight"
                )
                ui.label(f"{role_d} • {user.get('showroom', '-')}").classes(
                    "text-[10px] text-white/40 tracking-wide leading-none"
                )

def sidebar():
    # Attempt to get current route for active highlighting
    try:
        current_route = ui.context.client.page.route
    except Exception:
        current_route = ""

    def nav_link(label: str, target: str, icon: str):
        is_active = current_route == target
        base_classes = "flex items-center gap-3 px-4 py-2 text-[12.5px] no-underline transition-all rounded-r-lg mr-2"
        if is_active:
            classes = f"{base_classes} font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A]"
        else:
            classes = f"{base_classes} font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900"

        with ui.link(target=target).classes(classes):
            ui.icon(icon).classes("text-lg")
            ui.label(label)

    with ui.column().classes("w-full h-full"):
        ui.label("Quick Nav").classes(
            "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
        )

        nav_link("Dashboard", "/", "dashboard")
        nav_link("Daily Reporting", "/daily-reporting", "event_note")
        nav_link("Booking MIS", "/booking-mis", "assignment")
        nav_link("Delivery MIS", "/delivery-mis", "local_shipping")
        nav_link("Complaints Control Panel", "/complaints-table", "assignment_late")

        ui.element("div").classes("h-[1px] bg-gray-100 mx-4 my-2")

        ui.label("Quick Actions").classes(
            "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
        )

        with ui.button(on_click=open_new_entry_dialog).classes(
            "flex items-center justify-start gap-3 px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline w-full shadow-none rounded-r-lg mr-2"
        ).props("flat no-caps"):
            ui.icon("add_circle").classes("text-lg")
            ui.label("New Entry")

        with ui.link(target="/complaint-form").classes(
            "flex items-center gap-3 px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
        ):
            ui.icon("note_add").classes("text-primary text-lg")
            ui.label("Complaint Form")

        with ui.link(target="/settings").classes(
            "flex items-center gap-3 px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
        ):
            ui.icon("settings").classes("text-primary text-lg")
            ui.label("Settings")

        with ui.column().classes("mt-auto p-4 w-full"):
            def handle_logout():
                clear_token()
                ui.navigate.to("/login")

            ui.button("Logout", on_click=handle_logout).props(
                "color=red outline icon=logout no-caps"
            ).classes("w-full rounded-lg")
