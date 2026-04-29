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

    # Build month map over ALL transactions (for sidebar + filter options)
    all_month_map: dict = defaultdict(list)
    for t in all_transactions:
        bd = t.get("booking_date", "")
        if bd and len(bd) >= 7:
            all_month_map[bd[:7]].append(t)
    sorted_months = sorted(all_month_map.keys(), reverse=True)
    
    # ── DASHBOARD LAYOUT ─────────────────────────────────────
    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # ── SIDEBAR ─────────────────────────────────────────
        with ui.column().classes(
            "w-[220px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"
        ):
            ui.label("Quick Nav").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
            )

            ui.link("📊 Dashboard", "/").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] no-underline"
            )
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📑 Complaints Table", "/complaints-table").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )

            ui.label("Month-wise MIS").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
            )

            if sorted_months:
                for ym in sorted_months:
                    txns_in_month = all_month_map[ym]
                    cnt = len(txns_in_month)
                    exc = sum(1 for t in txns_in_month if t.get("status") == "Excess")
                    lbl = month_label(ym)
                    badge_cls = (
                        "bg-[#FECDC8] text-[#C0392B]"
                        if exc > 0
                        else "bg-gray-100 text-gray-500"
                    )

                    with ui.link(target=f"/delivery-mis?month={ym}").classes(
                        "flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline w-full"
                    ):
                        ui.label(lbl)
                        ui.label(str(cnt)).classes(
                            f"text-[10px] font-bold px-2 py-0.5 rounded-full min-w-[22px] text-center {badge_cls}"
                        )
            else:
                ui.label("No data yet").classes("px-4 py-2 text-xs text-gray-400")

            ui.element("div").classes("h-[1px] bg-gray-100 mx-4 my-2")
            ui.label("Quick Actions").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
            )
            with ui.button(on_click=open_new_entry_dialog).classes(
                "flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            ):
                ui.icon("add").classes("text-primary text-lg text-weight-bold")
                ui.label("New Entry").classes("text-weight-bold pl-2")
            with ui.link(target="/complaint-form").classes(
                "flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            ):
                ui.icon("insert_drive_file").classes(
                    "text-primary text-lg text-weight-bold"
                )
                ui.label("Complaint Form").classes("text-weight-bold pl-2")
            
            with ui.link(target="settings").classes(
                "flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            ):
                ui.icon("settings").classes("text-primary text-lg text-weight-bold")
                ui.label("Settings").classes("text-weight-bold pl-2")

            sidebar()

        # ── MAIN CONTENT ─────────────────────────────────────
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            # ── Page header + month filter ────────────────────
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    ui.label("Dashboard").classes(
                        "text-[18px] font-bold text-gray-900 leading-none"
                    )
                    ui.label("Overview of all audit transactions").classes(
                        "text-[12px] text-gray-400"
                    )

                with ui.row().classes("items-center gap-3 shrink-0"):
                    month_options = {"": "All Months"} | {
                        ym: month_label(ym) for ym in sorted_months
                    }
                    month_select = (
                        ui.select(
                            options=month_options, value="", label="Filter by Month"
                        )
                        .classes("w-44")
                        .props("outlined dense")
                    )
                    with (
                        ui.button(on_click=open_new_entry_dialog)
                        .classes(
                            "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-[0_3px_10px_rgba(232,64,42,0.3)]"
                        )
                        .props("no-caps unelevated")
                    ):
                        ui.icon("add").classes("text-white text-lg text-weight-bold")
                        ui.label("New Entry").classes("text-weight-bold pl-2")

            # ── Dynamic content container (plain div, no extra padding) ──
            booking_content_area = ui.element("div").classes("w-full")
            delivery_content_area = ui.element("div").classes("w-full")

            def compute_analytics(txns: list) -> dict:
                """Compute all dashboard metrics from a transaction list."""
                total_entries = len(txns)
                total_discount = sum(
                    t.get("total_allowed_discount", 0) or 0 for t in txns
                )
                total_actual_discount = sum(
                    t.get("total_actual_discount", 0) or 0 for t in txns
                )
                total_excess = sum(t.get("total_excess_discount", 0) or 0 for t in txns)
                excess_cases = sum(1 for t in txns if t.get("status") == "Excess")
                ok_cases = total_entries - excess_cases
                compliance_pct = round(
                    (ok_cases / total_entries * 100) if total_entries else 100, 1
                )
                avg_discount = (
                    round(total_discount / total_entries) if total_entries else 0
                )
                avg_actual_discount = (
                    round(total_actual_discount / total_entries) if total_entries else 0
                )

                # Time series (month-on-month)
                t_month_map: dict = defaultdict(list)
                for t in txns:
                    bd = t.get("booking_date", "")
                    if bd and len(bd) >= 7:
                        t_month_map[bd[:7]].append(t)
                chrono = sorted(t_month_map.keys())
                ts_lbl = [month_label(ym) for ym in chrono]
                ts_disc = [
                    sum(
                        t.get("total_allowed_discount", 0) or 0 for t in t_month_map[ym]
                    )
                    for ym in chrono
                ]
                ts_exc = [
                    sum(t.get("total_excess_discount", 0) or 0 for t in t_month_map[ym])
                    for ym in chrono
                ]

                # Sales analytics
                model_sales: dict = defaultdict(int)
                model_discount: dict = defaultdict(int)
                model_excess: dict = defaultdict(int)
                variant_excess: dict = defaultdict(int)
                outlet_sales: dict = defaultdict(int)
                outlet_disc: dict = defaultdict(int)
                outlet_excess: dict = defaultdict(int)
                condition_cnt: dict = defaultdict(int)

                for t in txns:
                    model = (
                        t.get("car_name")
                        or t.get("car")
                        or (
                            t.get("variant_name", "").split(" ")[0]
                            if t.get("variant_name")
                            else "Unknown"
                        )
                    )
                    outlet = t.get("outlet_name") or t.get("outlet") or "Unknown"
                    vname = t.get("variant_name") or t.get("variant") or "Unknown"
                    actual_discount = t.get("total_actual_discount", 0) or 0
                    ex = t.get("total_excess_discount", 0) or 0
                    disc = t.get("total_allowed_discount", 0) or 0

                    model_sales[model] += 1
                    model_discount[model] += disc
                    if ex > 0:
                        model_excess[model] += ex
                        variant_excess[vname] += ex

                    outlet_sales[outlet] += 1
                    outlet_disc[outlet] += disc
                    outlet_excess[outlet] += ex

                    for k, v in (t.get("conditions", {}) or {}).items():
                        if v:
                            condition_cnt[k.replace("_", " ").title()] += 1

                top_excess_txns = sorted(
                    [t for t in txns if (t.get("total_excess_discount", 0) or 0) > 0],
                    key=lambda x: -(x.get("total_excess_discount", 0) or 0),
                )[:6]

                return dict(
                    total_entries=total_entries,
                    total_discount=total_discount,
                    total_actual_discount=total_actual_discount,
                    total_excess=total_excess,
                    excess_cases=excess_cases,
                    ok_cases=ok_cases,
                    compliance_pct=compliance_pct,
                    avg_discount=avg_discount,
                    avg_actual_discount=avg_actual_discount,
                    ts_labels=ts_lbl,
                    ts_discount=ts_disc,
                    ts_excess=ts_exc,
                    chrono_months=chrono,
                    top_model_sales=sorted(model_sales.items(), key=lambda x: -x[1])[
                        :8
                    ],
                    top_model_disc=sorted(model_discount.items(), key=lambda x: -x[1])[
                        :8
                    ],
                    top_model_excess=sorted(model_excess.items(), key=lambda x: -x[1])[
                        :8
                    ],
                    top_variants=sorted(variant_excess.items(), key=lambda x: -x[1])[
                        :8
                    ],
                    outlets_sorted_sales=sorted(
                        outlet_sales.items(), key=lambda x: -x[1]
                    )[:8],
                    outlets_sorted_disc=sorted(
                        outlet_disc.items(), key=lambda x: -x[1]
                    )[:8],
                    outlet_excess=outlet_excess,
                    outlet_sales=outlet_sales,
                    outlet_discount=outlet_disc,
                    sorted_conds=sorted(condition_cnt.items(), key=lambda x: -x[1]),
                    top_excess_txns=top_excess_txns,
                    sorted_months_local=sorted(t_month_map.keys(), reverse=True),
                    month_map_local=t_month_map,
                )

            def render_dashboard(all_txns: list) -> None:
                """Build the full dashboard UI splitting by booking vs delivery."""
                booking_txns = [t for t in all_txns if t.get("stage") == "booking"]
                delivery_txns = [t for t in all_txns if t.get("stage") == "delivery"]

                booking_analytics = compute_analytics(booking_txns)
                delivery_analytics = compute_analytics(delivery_txns)
                booking_content_area.clear()
                delivery_content_area.clear()

                with booking_content_area:
                    excess_color = (
                        "#EF4444"
                        if booking_analytics["total_excess"] > 0
                        else "#10B981"
                    )
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Bookings").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")
                        ui.link("View All Bookings", "/booking-mis").classes(
                            "text-[10px] text-primary font-bold uppercase no-underline hover:underline"
                        )

                    with ui.grid(columns=4).classes("w-full gap-4 mb-5"):
                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#6366F1] shadow-sm rounded-xl"
                        ):
                            ui.label("🚗").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Bookings").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(str(booking_analytics["total_entries"])).classes(
                                "text-[24px] font-bold text-gray-900 leading-none mb-1.5 mono"
                            )
                            with ui.row().classes("gap-1"):
                                ui.label(f"{booking_analytics['ok_cases']} OK").classes(
                                    "bg-indigo-50 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded"
                                )
                                ui.label(
                                    f"{booking_analytics['excess_cases']} Excess"
                                ).classes(
                                    "bg-red-50 text-red-700 text-[10px] font-bold px-1.5 py-0.5 rounded"
                                )

                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"
                        ):
                            ui.label("💸").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Discount Given").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(
                                f"₹{booking_analytics['total_actual_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{booking_analytics['avg_actual_discount']:,.0f} / transaction"
                            ).classes("text-[14px] text-gray-600")

                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"
                        ):
                            ui.label("💸").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Allowable Discount").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(
                                f"₹{booking_analytics['total_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{booking_analytics['avg_discount']:,.0f} / transaction"
                            ).classes("text-[14px] text-gray-600")

                        with ui.card().classes(
                            f"relative overflow-hidden p-4.5 px-5 bg-white border-t-4 shadow-sm rounded-xl border-[{excess_color}]"
                        ):
                            ui.label("⚠️").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Excess Discount").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(
                                f"₹{booking_analytics['total_excess']:,.0f}"
                            ).classes(
                                f"text-[24px] font-bold leading-none mb-1.5 mono text-[{excess_color}]"
                            )
                            ui.label(
                                "⚠ Requires attention"
                                if booking_analytics["total_excess"] > 0
                                else "✓ All within limits"
                            ).classes(
                                f"text-[11px] font-medium {'text-red-500' if booking_analytics['total_excess'] > 0 else 'text-green-500'}"
                            )

                with delivery_content_area:
                    excess_color = (
                        "#EF4444"
                        if delivery_analytics["total_excess"] > 0
                        else "#10B981"
                    )
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Deliveries").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")
                        ui.link("View All Deliveries", "/delivery-mis").classes(
                            "text-[10px] text-primary font-bold uppercase no-underline hover:underline"
                        )
                    with ui.grid(columns=4).classes("w-full gap-4 mb-5"):
                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#6366F1] shadow-sm rounded-xl"
                        ):
                            ui.label("🚗").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Deliveries").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(str(delivery_analytics["total_entries"])).classes(
                                "text-[24px] font-bold text-gray-900 leading-none mb-1.5 mono"
                            )
                            with ui.row().classes("gap-1"):
                                ui.label(
                                    f"{delivery_analytics['ok_cases']} OK"
                                ).classes(
                                    "bg-indigo-50 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded"
                                )
                                ui.label(
                                    f"{delivery_analytics['excess_cases']} Excess"
                                ).classes(
                                    "bg-red-50 text-red-700 text-[10px] font-bold px-1.5 py-0.5 rounded"
                                )
                        
                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"
                        ):
                            ui.label("💸").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Discount Given").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(
                                f"₹{delivery_analytics['total_actual_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{delivery_analytics['avg_actual_discount']:,.0f} / transaction"
                            ).classes("text-[14px] text-gray-600")

                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"
                        ):
                            ui.label("💸").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Allowable Discount").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(
                                f"₹{delivery_analytics['total_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{delivery_analytics['avg_discount']:,.0f} / transaction"
                            ).classes("text-[14px] text-gray-600")

                        with ui.card().classes(
                            f"relative overflow-hidden p-4.5 px-5 bg-white border-t-4 shadow-sm rounded-xl border-[{excess_color}]"
                        ):
                            ui.label("⚠️").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Excess Discount").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(
                                f"₹{delivery_analytics['total_excess']:,.0f}"
                            ).classes(
                                f"text-[24px] font-bold leading-none mb-1.5 mono text-[{excess_color}]"
                            )
                            ui.label(
                                "⚠ Requires attention"
                                if delivery_analytics["total_excess"] > 0
                                else "✓ All within limits"
                            ).classes(
                                f"text-[11px] font-medium {'text-red-500' if delivery_analytics['total_excess'] > 0 else 'text-green-500'}"
                            )

                    # ── SALES ANALYTICS ────────────────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Sales Analytics").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Units Sold by Car Model").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )
                            render_bar_chart(
                                delivery_analytics["top_model_sales"],
                                color="#6366F1",
                                value_fmt="N",
                                empty_msg="No model data",
                                height=220,
                            )

                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Discount by Car Model").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )
                            render_bar_chart(
                                delivery_analytics["top_model_disc"],
                                color="#10B981",
                                value_fmt="K",
                                empty_msg="No model data",
                                height=220,
                            )

                    # Sales conditions (full-width, split 2-col)
                    if delivery_analytics["sorted_conds"]:
                        items_list = list(delivery_analytics["sorted_conds"])
                        half = (len(items_list) + 1) // 2
                        left_items = items_list[:half]
                        right_items = items_list[half:]
                        with ui.card().classes("w-full shadow-sm rounded-xl p-5 mb-4"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Sales Conditions Breakdown").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("transactions per flag").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            with ui.grid(columns=2).classes("w-full gap-5"):
                                render_bar_chart(
                                    left_items,
                                    color="#8B5CF6",
                                    value_fmt="N",
                                    height=max(120, len(left_items) * 36),
                                )
                                if right_items:
                                    render_bar_chart(
                                        right_items,
                                        color="#8B5CF6",
                                        value_fmt="N",
                                        height=max(120, len(right_items) * 36),
                                    )

                    # ── OUTLET ANALYTICS ───────────────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Outlet Analytics").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Sales by Outlet").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )
                            render_bar_chart(
                                delivery_analytics["outlets_sorted_sales"],
                                color="#0EA5E9",
                                value_fmt="N",
                                empty_msg="No outlet data",
                                height=220,
                            )

                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Discount by Outlet").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )
                            render_bar_chart(
                                delivery_analytics["outlets_sorted_disc"],
                                color="#F59E0B",
                                value_fmt="K",
                                empty_msg="No outlet data",
                                height=220,
                            )

                    # Outlet excess mini-table
                    if delivery_analytics["outlet_excess"]:
                        sorted_oe = sorted(
                            delivery_analytics["outlet_excess"].items(),
                            key=lambda x: -x[1],
                        )
                        with ui.card().classes("w-full shadow-sm rounded-xl p-5 mb-4"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Excess Discount by Outlet").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("excess rate = excess ÷ discount").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )

                            with ui.grid(columns="1fr 90px 70px 56px").classes(
                                "w-full gap-2 mb-0.5 pb-1.5 border-b-2 border-gray-100"
                            ):
                                ui.label("Outlet").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400"
                                )
                                ui.label("Excess").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400 text-right"
                                )
                                ui.label("Sales").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400 text-right"
                                )
                                ui.label("Rate").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400 text-right"
                                )

                            for o_name, o_exc in sorted_oe[:8]:
                                sales_n = delivery_analytics["outlet_sales"].get(
                                    o_name, 0
                                )
                                disc_n = delivery_analytics["outlet_discount"].get(
                                    o_name, 0
                                )
                                exc_rt = round(o_exc / disc_n * 100, 1) if disc_n else 0
                                rate_color = (
                                    "text-red-600" if exc_rt > 20 else "text-gray-400"
                                )
                                with ui.row().classes(
                                    "w-full grid grid-cols-[1fr_90px_70px_56px] gap-2 py-1.5 border-b border-gray-50 last:border-b-0 hover:bg-gray-50/50 cursor-pointer transition-colors"
                                ):
                                    ui.label(o_name).classes(
                                        "text-[12px] font-medium text-gray-700 truncate"
                                    )
                                    ui.label(f"₹{o_exc / 1000:.1f}K").classes(
                                        "text-[12px] font-bold text-red-600 text-right mono"
                                    )
                                    ui.label(str(sales_n)).classes(
                                        "text-[12px] text-gray-500 text-right mono"
                                    )
                                    ui.label(f"{exc_rt}%").classes(
                                        f"text-[12px] font-bold text-right mono {rate_color}"
                                    )

                    # ── EXCESS DISCOUNT ANALYSIS ───────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Excess Discount Analysis").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Excess by Car Model").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )
                            render_bar_chart(
                                delivery_analytics["top_model_excess"],
                                color="#F97316",
                                value_fmt="K",
                                empty_msg="No excess discounts",
                                height=220,
                            )

                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Excess by Variant").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )
                            render_bar_chart(
                                delivery_analytics["top_variants"],
                                color="#EF4444",
                                value_fmt="K",
                                empty_msg="No excess discounts",
                                height=220,
                            )
                    # ── EXCESS ANALYSIS ────────────────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Excess Analysis").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        # Top excess transactions list
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Top Excess Transactions").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )

                            if delivery_analytics["top_excess_txns"]:
                                for t in delivery_analytics["top_excess_txns"]:
                                    name = (
                                        t.get("customer_name")
                                        or t.get("customer")
                                        or "—"
                                    )
                                    ex = t.get("total_excess_discount", 0) or 0
                                    var = (
                                        t.get("variant_name") or t.get("variant") or "—"
                                    )
                                    txid = t.get("id", "")
                                    bd = t.get("booking_date", "—")
                                    with (
                                        ui.row()
                                        .classes(
                                            "w-full justify-between items-center py-2.5 border-b border-gray-50 last:border-b-0 hover:bg-gray-50/50 cursor-pointer transition-colors"
                                        )
                                        .on(
                                            "click",
                                            lambda _, tid=txid: ui.navigate.to(
                                                f"/form?transaction_id={tid}"
                                            ),
                                        )
                                    ):
                                        with ui.column().classes("gap-0"):
                                            ui.label(name).classes(
                                                "text-[12.5px] font-medium text-gray-700"
                                            )
                                            ui.label(f"{var} · {bd}").classes(
                                                "text-[10.5px] text-gray-400"
                                            )
                                        ui.label(f"₹{ex:,.0f}").classes(
                                            "text-[13px] font-bold text-red-600 mono"
                                        )
                            else:
                                ui.label("No excess transactions").classes(
                                    "w-full text-center py-8 text-gray-400 text-[13px]"
                                )

                        # Month-wise summary
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            ui.label("Month-wise Summary").classes(
                                "text-[12.5px] font-semibold text-gray-900 mb-3"
                            )

                            with ui.grid(columns="1fr 60px 80px 80px").classes(
                                "w-full gap-2 mb-2 pb-1 border-b border-gray-100"
                            ):
                                ui.label("Month").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400"
                                )
                                ui.label("Txns").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400 text-right"
                                )
                                ui.label("Disc").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400 text-right"
                                )
                                ui.label("Excess").classes(
                                    "text-[9px] font-bold tracking-[0.8px] uppercase text-gray-400 text-right"
                                )

                            if delivery_analytics["sorted_months_local"]:
                                for ym in delivery_analytics["sorted_months_local"][
                                    :10
                                ]:
                                    txns_m = delivery_analytics["month_map_local"][ym]
                                    cnt_m = len(txns_m)
                                    disc_m = sum(
                                        t.get("total_allowed_discount", 0) or 0
                                        for t in txns_m
                                    )
                                    exc_m = sum(
                                        t.get("total_excess_discount", 0) or 0
                                        for t in txns_m
                                    )
                                    lbl_m = month_label(ym)
                                    ec = (
                                        "text-red-600"
                                        if exc_m > 0
                                        else "text-green-600"
                                    )

                                    with (
                                        ui.row()
                                        .classes(
                                            "w-full grid grid-cols-[1fr_60px_80px_80px] gap-2 py-1.5 border-b border-gray-50 last:border-b-0 hover:bg-gray-50/50 cursor-pointer"
                                        )
                                        .on(
                                            "click",
                                            lambda _, y=ym: ui.navigate.to(
                                                f"/delivery-mis?month={y}"
                                            ),
                                        )
                                    ):
                                        ui.label(lbl_m).classes(
                                            "text-[12px] font-medium text-gray-700"
                                        )
                                        ui.label(str(cnt_m)).classes(
                                            "text-[12px] text-gray-500 text-right mono"
                                        )
                                        ui.label(f"₹{disc_m / 1000:.0f}K").classes(
                                            "text-[12px] text-gray-500 text-right mono"
                                        )
                                        ui.label(f"₹{exc_m / 1000:.0f}K").classes(
                                            f"text-[12px] font-bold text-right mono {ec}"
                                        )
                            else:
                                ui.label("No data yet").classes(
                                    "w-full text-center py-8 text-gray-400 text-[13px]"
                                )

            # ── Initial render with all data ─────────────────
            render_dashboard(all_transactions)

            # ── Wire month filter ─────────────────────────────
            def on_month_change(e):
                selected = e.value or ""
                filtered = (
                    [
                        t
                        for t in all_transactions
                        if (t.get("booking_date", "") or "").startswith(selected)
                    ]
                    if selected
                    else all_transactions
                )
                render_dashboard(filtered)

            month_select.on_value_change(on_month_change)

