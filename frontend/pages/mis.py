import calendar
from collections import defaultdict
from nicegui import ui

from auth.auth import protected_page
from components.layout import render_topbar, sidebar
from components.dialogs import open_new_entry_dialog
from services.api import api_get
from components.table import render_table, render_complaints_table

async def mis_table_page_base(stage: str, month: str | None = None) -> None:
    """Generic MIS table page logic used by both Booking and Delivery routes."""
    label = "Booking MIS" if stage == "booking" else "Delivery MIS"
    render_topbar(label)

    try:
        all_transactions: list = await api_get("/transactions")
    except Exception:
        all_transactions = []

    # Split logic
    if stage == "booking":
        transactions = [t for t in all_transactions if not t.get("delivery_date")]
    else:
        transactions = [t for t in all_transactions if t.get("delivery_date")]

    # Get months for sidebar grouping
    month_map = defaultdict(list)
    for t in transactions:
        bd = t.get("booking_date", "")
        if bd and len(bd) >= 7:
            month_map[bd[:7]].append(t)
    sorted_months = sorted(month_map.keys(), reverse=True)

    def month_label_local(ym: str) -> str:
        try:
            y, m = ym.split("-")
            return f"{calendar.month_abbr[int(m)]} '{y[2:]}"
        except Exception:
            return ym

    # Filter by specific month if passed in URL
    if month:
        transactions = [
            t
            for t in transactions
            if (t.get("booking_date", "") or "").startswith(month)
        ]

    total_entries = len(transactions)
    total_excess = sum(t.get("total_excess_discount", 0) or 0 for t in transactions)

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # ── SIDEBAR ─────────────────────────────────────────
        with ui.column().classes(
            "w-[220px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"
        ):
            ui.label("Quick Nav").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-400 px-4 mb-1.5 mt-4.5"
            )
            ui.link("📊 Dashboard", "/").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )

            is_booking = stage == "booking"
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                f"flex px-4 py-2 text-[12.5px] {'font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A]' if is_booking else 'font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50'} no-underline"
            )

            is_delivery = stage == "delivery"
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                f"flex px-4 py-2 text-[12.5px] {'font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A]' if is_delivery else 'font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50'} no-underline"
            )
            ui.link("📑 Complaints Table", "/complaints-table").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )

            ui.element("div").classes("h-[1px] bg-gray-100 mx-4 my-2")
            ui.label("Filter by Month").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-400 px-4 mb-1.5 mt-4.5"
            )

            route_path = f"/{stage}-mis"
            ui.link("All Months", route_path).classes(
                f"flex px-4 py-1.5 text-[12.5px] font-medium {'text-[#E8402A]' if not month else 'text-gray-600'} hover:bg-gray-50 no-underline"
            )
            for ym in sorted_months:
                is_curr = month == ym
                with ui.link(target=f"{route_path}?month={ym}").classes(
                    f"flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium {'text-[#E8402A] bg-[#FEF2F0]' if is_curr else 'text-gray-600'} hover:bg-gray-50 no-underline w-full"
                ):
                    ui.label(month_label_local(ym))
                    ui.label(str(len(month_map[ym]))).classes(
                        "text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500"
                    )
            
            sidebar()

        # ── MAIN CONTENT ─────────────────────────────────────
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    title = f"{label}{' — ' + month_label_local(month) if month else ' — All Months'}"
                    ui.label(title).classes(
                        "text-[18px] font-bold text-gray-900 leading-none"
                    )
                    exc_txt = (
                        f" · ₹{total_excess:,.0f} excess" if total_excess > 0 else ""
                    )
                    ui.label(f"{total_entries} records{exc_txt}").classes(
                        "text-[12px] text-gray-400"
                    )

                with (
                    ui.button(on_click=open_new_entry_dialog)
                    .classes(
                        "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm"
                    )
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("text-white text-lg text-weight-bold")
                    ui.label("New Entry").classes("text-weight-bold pl-2")

            with ui.card().classes("w-full p-0 shadow-sm rounded-xl mb-8"):
                render_table(transactions, stage=stage)

@ui.page("/booking-mis")
@protected_page
async def booking_mis_page(month: str | None = None) -> None:
    await mis_table_page_base(stage="booking", month=month)

@ui.page("/delivery-mis")
@protected_page
async def delivery_mis_page(month: str | None = None) -> None:
    await mis_table_page_base(stage="delivery", month=month)

@ui.page("/complaints-table")
@protected_page
async def complaints_table_page():
    render_topbar("Complaints Table")

    try:
        response: dict = await api_get("/complaints/")
        complaints = response.get("data", [])
        total_entries = response.get("total", 0)
    except Exception:
        complaints = []
        total_entries = 0

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # ── SIDEBAR ─────────────────────────────────────────
        with ui.column().classes(
            "w-[220px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"
        ):
            ui.label("Quick Nav").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-400 px-4 mb-1.5 mt-4.5"
            )
            ui.link("📊 Dashboard", "/").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📑 Complaints Table", "/complaints-table").classes(
                "flex px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] no-underline"
            )
            sidebar()

        # ── MAIN CONTENT ─────────────────────────────────────
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    ui.label("Complaints Table").classes(
                        "text-[18px] font-bold text-gray-900 leading-none"
                    )
                    ui.label(f"{total_entries} complaints").classes(
                        "text-[12px] text-gray-400"
                    )
                with (
                    ui.button(on_click=lambda: ui.navigate.to("/complaint-form"))
                    .classes(
                        "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm"
                    )
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("text-white text-lg text-weight-bold")
                    ui.label("New Complaint").classes("text-weight-bold pl-2")

            with ui.card().classes("w-full p-0 shadow-sm rounded-xl mb-8"):
                render_complaints_table(complaints)
