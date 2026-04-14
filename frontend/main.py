"""
Automobile Sales Audit MIS — NiceGUI Frontend  (v3)
Two-page architecture:
  /      → Dashboard + Persistent MIS Transaction Table
  /form  → Data Entry Form (New + Edit mode)

Backend: FastAPI at http://localhost:8000
"""

import re
import json
import httpx
from datetime import date
from collections import defaultdict
import calendar
from nicegui import ui, app


# ══════════════════════════════════════════════════════════════
# CONFIG & SHARED CONSTANTS
# ══════════════════════════════════════════════════════════════
BASE_URL = "http://localhost:8000"

CONDITION_KEYS = [
    ("exchange", "Exchange"),
    ("corporate", "Corporate"),
    ("govt_employee", "Govt Employee"),
    ("scrap", "Scrap"),
    ("upgrade", "Upgrade"),
    ("self_insurance", "Self Insurance"),
    ("tr_case", "TR Case"),
]

DELIVERY_CHECK_KEYS = [
    ("customer_ledger", "Customer Ledger"),
    ("tax_invoice", "Tax Invoice"),
    ("accessories_indent", "Accessories Indent"),
    ("insurance", "Insurance"),
    ("rto", "RTO"),
    ("finance", "Finance"),
    ("evaluation_certificate", "Evaluation Certificate"),
]

# ══════════════════════════════════════════════════════════════
# SHARED CSS  (injected on both pages)
# ══════════════════════════════════════════════════════════════
HEAD_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  body, .q-page {
    font-family: 'Inter', sans-serif !important;
    background: #F0F2F8 !important;
  }
  .mono { font-family: 'JetBrains Mono', monospace !important; }
  
  /* AG Grid Overrides */
  .ag-theme-alpine {
    --ag-font-family: 'Inter', sans-serif;
    --ag-header-background-color: #F8F9FC;
    --ag-odd-row-background-color: #FAFBFF;
  }
  
  /* Custom Scrollbar */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: #F0F2F8; }
  ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }
</style>
"""

ui.add_head_html(
    """
