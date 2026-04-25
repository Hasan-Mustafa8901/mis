"""
Automobile Sales Audit MIS — NiceGUI Frontend  (v3)
Two-page architecture:
  /      → Dashboard + Persistent MIS Transaction Table
  /form  → Data Entry Form (New + Edit mode)

Backend: FastAPI at http://localhost:8000
"""

import re
from utils import build_component_map_from_booking
import httpx
from datetime import date
from collections import defaultdict
import calendar
from nicegui import ui, app

from auth import set_token, get_token, clear_token, protected_page


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
    ("acc_kit", "Genuine Acc Kit"),
    ("fastag", "FasTag"),
    ("ext_warr", "Extended Warranty"),
    ("shield", "Shield Of Trust"),
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
BOOKING_CHECK_KEYS = [
    ("customer_kyc", "Customer KYC"),
    ("vehicle_details", "Vehicle Details"),
    ("price_quotation", "Price Quotation"),
    ("receipts", "Receipts"),
    ("accessories_indent", "Accessories Indent"),
    ("exchange_details", "Exchange Details"),
    ("md_reference", "MD Reference Approval"),
    ("corp_id", "Corp ID"),
    ("customer_sign", "Customer Sign"),
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
        ("variants", "/variants", []),
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
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════
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


def sidebar():
    with ui.column().classes("h-full justify-between w-full p-4 bg-white shadow"):
        with ui.column().classes("mt-auto items-center"):

            def handle_logout():
                clear_token()
                ui.navigate.to("/login")

            ui.button("Logout", on_click=handle_logout).props(
                "color=red outline"
            ).classes("w-full")


# ══════════════════════════════════════════════════════════════
# MIS TABLE RENDERING & HELPER METHODS
# ══════════════════════════════════════════════════════════════
def build_ordered_columns(row: dict, stage: str = "combined"):
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
    if stage == "delivery":
        ordered.append("delivery_date")

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


def render_table(transactions, stage: str = "delivery"):
    """
    Renders the MIS transaction table using AG Grid (ui.aggrid).
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

    ordered_keys = build_ordered_columns(transactions[0], stage=stage)

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
    pin_cols = {
        "id",
        "customer_name",
        "mobile_number",
        "variant_name",
        "booking_date",
        "delivery_date",
    }

    # Define custom widths for specific columns (optional)
    CUSTOM_WIDTHS = {
        "id": 10,
        "customer_name": 100,
        "mobile_number": 100,
        "variant_name": 100,
        "booking_date": 100,
        "delivery_date": 100,
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
                "rowHeight": 30,
                "suppressCellFocus": True,
            },
            theme="balham",
            auto_size_columns=False,
        )
        .classes("w-full h-100")
        .style("font-family:Inter,sans-serif;font-size:13px;")
    )

    async def on_cell_clicked(e):
        row = e.args.get("data", {})
        txn_id = row.get("id")
        if txn_id:
            ui.navigate.to(f"/form?transaction_id={txn_id}&stage={stage}")

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


def open_new_entry_dialog():
    with ui.dialog() as dialog, ui.card().classes("p-6 w-80"):
        ui.label("Create New Entry").classes("text-lg font-bold mb-2")

        ui.button(
            "Booking",
            on_click=lambda: (dialog.close(), ui.navigate.to("/form?stage=booking")),
        ).classes("w-full")

        ui.button(
            "Delivery",
            on_click=lambda: (
                dialog.close(),
                ui.navigate.to("/form?stage=delivery&mode=direct"),
            ),
        ).classes("w-full")

    dialog.open()


# ══════════════════════════════════════════════════════════════
#                        PAGE 1: DASHBOARD
# ══════════════════════════════════════════════════════════════
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
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
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
                    # ════════════════════════════════════════
                    # ROW 1 — KPI CARDS  (pure CSS grid)
                    # ════════════════════════════════════════
                    excess_color = (
                        "#EF4444"
                        if booking_analytics["total_excess"] > 0
                        else "#10B981"
                    )
                    # ── KPI CARDS ──────────────────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Bookings").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")
                        ui.link("View All Bookings", "/booking-mis").classes(
                            "text-[10px] text-primary font-bold uppercase no-underline hover:underline"
                        )

                    with ui.grid(columns=4).classes("w-full gap-4 mb-5"):
                        # KPI Card: Total Transactions
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
                            ui.label(
                                f"₹{booking_analytics['total_actual_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{booking_analytics['avg_actual_discount']:,.0f} / transaction"
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
                            ui.label(
                                f"₹{booking_analytics['total_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{booking_analytics['avg_discount']:,.0f} / transaction"
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
                            ui.label(
                                f"{booking_analytics['ok_cases']} of {booking_analytics['total_entries']} transactions OK"
                            ).classes("text-[14px] text-gray-600")

                with delivery_content_area:
                    # ════════════════════════════════════════
                    # ROW 1 — KPI CARDS  (pure CSS grid)
                    # ════════════════════════════════════════
                    excess_color = (
                        "#EF4444"
                        if delivery_analytics["total_excess"] > 0
                        else "#10B981"
                    )
                    # ── KPI CARDS ──────────────────────────────────
                    with ui.row().classes("w-full items-center gap-2 mb-3 mt-6"):
                        ui.label("Deliveries").classes(
                            "text-[11px] font-bold tracking-[0.8px] uppercase text-gray-500 whitespace-nowrap"
                        )
                        ui.separator().classes("flex-1")
                        ui.link("View All Deliveries", "/delivery-mis").classes(
                            "text-[10px] text-primary font-bold uppercase no-underline hover:underline"
                        )
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
                            ui.label(
                                f"₹{delivery_analytics['total_actual_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{delivery_analytics['avg_actual_discount']:,.0f} / transaction"
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
                            ui.label(
                                f"₹{delivery_analytics['total_discount']:,.0f}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{delivery_analytics['avg_discount']:,.0f} / transaction"
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

                            # KPI Card: Compliance Rate
                            ui.label(
                                f"{delivery_analytics['ok_cases']} of {delivery_analytics['total_entries']} transactions OK"
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
                                delivery_analytics["top_model_sales"],
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
                                delivery_analytics["outlets_sorted_sales"],
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
                                delivery_analytics["top_model_excess"],
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


# ══════════════════════════════════════════════════════════════
#                   PAGE: MIS TABLE
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#                   PAGE: MIS TABLES (Booking & Delivery)
# ══════════════════════════════════════════════════════════════
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

    # Get months for sidebar grouping (from the filtered set)
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

            # Booking link
            is_booking = stage == "booking"
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                f"flex px-4 py-2 text-[12.5px] {'font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A]' if is_booking else 'font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50'} no-underline"
            )

            # Delivery link
            is_delivery = stage == "delivery"
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                f"flex px-4 py-2 text-[12.5px] {'font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A]' if is_delivery else 'font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50'} no-underline"
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


# ══════════════════════════════════════════════════════════════
#                        PAGE 1: SETTINGS
# ══════════════════════════════════════════════════════════════


@ui.page("/settings")
@protected_page
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
        self.booking_id: int | None = None
        self.edit_mode: bool = False
        self.is_direct_delivery: bool = False

        self.stage: str = "booking"  # booking | delivery
        self.mode: str = "booking"  # booking | book-and-delivery
        self.booking_date: ui.input | None = None
        self.delivery_date: ui.input | None = None
        self.booking_amt: ui.input | None = None
        self.booking_receipt_num: ui.input | None = None
        self.booking_data: dict = {}

        # Reference data
        self.cars: list = []
        self.variants: list = []
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
        self.price_diff_labels: dict[str, ui.label] = {}
        self.discount_match_toggles: dict[str, ui.switch] = {}
        self.lbl_total_diff_price: ui.label | None = None
        self.lbl_excess_discount: ui.label | None = None

        self.listed_prices: dict[str, int] = {}
        self.price_listed_labels: dict[str, ui.label] = {}
        self.discount_listed_labels: dict[str, ui.label] = {}

        # Component inputs
        self.price_inputs: dict[str, ui.input] = {}
        self.price_rows: dict[str, ui.row] = {}
        self.discount_inputs: dict[str, ui.input] = {}
        self.discount_rows: dict[str, ui.row] = {}

        # Checkboxes
        self.condition_cbs: dict[str, ui.checkbox] = {}
        self.delivery_cbs: dict[str, ui.checkbox] = {}
        self.booking_cbs: dict[str, ui.checkbox] = {}
        self.overrides = {
            "customer": False,
            "vehicle": False,
            "price": False,
        }

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
        self.lbl_total_listed_price: ui.label | None = None
        self.lbl_total_offered_price: ui.label | None = None
        self.stage_toggle = None
        self.delivery_mode = None
        self.booking_select = None

    @property
    def all_component_inputs(self) -> dict[str, ui.input]:
        return {**self.price_inputs, **self.discount_inputs}

    @property
    def live_discount(self) -> int:
        """Sum of allowed discounts for all currently visible discount rows."""
        total = 0
        if not hasattr(self, "listed_prices") or not self.listed_prices:
            return 0
        for name, row in self.discount_rows.items():
            if row.visible:
                val = self.listed_prices.get(name)
                if val is not None:
                    total += int(val)
        return total

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

        # TR Case condition
        if self.condition_cbs.get("tr_case") and self.condition_cbs["tr_case"].value:
            if not _val(self.cust_other_id):
                return False, "Other ID Proof required for TR Case."

        if not _val(self.cust_file_no):
            return False, "Customer File Number is required."
        if self.stage == "delivery":
            if not _val(self.vin_no):
                return False, "VIN Number is required."

            if not _val(self.engine_no):
                return False, "Engine Number is required."

        year_val = _val(self.model_year)
        if not year_val or not year_val.isdigit():
            return False, "Valid Model Year is required."

        return True, ""


def on_car_change(state, car_id):
    variants = [v for v in state.variants if v["car_id"] == car_id]

    options = {v["id"]: v["variant_name"] for v in variants}

    state.variant_select.options = options


def _map_car_and_variant(state, data):
    car_name = data.get("car_name")
    variant_name = data.get("variant_name")

    # ── STEP 1: Find Car ID ─────────────
    car_id = None
    for car in state.cars:
        if car["name"].strip().lower() == (car_name or "").strip().lower():
            car_id = car["id"]
            break

    if not car_id:
        return

    # ── STEP 2: Set Car ─────────────
    state.car_select.set_value(car_id)
    state.car_id = car_id

    # ── STEP 3: Build Variant Options (CRITICAL) ─────────────
    variants = [v for v in state.variants if v["car_id"] == car_id]

    options = {v["id"]: v["variant_name"] for v in variants}

    # 👉 FORCE update options
    state.variant_select.clear()
    state.variant_select.options = options
    state.variant_select.update()

    # ── STEP 4: Find Variant ID ─────────────
    variant_id = None
    for v in variants:
        if (
            variant_name
            and variant_name.strip().lower() in v["variant_name"].strip().lower()
        ):
            variant_id = v["id"]
            break

    if not variant_id:
        return

    # ── STEP 5: Set Variant ─────────────
    ui.timer(0.05, lambda: state.variant_select.set_value(variant_id), once=True)
    state.variant_id = variant_id


def populate_from_booking(state: FormState, data: dict):

    if not data:
        return

    # ── Booking ──────────────────
    if state.booking_date:
        state.booking_date.set_value(data.get("booking_date", ""))
    if state.booking_amt:
        state.booking_amt.set_value(data.get("booking_amt", ""))
    if state.booking_receipt_num:
        state.booking_receipt_num.set_value(data.get("booking_receipt_num", ""))

    # ── Customer ─────────────────
    if state.cust_name:
        state.cust_name.set_value(data.get("customer_name", ""))

    if state.cust_mobile:
        state.cust_mobile.set_value(data.get("mobile_number", ""))

    if state.cust_email:
        state.cust_email.set_value(data.get("email", ""))

    if state.cust_pan:
        state.cust_pan.set_value(data.get("pan_number", ""))

    if state.cust_aadhar:
        state.cust_aadhar.set_value(data.get("aadhar_number", ""))

    if state.cust_address:
        state.cust_address.set_value(data.get("address", ""))

    if state.cust_city:
        state.cust_city.set_value(data.get("city", ""))

    if state.cust_pincode:
        state.cust_pincode.set_value(data.get("pin_code", ""))

    # ── Vehicle ──────────────────
    if state.cust_file_no:
        state.cust_file_no.set_value(data.get("customer_file_number", ""))

    if state.vin_no:
        state.vin_no.set_value(data.get("vin_number", ""))

    if state.engine_no:
        state.engine_no.set_value(data.get("engine_number", ""))

    if state.vehicle_regn_no:
        state.vehicle_regn_no.set_value(data.get("registration_number", ""))

    if state.regn_date:
        state.regn_date.set_value(data.get("registration_date", ""))

    # ── Variant / Car ────────────
    _map_car_and_variant(state, data)

    # ── Conditions ───────────────
    conditions = data.get("conditions", {})
    for key, cb in state.condition_cbs.items():
        cb.set_value(conditions.get(key, False))

    # ── Trigger recalculation ────
    _fs_update_live(state)
    _fs_revalidate(state)


def populate_price_and_discount(state, booking_data: dict):
    component_map = build_component_map_from_booking(booking_data)

    # Prices
    for name, inp in state.price_inputs.items():
        val = component_map.get(name)

        if val is None:
            norm_name = re.sub(r"[^a-z0-9]", "", name.lower())
            val = component_map.get(norm_name)

        if val is not None:
            inp.set_value(format_num_inr(val))


# ══════════════════════════════════════════════════════════════
# FORM SECTION BUILDERS
# ══════════════════════════════════════════════════════════════
FORM_COLUMNS = 3


def build_vehicle_section(state: FormState) -> None:
    car_opts = {car["id"]: car["name"] for car in state.cars}
    outlet_opts = {outlet["id"]: outlet["name"] for outlet in state.outlets}
    exec_opts = {executive["id"]: executive["name"] for executive in state.executives}

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6 w-full"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🚙").classes("text-[20px] select-none")
            ui.label("Vehicle Details").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
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
            state.model_year = (
                ui.input(label="Model Year *", placeholder="e.g. 2024")
                .classes("w-full")
                .props('outlined dense type="number"')
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            if state.stage == "delivery":
                state.vin_no = (
                    ui.input(label="VIN Number *")
                    .classes("w-full uppercase")
                    .props("outlined dense")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )
                state.delivery_date = (
                    ui.input(
                        label="Delivery Date *",
                    )
                    .classes("w-full")
                    .props('type="date" outlined dense')
                    .on_value_change(
                        lambda _: (
                            _fs_revalidate(state),
                            ui.timer(
                                0, lambda: _fs_try_price_preload(state), once=True
                            ),
                        )
                    )
                )
                state.engine_no = (
                    ui.input(label="Engine Number *")
                    .classes("w-full uppercase")
                    .props("outlined dense")
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


def build_customer_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("👤").classes("text-[20px] select-none")
            ui.label("Customer Details").classes("text-[15px] font-bold text-gray-900")

        # ── Basic Info ─────────────────────────────
        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
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


def build_conditions_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("☑️").classes("text-[20px] select-none")
            ui.label("Sale Conditions").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=FORM_COLUMNS + 2).classes("w-full"):
            for key, label in CONDITION_KEYS:
                state.condition_cbs[key] = (
                    ui.checkbox(label)
                    .props("dense color=primary")
                    .classes("text-gray-700 font-medium")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )


def build_booking_checklist_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("☑️").classes("text-[20px] select-none")
            ui.label("Booking Checklist").classes("text-[15px] font-bold text-gray-900")
        with ui.grid(columns=FORM_COLUMNS + 2).classes("w-full"):
            for key, label in BOOKING_CHECK_KEYS:
                state.booking_cbs[key] = (
                    ui.checkbox(label)
                    .props("dense color=primary")
                    .classes("text-gray-700 font-medium")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )


def build_booking_section(state: FormState):
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📖").classes("text-[20px] select-none")
            ui.label("Booking Details").classes("text-[15px] font-bold text-gray-900")

        # ── Basic Info ─────────────────────────────
        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
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
            state.booking_amt = (
                ui.input(label="Booking Amount*", placeholder="Full name")
                .classes("w-full")
                .props("outlined dense")
            )
            state.booking_receipt_num = (
                ui.input(label="Booking Receipt Number*", placeholder="Full name")
                .classes("w-full")
                .props("outlined dense")
            )


def _build_delivery_prices_section(state: FormState) -> None:
    price_comps = sorted(
        [c for c in state.components if c.get("type") == "price"],
        key=lambda x: x.get("order", 99),
    )

    booking_map = {
        k.replace("_actual", "").strip(): v
        for k, v in (state.booking_data or {}).items()
        if k.endswith("_actual")
    }

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        ui.label("💰 Price Comparison (Booking vs Delivery)").classes(
            "text-[15px] font-bold mb-2"
        )

        if price_comps:
            with ui.column().classes("w-full gap-2"):
                for comp in price_comps:
                    name = comp["name"]

                    with ui.row().classes("w-full items-center h-10 gap-2"):
                        # ── Label
                        ui.label(name).classes("w-52 text-sm")

                        # ── Listed Price
                        listed_label = ui.label("₹—").classes(
                            "w-28 text-gray-500 text-sm"
                        )
                        state.price_listed_labels[name] = listed_label

                        # ── Booking Price (READ ONLY)
                        booking_val = booking_map.get(name)

                        booking_input = (
                            ui.input(
                                value=format_num_inr(booking_val) if booking_val else ""
                            )
                            .props("readonly dense")
                            .classes("w-36")
                        )

                        # ── Toggle (Match Booking)
                        toggle = ui.switch("Same as Booking").props("dense color=green")

                        # ── Delivery Input (editable)
                        inp = accounting_input(
                            "",
                            placeholder="Delivery Price",
                            container_classes="w-36",
                        ).props("dense")

                        state.price_inputs[name] = inp

                        # ── Toggle Logic
                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = booking_map.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)

                            _fs_update_live(state)

                        toggle.on("update:model-value", on_toggle)

                        # Trigger calc
                        inp.on_value_change(lambda _: _fs_update_live(state))

        else:
            ui.label("No price components found").classes("text-xs text-gray-400")


def _build_direct_delivery_prices_section(state: FormState) -> None:
    """
    Price & Discount section for Direct Delivery.
    Shows manual inputs for both prices and discounts.
    """
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
            ui.label("Price & Discounts (Direct Delivery)").classes(
                "text-[15px] font-bold text-gray-900"
            )

        # ── PRICE SECTION ──
        ui.label("Price Charged as per Books of Accounts").classes(
            "text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mt-4"
        )
        ui.separator().classes("mt-0")
        if price_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in price_comps:
                    name = comp["name"]
                    with ui.row().classes("w-full items-center h-10") as row_element:
                        state.price_rows[name] = row_element
                        ui.label(name).classes("w-60 text-sm")
                        listed_label = ui.label("₹—").classes(
                            "w-32 text-gray-500 text-sm"
                        )
                        state.price_listed_labels[name] = listed_label

                        toggle = ui.switch("Match Listed Price").props(
                            'dense icon="check" color="green"'
                        )
                        inp = accounting_input(
                            "",
                            placeholder="Enter Charged Price",
                            container_classes="w-60",
                        ).props("dense")

                        state.price_inputs[name] = inp
                        state.price_match_toggles[name] = toggle

                        diff_label = ui.label("₹0").classes(
                            "w-32 text-gray-500 text-sm ml-2"
                        )
                        state.price_diff_labels[name] = diff_label

                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)
                                inp.set_value(None)
                            _fs_update_live(state)

                        toggle.on("update:model-value", on_toggle)
                        inp.on_value_change(lambda _: _fs_update_live(state))

        # ── DISCOUNT SECTION ──
        ui.label("Discounts Allowed as per Books of Accounts").classes(
            "text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mt-6"
        )
        ui.separator().classes("mt-0")
        if discount_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in discount_comps:
                    name = comp["name"]

                    # Default visible rows
                    is_default = name in [
                        "Cash Discount All Customers",
                        "Additional Discount From Dealer",
                        "Maximum benefit due to price increase",
                    ]

                    with ui.row().classes("w-full items-center h-10") as row_element:
                        state.discount_rows[name] = row_element
                        row_element.set_visibility(is_default)

                        ui.label(name).classes("w-60 text-sm")
                        listed_label = ui.label("₹—").classes(
                            "w-32 text-gray-500 text-sm"
                        )
                        state.discount_listed_labels[name] = listed_label

                        toggle = ui.switch("Match Listed Discount").props(
                            'dense icon="check" color="green"'
                        )
                        inp = accounting_input(
                            "",
                            placeholder="Enter Discount",
                            container_classes="w-60",
                        ).props("dense")

                        state.discount_inputs[name] = inp
                        state.discount_match_toggles[name] = toggle

                        def on_toggle_disc(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)
                                inp.set_value(None)
                            _fs_update_live(state)

                        toggle.on("update:model-value", on_toggle_disc)
                        inp.on_value_change(lambda _: _fs_update_live(state))

        # ── SUMMARY LABELS ──
        with ui.grid(columns=1).classes("w-full align-center mt-4 pt-4 border-t"):
            with ui.row().classes("w-full items-center h-10"):
                ui.label("Totals").classes(
                    "text-lg font-bold tracking-[0.9px] uppercase"
                )
                state.lbl_total_listed_price = ui.label("₹—").classes("w-32 text-lg")
                state.lbl_total_offered_price = ui.label("₹—").classes("w-32 text-lg")
                state.lbl_total_diff_price = ui.label("₹—").classes("w-32 text-lg ml-2")
                state.lbl_excess_discount = ui.label("₹0").classes(
                    "ml-auto text-lg font-bold"
                )


def _build_booking_prices_section(state: FormState) -> None:
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

                    with ui.row().classes("w-full items-center h-10") as row_element:
                        state.price_rows[name] = row_element
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

                        diff_label = ui.label("₹0").classes(
                            "w-32 text-gray-500 text-sm ml-2"
                        )
                        state.price_diff_labels[name] = diff_label

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
        with ui.grid(columns=1).classes("w-full align-center"):
            with ui.row().classes("w-full items-center h-10"):
                ui.label("Total On-Road Price").classes(
                    "text-lg font-bold tracking-[0.9px] uppercase mb-1 mt-1 pt-1"
                )
                total_listed_price = ui.label("₹—").classes("w-32 text-lg")
                total_offered_price = ui.label("₹—").classes("w-32 text-lg")
                total_diff_price = ui.label("₹—").classes("w-32 text-lg ml-2")
                state.lbl_total_listed_price = total_listed_price
                state.lbl_total_offered_price = total_offered_price
                state.lbl_total_diff_price = total_diff_price

        ui.label("Discounts Offered as per Books of Accounts").classes(
            "text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mb-1 mt-1 pt-1"
        )
        ui.separator().classes("mt-0 my-2")
        with ui.row().classes("w-full items-center pt-2 border-t border-gray-100"):
            ui.label("Total Discount as per booking file").classes(
                "text-sm font-bold tracking-[0.9px]"
            )
            state.total_discount_input = accounting_input(
                label_text="",
                placeholder="₹0",
                container_classes="w-60",
            )
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
                        state.discount_rows[name] = row_element

                # ── Excess Discount Row ─────────────────────────────
                with ui.row().classes(
                    "w-full items-center h-12 mt-2 pt-2 border-t border-gray-100"
                ):
                    ui.label("Adjustments").classes(
                        "w-60 text-lg font-bold tracking-[0.9px] uppercase"
                    )
                    with ui.button_group().classes("ml-auto"):
                        ui.button().props("dense color=primary icon=add")
                        ui.button().props("dense color=primary icon=remove")

                    state.addjustment_input = accounting_input(
                        label_text="",
                        placeholder="₹0",
                        container_classes="w-60",
                    )
                    ui.label("Excess Discount").classes(
                        "w-60 text-lg font-bold tracking-[0.9px] uppercase"
                    )
                    # Placeholder for the spacing matching the listed_label above
                    ui.label("").classes("w-32")

                    state.lbl_excess_discount = ui.label("₹0").classes(
                        "text-lg font-bold ml-2"
                    )

        else:
            ui.label("No discount components — check /components endpoint.").classes(
                "text-xs text-gray-400"
            )


def build_prices_section(state: FormState) -> None:
    if state.stage == "delivery":
        if state.is_direct_delivery:
            _build_direct_delivery_prices_section(state)
        else:
            _build_delivery_prices_section(state)
    else:
        _build_booking_prices_section(state)


def build_accessories_section(state: FormState) -> None:
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


def build_delivery_section(state: FormState) -> None:
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


def build_audit_section(state: FormState) -> None:
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


def build_invoice_section(state: FormState) -> None:
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


def build_payment_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("💳").classes("text-[20px] select-none")
            ui.label("Payment Received").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=FORM_COLUMNS + 1).classes("w-full gap-2 items-start"):
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


def build_live_bar(state: FormState) -> None:
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


def build_action_bar(state: FormState) -> None:
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
    # Extract booking date from available sources
    booking_date = None
    if state.booking_date and state.booking_date.value:
        booking_date = state.booking_date.value
    elif state.delivery_date and state.delivery_date.value:
        booking_date = state.delivery_date.value

    if not state.variant_id or not booking_date:
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
    total_comp_discount = 0
    if state.stage == "delivery" and state.is_direct_delivery:
        # Sum manual inputs
        for name, inp in state.discount_inputs.items():
            row = state.discount_rows.get(name)
            if row and row.visible:
                total_comp_discount += int(parsed_val(inp))
    else:
        # Use automated property
        total_comp_discount = state.live_discount

    if (
        state.invoice_discount
        and parsed_val(state.invoice_discount) != total_comp_discount
    ):
        state.invoice_discount.set_value(format_num_inr(total_comp_discount))

    # 3. Read current values for labels
    allowed_discount = state.live_discount

    # Discount Given (Actual)
    discount_given = total_comp_discount

    # 4. Update Labels
    if hasattr(state, "lbl_allowed") and state.lbl_allowed:
        state.lbl_allowed.set_text(f"₹{allowed_discount:,.0f}")

    if state.lbl_discount:
        state.lbl_discount.set_text(f"₹{discount_given:,.0f}")

    # Excess Discount = Actual Discount - Allowed Discount
    excess = discount_given - allowed_discount
    if state.lbl_excess:
        state.lbl_excess.set_text(f"₹{excess:,.0f}")
        # Color coding: Green if actual <= allowed (good), Red if actual > allowed (bad)
        if excess <= 0:
            state.lbl_excess.style("color:#6EE7B7")  # Soft green
        else:
            state.lbl_excess.style("color:#F87171")  # Soft red

    # 5. Update Total Price Labels (Sum of Prices section)
    total_listed = 0
    total_offered = 0
    for name, inp in state.price_inputs.items():
        # Skip if row is hidden
        row = state.price_rows.get(name)
        if row is not None and not row.visible:
            diff_label = state.price_diff_labels.get(name)
            if diff_label:
                diff_label.set_text("")
            continue

        toggle = state.price_match_toggles.get(name)
        is_toggled = toggle.value if toggle else False
        is_entered = bool(inp.value and str(inp.value).strip())

        # Sum listed price ONLY IF toggled or entered
        if is_toggled or is_entered:
            listed_price = int(state.listed_prices.get(name) or 0)
            total_listed += listed_price
        else:
            listed_price = 0

        # Sum offered price (from input)
        offered_price = 0
        try:
            offered_price = int(float(str(parsed_val(inp)).replace(",", "") or 0))
        except:
            pass
        total_offered += offered_price

        # Update Difference Label
        diff_label = state.price_diff_labels.get(name)
        if diff_label:
            if not is_toggled and not is_entered:
                diff_label.set_text("")
                diff_label.style("color: #9CA3AF")
            else:
                diff = listed_price - offered_price
                if diff > 0:
                    diff_label.set_text(f"₹{diff:,.2f}")
                    diff_label.style("color: #D41717")
                elif diff < 0:
                    diff_label.set_text("₹ 0")
                    diff_label.style("color: #1CC722")
                else:
                    diff_label.set_text("₹0")
                    diff_label.style("color: #9CA3AF")

    total_diff = total_listed - total_offered

    if state.lbl_total_listed_price:
        state.lbl_total_listed_price.set_text(f"₹{total_listed:,.2f}")
    if state.lbl_total_offered_price:
        state.lbl_total_offered_price.set_text(f"₹{total_offered:,.2f}")
    if state.lbl_total_diff_price:
        if total_diff > 0:
            state.lbl_total_diff_price.set_text(f"₹{abs(total_diff):,.2f}")
            state.lbl_total_diff_price.style("color: #D41717")
        elif total_diff < 0:
            state.lbl_total_diff_price.set_text(f"-₹{total_diff:,.2f}")
            state.lbl_total_diff_price.style("color: #1CC722")
        else:
            state.lbl_total_diff_price.set_text("₹0")
            state.lbl_total_diff_price.style("color: #9CA3AF")

    # ── Excess Discount Calculation ─────────────────
    # Formula: max(0, total_diff - allowed_discount)
    if hasattr(state, "lbl_excess_discount") and state.lbl_excess_discount:
        # Recalculate allowed discount directly to be safe
        current_allowed = 0
        if hasattr(state, "listed_prices") and state.listed_prices:
            for name, row in state.discount_rows.items():
                if row.visible:
                    val = state.listed_prices.get(name)
                    if val is not None:
                        current_allowed += int(val)

        excess_val = total_diff - current_allowed
        if excess_val < 0:
            excess_val = 0

        state.lbl_excess_discount.set_text(f"₹{excess_val:,.2f}")
        if excess_val > 0:
            state.lbl_excess_discount.style("color: #D41717")  # Red
        else:
            state.lbl_excess_discount.style("color: #9CA3AF")  # Gray


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

    discount_visibility_rules = {
        norm("Extra Kitty On TR cases"): is_checked("tr_case"),
        norm("Additional For POI /Corporate Customers"): is_checked("corporate")
        or is_checked("govt_employee"),
        norm("Additional For Exchange Customers"): is_checked("exchange"),
        norm("Additional For Scrappage Customers"): is_checked("scrap"),
        norm("Additional For Upward Sales Customers"): is_checked("upgrade"),
    }

    price_visibility_rules = {
        norm("Accessories"): is_checked("acc_kit"),
        norm("FasTag"): is_checked("fastag"),
        norm("Extended Warranty"): is_checked("ext_warr"),
        norm("Shield Of Trust"): is_checked("shield"),
        norm("Insurance (With Depreciation Cover)"): not is_checked("self_insurance"),
        norm("Insurance"): not is_checked("self_insurance"),
    }

    for name, row in state.discount_rows.items():
        n_name = norm(name)
        if n_name in discount_visibility_rules:
            row.set_visibility(discount_visibility_rules[n_name])

    for name, row in state.price_rows.items():
        n_name = norm(name)
        if n_name in price_visibility_rules:
            row.set_visibility(price_visibility_rules[n_name])

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
        if state.stage == "delivery":
            if state.txn_id:
                await api_put(f"/transactions/{state.txn_id}", payload)
                ui.notify("Delivery Data saved", color="green", type="positive")
            else:
                await api_post("/transactions", payload)
                ui.notify(
                    "Delivery Created Successfully", color="green", type="positive"
                )
        else:
            await api_post("/transactions", payload)
            ui.notify("Booking Created Successfully", color="green", type="positive")

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
        row = state.price_rows.get(name)
        if row is not None and not row.visible:
            actual_amounts[name] = 0
        else:
            actual_amounts[name] = intval(inp)

    # Discount components
    for name, row in state.discount_rows.items():
        if row.visible:
            if state.stage == "delivery" and state.is_direct_delivery:
                actual_amounts[name] = intval(state.discount_inputs.get(name))
            else:
                actual_amounts[name] = state.listed_prices.get(name, 0)
        else:
            actual_amounts[name] = 0

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
        "booking_amt": val(state.booking_amt),
        "booking_receipt_num": val(state.booking_receipt_num),
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
    if state.stage == "booking":
        payload["stage"] = "booking"
        payload["booking_checklist"] = {
            k: v.value for k, v in state.booking_cbs.items()
        }

    elif state.stage == "delivery":
        payload["stage"] = "delivery"
        payload["booking_id"] = state.booking_id
        payload["delivery_date"] = val(state.delivery_date)
        payload["is_direct_delivery"] = state.is_direct_delivery
        payload["overrides"] = state.overrides

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

    # Actual amounts → fill price
    amounts = txn.get("actual_amounts", {})
    for name, inp in state.price_inputs.items():
        if name in amounts:
            inp.set_value(amounts[name])
            if amounts[name] > 0 and name in state.price_match_toggles:
                state.price_match_toggles[name].set_value(True)

    # Accessories
    acc_details = txn.get("accessories_details", {})
    if state.acc_select:
        # Reconstruct selected IDs from transaction (backend 'accessories' key holds list of objects)
        selected_ids = [acc["id"] for acc in txn.get("accessories", [])]
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


# TODO: for booking MIS form the vehicle details will not include the vin, engine details. and add fuel type to the form.
# ══════════════════════════════════════════════════════════════
#   PAGE 2: FORM
# ══════════════════════════════════════════════════════════════
@protected_page
@ui.page("/form")
async def form_page(
    stage: str = "booking", mode: str = "booking", transaction_id: int | None = None
) -> None:
    state = FormState()

    state.stage = stage
    state.mode = mode
    state.txn_id = transaction_id
    state.is_direct_delivery = mode == "direct"

    txn_data = None

    if transaction_id and stage == "delivery":
        state.booking_id = transaction_id
        state.edit_mode = True

        try:
            txn_data = await api_get(f"/transactions/{transaction_id}")
            state.booking_data = txn_data
        except Exception:
            ui.notify("Failed to load booking data", type="negative")

    # Detect edit mode from query param
    if state.booking_id:
        pass

    # Breadcrumb label
    bc = f"Edit Entry #{state.txn_id}" if state.edit_mode else "New Entry"
    render_topbar(bc)

    # Fetch reference data
    ref = await fetch_reference_data()
    state.cars = ref["cars"]
    state.variants = ref["variants"]
    state.components = ref["components"]
    state.outlets = ref["outlets"]
    state.executives = ref["executives"]
    state.accessory_map = {acc["id"]: acc for acc in ref["accessories"]}

    with ui.element("div").classes("max-w-[1200px] mx-auto p-6"):
        # ── Edit mode indicator ──────────────────────────
        if state.edit_mode:
            variant_label = (
                txn_data.get("variant_name") or txn_data.get("variant") or ""
            )
            with ui.row().classes("items-center gap-3 mb-4"):
                ui.label(
                    f"✏️ Editing Booking #{state.txn_id} {(' — ' + variant_label) if variant_label else ''}"
                ).classes(
                    "bg-amber-100 text-amber-800 border border-amber-200 px-3 py-1 rounded-md text-[12px] font-medium"
                )
                ui.label("All fields pre-filled from saved data").classes(
                    "text-[11px] text-gray-400"
                )

        # ── Form sections ────────────────────────────────
        if state.stage == "booking":
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Booking MIS Form").classes("text-2xl text-bold mb-5")

                ui.checkbox("Is File Incomplete?").classes("text-bold ml-auto")
            build_vehicle_section(state)
            build_booking_section(state)
            build_customer_section(state)
            build_conditions_section(state)
            build_prices_section(state)
            build_accessories_section(state)
            build_booking_checklist_section(state)

        elif state.stage == "delivery":
            ui.label("Delivery MIS Form").classes("text-2xl text-bold mb-5")

            if state.booking_id:
                ...

            build_vehicle_section(state)
            build_booking_section(state)
            build_customer_section(state)
            build_conditions_section(state)
            build_prices_section(state)
            build_accessories_section(state)
            build_delivery_section(state)
            build_invoice_section(state)
            build_payment_section(state)
            build_audit_section(state)

        build_live_bar(state)
        build_action_bar(state)

        # Ensure button state is correct on first render
        _fs_revalidate(state)

    # ── Prefill after UI is built (edit mode) ───────────
    if state.booking_id and state.stage == "delivery":
        populate_from_booking(state, state.booking_data)
    elif state.edit_mode and txn_data:
        await _fs_prefill(state, txn_data)


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════
if __name__ in {"__main__", "__mp_main__"}:
    app.colors(primary="#e8402a")
    ui.run(
        title="AutoAudit",
        favicon="🚗",
        host="0.0.0.0",
        storage_secret="super-secret-key",
        port=3000,
        reload=True,
    )
