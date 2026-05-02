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
        transactions = [t for t in all_transactions if t.get("stage") == "booking"]
    else:
        transactions = [t for t in all_transactions if t.get("stage") == "delivery"]

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

    # Filter by specific month
    if month:
        transactions = [t for t in transactions if (t.get("booking_date", "") or "").startswith(month)]

    total_entries = len(transactions)
    total_excess = sum(t.get("total_excess_discount", 0) or 0 for t in transactions)

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        with ui.column().classes("w-[240px] shrink-0 bg-white border-r border-gray-200 py-4 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"):
            sidebar()

        with ui.column().classes("flex-1 min-w-0 p-8 bg-[#F8F9FC] overflow-x-hidden"):
            with ui.row().classes("w-full items-center justify-between mb-6"):
                with ui.column().classes("gap-1"):
                    title_suffix = f" — {month_label_local(month)}" if month else " — All Time"
                    ui.label(f"{label}{title_suffix}").classes("text-2xl font-bold text-gray-900")

                    with ui.row().classes("items-center gap-2"):
                        ui.label(f"{total_entries} Total Records").classes("text-sm text-gray-500")
                        if total_excess > 0:
                            ui.label(f"₹{total_excess:,.0f} Excess").classes("text-sm font-bold text-red-500 bg-red-50 px-2 py-0.5 rounded")

                with (
                    ui.button(on_click=open_new_entry_dialog)
                    .classes("bg-[#E8402A] text-white font-bold px-6 py-2.5 rounded-lg shadow-md hover:bg-[#D4351F]")
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("mr-2")
                    ui.label("New Entry")

            with ui.card().classes("w-full p-0 overflow-hidden rounded-xl shadow-sm border-none"):
                # Pass the theme explicitly for a consistent look
                grid = render_table(transactions, stage=stage)

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
        with ui.column().classes("w-[240px] shrink-0 bg-white border-r border-gray-200 py-4 sticky top-[52px] h-[calc(100vh-52px)]"):
            sidebar()

        with ui.column().classes("flex-1 min-w-0 p-8 bg-[#F8F9FC] overflow-x-hidden"):
            with ui.row().classes("w-full items-center justify-between mb-6"):
                with ui.column().classes("gap-1"):
                    ui.label("Complaints Management").classes("text-2xl font-bold text-gray-900")
                    ui.label(f"{total_entries} Active Complaints").classes("text-sm text-gray-500")

                with (
                    ui.button(on_click=lambda: ui.navigate.to("/complaint-form"))
                    .classes("bg-[#E8402A] text-white font-bold px-6 py-2.5 rounded-lg shadow-md hover:bg-[#D4351F]")
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("mr-2")
                    ui.label("New Complaint")

            with ui.card().classes("w-full p-0 overflow-hidden rounded-xl shadow-sm border-none"):
                render_complaints_table(complaints)