<style>
.sticky-col {
    position: sticky;
    left: 0;
    background: white;
    z-index: 1;
}
</style>
""",
    shared=True,
)


# ══════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════
async def api_get(path: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()


async def api_post(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()


async def api_post_file(path: str, file, data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}{path}",
            files={"file": (file.name, await file.content.read())},
            data=data,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()


async def api_put(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.put(f"{BASE_URL}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()


# ══════════════════════════════════════════════════════════════
# SHARED BOOTSTRAP FETCH
# ══════════════════════════════════════════════════════════════
async def fetch_reference_data() -> dict:
    """
    Fetch all static reference data needed by the form.
    Returns a dict with keys: cars, components, outlets, executives
    """
    result = {}
    for key, path, fallback in [
        ("cars", "/cars", []),
        ("components", "/components", []),
        ("outlets", "/outlets", [{"id": 1, "name": "Main Outlet"}]),
        ("executives", "/sales-executives", [{"id": 1, "name": "Default SE"}]),
        ("accessories", "/accessories", []),
    ]:
        try:
            result[key] = await api_get(path)
        except Exception:
            result[key] = fallback

    return result


# ══════════════════════════════════════════════════════════════
# GLOBAL WIDGETS & INP HELPER
# ══════════════════════════════════════════════════════════════
def format_num_inr(num_val):
    """Format float into standard accounting formatting, e.g. 1,000.00"""
    return f"{float(num_val):,.2f}"


def get_eval_math(val_str):
    import re

    val_clean = str(val_str).replace(",", "").strip()
    if not val_clean:
        return None
    if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", val_clean):
        return eval(val_clean)
    return None


def parsed_val(ui_input_element) -> float | int:
    """Safe evaluation helper to get the numeric underlying float value from accounting_input or ui.number"""
    if not ui_input_element:
        return 0
    v = getattr(ui_input_element, "value", None)
    if not v:
        return 0
    try:
        if isinstance(v, (int, float)):
            return float(v)
        v_str = str(v).replace(",", "").strip()
        import re

        if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
            res = float(eval(v_str))
            return int(res) if res.is_integer() else res
        return float(v_str) if "." in v_str else int(v_str)
    except Exception:
        return 0


def accounting_input(
    label_text: str, placeholder: str = "", container_classes: str = "w-full"
) -> ui.input:
    with ui.column().classes(f"gap-0 {container_classes} mb-1"):
        inp = (
            ui.input(label=label_text, placeholder=placeholder)
            .props("outlined dense")
            .classes("w-full")
        )
        hint = ui.label("").classes(
            "text-[11px] text-green-600 font-bold ml-1 h-3 -mt-2"
        )

    def handle_eval(e):
        val = e.value
        if not val:
            hint.set_text("")
            return
        try:
            res = get_eval_math(val)
            if res is not None:
                res_str = format_num_inr(res)
                val_clean = str(val).replace(",", "").strip()
                if val_clean != str(res) and not val_clean.replace(".", "").isdigit():
                    hint.set_text(f"= {res_str}")
                else:
                    hint.set_text("")
                hint.classes(replace="text-red-500", add="text-green-600")
                return
        except Exception:
            pass
        hint.set_text("Invalid math")
        hint.classes(replace="text-green-600", add="text-red-500")

    def handle_blur(e=None):
        if not inp.value:
            return
        try:
            res = get_eval_math(inp.value)
            if res is not None:
                inp.set_value(format_num_inr(res))
                hint.set_text("")
        except Exception:
            pass

    inp.on_value_change(handle_eval)
    inp.on("blur", handle_blur)
    inp.on("keyup.enter", handle_blur)
    return inp


# ══════════════════════════════════════════════════════════════
# TOPBAR  (shared component for both pages)
# ══════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════
# MIS TABLE RENDERING & HELPER METHODS
# ══════════════════════════════════════════════════════════════
def build_ordered_columns(row: dict):
    """
    Build ordered columns for the MIS table.
    """
    keys = list(row.keys())

    def pick(prefix):
        return [k for k in keys if k.startswith(prefix)]

    #  GROUPS (based on your backend naming)
    ordered = []

    # 1. Core info
    ordered += [
        "id",
        "customer_name",
        "mobile_number",
        "variant_name",
        "booking_date",
    ]

    # 2. Price components
    ordered += pick("Ex ") + pick("Insurance") + pick("Registration")

    # 3. Discount components
    ordered += [k for k in keys if "_actual" in k and "Discount" in k]

    # 4. Allowed + diff (keep near actual)
    # ordered += [k for k in keys if "_allowed" in k]
    # ordered += [k for k in keys if "_diff" in k]
    # ordered += [k for k in keys if "net_" in k]

    # 5. Conditions
    ordered += pick("cond_")

    # 6. Accessories / finance / exchange
    ordered += pick("accessories_")
    ordered += pick("finance_")
    ordered += pick("exchange_")

    # 7. Checklist
    ordered += pick("checklist_")

    # 8. Audit
    ordered += pick("audit_")

    # 9. Totals
    ordered += [
        "net_receivable",
        "total_received",
        "balance_amount",
        "total_actual_discount",
        "total_allowed_discount",
        "total_excess_discount",
        "status",
    ]

    # remove duplicates + preserve order
    seen = set()
    ordered = [x for x in ordered if not (x in seen or seen.add(x))]

    return ordered


def clear_label(column_name: str):
    """
    Cleans up column names for display.
    """
    return (
        column_name.replace("_", " ")
        .replace("actual", "(Actual)")
        .replace("allowed", "(Allowed)")
        .replace("diff", "(Diff)")
        .title()
    )


def render_table(transactions):
    """
    Renders the MIS transaction table using AG Grid (ui.aggrid).
    NiceGUI aggrid notes:
    - JS expressions in column defs must use the ':field' colon-prefix syntax
    - rowData is passed directly; no 'function' dict wrappers needed
    - cellClicked event args['data'] holds the row dict
    """
    if not transactions:
        with ui.card().classes("w-full").style("padding:48px;text-align:center"):
            ui.label("📭").style("font-size:36px")
            ui.label("No transactions yet").style(
                "font-size:14px;font-weight:500;color:#6B7280;margin-top:8px"
            )
            ui.label("Click 'New Entry' to add the first record.").style(
                "font-size:12px;color:#9CA3AF;margin-top:4px"
            )
        return

    ordered_keys = build_ordered_columns(transactions[0])

    NUMERIC_KEYS = {
        k
        for k in ordered_keys
        if any(
            tok in k
            for tok in (
                "_actual",
                # "_allowed",
                # "_diff",
                "total_",
                "price",
                "amount",
                "discount",
                "excess",
                "payment",
                "invoice_",
                "net_",
            )
        )
    }
    pin_cols = {"id", "customer_name", "mobile_number", "variant_name", "booking_date"}

    # Define custom widths for specific columns (optional)
    # Any column not defined here will fall back to `minWidth` from defaultColDef.
    CUSTOM_WIDTHS = {
        "id": 10,
        "customer_name": 100,
        "mobile_number": 100,
        "variant_name": 100,
        "booking_date": 100,
    }

    col_defs = []
    for key in ordered_keys:
        is_num = key in NUMERIC_KEYS
        is_status = key == "status"

        col: dict = {
            "field": key,
            "headerName": clear_label(key),
            "filter": "agNumberColumnFilter" if is_num else "agTextColumnFilter",
        }

        if key in CUSTOM_WIDTHS:
            col["width"] = CUSTOM_WIDTHS[key]

        if is_num:
            col[":valueFormatter"] = (
                "params.value != null"
                " ? '₹' + Number(params.value).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})"
                " : '—'"
            )
            col["type"] = "numericColumn"

        if is_status:
            col[":cellStyle"] = (
                "params.value === 'Excess'"
                " ? {background:'#FEE2E2', color:'#991B1B', fontWeight:'600', borderRadius:'4px'}"
                " : {background:'#D1FAE5', color:'#065F46', fontWeight:'600', borderRadius:'4px'}"
            )

        if key in pin_cols:
            col["pinned"] = "left"

        col_defs.append(col)

    grid = (
        ui.aggrid(
            {
                "columnDefs": col_defs,
                "rowData": transactions,
                "defaultColDef": {
                    "flex": 0,
                    "minWidth": 70,
                    "sortable": True,
                    "filter": True,
                    "floatingFilter": True,
                    "resizable": True,
                },
                "domLayout": "normal",
                "suppressColumnVirtualization": False,
                "animateRows": True,
                "pagination": True,
                "paginationPageSize": 25,
                "rowSelection": "single",
                "suppressCellFocus": True,
            },
            theme="balham",
            auto_size_columns=False,
        )
        .classes("w-full")
        .style("font-family:Inter,sans-serif;font-size:13px;")
    )

    async def on_cell_clicked(e):
        row = e.args.get("data", {})
        txn_id = row.get("id")
        if txn_id:
            ui.navigate.to(f"/form?transaction_id={txn_id}")

    grid.on("cellClicked", on_cell_clicked)


# ══════════════════════════════════════════════════════════════
#   CHART HELPERS — ui.echart wrappers
#   ui.echart() accepts a plain Apache ECharts option dict.
#   No JS function strings needed — formatters use ECharts
#   template syntax ('{b}', '{c}', etc.) or plain Python values.
# ══════════════════════════════════════════════════════════════


def render_line_chart(
    series_data: list[tuple[str, list[float]]],
    categories: list[str],
    colors: list[str] | None = None,
    height: int = 240,
) -> None:
    """Smooth multi-series line chart via ui.echart()."""
    default_colors = ["#6366F1", "#EF4444", "#10B981", "#F59E0B"]
    used_colors = colors or default_colors

    series = [
        {
            "name": name,
            "type": "line",
            "smooth": True,
            "data": [round(v) for v in vals],
            "itemStyle": {"color": used_colors[i % len(used_colors)]},
            "lineStyle": {"width": 2, "color": used_colors[i % len(used_colors)]},
            "areaStyle": {"opacity": 0.06, "color": used_colors[i % len(used_colors)]},
            "symbolSize": 6,
        }
        for i, (name, vals) in enumerate(series_data)
    ]

    ui.echart(
        {
            "backgroundColor": "transparent",
            "animation": True,
            "legend": {
                "show": True,
                "top": 0,
                "left": "left",
                "textStyle": {"fontSize": 11, "color": "#6B7280"},
            },
            "grid": {
                "left": 60,
                "right": 16,
                "top": 36,
                "bottom": 36,
                "containLabel": False,
            },
            "xAxis": {
                "type": "category",
                "data": categories,
                "axisLine": {"lineStyle": {"color": "#E5E7EB"}},
                "axisTick": {"show": False},
                "axisLabel": {"fontSize": 10, "color": "#9CA3AF"},
                "splitLine": {"show": False},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": {
                    "fontSize": 10,
                    "color": "#9CA3AF",
                    "formatter": "{value}",  # plain string — no JS needed
                },
                "splitLine": {"lineStyle": {"color": "#F3F4F6", "type": "dashed"}},
                "axisLine": {"show": False},
                "axisTick": {"show": False},
            },
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "#1F2937",
                "borderColor": "#1F2937",
                "textStyle": {"color": "#F9FAFB", "fontSize": 12},
            },
            "series": series,
        }
    ).style(f"height:{height}px;width:100%")


def render_bar_chart(
    items: list[tuple[str, float]],
    color: str = "#6366F1",
    value_fmt: str = "K",  # "K"→₹XK  "N"→count  "raw"→₹X,000
    height: int = 240,
    empty_msg: str = "No data yet",
) -> None:
    """Horizontal bar chart via ui.echart()."""
    if not items:
        ui.label(empty_msg).style(
            "color:#9CA3AF;font-size:12px;padding:20px 0;display:block;text-align:center"
        )
        return

    # ECharts horizontal bar: categories on yAxis, values on xAxis
    categories = [lbl for lbl, _ in items]
    values = [round(val) for _, val in items]

    axis_fmt = "{value}"
    if value_fmt == "K":

        def label_fmt(v):
            return f"₹{v / 1000:.1f}K"

        tt_fmt = "{b}: ₹{c}"  # ECharts template — {b}=category {c}=value
    elif value_fmt == "raw":

        def label_fmt(v):
            return f"₹{v:,.0f}"

        tt_fmt = "{b}: ₹{c}"
    else:  # N — plain count

        def label_fmt(v):
            return str(int(v))

        tt_fmt = "{b}: {c}"

    # Pre-compute label strings in Python — no JS formatter needed
    labels = [label_fmt(v) for v in values]

    ui.echart(
        {
            "backgroundColor": "transparent",
            "animation": True,
            "grid": {
                "left": 120,
                "right": 48,
                "top": 8,
                "bottom": 8,
                "containLabel": False,
            },
            "xAxis": {
                "type": "value",
                "axisLabel": {
                    "fontSize": 10,
                    "color": "#9CA3AF",
                    "formatter": axis_fmt,
                },
                "splitLine": {"lineStyle": {"color": "#F3F4F6", "type": "dashed"}},
                "axisLine": {"show": False},
                "axisTick": {"show": False},
            },
            "yAxis": {
                "type": "category",
                "data": categories,
                "axisLabel": {"fontSize": 11, "color": "#374151"},
                "axisLine": {"lineStyle": {"color": "#E5E7EB"}},
                "axisTick": {"show": False},
                "inverse": False,
            },
            "tooltip": {
                "trigger": "item",
                "backgroundColor": "#1F2937",
                "borderColor": "#1F2937",
                "textStyle": {"color": "#F9FAFB", "fontSize": 12},
                "formatter": tt_fmt,
            },
            "series": [
                {
                    "type": "bar",
                    "data": [
                        {
                            "value": v,
                            "label": {
                                "show": True,
                                "position": "right",
                                "formatter": lbl,
                                "fontSize": 10,
                                "color": "#6B7280",
                            },
                            "itemStyle": {"color": color, "borderRadius": [0, 3, 3, 0]},
                        }
                        for v, lbl in zip(values, labels)
                    ],
                    "barMaxWidth": 28,
                }
            ],
        }
    ).style(f"height:{height}px;width:100%")


# ══════════════════════════════════════════════════════════════
#                        PAGE 1: DASHBOARD
# ══════════════════════════════════════════════════════════════
@ui.page("/")
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
            ui.link("📋 MIS Table", "/mis-table").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )

            # ui.separator().classes("mx-4 my-2")
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

                    with ui.link(target=f"/mis-table?month={ym}").classes(
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
            with ui.link(target="/form").classes(
                "flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            ):
                ui.icon("add").classes("text-primary text-lg text-weight-bold")
                ui.label("New Entry").classes("text-weight-bold pl-2")
            with ui.link(target="settings").classes(
                "flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            ):
                ui.icon("settings").classes("text-primary text-lg text-weight-bold")
                ui.label("Settings").classes("text-weight-bold pl-2")

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
                        ui.button(on_click=lambda: ui.navigate.to("/form"))
                        .classes(
                            "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-[0_3px_10px_rgba(232,64,42,0.3)]"
                        )
                        .props("no-caps unelevated")
                    ):
                        ui.icon("add").classes("text-white text-lg text-weight-bold")
                        ui.label("New Entry").classes("text-weight-bold pl-2")

            # ── Dynamic content container (plain div, no extra padding) ──
            content_area = ui.element("div").classes("w-full")

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

            def render_dashboard(txns: list) -> None:
                """Build the full dashboard UI for a given transaction list."""
                a = compute_analytics(txns)
                content_area.clear()

                with content_area:
                    # ════════════════════════════════════════
                    # ROW 1 — KPI CARDS  (pure CSS grid)
                    # ════════════════════════════════════════
                    excess_color = "#EF4444" if a["total_excess"] > 0 else "#10B981"
                    # ── KPI CARDS ──────────────────────────────────
                    with ui.grid(columns=4).classes("w-full gap-4 mb-5"):
                        # KPI Card: Total Transactions
                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#6366F1] shadow-sm rounded-xl"
                        ):
                            ui.label("🚗").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Deliveries").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(str(a["total_entries"])).classes(
                                "text-[24px] font-bold text-gray-900 leading-none mb-1.5 mono"
                            )
                            with ui.row().classes("gap-1"):
                                ui.label(f"{a['ok_cases']} OK").classes(
                                    "bg-indigo-50 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded"
                                )
                                ui.label(f"{a['excess_cases']} Excess").classes(
                                    "bg-red-50 text-red-700 text-[10px] font-bold px-1.5 py-0.5 rounded"
                                )
                        # KPI Card: Total Allowed Discount
                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"
                        ):
                            ui.label("💸").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Discount Given").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(f"₹{a['total_actual_discount']:,.0f}").classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{a['avg_actual_discount']:,.0f} / transaction"
                            ).classes("text-[14px] text-gray-600")
                        # KPI Card: Total Allowed Discount
                        with ui.card().classes(
                            "relative overflow-hidden p-4.5 px-5 bg-white border-t-4 border-[#10B981] shadow-sm rounded-xl"
                        ):
                            ui.label("💸").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Allowable Discount").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(f"₹{a['total_discount']:,.0f}").classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{a['avg_discount']:,.0f} / transaction"
                            ).classes("text-[14px] text-gray-600")

                        # KPI Card: Total Excess Discount
                        with ui.card().classes(
                            f"relative overflow-hidden p-4.5 px-5 bg-white border-t-4 shadow-sm rounded-xl border-[{excess_color}]"
                        ):
                            ui.label("⚠️").classes(
                                "absolute right-4 top-4 text-[30px] opacity-25 select-none"
                            )
                            ui.label("Total Excess Discount").classes(
                                "text-[11px] font-bold tracking-[0.9px] uppercase text-gray-400 mb-2.5"
                            )
                            ui.label(f"₹{a['total_excess']:,.0f}").classes(
                                f"text-[24px] font-bold leading-none mb-1.5 mono text-[{excess_color}]"
                            )
                            ui.label(
                                "⚠ Requires attention"
                                if a["total_excess"] > 0
                                else "✓ All within limits"
                            ).classes(
                                f"text-[11px] font-medium {'text-red-500' if a['total_excess'] > 0 else 'text-green-500'}"
                            )

                            # KPI Card: Compliance Rate
                            ui.label(
                                f"{a['ok_cases']} of {a['total_entries']} transactions OK"
                            ).classes("text-[14px] text-gray-600")

                    # ── SALES ANALYTICS ────────────────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Sales Analytics").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")

                    with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                        # Units Sold by Car Model
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Units Sold by Car Model").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("all time").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            render_bar_chart(
                                a["top_model_sales"],
                                color="#6366F1",
                                value_fmt="N",
                                empty_msg="No model data",
                                height=220,
                            )

                        # Discount by Car Model
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Discount by Car Model").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("total allowed").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            render_bar_chart(
                                a["top_model_disc"],
                                color="#10B981",
                                value_fmt="K",
                                empty_msg="No model data",
                                height=220,
                            )

                    # Sales conditions (full-width, split 2-col)
                    if a["sorted_conds"]:
                        items_list = list(a["sorted_conds"])
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
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Sales by Outlet").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("transaction count").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            render_bar_chart(
                                a["outlets_sorted_sales"],
                                color="#0EA5E9",
                                value_fmt="N",
                                empty_msg="No outlet data",
                                height=220,
                            )

                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Discount by Outlet").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("total allowed").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            render_bar_chart(
                                a["outlets_sorted_disc"],
                                color="#F59E0B",
                                value_fmt="K",
                                empty_msg="No outlet data",
                                height=220,
                            )

                    # Outlet excess mini-table
                    if a["outlet_excess"]:
                        sorted_oe = sorted(
                            a["outlet_excess"].items(), key=lambda x: -x[1]
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
                                sales_n = a["outlet_sales"].get(o_name, 0)
                                disc_n = a["outlet_discount"].get(o_name, 0)
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
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Excess by Car Model").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("aggregated").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            render_bar_chart(
                                a["top_model_excess"],
                                color="#F97316",
                                value_fmt="K",
                                empty_msg="No excess discounts",
                                height=220,
                            )

                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Excess by Variant").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("granular view").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )
                            render_bar_chart(
                                a["top_variants"],
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
                        # Panel G — Top excess transactions list
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Top Excess Transactions").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("by amount").classes(
                                    "text-[10px] text-gray-400 font-normal"
                                )

                            if a["top_excess_txns"]:
                                for t in a["top_excess_txns"]:
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
                                ui.label("No excess transactions 🎉").classes(
                                    "w-full text-center py-8 text-gray-400 text-[13px]"
                                )

                        # Panel H — Month-wise summary
                        with ui.card().classes("shadow-sm rounded-xl p-5"):
                            with ui.row().classes(
                                "w-full items-baseline justify-between mb-3.5 pb-2.5 border-b border-gray-50"
                            ):
                                ui.label("Month-wise Summary").classes(
                                    "text-[12.5px] font-semibold text-gray-900"
                                )
                                ui.label("click to drill down").classes(
                                    "text-[10px] text-gray-400 font-normal"
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

                            if a["sorted_months_local"]:
                                for ym in a["sorted_months_local"][:10]:
                                    txns_m = a["month_map_local"][ym]
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
                                                f"/mis-table?month={y}"
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


# ══════════════════════════════════════════════════════════════
#                   PAGE: MIS TABLE
# ══════════════════════════════════════════════════════════════
@ui.page("/mis-table")
async def mis_table_page(month: str | None = None) -> None:
    render_topbar("MIS Table")

    try:
        transactions: list = await api_get("/transactions")
    except Exception:
        transactions = []

    # Get months from ALL transactions for sidebar grouping
    month_map = defaultdict(list)
    for t in transactions:
        bd = t.get("booking_date", "")
        if bd and len(bd) >= 7:
            month_map[bd[:7]].append(t)
    sorted_months = sorted(month_map.keys(), reverse=True)

    def month_label(ym: str) -> str:
        try:
            y, m = ym.split("-")
            return f"{calendar.month_abbr[int(m)]} '{y[2:]}"
        except Exception:
            return ym

    # Filter main list if needed
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
            ui.link("📋 MIS Table", "/mis-table").classes(
                "flex px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] no-underline"
            )

            ui.element("div").classes("h-[1px] bg-gray-100 mx-4 my-2")
            ui.label("Filter by Month").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-400 px-4 mb-1.5 mt-4.5"
            )

            ui.link("All Months", "/mis-table").classes(
                f"flex px-4 py-1.5 text-[12.5px] font-medium {'text-[#E8402A]' if not month else 'text-gray-600'} hover:bg-gray-50 no-underline"
            )
            for ym in sorted_months:
                is_curr = month == ym
                with ui.link(target=f"/mis-table?month={ym}").classes(
                    f"flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium {'text-[#E8402A] bg-[#FEF2F0]' if is_curr else 'text-gray-600'} hover:bg-gray-50 no-underline w-full"
                ):
                    ui.label(month_label(ym))
                    ui.label(str(len(month_map[ym]))).classes(
                        "text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500"
                    )

        # ── MAIN CONTENT ─────────────────────────────────────
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    title = f"MIS Table{' — ' + month_label(month) if month else ' — All Months'}"
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
                    ui.button(on_click=lambda: ui.navigate.to("/form"))
                    .classes(
                        "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm"
                    )
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("text-white text-lg text-weight-bold")
                    ui.label("New Entry").classes("text-weight-bold pl-2")

            with ui.card().classes("w-full p-0 shadow-sm rounded-xl mb-8"):
                render_table(transactions)


# ══════════════════════════════════════════════════════════════
#                        PAGE 1: SETTINGS
# ══════════════════════════════════════════════════════════════


@ui.page("/settings")
def settings_page():
    render_topbar("Settings")

    with ui.card().classes(
        "max-w-[1100px] mx-auto p-8 w-full shadow-sm rounded-xl mt-6"
    ):
        ui.label("Upload Price List").classes("text-xl font-bold mb-4")

        # 🔹 Default today
        today = date.today().isoformat()
        with ui.row().classes("justify-end"):
            # 🔹 REQUIRED: valid_from
            valid_from = ui.date_input(
                label="Valid From (Required)", value=today
            ).classes("w-64")

            # 🔹 OPTIONAL: valid_to
            valid_to = ui.date_input(label="Valid To (Optional)").classes("w-64")

            status_label = ui.label("").classes("text-sm mt-2")

            async def handle_upload(e):
                try:
                    if not valid_from.value:
                        status_label.text = "❌ Valid From date is required"
                        status_label.classes("text-red-600")
                        return

                    file = e
                    payload = {"valid_from": valid_from.value}
                    if valid_to.value:
                        payload["valid_to"] = valid_to.value

                    await api_post_file("/price-list/upload", file, payload)
                    status_label.text = "✅ Price list uploaded successfully"
                    status_label.classes("text-green-600")
                except Exception as ex:
                    status_label.text = f"❌ {str(ex)}"
                    status_label.classes("text-red-600")

            ui.upload(on_upload=handle_upload, auto_upload=True).classes("")
            ui.label("Upload Excel file (.xlsx)").classes("text-xs text-gray-400 mt-2")


# ══════════════════════════════════════════════════════════════
#                   PAGE-LOCAL FORM STATE
# ══════════════════════════════════════════════════════════════
class FormState:
    """
    All mutable state for a single /form session.
    Instantiated inside form_page() — never shared across sessions.
    """

    def __init__(self):
        # Edit mode
        self.txn_id: int | None = None
        self.edit_mode: bool = False

        # Reference data
        self.cars: list = []
        self.components: list = []
        self.outlets: list = []
        self.executives: list = []

        # Selected foreign keys
        self.car_id: int | None = None
        self.variant_id: int | None = None
        self.outlet_id: int | None = None
        self.executive_id: int | None = None

        # UI element refs — vehicle
        self.car_select: ui.select | None = None
        self.variant_select: ui.select | None = None
        self.booking_date: ui.input | None = None
        self.outlet_select: ui.select | None = None
        self.exec_select: ui.select | None = None
        self.cust_file_no: ui.input | None = None
        self.vin_no: ui.input | None = None
        self.engine_no: ui.input | None = None
        self.model_year: ui.input | None = None
        self.vehicle_regn_no: ui.input | None = None
        self.regn_date: ui.input | None = None

        # UI element refs — customer
        self.cust_name: ui.input | None = None
        self.cust_mobile: ui.input | None = None
        self.cust_email: ui.input | None = None
        self.cust_relative: ui.input | None = None
        self.cust_address: ui.input | None = None
        self.cust_city: ui.input | None = None
        self.cust_pincode: ui.input | None = None
        self.cust_pan: ui.input | None = None
        self.cust_aadhar: ui.input | None = None
        self.cust_other_id: ui.input | None = None

        # UI element refs — accessories / audit
        self.acc_select: ui.select | None = None
        self.acc_charged: ui.number | None = None
        self.acc_total_label: ui.label | None = None
        self.accessory_allowed: ui.number | None = None
        self.accessory_map: dict = {}

        self.audit_obs: ui.textarea | None = None
        self.audit_action: ui.textarea | None = None

        # UI element refs — actions
        self.submit_btn: ui.button | None = None
        self.error_banner: ui.html | None = None

        # Component toggles
        self.price_match_toggles: dict[str, ui.switch] = {}
        self.discount_match_toggles: dict[str, ui.switch] = {}

        self.listed_prices: dict[str, int] = {}
        self.price_listed_labels: dict[str, ui.label] = {}
        self.discount_listed_labels: dict[str, ui.label] = {}

        # Component inputs
        self.price_inputs: dict[str, ui.input] = {}
        self.discount_inputs: dict[str, ui.input] = {}
        self.discount_rows: dict[str, ui.row] = {}

        # Checkboxes
        self.condition_cbs: dict[str, ui.checkbox] = {}
        self.delivery_cbs: dict[str, ui.checkbox] = {}

        # Invoice Section
        self.invoice_number: ui.input | None = None
        self.invoice_date: ui.input | None = None
        self.invoice_ex_showroom: ui.input | None = None
        self.invoice_discount: ui.input | None = None
        self.invoice_taxable_value: ui.input | None = None
        self.invoice_cgst: ui.input | None = None
        self.invoice_sgst: ui.input | None = None
        self.invoice_igst: ui.input | None = None
        self.invoice_cess: ui.input | None = None
        self.invoice_total: ui.input | None = None

        # Payment Section
        self.payment_cash: ui.input | None = None
        self.payment_bank: ui.input | None = None
        self.payment_finance: ui.input | None = None
        self.payment_exchange: ui.input | None = None

        # Live calc labels
        self.lbl_allowed: ui.label | None = None
        self.lbl_discount: ui.label | None = None
        self.lbl_excess: ui.label | None = None

    @property
    def all_component_inputs(self) -> dict[str, ui.input]:
        return {**self.price_inputs, **self.discount_inputs}

    @property
    def live_discount(self) -> int:
        return sum(int(parsed_val(inp)) for inp in self.discount_inputs.values())

    def is_valid(self) -> tuple[bool, str]:
        def _val(f):
            return (f.value or "").strip() if f else ""

        def _val_upper(f):
            return (f.value or "").strip().upper() if f else ""

        if not self.variant_id:
            return False, "Please select a Car and Variant."

        if not _val(self.cust_name):
            return False, "Customer name is required."

        mob = _val(self.cust_mobile)
        if not re.fullmatch(r"[6-9]\d{9}", mob):
            return False, "Mobile must be 10 digits starting with 6–9."

        if not _val(self.cust_address):
            return False, "Address is required."

        if not _val(self.cust_city):
            return False, "City is required."

        # pincode_clean = re.sub(r"\D", "", _val(self.cust_pincode))
        # if len(pincode_clean) != 6:
        #     return False, "Valid 6-digit PIN code required."

        pan_val = _val_upper(self.cust_pan)
        if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_val):
            return False, "Valid PAN required."

        # aadhar_raw = _val(self.cust_aadhar)
        # aadhar_clean = re.sub(r"\D", "", aadhar_raw)
        # if aadhar_clean and len(aadhar_clean) != 12:
        #     return False, "Valid 12-digit Aadhar required."

        # TR Case condition
        if self.condition_cbs.get("tr_case") and self.condition_cbs["tr_case"].value:
            if not _val(self.cust_other_id):
                return False, "Other ID Proof required for TR Case."

        if not _val(self.cust_file_no):
            return False, "Customer File Number is required."

        if not _val(self.vin_no):
            return False, "VIN Number is required."

        if not _val(self.engine_no):
            return False, "Engine Number is required."

        year_val = _val(self.model_year)
        if not year_val or not year_val.isdigit():
            return False, "Valid Model Year is required."

        return True, ""


# ══════════════════════════════════════════════════════════════
# FORM SECTION BUILDERS
# ══════════════════════════════════════════════════════════════
def build_form_sec_vehicle(state: FormState) -> None:
    car_opts = {car["id"]: car["name"] for car in state.cars}
    outlet_opts = {outlet["id"]: outlet["name"] for outlet in state.outlets}
    exec_opts = {executive["id"]: executive["name"] for executive in state.executives}

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🚙").classes("text-[20px] select-none")
            ui.label("Vehicle & Delivery Details").classes(
                "text-[15px] font-bold text-gray-900"
            )

        with ui.grid(columns=4).classes("w-full gap-5"):
            state.car_select = (
                ui.select(
                    options=car_opts,
                    label="Car *",
                    with_input=True,
                    on_change=lambda e: _fs_on_car_change(e.value, state),
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.variant_select = (
                ui.select(
                    options={},
                    with_input=True,
                    label="Variant *",
                    on_change=lambda e: _fs_on_variant_change(e.value, state),
                )
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.booking_date = (
                ui.input(
                    label="Booking Date *",
                    value=str(date.today()),
                    on_change=lambda _: _fs_try_price_preload(state),
                )
                .classes("w-full")
                .props('type="date" outlined dense')
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.outlet_select = (
                ui.select(
                    options=outlet_opts,
                    label="Outlet",
                    on_change=lambda e: setattr(state, "outlet_id", e.value),
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.exec_select = (
                ui.select(
                    options=exec_opts,
                    label="Sales Executive",
                    on_change=lambda e: setattr(state, "executive_id", e.value),
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.cust_file_no = (
                ui.input(label="Customer File No *")
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.vin_no = (
                ui.input(label="VIN Number *")
                .classes("w-full uppercase")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.engine_no = (
                ui.input(label="Engine Number *")
                .classes("w-full uppercase")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.model_year = (
                ui.input(label="Model Year *", placeholder="e.g. 2024")
                .classes("w-full")
                .props('outlined dense type="number"')
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.vehicle_regn_no = (
                ui.input(label="Vehicle Regn Number")
                .classes("w-full uppercase")
                .props("outlined dense")
            )
            state.regn_date = (
                ui.input(label="Date of Registration")
                .classes("w-full")
                .props('outlined dense type="date"')
            )

        if state.outlets:
            state.outlet_select.set_value(state.outlets[0]["id"])
            state.outlet_id = state.outlets[0]["id"]
        if state.executives:
            state.exec_select.set_value(state.executives[0]["id"])
            state.executive_id = state.executives[0]["id"]


def build_form_sec_customer(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("👤").classes("text-[20px] select-none")
            ui.label("Customer Details").classes("text-[15px] font-bold text-gray-900")

        # ── Basic Info ─────────────────────────────
        with ui.grid(columns=4).classes("w-full gap-5"):
            state.cust_name = (
                ui.input(label="Name *", placeholder="Full name")
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.cust_mobile = (
                ui.input(
                    label="Mobile *",
                    placeholder="10-digit",
                    validation={
                        "Must be 10 digits starting 6–9": lambda v: (
                            not v or re.fullmatch(r"[6-9]\d{9}", v)
                        )
                    },
                )
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.cust_email = (
                ui.input(label="Email", placeholder="optional")
                .classes("w-full")
                .props("outlined dense")
            )
            state.cust_relative = (
                ui.input(label="Relative Name", placeholder="optional")
                .classes("w-full")
                .props("outlined dense")
            )
            state.cust_address = (
                ui.textarea(label="Address *")
                .classes("w-full")
                .props("outlined dense rows=2")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.cust_city = (
                ui.input(label="City *")
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.cust_pincode = (
                ui.input(
                    label="Pin Code *",
                    placeholder="6 digits",
                    validation={
                        "Must be 6 digits": lambda v: (
                            len(re.sub(r"\D", "", v or "")) == 6
                        )
                    },
                )
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.cust_pan = (
                ui.input(
                    label="PAN *",
                    placeholder="ABCDE1234F",
                    validation={
                        "Invalid PAN format": lambda v: (
                            not v or re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v.upper())
                        )
                    },
                )
                .classes("w-full uppercase")
                .props("outlined dense")
                .on(
                    "update:model-value",
                    lambda e: (
                        state.cust_pan.set_value(e.args.upper())
                        if isinstance(e.args, str)
                        else None,
                        _fs_revalidate(state),
                    ),
                )
            )
            state.cust_aadhar = (
                ui.input(
                    label="Aadhar *",
                    placeholder="12 digits",
                    validation={
                        "Must be 12 digits": lambda v: (
                            len(re.sub(r"\D", "", v or "")) == 12
                        )
                    },
                )
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.cust_other_id = (
                ui.input(label="Other ID Proof")
                .classes("w-full")
                .props("outlined dense")
            )


def build_form_sec_conditions(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("☑️").classes("text-[20px] select-none")
            ui.label("Sale Conditions").classes("text-[15px] font-bold text-gray-900")

        with ui.row().classes("flex-wrap gap-x-8 gap-y-4"):
            for key, label in CONDITION_KEYS:
                state.condition_cbs[key] = (
                    ui.checkbox(label)
                    .props("dense color=primary")
                    .classes("text-gray-700 font-medium")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )


def build_form_sec_prices(state: FormState) -> None:
    price_comps = sorted(
        [
            price_comp
            for price_comp in state.components
            if price_comp.get("type") == "price"
        ],
        key=lambda x: x.get("order", 99),
    )
    discount_comps = sorted(
        [
            discount_comp
            for discount_comp in state.components
            if discount_comp.get("type") == "discount"
        ],
        key=lambda x: x.get("order", 99),
    )

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 pb-2 border-b border-gray-100"
        ):
            ui.label("💰").classes("text-lg select-none")
            ui.label("Price & Discounts").classes("text-[15px] font-bold text-gray-900")

        ui.label("Price Charged as per Books of Accounts").classes(
            "text-sm font-bold tracking-[0.9px] uppercase text-gray-400 "
        )
        ui.separator().classes("mt-0")
        if price_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in price_comps:
                    name = comp["name"]

                    with ui.row().classes("w-full items-center h-10"):
                        # Label
                        ui.label(name).classes("w-60 text-sm")

                        # Listed price display
                        listed_label = ui.label("₹—").classes(
                            "w-32 text-gray-500 text-sm"
                        )
                        state.price_listed_labels[name] = listed_label

                        # Toggle (Match Listed Price)
                        toggle = (
                            ui.switch("Match Listed Price")
                            # .classes("m-10")
                            .props('dense icon="check" color="green"')
                        )

                        # Input
                        inp = (
                            accounting_input(
                                "",
                                placeholder="Enter Charged Price",
                                container_classes="w-60",
                            )
                        ).props("dense")

                        state.price_inputs[name] = inp
                        state.price_match_toggles[name] = toggle

                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)  # disable input
                            else:
                                inp.set_enabled(True)  # re-enable input
                                inp.set_value(None)  # optional: clear
                            _fs_update_live(state)

                        toggle.on("update:model-value", on_toggle)
                        inp.on_value_change(lambda _: _fs_update_live(state))

        else:
            ui.label("No price components — check /components endpoint.").classes(
                "text-xs text-gray-400"
            )

        ui.label("Discounts Offered as per Books of Accounts").classes(
            "text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mb-1 mt-1 pt-1"
        )
        ui.separator().classes("mt-0 my-2")
        if discount_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in discount_comps:
                    name = comp["name"]

                    with ui.row().classes("w-full align-center h-10") as row_element:
                        ui.label(name).classes("w-60 text-sm")

                        listed_label = ui.label("₹—").classes(
                            "w-32 text-gray-500 text-sm"
                        )
                        state.discount_listed_labels[name] = listed_label

                        toggle = (
                            ui.switch("Standard Discount")
                            # .classes("m-10")
                            .props('dense icon="check" color="green"')
                        )

                        inp = (
                            accounting_input(
                                "", placeholder="₹", container_classes="w-60"
                            )
                        ).props("dense")
                        inp.on_value_change(lambda _: _fs_update_live(state))

                        state.discount_inputs[name] = inp
                        state.discount_match_toggles[name] = toggle
                        state.discount_rows[name] = row_element

                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)  # disable input
                            else:
                                inp.set_enabled(True)  # re-enable input
                                inp.set_value(None)  # optional: clear

                        toggle.on("update:model-value", on_toggle)

        else:
            ui.label("No discount components — check /components endpoint.").classes(
                "text-xs text-gray-400"
            )


def build_form_sec_accessories(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🔧").classes("text-[20px] select-none")
            ui.label("Accessories").classes("text-[15px] font-bold text-gray-900")

        options = {
            acc_id: f"{data['name']} (₹{data['listed_price']})"
            for acc_id, data in state.accessory_map.items()
        }

        # ── Visual List Display ────────────────────
        selection_display = ui.column().classes("w-full mt-2 gap-1 col-span-3")

        def update_total(e):
            selected = e.value or []
            total = sum(
                state.accessory_map.get(int(i), {}).get("listed_price", 0)
                for i in selected
            )

            state.acc_total_label.set_text(f"Total: ₹{total:,.0f}")

            # auto-fill charged if empty
            if not state.acc_charged.value:
                state.acc_charged.set_value(total)

            # Update visual list
            selection_display.clear()
            with selection_display:
                if selected:
                    ui.label("Selected Accessories:").classes(
                        "text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1"
                    )
                    for i in selected:
                        acc = state.accessory_map.get(int(i))
                        if acc:
                            with ui.row().classes(
                                "items-center gap-2 bg-gray-50/50 px-3 py-1.5 rounded-lg border border-gray-100 w-full"
                            ):
                                ui.label(f"ID: {acc['id']}").classes(
                                    "text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded"
                                )
                                ui.label(acc["name"]).classes(
                                    "text-[12px] text-gray-700 font-medium"
                                )
                                ui.label(f"₹{acc['listed_price']:,}").classes(
                                    "text-[11px] text-gray-400 mono ml-auto"
                                )

        # ── Multi-select ───────────────────────────
        with ui.grid(columns=3).classes("w-full items-center gap-4"):
            state.acc_select = (
                ui.select(
                    options=options,
                    label="Select Accessories",
                    multiple=True,
                    with_input=True,  # search enabled
                    on_change=update_total,
                )
                .classes("w-full h-10")
                .props("outlined dense use-input")
            )

            # ── Total Display ──────────────────────────
            state.acc_total_label = (
                ui.label("Total: ₹0")
                .classes("text-sm text-bold vertical-align-center")
                .props("dense")
            )

            # ── Charged Input ─────────────────────────
            state.acc_charged = accounting_input(label_text="Actual Charged (₹)")


def build_form_sec_delivery(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("✅").classes("text-[20px] select-none")
            ui.label("Delivery Checklist").classes(
                "text-[15px] font-bold text-gray-900"
            )
        with ui.grid(columns=5).classes("w-full gap-y-2"):
            for key, label in DELIVERY_CHECK_KEYS:
                state.delivery_cbs[key] = ui.checkbox(label).props("dense")


def build_form_sec_audit(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📋").classes("text-[20px] select-none")
            ui.label("Audit").classes("text-[15px] font-bold text-gray-900")
        with ui.grid(columns=2).classes("w-full gap-2"):
            state.audit_obs = (
                ui.textarea(label="Observations", placeholder="Enter observations...")
                .classes("w-full")
                .props("outlined dense rows=3")
            )
            state.audit_action = (
                ui.textarea(label="Follow-up Action", placeholder="Enter actions...")
                .classes("w-full")
                .props("outlined dense rows=3")
            )


def build_form_sec_invoice(state: FormState) -> None:
    def calculate_taxes():
        taxable = parsed_val(state.invoice_taxable_value)
        cgst = taxable * 0.09
        sgst = taxable * 0.09
        state.invoice_cgst.set_value(format_num_inr(cgst))
        state.invoice_sgst.set_value(format_num_inr(sgst))
        calculate_total()

    def calculate_total():
        taxable = parsed_val(state.invoice_taxable_value)
        cgst = parsed_val(state.invoice_cgst)
        sgst = parsed_val(state.invoice_sgst)
        igst = (
            parsed_val(state.invoice_igst)
            if state.igst_toggle and state.igst_toggle.value
            else 0
        )
        cess = (
            parsed_val(state.invoice_cess)
            if state.cess_toggle and state.cess_toggle.value
            else 0
        )

        total = taxable + cgst + sgst + igst + cess
        state.invoice_total.set_value(format_num_inr(total))

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🧾").classes("text-[20px] select-none")
            ui.label("Invoice Details").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=3).classes("w-full gap-5"):
            state.invoice_number = (
                ui.input(label="Invoice Number")
                .classes("uppercase")
                .props("outlined dense")
            )
            state.invoice_date = ui.input(label="Invoice Date").props(
                'outlined dense type="date"'
            )

            state.invoice_ex_showroom = accounting_input(
                label_text="Ex-Showroom Price (From Price List)"
            )
            state.invoice_ex_showroom.props("readonly")
            state.invoice_ex_showroom.on_value_change(lambda _: _fs_update_live(state))

            state.invoice_discount = accounting_input(label_text="Discount")
            state.invoice_discount.on_value_change(lambda _: _fs_update_live(state))

            state.invoice_taxable_value = accounting_input(label_text="Taxable Value")
            state.invoice_taxable_value.on_value_change(
                lambda _: (
                    calculate_taxes(),
                    calculate_total(),
                    _fs_update_live(state),
                )
            )

            state.invoice_cgst = accounting_input(label_text="CGST")
            state.invoice_cgst.on_value_change(lambda _: calculate_total())

            state.invoice_sgst = accounting_input(label_text="SGST")
            state.invoice_sgst.on_value_change(lambda _: calculate_total())

            state.igst_toggle = ui.switch("Apply IGST").props("dense")
            state.invoice_igst = accounting_input(label_text="IGST")
            state.invoice_igst.on_value_change(lambda _: calculate_total())

            state.cess_toggle = ui.switch("Apply CESS").props("dense")
            state.invoice_cess = accounting_input(label_text="CESS")
            state.invoice_cess.on_value_change(lambda _: calculate_total())

            state.invoice_total = accounting_input(label_text="Total Invoice Value")

        def toggle_taxes():
            state.invoice_igst.set_enabled(state.igst_toggle.value)
            state.invoice_cess.set_enabled(state.cess_toggle.value)

        state.igst_toggle.on(
            "update:model-value", lambda _: (toggle_taxes(), calculate_total())
        )
        state.cess_toggle.on(
            "update:model-value", lambda _: (toggle_taxes(), calculate_total())
        )

        toggle_taxes()
        calculate_total()


def build_form_sec_payment(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("💳").classes("text-[20px] select-none")
            ui.label("Payment Received").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=4).classes("w-full gap-2 items-start"):
            state.payment_cash = accounting_input("Cash Payment")
            state.payment_bank = accounting_input("Bank Payment")
            state.payment_finance = accounting_input("Finance")
            state.payment_exchange = accounting_input("Exchange")

        # ── Dynamic Enable/Disable ─────────────
        def toggle_fields():
            if state.condition_cbs.get("finance"):
                state.payment_finance.set_enabled(state.condition_cbs["finance"].value)

            if state.condition_cbs.get("exchange"):
                state.payment_exchange.set_enabled(
                    state.condition_cbs["exchange"].value
                )

        # attach listeners
        for key in ["finance", "exchange"]:
            if key in state.condition_cbs:
                state.condition_cbs[key].on(
                    "update:model-value", lambda _: toggle_fields()
                )

        toggle_fields()


def build_form_sec_live_bar(state: FormState) -> None:
    with ui.row().classes(
        "w-full bg-[#0F1623] text-white p-3 px-6 rounded-xl items-center gap-6 shadow-lg mb-4"
    ):
        ui.label("LIVE TOTALS").classes(
            "text-[10px] font-bold tracking-[1.2px] text-white/40 uppercase"
        )
        ui.element("div").classes("w-[1px] h-4 bg-white/10")

        with ui.row().classes("items-center gap-2"):
            ui.label("Allowable Discount (As per Price List):").classes(
                "text-[11px] text-white/50"
            )
            state.lbl_allowed = ui.label("₹0").classes(
                "text-[16px] font-bold text-white mono"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Discount Given:").classes("text-[11px] text-white/50")
            state.lbl_discount = ui.label("₹0").classes(
                "text-[16px] font-bold text-white mono"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Excess Discount:").classes("text-[11px] text-white/50")
            state.lbl_excess = ui.label("—").classes(
                "text-[16px] font-bold text-white/30 mono"
            )


def build_form_sec_action_bar(state: FormState) -> None:
    with ui.row().classes(
        "w-full bg-red-50 border border-red-200 p-3 rounded-lg items-center gap-3 mb-4"
    ) as banner:
        state.error_banner = banner
        ui.label("⚠️").classes("text-red-500")
        state.error_msg_label = ui.label("").classes(
            "text-red-800 text-[13px] font-medium"
        )

    state.error_banner.set_visibility(False)

    with ui.row().classes("w-full items-center justify-between py-4"):
        ui.button("← Back to Dashboard", on_click=lambda: ui.navigate.to("/")).classes(
            "text-gray-500 text-[13px] hover:text-gray-800"
        ).props("flat no-caps")
        state.submit_btn = (
            ui.button(
                "Save Entry" if not state.edit_mode else "Update Entry",
                on_click=lambda: _fs_handle_submit(state),
            )
            .classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            )
            .props("no-caps unelevated")
        )


# ══════════════════════════════════════════════════════════════
# FORM EVENT HANDLERS
# ══════════════════════════════════════════════════════════════
async def _fs_on_car_change(car_id, state: FormState) -> None:
    state.car_id = car_id
    state.variant_id = None
    if state.variant_select is None:
        return
    state.variant_select.set_value(None)
    state.variant_select.options = {}
    state.variant_select.update()
    _fs_clear_prices(state)
    if not car_id:
        return
    try:
        variants = await api_get(f"/cars/{car_id}/variants")
        state.variant_select.options = {
            v["id"]: v["full_variant_name"] for v in variants
        }
        state.variant_select.update()
    except Exception as ex:
        _fs_show_error(state, f"Failed to load variants: {ex}")


async def _fs_on_variant_change(variant_id, state: FormState) -> None:
    state.variant_id = variant_id

    # force UI sync before validation
    await ui.run_javascript("")

    _fs_revalidate(state)

    if variant_id:
        await _fs_try_price_preload(state)


async def _fs_try_price_preload(state: FormState) -> None:
    """Call GET /price-list/preview when both variant + date are known."""
    if not state.variant_id or not (state.booking_date and state.booking_date.value):
        return

    try:
        booking_date = state.booking_date.value
        preview = await api_get(
            f"/price-list/preview?variant_id={state.variant_id}&booking_date={booking_date}"
        )

        # ── Store listed prices (source of truth) ──
        state.listed_prices = preview or {}
        filled = 0

        for name, value in state.listed_prices.items():
            if value is None:
                continue

            formatted = f"₹{int(value):,}"

            # ── Update Listed Price Labels ──
            if name in state.price_listed_labels:
                state.price_listed_labels[name].set_text(formatted)

            if name in state.discount_listed_labels:
                state.discount_listed_labels[name].set_text(formatted)

            # ── Auto-fill ONLY if toggle is ON ──
            if name in state.price_match_toggles:
                toggle = state.price_match_toggles[name]
                inp = state.price_inputs.get(name)

                if toggle.value and inp:
                    inp.set_value(int(value))
                    inp.props("readonly")
                    filled += 1

            if name in state.discount_match_toggles:
                toggle = state.discount_match_toggles[name]
                inp = state.discount_inputs.get(name)

                if toggle.value and inp:
                    inp.set_value(int(value))
                    inp.props("readonly")
                    filled += 1

        if state.invoice_ex_showroom:
            # Match main.py line 1516
            val = state.listed_prices.get("Ex Showroom Price", 0)
            state.invoice_ex_showroom.set_value(val)

        _fs_update_live(state)

        if filled:
            ui.notify(
                f"✓ {filled} field{'s' if filled > 1 else ''} synced with listed price.",
                type="info",
                position="top-right",
                timeout=2500,
            )

    except Exception:
        pass  # best-effort; silently skip if endpoint missing


def _fs_update_live(state: FormState) -> None:
    if not state.lbl_discount:
        return

    # 1. Sync Ex-showroom from Prices Section (if match exists)
    # Match main.py line 1574
    found_ex = None
    if "Ex Showroom Price" in state.price_inputs:
        found_ex = state.price_inputs["Ex Showroom Price"]
    elif "Ex-Showroom Price" in state.price_inputs:
        found_ex = state.price_inputs["Ex-Showroom Price"]

    if state.invoice_ex_showroom and found_ex:
        price_val = int(parsed_val(found_ex))
        if parsed_val(state.invoice_ex_showroom) != price_val:
            state.invoice_ex_showroom.set_value(format_num_inr(price_val))

    # 2. Sync Total Discount from Components -> Invoice Discount field
    total_comp_discount = state.live_discount
    if (
        state.invoice_discount
        and parsed_val(state.invoice_discount) != total_comp_discount
    ):
        state.invoice_discount.set_value(format_num_inr(total_comp_discount))

    # 3. Read current values for labels
    allowed_discount = 0
    if hasattr(state, "listed_prices") and state.listed_prices:
        for name, inp in state.discount_inputs.items():
            row = state.discount_rows.get(name)
            if row is None or row.visible:
                val = state.listed_prices.get(name)
                if val is not None:
                    allowed_discount += int(val)

    inv_discount = (
        int(parsed_val(state.invoice_discount)) if state.invoice_discount else 0
    )

    # 4. Update Labels
    if hasattr(state, "lbl_allowed") and state.lbl_allowed:
        state.lbl_allowed.set_text(f"₹{allowed_discount:,.0f}")

    if state.lbl_discount:
        state.lbl_discount.set_text(f"₹{inv_discount:,.0f}")

    # Excess Discount = Actual Discount - Allowed Discount
    excess = inv_discount - allowed_discount
    if state.lbl_excess:
        state.lbl_excess.set_text(f"₹{excess:,.0f}")
        # Color coding: Green if actual <= allowed (good), Red if actual > allowed (bad)
        if excess <= 0:
            state.lbl_excess.style("color:#6EE7B7")  # Soft green
        else:
            state.lbl_excess.style("color:#FCA5A5")  # Soft red


def _fs_validate_mobile(state: FormState) -> None:
    if state.cust_mobile is None:
        return
    mob = (state.cust_mobile.value or "").strip()
    if mob and not re.fullmatch(r"[6-9]\d{9}", mob):
        state.cust_mobile.props(
            "error error-message='Must be 10 digits starting 6 to 9'"
        )
    else:
        state.cust_mobile.props(remove="error")
    _fs_revalidate(state)


def _fs_validate_pincode(state: FormState) -> None:
    if state.cust_pincode is None:
        return
    val = (state.cust_pincode.value or "").strip()
    if not re.fullmatch(r"\d{6}", val):
        state.cust_pincode.props("error error-message='Must be 6 digits'")
    else:
        state.cust_pincode.props(remove="error")
    _fs_revalidate(state)


def _fs_validate_pan(state: FormState) -> None:
    if state.cust_pan is None:
        return
    val = (state.cust_pan.value or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", val):
        state.cust_pan.props("error error-message='Invalid PAN format'")
    else:
        state.cust_pan.props(remove="error")
    _fs_revalidate(state)


def _fs_validate_aadhar(state: FormState) -> None:
    if state.cust_aadhar is None:
        return
    val = (state.cust_aadhar.value or "").strip()
    if not re.fullmatch(r"\d{12}", val):
        state.cust_aadhar.props("error error-message='Must be 12 digits'")
    else:
        state.cust_aadhar.props(remove="error")
    _fs_revalidate(state)


def _fs_update_visibility(state: FormState) -> None:
    def is_checked(key: str) -> bool:
        cb = state.condition_cbs.get(key)
        return bool(cb and cb.value)

    def norm(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

    visibility_rules = {
        norm("Extra Kitty On TR cases"): is_checked("tr_case"),
        norm("Additional For POI /Corporate Customers"): is_checked("corporate")
        or is_checked("govt_employee"),
        norm("Additional For Exchange Customers"): is_checked("exchange"),
        norm("Additional For Scrappage Customers"): is_checked("scrap"),
        norm("Additional For Upward Sales Customers"): is_checked("upgrade"),
    }

    modified = False
    for name, row in state.discount_rows.items():
        n_name = norm(name)
        if n_name in visibility_rules:
            visible = visibility_rules[n_name]
            row.set_visibility(visible)
            if not visible:
                inp = state.discount_inputs.get(name)
                toggle = state.discount_match_toggles.get(name)

                if toggle and toggle.value:
                    toggle.set_value(False)

                if inp and inp.value:
                    inp.set_value(None)
                    modified = True

    if modified:
        _fs_update_live(state)


def _fs_revalidate(state: FormState) -> None:
    _fs_update_visibility(state)
    ok, msg = state.is_valid()

    if state.submit_btn:
        state.submit_btn.set_enabled(ok)

    if state.error_banner and state.error_msg_label:
        if not ok:
            state.error_msg_label.set_text(msg)
            state.error_banner.set_visibility(True)
        else:
            state.error_banner.set_visibility(False)


def _fs_clear_prices(state: FormState) -> None:
    for inp in state.price_inputs.values():
        inp.set_value(None)


def _fs_show_error(state: FormState, msg: str) -> None:
    if state.error_banner and state.error_msg_label:
        state.error_msg_label.set_text(msg)
        state.error_banner.set_visibility(True)


def _fs_clear_error(state: FormState) -> None:
    if state.error_banner and state.error_msg_label:
        state.error_banner.set_visibility(False)
        state.error_msg_label.set_text("")


# ══════════════════════════════════════════════════════════════
# SUBMIT HANDLER
# ══════════════════════════════════════════════════════════════
async def _fs_handle_submit(state: FormState) -> None:
    if not state.error_banner or not state.error_msg_label:
        return

    valid, msg = state.is_valid()
    if not valid:
        state.error_msg_label.set_text(msg)
        state.error_banner.set_visibility(True)
        return

    payload = build_payload(state)

    try:
        await api_post("/transactions", payload)
        ui.notify("✅ Transaction saved", color="green")
        ui.navigate.to("/")
    except Exception as e:
        state.error_msg_label.set_text(str(e))
        state.error_banner.set_visibility(True)


def build_payload(state: FormState) -> dict:
    def val(x):
        return x.value if x else None

    def intval(x):
        if not x:
            return 0
        v = x.value
        if not v:
            return 0
        try:
            v_str = str(v).replace(",", "").strip()
            import re

            if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
                return int(float(eval(v_str)))
            return int(float(v_str))
        except Exception:
            return 0

    # ─────────────────────────────
    # COMPONENTS (CRITICAL)
    # ─────────────────────────────
    actual_amounts = {}

    # Price components
    for name, inp in state.price_inputs.items():
        actual_amounts[name] = intval(inp)

    # Discount components
    for name, inp in state.discount_inputs.items():
        actual_amounts[name] = intval(inp)

    # ─────────────────────────────
    # CONDITIONS
    # ─────────────────────────────
    conditions = {key: (cb.value or False) for key, cb in state.condition_cbs.items()}

    # ─────────────────────────────
    # DELIVERY CHECKS
    # ─────────────────────────────
    delivery_checks = {
        key: (cb.value or False) for key, cb in state.delivery_cbs.items()
    }

    # ─────────────────────────────
    # ACCESSORIES
    # ─────────────────────────────
    # selected_ids list (for backend model logic)
    selected_acc_ids = state.acc_select.value or []

    # helper for flat listing
    items_list = []
    for aid in selected_acc_ids:
        acc_info = state.accessory_map.get(int(aid))
        if acc_info:
            items_list.append(
                {"id": aid, "name": acc_info["name"], "price": acc_info["listed_price"]}
            )

    total_listed = sum(item["price"] for item in items_list)

    accessories_details = {
        "items": items_list,
        "charged_amount": intval(state.acc_charged),
        "allowed_amount": total_listed,
    }

    # ─────────────────────────────
    # INVOICE
    # ─────────────────────────────
    invoice_details = {
        "invoice_number": val(state.invoice_number),
        "invoice_date": val(state.invoice_date),
        "ex_showroom_price": intval(state.invoice_ex_showroom),
        "discount": intval(state.invoice_discount),
        "taxable_value": intval(state.invoice_taxable_value),
        "cgst": intval(state.invoice_cgst),
        "sgst": intval(state.invoice_sgst),
        "igst": intval(state.invoice_igst),
        "cess": intval(state.invoice_cess),
        "total": intval(state.invoice_total),
    }

    # ─────────────────────────────
    # PAYMENT
    # ─────────────────────────────
    payment_details = {
        "cash": intval(state.payment_cash),
        "bank": intval(state.payment_bank),
        "finance": intval(state.payment_finance),
        "exchange": intval(state.payment_exchange),
    }

    # ─────────────────────────────
    # MAIN PAYLOAD
    # ─────────────────────────────
    payload = {
        # ── REQUIRED ──
        "variant_id": state.variant_id,
        "booking_date": val(state.booking_date),
        "outlet_id": state.outlet_id,
        "sales_executive_id": state.executive_id,
        # ── CUSTOMER ──
        "customer": {
            "name": val(state.cust_name),
            "mobile_number": val(state.cust_mobile),
            "email": val(state.cust_email),
            "pan_number": val(state.cust_pan),
            "aadhar_number": val(state.cust_aadhar),
            "address": val(state.cust_address),
            "city": val(state.cust_city),
            "pin_code": val(state.cust_pincode),
        },
        # ── VEHICLE ──
        "customer_file_number": val(state.cust_file_no),
        "vin_number": val(state.vin_no),
        "engine_number": val(state.engine_no),
        "registration_number": val(state.vehicle_regn_no),
        "registration_date": val(state.regn_date),
        # ── CORE LOGIC ──
        "actual_amounts": actual_amounts,
        "conditions": conditions,
        "delivery_checks": delivery_checks,
        # ── JSON SECTIONS ──
        "accessories_details": accessories_details,
        "accessory_ids": selected_acc_ids,  # Explicitly for TransactionService
        "invoice_details": invoice_details,
        "payment_details": payment_details,
        # ── OPTIONAL FUTURE SAFE ──
        "finance_details": {},
        "exchange_details": {},
        # ── AUDIT INFO ──
        "audit_info": {
            "observations": val(state.audit_obs),
            "actions": val(state.audit_action),
        },
    }

    return payload


# ══════════════════════════════════════════════════════════════
# PREFILL FORM FROM EXISTING TRANSACTION (edit mode)
# ══════════════════════════════════════════════════════════════
async def _fs_prefill(state: FormState, txn: dict) -> None:
    """
    Populate all form fields from a fetched transaction dict.
    Called after the UI is fully built in edit mode.
    """
    # Customer
    cust = txn.get("customer", {})
    if state.cust_name:
        state.cust_name.set_value(cust.get("name", ""))
    if state.cust_mobile:
        state.cust_mobile.set_value(cust.get("mobile_number", ""))
    if state.cust_email:
        state.cust_email.set_value(cust.get("email", "") or "")

    # Booking date
    bd = txn.get("booking_date")
    if bd and state.booking_date:
        state.booking_date.set_value(bd)

    # Outlet / executive
    if txn.get("outlet_id") and state.outlet_select:
        state.outlet_select.set_value(txn["outlet_id"])
        state.outlet_id = txn["outlet_id"]
    if txn.get("sales_executive_id") and state.exec_select:
        state.exec_select.set_value(txn["sales_executive_id"])
        state.executive_id = txn["sales_executive_id"]

    # Car → triggers variant dropdown load
    car_id = txn.get("car_id")
    if car_id and state.car_select:
        state.car_select.set_value(car_id)
        state.car_id = car_id
        # Load variants for this car
        try:
            variants = await api_get(f"/cars/{car_id}/variants")
            state.variant_select.options = {
                v["id"]: v["full_variant_name"] for v in variants
            }
            state.variant_select.update()
        except Exception:
            pass

    # Variant
    variant_id = txn.get("variant_id")
    if variant_id and state.variant_select:
        state.variant_select.set_value(variant_id)
        state.variant_id = variant_id

    # Conditions
    conds = txn.get("conditions", {})
    for key, cb in state.condition_cbs.items():
        cb.set_value(bool(conds.get(key, False)))

    # Actual amounts → fill price + discount inputs
    amounts = txn.get("actual_amounts", {})
    for name, inp in state.all_component_inputs.items():
        if name in amounts:
            inp.set_value(amounts[name])

    # Accessories
    acc_details = txn.get("accessories_details", {})
    if state.acc_select:
        # Reconstruct selected IDs from transaction (backend 'accessories' key holds list of objects)
        selected_ids = [a["id"] for a in txn.get("accessories", [])]
        state.acc_select.set_value(selected_ids)

    if state.acc_charged:
        state.acc_charged.set_value(acc_details.get("charged_amount", 0))

    if state.accessory_allowed:
        state.accessory_allowed.set_value(acc_details.get("allowed_amount", 0))

    # Delivery checks
    delv = txn.get("delivery_checks", {})
    for key, cb in state.delivery_cbs.items():
        cb.set_value(bool(delv.get(key, False)))

    # Audit
    audit = txn.get("audit_info", {})
    if state.audit_obs:
        state.audit_obs.set_value(audit.get("observations", ""))
    if state.audit_action:
        state.audit_action.set_value(audit.get("follow_up_action", ""))

    # Refresh live calc
    _fs_update_live(state)
    _fs_revalidate(state)


# ══════════════════════════════════════════════════════════════
#   PAGE 2: FORM
# ══════════════════════════════════════════════════════════════
@ui.page("/form")
async def form_page(transaction_id: str | None = None) -> None:
    state = FormState()

    # Detect edit mode from query param
    txn_data = None
    if transaction_id:
        try:
            txn_data = await api_get(f"/transactions/{transaction_id}")
            state.txn_id = int(transaction_id)
            state.edit_mode = True
        except Exception:
            pass  # If fetch fails, fall through to blank form

    # Breadcrumb label
    bc = f"Edit Entry #{state.txn_id}" if state.edit_mode else "New Entry"
    render_topbar(bc)

    # Fetch reference data
    ref = await fetch_reference_data()
    state.cars = ref["cars"]
    state.components = ref["components"]
    state.outlets = ref["outlets"]
    state.executives = ref["executives"]
    state.accessory_map = {acc["id"]: acc for acc in ref["accessories"]}

    with ui.element("div").classes("max-w-[1100px] mx-auto p-6"):
        # ── Edit mode indicator ──────────────────────────
        if state.edit_mode:
            variant_label = (
                txn_data.get("variant_name") or txn_data.get("variant") or ""
            )
            with ui.row().classes("items-center gap-3 mb-4"):
                ui.label(
                    f"✏️ Editing Transaction #{state.txn_id} {(' — ' + variant_label) if variant_label else ''}"
                ).classes(
                    "bg-amber-100 text-amber-800 border border-amber-200 px-3 py-1 rounded-md text-[12px] font-medium"
                )
                ui.label("All fields pre-filled from saved data").classes(
                    "text-[11px] text-gray-400"
                )

        # ── Form sections ────────────────────────────────
        build_form_sec_vehicle(state)
        build_form_sec_customer(state)
        build_form_sec_conditions(state)
        build_form_sec_prices(state)
        build_form_sec_accessories(state)
        build_form_sec_delivery(state)
        build_form_sec_invoice(state)
        build_form_sec_payment(state)
        build_form_sec_audit(state)
        build_form_sec_live_bar(state)
        build_form_sec_action_bar(state)

        # Ensure button state is correct on first render
        _fs_revalidate(state)

    # ── Prefill after UI is built (edit mode) ───────────
    if state.edit_mode and txn_data:
        await _fs_prefill(state, txn_data)


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════
if __name__ in {"__main__", "__mp_main__"}:
    app.colors(primary="#e8402a")
    ui.run(title="AutoAudit", favicon="🚗", host="0.0.0.0", port=10000, reload=True)
