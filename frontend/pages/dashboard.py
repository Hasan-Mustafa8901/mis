import calendar
from collections import defaultdict
from datetime import date
from nicegui import ui

from auth.auth import protected_page
from components.layout import render_topbar, sidebar
from components.dialogs import open_new_entry_dialog
from services.api import api_get
from components.charts import render_bar_chart

@ui.page("/")
@protected_page
async def dashboard_page() -> None:
    render_topbar("Dashboard")

    # ── Fetch all transactions ─────────────────────────────
    try:
        all_transactions: list = await api_get("/transactions")
    except Exception:
        all_transactions = []

    # ── Month helpers ──────────────────────────────────────
    def month_label(ym: str) -> str:
        try:
            y, m = ym.split("-")
            return f"{calendar.month_abbr[int(m)]} '{y[2:]}"
        except Exception:
            return ym

    all_month_map: dict = defaultdict(list)
    for txn in all_transactions:
        booking_date = txn.get("booking_date", "")
        if booking_date and len(booking_date) >= 7:
            all_month_map[booking_date[:7]].append(txn)
    sorted_months = sorted(all_month_map.keys(), reverse=True)

    # ── DASHBOARD LAYOUT ─────────────────────────────────────
    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # ── SIDEBAR ─────────────────────────────────────────
        with ui.column().classes(
            "w-[240px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"
        ):
            sidebar()

        # ── MAIN CONTENT ─────────────────────────────────────
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden bg-[#F8F9FC]"):
            # ── Page header + month filter ────────────────────
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    ui.label("Audit Dashboard").classes("text-[18px] font-bold text-gray-900 leading-none")
                    ui.label("Comprehensive overview of bookings and deliveries").classes("text-[12px] text-gray-400")

                with ui.row().classes("items-center gap-3 shrink-0"):
                    month_options = {"": "All Time"} | {ym: month_label(ym) for ym in sorted_months}
                    month_select = ui.select(options=month_options, value="", label="Filter by Month").classes("w-44").props("outlined dense")

                    with ui.button(on_click=open_new_entry_dialog).classes("bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm").props("no-caps unelevated"):
                        ui.icon("add").classes("text-white text-lg font-bold mr-2")
                        ui.label("New Entry")

            # ── Dynamic content containers ──
            booking_content_area = ui.element("div").classes("w-full")
            delivery_content_area = ui.element("div").classes("w-full")

            def compute_analytics(txns: list) -> dict:
                total_entries = len(txns)
                total_discount = sum(t.get("total_allowed_discount", 0) or 0 for t in txns)
                total_actual_discount = sum(t.get("total_actual_discount", 0) or 0 for t in txns)
                total_excess = sum(t.get("total_excess_discount", 0) or 0 for t in txns)
                excess_cases = sum(1 for t in txns if t.get("status") == "Excess")
                ok_cases = total_entries - excess_cases

                avg_discount = round(total_discount / total_entries) if total_entries else 0
                avg_actual_discount = round(total_actual_discount / total_entries) if total_entries else 0

                model_sales, model_discount, model_excess, variant_excess = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)
                outlet_sales, outlet_disc, outlet_excess, condition_cnt = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)
                t_month_map = defaultdict(list)

                for t in txns:
                    model = t.get("car_name") or t.get("car") or "Unknown"
                    outlet = t.get("outlet_name") or t.get("outlet") or "Unknown"
                    vname = t.get("variant_name") or t.get("variant") or "Unknown"
                    actual_discount = t.get("total_actual_discount", 0) or 0
                    ex = t.get("total_excess_discount", 0) or 0
                    disc = t.get("total_allowed_discount", 0) or 0
                    bd = t.get("booking_date", "")

                    if bd and len(bd) >= 7: t_month_map[bd[:7]].append(t)

                    model_sales[model] += 1
                    model_discount[model] += disc
                    if ex > 0:
                        model_excess[model] += ex
                        variant_excess[vname] += ex
                    outlet_sales[outlet] += 1
                    outlet_disc[outlet] += disc
                    outlet_excess[outlet] += ex
                    for k, v in (t.get("conditions", {}) or {}).items():
                        if v: condition_cnt[k.replace("_", " ").title()] += 1

                top_excess_txns = sorted([t for t in txns if (t.get("total_excess_discount", 0) or 0) > 0], key=lambda x: -(x.get("total_excess_discount", 0) or 0))[:6]

                return dict(
                    total_entries=total_entries, total_discount=total_discount, total_actual_discount=total_actual_discount,
                    total_excess=total_excess, excess_cases=excess_cases, ok_cases=ok_cases,
                    avg_discount=avg_discount, avg_actual_discount=avg_actual_discount,
                    top_model_sales=sorted(model_sales.items(), key=lambda x: -x[1])[:8],
                    top_model_disc=sorted(model_discount.items(), key=lambda x: -x[1])[:8],
                    top_model_excess=sorted(model_excess.items(), key=lambda x: -x[1])[:8],
                    top_variants=sorted(variant_excess.items(), key=lambda x: -x[1])[:8],
                    outlets_sorted_sales=sorted(outlet_sales.items(), key=lambda x: -x[1])[:8],
                    outlets_sorted_disc=sorted(outlet_disc.items(), key=lambda x: -x[1])[:8],
                    outlet_excess=outlet_excess, outlet_sales=outlet_sales, outlet_discount=outlet_disc,
                    sorted_conds=sorted(condition_cnt.items(), key=lambda x: -x[1]),
                    top_excess_txns=top_excess_txns, sorted_months_local=sorted(t_month_map.keys(), reverse=True),
                    month_map_local=t_month_map,
                )

            def render_section_header(title: str, link_label: str, link_target: str):
                with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                    ui.label(title).classes("text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap")
                    ui.separator().classes("flex-1")
                    ui.link(link_label, link_target).classes("text-[10px] text-primary font-bold uppercase no-underline hover:underline")

            def render_kpi_cards(analytics: dict, label: str):
                excess_color = "#EF4444" if analytics["total_excess"] > 0 else "#10B981"
                with ui.grid(columns=4).classes("w-full gap-4 mb-5"):
                    # Card 1: Total
                    with ui.card().classes("relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#6366F1] shadow-sm rounded-xl"):
                        ui.label("🚗").classes("absolute right-4 top-4 text-[30px] opacity-10 select-none")
                        ui.label(f"Total {label}").classes("text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5")
                        ui.label(str(analytics["total_entries"])).classes("text-[24px] font-bold text-gray-900 leading-none mb-1.5 mono")
                        with ui.row().classes("gap-1"):
                            ui.label(f"{analytics['ok_cases']} OK").classes("bg-indigo-50 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded")
                            ui.label(f"{analytics['excess_cases']} Excess").classes("bg-red-50 text-red-700 text-[10px] font-bold px-1.5 py-0.5 rounded")
                    # Card 2: Actual Discount
                    with ui.card().classes("relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"):
                        ui.label("💸").classes("absolute right-4 top-4 text-[30px] opacity-10 select-none")
                        ui.label("Discount Given").classes("text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5")
                        ui.label(f"₹{analytics['total_actual_discount']:,.0f}").classes("text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono")
                        ui.label(f"Avg ₹{analytics['avg_actual_discount']:,.0f} / txn").classes("text-[12px] text-gray-500")
                    # Card 3: Allowable Discount
                    with ui.card().classes("relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#6366F1] shadow-sm rounded-xl"):
                        ui.label("⚖️").classes("absolute right-4 top-4 text-[30px] opacity-10 select-none")
                        ui.label("Allowable Limit").classes("text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5")
                        ui.label(f"₹{analytics['total_discount']:,.0f}").classes("text-[24px] font-bold text-indigo-600 leading-none mb-1.5 mono")
                        ui.label(f"Avg ₹{analytics['avg_discount']:,.0f} / txn").classes("text-[12px] text-gray-500")
                    # Card 4: Excess
                    with ui.card().classes(f"relative overflow-hidden p-4.5 px-5 bg-white border-t-4 shadow-sm rounded-xl border-[{excess_color}]"):
                        ui.label("⚠️").classes("absolute right-4 top-4 text-[30px] opacity-10 select-none")
                        ui.label("Total Excess").classes("text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5")
                        ui.label(f"₹{analytics['total_excess']:,.0f}").classes(f"text-[24px] font-bold leading-none mb-1.5 mono text-[{excess_color}]")
                        ui.label("Requires attention" if analytics["total_excess"] > 0 else "Within limits").classes(f"text-[11px] font-bold {'text-red-500' if analytics['total_excess'] > 0 else 'text-green-500'}")

            def render_dashboard(all_txns: list) -> None:
                booking_txns = [t for t in all_txns if t.get("stage") == "booking"]
                delivery_txns = [t for t in all_txns if t.get("stage") == "delivery"]
                b_ana = compute_analytics(booking_txns)
                d_ana = compute_analytics(delivery_txns)

                booking_content_area.clear()
                delivery_content_area.clear()

                with booking_content_area:
                    render_section_header("Bookings Overview", "View Booking MIS", "/booking-mis")
                    render_kpi_cards(b_ana, "Bookings")

                with delivery_content_area:
                    render_section_header("Deliveries Overview", "View Delivery MIS", "/delivery-mis")
                    render_kpi_cards(d_ana, "Deliveries")

                    # Sales Analytics
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Sales & Discount Analytics").classes("text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap")
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Units Sold by Model").classes("text-[12.5px] font-semibold mb-3")
                            render_bar_chart(d_ana["top_model_sales"], color="#6366F1", value_fmt="N", height=220)
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Discount by Model").classes("text-[12.5px] font-semibold mb-3")
                            render_bar_chart(d_ana["top_model_disc"], color="#10B981", value_fmt="K", height=220)

                    # Conditions Breakdown
                    if d_ana["sorted_conds"]:
                        with ui.card().classes("w-full shadow-sm rounded-xl p-5 mb-4"):
                            ui.label("Sales Conditions Breakdown").classes("text-[12.5px] font-semibold mb-3 pb-2 border-b border-gray-50")
                            items = d_ana["sorted_conds"]
                            half = (len(items) + 1) // 2
                            with ui.grid(columns=2).classes("w-full gap-5"):
                                render_bar_chart(items[:half], color="#8B5CF6", value_fmt="N", height=max(120, half * 36))
                                if items[half:]: render_bar_chart(items[half:], color="#8B5CF6", value_fmt="N", height=max(120, (len(items)-half) * 36))

                    # Outlet Analytics
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Outlet Performance").classes("text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap")
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Sales by Outlet").classes("text-[12.5px] font-semibold mb-3")
                            render_bar_chart(d_ana["outlets_sorted_sales"], color="#0EA5E9", value_fmt="N", height=220)
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Discount by Outlet").classes("text-[12.5px] font-semibold mb-3")
                            render_bar_chart(d_ana["outlets_sorted_disc"], color="#F59E0B", value_fmt="K", height=220)

                    # Outlet Excess Table
                    if d_ana["outlet_excess"]:
                        with ui.card().classes("w-full shadow-sm rounded-xl p-5 mb-4"):
                            ui.label("Excess Discount by Outlet").classes("text-[12.5px] font-semibold mb-3 pb-2 border-b border-gray-100")
                            with ui.grid(columns="1fr 90px 70px 56px").classes("w-full gap-2 pb-1.5 border-b-2 border-gray-50"):
                                for h in ["Outlet", "Excess", "Sales", "Rate"]:
                                    ui.label(h).classes("text-[9px] font-bold uppercase text-gray-400" + (" text-right" if h != "Outlet" else ""))
                            for o_name, o_exc in sorted(d_ana["outlet_excess"].items(), key=lambda x: -x[1])[:8]:
                                sales_n = d_ana["outlet_sales"].get(o_name, 0)
                                disc_n = d_ana["outlet_discount"].get(o_name, 0)
                                exc_rt = round(o_exc / disc_n * 100, 1) if disc_n else 0
                                with ui.row().classes("w-full grid grid-cols-[1fr_90px_70px_56px] gap-2 py-2 border-b border-gray-50 last:border-b-0 hover:bg-gray-50 transition-colors"):
                                    ui.label(o_name).classes("text-[12px] font-medium text-gray-700 truncate")
                                    ui.label(f"₹{o_exc / 1000:.1f}K").classes("text-[12px] font-bold text-red-600 text-right mono")
                                    ui.label(str(sales_n)).classes("text-[12px] text-gray-500 text-right mono")
                                    ui.label(f"{exc_rt}%").classes(f"text-[12px] font-bold text-right mono {'text-red-600' if exc_rt > 20 else 'text-gray-400'}")

                    # Excess Analysis
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Excess Discount Drill-down").classes("text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap")
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Top Excess Deliveries").classes("text-[12.5px] font-semibold mb-3 pb-2 border-b border-gray-50")
                            if d_ana["top_excess_txns"]:
                                for t in d_ana["top_excess_txns"]:
                                    with ui.row().classes("w-full justify-between items-center py-2 border-b border-gray-50 last:border-b-0 cursor-pointer").on("click", lambda _, tid=t.get("id"): ui.navigate.to(f"/form?transaction_id={tid}")):
                                        with ui.column().classes("gap-0"):
                                            ui.label(t.get("customer_name") or "—").classes("text-[12.5px] font-medium text-gray-700")
                                            ui.label(f"{t.get('variant_name') or '—'} · {t.get('booking_date','—')}").classes("text-[10.5px] text-gray-400")
                                        ui.label(f"₹{t.get('total_excess_discount', 0):,.0f}").classes("text-[13px] font-bold text-red-600 mono")
                            else: ui.label("No excess transactions").classes("w-full text-center py-8 text-gray-400 text-[13px]")

                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Month-wise Summary").classes("text-[12.5px] font-semibold mb-3 pb-2 border-b border-gray-50")
                            with ui.grid(columns="1fr 60px 80px 80px").classes("w-full gap-2 pb-1 border-b border-gray-50"):
                                for h in ["Month", "Txns", "Disc", "Excess"]:
                                    ui.label(h).classes("text-[9px] font-bold uppercase text-gray-400" + (" text-right" if h != "Month" else ""))
                            for ym in d_ana["sorted_months_local"][:10]:
                                txns_m = d_ana["month_map_local"][ym]
                                disc_m = sum(t.get("total_allowed_discount", 0) or 0 for t in txns_m)
                                exc_m = sum(t.get("total_excess_discount", 0) or 0 for t in txns_m)
                                with ui.row().classes("w-full grid grid-cols-[1fr_60px_80px_80px] gap-2 py-2 border-b border-gray-50 last:border-b-0 cursor-pointer").on("click", lambda _, y=ym: ui.navigate.to(f"/delivery-mis?month={y}")):
                                    ui.label(month_label(ym)).classes("text-[12px] font-medium text-gray-700")
                                    ui.label(str(len(txns_m))).classes("text-[12px] text-gray-500 text-right mono")
                                    ui.label(f"₹{disc_m / 1000:.0f}K").classes("text-[12px] text-gray-500 text-right mono")
                                    ui.label(f"₹{exc_m / 1000:.1f}K").classes(f"text-[12px] font-bold text-right mono {'text-red-600' if exc_m > 0 else 'text-green-600'}")

            # ── Initial render with all data ─────────────────
            render_dashboard(all_transactions)

            # ── Month Filter ──
            month_select.on_value_change(lambda e: render_dashboard([t for t in all_transactions if (t.get("booking_date", "") or "").startswith(e.value)] if e.value else all_transactions))
