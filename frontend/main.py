"""
Automobile Sales Audit MIS — NiceGUI Frontend  (v3)
Two-page architecture:
  /      → Dashboard + Persistent MIS Transaction Table
  /form  → Data Entry Form (New + Edit mode)

Backend: FastAPI at http://localhost:8000
"""

import asyncio
import re
from utils_old import build_component_map_from_booking
import httpx
from datetime import datetime, date, timedelta
from collections import defaultdict
import calendar
from nicegui import ui, app
from utils_old import get_ist_today, disp_date, date_for_input
from dotenv import load_dotenv

import os
from auth_old import get_token, clear_user, protected_page, set_user


# ══════════════════════════════════════════════════════════════
# CONFIG & SHARED CONSTANTS
# ══════════════════════════════════════════════════════════════
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
BASE_URL = os.getenv("API_URL", "http://localhost:8000")

CONDITION_KEYS = [
    ("exchange", "Exchange"),
    ("corporate", "Corporate"),
    ("govt_employee", "Govt Employee"),
    ("scrap", "Scrap"),
    ("upgrade", "Upgrade"),
    ("self_insurance", "Self Insurance"),
    # ("tr_case", "TR Case"),
    ("tcs", "TCS"),
    ("green_bonus", "Green Bonus"),
    ("acc_kit", "Accessories"),
    ("fastag", "FasTag"),
    ("ext_warr", "Extended Warranty"),
    ("amc", "AMC"),
    ("loyalty_ev_ev", "Additional Loyalty (EV TO EV)"),
    ("loyalty_ice_ev", "Additional Loyalty (ICE TO EV)"),
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

# date_regex = re.compile(r"^(0[1-9]|[12][0-9]|3[01])\-(0[1-9]|1[0-2])\-\d{4}$")
vin_regex = re.compile(r"^[A-HJ-NPR-Z0-9]{13}[0-9]{4}$")
regn_regex = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$")
bharat_regex = re.compile(r"^\d{2}BH\d{4}[A-Z]{2}$")


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
def get_auth_headers():
    token = app.storage.user.get("token")  # adjust if stored differently
    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def api_get(path: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE_URL}{path}", headers=get_auth_headers(), timeout=10
        )
        r.raise_for_status()
        return r.json()


async def api_post(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}{path}", json=payload, headers=get_auth_headers(), timeout=10
        )
        if r.status_code == 422:
            print("422 ERROR: ", r.json())  # debug help
        r.raise_for_status()
        return r.json()


# async def api_post_file(path: str, file, data: dict):
#     token = app.storage.user.get("token")
#     headers = {}
#     if token:
#         headers["Authorization"] = f"Bearer {token}"


#     async with httpx.AsyncClient() as client:
#         r = await client.post(
#             f"{BASE_URL}{path}",
#             files={"file": (file.name, await file.content.read())},
#             data=data,
#             headers=headers,
#             timeout=20,
#         )
#         r.raise_for_status()
#         return r.json()


async def api_post_file(path: str, file, data: dict):
    token = app.storage.user.get("token")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    name = file.file.name
    content = await file.file.read()

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}{path}",
            files={
                "file": (name, content)  # ✅ no await
            },
            data=data,
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()


async def api_put(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{BASE_URL}{path}", json=payload, headers=get_auth_headers(), timeout=10
        )
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
    tasks = {
        "cars": api_get("/cars"),
        "variants": api_get("/variants"),
        "outlets": api_get("/outlets"),
        "executives": api_get("/sales-executives"),
        "accessories": api_get("/accessories"),
        "dealerships": api_get("/complaints/dealerships"),
        "components": api_get("/components"),
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    final = {}
    for (key, _), result in zip(tasks.items(), results):
        if isinstance(results, Exception):
            final[key] = []
        else:
            final[key] = result
    return final
    # for key, path, fallback in [
    #     ("cars", "/cars", []),
    #     ("variants", "/variants", []),
    #     ("components", "/components", []),
    #     ("outlets", "/outlets", [{"id": 1, "name": "Main Outlet"}]),
    #     ("executives", "/sales-executives", [{"id": 1, "name": "Default SE"}]),
    #     ("accessories", "/accessories", []),
    #     ("dealerships", "/complaints/dealerships", []),
    # ]:
    #     try:
    #         result[key] = await api_get(path)
    #     except Exception:
    #         result[key] = fallback

    # return result


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


def get_user():
    return {
        "name": app.storage.user.get("name"),
        "role": app.storage.user.get("role"),
        "outlet_id": app.storage.user.get("outlet_id"),
    }


def is_valid_date(v: str) -> bool:
    try:
        datetime.strptime(v, "%Y-%m-%d")
        return True
    except:
        return False


# ══════════════════════════════════════════════════════════════
# TOPBAR  (shared component for both pages)
# ══════════════════════════════════════════════════════════════
def render_topbar(page_label: str) -> None:
    """Injects sticky top header. page_label is shown as breadcrumb."""
    # user = app.storage.user.get("user")
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
            role = user.get("role") or []
            role_d = ", ".join(role) if role else "-"
            # Avatar (initial)
            with ui.element("div").classes(
                "w-8 h-8 rounded-full bg-[#E8402A] flex items-center justify-center text-white font-bold text-sm shadow"
            ):
                initials = "".join([word[0].upper() for word in name.split()])
                ui.label(initials if len(initials) <= 3 else initials[:2])

            # User details
            with ui.column().classes("gap-0"):
                ui.label(name).classes(
                    "text-[12.5px] text-white font-semibold leading-tight"
                )
                ui.label(f"{role_d.title()} • {user.get('showroom', '-')}").classes(
                    "text-[10px] text-white tracking-wide leading-none"
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

                    set_user(data)

                    ui.notify("Login successful", type="positive")
                    ui.navigate.to("/")

                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 401:
                        ui.notify("Invalid Credentials", type="negative")
                    elif exc.response.status_code == 404:
                        ui.notify("Not Found", type="negative")

                except httpx.ConnectError as exc:
                    # log this exc error
                    ui.notify(
                        str(exc),
                        type="negative",
                    )

            ui.button("Login", on_click=handle_login).classes("w-full rounded-md")


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


def render_table(transactions, stage: str = "booking"):
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
    # Add derived column

    for t in transactions:
        t["Delivered"] = "Yes" if t.get("stage") == "delivery" else "No"

    ordered_keys = build_ordered_columns(transactions[0], stage=stage)

    if "Delivered" not in ordered_keys:
        ordered_keys.insert(6, "Delivered")

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
        "Delivered",
    }

    # Define custom widths for specific columns (optional)
    CUSTOM_WIDTHS = {
        "id": 10,
        "customer_name": 100,
        "mobile_number": 100,
        "variant_name": 100,
        "booking_date": 100,
        "delivery_date": 100,
        "Delivered": 90,
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

    def create_dialog(txn_id):
        with ui.dialog() as dialog, ui.card().classes("p-6 w-80"):
            ui.label("Update Entry").classes("text-lg font-bold mb-2")

            ui.button(
                "Edit this Entry",
                on_click=lambda: (
                    dialog.close(),
                    ui.navigate.to(f"/form?transaction_id={txn_id}&stage=booking"),
                ),
            ).classes("w-full")

            ui.button(
                "Delivered",
                on_click=lambda: (
                    dialog.close(),
                    ui.navigate.to(f"/form?transaction_id={txn_id}&stage=delivery"),
                ),
            ).classes("w-full")

            ui.button(
                "Make A Complaint",
                on_click=lambda: (
                    dialog.close(),
                    ui.notify("Complaint feature coming soon!", type="info"),
                ),
            ).classes("w-full")

        dialog.open()

    async def on_cell_clicked(e):
        row = e.args.get("data", {})
        txn_id = row.get("id")
        if txn_id and stage == "booking":
            create_dialog(txn_id)
        if txn_id and stage == "delivery":
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
    for txn in all_transactions:
        booking_date = txn.get("booking_date", "")
        if booking_date and len(booking_date) >= 7:
            all_month_map[booking_date[:7]].append(txn)
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
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent no-underline"
            )
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📑 Complaints Control Panel", "/complaints-ctrl").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )

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
            with ui.column().classes(
                "h-full justify-between w-full p-4 bg-white shadow"
            ):
                with ui.column().classes("mt-auto items-center"):

                    def handle_logout():
                        clear_user()
                        ui.navigate.to("/login")

                    ui.button("Logout", on_click=handle_logout).props(
                        "color=red outline"
                    ).classes("w-full")

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
                                ui.label("Top Excess Deliveries").classes(
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
        transactions = all_transactions
    else:
        transactions = [t for t in all_transactions if t.get("delivery_date")]

    # # Split logic
    # if stage == "booking":
    #     transactions = [t for t in all_transactions if t.get("stage") == "booking"]
    # else:
    #     transactions = [t for t in all_transactions if t.get("stage") == "delivery"]

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
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
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
            ui.link("📑 Complaints Control Panel", "/complaints-ctrl").classes(
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
#                    COMPLAINTS TABLE RENDERER
# ══════════════════════════════════════════════════════════════
def render_complaints_table(complaints):
    """
    Renders the Complaints table using AG Grid.
    """
    if not complaints:
        with ui.card().classes("w-full").style("padding:48px;text-align:center"):
            ui.label("📭").style("font-size:36px")
            ui.label("No complaints yet").style(
                "font-size:14px;font-weight:500;color:#6B7280;margin-top:8px"
            )
            return

    # Define columns for complaints table
    col_defs = [
        # ─────────────────────────────
        # Core Info
        # ─────────────────────────────
        {
            "field": "complaint_code",
            "headerName": "Complaint Code",
            "pinned": "left",
            "width": 130,
            "checkboxSelection": True,
        },
        {
            "field": "date_of_complaint",
            "headerName": "Complaint Date",
            "width": 140,
            ":valueFormatter": "params.value ? new Date(params.value).toLocaleDateString() : '—'",
        },
        {
            "field": "status",
            "headerName": "Status",
            "width": 130,
            ":cellStyle": (
                "params.value === 'ESCALATED'"
                " ? {background:'#FEE2E2', color:'#991B1B', fontWeight:'600'}"
                " : {background:'#D1FAE5', color:'#065F46', fontWeight:'600'}"
            ),
        },
        # ─────────────────────────────
        # Customer Details
        # ─────────────────────────────
        {"field": "customer_name", "headerName": "Customer Name", "width": 160},
        {"field": "customer_mobile", "headerName": "Mobile", "width": 130},
        {"field": "customer_address", "headerName": "Address", "width": 180},
        {"field": "customer_city", "headerName": "City", "width": 120},
        {"field": "customer_pin", "headerName": "PIN", "width": 100},
        {"field": "customer_aadhar", "headerName": "Aadhar", "width": 150},
        {"field": "customer_pan", "headerName": "PAN", "width": 130},
        # ─────────────────────────────
        # Vehicle
        # ─────────────────────────────
        {"field": "car_name", "headerName": "Car Model", "width": 150},
        {"field": "variant_name", "headerName": "Variant", "width": 200},
        # ─────────────────────────────
        # Dealership Info
        # ─────────────────────────────
        {
            "field": "complainant_dealer_name",
            "headerName": "Complainant Dealer",
            "width": 180,
        },
        {
            "field": "complainant_showroom_name",
            "headerName": "Complainant Showroom",
            "width": 180,
        },
        {
            "field": "complainee_dealer_name",
            "headerName": "Complainee Dealer",
            "width": 180,
        },
        {
            "field": "complainee_showroom_name",
            "headerName": "Complainee Showroom",
            "width": 180,
        },
        # ─────────────────────────────
        # Quotation
        # ─────────────────────────────
        {"field": "quotation_number", "headerName": "Quotation No", "width": 150},
        {
            "field": "quotation_date",
            "headerName": "Quotation Date",
            "width": 140,
            ":valueFormatter": "params.value ? new Date(params.value).toLocaleDateString() : '—'",
        },
        {
            "field": "tcs_amount",
            "headerName": "TCS",
            "width": 120,
            ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        },
        {
            "field": "total_offered_price",
            "headerName": "Total Offered",
            "width": 140,
            ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        },
        {
            "field": "net_offered_price",
            "headerName": "Net Offered",
            "width": 140,
            ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        },
        # ─────────────────────────────
        # Booking
        # ─────────────────────────────
        {"field": "booking_file_number", "headerName": "File No", "width": 140},
        {"field": "receipt_number", "headerName": "Receipt No", "width": 140},
        {
            "field": "booking_amount",
            "headerName": "Booking Amount",
            "width": 140,
            ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        },
        {"field": "mode_of_payment", "headerName": "Payment Mode", "width": 130},
        {
            "field": "instrument_date",
            "headerName": "Instrument Date",
            "width": 140,
            ":valueFormatter": "params.value ? new Date(params.value).toLocaleDateString() : '—'",
        },
        {"field": "instrument_number", "headerName": "Instrument No", "width": 150},
        {"field": "bank_name", "headerName": "Bank", "width": 150},
        # ─────────────────────────────
        # Pricing
        # ─────────────────────────────
        # {
        #     "field": "ex_showroom_price",
        #     "headerName": "Ex-Showroom",
        #     "width": 140,
        #     ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        # },
        # {
        #     "field": "insurance",
        #     "headerName": "Insurance",
        #     "width": 130,
        #     ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        # },
        # {
        #     "field": "registration_road_tax",
        #     "headerName": "Reg/Road Tax",
        #     "width": 140,
        #     ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        # },
        # {
        #     "field": "discount",
        #     "headerName": "Discount",
        #     "width": 120,
        #     ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        # },
        # {
        #     "field": "accessories_charged",
        #     "headerName": "Accessories",
        #     "width": 140,
        #     ":valueFormatter": "params.value != null ? Math.floor(params.value).toLocaleString() : '—'",
        # },
        # ─────────────────────────────
        # Remarks
        # ─────────────────────────────
        {
            "field": "remarks_complainant",
            "headerName": "Complainant Remarks",
            "width": 220,
        },
        {"field": "remark_complainee_aa", "headerName": "AA Remarks", "width": 220},
        {"field": "remark_admin", "headerName": "Admin Remarks", "width": 220},
    ]

    grid = (
        ui.aggrid(
            {
                "columnDefs": col_defs,
                "rowData": complaints,
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
        complaint_code = row.get("complaint_code")
        if complaint_code:
            ui.navigate.to(f"/complaint-form?complaint_code={complaint_code}")

    grid.on("cellClicked", on_cell_clicked)

    return grid


# ══════════════════════════════════════════════════════════════
#                    PAGE: COMPLAINTS TABLE
# ══════════════════════════════════════════════════════════════
@ui.page("/complaints-ctrl")
@protected_page
async def complaints_ctrl_page():

    render_topbar("Complaints Control Panel")

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
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
            )
            ui.link("📊 Dashboard", "/").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent no-underline"
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
            ui.link("📑 Complaints Control Panel", "/complaints-ctrl").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )

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
            with ui.column().classes(
                "h-full justify-between w-full p-4 bg-white shadow"
            ):
                with ui.column().classes("mt-auto items-center"):

                    def handle_logout():
                        clear_user()
                        ui.navigate.to("/login")

                    ui.button("Logout", on_click=handle_logout).props(
                        "color=red outline"
                    ).classes("w-full")

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
                grid = render_complaints_table(complaints)

                async def get_selected_row():
                    rows = await grid.get_selected_rows()  # type: ignore
                    return rows[0] if rows else None

            with ui.card().classes("w-full p-5 shadow-sm rounded-xl"):
                ui.label("Actions Panel").classes("text-lg font-bold mb-4")
                # ─────────────────────────────
                # STATUS
                # ─────────────────────────────
                try:
                    status_resp = await api_get("/complaints/statuses")
                    status_options_raw = status_resp.get("data", [])
                except Exception:
                    status_options_raw = []

                status_options = {
                    item["value"]: item["label"].replace("_", " ").title()
                    for item in status_options_raw
                }
                status_select = (
                    ui.select(
                        options=status_options,
                        label="Change Status",
                    )
                    .props("outlined dense")
                    .classes("w-64")
                )

                async def update_status():
                    row = await get_selected_row()

                    if not row:
                        ui.notify("Select a complaint first", type="warning")
                        return

                    await api_post(
                        "/complaints/update-status",
                        {
                            "complaint_code": row["complaint_code"],
                            "status": status_select.value,
                        },
                    )

                    ui.notify("Status updated", type="positive")

                ui.button("Update Status", on_click=update_status).classes(
                    "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
                ).props("no-caps unelevated")

                # ─────────────────────────────
                # REMARKS
                # ─────────────────────────────
                remarks_input = (
                    ui.textarea(label="Add Remarks")
                    .props("outlined dense")
                    .classes("w-full")
                )

                async def submit_remarks():
                    row = await get_selected_row()

                    if not row:
                        ui.notify("Select a complaint first", type="warning")
                        return

                    await api_post(
                        "/complaints/remarks",
                        {
                            "code": row["complaint_code"],
                            "remark": remarks_input.value,
                            "submitted_by": "admin",
                        },
                    )

                    remarks_input.set_value("")
                    ui.notify("Remarks added", type="positive")

                ui.button("Submit Remarks", on_click=submit_remarks).classes(
                    "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
                ).props("no-caps unelevated")

                # ─────────────────────────────
                # FLAG
                # ─────────────────────────────
                try:
                    flag_resp = await api_get("/complaints/flags")
                    flag_options_raw = flag_resp.get("data", [])
                except Exception:
                    flag_options_raw = []

                flag_options = {
                    item["value"]: item["label"].replace("_", " ").title()
                    for item in flag_options_raw
                }

                flag_select = (
                    ui.select(
                        options=flag_options,
                        label="Set Flag",
                    )
                    .props("outlined dense")
                    .classes("w-64")
                )

                async def update_flag():
                    row = await get_selected_row()

                    if not row:
                        ui.notify("Select a complaint first", type="warning")
                        return

                    await api_post(
                        "/complaints/update-flag",
                        {
                            "complaint_code": row["complaint_code"],
                            "flag": flag_select.value,
                        },
                    )

                    ui.notify("Flag updated", type="positive")

                ui.button("Update Flag", on_click=update_flag).classes(
                    "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
                ).props("no-caps unelevated")


class ReportingState:
    def __init__(self):
        self.row_data: dict = {}  # (tt, date) → {total_count, files_received, file_incomplete, files_in_mis}
        self.dialog_data: dict = {}  # (tt, date, col) → [{date, name, pan, remarks}, …]
        self.label_refs: dict = {}  # (tt, date, col) → ui.label  for computed cells
        self.total_refs: dict = {}  # (tt, col) → ui.label  for footer totals
        self.locked_dates: set = (
            set()
        )  # this keeps the user from reentring from on a already done date


# ══════════════════════════════════════════════════════════════
#                   PAGE: DAILY REPORTING
# ══════════════════════════════════════════════════════════════


@ui.page("/daily-reporting")
@protected_page
async def daily_reporting_page() -> None:
    rstate = ReportingState()
    render_topbar("Daily Reporting")

    # ── Transactions ─────────────────────────────────────────
    try:
        all_transactions: list = await api_get("/transactions")
    except Exception:
        all_transactions = []

    async def save_reporting():
        payload = build_reporting_payload(rstate)

        try:
            await api_post("/daily-report/", payload)

            # ✅ lock all submitted dates
            for _, d in rstate.row_data.keys():
                rstate.locked_dates.add(d)

            ui.notify("Saved successfully", type="positive")

            # refresh UI
            _rebuild(_get_current_range(), from_inp.value, to_inp.value)

        except Exception as e:
            print(str(e))
            ui.notify("Failed to save", type="negative")

    today_str = date.today().isoformat()

    def mis_count(stage: str, input_date: str) -> int:
        field = "booking_date" if stage == "booking" else "delivery_date"
        return sum(
            1 for t in all_transactions if (t.get(field) or "")[:10] == input_date
        )

    def incomplete_count(stage: str, input_date: str) -> int:
        date_field = "booking_date" if stage == "booking" else "delivery_date"
        incomplete_field = (
            "booking_file_incomplete"
            if stage == "booking"
            else "delivery_file_incomplete"
        )

        return sum(
            1
            for t in all_transactions
            if (t.get(date_field) or "")[:10] == input_date and t.get(incomplete_field)
        )

    def get_all_txn_dates(stage: str) -> set:
        field = "booking_date" if stage == "booking" else "delivery_date"
        return {
            (t.get(field) or "")[:10]
            for t in all_transactions
            if (t.get(field) or "")[:10]
        }

    def get_stored(stage: str, input_date: str) -> dict:
        return rstate.row_data.get((stage, input_date), {})

    # ── Computed cell values ──────────────────────────────────
    def compute_row(stage: str, input_date: str) -> dict:
        s = get_stored(stage, input_date)
        tc = int(s.get("total_count", 0) or 0)
        fr = int(s.get("files_received", 0) or 0)
        fi = incomplete_count(stage, input_date)
        fm = mis_count(stage, input_date)
        fp = max(0, tc - fr)  # Files Pending  = Total Count - Files Received
        fv = int(s.get("files_verified", 0) or 0)
        diff = fv - fm  # Difference     = Files Verified - Files in MIS
        return dict(tc=tc, fr=fr, fi=fi, fm=fm, fp=fp, fv=fv, diff=diff)

    # ── Totals recompute ─────────────────────────────────────
    def recompute_totals(stage: str, dates: list) -> None:
        sums = {
            c: 0
            for c in [
                "total_count",
                "files_received",
                "files_pending",
                "file_incomplete",
                "files_verified",
                "files_in_mis",
                "difference",
            ]
        }
        for d in dates:
            r = compute_row(stage, d)
            sums["total_count"] += r["tc"]
            sums["files_received"] += r["fr"]
            sums["files_pending"] += r["fp"]
            sums["file_incomplete"] += r["fi"]
            sums["files_verified"] += r["fv"]
            sums["files_in_mis"] += r["fm"]
            sums["difference"] += r["diff"]
        for col, total in sums.items():
            lbl = rstate.total_refs.get((stage, col))
            if lbl:
                lbl.set_text(str(total))

    def refresh_computed_row(stage: str, input_date: str, dates: list) -> None:
        r = compute_row(stage, input_date)

        # Files Pending label
        lbl_fp = rstate.label_refs.get((stage, input_date, "files_pending"))
        if lbl_fp:
            color = "#92400E" if r["fp"] > 0 else "#10B981"
            weight = "700" if r["fp"] > 0 else "600"
            lbl_fp.set_text(str(r["fp"]))
            lbl_fp.style(
                f"font-family:monospace;font-size:15px;font-weight:{weight};color:{color};text-align:center"
            )

        # Files Incomplete label
        lbl_fi = rstate.label_refs.get((stage, input_date, "file_incomplete"))
        if lbl_fi:
            fi_color = "#92400E" if r["fi"] > 0 else "#10B981"
            fi_weight = "700" if r["fi"] > 0 else "600"
            lbl_fi.set_text(str(r["fi"]))
            lbl_fi.style(
                f"font-family:monospace;font-size:15px;font-weight:{fi_weight};color:{fi_color};text-align:center"
            )

        # Files Verified label
        lbl_fv = rstate.label_refs.get((stage, input_date, "files_verified"))
        if lbl_fv:
            lbl_fv.set_text(str(r["fv"]))

        # Difference label
        lbl_diff = rstate.label_refs.get((stage, input_date, "difference"))
        if lbl_diff:
            color = (
                "#EF4444"
                if r["diff"] < 0
                else ("#10B981" if r["diff"] == 0 else "#F59E0B")
            )
            lbl_diff.set_text(str(r["diff"]))
            lbl_diff.style(
                f"font-family:monospace;font-size:15px;font-weight:700;color:{color};text-align:center"
            )

        recompute_totals(stage, dates)

    # ── Generic detail dialog (Pending & Incomplete) ─────────
    _dlg_state: dict = {
        "tt": None,
        "d": None,
        "col": None,
        "title_el": None,
        "body_el": None,
        "dates": [],
    }

    def refresh_detail_dialog(rows: list = []) -> None:
        _dlg_state["body_el"].clear()

        TH = (
            "border:1px solid #D1D5DB;padding:9px 13px;text-align:center;"
            "font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:.06em;color:#6B7280;background:#F9FAFB;white-space:nowrap"
        )
        TD = (
            "border:1px solid #E5E7EB;padding:8px 12px;"
            "font-size:13px;vertical-align:middle;text-align:center"
        )

        with _dlg_state["body_el"]:
            with ui.element("table").style(
                "width:100%;border-collapse:collapse;min-width:680px"
            ):
                with ui.element("thead"):
                    with ui.element("tr"):
                        for h, w in [
                            ("S.No", "60px"),
                            ("Date", "130px"),
                            ("Customer Name", ""),
                            ("PAN Card", "130px"),
                            ("Remarks", "180px"),
                        ]:
                            with ui.element("th").style(
                                TH + (f";width:{w}" if w else "")
                            ):
                                ui.label(h)

                with ui.element("tbody"):
                    if not rows:
                        with ui.element("tr"):
                            with (
                                ui.element("td")
                                .props('colspan="5"')
                                .style(
                                    "border:1px solid #E5E7EB;padding:40px;"
                                    "text-align:center;color:#9CA3AF;font-size:13px"
                                )
                            ):
                                with ui.column().classes("items-center gap-2"):
                                    ui.label("📭").style("font-size:28px")
                                    ui.label("No records found for this date").style(
                                        "color:#9CA3AF;font-size:13px"
                                    )
                    else:
                        for i, row in enumerate(rows):
                            row_bg = "#FFFFFF" if i % 2 == 0 else "#F9FAFB"
                            with ui.element("tr").style(f"background:{row_bg}"):
                                # S.No
                                with ui.element("td").style(
                                    TD + ";font-family:monospace;font-weight:700;"
                                    "color:#6366F1;background:#EEF2FF;width:60px"
                                ):
                                    ui.label(str(i + 1))

                                # Date
                                with ui.element("td").style(TD + ";width:130px"):
                                    ui.label(row.get("date", "—")).style(
                                        "font-size:13px;color:#374151;font-weight:500"
                                    )

                                # Customer Name
                                with ui.element("td").style(TD):
                                    ui.label(row.get("customer_name", "—")).style(
                                        "font-size:13px;color:#111827;font-weight:600"
                                    )

                                # PAN Card
                                with ui.element("td").style(TD + ";width:130px"):
                                    ui.label(row.get("pan_number", "—")).style(
                                        "font-family:monospace;font-size:13px;"
                                        "color:#374151;letter-spacing:.04em"
                                    )

                                # Remarks
                                with ui.element("td").style(TD + ";width:180px"):
                                    ui.label(row.get("remarks", "—")).style(
                                        "font-size:13px;color:#6B7280"
                                    )

    # Build dialog once
    with (
        ui.dialog() as detail_dlg,
        ui.card().classes("w-[860px] max-w-[96vw] p-6 rounded-xl shadow-2xl"),
    ):
        with ui.row().classes("w-full items-center justify-between mb-4"):
            title_el = ui.label("Details").classes(
                "text-[15px] font-bold text-gray-900"
            )
            _dlg_state["title_el"] = title_el
            ui.button(icon="close", on_click=detail_dlg.close).props("flat round dense")

        body_el = (
            ui.element("div")
            .classes("w-full overflow-x-auto")
            .style("max-height:450px;overflow-y:auto")
        )
        _dlg_state["body_el"] = body_el

        with ui.row().classes(
            "w-full justify-between items-center mt-4 pt-4 border-t border-gray-100"
        ):
            dlg_count_label = ui.label("0 records").classes(
                "text-[12px] font-semibold text-gray-400"
            )
            _dlg_state["count_label"] = dlg_count_label

            with ui.row().classes("gap-2"):

                async def _refresh_dlg():
                    await _fetch_and_show_dialog()

                ui.button("↻ Refresh", on_click=_refresh_dlg).props(
                    "outline no-caps"
                ).classes("text-[13px] border-gray-300 text-gray-600")
                ui.button("Close", on_click=detail_dlg.close).props(
                    "unelevated no-caps"
                ).classes("bg-[#E8402A] text-white text-[13px] px-5")

    async def _fetch_and_show_dialog() -> None:
        """Fetch records from backend and populate the dialog."""
        tt = _dlg_state["tt"]
        d = _dlg_state["d"]
        col = _dlg_state["col"]

        # Show loading state immediately
        _dlg_state["body_el"].clear()
        with _dlg_state["body_el"]:
            with ui.row().classes("w-full justify-center items-center gap-3 py-10"):
                ui.spinner(size="md", color="primary")
                ui.label("Loading records…").style("color:#9CA3AF;font-size:13px")

        try:
            # ── API endpoint — adjust the path to match your backend ──────────
            # Expected response: list of dicts with keys:
            #   date, customer_name, pan_number, remarks
            # col == "files_pending"    → fetch pending files for that date
            # col == "files_incomplete" → fetch incomplete files for that date
            endpoint = (
                f"/daily-report/pending?type={tt}&date={d}"
                if col == "files_pending"
                else f"/daily-report/incomplete?type={tt}&date={d}"
            )
            rows: list = await api_get(endpoint)
        except Exception:
            rows = []

        # Update count label
        count_lbl = _dlg_state.get("count_label")
        if count_lbl:
            count_lbl.set_text(f"{len(rows)} record{'s' if len(rows) != 1 else ''}")

        # Update the cell count label and recompute totals for incomplete column
        if col == "files_incomplete":
            k = (tt, d, "files_incomplete")
            rstate.dialog_data[k] = rows  # store so compute_row can read len()
            refresh_computed_row(tt, d, _dlg_state["dates"])

        refresh_detail_dialog(rows)

    def open_detail_dialog(tt: str, d: str, col: str, dates: list = []) -> None:
        _dlg_state["tt"] = tt
        _dlg_state["d"] = d
        _dlg_state["col"] = col
        _dlg_state["dates"] = dates
        ttype = "Booking" if tt == "booking" else "Delivery"
        col_label = "Files Pending" if col == "files_pending" else "Files Incomplete"
        _dlg_state["title_el"].set_text(f"📋 {col_label} — {d}  ({ttype})")
        detail_dlg.open()
        # Schedule async fetch after dialog is open
        ui.timer(0.05, _fetch_and_show_dialog, once=True)

    # ── Shared cell styles ───────────────────────────────────
    TH_S = (
        "border:1px solid #D1D5DB;padding:9px 14px;text-align:center;"
        "font-size:12px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.07em;color:#6B7280;background:#F9FAFB;white-space:nowrap"
    )
    TD_S = (
        "border:1px solid #E5E7EB;padding:6px 10px;"
        "font-size:15px;vertical-align:middle;text-align:center"
    )
    TF_S = (
        "border:1px solid #D1D5DB;padding:9px 14px;text-align:center;"
        "font-size:15px;font-weight:700;background:#ECEEF2;color:#111827"
    )

    # ── Table builder ────────────────────────────────────────
    def build_table(stage: str, dates: list, parent) -> None:
        with parent:
            with ui.element("table").style(
                "width:100%;border-collapse:collapse;border:1px solid #D1D5DB;"
                "table-layout:auto;font-family:Inter,sans-serif"
            ):
                # ── THEAD ─────────────────────────────────────────
                with ui.element("thead"):
                    with ui.element("tr"):
                        headers = [
                            ("Date", "140px"),
                            ("Total Count", "130px"),
                            ("Files Received", "130px"),
                            ("Files Pending", "130px"),
                            ("Files Incomplete", "130px"),
                            ("Files Verified", "130px"),
                            ("Files in MIS", "130px"),
                            ("Difference", "120px"),
                        ]
                        for hdr, w in headers:
                            with ui.element("th").style(TH_S + f";width:{w}"):
                                ui.label(hdr)

                # ── TBODY ─────────────────────────────────────────
                with ui.element("tbody"):
                    for date_idx, date in enumerate(dates):
                        r = compute_row(stage, date)
                        is_today = date == today_str
                        is_locked = date in rstate.locked_dates

                        if is_today:
                            row_bg = "background:#EFF6FF"
                        elif date_idx % 2 == 1:
                            row_bg = "background:#FAFAFA"
                        else:
                            row_bg = "background:#FFFFFF"

                        with ui.element("tr").style(row_bg):
                            from datetime import datetime

                            date = datetime.strptime(date, r"%Y-%m-%d").strftime(
                                "%d/%m/%Y"
                            )
                            # ── Date ───────────────────────────────
                            with ui.element("td").style(TD_S + ";white-space:nowrap"):
                                if is_today:
                                    with ui.row().classes(
                                        "items-center justify-center gap-1.5"
                                    ):
                                        ui.label(date).style(
                                            "font-weight:700;color:#2563EB;font-size:14px"
                                        )
                                        ui.label("TODAY").style(
                                            "background:#DBEAFE;color:#1D4ED8;font-size:10px;"
                                            "padding:1px 7px;border-radius:10px;font-weight:800;"
                                            "letter-spacing:.04em"
                                        )
                                else:
                                    ui.label(date).style(
                                        "font-weight:500;color:#374151;font-size:14px"
                                    )

                            # ── Total Count (editable text input) ──
                            with ui.element("td").style(TD_S):
                                total_count_inp = (
                                    ui.input(
                                        value=str(r["tc"]) if r["tc"] else "",
                                        placeholder="0",
                                        on_change=lambda e, _tt=stage, _d=date: (
                                            rstate.row_data.setdefault(
                                                (_tt, _d), {}
                                            ).__setitem__(
                                                "total_count",
                                                int(e.value)
                                                if (e.value or "").isdigit()
                                                else 0,
                                            ),
                                            refresh_computed_row(_tt, _d, dates),
                                        ),
                                    )
                                    .props(
                                        f'type="number" min="0" step="1" outlined dense {"readonly" if is_locked else ""}'
                                    )
                                    .classes("w-full text-center")
                                    .style(
                                        "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                    )
                                )

                            # ── Files Received (editable text input) ──
                            with ui.element("td").style(TD_S):
                                fr_inp = (
                                    ui.input(
                                        value=str(r["fr"]) if r["fr"] else "",
                                        placeholder="0",
                                        on_change=lambda e, _tt=stage, _d=date: (
                                            rstate.row_data.setdefault(
                                                (_tt, _d), {}
                                            ).__setitem__(
                                                "files_received",
                                                int(e.value)
                                                if (e.value or "").isdigit()
                                                else 0,
                                            ),
                                            refresh_computed_row(_tt, _d, dates),
                                        ),
                                    )
                                    .props(
                                        f'type="number" min="0" step="1" outlined dense {"readonly" if is_locked else ""}'
                                    )
                                    .classes("w-full text-center")
                                    .style(
                                        "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                    )
                                )

                            # ── Files Pending (computed + clickable for dialog) ──
                            fp_color = "#92400E" if r["fp"] > 0 else "#10B981"
                            fp_weight = "700" if r["fp"] > 0 else "600"
                            with (
                                ui.element("td")
                                .style(
                                    TD_S + ";cursor:pointer;background:#FFF7ED"
                                    if r["fp"] > 0
                                    else TD_S + ";cursor:pointer"
                                )
                                .on(
                                    "click",
                                    lambda _, _tt=stage, _d=date: open_detail_dialog(
                                        _tt, _d, "files_pending"
                                    ),
                                )
                            ):
                                fp_lbl = ui.label(str(r["fp"])).style(
                                    f"font-family:monospace;font-size:15px;"
                                    f"font-weight:{fp_weight};color:{fp_color};text-align:center"
                                )
                                rstate.label_refs[(stage, date, "files_pending")] = (
                                    fp_lbl
                                )

                            # ── Files Incomplete (clickable label → opens dialog, count = dialog rows) ──
                            fi_color = "#92400E" if r["fi"] > 0 else "#10B981"
                            fi_weight = "700" if r["fi"] > 0 else "600"
                            with (
                                ui.element("td")
                                .style(
                                    TD_S + ";cursor:pointer;background:#FFF7ED"
                                    if r["fi"] > 0
                                    else TD_S + ";cursor:pointer"
                                )
                                .on(
                                    "click",
                                    lambda _, _tt=stage, _d=date, _dates=dates: (
                                        open_detail_dialog(
                                            _tt, _d, "files_incomplete", _dates
                                        )
                                    ),
                                )
                            ):
                                fi_lbl = ui.label(str(r["fi"])).style(
                                    f"font-family:monospace;font-size:15px;"
                                    f"font-weight:{fi_weight};color:{fi_color};text-align:center"
                                )
                                rstate.label_refs[(stage, date, "file_incomplete")] = (
                                    fi_lbl
                                )

                            # ── Files Verified (user entry) ──
                            with ui.element("td").style(TD_S):
                                ui.input(
                                    value=str(r["fv"]) if r["fv"] else "",
                                    placeholder="0",
                                    on_change=lambda e, _tt=stage, _d=date: (
                                        rstate.row_data.setdefault(
                                            (_tt, _d), {}
                                        ).__setitem__(
                                            "files_verified",
                                            int(e.value)
                                            if (e.value or "").isdigit()
                                            else 0,
                                        ),
                                        refresh_computed_row(_tt, _d, dates),
                                    ),
                                ).props(
                                    f'type="number" min="0" step="1" outlined dense {"readonly" if is_locked else ""}'
                                ).classes("w-full text-center").style(
                                    "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                )

                            # ── Files in MIS (editable text input) ──
                            with ui.element("td").style(TD_S):
                                ui.label(str(r["fm"])).style(
                                    "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                )
                            # ── Difference (computed: fv - fm) ──
                            diff_color = (
                                "#EF4444"
                                if r["diff"] < 0
                                else ("#10B981" if r["diff"] == 0 else "#F59E0B")
                            )
                            with ui.element("td").style(TD_S):
                                diff_lbl = ui.label(str(r["diff"])).style(
                                    f"font-family:monospace;font-size:15px;"
                                    f"font-weight:700;color:{diff_color};text-align:center"
                                )
                                rstate.label_refs[(stage, date, "difference")] = (
                                    diff_lbl
                                )

                # ── TFOOT ─────────────────────────────────────────
                with ui.element("tfoot"):
                    with ui.element("tr").style(
                        "background:#ECEEF2;border-top:2px solid #D1D5DB"
                    ):
                        with ui.element("td").style(TF_S):
                            ui.label("TOTAL").style(
                                "font-size:12px;font-weight:800;letter-spacing:.06em;color:#374151"
                            )
                        for col_key in [
                            "total_count",
                            "files_received",
                            "files_pending",
                            "file_incomplete",
                            "files_verified",
                            "files_in_mis",
                            "difference",
                        ]:
                            with ui.element("td").style(TF_S):
                                lbl = ui.label("0").style(
                                    "font-family:monospace;font-size:15px;font-weight:700;color:#111827"
                                )
                                rstate.total_refs[(stage, col_key)] = lbl

        recompute_totals(stage, dates)

    # ── Date range helpers ────────────────────────────────────
    _today = date.today()
    _yester = _today - timedelta(days=1)

    _RANGE_OPTIONS = {
        "today": f"Today ({_today.strftime('%d/%m/%Y')})",
        "yesterday": f"Yesterday ({_yester.strftime('%d/%m/%Y')})",
        "last7": "Last 7 Days",
        "last15": "Last 15 Days",
        "custom": "Custom Date Range",
    }

    def _dates_for_range(
        selection: str, tt: str, from_date: str = "", to_date: str = ""
    ) -> list[str]:
        if selection == "today":
            base = {_today.isoformat()}
        elif selection == "yesterday":
            base = {_yester.isoformat()}
        elif selection == "last7":
            base = {(_today - timedelta(days=i)).isoformat() for i in range(7)}
        elif selection == "last15":
            base = {(_today - timedelta(days=i)).isoformat() for i in range(15)}
        else:  # custom range
            if from_date and to_date and from_date <= to_date:
                try:
                    fd = date.fromisoformat(from_date)
                    td_ = date.fromisoformat(to_date)
                    delta = (td_ - fd).days
                    base = {
                        (fd + timedelta(days=i)).isoformat() for i in range(delta + 1)
                    }
                except ValueError:
                    base = {today_str}
            elif from_date:
                base = {from_date}
            else:
                # fallback: all MIS dates + today
                txn_dates = get_all_txn_dates(tt)
                return sorted(txn_dates | {today_str})

        txn_dates = get_all_txn_dates(tt)
        return sorted(base | (txn_dates & base))

    # ── Rebuild function ──────────────────────────────────────
    booking_dates_state: dict = {"v": []}
    delivery_dates_state: dict = {"v": []}

    def _rebuild(selection: str, from_date: str = "", to_date: str = "") -> None:
        rstate.label_refs.clear()
        rstate.total_refs.clear()
        bking_dates = _dates_for_range(selection, "booking", from_date, to_date)
        del_dates = _dates_for_range(selection, "delivery", from_date, to_date)
        booking_dates_state["v"] = bking_dates
        delivery_dates_state["v"] = del_dates
        booking_wrap.clear()
        delivery_wrap.clear()
        build_table("booking", bking_dates, booking_wrap)
        build_table("delivery", del_dates, delivery_wrap)

    # ── Page layout ───────────────────────────────────────────
    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # ── Sidebar ───────────────────────────────────────────
        with ui.column().classes(
            "w-[220px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 "
            "sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"
        ):
            ui.label("Quick Nav").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5"
            )

            ui.link("📊 Dashboard", "/").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent no-underline"
            )
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )
            ui.link("📑 Complaints Control Panel", "/complaints-ctrl").classes(
                "flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline"
            )

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
            with ui.column().classes(
                "h-full justify-between w-full p-4 bg-white shadow"
            ):
                with ui.column().classes("mt-auto items-center"):

                    def handle_logout():
                        clear_user()
                        ui.navigate.to("/login")

                    ui.button("Logout", on_click=handle_logout).props(
                        "color=red outline"
                    ).classes("w-full")

        # ── Main content ──────────────────────────────────────
        with ui.column().classes(
            "flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden gap-6"
        ):
            # Page header
            with ui.row().classes("w-full items-start justify-between mb-1"):
                with ui.column().classes("gap-1"):
                    ui.label("Daily Reporting").classes(
                        "text-[18px] font-bold text-gray-900 leading-none"
                    )
                    ui.label("Track booking & delivery file status by date").classes(
                        "text-[12px] text-gray-400"
                    )

                # Controls: range selector + custom date range pickers
                with ui.column().classes("gap-2 items-end"):
                    range_select = (
                        ui.select(
                            options=_RANGE_OPTIONS,
                            value="custom",
                            label="Date Range",
                        )
                        .classes("w-52")
                        .props("outlined dense")
                        .style("font-size:13px;font-weight:500;border-radius:8px")
                    )

                    # Custom date range row — From … To
                    custom_range_row = ui.row().classes("items-center gap-2")
                    with custom_range_row:
                        ui.label("From:").classes(
                            "text-[12px] text-gray-500 whitespace-nowrap"
                        )

                        from_inp = (
                            ui.input(label="", value=today_str)
                            .props('type="date" outlined dense')
                            .classes("w-36")
                        )
                        ui.label("To:").classes(
                            "text-[12px] text-gray-500 whitespace-nowrap"
                        )
                        to_inp = (
                            ui.input(label="", value=today_str)
                            .props('type="date" outlined dense')
                            .classes("w-36")
                        )

            # ── Booking Card ───────────────────────────────────
            with ui.card().classes("w-full shadow-sm rounded-xl p-0 overflow-hidden"):
                with ui.row().classes(
                    "w-full items-center justify-between px-5 py-3 "
                    "border-b border-gray-100 bg-white"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes(
                            "w-2.5 h-2.5 rounded-full bg-[#6366F1]"
                        )
                        ui.label("Booking Details").classes(
                            "text-[13px] font-bold text-gray-800"
                        )
                    ui.label(
                        "Click 'Files Pending' or  on 'Files Incomplete' to see details"
                    ).classes("text-[11px] text-gray-400")

                booking_wrap = (
                    ui.element("div")
                    .classes("w-full overflow-x-auto")
                    .style("padding:0")
                )

            # ── Delivery Card ──────────────────────────────────
            with ui.card().classes("w-full shadow-sm rounded-xl p-0 overflow-hidden"):
                with ui.row().classes(
                    "w-full items-center justify-between px-5 py-3 "
                    "border-b border-gray-100 bg-white"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes(
                            "w-2.5 h-2.5 rounded-full bg-[#10B981]"
                        )
                        ui.label("Delivery Details").classes(
                            "text-[13px] font-bold text-gray-800"
                        )
                    ui.label(
                        "Click 'Files Pending' or  on 'Files Incomplete' to see details"
                    ).classes("text-[11px] text-gray-400")

                delivery_wrap = (
                    ui.element("div")
                    .classes("w-full overflow-x-auto")
                    .style("padding:0")
                )
            ui.button("Save", on_click=save_reporting).classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            ).props("no-caps unelevated")

    # ── Wire controls ─────────────────────────────────────────
    def _get_current_range():
        return range_select.value or "custom"

    def on_range_change(e):
        sel = e.value or "custom"
        # Show date pickers only for custom
        custom_range_row.set_visibility(sel == "custom")
        if sel != "custom":
            _rebuild(sel)
        else:
            # rebuild using current from/to values
            _rebuild("custom", from_inp.value or today_str, to_inp.value or today_str)

    def on_from_change(e):
        if _get_current_range() == "custom":
            _rebuild("custom", e.value or today_str, to_inp.value or today_str)

    def on_to_change(e):
        if _get_current_range() == "custom":
            _rebuild("custom", from_inp.value or today_str, e.value or today_str)

    range_select.on_value_change(on_range_change)
    from_inp.on_value_change(on_from_change)
    to_inp.on_value_change(on_to_change)

    # ── Initial render (default: custom = today only) ──────────
    _rebuild("custom", today_str, today_str)


def build_reporting_payload(rstate: ReportingState):
    payload = {
        "bookings": [],
        "deliveries": [],
    }

    for (stage, _date), values in rstate.row_data.items():
        base = {
            "date": _date,
            "outlet_id": values.get("outlet_id", 1),  # ⚠️ adjust this properly
            "file_received": values.get("files_received", 0),
            "files_pending": max(
                0,
                values.get("total_count", 0) - values.get("files_received", 0),
            ),
            "files_verified": values.get("files_verified", 0),
        }

        if stage == "booking":
            payload["bookings"].append(
                {
                    **base,
                    "number_bookings": values.get("total_count", 0),
                }
            )
        else:  # delivery
            payload["deliveries"].append(
                {
                    **base,
                    "number_deliveries": values.get("total_count", 0),
                }
            )

    return payload


# ══════════════════════════════════════════════════════════════
#                        PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════
@ui.page("/settings")
@protected_page
async def settings_page():

    def get_id_by_name(iter: list[dict], name: str) -> int | None:
        for o in iter:
            if o["name"] == name:
                return o["id"]
        return None

    dealers = await api_get("/complaints/dealerships")
    outlets = await api_get("/outlets")
    outlet_names = [o["name"] for o in outlets]
    dealer_names = [d["name"] for d in dealers]

    render_topbar("Settings")
    with ui.column().classes("w-full"):
        with ui.card().classes(
            "max-w-[1100px] mx-auto p-8 w-full shadow-sm rounded-xl mt-6"
        ):
            ui.label("Register New Users").classes("text-xl font-bold mb-4")
            with ui.row().classes("w-full gap-6"):
                # ── LEFT: FORM ─────────────────────────────────────
                with ui.column().classes("flex-1 gap-4 "):
                    name = (
                        ui.input("Full Name")
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )
                    username = (
                        ui.input("User Name")
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )

                    password = (
                        ui.input("Password", password=True, password_toggle_button=True)
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )

                    def on_role_change(e):
                        if e.value == "Admin":
                            outlet.value = None
                            outlet.disable()
                        else:
                            outlet.enable()

                    role = (
                        ui.select(
                            ["Admin", "Client", "Audit Assistant"],
                            label="Role",
                        )
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )
                    role.on_value_change(on_role_change)

                    outlet = (
                        (
                            ui.select(
                                options=outlet_names,
                                label="Showroom",
                                value=None,
                            )
                        )
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )
                    print("user register", outlet.value)
                    # ── ACTIONS ────────────────────────────────────
                    with ui.row().classes("gap-3 mt-4"):

                        async def handle_register():
                            if not name.value or not password.value:
                                ui.notify("Name and Password required", type="negative")
                                return

                            if not role.value:
                                ui.notify("Role is required", type="negative")
                                return
                            if role.value != "Admin" and not outlet.value:
                                ui.notify("Showroom is required.", type="negative")
                                return

                            payload = {
                                "name": name.value.strip(),
                                "username": username.value,
                                "password": password.value,
                                "role": role.value.replace(" ", "_").lower(),
                                "outlet_id": None
                                if role.value == "Admin"
                                else get_id_by_name(outlets, outlet.value),
                            }

                            try:
                                await api_post("/auth/register", payload)

                                ui.notify("User created successfully", type="positive")

                                # Reset form
                                name.value = ""
                                username.value = ""
                                password.value = ""
                                role.value = None
                                outlet.value = None

                            except httpx.HTTPStatusError as e:
                                # Backend validation / known errors
                                try:
                                    error_detail = e.response.json()
                                except Exception:
                                    error_detail = e.response.text

                                ui.notify(f"Error: {error_detail}", type="negative")

                            except httpx.ConnectError:
                                ui.notify("Server unreachable", type="negative")

                            except Exception as e:
                                ui.notify(str(e), type="negative")

                        ui.button("Create User", on_click=handle_register).classes(
                            "bg-[#E8402A] text-white px-4 py-2 rounded-md"
                        )

                        ui.button(
                            "Reset",
                            on_click=lambda: [
                                setattr(name, "value", ""),
                                setattr(password, "value", ""),
                                setattr(role, "value", None),
                                setattr(outlet, "value", None),
                            ],
                        ).props("outline")

                # ── RIGHT: INFO PANEL (professional touch) ─────────
                with ui.column().classes(
                    "w-[280px] bg-gray-50 rounded-lg p-4 border text-sm text-gray-600"
                ):
                    ui.label("Guidelines").classes("font-semibold text-gray-800 mb-2")

                    ui.label("• Use a unique username")
                    ui.label("• Assign correct role carefully")
                    ui.label("• Outlet determines data visibility")
                    ui.label("• Password should be secure")

                    ui.separator()

                    ui.label("Roles").classes("font-semibold mt-2 text-gray-800")
                    ui.label("Admin → Full access")
                    ui.label("Audit Assistant → For Audit Assistant")
                    ui.label("Client → For Dealership Owners")

    with ui.column().classes("w-full items-center"):
        with ui.card().classes(
            "max-w-[900px] w-full p-8 mt-8 rounded-2xl shadow-lg border border-gray-100"
        ):
            # ── Header ─────────────────────────────────────
            ui.label("Upload Price List").classes("text-xl font-semibold text-gray-800")
            ui.label("Upload Excel file with pricing details").classes(
                "text-sm text-gray-400 mb-4"
            )

            ui.separator()

            # ── Form Section ───────────────────────────────
            with ui.column().classes("w-full gap-4 mt-4"):
                with ui.row().classes("w-full gap-4"):
                    valid_from = (
                        ui.date_input(
                            label="Valid From",
                            value=date.today().isoformat(),
                        )
                        .props("outlined dense")
                        .classes("w-1/3")
                    )

                    valid_to = (
                        ui.date_input(label="Valid To")
                        .props("outlined dense")
                        .classes("w-1/3")
                    )

                    model_year = (
                        ui.number(label="Model Year")
                        .props("outlined dense")
                        .classes("w-1/3")
                    )

            # ── Upload Area ────────────────────────────────
            with ui.card().classes(
                "mt-6 p-6 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50 w-full items-center text-center"
            ):
                ui.icon("upload_file", size="2.5rem").classes("text-gray-400")

                ui.label("Drag & drop your Excel file here").classes(
                    "text-sm text-gray-600 mt-2"
                )

                ui.label("or click to browse (.xlsx only)").classes(
                    "text-xs text-gray-400"
                )

                status_label = ui.label("").classes("text-sm mt-3")

                async def handle_upload(e):
                    try:
                        # ── Validation ─────────────────────
                        if not valid_from.value:
                            status_label.text = "❌ Valid From is required"
                            status_label.classes("text-red-500")
                            return

                        if not model_year.value:
                            status_label.text = "❌ Model Year is required"
                            status_label.classes("text-red-500")
                            return

                        payload = {
                            "valid_from": valid_from.value,
                            "model_year": int(model_year.value),
                            "sheet_name": "0",
                        }

                        if valid_to.value:
                            payload["valid_to"] = valid_to.value

                        status_label.text = "Uploading..."
                        status_label.classes("text-blue-500")

                        await api_post_file("/price-list/upload", e, payload)

                        status_label.text = "✅ Upload successful"
                        status_label.classes("text-green-600")

                    except Exception as ex:
                        status_label.text = f"❌ {str(ex)}"
                        status_label.classes("text-red-500")

                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                ).props("accept=.xlsx").classes("mt-4")

            # ── Footer Note ────────────────────────────────
            ui.label("Only .xlsx files are supported").classes(
                "text-xs text-gray-400 mt-3 text-center"
            )
    # with ui.column().classes("w-full"):
    #     with ui.card().classes(
    #         "max-w-[1100px] mx-auto p-8 w-full shadow-sm rounded-xl mt-6"
    #     ):
    #         # 🔹 Default today
    #         today = date.today().isoformat()
    #         with ui.row().classes("justify-end"):
    #             # 🔹 REQUIRED: valid_from
    #             valid_from = ui.date_input(
    #                 label="Valid From (Required)", value=today
    #             ).classes("w-64")

    #             # 🔹 OPTIONAL: valid_to
    #             valid_to = ui.date_input(label="Valid To (Optional)").classes("w-64")
    #             # 🔹 OPTIONAL: valid_to
    #             model_year = ui.number(label="Model Year").classes("w-64")

    #             status_label = ui.label("").classes("text-sm mt-2")

    #             async def handle_upload(e):
    #                 try:
    #                     if not valid_from.value:
    #                         status_label.text = "❌ Valid From date is required"
    #                         status_label.classes("text-red-600")
    #                         return

    #                     payload = {
    #                         "valid_from": valid_from.value,
    #                         "model_year": model_year.value,
    #                         "sheet_name": "0",
    #                     }
    #                     if valid_to.value:
    #                         payload["valid_to"] = valid_to.value

    #                     await api_post_file("/price-list/upload", e, payload)

    #                     status_label.text = "✅ Price list uploaded successfully"
    #                     status_label.classes("text-green-600")

    #                 except Exception as ex:
    #                     status_label.text = f"❌ {str(ex)}"
    #                     status_label.classes("text-red-600")

    #             ui.upload(on_upload=handle_upload, auto_upload=True).classes("")
    #             ui.label("Upload Excel file (.xlsx)").classes(
    #                 "text-xs text-gray-400 mt-2"
    #             )
    with ui.column().classes("w-full items-center gap-6"):
        # ─────────────────────────────────────────────
        # 🏢 DEALERSHIP CARD
        # ─────────────────────────────────────────────
        with ui.card().classes("w-full max-w-[900px] p-6 rounded-2xl shadow border"):
            ui.label("Create Dealership").classes("text-lg font-semibold")

            d_name = (
                ui.input("Dealership Name").props("outlined dense").classes("w-full")
            )
            d_code = (
                ui.input("Dealership Code").props("outlined dense").classes("w-full")
            )

            async def create_dealership():
                try:
                    await api_post(
                        "/dealership",
                        {
                            "name": d_name.value,
                            "code": d_code.value,
                        },
                    )
                    ui.notify("Dealership created", type="positive")
                    d_name.value = ""
                    d_code.value = ""
                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button("Create Dealership", on_click=create_dealership).classes(
                "mt-3 bg-[#E8402A] text-white"
            )

        # ─────────────────────────────────────────────
        # 🏬 OUTLET CARD
        # ─────────────────────────────────────────────
        with ui.card().classes("w-full max-w-[900px] p-6 rounded-2xl shadow border"):
            ui.label("Create Showroom").classes("text-lg font-semibold")

            o_name = ui.input("Outlet Name").props("outlined dense").classes("w-full")
            o_code = ui.input("Outlet Code").props("outlined dense").classes("w-full")
            o_address = ui.input("Address").props("outlined dense").classes("w-full")
            print(dealer_names)
            dealership_select = (
                ui.select(options=dealer_names, label="Dealership", value=None)
                .props("outlined dense")
                .classes("w-full")
            )

            async def create_outlet():
                try:
                    await api_post(
                        "/outlets",
                        {
                            "name": o_name.value,
                            "code": o_code.value,
                            "address": o_address.value,
                            "dealership_id": get_id_by_name(
                                dealers, dealership_select.value
                            ),
                        },
                    )
                    ui.notify("Outlet created", type="positive")

                    o_name.value = ""
                    o_code.value = ""
                    o_address.value = ""
                    dealership_select.value = None

                except Exception as e:
                    ui.notify(str(e), type="negative")

            print("name", o_name.value)
            print("code", o_code.value)
            print("address", o_address.value)
            print("Showroom", dealership_select.value)
            ui.button("Create Outlet", on_click=create_outlet).classes(
                "mt-3 bg-[#E8402A] text-white"
            )

        # ─────────────────────────────────────────────
        # 👤 EMPLOYEE CARD
        # ─────────────────────────────────────────────
        with ui.card().classes("w-full max-w-[900px] p-6 rounded-2xl shadow border"):
            ui.label("Create Showroom Employee").classes("text-lg font-semibold")

            e_name = ui.input("Employee Name").props("outlined dense").classes("w-full")
            e_designation = (
                ui.input("Designation").props("outlined dense").classes("w-full")
            )

            outlet_select = (
                ui.select(
                    options=outlet_names,
                    label="Outlet",
                )
                .props("outlined dense")
                .classes("w-full")
            )
            print("Employee", outlet_select.value)

            async def create_employee():
                try:
                    await api_post(
                        "/sales-executive",
                        {
                            "name": e_name.value,
                            "outlet_id": get_id_by_name(outlets, outlet_select.value),
                            "designation": e_designation.value,
                        },
                    )
                    ui.notify("Employee created", type="positive")

                    e_name.value = ""
                    e_designation.value = ""
                    outlet_select.value = None

                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button("Create Employee", on_click=create_employee).classes(
                "mt-3 bg-[#E8402A] text-white"
            )


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
        # booking_edit in future
        self.form_mode: str = "booking_create"  # booking_create | delivery_create | delivery_from_booking | delivery_edit | complaint_create | complaint_edit
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
        self.car_color: ui.input | None = None

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
        self.error_msg_label: ui.html | None = None

        self.listed_prices: dict[str, int] = {}
        self.price_listed_labels: dict[str, ui.label] = {}
        self.discount_listed_labels: dict[str, ui.label] = {}

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

        # Component inputs
        self.price_inputs: dict[str, ui.input] = {}
        self.price_rows: dict[str, ui.row] = {}
        self.discount_inputs: dict[str, ui.input] = {}
        self.discount_rows: dict[str, ui.row] = {}

        # Component toggles
        self.price_match_toggles: dict[str, ui.switch] = {}
        self.price_diff_labels: dict[str, ui.label] = {}
        self.discount_match_toggles: dict[str, ui.switch] = {}  # Not required now
        self.lbl_excess_discount: ui.label | None = None

        # Live calc labels
        self.lbl_allowed: ui.label | None = None
        self.lbl_discount: ui.label | None = None
        self.lbl_excess: ui.label | None = None
        self.lbl_total_listed_price: ui.label | None = None  # a
        self.lbl_total_offered_price: ui.label | None = None  # b
        self.lbl_total_diff_price: ui.label | None = None  # = a-b
        self.lbl_total_listed_discount: ui.label | None = None
        self.adjustment_input: ui.input | None = None
        self.stage_toggle = None
        self.delivery_mode = None
        self.booking_select = None
        self.total_discount_booking = 0.0

        # Complaint Form Specifics
        self.complaint_dealerships: list = []
        self.complainant_outlets: list = []
        self.complainee_outlets: list = []

        self.complainant_dealership: ui.select | None = None
        self.complainant_showroom: ui.select | None = None
        self.complainee_dealership: ui.select | None = None
        self.complainee_showroom: ui.select | None = None
        self.complaint_status: ui.select | None = None

        self.comp_quotation_no: ui.input | None = None
        self.comp_quotation_date: ui.input | None = None
        self.comp_total_offered: ui.input | None = None
        self.comp_net_offered: ui.input | None = None
        self.comp_tcs: ui.input | None = None

        self.comp_booking_file_no: ui.input | None = None
        self.comp_receipt_no: ui.input | None = None
        self.comp_booking_amt: ui.input | None = None
        self.comp_mode_of_payment: ui.input | None = None
        self.comp_instrument_date: ui.input | None = None
        self.comp_instrument_no: ui.input | None = None
        self.comp_bank_name: ui.input | None = None

        self.complainant_remarks: ui.textarea | None = None
        self.complainee_aa_name: ui.input | None = None
        self.complainant_aa_remarks: ui.textarea | None = None
        self.complaint_date: ui.input | None = None

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

    def _validate_complaint(self) -> tuple[bool, str]:
        if not self.complainant_dealership or not self.complainant_dealership.value:
            return False, "Complainant dealership is required."
        if not self.complainant_showroom or not self.complainant_showroom.value:
            return False, "Complainant showroom is required."
        if not self.complainee_dealership or not self.complainee_dealership.value:
            return False, "Complainee dealership is required."
        if not self.complainee_showroom or not self.complainee_showroom.value:
            return False, "Complainee showroom is required."
        if not self.cust_name or not self.cust_name.value:
            return False, "Customer Name is required."
        if not self.cust_mobile or not self.cust_mobile.value:
            return False, "Customer Mobile is required."
        if not self.cust_address or not self.cust_address.value:
            return False, "Customer Address is required."
        if not self.cust_city or not self.cust_city.value:
            return False, "Customer City is required."
        if not self.cust_pincode or not self.cust_pincode.value:
            return False, "Customer PIN Code is required."
        if not self.variant_id:
            return False, "Please select a Car and Variant."
        # if not self.complainant_remarks or not self.complainant_remarks.value:
        #     return False, "Complainant's Remarks are required."

        return True, ""

    def is_valid(self) -> tuple[bool, str]:
        if self.form_mode == "complaint_create" or self.form_mode == "complaint_edit":
            return self._validate_complaint()

        def _val(f):
            return (str(f.value) or "").strip() if f else ""

        def _val_upper(f):
            return (f.value or "").strip().upper() if f else ""

        if not self.variant_id:
            return False, "Please select a Car and Variant."

        if not _val(self.cust_name):
            return False, "Customer name is required."

        if len(_val(self.model_year)) > 4:
            return False, "Invalid Model Year."

        mob = _val(self.cust_mobile)
        if not re.fullmatch(r"[6-9]\d{9}", mob):
            return False, "Mobile must be 10 digits starting with 6–9."

        if not _val(self.cust_address):
            return False, "Address is required."

        if not _val(self.cust_city):
            return False, "City is required."

        pan_val = _val_upper(self.cust_pan)
        if pan_val and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_val):
            return False, "Valid PAN required."

        # TR Case condition
        if self.condition_cbs.get("tr_case") and self.condition_cbs["tr_case"].value:
            if not _val(self.cust_other_id):
                return False, "Other ID Proof required for TR Case."

        year_val = _val(self.model_year)
        if not year_val or not year_val.isdigit():
            return False, "Valid Model Year is required."

        if self.stage == "delivery":
            if not _val(self.vin_no):
                return False, "VIN Number is required."
            if not _val(self.engine_no):
                return False, "Engine Number is required."

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

    # FORCE update options
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
    ui.timer(0.15, lambda: state.variant_select.set_value(variant_id), once=True)
    state.variant_id = variant_id


def populate_from_booking(state: FormState, data: dict):

    if not data:
        return

    # ── Booking ──────────────────
    if state.booking_date:
        state.booking_date.set_value(data.get("booking_date"))

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
    if state.model_year:
        state.model_year.set_value(data.get("model_year", ""))

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
    if state.model_year:
        state.model_year.set_value(data.get("model_year", ""))

    # ── Variant / Car ────────────
    _map_car_and_variant(state, data)

    # ── Conditions ───────────────
    conditions = data.get("conditions", {})
    disp_key = [
        "Exchange",
        "Corporate",
        "Govt Employee",
        "Scrap",
        "Upgrade",
        "Self Insurance",
        "FasTag",
        "Entended Warranty",
        "Shield Of Trust",
    ]
    for key, cb in zip(disp_key, state.condition_cbs.values()):
        print(f"From populate_booking: {key}")
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

    # Discounts
    for name, inp in state.discount_inputs.items():
        val = component_map.get(name)
        if val is not None:
            inp.set_value(format_num_inr(val))


def populate_from_delivery(state: FormState, delivery: dict):

    if not delivery:
        return

    populate_from_booking(state, delivery)

    if state.delivery_date:
        state.delivery_date.set_value(delivery.get("delivery_date", ""))
    if state.car_color:
        state.car_color.set_value(delivery.get("color", ""))
    if state.invoice_number:
        state.invoice_number.set_value(delivery.get("invoice_number", ""))
    if state.invoice_date:
        state.invoice_date.set_value(delivery.get("invoice_date", ""))
    if state.invoice_taxable_value:
        state.invoice_taxable_value.set_value(delivery.get("taxable_value", ""))
    if state.invoice_ex_showroom:
        state.invoice_ex_showroom.set_value(delivery.get("ex_showroom_price", ""))
    if state.invoice_discount:
        state.invoice_discount.set_value(delivery.get("discount", ""))
    if state.invoice_cgst:
        state.invoice_cgst.set_value(delivery.get("cgst", ""))
    if state.invoice_sgst:
        state.invoice_sgst.set_value(delivery.get("sgst", ""))
    if state.invoice_igst:
        state.invoice_igst.set_value(delivery.get("igst", ""))
    if state.invoice_cess:
        state.invoice_cess.set_value(delivery.get("cess", ""))
    if state.invoice_total:
        state.invoice_total.set_value(delivery.get("total_amount", ""))

    # Delivery checks
    delv = delivery.get("delivery_checks", {})
    for key, cb in state.delivery_cbs.items():
        cb.set_value(bool(delv.get(key, False)))

    # Audit
    audit = delivery.get("audit_info", {})
    if state.audit_obs:
        state.audit_obs.set_value(audit.get("observations", ""))
    if state.audit_action:
        state.audit_action.set_value(audit.get("follow_up_action", ""))

    # ── Trigger recalculation ────
    _fs_update_live(state)
    _fs_revalidate(state)


def populate_from_complaint(state: FormState, complaint: dict):
    import asyncio

    if not complaint:
        return

    # --- Customer details ---
    if state.cust_name:
        state.cust_name.set_value(complaint.get("customer_name", ""))
    if state.cust_mobile:
        state.cust_mobile.set_value(complaint.get("customer_mobile", ""))
    if state.cust_email:
        state.cust_email.set_value(complaint.get("email", ""))
    if state.cust_address:
        state.cust_address.set_value(complaint.get("customer_address", ""))
    if state.cust_city:
        state.cust_city.set_value(complaint.get("customer_city", ""))
    if state.cust_pincode:
        state.cust_pincode.set_value(complaint.get("customer_pin", ""))
    if state.cust_pan:
        state.cust_pan.set_value(complaint.get("customer_pan", ""))
    if state.cust_aadhar:
        state.cust_aadhar.set_value(complaint.get("customer_aadhar", ""))

    # --- Quotation & Booking ---
    if state.comp_quotation_no:
        state.comp_quotation_no.set_value(complaint.get("quotation_number", ""))
    if state.comp_quotation_date:
        state.comp_quotation_date.set_value(complaint.get("quotation_date", ""))
    if state.comp_net_offered:
        state.comp_net_offered.set_value(complaint.get("net_offered_price", ""))
    if state.comp_total_offered:
        state.comp_total_offered.set_value(complaint.get("total_offered_price", ""))
    if state.comp_tcs:
        state.comp_tcs.set_value(complaint.get("tcs_amount", ""))
    if state.comp_booking_file_no:
        state.comp_booking_file_no.set_value(complaint.get("booking_file_number", ""))
    if state.comp_receipt_no:
        state.comp_receipt_no.set_value(complaint.get("receipt_number", ""))
    if state.comp_booking_amt:
        state.comp_booking_amt.set_value(complaint.get("booking_amount", ""))
    if state.comp_mode_of_payment:
        state.comp_mode_of_payment.set_value(complaint.get("mode_of_payment", ""))
    if state.comp_instrument_date:
        state.comp_instrument_date.set_value(complaint.get("instrument_date", ""))
    if state.comp_instrument_no:
        state.comp_instrument_no.set_value(complaint.get("instrument_number", ""))
    if state.comp_bank_name:
        state.comp_bank_name.set_value(complaint.get("bank_name", ""))

    # --- Vehicle ---
    if state.vin_no:
        state.vin_no.set_value(complaint.get("vin_number", ""))
    if state.engine_no:
        state.engine_no.set_value(complaint.get("engine_number", ""))
    if state.vehicle_regn_no:
        state.vehicle_regn_no.set_value(complaint.get("registration_number", ""))
    if state.regn_date:
        state.regn_date.set_value(complaint.get("registration_date", ""))
    if state.car_color:
        state.car_color.set_value(complaint.get("car_color", ""))

    # --- Dealerships (CRITICAL ORDER) ---
    dlr = complaint.get("complainant_dealer_name")

    if dlr:
        state.complainant_dealership.set_value(dlr)

        if hasattr(state, "_handle_complainant_change"):
            asyncio.create_task(state._handle_complainant_change(dlr))

    comp_dlr = complaint.get("complainee_dealer_name")

    if comp_dlr:
        if hasattr(state, "_handle_complainee_change"):
            asyncio.create_task(state._handle_complainee_change(comp_dlr))

    # --- Delayed dependent fields ---
    def set_dependent_fields():
        if state.complainant_showroom:
            state.complainant_showroom.set_value(
                complaint.get("complainant_showroom_name")
            )

        if state.complainee_dealership:
            state.complainee_dealership.set_value(
                complaint.get("complainee_dealer_name")
            )

        if state.complainee_showroom:
            state.complainee_showroom.set_value(
                complaint.get("complainee_showroom_name")
            )

    ui.timer(0.2, set_dependent_fields, once=True)

    # --- Remarks ---
    if state.complaint_date:
        state.complaint_date.set_value(complaint.get("date_of_complaint", ""))
    if state.complainant_remarks:
        state.complainant_remarks.set_value(complaint.get("remarks_complainant", ""))
    if state.complainee_aa_name:
        state.complainee_aa_name.set_value(complaint.get("remark_complainee_aa", ""))
    if state.complainant_aa_remarks:
        state.complainant_aa_remarks.set_value(complaint.get("remark_admin", ""))

    if state.complaint_status:
        state.complaint_status.set_value(complaint.get("status", ""))

    # --- Variant mapping ---
    _map_car_and_variant(state, complaint)


async def resolve_form_mode(state, transaction_id):
    if state.stage != "delivery":
        return

    if transaction_id:
        txn_data = await api_get(f"/transactions/{transaction_id}")

        if txn_data.get("stage") == "delivery":
            state.form_mode = "delivery_edit"
        else:
            state.form_mode = "delivery_from_booking"

        state.txn_id = transaction_id
        state.edit_mode = True
        state.booking_data = txn_data

        return txn_data

    else:
        state.form_mode = "delivery_direct_create"
        return None


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
            state.car_color = (
                ui.input(label="Car Colour").classes("w-full").props("outlined dense")
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
            if state.form_mode not in ["complaint_create", "complaint_edit"]:
                state.cust_file_no = (
                    ui.input(label="Customer File No *")
                    .classes("w-full")
                    .props("outlined dense")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )
                state.model_year = (
                    ui.input(
                        label="Model Year *",
                        value="2026",
                        placeholder="e.g. 2024",
                        on_change=lambda _: _fs_try_price_preload(state),
                        validation={
                            "Must be 4 digits": lambda value: (
                                len(value) == 4 and value.isdigit()
                            )
                        },
                    )
                    .classes("w-full")
                    .props("outlined dense")
                    .on_value_change(
                        lambda _: _fs_revalidate(state),
                    )
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
            if state.stage == "delivery":
                state.vin_no = (
                    ui.input(
                        label="VIN Number *",
                        placeholder="MALB000CLSM000000",
                        validation={
                            "Invalid VIN Number": lambda v: (
                                bool(v) and bool(vin_regex.match(v))
                            )
                        },
                    )
                    .classes("w-full uppercase")
                    .props("outlined dense")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )
                state.delivery_date = (
                    ui.input(
                        label="Delivery Date *",
                        validation={
                            "Enter valid date (DD/MM/YYYY)": lambda v: (
                                bool(v) and is_valid_date(v)
                            )
                        },
                    )
                    .classes("w-full")
                    .props('type="date" outlined dense')
                    .on_value_change(lambda _: _fs_revalidate(state))
                )
                state.engine_no = (
                    ui.input(
                        label="Engine Number *",
                        validation={
                            "Enter 10–15 alphanumeric characters": lambda v: (
                                bool(v)
                                and 10 <= len(v.strip()) <= 15
                                and v.strip().isalnum()
                            )
                        },
                    )
                    .classes("w-full uppercase")
                    .props("outlined dense")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )

                state.vehicle_regn_no = (
                    ui.input(
                        label="Vehicle Regn Number",
                        placeholder="UP32AB0000 or 26BH1234AB",
                        validation={
                            "Invalid Registration Number": lambda v: (
                                not v
                                or (
                                    bool(regn_regex.match(v.strip().upper()))
                                    or bool(bharat_regex.match(v.strip().upper()))
                                )
                            )
                        },
                    )
                    .classes("w-full uppercase")
                    .props("outlined dense")
                )
                state.regn_date = (
                    ui.input(
                        label="Date of Registration",
                        placeholder="DD/MM/YYYY",
                        validation={
                            "Enter valid date (DD/MM/YYYY)": lambda v: (
                                bool(v) and is_valid_date(v)
                            )
                        },
                    )
                    .classes("w-full")
                    .props('outlined dense type="date"')
                )

        if state.outlet_select and state.outlets:
            state.outlet_select.set_value(state.outlets[0]["id"])
            state.outlet_id = state.outlets[0]["id"]
        if state.exec_select and state.executives:
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
                            not v or bool(re.fullmatch(r"[6-9]\d{9}", v))
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
                            not v
                            or bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v.upper()))
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

        with ui.grid(columns=FORM_COLUMNS + 1).classes("w-full"):
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
                    validation={
                        "Enter valid date (DD-MM-YYYY)": lambda v: (
                            bool(v) and is_valid_date(v)
                        )
                    },
                )
                .classes("w-full")
                .props("type='date' outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.booking_amt = accounting_input(
                label_text="Booking Amount", placeholder="Enter Amount"
            )

            state.booking_receipt_num = (
                ui.input(
                    label="Booking Receipt Number*", placeholder="Enter Receipt Number"
                )
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
                with ui.column().classes("w-full"):
                    with ui.row().classes("w-full mb-0"):
                        ui.label("Price Adjustment").classes(
                            "w-146 text-lg font-bold tracking-[0.9px] uppercase vertical-align-center"
                        )
                        state.adjustment_input = accounting_input(
                            "Price Adjustment",
                            placeholder="Enter Adjustment",
                            container_classes="w-[250px]",
                        )
                        state.adjustment_input.on_value_change(
                            lambda _: _fs_update_live(state)
                        )
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
            state.total_discount_booking = accounting_input(
                label_text="",
                placeholder="₹0",
                container_classes="w-60",
            )
            state.total_discount_booking.on_value_change(
                lambda _: _fs_update_live(state)
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
                    ui.label("Price Adjustment").classes(
                        "w-60 text-lg font-bold tracking-[0.9px] uppercase"
                    )

                    state.adjustment_input = accounting_input(
                        label_text="",
                        placeholder="₹0",
                        container_classes="w-60",
                    )
                    state.adjustment_input.on_value_change(
                        lambda _: _fs_update_live(state)
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
                .classes(
                    "text-lg text-bold vertical-align-center horizotal-align-center"
                )
                .props("dense")
            )

            # ── Charged Input ─────────────────────────
            state.acc_charged = accounting_input(
                label_text="Actual Charged (₹)"
            ).on_value_change(lambda _: _fs_update_live(state))


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
            state.invoice_date = ui.input(
                label="Invoice Date",
                validation={
                    "Enter valid date (DD-MM-YYYY)": lambda v: (
                        bool(v) and is_valid_date(v)
                    )
                },
            ).props('outlined dense type="date"')

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


def build_complaint_dealership_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🏢").classes("text-[20px] select-none")
            ui.label("Dealership Details").classes(
                "text-[15px] font-bold text-gray-900"
            )

        with ui.grid(columns=2).classes("w-full gap-5"):
            # ── Selectors ─────────────────────────────
            state.complainant_dealership = (
                ui.select(
                    {d["name"]: d["name"] for d in state.complaint_dealerships},
                    label="Complainant Dealership *",
                )
                .classes("w-full")
                .props("outlined dense")
            )

            state.complainant_showroom = (
                ui.select({}, label="Showroom *")
                .classes("w-full")
                .props("outlined dense")
            )

            complainee_options = {"X": "X"}
            for d in state.complaint_dealerships:
                complainee_options[d["name"]] = d["name"]

            state.complainee_dealership = (
                ui.select(complainee_options, label="Complainee Dealership *")
                .classes("w-full")
                .props("outlined dense")
            )

            state.complainee_showroom = (
                ui.select({"X": "X"}, label="Showroom *")
                .classes("w-full")
                .props("outlined dense")
            )

            # ── Shared Logic ─────────────────────────
            async def handle_complainant_change(dlr):
                if not dlr:
                    return

                # Update complainee dealership options
                filtered = {"X": "X"}
                for d in state.complaint_dealerships:
                    if d["name"] != dlr:
                        filtered[d["name"]] = d["name"]

                state.complainee_dealership.options = filtered
                state.complainee_dealership.update()

                # Fetch complainant showrooms
                try:
                    outs = await api_get(f"/complaints/dealerships/{dlr}/outlets")
                    if outs:
                        state.complainant_showroom.options = {o: o for o in outs}
                        state.complainant_showroom.update()
                except Exception as ex:
                    print(f"Error fetching outlets: {ex}")

            async def handle_complainee_change(dlr):
                if dlr == "X":
                    state.complainee_showroom.options = {"X": "X"}
                    state.complainee_showroom.update()
                    return

                if not dlr:
                    return

                try:
                    outs = await api_get(f"/complaints/dealerships/{dlr}/outlets")
                    if outs:
                        opts = {"X": "X"}
                        for o in outs:
                            opts[o] = o
                        state.complainee_showroom.options = opts
                        state.complainee_showroom.update()
                except Exception as ex:
                    print(f"Error fetching outlets: {ex}")

            # ── Handlers ─────────────────────────────
            def on_complainant_dealership_change(e):
                import asyncio

                asyncio.create_task(handle_complainant_change(e.value))

            def on_complainee_dealership_change(e):
                import asyncio

                asyncio.create_task(handle_complainee_change(e.value))

            # ── Bind Events ──────────────────────────
            state.complainant_dealership.on_value_change(
                on_complainant_dealership_change
            )

            state.complainee_dealership.on_value_change(on_complainee_dealership_change)

            # ── SAVE HANDLERS FOR POPULATION (IMPORTANT) ──
            state._handle_complainant_change = handle_complainant_change
            state._handle_complainee_change = handle_complainee_change


def build_complaint_quotation_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📋").classes("text-[20px] select-none")
            ui.label("Complaint Quotation Details").classes(
                "text-[15px] font-bold text-gray-900"
            )
        with ui.grid(columns=3).classes("w-full gap-5"):
            state.comp_quotation_no = (
                ui.input(label="Quotation Number")
                .classes("w-full")
                .props("outlined dense")
            )
            state.comp_quotation_date = (
                ui.input(
                    label="Quotation Date",
                    validation={
                        "Enter valid date (DD/MM/YYYY)": lambda v: (
                            bool(v) and is_valid_date(v)
                        )
                    },
                )
                .classes("w-full")
                .props('outlined dense type="date"')
            )
            state.comp_tcs = accounting_input(label_text="TCS")
            state.comp_total_offered = accounting_input(
                label_text="Total Offered Price"
            )
            state.comp_net_offered = accounting_input(label_text="Net Offered Price")


def build_complaint_booking_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📝").classes("text-[20px] select-none")
            ui.label("Complaint Booking Details").classes(
                "text-[15px] font-bold text-gray-900"
            )
        with ui.grid(columns=3).classes("w-full gap-5"):
            state.comp_booking_file_no = (
                ui.input(label="Booking File Number")
                .classes("w-full")
                .props("outlined dense")
            )
            state.comp_receipt_no = (
                ui.input(label="Receipt Number")
                .classes("w-full")
                .props("outlined dense")
            )
            state.comp_booking_amt = accounting_input(label_text="Booking Amount")
            mop_ops = [
                "Cash",
                "Credit Card",
                "Debit Card",
                "Net Banking",
                "UPI",
                "Other",
            ]
            state.comp_mode_of_payment = (
                ui.input(label="Mode of Payment", autocomplete=mop_ops)
                .classes("w-full")
                .props("outlined dense")
            )
            state.comp_instrument_date = (
                ui.input(
                    label="Instrument Date",
                    validation={
                        "Enter valid date (DD/MM/YYYY)": lambda v: (
                            bool(v) and is_valid_date(v)
                        )
                    },
                )
                .classes("w-full")
                .props('outlined dense type="date"')
            )
            state.comp_instrument_no = (
                ui.input(label="Instrument Number")
                .classes("w-full")
                .props("outlined dense")
            )
            state.comp_bank_name = (
                ui.input(label="Bank Name").classes("w-full").props("outlined dense")
            )


def build_complaint_remarks_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("💬").classes("text-[20px] select-none")
            ui.label("Remarks").classes("text-[15px] font-bold text-gray-900")
        with ui.grid(columns=2).classes("w-full gap-5"):
            state.complaint_date = (
                ui.input(
                    label="Date of Complaint Raised",
                    value=str(get_ist_today()),
                    validation={
                        "Enter valid date (DD/MM/YYYY)": lambda v: (
                            bool(v) and is_valid_date(v)
                        )
                    },
                )
                .classes("w-full")
                .props('outlined dense type="date"')
            )
            state.complainee_aa_name = (
                ui.input(label="Audit Assistant Name at Complainee")
                .classes("w-full")
                .props("outlined dense")
            )
            state.complainant_remarks = (
                ui.textarea(label="Remarks by Complainant *")
                .classes("w-full")
                .props("outlined dense rows=3")
            )
            state.complainant_aa_remarks = (
                ui.textarea(label="Remarks by Audit Assistant at Complainant")
                .classes("w-full")
                .props("outlined dense rows=3")
            )


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


def build_complaint_action_bar(state: FormState) -> None:
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

        async def handle_complaint_submit():
            valid, msg = state.is_valid()
            if not valid:
                state.error_msg_label.set_text(msg)
                state.error_banner.set_visibility(True)
                return

            payload = build_complaint_payload(state)
            try:
                await api_post("/complaints/save-complaint", payload)
                ui.notify(
                    "Complaint Submitted Successfully", color="green", type="positive"
                )
                ui.navigate.to("/")
            except Exception as e:
                state.error_msg_label.set_text(str(e))
                state.error_banner.set_visibility(True)

        state.submit_btn = (
            ui.button("Submit Complaint", on_click=handle_complaint_submit)
            .classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            )
            .props("no-caps unelevated")
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
    if state.booking_date and state.booking_date.value and state.model_year.value:
        booking_date = state.booking_date.value
    elif state.delivery_date and state.delivery_date.value and state.model_year.value:
        booking_date = state.delivery_date.value
    if not state.variant_id or not booking_date or not state.model_year:
        return

    try:
        booking_date = state.booking_date.value
        model_year = state.model_year.value
        preview = await api_get(
            f"/price-list/preview?variant_id={state.variant_id}&booking_date={booking_date}&model_year={model_year}"
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

    except Exception as e:
        print(e)
        pass  # best-effort; silently skip if endpoint missing


def _fs_update_live(state: FormState) -> None:
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
            offered_price = parsed_val(inp)
        except Exception:
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

    acc_listed, acc_charged = 0, 0
    if (
        hasattr(state, "acc_total_label")
        and hasattr(state, "acc_charged")
        and state.acc_charged
        and state.acc_total_label
    ):
        try:
            acc_listed = float(state.acc_total_label.text[8:].replace(",", ""))

            acc_charged = parsed_val(state.acc_charged)
        except Exception:
            pass
    acc_diff = acc_listed - acc_charged
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
        total_discount_given = (
            total_diff
            + acc_diff
            + parsed_val(state.total_discount_booking)
            - parsed_val(state.adjustment_input)
        )
        excess_val = total_discount_given - current_allowed

        if excess_val < 0:
            excess_val = 0

        state.lbl_excess_discount.set_text(f"₹{excess_val:,.2f}")
        state.lbl_allowed.set_text(f"₹{current_allowed:,.2f}")
        state.lbl_discount.set_text(f"₹{total_discount_given:,.2f}")

        if excess_val > 0:
            state.lbl_excess_discount.style("color: #D41717")  # Red
        else:
            state.lbl_excess_discount.style("color: #9CA3AF")  # Gray

        if state.lbl_excess:
            state.lbl_excess.set_text(f"₹{excess_val:,.0f}")
        # Color coding: Green if actual <= allowed (good), Red if actual > allowed (bad)
        if excess_val <= 0:
            state.lbl_excess.style("color:#6EE7B7")  # Soft green
        else:
            state.lbl_excess.style("color:#F87171")  # Soft red


# def _fs_validate_mobile(state: FormState) -> None:
#     if state.cust_mobile is None:
#         return
#     mob = (state.cust_mobile.value or "").strip()
#     if mob and not re.fullmatch(r"[6-9]\d{9}", mob):
#         state.cust_mobile.props(
#             "error error-message='Must be 10 digits starting 6 to 9'"
#         )
#     else:
#         state.cust_mobile.props(remove="error")
#     _fs_revalidate(state)


# def _fs_validate_pincode(state: FormState) -> None:
#     if state.cust_pincode is None:
#         return
#     val = (state.cust_pincode.value or "").strip()
#     if not re.fullmatch(r"\d{6}", val):
#         state.cust_pincode.props("error error-message='Must be 6 digits'")
#     else:
#         state.cust_pincode.props(remove="error")
#     _fs_revalidate(state)


# def _fs_validate_pan(state: FormState) -> None:
#     if state.cust_pan is None:
#         return
#     val = (state.cust_pan.value or "").strip().upper()
#     if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", val):
#         state.cust_pan.props("error error-message='Invalid PAN format'")
#     else:
#         state.cust_pan.props(remove="error")
#     _fs_revalidate(state)


# def _fs_validate_aadhar(state: FormState) -> None:
#     if state.cust_aadhar is None:
#         return
#     val = (state.cust_aadhar.value or "").strip()
#     if not re.fullmatch(r"\d{12}", val):
#         state.cust_aadhar.props("error error-message='Must be 12 digits'")
#     else:
#         state.cust_aadhar.props(remove="error")
#     _fs_revalidate(state)


def _fs_update_visibility(state: FormState) -> None:

    def is_checked(key: str) -> bool:
        cb = state.condition_cbs.get(key)
        return bool(cb and cb.value)

    def norm(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

    discount_visibility_rules = {
        # norm("Extra Kitty On TR cases"): is_checked("tr_case"),
        norm("Additional For POI /Corporate Customers"): is_checked("corporate")
        or is_checked("govt_employee"),
        norm("Additional For Exchange Customers"): is_checked("exchange"),
        norm("Additional For Scrappage Customers"): is_checked("scrap"),
        norm("Additional For Upward Sales Customers"): is_checked("upgrade"),
        norm("Additional Loyalty (EV TO EV)"): is_checked("loyalty_ev_ev"),
        norm("Additional Loyalty (ICE TO EV)"): is_checked("loyalty_ice_ev"),
        norm("Green Bonus"): is_checked("green_bonus"),
    }

    price_visibility_rules = {
        norm("Accessories"): is_checked("acc_kit"),
        norm("FasTag"): is_checked("fastag"),
        norm("Extended Warranty"): is_checked("ext_warr"),
        norm("AMC"): is_checked("amc"),
        norm("TCS"): is_checked("tcs"),
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

    def lbl_val(x, chr_slice=1):
        val = x.text[chr_slice:].strip().replace(",", "")
        return float(val)

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
        "booking_amt": intval(state.booking_amt),
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
        "color": val(state.car_color),
        "engine_number": val(state.engine_no),
        "model_year": val(state.model_year),
        "registration_number": val(state.vehicle_regn_no),
        "registration_date": val(state.regn_date),
        "price_adjustment": val(state.adjustment_input),
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
        payload["booking_file_incomplete"] = any(
            not bool(v.value) for v in state.delivery_cbs.values()
        )
        payload["discount_booking"] = intval(
            state.total_discount_booking
        )  # discount as per booking file
        payload["total_discount_booking"] = lbl_val(
            state.lbl_discount
        )  # after adding differences and subtracting price adjustment
        payload["price_offered_booking"] = lbl_val(state.lbl_total_offered_price)
        payload["excess_booking"] = lbl_val(state.lbl_excess)

    elif state.stage == "delivery":
        payload["stage"] = "delivery"
        payload["booking_id"] = state.booking_id
        payload["delivery_date"] = val(state.delivery_date)
        payload["is_direct_delivery"] = state.is_direct_delivery
        payload["overrides"] = state.overrides
        payload["delivery_file_incomplete"] = any(
            not bool(v.value) for v in state.delivery_cbs.values()
        )

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
@ui.page("/form")
@protected_page
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
    if transaction_id and stage == "booking":
        state.form_mode = "booking_edit"

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
    txn_data = None

    if state.stage == "delivery":
        txn_data = await resolve_form_mode(state, transaction_id)

    with ui.element("div").classes("max-w-[1200px] mx-auto p-6"):
        # ── Edit mode indicator ──────────────────────────
        if state.form_mode in ["delivery_from_booking", "delivery_edit"]:
            variant_label = (
                txn_data.get("variant_name") or txn_data.get("variant") or ""
            )

            with ui.row().classes("items-center gap-3 mb-4"):
                if state.form_mode == "delivery_from_booking":
                    title = f"📦 Converting Booking #{state.txn_id} to Delivery"

                elif state.form_mode == "delivery_edit":
                    title = f"✏️ Editing Delivery #{state.txn_id}"

                ui.label(
                    f"{title} {(' — ' + variant_label) if variant_label else ''}"
                ).classes(
                    "bg-amber-100 text-amber-800 border border-amber-200 px-3 py-1 rounded-md text-[12px] font-medium"
                )

                ui.label("Fields pre-filled from saved data").classes(
                    "text-[11px] text-gray-400"
                )

        # ── Different Forms ────────────────────────────────
        if state.form_mode == "booking_create":
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

        elif state.form_mode == "booking_edit":
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

        elif state.form_mode == "delivery_direct_create":
            ui.label("Direct Delivery MIS Form").classes("text-2xl text-bold mb-5")

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

        elif state.form_mode == "delivery_from_booking":
            ui.label("Delivery (From Booking)").classes("text-2xl text-bold mb-5")

            build_vehicle_section(state)
            build_booking_section(state)
            build_customer_section(state)
            build_conditions_section(state)
            build_prices_section(state)

            # Only delivery additions
            build_accessories_section(state)
            build_delivery_section(state)
            build_invoice_section(state)
            build_payment_section(state)
            build_audit_section(state)

        elif state.form_mode == "delivery_edit":
            ui.label("Edit Delivery Entry").classes("text-2xl text-bold mb-5")

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
    if state.form_mode == "booking_edit":
        populate_from_booking(state, state.booking_data)

    elif state.form_mode == "delivery_from_booking":
        populate_from_booking(state, state.booking_data)

    elif state.form_mode == "delivery_edit" and txn_data:
        populate_from_delivery(state, txn_data)


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════


def build_complaint_payload(state: FormState) -> dict:
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

    return {
        "stage": "complaint",
        "variant_id": state.variant_id,
        "employee_id": get_token() if get_token() else "unknown",
        "dealer_showroom_details": {
            "complainant_dealership": val(state.complainant_dealership),
            "complainant_showroom": val(state.complainant_showroom),
            "complainee_dealership": val(state.complainee_dealership),
            "complainee_showroom": val(state.complainee_showroom),
        },
        "customer_details": {
            "customer_name": val(state.cust_name),
            "contact_number": val(state.cust_mobile),
            "email": val(state.cust_email),
            "address": val(state.cust_address),
            "city": val(state.cust_city),
            "pin": val(state.cust_pincode),
            "pan": val(state.cust_pan),
            "aadhar": val(state.cust_aadhar),
        },
        "vehicle_details": {
            "vin_number": val(state.vin_no),
            "engine_number": val(state.engine_no),
            "registration_number": val(state.vehicle_regn_no),
            "registration_date": val(state.regn_date),
            "car_color": val(state.car_color),
        },
        "quotation_details": {
            "quotation_number": val(state.comp_quotation_no),
            "quotation_date": val(state.comp_quotation_date),
            "tcs_amount": intval(state.comp_tcs),
            "total_offered_price": intval(state.comp_total_offered),
            "net_offered_price": intval(state.comp_net_offered),
        },
        "booking_details": {
            "booking_file_number": val(state.comp_booking_file_no),
            "receipt_number": val(state.comp_receipt_no),
            "booking_amount": intval(state.comp_booking_amt),
            "mode_of_payment": val(state.comp_mode_of_payment),
            "instrument_date": val(state.comp_instrument_date),
            "instrument_number": val(state.comp_instrument_no),
            "bank_name": val(state.comp_bank_name),
        },
        "remarks_page": {
            "complaint_raised_date": val(state.complaint_date),
            "aa_name": val(state.complainee_aa_name),
            "remarks_by_complainant": val(state.complainant_remarks),
            "remarks_by_aa": val(state.complainant_aa_remarks),
        },
        # Price information
        "price_info": {
            "ex_showroom_price": intval(
                state.price_inputs.get("Ex Showroom Price")
                or state.price_inputs.get("Ex-Showroom Price")
            ),
            "insurance": intval(state.price_inputs.get("Insurance")),
            "registration_road_tax": intval(
                state.price_inputs.get("Registration / Road Tax")
            ),
            "discount": state.live_discount,
            "accessories_charged": intval(state.acc_charged),
        },
    }


@protected_page
@ui.page("/complaint-form")
async def complaint_form_page(
    transaction_id: int | None = None, complaint_code: str | None = None
) -> None:
    state = FormState()
    state.form_mode = (
        "complaint_edit" if transaction_id or complaint_code else "complaint_create"
    )
    state.txn_id = transaction_id
    state.edit_mode = bool(transaction_id or complaint_code)

    title = "New Complaint"
    if transaction_id:
        title = f"Edit Complaint #{transaction_id}"
    elif complaint_code:
        title = f"Edit Complaint {complaint_code}"

    render_topbar(title)

    ref = await fetch_reference_data()
    state.cars = ref.get("cars", [])
    state.variants = ref.get("variants", [])
    state.components = ref.get("components", [])
    state.outlets = ref.get("outlets", [])
    state.executives = ref.get("executives", [])
    state.accessory_map = {acc["id"]: acc for acc in ref.get("accessories", [])}
    state.complaint_dealerships = ref.get("dealerships", [])

    with ui.element("div").classes("max-w-[1100px] mx-auto p-6"):
        ui.label("Complaint MIS Form").classes("text-2xl font-bold mb-5")

        build_complaint_dealership_section(state)
        build_customer_section(state)
        build_vehicle_section(state)
        build_complaint_quotation_section(state)
        build_complaint_booking_section(state)
        build_complaint_remarks_section(state)
        build_complaint_action_bar(state)
    # Load existing complaint data if complaint_code is provided
    if complaint_code:
        try:
            # Since no single-item GET exists, we fetch all and filter
            res = await api_get("/complaints/")
            all_complaints = res.get("data", [])
            target = next(
                (
                    c
                    for c in all_complaints
                    if c.get("complaint_code") == complaint_code
                ),
                None,
            )
            if target:
                populate_from_complaint(state, target)
        except Exception as e:
            ui.notify(f"Failed to load complaint: {str(e)}", type="negative")


if __name__ in {"__main__", "__mp_main__"}:
    app.colors(primary="#e8402a")
    ui.run(
        title="AutoAudit",
        favicon="🚗",
        host="0.0.0.0",
        storage_secret=SECRET_KEY,
        reload=False,
        port=3000,
    )
