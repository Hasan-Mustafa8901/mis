"""
Automobile Sales Audit MIS — NiceGUI Frontend  (v3)
Two-page architecture:
  /      → Dashboard + Persistent MIS Transaction Table
  /form  → Data Entry Form (New + Edit mode)

Backend: FastAPI at http://localhost:8000
"""

import json
import asyncio
import re

# from utils_old import build_component_map_from_booking
import httpx
from datetime import datetime, date, timedelta
from collections import defaultdict
import calendar
from nicegui import ui, app
from utils_old import get_ist_today, disp_date  # , date_for_input
from dotenv import load_dotenv

import os
from auth_old import (
    get_token,
    logout_user,
    protected_page,
    require_roles,
    set_user,
    token_is_valid,
    clear_user,
)
from api_old import (
    api_get,
    api_post,
    api_delete,
    api_put,
    api_post_file,
    http_client,
    APIError,
    UnauthorizedError,
    ForbiddenError,
    ConnectionFailedError,
    ServerError,
)


# CONFIG & SHARED CONSTANTS
load_dotenv()

SECRET_KEY_FRONTEND = os.getenv("SECRET_KEY_FRONTEND")
BASE_URL = os.getenv("API_URL", "http://localhost:8000")


CONDITION_KEYS = {
    "Price Component": [
        ("self_insurance", "Self Insurance"),
        ("acc_kit", "Accessories"),
        ("fastag", "FasTag"),
        ("amc", "AMC"),
        ("ext_warr", "Extended Warranty"),
    ],
    "Discount Component": [
        ("exchange", "Exchange"),
        ("corporate", "Corporate"),
        ("govt_employee", "Govt Employee"),
        ("scrap", "Scrap"),
        ("green_bonus", "Green Bonus"),
        ("micro_segment", "Micro Segment (Solar Roof Top)"),
        ("sbi_yono", "SBI Yono"),
        ("power_of_twelve", "Power of 12"),
        ("sss", "Shop Share Smile (SSS)"),
        ("alliance_offer", "Alliance Offer"),
        ("loyalty_ev_ev", "Additional Loyalty (EV TO EV)"),
        ("loyalty_ice_ev", "Additional Loyalty (ICE TO EV)"),
    ],
}
# NOT FOR LLMs: These hard-coded keys should be avoided because it the whole code dependent on the field name
# NOT FOR LLMs: but for now lets keep it but in future we will discard them
COMPONENT_CONDITIONS = {
    # discounts
    "Additional for Exchange Customers": "exchange",
    "Additional for Scrappage Customers": "scrap",
    "Additional for POI /Corporate Customers": "corporate",
    "Green Bonus": "green_bonus",
    "Additional Loyalty (EV TO EV)": "loyalty_ev_ev",
    "Additional Loyalty (ICE TO EV)": "loyalty_ice_ev",
    "Micro Segment (Solar Roof Top)": "micro_segment",
    "SBI Yono": "sbi_yono",
    "Power of 12": "power_of_twelve",
    "Shop Share Smile (SSS)": "sss",
    "Alliance Offer": "alliance_offer",
    # prices
    "Accessories": "acc_kit",
    "FasTag": "fastag",
    "Extended Warranty": "ext_warr",
    "AMC": "amc",
}

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
vin_regex = re.compile(r"^[a-zA-Z]{3}\d{6}[a-zA-Z]{3}\d{5}$")  # for TATA OEM
regn_regex = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$")
bharat_regex = re.compile(r"^\d{2}BH\d{4}[A-Z]{2}$")


# SHARED CSS  (injected on both pages)
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

ui.add_head_html(
    """
    <script src="https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js"></script>
    """,
    shared=True,
)

ui.add_head_html(
    """
<style>

.ag-header-cell-label {
    justify-content: center !important;
}

.ag-header-cell-text {
    text-align: center !important;
    width: 100%;
}

</style>
""",
    shared=True,
)

ui.add_head_html(
    """
<style>

.ag-header-cell-label {
    justify-content: center !important;
}

.ag-header-cell-text {
    text-align: center !important;
    width: 100%;
}

</style>
""",
    shared=True,
)


# API HELPERS
def get_auth_headers():
    token = get_token()  # adjust if stored differently

    if not token:
        return {}

    if not token_is_valid():
        clear_user()
        return {}

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def api_request(
    method: str,
    path: str,
    **kwargs,
):

    headers = kwargs.pop("headers", {})
    auth_headers = get_auth_headers()
    headers.update(auth_headers)

    # REMOVE NONE QUERY PARAMS
    if "params" in kwargs and kwargs["params"]:
        kwargs["params"] = {k: v for k, v in kwargs["params"].items() if v is not None}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"{BASE_URL}{path}",
                headers=headers,
                timeout=20,
                **kwargs,
            )

        # TOKEN EXPIRED / INVALID
        if response.status_code == 401:
            await logout_user()
            ui.notify("Session expired. Please login again.", type="warning")
            ui.navigate.to("/login")
            return None

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as exc:
        ui.notify(f"HTTP Error: {exc.response.status_code}", type="negative")
        raise

    except httpx.ConnectError:
        ui.notify("Unable to connect to server", type="negative")
        raise


REFERENCE_CACHE: dict = {}


async def fetch_reference_data(
    force_refresh: bool = False,
) -> dict:

    global REFERENCE_CACHE

    if REFERENCE_CACHE and not force_refresh:
        return REFERENCE_CACHE

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

    for key, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            print(f"REFERENCE DATA ERROR [{key}]:", result)
            final[key] = []
        else:
            final[key] = result or []

    REFERENCE_CACHE = final

    return REFERENCE_CACHE


def get_reference_data() -> dict:
    return REFERENCE_CACHE


# GLOBAL WIDGETS & INP HELPER
def format_num_inr(num_val):
    """Format float into standard accounting formatting, e.g. 1,000.00"""
    return f"{int(num_val):,}"


def get_eval_math(val_str):
    import re

    val_clean = str(val_str).replace(",", "").strip()
    if not val_clean:
        return None
    if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", val_clean):
        return eval(val_clean)
    return None


def parsed_val(ui_input_element) -> int:
    """Safe evaluation helper to get the numeric underlying float value from accounting_input or ui.number"""
    if not ui_input_element:
        return 0
    v = getattr(ui_input_element, "value", None)
    if not v:
        return 0
    try:
        if isinstance(v, (int, float)):
            return int(v)
        v_str = str(v).replace(",", "").strip()
        import re

        if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
            res = float(eval(v_str))
            return int(res)
        return int(v_str)
    except Exception:
        return 0


def accounting_input(
    label_text: str, placeholder: str = "", container_classes: str = "w-full"
) -> ui.input:
    """Text input with inline math evaluation and blur-collapse."""
    with ui.column().classes(f"gap-0 {container_classes} mb-1"):
        inp = (
            ui.input(label=label_text, placeholder=placeholder)
            .props(
                "outlined dense input-class='text-right' input-style='text-align: right;"
            )
            .classes("w-full")
        )
        hint = ui.label("").classes(
            "text-[11px] text-green-600 font-bold ml-1 h-3 -mt-2 text-right"
        )

    def handle_eval(e):
        val = e.value
        if not val:
            hint.set_text("")
            return
        try:
            res = get_eval_math(val)
            if res is not None:
                val_clean = str(val).replace(",", "").strip()
                if val_clean != str(res) and not val_clean.replace(".", "").isdigit():
                    hint.set_text(f"= {format_num_inr(res)}")
                    hint.classes(replace="text-red-500", add="text-green-600")
                    return
                hint.set_text("")
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
        "id": app.storage.user.get("id"),
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


# TOPBAR  (shared component for both pages)
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


# LOGIN PAGE
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
                    data = await api_post(
                        "/auth/login",
                        payload={
                            "name": username.value,
                            "password": password.value,
                        },
                    )

                    if not data:
                        ui.notify("Login failed", type="negative")
                        return

                    set_user(data)
                    ui.notify("Login successful", type="positive")
                    ui.navigate.to("/")

                except UnauthorizedError:
                    ui.notify("Invalid credentials", type="negative")

                except ForbiddenError:
                    ui.notify("Access denied", type="negative")

                except ConnectionFailedError as e:
                    ui.notify(
                        str(e),
                        type="negative",
                    )

                except APIError as e:
                    ui.notify(str(e), type="negative")

                except Exception as e:
                    print("LOGIN ERROR:", e)

                    ui.notify(
                        "Something went wrong",
                        type="negative",
                    )

            ui.button("Login", on_click=handle_login).classes("w-full rounded-md")


DATE_COLUMNS = {
    "booking_date",
    "delivery_date",
    "created_at",
}


# MIS TABLE RENDERING & HELPER METHODS
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
        "booking_date",
        # add booking status
        "audit_observations",
        "outlet_name",
        "sales_executive_name",
        "customer_name",
        "mobile_number",
        "variant_name",
        "status",
    ]
    if stage == "delivery":
        ordered.insert(2, "delivery_date")

    # 2. Price components
    ordered += (
        pick("Ex")
        + pick("Insurance")
        + pick("Registration")
        + pick("AMC")
        + pick("Extended")
        + pick("FasTag")
        + pick("TCS")
    )

    # 3. Discount components
    ordered += [k for k in keys if "_actual" in k and "Discount" in k]
    ordered += (
        pick("Additional for")
        + pick("Additional Loyalty")
        + pick("Micro")
        + pick("SBI")
        + pick("Power")
        + pick("Shop")
        + pick("Alliance")
        + pick("Green")
    )

    # 4. Allowed + diff (keep near actual)

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
        "discount_booking",
        "total_discount_booking",
        "price_offered_booking",
        "excess_booking",
        "total_receivable",
        "total_received",
        "balance_amount",
        "payment_status",
        "total_actual_discount",
        "total_allowed_discount",
        "total_excess_discount",
        "created_by",
        "created_at",
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
        .replace("allowed", "(Listed)")
        .replace("diff", "(Diff)")
        .title()
    )


def should_center_column(
    key: str,
) -> bool:

    key = key.lower()

    # Do not center numeric/currency columns
    if any(
        pattern in key
        for pattern in (
            "amount",
            "price",
            "discount",
            "received",
            "balance",
            "excess",
            "payment",
            "invoice",
            "receivable",
            "allowed",
            "actual",
            "diff",
        )
    ):
        return False

    return True


def render_table(transactions, state, stage: str = "booking"):
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
        for key in DATE_COLUMNS:
            if key in t:
                t[key] = disp_date(t.get(key))

    ordered_keys = build_ordered_columns(transactions[0], stage=stage)

    if "id" in ordered_keys:
        ordered_keys.remove("id")

    for idx, t in enumerate(transactions, start=1):
        t["serial_no"] = idx

    if "serial_no" not in ordered_keys:
        ordered_keys.insert(0, "serial_no")

    if "Delivered" not in ordered_keys:
        ordered_keys.insert(3, "Delivered")

    NUMERIC_KEYS = {
        k
        for k in ordered_keys
        if any(
            tok in k
            for tok in (
                "_actual",
                "_allowed",
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
        "serial_no",
        "booking_date",
        # "audit_observations",
        "Delivered",
        # "sales_executive_name",
        "customer_name",
        # "mobile_number",
        # "variant_name",
        "delivery_date",
    }

    # Define custom widths for specific columns (optional)
    CUSTOM_WIDTHS = {
        "serial_no": 80,
        "customer_name": 150,
        "mobile_number": 150,
        "variant_name": 200,
        "booking_date": 115,
        "delivery_date": 110,
        "Delivered": 100,
    }

    col_defs = []
    col_defs.insert(
        0,
        {
            "headerCheckboxSelection": True,
            "checkboxSelection": True,
            "width": 20,
            "pinned": "left",
            "filter": False,
        },
    )
    for key in ordered_keys:
        is_num = key in NUMERIC_KEYS
        is_status = key == "status"

        col: dict = {
            "field": key,
            "headerName": clear_label(key),
            "filter": "agNumberColumnFilter" if is_num else "agTextColumnFilter",
        }

        if key == "serial_no":
            col["headerName"] = "S.No."
        elif key == "discount_booking":
            col["headerName"] = "Other Discount at booking"

        if key in pin_cols:
            col["pinned"] = "left"

        if key in CUSTOM_WIDTHS:
            col["width"] = CUSTOM_WIDTHS[key]

        if is_num:
            col[":valueFormatter"] = """
            (params) => {
                if (
                    params.value === null ||
                    params.value === undefined ||
                    params.value === ''
                ) {
                    return '—';
                }

                return '₹' + Number(params.value)
                    .toLocaleString('en-IN');
            }
            """

            col["type"] = "numericColumn"

        if is_status:
            col[":cellStyle"] = """
            (params) => {

                if (params.value === 'Excess Discount') {

                    return {
                        background: '#FEE2E2',
                        color: '#991B1B',
                        fontWeight: '600',
                        borderRadius: '4px',
                        textAlign: 'center',
                    };
                }

                return {
                    background: '#D1FAE5',
                    color: '#065F46',
                    fontWeight: '600',
                    borderRadius: '4px',
                    textAlign: 'center',
                };
            }
            """
        if is_num:
            existing_style = col.get(
                "cellStyle",
                {},
            )

            col["cellStyle"] = {
                **existing_style,
                "justifyContent": "flex-end",
                "textAlign": "right",
            }

        elif should_center_column(key):
            existing_style = col.get(
                "cellStyle",
                {},
            )

            col["cellStyle"] = {
                **existing_style,
                "justifyContent": "center",
                "textAlign": "center",
            }

        col_defs.append(col)

    grid = (
        ui.aggrid(
            {
                "columnDefs": col_defs,
                "rowData": transactions,
                "defaultColDef": {
                    "flex": 0,
                    "sortable": True,
                    "filter": True,
                    "floatingFilter": True,
                    "resizable": True,
                    "wrapHeaderText": True,
                    "autoHeaderHeight": True,
                    "wrapText": True,
                    "autoHeight": True,
                    "headerClass": "ag-center-header",
                    "cellStyle": {
                        "display": "flex",
                        "alignItems": "center",
                        "lineHeight": "18px",
                    },
                },
                "domLayout": "normal",
                "suppressColumnVirtualization": False,
                "animateRows": True,
                "rowSelection": "multiple",
                "suppressRowClickSelection": True,
                "rowHeight": 38,
                "suppressCellFocus": True,
            },
            theme="alpine",
            auto_size_columns=False,
        )
        .classes("w-full h-130")
        .style("font-family:Inter,sans-serif;font-size:13px;")
    )
    state.grid = grid

    async def go_prev():
        if state.offset <= 0:
            return
        state.offset = max(0, state.offset - state.limit)
        await state.load_data()

    async def go_next():
        print("OFFSET, LIMIT", state.offset, state.limit)
        print("Total Rows: ", state.total_rows)
        next_offset = state.offset + state.limit
        # OPTIONAL GUARD
        if next_offset >= state.total_rows:
            ui.notify("No more records", type="info")
            return
        state.offset = next_offset

        await state.load_data()

    async def on_limit_change(e):
        new_limit = int(e.value)
        # RESET TO FIRST PAGE
        state.offset = 0
        state.limit = new_limit
        await state.load_data()

    with ui.row().classes("w-full justify-between items-center px-4 py-4"):
        # LEFT SIDE
        with ui.row().classes("items-center gap-3"):
            ui.label().bind_text_from(
                state,
                "offset",
                backward=lambda o: (
                    f"Showing "
                    f"{o + 1}"
                    f" - "
                    f"{min(o + state.limit, state.total_rows)}"
                    f" of "
                    f"{state.total_rows}"
                ),
            )
            ui.space().classes("w-5")
            ui.select(
                options=[25, 50, 100],
                value=state.limit,
                label="Rows per Page",
                on_change=on_limit_change,
            ).props("dense outlined").classes("w-36")

        # RIGHT SIDE
        with ui.row().classes("gap-2"):
            ui.button(
                icon="chevron_left",
                text="Previous",
                on_click=go_prev,
            ).props("outline").classes("rounded-lg px-4")

            ui.button(
                text="Next",
                icon="chevron_right",
                on_click=go_next,
            ).props("unelevated").classes("bg-primary text-white rounded-lg px-4")

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


#   CHART HELPERS — ui.echart wrappers
#   ui.echart() accepts a plain Apache ECharts option dict.
#   No JS function strings needed — formatters use ECharts
#   template syntax ('{b}', '{c}', etc.) or plain Python values.
def render_line_chart(
    series_data: list[tuple[str, list[int]]],
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
    items: list[tuple[str, int]],
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
            return f"₹{v / 1000}K"

        tt_fmt = "{b}: ₹{c}"  # ECharts template — {b}=category {c}=value
    elif value_fmt == "raw":

        def label_fmt(v):
            return f"₹{v:,}"

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


# PAGE 1: DASHBOARD
@ui.page("/")
@require_roles("admin", "client", "audit_assistant")
async def dashboard_page() -> None:
    render_topbar("Dashboard")

    user_data = app.storage.user
    allowed_outlet_ids = user_data.get("allowed_outlet_ids", []) or []
    user_role = user_data.get("role", [""])[0].lower()

    current_transactions: list[dict] = []

    dealerships: list[dict] = []
    try:
        dealerships = await api_get("/complaints/dealerships") or []
    except Exception as e:
        ui.notify("ERROR Occured", type="negative")
        print("ERROR While loading dealerships on Dashboard: ", str(e))

    outlets: list[dict] = []
    try:
        outlets = await api_get("/outlets") or []
    except Exception as e:
        ui.notify("ERROR Occured", type="negative")
        print("ERROR While loading outlets on Dashboard: ", str(e))

    # ADMIN => unrestricted
    if user_role != "admin":
        # FILTER OUTLETS
        outlets = [o for o in outlets if o["id"] in allowed_outlet_ids]

        # FIND ALLOWED DEALERSHIP IDS
        allowed_dealership_ids = {o["dealership_id"] for o in outlets}

        # FILTER DEALERSHIPS
        dealerships = [d for d in dealerships if d["id"] in allowed_dealership_ids]

    default_dealership: str | None = None
    if user_role != "admin" and len(dealerships) == 1:
        default_dealership = str(dealerships[0]["id"])

    async def load_dashboard_data():
        nonlocal current_transactions

        params = {}

        if dealership_select.value:
            params["dealership_id"] = int(dealership_select.value)

        if outlet_select.value:
            params["outlet_id"] = int(outlet_select.value)

        txns: list[dict] = await api_get("/transactions", params=params) or []

        current_transactions = txns
        all_month_map = defaultdict(list)
        for txn in txns:
            booking_date = txn.get(
                "booking_date",
                "",
            )

            if booking_date and len(booking_date) >= 7:
                all_month_map[booking_date[:7]].append(txn)
        sorted_months_local = sorted(
            all_month_map.keys(),
            reverse=True,
        )
        month_select.options = {
            "": "All Months",
            **{ym: month_label(ym) for ym in sorted_months_local},
        }
        month_select.update()
        render_dashboard(txns)

    async def reload_backend_data(_=None):
        await load_dashboard_data()

    #  Month helpers
    def month_label(ym: str) -> str:
        try:
            y, m = ym.split("-")
            return f"{calendar.month_abbr[int(m)]} '{y[2:]}"
        except Exception:
            return ym

    DISCOUNT_KEYS = {
        "Cash Discount All Customers",
        "Additional Discount From Dealer",
        "Additional for POI /Corporate Customers",
        "Additional for Exchange Customers",
        "Additional for Scrappage Customers",
        "Additional Loyalty (EV TO EV)",
        "Additional Loyalty (ICE TO EV)",
        "Maximum benefit due to price increase",
    }

    def get_allowed_discount(t: dict) -> float:
        return sum(float(t.get(f"{k}_allowed", 0) or 0) for k in DISCOUNT_KEYS)

    #  DASHBOARD LAYOUT
    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        #  SIDEBAR
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

                    async def handle_logout():
                        await logout_user()

                    ui.button("Logout", on_click=handle_logout).props(
                        "color=red outline"
                    ).classes("w-full")

        #  MAIN CONTENT
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            #  Page header + month filter
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    ui.label("Dashboard").classes(
                        "text-[18px] font-bold text-gray-900 leading-none"
                    )
                    ui.label("Overview of all audit transactions").classes(
                        "text-[12px] text-gray-400"
                    )
                with ui.row().classes("items-center gap-3 shrink-0"):
                    # =========================================
                    # DEALERSHIP FILTER
                    # =========================================
                    if user_role == "admin":
                        default_dealership = ""

                    else:
                        default_dealership = (
                            str(dealerships[0]["id"]) if dealerships else None
                        )
                    if user_role == "admin":
                        dealership_options = {
                            "": "All Dealerships",
                            **{str(d["id"]): d["name"] for d in dealerships},
                        }

                    else:
                        dealership_options = {
                            str(d["id"]): d["name"] for d in dealerships
                        }

                    dealership_select = (
                        ui.select(
                            options=dealership_options,
                            value=default_dealership,
                            label="Dealership",
                        )
                        .classes("w-48")
                        .props("outlined dense")
                    )

                    # =========================================
                    # OUTLET FILTER
                    # =========================================

                    outlet_options = {
                        "": "All Showrooms",
                    } | {str(o["id"]): o["name"] for o in outlets}

                    outlet_select = (
                        ui.select(options=outlet_options, value="", label="Showroom")
                        .classes("w-52")
                        .props("outlined dense")
                    )

                    async def on_dealership_filter_change(e):
                        on_dealership_change(e)
                        await load_dashboard_data()

                    async def on_outlet_filter_change(_):
                        await load_dashboard_data()

                    dealership_select.on_value_change(on_dealership_filter_change)
                    outlet_select.on_value_change(on_outlet_filter_change)

                    # =========================================
                    # MONTH FILTER
                    # =========================================

                    month_select = (
                        ui.select(
                            options={"": "All Months"},
                            value="",
                            label="Month",
                        )
                        .classes("w-44")
                        .props("outlined dense")
                    )

                    def on_dealership_change(e):
                        selected = e.value

                        if not selected:
                            filtered = outlets
                        else:
                            filtered = [
                                o
                                for o in outlets
                                if str(o["dealership_id"]) == str(selected)
                            ]
                        outlet_select.options = {
                            "": "All Showrooms",
                            **{str(o["id"]): o["name"] for o in filtered},
                        }

                        outlet_select.update()

                    with (
                        ui.button(on_click=open_new_entry_dialog)
                        .classes(
                            "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-[0_3px_10px_rgba(232,64,42,0.3)]"
                        )
                        .props("no-caps unelevated")
                    ):
                        ui.icon("add").classes("text-white text-lg text-weight-bold")
                        ui.label("New Entry").classes("text-weight-bold pl-2")

            #  Dynamic content container (plain div, no extra padding)
            booking_content_area = ui.element("div").classes("w-full")
            delivery_content_area = ui.element("div").classes("w-full")

            def compute_analytics(txns: list, stage: str = "delivery") -> dict:
                """
                mode = "delivery" | "booking"
                """

                # FILTER DATA

                if stage == "delivery":
                    data = [t for t in txns if t.get("stage") == "delivery"]

                    get_allowed = lambda t: t.get("total_allowed_discount", 0) or 0
                    get_actual = lambda t: t.get("total_actual_discount", 0) or 0
                    get_excess = lambda t: t.get("total_excess_discount", 0) or 0

                else:  # booking
                    data = txns  # ALL transactions

                    get_allowed = get_allowed_discount
                    get_actual = lambda t: t.get("total_discount_booking", 0) or 0
                    get_excess = lambda t: t.get("excess_booking", 0) or 0

                # CORE METRICS

                total_entries = len(data)

                total_discount = sum(get_allowed(t) for t in data)
                total_actual_discount = sum(get_actual(t) for t in data)
                total_excess = sum(get_excess(t) for t in data)

                excess_cases = sum(1 for t in data if get_excess(t) > 0)
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

                # TIME SERIES (based on booking date)

                from collections import defaultdict

                t_month_map: dict = defaultdict(list)

                for t in data:
                    bd = t.get("booking_date", "")
                    if bd and len(bd) >= 7:
                        t_month_map[bd[:7]].append(t)

                chrono = sorted(t_month_map.keys())

                ts_lbl = [month_label(ym) for ym in chrono]

                ts_disc = [
                    sum(get_allowed(t) for t in t_month_map[ym]) for ym in chrono
                ]

                ts_exc = [sum(get_excess(t) for t in t_month_map[ym]) for ym in chrono]

                # SALES ANALYTICS

                model_sales = defaultdict(int)
                model_discount = defaultdict(int)
                model_excess = defaultdict(int)
                variant_excess = defaultdict(int)
                outlet_sales = defaultdict(int)
                outlet_disc = defaultdict(int)
                outlet_excess = defaultdict(int)
                condition_cnt = defaultdict(int)

                for t in data:
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

                    disc = get_allowed(t)
                    ex = get_excess(t)

                    model_sales[model] += 1
                    model_discount[model] += int(float(disc))

                    if ex > 0:
                        model_excess[model] += ex
                        variant_excess[vname] += ex

                    outlet_sales[outlet] += 1
                    outlet_disc[outlet] += int(float(disc))
                    outlet_excess[outlet] += ex

                    for k, v in (t.get("conditions", {}) or {}).items():
                        if v:
                            condition_cnt[k.replace("_", " ").title()] += 1

                top_excess_txns = sorted(
                    [t for t in data if get_excess(t) > 0],
                    key=lambda x: -get_excess(x),
                )[:6]

                # RETURN

                return dict(
                    total_entries=int(total_entries),
                    total_discount=int(float(total_discount)),
                    total_actual_discount=int(float(total_actual_discount)),
                    total_excess=int(float(total_excess)),
                    excess_cases=int(float(excess_cases)),
                    ok_cases=ok_cases,
                    compliance_pct=int(float(compliance_pct)),
                    avg_discount=int(float(avg_discount)),
                    avg_actual_discount=int(float(avg_actual_discount)),
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

                booking_analytics = compute_analytics(all_txns, "booking")
                delivery_analytics = compute_analytics(all_txns, "delivery")
                booking_content_area.clear()
                delivery_content_area.clear()

                with booking_content_area:
                    # ROW 1 — KPI CARDS  (pure CSS grid)
                    excess_color = (
                        "#EF4444"
                        if booking_analytics["total_excess"] > 0
                        else "#10B981"
                    )
                    #  KPI CARDS
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
                                f"₹{booking_analytics['total_actual_discount']:,}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{booking_analytics['avg_actual_discount']:,} / transaction"
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
                                f"₹{booking_analytics['total_discount']:,}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{booking_analytics['avg_discount']:,} / transaction"
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
                            ui.label(f"₹{booking_analytics['total_excess']:,}").classes(
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
                    # ROW 1 — KPI CARDS  (pure CSS grid)
                    excess_color = (
                        "#EF4444"
                        if delivery_analytics["total_excess"] > 0
                        else "#10B981"
                    )
                    #  KPI CARDS
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
                                f"₹{delivery_analytics['total_actual_discount']:,}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{delivery_analytics['avg_actual_discount']:,} / transaction"
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
                                f"₹{delivery_analytics['total_discount']:,}"
                            ).classes(
                                "text-[24px] font-bold text-[#10B981] leading-none mb-1.5 mono"
                            )
                            ui.label(
                                f"Avg ₹{delivery_analytics['avg_discount']:,} / transaction"
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
                                f"₹{delivery_analytics['total_excess']:,}"
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

                    #  SALES ANALYTICS
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

                    #  OUTLET ANALYTICS
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

                    #  EXCESS DISCOUNT ANALYSIS
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
                    #  EXCESS ANALYSIS
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
                                        ui.label(f"₹{ex:,}").classes(
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

            #  Initial render with all data
            await load_dashboard_data()

            # MONTH FILTER
            # FRONTEND ONLY
            def on_month_change(e):

                selected = e.value or ""

                filtered: list[dict] = (
                    [
                        t
                        for t in current_transactions
                        if (t.get("booking_date", "") or "").startswith(selected)
                    ]
                    if selected
                    else current_transactions
                )

                render_dashboard(filtered)

            month_select.on_value_change(on_month_change)


class MISState:
    def __init__(self) -> None:
        self.selected_dealer: int | None
        self.selected_outlet: int | None
        self.dealer_select: ui.select | None
        self.outlet_select: ui.select | None
        self.dealerships: list = []
        self.outlets: list = []
        self._load_tasks = None
        self._debounce = None

        self.stage: str = "booking"
        self.month: str | None = None
        self.grid = None
        self.load_data = []
        self.selected_ids: list[int] = []
        self.limit: int = 0
        self.offset: int = 0
        self.total_rows: int = 0
        self.total_entries = 0
        self.total_excess = 0
        self.sorted_months = {}
        self.month_map = {}


async def load_master_data(state):
    try:
        state.dealerships = await api_get("/dealerships")
        state.outlets = await api_get("/outlets")

    except UnauthorizedError:
        await logout_user()

        ui.notify(
            "Session expired. Please login again.",
            type="warning",
        )

        ui.navigate.to("/login")

    except ConnectionFailedError:
        ui.notify(
            "Unable to connect to server",
            type="negative",
        )

        state.dealerships = []
        state.outlets = []

    except APIError as e:
        print("MASTER DATA ERROR:", e)

        ui.notify(
            "Unable to load master data",
            type="negative",
        )

        state.dealerships = []
        state.outlets = []

    except Exception as e:
        print("UNEXPECTED MASTER DATA ERROR:", e)

        ui.notify(
            "Something went wrong",
            type="negative",
        )

        state.dealerships = []
        state.outlets = []


# PAGE: MIS TABLES (Booking & Delivery)
async def mis_table_page_base(stage: str, month: str | None = None) -> None:
    """Generic MIS table page logic used by both Booking and Delivery routes."""
    label = "Booking MIS" if stage == "booking" else "Delivery MIS"
    render_topbar(label)
    mstate = MISState()

    mstate.selected_dealer = None
    mstate.selected_outlet = None
    mstate.stage = stage
    mstate.month = month
    mstate.limit = 25
    mstate.offset = 0

    async def get_selected_ids():
        if not mstate.grid:
            return []
        rows: list[dict] = await mstate.grid.get_selected_rows()  # type: ignore
        ids = [r["id"] for r in rows if r.get("id")]
        mstate.selected_ids = ids
        return ids

    def month_label_local(ym: str) -> str:
        try:
            y, m = ym.split("-")
            return f"{calendar.month_abbr[int(m)]} '{y[2:]}"
        except Exception:
            return ym

    async def delete_entry() -> None:
        txn_ids = await get_selected_ids()
        try:
            if not txn_ids:
                ui.notify("Select atleast one entry.", type="info")
                return

            for id in txn_ids:
                await api_delete(f"/transactions/{id}")
            ui.notify("Deleted the entry successfully", type="positive")

            await load_data()

        except UnauthorizedError:
            await logout_user()
            ui.notify("Session Expired. Please Login in again.")
            ui.navigate.to("/login")

        except ForbiddenError:
            ui.notify("You are not allowed to delete.")

        except Exception as e:
            print("ERROR: error occured while deletion", e)
            ui.notify("Error Occured", type="negative")

    def reset_filters():
        mstate.selected_dealer = None
        mstate.selected_outlet = None

        mstate.dealer_select.set_value(None)
        mstate.outlet_select.set_value(None)

        schedule_load()

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        #  SIDEBAR
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
            for ym in mstate.sorted_months:
                is_curr = month == ym
                with ui.link(target=f"{route_path}?month={ym}").classes(
                    f"flex items-center justify-between px-4 py-1.5 text-[12.5px] font-medium {'text-[#E8402A] bg-[#FEF2F0]' if is_curr else 'text-gray-600'} hover:bg-gray-50 no-underline w-full"
                ):
                    ui.label(mstate.month_label_local(ym))
                    ui.label(str(mstate.month_map[ym])).classes(
                        "text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500"
                    )

        @ui.refreshable
        def render_header_meta():
            with ui.column().classes("gap-1"):
                title = (
                    f"{label}"
                    f"{' — ' + month_label_local(month) if month else ' — All Months'}"
                )
                ui.label(title).classes(
                    "text-[18px] font-bold text-gray-900 leading-none"
                )
                exc_txt = (
                    f" · ₹{mstate.total_excess:,} excess"
                    if mstate.total_excess > 0
                    else ""
                )
                ui.label(f"{mstate.total_entries} records{exc_txt}").classes(
                    "text-[12px] text-gray-400"
                )

        async def load_meta():
            try:
                params = {"stage": mstate.stage}

                if mstate.selected_outlet:
                    params["outlet_id"] = mstate.selected_outlet

                elif mstate.selected_dealer:
                    params["dealership_id"] = mstate.selected_dealer

                meta = await api_get("/transactions/meta", params=params)

                if not meta:
                    return

                mstate.total_entries = meta.get("total_entries", 0)
                mstate.total_excess = meta.get("total_excess", 0)
                mstate.month_map = meta.get("months", {})
                mstate.sorted_months = sorted(mstate.month_map.keys(), reverse=True)
                render_header_meta.refresh()

            except UnauthorizedError:
                await logout_user()

                ui.notify("Session expired. Please login again.", type="warning")
                ui.navigate.to("/login")

            except ConnectionFailedError:
                ui.notify("Unable to load metadata", type="negative")

            except APIError as e:
                print("LOAD META API ERROR:", e)

                ui.notify("Failed to load metadata", type="negative")

            except Exception as e:
                print("LOAD META ERROR:", e)

                ui.notify("Something went wrong", type="negative")

        # Refactor this after merge this is change now in the main branch.
        async def load_data():

            try:
                # LOAD META
                await load_meta()

                params = {"limit": mstate.limit, "offset": mstate.offset}

                if mstate.selected_outlet:
                    params["outlet_id"] = mstate.selected_outlet

                elif mstate.selected_dealer:
                    params["dealership_id"] = mstate.selected_dealer

                response = await api_get("/transactions-pages", params=params)

                if not response:
                    response = {}

                mstate.total_rows = response.get("total", 0)

                data = response.get("rows", [])

                # DELIVERY FILTER
                if mstate.stage == "delivery":
                    data = [t for t in data if t.get("stage") == "delivery"]

                # MONTH FILTER
                if mstate.month:
                    data = [
                        t
                        for t in data
                        if (t.get("booking_date", "") or "").startswith(mstate.month)
                    ]

                # SAFE UI CONTEXT
                with mstate.table_container:
                    mstate.table_container.clear()

                    render_table(data, mstate, stage=mstate.stage)

            except UnauthorizedError:
                await logout_user()

                ui.notify("Session expired. Please login again.", type="warning")

                ui.navigate.to("/login")

            except ConnectionFailedError:
                ui.notify("Unable to load transactions", type="negative")

            except APIError as e:
                print("LOAD DATA API ERROR:", e)

                ui.notify("Failed to load transactions", type="negative")

            except Exception as e:
                print("LOAD DATA ERROR:", e)

                ui.notify("Something went wrong", type="negative")

        def schedule_load():
            if mstate._debounce:
                mstate._debounce.cancel()

            mstate._debounce = ui.timer(0.3, lambda: load_data(), once=True)

        mstate.load_data = load_data

        #  MAIN CONTENT
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            with ui.row().classes("w-full items-center justify-between mb-5"):
                render_header_meta()

                await load_master_data(mstate)
                dealer_opts = {d["id"]: d["name"] for d in mstate.dealerships}
                outlet_opts = {o["id"]: o["name"] for o in mstate.outlets}

                with ui.row().classes("items-center gap-3 mb-3"):
                    mstate.dealer_select = (
                        ui.select(options=dealer_opts, label="Dealership")
                        .props("outlined dense clearable")
                        .classes("w-64")
                        .on_value_change(lambda e: on_dealer_change(e.value))
                    )

                    mstate.outlet_select = (
                        ui.select(options=outlet_opts, label="Showroom")
                        .props("outlined dense clearable")
                        .classes("w-64")
                        .on_value_change(lambda e: on_outlet_change(e.value))
                    )

                    ui.button("Reset", on_click=reset_filters).props("outline dense")

                def on_dealer_change(val):
                    mstate.selected_dealer = int(val) if val else None

                    # filter outlets by dealer
                    filtered = (
                        [
                            o
                            for o in mstate.outlets
                            if o["dealership_id"] == mstate.selected_dealer
                        ]
                        if val
                        else mstate.outlets
                    )

                    mstate.outlet_select.options = {
                        o["id"]: o["name"] for o in filtered
                    }

                    mstate.outlet_select.set_value(None)
                    mstate.selected_outlet = None

                    schedule_load()

                def on_outlet_change(val):
                    mstate.selected_outlet = int(val) if val else None
                    schedule_load()

                ## Delete Button
                with (
                    ui.button(on_click=delete_entry)
                    .classes(
                        "bg-[#FF0000] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm ml-auto"
                    )
                    .props("no-caps unelevated")
                ):
                    ui.icon("delete").classes("text-white text-lg text-weight-bold")
                    ui.label("Delete").classes("text-weight-bold pl-2")

                ## New Entry Button
                with (
                    ui.button(on_click=open_new_entry_dialog)
                    .classes(
                        "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm"
                    )
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("text-white text-lg text-weight-bold")
                    ui.label("New Entry").classes("text-weight-bold pl-2")

            with ui.card().classes(
                "w-full p-0 shadow-sm rounded-xl mb-8"
            ) as table_container:
                mstate.table_container = table_container
                await load_data()


@ui.page("/booking-mis")
@require_roles("admin", "audit_assistant")
async def booking_mis_page(month: str | None = None) -> None:
    await mis_table_page_base(stage="booking", month=month)


@ui.page("/delivery-mis")
@require_roles("admin", "audit_assistant")
async def delivery_mis_page(month: str | None = None) -> None:
    await mis_table_page_base(stage="delivery", month=month)


# COMPLAINTS TABLE RENDERER
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
        # Core Info
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
        # Customer Details
        {"field": "customer_name", "headerName": "Customer Name", "width": 160},
        {"field": "customer_mobile", "headerName": "Mobile", "width": 130},
        {"field": "customer_address", "headerName": "Address", "width": 180},
        {"field": "customer_city", "headerName": "City", "width": 120},
        {"field": "customer_pin", "headerName": "PIN", "width": 100},
        {"field": "customer_aadhar", "headerName": "Aadhar", "width": 150},
        {"field": "customer_pan", "headerName": "PAN", "width": 130},
        # Vehicle
        {"field": "car_name", "headerName": "Car Model", "width": 150},
        {"field": "variant_name", "headerName": "Variant", "width": 200},
        # Dealership Info
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
        # Quotation
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
        # Booking
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
        # Pricing
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
        # Remarks
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


# PAGE: COMPLAINTS TABLE
@ui.page("/complaints-ctrl")
@require_roles("admin")
async def complaints_ctrl_page():

    render_topbar("Complaints Control Panel")
    complaints: list[dict] = []
    total_entries: int = 0
    try:
        response: dict = await api_get("/complaints/")
        complaints: list[dict] = response.get("data", [])
        total_entries = response.get("total", 0)
    except UnauthorizedError:
        await logout_user()
        ui.notify("Session expired. Please login again.", type="warning")
        ui.navigate.to("/login")

    except ConnectionFailedError:
        ui.notify("Unable to connect to server", type="negative")
        complaints = []
        total_entries = 0
    except APIError as e:
        print("ERROR ON DASHBOARD: ", str(e))
        ui.notify("An Error Occured", type="negative")
        complaints = []
        total_entries = 0

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        #  SIDEBAR
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

                    async def handle_logout():
                        await logout_user()

                    ui.button("Logout", on_click=handle_logout).props(
                        "color=red outline"
                    ).classes("w-full")

        #  MAIN CONTENT
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

                # STATUS
                status_options_raw = []
                try:
                    status_resp = await api_get("/complaints/statuses")
                    status_options_raw = status_resp.get("data", [])
                except UnauthorizedError:
                    await logout_user()
                    ui.notify("Session expired. Please login again.", type="warning")
                    ui.navigate.to("/login")

                except ConnectionFailedError:
                    ui.notify("Unable to connect to server", type="negative")
                    status_options_raw = []
                except APIError as e:
                    print("ERROR ON DASHBOARD: ", str(e))
                    ui.notify("An Error Occured", type="negative")
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

                    try:
                        row = await get_selected_row()

                        if not row:
                            ui.notify("Select a complaint first", type="warning")

                            return

                        await api_post(
                            "/complaints/update-status",
                            payload={
                                "complaint_code": row["complaint_code"],
                                "status": (status_select.value),
                            },
                        )

                        ui.notify("Status updated", type="positive")

                    except UnauthorizedError:
                        await logout_user()
                        ui.notify(
                            "Session expired. Please login again.", type="warning"
                        )

                        ui.navigate.to("/login")

                    except ConnectionFailedError:
                        ui.notify("Unable to update status", type="negative")

                    except APIError as e:
                        print("UPDATE STATUS API ERROR:", e)
                        ui.notify("Failed to update status", type="negative")

                    except Exception as e:
                        print("UPDATE STATUS ERROR:", e)
                        ui.notify("Something went wrong", type="negative")

                ui.button("Update Status", on_click=update_status).classes(
                    "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
                ).props("no-caps unelevated")

                # REMARKS

                remarks_input = (
                    ui.textarea(label="Add Remarks")
                    .props("outlined dense")
                    .classes("w-full")
                )

                async def submit_remarks():

                    try:
                        row = await get_selected_row()

                        if not row:
                            ui.notify("Select a complaint first", type="warning")

                            return

                        remark = (remarks_input.value or "").strip()

                        if not remark:
                            ui.notify(
                                "Remark cannot be empty",
                                type="warning",
                            )

                            return

                        await api_post(
                            "/complaints/remarks",
                            payload={
                                "code": row["complaint_code"],
                                "remark": remark,
                                "submitted_by": "admin",
                            },
                        )

                        remarks_input.set_value("")

                        ui.notify(
                            "Remarks added",
                            type="positive",
                        )

                    except UnauthorizedError:
                        await logout_user()

                        ui.notify(
                            "Session expired. Please login again.",
                            type="warning",
                        )

                        ui.navigate.to("/login")

                    except ConnectionFailedError:
                        ui.notify(
                            "Unable to submit remarks",
                            type="negative",
                        )

                    except APIError as e:
                        print(
                            "SUBMIT REMARKS API ERROR:",
                            e,
                        )

                        ui.notify(
                            "Failed to submit remarks",
                            type="negative",
                        )

                    except Exception as e:
                        print(
                            "SUBMIT REMARKS ERROR:",
                            e,
                        )

                        ui.notify(
                            "Something went wrong",
                            type="negative",
                        )

                ui.button("Submit Remarks", on_click=submit_remarks).classes(
                    "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
                ).props("no-caps unelevated")

                # FLAG
                flag_options_raw = []
                try:
                    flag_resp = await api_get("/complaints/flags")
                    flag_options_raw = flag_resp.get("data", [])
                except UnauthorizedError:
                    await logout_user()
                    ui.notify("Session expired. Please login again.", type="warning")
                    ui.navigate.to("/login")

                except ConnectionFailedError:
                    ui.notify("Unable to connect to server", type="negative")
                    flag_options_raw = []
                except APIError as e:
                    print("ERROR ON DASHBOARD: ", str(e))
                    ui.notify("An Error Occured", type="negative")
                    flag_options_raw = []
                except Exception as exc:
                    print("ERROR ON DASHBOARD: ", str(exc))
                    ui.notify("An Error Occured", type="negative")
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

                    try:
                        row = await get_selected_row()

                        if not row:
                            ui.notify(
                                "Select a complaint first",
                                type="warning",
                            )

                            return

                        flag = flag_select.value

                        if not flag:
                            ui.notify(
                                "Select a flag",
                                type="warning",
                            )

                            return

                        await api_post(
                            "/complaints/update-flag",
                            payload={
                                "complaint_code": row["complaint_code"],
                                "flag": flag,
                            },
                        )

                        ui.notify(
                            "Flag updated",
                            type="positive",
                        )

                    except UnauthorizedError:
                        await logout_user()

                        ui.notify(
                            "Session expired. Please login again.",
                            type="warning",
                        )

                        ui.navigate.to("/login")

                    except ConnectionFailedError:
                        ui.notify(
                            "Unable to update flag",
                            type="negative",
                        )

                    except APIError as e:
                        print(
                            "UPDATE FLAG API ERROR:",
                            e,
                        )

                        ui.notify(
                            "Failed to update flag",
                            type="negative",
                        )

                    except Exception as e:
                        print(
                            "UPDATE FLAG ERROR:",
                            e,
                        )

                        ui.notify(
                            "Something went wrong",
                            type="negative",
                        )

                ui.button("Update Flag", on_click=update_flag).classes(
                    "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
                ).props("no-caps unelevated")


class ReportingState:
    def __init__(self):
        self.selected_dealer: int | None = None
        self.selected_outlet: int | None = None
        self.dealer_select: ui.select | None = None
        self.outlet_select: ui.select | None = None
        self.report_from: date | str = ""
        self.report_to: date | str = ""
        self.dealerships: dict = {}
        self.outlets: dict = {}


# PAGE: DAILY REPORTING
@ui.page("/daily-reporting")
@require_roles("admin", "client", "audit_assistant")
@protected_page
async def daily_reporting_page() -> None:

    rstate = ReportingState()
    render_topbar("Daily Reporting")

    today_str = get_ist_today().isoformat()
    rstate.report_from = today_str
    rstate.report_to = today_str

    #  Generic detail dialog (Pending & Incomplete)
    _dlg_state: dict = {
        "selected_ids": None,
        "tt": None,
        "d": None,
        "col": None,
        "title_el": None,
        "body_el": None,
        "dates": [],
        "is_footer": False,
        "start_date": None,
        "end_date": None,
        "all_rows": [],
        "search": "",
    }

    def apply_dialog_filter():
        rows = _dlg_state.get("all_rows", [])
        search = (_dlg_state.get("search") or "").strip().lower()

        if not search:
            refresh_detail_dialog(rows)
            return

        filtered = []

        for row in rows:
            searchable = " ".join(str(v or "").lower() for v in row.values())

            if search in searchable:
                filtered.append(row)

        refresh_detail_dialog(filtered)

    def refresh_detail_dialog(rows: list = []) -> None:

        _dlg_state["body_el"].clear()
        dialog_type = _dlg_state["col"]
        stage = _dlg_state["tt"]

        TH = (
            "border:1px solid #D1D5DB;padding:9px 13px;text-align:center;"
            "font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:.06em;color:#6B7280;background:#F9FAFB;"
            "white-space:nowrap"
        )

        TD = (
            "border:1px solid #E5E7EB;padding:8px 12px;"
            "font-size:13px;vertical-align:middle;text-align:center"
        )
        INPUT_CELL_STYLE = "w-full item-center no-wrap gap-2"

        # COMMON HEADERS
        headers = [
            ("Select", "30px"),
            ("S.No", "50px"),
            (f"{_dlg_state['tt'].title()} Date", "120px"),
            ("Customer Name", "220px"),
            ("Mobile", "120px"),
            ("Car Model", "120px"),
            ("TL", "120px"),
            ("Receiving<br>Date", "130px"),
            ("Out of Scope<br>Reason", "220px"),
            ("Approved", "90px"),
            ("Rejection<br>Reason", "220px"),
            ("Scanned Date", "130px"),
            ("MIS Entry", "130px"),
            ("Incomplete", "100px"),
            ("Incomplete Remarks", "100px"),
        ]

        # =========================================================
        # DYNAMIC ACTION HEADERS
        # =========================================================

        if dialog_type == "total_count":
            headers.extend(
                [
                    ("Received", "90px"),
                ]
            )

        elif dialog_type == "files_received":
            headers.extend(
                [
                    ("Out Of Scope", "100px"),
                ]
            )

        elif dialog_type == "files_to_be_verified":
            if stage == "booking":
                headers.extend(
                    [
                        ("Approve", "90px"),
                        ("Reject", "300px"),
                    ]
                )

        elif dialog_type == "files_scanned":
            headers.extend(
                [
                    ("Scanned", "90px"),
                ]
            )

        # TABLE
        with _dlg_state["body_el"]:
            with (
                ui.element("table")
                .props("id='details-dialog-table'")
                .style(
                    "width:100%;border-collapse:collapse;min-width:1800px;  "
                    "box-shadow:0 1px 0 #D1D5DB;"
                )
            ):
                with ui.element("thead").style("position:sticky;top:0;z-index:20"):
                    with ui.element("tr"):
                        for h, w in headers:
                            with ui.element("th").style(
                                TH
                                + "position:sticky;top:0;z-index:20;background:#F9FAFB;"
                                + (f";width:{w}" if w else "")
                            ):
                                ui.html(h)

                with ui.element("tbody"):
                    # EMPTY STATE

                    if not rows:
                        with ui.element("tr"):
                            with (
                                ui.element("td")
                                .props(f'colspan="{len(headers)}"')
                                .style(
                                    "border:1px solid #E5E7EB;padding:40px;"
                                    "text-align:center;color:#9CA3AF;font-size:13px"
                                )
                            ):
                                with ui.column().classes("items-center gap-2"):
                                    ui.label("📭").style("font-size:28px")

                                    ui.label("No records found").style(
                                        "color:#9CA3AF;font-size:13px"
                                    )

                    # ROWS
                    else:
                        for i, row in enumerate(rows):
                            row_bg = "#FFFFFF" if i % 2 == 0 else "#F9FAFB"
                            with ui.element("tr").style(f"background:{row_bg}"):
                                with ui.element("td").style(TD):

                                    async def toggle_selected(
                                        e,
                                        rid=row["id"],
                                    ):
                                        if e.value:
                                            _dlg_state["selected_ids"].add(rid)
                                        else:
                                            _dlg_state["selected_ids"].discard(rid)

                                    ui.checkbox(
                                        value=row["id"] in _dlg_state["selected_ids"],
                                        on_change=toggle_selected,
                                    )
                                # S.NO
                                with ui.element("td").style(
                                    TD + ";font-family:monospace;"
                                    "font-weight:700;"
                                    "color:#6366F1;"
                                    "background:#EEF2FF"
                                ):
                                    ui.label(str(i + 1))

                                # DATE
                                with ui.element("td").style(TD):
                                    date_ = disp_date(row.get("date"))

                                    ui.label(date_ if date_ else "—")

                                # CUSTOMER
                                with ui.element("td").style(TD + ";text-align:left"):
                                    ui.label(
                                        row.get(
                                            "customer_name",
                                            "—",
                                        )
                                    ).style("font-size:13px;font-weight:600")

                                # MOBILE
                                with ui.element("td").style(TD):
                                    ui.label(
                                        row.get(
                                            "customer_mobile",
                                            "—",
                                        )
                                    )

                                # CAR MODEL
                                with ui.element("td").style(TD):
                                    ui.label(
                                        row.get(
                                            "car_model",
                                            "—",
                                        )
                                    )

                                # TL
                                with ui.element("td").style(TD):
                                    ui.label(
                                        row.get(
                                            "team_leader",
                                            "—",
                                        )
                                    )

                                # RECEIVING DATE
                                with ui.element("td").style(TD):
                                    ui.label(
                                        disp_date(row.get("receiving_date")) or "—"
                                    )

                                # OOS REASON
                                with ui.element("td").style(TD + ";text-align:left"):
                                    ui.label(row.get("out_of_scope_reason") or "—")

                                # APPROVED
                                with ui.element("td").style(TD):
                                    ui.checkbox(
                                        value=row.get(
                                            "approved",
                                            False,
                                        )
                                    ).props("disable")

                                # REJECTION REASON
                                with ui.element("td").style(TD + ";text-align:left"):
                                    ui.label(row.get("rejection_reason") or "—")

                                # SCANNED DATE
                                with ui.element("td").style(TD):
                                    ui.label(disp_date(row.get("scanning_date")) or "—")

                                # ENTRY DATE
                                with ui.element("td").style(TD):
                                    ui.label(disp_date(row.get("entry_date")) or "—")

                                # INCOMPLETE
                                with ui.element("td").style(TD):
                                    ui.checkbox(
                                        value=row.get(
                                            "incomplete",
                                            False,
                                        )
                                    ).props("disable")

                                # INCOMPLETE REMARKS
                                with ui.element("td").style(TD + ";text-align:left"):
                                    ui.label(row.get("incomplete_remarks") or "—")

                                # DYNAMIC ACTION CELLS
                                # TOTAL COUNT -> RECEIVED
                                if dialog_type == "total_count":
                                    with ui.element("td").style(TD):
                                        with ui.row().classes(INPUT_CELL_STYLE):
                                            receiving_date = (
                                                ui.input(
                                                    value=row.get("receiving_date"),
                                                    placeholder="Receiving Date",
                                                )
                                                .classes("w-36")
                                                .props("dense outlined type='date'")
                                            )

                                            async def toggle_received(
                                                e,
                                                record_id=row["id"],
                                                record_date=receiving_date,
                                            ):

                                                try:
                                                    await api_post(
                                                        "/mis/toggle-received",
                                                        payload={
                                                            "mis_record_id": record_id,
                                                            "receiving_date": (
                                                                record_date.value
                                                            ),
                                                            "value": e.value,
                                                        },
                                                    )

                                                    await _fetch_and_show_dialog()

                                                    await reload_current_range()

                                                except UnauthorizedError:
                                                    await logout_user()

                                                    ui.notify(
                                                        "Session expired. Please login again.",
                                                        type="warning",
                                                    )

                                                    ui.navigate.to("/login")

                                                except ConnectionFailedError:
                                                    ui.notify(
                                                        "Unable to update status",
                                                        type="negative",
                                                    )

                                                except APIError as e:
                                                    print(
                                                        "TOGGLE RECEIVED API ERROR:",
                                                        e,
                                                    )

                                                    ui.notify(
                                                        "Failed to update status",
                                                        type="negative",
                                                    )

                                                except Exception as e:
                                                    print(
                                                        "TOGGLE RECEIVED ERROR:",
                                                        e,
                                                    )

                                                    ui.notify(
                                                        "Something went wrong",
                                                        type="negative",
                                                    )

                                            ui.checkbox(
                                                value=row.get(
                                                    "received",
                                                    False,
                                                ),
                                                on_change=toggle_received,
                                            )

                                # FILES RECEIVED -> OOS
                                elif dialog_type == "files_received":
                                    with ui.element("td").style(TD):
                                        with ui.row().classes(INPUT_CELL_STYLE):
                                            remarks_input = (
                                                ui.input(
                                                    value=row.get(
                                                        "out_of_scope_reason",
                                                        "",
                                                    ),
                                                    placeholder="Reason",
                                                )
                                                .props("dense outlined")
                                                .classes("w-44")
                                            )

                                            async def toggle_oos(
                                                e,
                                                record_id=row["id"],
                                                inp=remarks_input,
                                            ):

                                                try:
                                                    await api_post(
                                                        "/mis/toggle-oos",
                                                        payload={
                                                            "mis_record_id": record_id,
                                                            "value": e.value,
                                                            "reason": (
                                                                inp.value or ""
                                                            ).strip(),
                                                        },
                                                    )

                                                    await _fetch_and_show_dialog()

                                                    await reload_current_range()

                                                except UnauthorizedError:
                                                    await logout_user()

                                                    ui.notify(
                                                        "Session expired. Please login again.",
                                                        type="warning",
                                                    )

                                                    ui.navigate.to("/login")

                                                except ConnectionFailedError:
                                                    ui.notify(
                                                        "Unable to update out-of-scope status",
                                                        type="negative",
                                                    )

                                                except APIError as e:
                                                    print(
                                                        "TOGGLE OOS API ERROR:",
                                                        e,
                                                    )

                                                    ui.notify(
                                                        "Failed to update out-of-scope status",
                                                        type="negative",
                                                    )

                                                except Exception as e:
                                                    print(
                                                        "TOGGLE OOS ERROR:",
                                                        e,
                                                    )

                                                    ui.notify(
                                                        "Something went wrong",
                                                        type="negative",
                                                    )

                                            ui.checkbox(
                                                value=row.get(
                                                    "out_of_scope",
                                                    False,
                                                ),
                                                on_change=toggle_oos,
                                            )

                                # TO BE VERIFIED
                                elif dialog_type == "files_to_be_verified":
                                    if stage == "booking":
                                        # APPROVE

                                        with ui.element("td").style(TD):

                                            async def toggle_approve(
                                                e,
                                                record_id=row["id"],
                                            ):
                                                try:
                                                    await api_post(
                                                        "/mis/toggle-approve",
                                                        {
                                                            "mis_record_id": record_id,
                                                            "value": e.value,
                                                        },
                                                    )

                                                    await _fetch_and_show_dialog()

                                                    await reload_current_range()
                                                except UnauthorizedError:
                                                    await logout_user()
                                                    ui.notify(
                                                        "Session expired. Please Login again."
                                                    )
                                                    ui.navigate.to("/login")
                                                except ConnectionFailedError:
                                                    ui.notify(
                                                        "Unable to connect to the server. Please Try again after a while.",
                                                        type="negative",
                                                    )
                                                except ServerError:
                                                    ui.notify(
                                                        "Some error occured. Not Updated.",
                                                        type="negative",
                                                    )

                                                except APIError as exc:
                                                    ui.notify(
                                                        "Some Error Occured.",
                                                        type="negative",
                                                    )
                                                    print(
                                                        "ERROR OCCURED WHILE APPROVING: ",
                                                        str(exc),
                                                    )
                                                except Exception as e:
                                                    ui.notify(
                                                        "Some Error Occured.",
                                                        type="negative",
                                                    )
                                                    print(
                                                        "ERROR OCCURED WHILE APPROVING: ",
                                                        str(e),
                                                    )

                                            ui.checkbox(
                                                value=row.get(
                                                    "approved",
                                                    False,
                                                ),
                                                on_change=toggle_approve,
                                            ).props(
                                                f"disable={str(row.get('rejected', False)).lower()}"
                                            )

                                        # REJECT
                                        with ui.element("td").style(TD):
                                            with ui.row().classes(INPUT_CELL_STYLE):
                                                reason_input = (
                                                    ui.input(
                                                        value=row.get(
                                                            "rejection_reason",
                                                            "",
                                                        ),
                                                        placeholder="Reason",
                                                    )
                                                    .classes("w-44")
                                                    .props("dense outlined")
                                                )

                                                async def toggle_reject(
                                                    e,
                                                    record_id=row["id"],
                                                    inp=reason_input,
                                                ):
                                                    try:
                                                        await api_post(
                                                            "/mis/toggle-reject",
                                                            {
                                                                "mis_record_id": record_id,
                                                                "value": e.value,
                                                                "reason": inp.value
                                                                or "",
                                                            },
                                                        )

                                                        await _fetch_and_show_dialog()

                                                        await reload_current_range()

                                                    except UnauthorizedError:
                                                        await logout_user()
                                                        ui.notify(
                                                            "Session expired. Please Login again."
                                                        )
                                                        ui.navigate.to("/login")
                                                    except ConnectionFailedError:
                                                        ui.notify(
                                                            "Unable to connect to the server. Please Try again after a while.",
                                                            type="negative",
                                                        )
                                                    except ServerError:
                                                        ui.notify(
                                                            "Some error occured. Not Updated.",
                                                            type="negative",
                                                        )

                                                    except APIError as exc:
                                                        ui.notify(
                                                            "Some Error Occured.",
                                                            type="negative",
                                                        )
                                                        print(
                                                            "ERROR OCCURED WHILE APPROVING: ",
                                                            str(exc),
                                                        )
                                                    except Exception as e:
                                                        ui.notify(
                                                            "Some Error Occured.",
                                                            type="negative",
                                                        )
                                                        print(
                                                            "ERROR OCCURED WHILE APPROVING: ",
                                                            str(e),
                                                        )

                                                ui.checkbox(
                                                    value=row.get(
                                                        "rejected",
                                                        False,
                                                    ),
                                                    on_change=toggle_reject,
                                                ).props(
                                                    f"disable={str(row.get('approved', False)).lower()}"
                                                )

                                # FILES SCANNED
                                elif dialog_type == "files_scanned":
                                    with ui.element("td").style(TD):
                                        with ui.row().classes(INPUT_CELL_STYLE):
                                            scanning_date = (
                                                ui.input(
                                                    value=row.get("scanning_date"),
                                                    placeholder="Scanning Date",
                                                )
                                                .classes("w-36")
                                                .props("dense outlined type='date'")
                                            )

                                            async def toggle_scanned(
                                                e,
                                                record_id=row["id"],
                                                scan_date=scanning_date,
                                            ):
                                                try:
                                                    payload = {
                                                        "mis_record_id": record_id,
                                                        "value": e.value,
                                                        "scanning_date": scan_date.value,
                                                    }
                                                    await api_post(
                                                        "/mis/toggle-scanned",
                                                        payload=payload,
                                                    )

                                                    await _fetch_and_show_dialog()

                                                    await reload_current_range()
                                                except UnauthorizedError:
                                                    await logout_user()
                                                    ui.notify(
                                                        "Session expired. Please Login again."
                                                    )
                                                    ui.navigate.to("/login")
                                                except ConnectionFailedError:
                                                    ui.notify(
                                                        "Unable to connect to the server. Please Try again after a while.",
                                                        type="negative",
                                                    )
                                                except ServerError:
                                                    ui.notify(
                                                        "Some error occured. Not Updated.",
                                                        type="negative",
                                                    )

                                                except APIError as exc:
                                                    ui.notify(
                                                        "Some Error Occured.",
                                                        type="negative",
                                                    )
                                                    print(
                                                        "ERROR OCCURED WHILE APPROVING: ",
                                                        str(exc),
                                                    )
                                                except Exception as e:
                                                    ui.notify(
                                                        "Some Error Occured.",
                                                        type="negative",
                                                    )
                                                    print(
                                                        "ERROR OCCURED WHILE APPROVING: ",
                                                        str(e),
                                                    )

                                            ui.checkbox(
                                                value=row.get(
                                                    "scanned",
                                                    False,
                                                ),
                                                on_change=toggle_scanned,
                                            )

    # Build dialog once
    with (
        ui.dialog() as detail_dlg,
        ui.card().classes("w-[1800px] max-w-[98vw] p-6 rounded-xl shadow-2xl"),
    ):
        with ui.row().classes("w-full items-center justify-between mb-4"):

            def on_search(e):
                _dlg_state["search"] = e.value or ""
                apply_dialog_filter()

            title_el = ui.label("Details").classes(
                "text-[15px] font-bold text-gray-900"
            )
            _dlg_state["title_el"] = title_el
            ui.space()
            ui.input(placeholder="Search...").props("dense outlined clearable").classes(
                "w-1/2"
            ).on_value_change(on_search)
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

                async def bulk_delete_selected():

                    try:
                        ids = list(_dlg_state["selected_ids"])

                        if not ids:
                            ui.notify("No records selected", type="warning")
                            return

                        await api_delete(
                            "/mis/bulk-delete",
                            {
                                "ids": ids,
                            },
                        )
                        ui.notify(f"{len(ids)} records deleted", type="positive")
                        _dlg_state["selected_ids"].clear()
                        await _fetch_and_show_dialog()
                        await reload_current_range()
                    except UnauthorizedError:
                        await logout_user()
                        ui.notify("Session expired. Please Login again.")
                        ui.navigate.to("/login")
                    except ConnectionFailedError:
                        ui.notify(
                            "Unable to connect to the server. Please Try again after a while.",
                            type="negative",
                        )
                    except ServerError:
                        ui.notify(
                            "Some error occured. Not Updated.",
                            type="negative",
                        )

                    except APIError as exc:
                        ui.notify(
                            "Some Error Occured.",
                            type="negative",
                        )
                        print(
                            "ERROR OCCURED WHILE APPROVING: ",
                            str(exc),
                        )
                    except Exception as e:
                        ui.notify(
                            "Some Error Occured.",
                            type="negative",
                        )
                        print(
                            "ERROR OCCURED WHILE APPROVING: ",
                            str(e),
                        )

                ui.button(
                    "Delete Selected",
                    on_click=bulk_delete_selected,
                ).props("color=negative")

                async def export_dialog_excel():
                    title = (
                        (_dlg_state.get("col") or "details").replace("_", " ").lower()
                    )

                    filename = f"{title}-details.xlsx"
                    ui.run_javascript(f"""
                        const table = document.getElementById(
                            'details-dialog-table'
                        );

                        if (!table) return;

                        // CLONE TABLE
                        const cloned = table.cloneNode(true);

                        // REPLACE CHECKBOXES
                        cloned.querySelectorAll('td').forEach(td => {{

                            const checkbox = td.querySelector(
                                '[role="checkbox"]'
                            );

                            // No checkbox in this cell
                            if (!checkbox) {{

                                // Fill only empty cells
                                if (!td.innerText.trim()) {{
                                    td.innerHTML = 'Not Applicable';
                                }}

                                return;
                            }}

                            // Checkbox exists
                            const isChecked =
                                checkbox.getAttribute(
                                    'aria-checked'
                                ) === 'true';

                            td.innerHTML = isChecked ? 'Yes' : 'No';
                        }});


                        // REMOVE INTERACTIVE CONTROLS
                        cloned.querySelectorAll(
                            'button, textarea, select, input[type="date"]'
                        ).forEach(el => el.remove());


                        // CREATE WORKBOOK
                        const wb = XLSX.utils.book_new();

                        const ws = XLSX.utils.table_to_sheet(
                            cloned,
                            {{
                                raw: true
                            }}
                        );


                        // COLUMN WIDTHS
                        ws['!cols'] = [
                            {{ wch: 8 }},   // S.No
                            {{ wch: 14 }},  // Date
                            {{ wch: 28 }},  // Customer
                            {{ wch: 18 }},  // Mobile
                            {{ wch: 28 }},  // Model
                            {{ wch: 20 }},  // Team Leader
                            {{ wch: 16 }},  // Entry Date
                            {{ wch: 30 }},  // Remarks
                        ];


                        // STYLING
                        const range = XLSX.utils.decode_range(
                            ws['!ref']
                        );

                        for (
                            let R = range.s.r;
                            R <= range.e.r;
                            ++R
                        ) {{

                            for (
                                let C = range.s.c;
                                C <= range.e.c;
                                ++C
                            ) {{

                                const cellRef =
                                    XLSX.utils.encode_cell(
                                        {{ r: R, c: C }}
                                    );

                                const cell = ws[cellRef];

                                if (!cell) continue;

                                // FORCE DD/MM/YYYY AS TEXT
                                if (
                                    typeof cell.v === 'string' &&
                                    /^\\d{{2}}\\/\\d{{2}}\\/\\d{{4}}$/.test(cell.v)
                                ) {{
                                    cell.t = 's';
                                }}

                                // BASE STYLE
                                cell.s = {{

                                    alignment: {{
                                        vertical: 'center',
                                        horizontal: 'center',
                                        wrapText: false,
                                    }},

                                    border: {{
                                        top: {{
                                            style: 'thin',
                                            color: {{ rgb: '000000' }}
                                        }},
                                        bottom: {{
                                            style: 'thin',
                                            color: {{ rgb: '000000' }}
                                        }},
                                        left: {{
                                            style: 'thin',
                                            color: {{ rgb: '000000' }}
                                        }},
                                        right: {{
                                            style: 'thin',
                                            color: {{ rgb: '000000' }}
                                        }},
                                    }},

                                    font: {{
                                        sz: 12,
                                        name: 'Times New Roman',
                                    }},
                                }};

                                // HEADER ROW
                                if (R === 0) {{

                                    cell.s.fill = {{
                                        fgColor: {{
                                            rgb: '000080'
                                        }}
                                    }};

                                    cell.s.font = {{
                                        bold: true,
                                        color: {{
                                            rgb: 'FFFFFF'
                                        }},
                                        sz: 12,
                                        name: 'Times New Roman',
                                    }};
                                }}
                            }}
                        }}


                        // APPEND SHEET
                        XLSX.utils.book_append_sheet(
                            wb,
                            ws,
                            'Details'
                        );

                        // DOWNLOAD
                        XLSX.writeFile(
                            wb,
                            '{filename}'
                        );

                    """)

                ui.button(
                    "Export Excel",
                    on_click=export_dialog_excel,
                ).props("outline no-caps").classes(
                    "text-[13px] border-green-300 text-green-700"
                )

                async def _refresh_dlg():
                    await _fetch_and_show_dialog()

                ui.button("↻ Refresh", on_click=_refresh_dlg).props(
                    "outline no-caps"
                ).classes("text-[13px] border-gray-300 text-gray-600")
                ui.button("Close", on_click=detail_dlg.close).props(
                    "unelevated no-caps"
                ).classes("bg-[#E8402A] text-white text-[13px] px-5")

    async def _fetch_and_show_dialog():
        """
        Populate dialog using already fetched transactions.
        """
        try:
            dealer_id = (
                int(rstate.dealer_select.value) if rstate.dealer_select.value else None
            )
            outlet_id = (
                int(rstate.outlet_select.value) if rstate.outlet_select.value else None
            )
            params = {
                "record_date": _dlg_state["d"],
                "stage": _dlg_state["tt"],
                "column": _dlg_state["col"],
                "outlet_id": outlet_id,
                "dealership_id": dealer_id,
                "is_footer": _dlg_state["is_footer"],
                "start_date": rstate.report_from,
                "end_date": rstate.report_to,
            }

            rows = []

            # DERIVED VERIFIED (DELIVERY ONLY)
            if _dlg_state["tt"] == "delivery" and _dlg_state["col"] == "files_verified":
                to_verify_rows, incomplete_rows = await asyncio.gather(
                    api_get("/mis/details", params=params),
                    api_get("/mis/details", params=params),
                )

                incomplete_ids = {row["id"] for row in incomplete_rows}

                rows = [
                    row for row in to_verify_rows if row["id"] not in incomplete_ids
                ]
            else:
                rows = await api_get("/mis/details", params=params)

            if not rows:
                rows = []

        except UnauthorizedError:
            await logout_user()
            ui.notify("Session expired. Please login again.", type="warning")
            ui.navigate.to("/login")
            rows = []

        except ConnectionFailedError:
            ui.notify("Unable to load report details", type="negative")
            rows = []

        except APIError as e:
            print("MIS DETAILS API ERROR:", e)
            ui.notify("Failed to load report details", type="negative")
            rows = []

        except Exception as e:
            print("ERROR: While Loading EBD data", e)
            ui.notify("Something went wrong", type="negative")
            rows = []

        # UPDATE COUNT LABEL
        count_lbl = _dlg_state.get("count_label")

        if count_lbl:
            count = len(rows)
            message = f"{count} records" if count != 1 else "1 record"
            count_lbl.set_text(message)

        # STORE + FILTER
        _dlg_state["all_rows"] = rows
        apply_dialog_filter()

    def open_detail_dialog(row, column, is_footer) -> None:
        # STAGE
        stage = "booking" if "files_not_verified" in row else "delivery"
        _dlg_state["tt"] = stage

        # DATE / COLUMN
        _dlg_state["d"] = row.get("date")
        _dlg_state["col"] = column

        # Footer Row
        _dlg_state["is_footer"] = is_footer
        _dlg_state["start_date"] = rstate.report_from
        _dlg_state["end_date"] = rstate.report_to
        _dlg_state["selected_ids"] = set()

        # TITLE MAP
        title_map = {
            "total_count": "Total Count",
            "files_received": "Files Received",
            "files_pending": "Files Pending",
            "files_out_of_scope": "Files Out Of Scope",
            "files_to_be_verified": "Files To Be Verified",
            "files_incomplete": "Files Incomplete",
            "files_verified": "Files Verified",
            "files_approved": "Files Approved",
            "files_rejected": "Files Rejected",
            "files_in_mis": "Files in MIS",
            "files_scanned": "Files Scanned",
            "files_not_verified": "Files Not Verified",
            "rejected_files_delivered": ("Rejected Files Delivered"),
        }

        label = title_map.get(
            column,
            column,
        )

        # TITLE
        date_ = disp_date(row.get("date"))
        if is_footer:
            _dlg_state["title_el"].set_text(f"{label} — All Dates")
        else:
            _dlg_state["title_el"].set_text(f"{label} — {date_}")

        # OPEN
        detail_dlg.open()

        asyncio.create_task(_fetch_and_show_dialog())

    def render_clickable_cell(
        value,
        column,
        row,
        highlight=False,
    ):

        bg = "background:#FFF7ED;" if highlight else ""

        with (
            ui.element("td")
            .style(TABLE_DATA_STYLE + ";cursor:pointer;" + bg)
            .on(
                "click",
                lambda: open_detail_dialog(
                    row=row,
                    column=column,
                    is_footer=row.get("is_footer", False),
                ),
            )
        ):
            display = "No Data" if value is None else str(value)
            ui.label(display).style(
                "font-family:monospace;font-size:14px;font-weight:700;text-align:center"
            )

    #  Shared cell styles
    TABLE_HEADER_STYLE = (
        "border:1px solid #D1D5DB; padding:9px 14px; text-align:center;"
        "font-size:12px; font-weight:700; text-transform:capitalize;"
        "letter-spacing:.07em; color:#6B7280; background:#F9FAFB;"
        "white-space: normal; word-break: break-word; line-height:1.2;"
    )
    TABLE_DATA_STYLE = (
        "border:1px solid #E5E7EB;padding:6px 10px;"
        "font-size:15px;vertical-align:middle;text-align:center"
    )
    TABLE_FOOTER_STYLE = (
        "border:1px solid #D1D5DB;padding:9px 14px;text-align:center;"
        "font-size:15px;font-weight:700;background:#ECEEF2;color:#111827"
    )

    #  Table builder
    def build_table(stage: str, parent, rows) -> None:
        with parent:
            with ui.element("table").style(
                "width:100%;border-collapse:collapse;border:1px solid #D1D5DB;"
                "table-layout:auto;font-family:Inter,sans-serif"
            ):
                with ui.element("thead"):
                    # HEADER ROW 1

                    with ui.element("tr"):
                        # DATE
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(TABLE_HEADER_STYLE + ";min-width:100px")
                        ):
                            ui.label(f"{stage.title()} Date")

                        # TOTAL
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(
                                TABLE_HEADER_STYLE
                                + ";min-width:100px;word-break: break-all;"
                            )
                        ):
                            ui.label("Total Count")

                        # FILES RECEIVED GROUP
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                        ):
                            ui.label("Files Received")
                        # FILES PENDING GROUP
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                        ):
                            ui.label("Files Pending")
                        # FILES OUT OF SCOPE
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(
                                TABLE_HEADER_STYLE
                                + ";min-width:100px;white-space:nowrap;"
                            )
                        ):
                            ui.html("Files<br>Out of Scope")

                        # FILES TO BE VERIFIED
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(TABLE_HEADER_STYLE + ";min-width:100px")
                        ):
                            ui.html("Files<br>To Be Verified")

                        # FILES INCOMPLETE
                        with (
                            ui.element("th")
                            .props('rowspan="2"')
                            .style(TABLE_HEADER_STYLE + ";min-width:80px;")
                        ):
                            ui.html("Files<br>Incomplete")
                        # FILES SCANNED
                        with (
                            ui.element("th")
                            .props("rowspan='2'")
                            .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                        ):
                            ui.html("Files<br>Scanned")
                        # FILES IN MIS
                        with (
                            ui.element("th")
                            .props("rowspan='2'")
                            .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                        ):
                            ui.html("Files in<br>MIS")

                        # FILES VERIFIED GROUP
                        if stage == "booking":
                            with (
                                ui.element("th")
                                .props('colspan="2"')
                                .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                            ):
                                ui.label("Files Verified")
                        else:
                            with (
                                ui.element("th")
                                .props('rowspan="2"')
                                .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                            ):
                                ui.label("Files Verified")
                        if stage == "booking":
                            # FILES not verified
                            with (
                                ui.element("th")
                                .props('rowspan="2"')
                                .style(
                                    TABLE_HEADER_STYLE
                                    + ";min-width:100px;white-space:nowrap;"
                                )
                            ):
                                ui.html("Files<br>Not Verified")
                        else:
                            # FILES not verified
                            with (
                                ui.element("th")
                                .props('rowspan="2"')
                                .style(TABLE_HEADER_STYLE + ";min-width:100px;")
                            ):
                                ui.html("Rejected<br>Files Delivered")

                    # HEADER ROW 2
                    with ui.element("tr"):
                        if stage == "booking":
                            verified_headers = [
                                "Approved",
                                "Rejected",
                            ]

                            for h in verified_headers:
                                with ui.element("th").style(
                                    TABLE_HEADER_STYLE
                                    + ";background:#F0FDF4;white-space:nowrap;"
                                ):
                                    ui.label(h)

                # TABLE BODY
                with ui.element("tbody"):
                    for idx, row in enumerate(rows):
                        is_today = row["date"] == today_str

                        row_bg = (
                            "background:#EFF6FF"
                            if is_today
                            else (
                                "background:#FAFAFA"
                                if idx % 2
                                else "background:#FFFFFF"
                            )
                        )
                        is_placeholder = row.get("is_placeholder", False)

                        with ui.element("tr").style(row_bg):
                            # DATE

                            with ui.element("td").style(
                                TABLE_DATA_STYLE + ";white-space:nowrap"
                            ):
                                date = disp_date(row.get("date"))
                                ui.label(date).style("font-weight:600;color:#374151")

                            # TOTAL COUNT

                            render_clickable_cell(
                                value=None if is_placeholder else row["total_count"],
                                column="total_count",
                                row=row,
                            )

                            # FILES RECEIVED
                            render_clickable_cell(
                                value=None if is_placeholder else row["files_received"],
                                column="files_received",
                                row=row,
                            )

                            # FILES PENDING
                            render_clickable_cell(
                                value=None if is_placeholder else row["files_pending"],
                                column="files_pending",
                                row=row,
                                highlight=((row.get("files_pending") or 0) > 0),
                            )

                            # OUT OF SCOPE
                            render_clickable_cell(
                                value=None
                                if is_placeholder
                                else row["files_out_of_scope"],
                                column="files_out_of_scope",
                                row=row,
                            )

                            # TO BE VERIFIED
                            render_clickable_cell(
                                value=None
                                if is_placeholder
                                else row["files_to_be_verified"],
                                column="files_to_be_verified",
                                row=row,
                            )

                            # INCOMPLETE
                            render_clickable_cell(
                                value=None
                                if is_placeholder
                                else row["files_incomplete"],
                                column="files_incomplete",
                                row=row,
                                highlight=((row.get("files_incomplete") or 0) > 0),
                            )

                            # FILES SCANNED THIS WITH CORRECT DATA FROM THE BACKEND
                            render_clickable_cell(
                                value=None if is_placeholder else row["files_scanned"],
                                column="files_scanned",
                                row=row,
                                highlight=((row.get("files_scanned") or 0) > 0),
                            )

                            # FILES IN MIS CHANGE THIS WITH CORRECT DATA FROM THE BACKEND
                            render_clickable_cell(
                                value=None if is_placeholder else row["files_in_mis"],
                                column="files_in_mis",
                                row=row,
                                highlight=((row.get("files_in_mis") or 0) > 0),
                            )

                            # VERIFIED
                            if stage == "booking":
                                # APPROVED
                                render_clickable_cell(
                                    value=None
                                    if is_placeholder
                                    else row["files_approved"],
                                    column="files_approved",
                                    row=row,
                                )

                                # REJECTED
                                render_clickable_cell(
                                    value=None
                                    if is_placeholder
                                    else row["files_rejected"],
                                    column="files_rejected",
                                    row=row,
                                )

                            else:
                                render_clickable_cell(
                                    value=None
                                    if is_placeholder
                                    else row["files_verified"],
                                    column="files_verified",
                                    row=row,
                                )

                            # LAST COLUMN
                            if stage == "booking":
                                render_clickable_cell(
                                    value=None
                                    if is_placeholder
                                    else row["files_not_verified"],
                                    column="files_not_verified",
                                    row=row,
                                )

                            else:
                                render_clickable_cell(
                                    value=None
                                    if is_placeholder
                                    else row["rejected_files_delivered"],
                                    column="rejected_files_delivered",
                                    row=row,
                                )

                # TFOOT
                footer_columns = [
                    "total_count",
                    "files_received",
                    "files_pending",
                    "files_out_of_scope",
                    "files_to_be_verified",
                    "files_incomplete",
                    "files_scanned",
                    "files_in_mis",
                ]

                if stage == "booking":
                    footer_columns.extend(
                        ["files_approved", "files_rejected", "files_not_verified"]
                    )
                else:
                    footer_columns.extend(
                        ["files_verified", "rejected_files_delivered"]
                    )

                def get_total(column: str) -> int:
                    return sum(r.get(column, 0) or 0 for r in rows)

                with ui.element("tfoot"):
                    with ui.element("tr").style(
                        "background:#ECEEF2;border-top:2px solid #D1D5DB;"
                    ):
                        # TOTAL LABEL
                        with ui.element("td").style(TABLE_FOOTER_STYLE):
                            ui.label("TOTAL").style(
                                "font-size:12px;font-weight:800;letter-spacing:.06em;color:#374151"
                            )

                        # TOTAL VALUES
                        footer_row = {
                            "date": None,
                            "is_footer": True,
                        }
                        for column in footer_columns:
                            footer_row[column] = get_total(column)

                        for column in footer_columns:
                            render_clickable_cell(
                                value=get_total(column),
                                column=column,
                                row=footer_row,
                                highlight=False,
                            )

    # Date range helpers
    _today = get_ist_today()
    _yester = _today - timedelta(days=1)

    _RANGE_OPTIONS = {
        "today": f"Today ({_today.strftime('%d/%m/%Y')})",
        "yesterday": f"Yesterday ({_yester.strftime('%d/%m/%Y')})",
        "last7": "Last 7 Days",
        "last15": "Last 15 Days",
        "last30": "1 Month",
        "last60": "2 Months",
        "last90": "3 Months",
        "custom": "Custom Date Range",
    }

    def ensure_today_row(rows, stage):

        exists = any(r["date"] == today_str for r in rows)
        if exists:
            return rows
        base = {
            "date": today_str,
            "is_placeholder": True,
        }

        rows.append(base)

        return sorted(
            rows,
            key=lambda x: x["date"],
        )

    # Fetching EBD data counts from the daily tables
    async def load_daily_report(
        report_from: str,
        report_to: str,
    ):

        try:
            params = {"report_from": report_from, "report_to": report_to}

            if rstate.selected_outlet:
                params["outlet_id"] = rstate.outlet_select.value

            elif rstate.selected_dealer:
                params["dealership_id"] = rstate.dealer_select.value

            # FETCH REPORT DATA
            data = await api_get("/report/", params=params)

            if not data:
                data = {}

            # BOOKINGS
            booking_rows = []

            for row in data.get("bookings", []):
                row["files_to_be_verified"] = max(
                    (row.get("files_received", 0) - row.get("files_out_of_scope", 0)),
                    0,
                )

                row["files_verified"] = max(
                    (
                        row.get("files_to_be_verified", 0)
                        - row.get("files_incomplete", 0)
                    ),
                    0,
                )

                booking_rows.append(row)

            # DELIVERIES
            delivery_rows = []

            for row in data.get("deliveries", []):
                row["files_to_be_verified"] = max(
                    (row.get("files_received", 0) - row.get("files_out_of_scope", 0)),
                    0,
                )

                row["files_verified"] = max(
                    (
                        row.get("files_to_be_verified", 0)
                        - row.get("files_incomplete", 0)
                    ),
                    0,
                )

                delivery_rows.append(row)

            # PLACEHOLDER ROWS
            booking_rows = ensure_today_row(booking_rows, "booking")
            delivery_rows = ensure_today_row(delivery_rows, "delivery")

            # RENDER
            booking_wrap.clear()
            delivery_wrap.clear()
            build_table(stage="booking", rows=booking_rows, parent=booking_wrap)
            build_table(stage="delivery", rows=delivery_rows, parent=delivery_wrap)

        except UnauthorizedError:
            await logout_user()
            ui.notify("Session expired. Please login again.", type="warning")
            ui.navigate.to("/login")

        except ConnectionFailedError:
            ui.notify("Unable to load report", type="negative")

        except APIError as e:
            print("DAILY REPORT API ERROR:", e)
            ui.notify("Failed to load report", type="negative")

        except Exception as e:
            print("LOAD DAILY REPORT ERROR:", e)
            ui.notify("Something went wrong", type="negative")

    async def reload_current_range():
        selection = range_select.value or "today"
        await on_range_change(type("E", (), {"value": selection})())

    async def download_report():
        try:
            # VALIDATION
            if not rstate.selected_dealer and not rstate.selected_outlet:
                ui.notify("Select atleast a dealership or a showroom.", type="info")

                return

            params = {
                "start_date": (rstate.report_from),
                "end_date": (rstate.report_to),
            }

            if rstate.selected_outlet:
                params["outlet_id"] = rstate.selected_outlet

            elif rstate.selected_dealer:
                params["dealership_id"] = rstate.selected_dealer

            # DOWNLOAD REQUEST
            response = await http_client.get(
                f"{BASE_URL}/reports/daily",
                headers=get_auth_headers(),
                params=params,
                timeout=60,
            )

            # AUTH / STATUS
            if response.status_code == 401:
                await logout_user()
                ui.notify("Session expired. Please login again.", type="warning")
                ui.navigate.to("/login")
                return

            if response.status_code == 403:
                ui.notify(
                    "You do not have permission to download reports", type="negative"
                )

                return

            response.raise_for_status()

            # FILENAME
            filename = "daily-report.xlsx"

            content_disposition = response.headers.get("Content-Disposition")

            if content_disposition and "filename=" in content_disposition:
                filename = (
                    content_disposition.split("filename=")[-1].replace('"', "").strip()
                )

            # DOWNLOAD
            ui.download(src=response.content, filename=filename)

            ui.notify("Report downloaded successfully", type="positive")

        except ConnectionFailedError:
            ui.notify("Server unreachable", type="negative")

        except httpx.TimeoutException:
            ui.notify("Download timed out", type="negative")

        except httpx.HTTPStatusError as e:
            print("DOWNLOAD REPORT HTTP ERROR:", e)
            ui.notify(f"Download failed: {e.response.status_code}", type="negative")

        except Exception as e:
            print("DOWNLOAD REPORT ERROR:", e)
            ui.notify("Download failed", type="negative")

    # async def download_report():
    #     try:
    #         if not rstate.selected_dealer and not rstate.selected_outlet:
    #             ui.notify("Select atleast a dealership or a showroom.", type="info")
    #             return

    #         params = {
    #             "start_date": rstate.report_from,
    #             "end_date": rstate.report_to,
    #         }
    #         if rstate.selected_outlet:
    #             params["outlet_id"] = rstate.selected_outlet

    #         elif rstate.selected_dealer:
    #             params["dealership_id"] = rstate.selected_dealer

    #         async with httpx.AsyncClient() as client:
    #             response = await client.get(
    #                 f"{BASE_URL}/reports/daily",
    #                 headers=get_auth_headers(),
    #                 params=params,
    #                 timeout=60,
    #             )
    #             response.raise_for_status()
    #             filename = "daily-report.xlsx"
    #             content_disposition = response.headers.get("Content-Disposition")
    #             if content_disposition and "filename=" in content_disposition:
    #                 filename = (
    #                     content_disposition.split("filename=")[-1]
    #                     .replace('"', "")
    #                     .strip()
    #                 )
    #             ui.download(
    #                 src=response.content,
    #                 filename=filename,
    #             )
    #             ui.notify(
    #                 "Report downloaded successfully",
    #                 type="positive",
    #             )
    #     except Exception as e:
    #         ui.notify(
    #             f"Download failed: {str(e)}",
    #             type="negative",
    #         )

    # Page layout
    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # Sidebar
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

                    async def handle_logout():
                        await logout_user()

                    ui.button("Logout", on_click=handle_logout).props(
                        "color=red outline"
                    ).classes("w-full")

        # Main content
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
                await load_master_data(rstate)
                dealer_opts = {d["id"]: d["name"] for d in rstate.dealerships}
                outlet_opts = {o["id"]: o["name"] for o in rstate.outlets}

                async def on_dealer_change(e):
                    val = e.value
                    rstate.selected_dealer = int(val) if val else None
                    filtered = (
                        [
                            o
                            for o in rstate.outlets
                            if o["dealership_id"] == rstate.selected_dealer
                        ]
                        if val
                        else rstate.outlets
                    )
                    new_options = {o["id"]: o["name"] for o in filtered}
                    rstate.outlet_select.set_options(new_options)
                    rstate.outlet_select.set_value(None)
                    rstate.selected_outlet = None
                    await reload_current_range()

                async def on_outlet_change(e):
                    val = e.value
                    rstate.selected_outlet = int(val) if val else None
                    await reload_current_range()

                ui.space()
                with ui.row().classes("items-center gap-3 mb-4"):
                    rstate.dealer_select = (
                        ui.select(
                            options=dealer_opts,
                            label="Dealership",
                        )
                        .props("outlined dense clearable")
                        .classes("w-64")
                        .on_value_change(on_dealer_change)
                    )

                    rstate.outlet_select = (
                        ui.select(
                            options=outlet_opts,
                            label="Showroom",
                        )
                        .props("outlined dense clearable")
                        .classes("w-64")
                        .on_value_change(on_outlet_change)
                    )

                # Controls: range selector + custom date range pickers
                with ui.column().classes("gap-2 items-start"):
                    range_select = (
                        ui.select(
                            options=_RANGE_OPTIONS,
                            value="today",
                            label="Date Range",
                        )
                        .classes("w-52")
                        .props("outlined dense")
                        .style("font-size:13px;font-weight:500;border-radius:8px")
                    )

                    # Custom date range row
                    custom_range_row = ui.row().classes("items-center gap-2")

                    custom_range_row.set_visibility(False)

                    with custom_range_row:
                        ui.label("From:").classes(
                            "text-[12px] text-gray-500 whitespace-nowrap"
                        )

                        from_inp = (
                            ui.input(
                                label="",
                                value=today_str,
                            )
                            .props('type="date" outlined dense')
                            .classes("w-36")
                        )

                        ui.label("To:").classes(
                            "text-[12px] text-gray-500 whitespace-nowrap"
                        )

                        to_inp = (
                            ui.input(
                                label="",
                                value=today_str,
                            )
                            .props('type="date" outlined dense')
                            .classes("w-36")
                        )

            # Booking Card
            with ui.card().classes("w-full shadow-sm rounded-xl p-0 overflow-hidden"):
                with ui.row().classes(
                    "w-full items-center justify-between px-5 py-3 bg-white h-2"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes(
                            "w-2.5 h-2.5 rounded-full bg-[#6366F1]"
                        )
                        ui.label("Booking Report").classes(
                            "text-[13px] font-bold text-gray-800"
                        )
                    ui.label("Click on any cell to see details").classes(
                        "text-[11px] text-gray-600"
                    )

                booking_wrap = (
                    ui.element("div")
                    .classes("w-full overflow-x-auto")
                    .style("padding:0")
                )

            # Delivery Card
            with ui.card().classes("w-full shadow-sm rounded-xl p-0 overflow-hidden"):
                with ui.row().classes(
                    "w-full items-center justify-between px-5 py-3 bg-white h-2"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes(
                            "w-2.5 h-2.5 rounded-full bg-[#10B981]"
                        )
                        ui.label("Delivery Report").classes(
                            "text-[13px] font-bold text-gray-800"
                        )
                    ui.label("Click on any cell to see details").classes(
                        "text-[11px] text-gray-600"
                    )

                delivery_wrap = (
                    ui.element("div")
                    .classes("w-full overflow-x-auto")
                    .style("padding:0")
                )

            with ui.row().classes("gap-3 w-full"):
                ui.button(
                    "Download Report",
                    on_click=download_report,
                ).classes(
                    "bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] "
                    "text-white px-8 py-2.5 rounded-lg font-bold "
                    "shadow-lg shadow-blue-500/20"
                ).props("no-caps unelevated")
                ui.space()

                status_label = ui.label("")

                async def handle_mis_upload(e):
                    try:
                        status_label.text = "Uploading..."
                        status_label.classes("text-blue-500")
                        payload = {
                            "outlet_id": rstate.outlet_select.value,  # temporarily make it 1 change it later
                        }
                        response = await api_post_file(
                            "/mis/upload-ebd",
                            e,
                            payload,
                        )

                        created = response.get(
                            "records_created",
                            0,
                        )

                        status_label.text = f"✅ Upload successful ({created} records)"
                        status_label.classes("text-green-600")
                    except UnauthorizedError:
                        await logout_user()
                        ui.notify("Session Expired. Please Login Again")
                        ui.navigate.to("/login")

                    except APIError as ex:
                        print("Error While EBD UPLOADING: ", str(ex))
                        if "500" in str(ex).strip():
                            status_label.text = "❌ Server Side Error Contact Admin"
                        elif "422" in str(ex).strip():
                            status_label.text = "❌ Have Selected a Showroom? If not, please select and try again."

                        status_label.classes("text-red-500 text-lg fold-bold")

                ui.upload(
                    label="Upload EBD Data",
                    on_upload=handle_mis_upload,
                    auto_upload=True,
                ).props('accept=".xlsx,.xls"')

    # Wire controls
    def _get_current_range():
        return range_select.value or "custom"

    async def on_range_change(e):
        selection = e.value or "today"
        # Show date pickers only for custom
        custom_range_row.set_visibility(selection == "custom")
        if selection == "today":
            rstate.report_from = today_str
            rstate.report_to = today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

        elif selection == "yesterday":
            y = _yester.isoformat()  # yesterday
            rstate.report_from = y
            rstate.report_to = y
            await load_daily_report(rstate.report_from, rstate.report_to)

        elif selection == "last7":
            week = (_today - timedelta(days=6)).isoformat()
            rstate.report_from = week
            rstate.report_to = today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

        elif selection == "last15":
            fd = (_today - timedelta(days=14)).isoformat()
            rstate.report_from = fd
            rstate.report_to = today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

        elif selection == "last30":
            tn = (_today - timedelta(days=29)).isoformat()
            rstate.report_from = tn
            rstate.report_to = today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

        elif selection == "last60":
            fnine = (_today - timedelta(days=59)).isoformat()
            rstate.report_from = fnine
            rstate.report_to = today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

        elif selection == "last90":
            enine = (_today - timedelta(days=89)).isoformat()
            rstate.report_from = enine
            rstate.report_to = today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

        else:
            rstate.report_from = from_inp.value or today_str
            rstate.report_to = to_inp.value or today_str
            await load_daily_report(rstate.report_from, rstate.report_to)

    async def on_from_change(e):
        if _get_current_range() == "custom":
            await load_daily_report(
                e.value or today_str,
                to_inp.value or today_str,
            )

    async def on_to_change(e):
        if _get_current_range() == "custom":
            await load_daily_report(
                from_inp.value or today_str,
                e.value or today_str,
            )

    range_select.on_value_change(on_range_change)
    from_inp.on_value_change(on_from_change)
    to_inp.on_value_change(on_to_change)

    # Initial render (default: custom = today only)
    await load_daily_report(today_str, today_str)


class SettingsState:
    def __init__(self) -> None:
        self.outlets: list[dict] = []
        self.dealerships: list[dict] = []


# PAGE: SETTINGS
@ui.page("/settings")
@require_roles("admin")
async def settings_page():
    sstate = SettingsState()

    def get_id_by_name(items: list[dict], name: str) -> int | None:
        for item in items:
            if item["name"] == name:
                return item["id"]

        return None

    # FETCH MASTER DATA
    await load_master_data(state=sstate)

    outlet_names = [o["name"] for o in sstate.outlets]
    dealer_names = [d["name"] for d in sstate.dealerships]

    # PAGE
    render_topbar("Settings")

    with ui.column().classes("w-full"):
        with ui.card().classes(
            "max-w-[1100px] mx-auto p-8 w-full shadow-sm rounded-xl mt-6"
        ):
            ui.label("Register New Users").classes("text-xl font-bold mb-4")

            with ui.row().classes("w-full gap-6"):
                # LEFT FORM
                with ui.column().classes("flex-1 gap-4"):
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
                        ui.input(
                            "Password",
                            password=True,
                            password_toggle_button=True,
                        )
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )

                    role = (
                        ui.select(["Admin", "Client", "Audit Assistant"], label="Role")
                        .props("outlined dense")
                        .classes("w-[500px]")
                    )

                    # MULTI OUTLET SELECT
                    ui.label("Allowed Showrooms").classes(
                        "text-sm font-medium text-gray-700 mt-2"
                    )

                    outlet_checkboxes = []

                    with ui.card().classes(
                        "w-[500px] max-h-[260px] overflow-auto border rounded-lg p-3"
                    ):
                        for outlet_data in sstate.outlets:
                            checkbox = ui.checkbox(outlet_data["name"])

                            outlet_checkboxes.append(
                                {
                                    "id": outlet_data["id"],
                                    "checkbox": checkbox,
                                }
                            )

                    # ROLE CHANGE
                    def on_role_change(e):
                        if e.value == "Admin":
                            for item in outlet_checkboxes:
                                item["checkbox"].value = False
                                item["checkbox"].disable()

                        else:
                            for item in outlet_checkboxes:
                                item["checkbox"].enable()

                    # ACTIONS
                    with ui.row().classes("gap-3 mt-4"):

                        async def handle_register():
                            selected_outlet_ids = [
                                item["id"]
                                for item in outlet_checkboxes
                                if item["checkbox"].value
                            ]
                            # VALIDATION
                            if not name.value or not password.value:
                                ui.notify("Name and Password required", type="negative")
                                return
                            if not username.value:
                                ui.notify("Username required", type="negative")
                                return

                            if not role.value:
                                ui.notify("Role is required", type="negative")
                                return

                            if role.value != "Admin" and not selected_outlet_ids:
                                ui.notify(
                                    "At least one showroom is required", type="negative"
                                )

                                return

                            # PAYLOAD
                            payload = {
                                "name": name.value.strip(),
                                "username": username.value.strip(),
                                "password": password.value,
                                "role": (role.value.replace(" ", "_").lower()),
                                "allowed_outlet_ids": (
                                    [] if role.value == "Admin" else selected_outlet_ids
                                ),
                            }

                            try:
                                await api_post("/auth/register", payload=payload)
                                ui.notify("User created successfully", type="positive")

                                # RESET FORM
                                name.value = ""
                                username.value = ""
                                password.value = ""
                                role.value = None

                                for item in outlet_checkboxes:
                                    checkbox = item["checkbox"]

                                    checkbox.value = False

                                    checkbox.enable()

                            except UnauthorizedError:
                                await logout_user()

                                ui.notify(
                                    "Session expired. Please login again.",
                                    type="warning",
                                )

                                ui.navigate.to("/login")

                            except ForbiddenError:
                                ui.notify(
                                    "You do not have permission to create users",
                                    type="negative",
                                )

                            except ConnectionFailedError:
                                ui.notify("Server unreachable", type="negative")

                            except APIError as e:
                                print("USER REGISTRATION API ERROR:", e)
                                ui.notify(str(e), type="negative")

                            except Exception as e:
                                print("USER REGISTRATION ERROR:", e)
                                ui.notify("Something went wrong", type="negative")

                        ui.button("Create User", on_click=handle_register).classes(
                            "bg-[#E8402A] text-white px-4 py-2 rounded-md"
                        )

                        ui.button(
                            "Reset",
                            on_click=lambda: [
                                setattr(name, "value", ""),
                                setattr(username, "value", ""),
                                setattr(password, "value", ""),
                                setattr(role, "value", None),
                                [
                                    setattr(item["checkbox"], "value", False)
                                    for item in outlet_checkboxes
                                ],
                            ],
                        ).props("outline")

                # RIGHT PANEL
                with ui.column().classes(
                    "w-[280px] bg-gray-50 rounded-lg p-4 border text-sm text-gray-600"
                ):
                    ui.label("Guidelines").classes("font-semibold text-gray-800 mb-2")
                    ui.label("• Use a unique username")
                    ui.label("• Assign correct role carefully")
                    ui.label("• Showroom assignment controls visibility")
                    ui.label("• Multiple showrooms supported")
                    ui.label("• Password should be secure")
                    ui.separator()
                    ui.label("Roles").classes("font-semibold mt-2 text-gray-800")
                    ui.label("Admin → Full access")
                    ui.label("Client → Dealership access")
                    ui.label("Audit Assistant → Assigned showroom access")
        # USERS TABLE
        users = []
        try:
            users = await api_get("/auth/users")
        except UnauthorizedError:
            await logout_user()
            ui.notify("Session expired. Please Login again", type="warning")
            ui.navigate.to("/login")
        except ForbiddenError:
            ui.notify("Access Denied", type="negative")
            ui.navigate.to("/")
        except ConnectionFailedError:
            ui.notify("Unable to connect to the server", type="negative")
            users = []
        except APIError as exc:
            print("ERROR FETCHING USERS:", exc)
            ui.notify(str(exc), type="negative")
            users = []

        except Exception as e:
            print("ERROR FETCHING USERS:", e)
            ui.notify(str(e), type="negative")
            users = []

        row_data = []

        for user in users:
            allowed_outlets = user.get("allowed_outlets", []) or []

            # ADMIN
            if not allowed_outlets:
                outlet_display = "All Outlets"

            else:
                outlet_display = ", ".join(outlet["name"] for outlet in allowed_outlets)

            row = {
                "name": user["name"],
                "username": user["username"],
                "outlet_name": outlet_display,
                "role": (str(user["role"]).replace("_", " ").title()),
            }

            row_data.append(row)

        with ui.column().classes("w-full items-center mt-8"):
            with ui.card().classes(
                "max-w-[1100px] w-full p-6 rounded-2xl shadow border"
            ):
                ui.label("Users").classes("text-xl font-semibold text-gray-800 mb-4")

                ui.aggrid(
                    {
                        "columnDefs": [
                            {
                                "headerName": "Name",
                                "field": "name",
                            },
                            {
                                "headerName": "Username",
                                "field": "username",
                            },
                            {
                                "headerName": "Can View",
                                "field": "outlet_name",
                                "wrapText": True,
                            },
                            {
                                "headerName": "Role",
                                "field": "role",
                            },
                        ],
                        "defaultColDefs": {
                            "wraptext": True,
                            "flex": 1,
                            "autoHeight": True,
                        },
                        "rowData": row_data,
                    }
                ).classes("w-full h-[500px] ag-theme-balham")

    with ui.column().classes("w-full items-center"):
        with ui.card().classes(
            "max-w-[900px] w-full p-8 mt-8 rounded-2xl shadow-lg border border-gray-100"
        ):
            # Header
            ui.label("Upload Price List").classes("text-xl font-semibold text-gray-800")
            ui.label("Upload Excel file with pricing details").classes(
                "text-sm text-gray-400 mb-4"
            )

            ui.separator()

            # Form Section
            with ui.column().classes("w-full gap-4 mt-4"):
                with ui.row().classes("w-full gap-4"):
                    valid_from = (
                        ui.date_input(
                            label="Valid From",
                            value=get_ist_today().isoformat(),
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

            # Upload Area
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
                        # Validation
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

                        await fetch_reference_data(force_refresh=True)

                        status_label.text = "✅ Upload successful"
                        status_label.classes("text-green-600")

                    except UnauthorizedError:
                        await logout_user()
                        ui.notify(
                            "Session expired. Please login again.", type="warning"
                        )
                        ui.navigate.to("/login")
                    except ForbiddenError:
                        ui.notify(
                            "You don't have the permission to create dealerships",
                            type="negative",
                        )

                    except ConnectionFailedError:
                        ui.notify("Unable to load transaction", type="negative")
                    except ServerError:
                        ui.notify(
                            "Some Error Occured while updating file, please try again.",
                            type="negative",
                        )

                    except APIError as e:
                        print("LOAD TRANSACTION API ERROR:", e)
                        ui.notify("Failed to load transaction", type="negative")
                    except Exception as ex:
                        status_label.text = f"❌ {str(ex)}"
                        status_label.classes("text-red-500")

                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                ).props("accept=.xlsx").classes("mt-4")

            # Footer Note
            ui.label("Only .xlsx files are supported").classes(
                "text-xs text-gray-400 mt-3 text-center"
            )
    with ui.column().classes("w-full items-center gap-6"):
        # DEALERSHIP CARD
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
                    # Refresh Cache
                    await fetch_reference_data(force_refresh=True)
                    ui.notify("Dealership created", type="positive")
                    d_name.value = ""
                    d_code.value = ""
                except UnauthorizedError:
                    await logout_user()
                    ui.notify("Session expired. Please login again.", type="warning")
                    ui.navigate.to("/login")
                except ForbiddenError:
                    ui.notify(
                        "You don't have the permission to create dealerships",
                        type="negative",
                    )

                except ConnectionFailedError:
                    ui.notify("Unable to load transaction", type="negative")

                except APIError as e:
                    print("LOAD TRANSACTION API ERROR:", e)
                    ui.notify("Failed to load transaction", type="negative")

                except Exception as e:
                    print("LOAD TRANSACTION ERROR:", e)
                    ui.notify("Something went wrong", type="negative")

            ui.button("Create Dealership", on_click=create_dealership).classes(
                "mt-3 bg-[#E8402A] text-white"
            )
        # OUTLET CARD
        with ui.card().classes("w-full max-w-[900px] p-6 rounded-2xl shadow border"):
            ui.label("Create Showroom").classes("text-lg font-semibold")

            o_name = ui.input("Outlet Name").props("outlined dense").classes("w-full")
            o_code = ui.input("Outlet Code").props("outlined dense").classes("w-full")
            o_address = ui.input("Address").props("outlined dense").classes("w-full")
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
                                sstate.dealerships, dealership_select.value
                            ),
                        },
                    )
                    # Refresh Cache
                    await fetch_reference_data(force_refresh=True)
                    ui.notify("Outlet created", type="positive")

                    o_name.value = ""
                    o_code.value = ""
                    o_address.value = ""
                    dealership_select.value = None

                except UnauthorizedError:
                    await logout_user()
                    ui.notify("Session expired. Please login again.", type="warning")
                    ui.navigate.to("/login")
                except ForbiddenError:
                    ui.notify(
                        "You don't have the permission to create dealerships",
                        type="negative",
                    )

                except ConnectionFailedError:
                    ui.notify("Unable to load transaction", type="negative")

                except APIError as e:
                    print("LOAD TRANSACTION API ERROR:", e)
                    ui.notify("Failed to load transaction", type="negative")

                except Exception as e:
                    print("LOAD TRANSACTION ERROR:", e)
                    ui.notify("Something went wrong", type="negative")

            ui.button("Create Outlet", on_click=create_outlet).classes(
                "mt-3 bg-[#E8402A] text-white"
            )

        # EMPLOYEE CARD
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

            async def create_employee():
                try:
                    await api_post(
                        "/sales-executive",
                        {
                            "name": e_name.value,
                            "outlet_id": get_id_by_name(
                                sstate.outlets, outlet_select.value
                            ),
                            "designation": e_designation.value,
                        },
                    )
                    # Refresh Cache
                    await fetch_reference_data(force_refresh=True)
                    ui.notify("Employee created", type="positive")

                    e_name.value = ""
                    e_designation.value = ""
                    outlet_select.value = None

                except UnauthorizedError:
                    await logout_user()
                    ui.notify("Session expired. Please login again.", type="warning")
                    ui.navigate.to("/login")
                except ForbiddenError:
                    ui.notify(
                        "You don't have the permission to create dealerships",
                        type="negative",
                    )

                except ConnectionFailedError:
                    ui.notify("Unable to load transaction", type="negative")

                except APIError as e:
                    print("LOAD TRANSACTION API ERROR:", e)
                    ui.notify("Failed to load transaction", type="negative")

                except Exception as e:
                    print("LOAD TRANSACTION ERROR:", e)
                    ui.notify("Something went wrong", type="negative")

            ui.button("Create Employee", on_click=create_employee).classes(
                "mt-3 bg-[#E8402A] text-white"
            )


# PAGE-LOCAL FORM STATE
class FormController:
    def __init__(self, state):
        self.state = state

    async def initialize(self):
        await self.load_reference_data()
        await self.load_transaction_if_needed()

        self.build_form()

        if self.state.transaction_data:
            self.hydrate_form()

        self.refresh_visibility()
        self.refresh_live_calculations()

        self.attach_handlers()

    async def load_reference_data(self):

        data = get_reference_data()

        if not data:
            data = await fetch_reference_data()

        self.state.cars = data.get("cars", [])
        self.state.variants = data.get("variants", [])
        self.state.outlets = data.get("outlets", [])
        self.state.executives = data.get("executives", [])
        self.state.components = data.get("components", [])
        self.state.accessories = data.get("accessories", [])
        self.state.dealerships = data.get("dealerships", [])

    async def load_transaction_if_needed(self):
        transaction_id = self.state.transaction_id
        if not transaction_id:
            return

        try:
            data = await api_get(f"/transactions/{transaction_id}")
            if not data:
                return

            self.state.transaction_data = data

        except UnauthorizedError:
            await logout_user()
            ui.notify("Session expired. Please login again.", type="warning")
            ui.navigate.to("/login")

        except ConnectionFailedError:
            ui.notify("Unable to load transaction", type="negative")

        except APIError as e:
            print("LOAD TRANSACTION API ERROR:", e)
            ui.notify("Failed to load transaction", type="negative")

        except Exception as e:
            print("LOAD TRANSACTION ERROR:", e)
            ui.notify("Something went wrong", type="negative")

    def build_form(self):
        build_full_form(self.state)

    def hydrate_form(self):
        hydrate_form(
            self.state,
        )

    def refresh_visibility(self):
        refresh_visibility(self.state)

    def refresh_live_calculations(self):
        _fs_update_live(self.state)

    def attach_handlers(self):
        attach_form_handlers(self.state)


class FormState:
    """
    All mutable state for a single /form session.
    Instantiated inside form_page() — never shared across sessions.
    """

    def __init__(self):
        self.transaction_id = None
        self.transaction_data = None

        self.is_hydrating = False
        self.form_ready = False
        self.handlers_attached = False

        self.is_edit_mode = False
        self.is_delivery = False
        self.is_direct_delivery = False
        self.is_conversion_flow = False
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

        self.visible_price_rows: dict[str, bool] = {}
        self.visible_discount_rows: dict[str, bool] = {}

        # UI element refs — accessories / audit
        self.acc_select: ui.select | None = None
        self.acc_charged: ui.number | None = None
        self.acc_total_label: ui.label | None = None
        self.accessory_allowed: ui.number | None = None
        self.accessory_map: dict = {}
        self.accessory_rows: list = []

        self.audit_obs: ui.textarea | None = None
        self.audit_action: ui.textarea | None = None

        # booking/delivery file status complete and incomplete
        self.booking_file_incomplete: None | ui.checkbox = None
        self.delivery_file_incomplete: None | ui.checkbox = None
        self.booking_file_incomplete_remarks: None | ui.textarea = None
        self.delivery_file_incomplete_remarks: None | ui.textarea = None

        # UI element refs — actions
        self.submit_btn: ui.button | None = None
        self.error_banner: ui.html | None = None
        self.error_msg_label: ui.html | None = None

        self.listed_prices: dict[str, int] = {}
        self.price_listed_labels: dict[str, ui.label] = {}
        self.discount_listed_labels: dict[str, ui.label] = {}
        self.discount_inputs = {}
        self.discount_match_toggles = {}
        self.discount_given_labels = {}  # already used elsewhere

        # Customer Ledger vars
        self.total_receivable: ui.label | None = None
        self.total_received: ui.label | None = None
        self.balance_amount: ui.label | None = None
        self.ledger_adjustment: ui.input | None = None
        self.ledger_adjustment_remarks: ui.input | None = None
        self.adjustment_type: ui.select | str = ""

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
        self.lbl_allowed_lv: ui.label | None = None
        self.lbl_discount_lv: ui.label | None = None
        self.lbl_excess_lv: ui.label | None = None
        self.total_given: ui.label | None = None
        self.total_allowed: ui.label | None = None
        self.lbl_total_listed_price: ui.label | None = None  # a
        self.lbl_total_offered_price: ui.label | None = None  # b
        self.lbl_total_diff_price: ui.label | None = None  # = a-b
        self.lbl_total_listed_discount: ui.label | None = None

        # new one
        self.discount_given_labels: ui.label | dict = {}
        self.discount_diff_labels: ui.label | dict = {}
        self.adjustment_input: ui.input | None = None
        self.stage_toggle = None
        self.delivery_mode = None
        self.booking_select = None
        self.total_discount_booking = 0.0
        self.other_discount_delivery = 0.0

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

        if getattr(self, "is_hydrating", False):
            return True, ""

        if self.form_mode == "complaint_create" or self.form_mode == "complaint_edit":
            return self._validate_complaint()

        def _val(f):
            return (str(f.value) or "").strip() if f else ""

        def _val_upper(f):
            return (f.value or "").strip().upper() if f else ""

        if self.variant_id in [None, "", 0]:
            return False, "Please select a Car and Variant."

        outlet_val = getattr(
            self.outlet_select,
            "value",
            None,
        )

        if outlet_val in [None, "", 0]:
            return False, "Please select Showroom."

        exec_val = getattr(
            self.exec_select,
            "value",
            None,
        )

        if exec_val in [None, "", 0]:
            return False, "Please select Sale Executive."

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

        delivery_validation_modes = [
            "delivery_edit",
            "delivery_direct_create",
            "delivery_from_booking",
        ]
        if self.form_mode in delivery_validation_modes:
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

    # Find Car ID
    car_id = None
    for car in state.cars:
        if car["name"].strip().lower() == (car_name or "").strip().lower():
            car_id = car["id"]
            break

    if not car_id:
        return

    # Set Car
    state.car_select.set_value(car_id)
    state.car_id = car_id

    # Build Variant Options
    variants = [v for v in state.variants if v["car_id"] == car_id]

    options = {v["id"]: v["variant_name"] for v in variants}

    # FORCE update options
    state.variant_select.clear()
    state.variant_select.options = options
    state.variant_select.update()

    # Find Variant ID
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

    # Set Variant
    ui.timer(0.15, lambda: state.variant_select.set_value(variant_id), once=True)
    state.variant_id = variant_id


def populate_from_booking(state: FormState, data: dict):
    if not data:
        return

    # Booking
    if state.booking_date:
        state.booking_date.set_value(data.get("booking_date"))

    if state.booking_amt:
        state.booking_amt.set_value(data.get("booking_amt", ""))
    if state.booking_receipt_num:
        state.booking_receipt_num.set_value(data.get("booking_receipt_num", ""))

    # Customer
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

    # Vehicle
    if state.cust_file_no:
        state.cust_file_no.set_value(data.get("customer_file_number", ""))

    if state.vin_no:
        state.vin_no.set_value(data.get("vin_number", ""))

    if state.engine_no:
        state.engine_no.set_value(data.get("engine_number", ""))

    if state.vehicle_regn_no:
        state.vehicle_regn_no.set_value(data.get("registration_number", ""))

    if state.car_color:
        state.car_color.set_value(data.get("color", ""))

    if state.regn_date:
        state.regn_date.set_value(data.get("registration_date", ""))

    if state.model_year:
        state.model_year.set_value(data.get("model_year", ""))

    # Variant / Car
    _map_car_and_variant(state, data)

    # Conditions
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
        cb.set_value(conditions.get(key, False))


def populate_price_and_discount(
    state,
    booking_data: dict,
    *,
    edit_mode: bool = False,
) -> None:
    """
    Auto-fill all price and discount inputs from booking_data.

    Args:
        state:        FormState with price_inputs / discount_inputs populated.
        booking_data: Raw dict from the API — may contain both list prices and
                      actual (charged) amounts under different key patterns.
        edit_mode:    When True (editing an existing transaction), the "charged"
                      column is filled from *_actual keys so the auditor sees
                      what was entered previously, not the price list defaults.

    Populates:
        state.listed_prices          : price-list reference values (always)
        state.price_listed_labels    : the ₹ display in the Listed column
        state.discount_listed_labels : allowed amount display
        state.discount_given_labels  : given amount display (read-only)
        state.discount_diff_labels   : per-row difference display
        Price and discount inputs    : filled with listed OR actual values
    """
    if not booking_data:
        return

    #  Build two maps: listed (price list) and actual (what was charged)
    # listed_map:  component name → price-list value
    # charged_map: component name → what was actually charged/given
    listed_map: dict = {}
    charged_map: dict = {}

    for raw_key, val in booking_data.items():
        if val is None:
            continue
        is_actual = raw_key.endswith("_actual")
        is_allowed = raw_key.endswith("_allowed") or raw_key.endswith("_listed")
        clean = re.sub(r"_(actual|allowed|listed)$", "", raw_key).strip()
        norm = re.sub(r"[^a-z0-9]", "", clean.lower())

        if is_actual:
            charged_map[clean] = val
            charged_map[norm] = val
        elif is_allowed:
            listed_map[clean] = val
            listed_map[norm] = val
        else:
            # Plain key — treat as both listed and charged default
            listed_map[clean] = val
            listed_map[norm] = val
            # Only use as charged default if edit_mode not explicitly set;
            # in edit_mode we prefer *_actual keys.
            if not edit_mode:
                charged_map.setdefault(clean, val)
                charged_map.setdefault(norm, val)

    def _resolve_listed(name: str):
        norm = re.sub(r"[^a-z0-9]", "", name.lower())
        return listed_map.get(name) or listed_map.get(norm)

    def _resolve_charged(name: str):
        norm = re.sub(r"[^a-z0-9]", "", name.lower())
        return charged_map.get(name) or charged_map.get(norm)

    #  Price inputs
    for name, inp in state.price_inputs.items():
        listed_val = _resolve_listed(name)
        charged_val = _resolve_charged(name) if edit_mode else listed_val

        # Always store and display the listed price
        if listed_val is not None:
            state.listed_prices[name] = listed_val
            lbl = state.price_listed_labels.get(name)
            if lbl:
                lbl.set_text(f"₹{float(listed_val):,}")

        # Fill the charged input:
        #   edit_mode  → restore what the auditor entered previously (actual)
        #   new entry  → pre-fill with listed price so auditor can match/deviate
        fill_val = (
            charged_val if (edit_mode and charged_val is not None) else listed_val
        )
        if fill_val is not None:
            inp.set_value(format_num_inr(fill_val))

    # Discount inputs + read-only displays
    for name, inp in state.discount_inputs.items():
        listed_val = _resolve_listed(name)
        charged_val = _resolve_charged(name)

        if listed_val is not None:
            state.listed_prices[name] = listed_val
            a_lbl = state.discount_listed_labels.get(name)
            if a_lbl:
                a_lbl.set_text(f"₹{float(listed_val):,}")

        if edit_mode and charged_val is not None:
            inp.set_value(format_num_inr(charged_val))

        # Update the read-only Given label
        g_lbl = state.discount_given_labels.get(name)
        if g_lbl:
            booking_actuals: dict = getattr(state, "booking_discount_actuals", {}) or {}
            display_val = booking_actuals.get(name, charged_val)
            if display_val is not None:
                g_lbl.set_text(f"₹{float(display_val):,.2f}")


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


async def resolve_form_mode(
    state: FormState,
    stage: str,
    transaction_id: int | None,
    mode: str | None,
):

    txn_data = None

    try:
        # LOAD TRANSACTION IF AVAILABLE
        if transaction_id:
            txn_data = await api_get(f"/transactions/{transaction_id}")

            state.edit_mode = True

        # BOOKING
        if stage == "booking":
            if transaction_id:
                state.form_mode = "booking_edit"

            else:
                state.form_mode = "booking_create"

        # DELIVERY
        elif stage == "delivery":
            # DIRECT DELIVERY
            if mode == "direct":
                if transaction_id:
                    state.form_mode = "delivery_edit"

                else:
                    state.form_mode = "delivery_direct_create"

            # DELIVERY FROM BOOKING
            else:
                if transaction_id and txn_data:
                    txn_stage = txn_data.get("stage")

                    # EXISTING DELIVERY
                    if txn_stage == "delivery":
                        state.form_mode = "delivery_edit"

                    # BOOKING → DELIVERY
                    else:
                        state.form_mode = "delivery_from_booking"

                else:
                    state.form_mode = "delivery_direct_create"

        # SAVE TRANSACTION DATA
        if txn_data:
            state.transaction_data = txn_data

            state.booking_data = txn_data

            state.txn_id = transaction_id

        return txn_data

    except UnauthorizedError:
        await logout_user()

        ui.notify("Session expired. Please login again.", type="warning")

        ui.navigate.to("/login")

    except ConnectionFailedError:
        ui.notify("Unable to load transaction", type="negative")

    except APIError as e:
        print("RESOLVE FORM MODE API ERROR:", e)

        ui.notify("Failed to load transaction", type="negative")

    except Exception as e:
        print("RESOLVE FORM MODE ERROR:", e)

        ui.notify("Something went wrong", type="negative")

    return None


async def hydrate_vehicle_section(
    state,
    txn,
):

    state.is_hydrating = True

    try:
        car_id = txn.get("car_id")
        variant_id = txn.get("variant_id")
        outlet_id = txn.get("outlet_id")
        exec_id = txn.get("sales_executive_id")
        delivery_date = txn.get("delivery_date")
        registration_date = txn.get("registration_date")
        registration_number = txn.get("registration_number")

        # CAR
        if car_id:
            state.car_select.set_value(car_id)

            # IMPORTANT
            await _fs_on_car_change(
                car_id,
                state,
                preserve_variant=True,
            )

        # VARIANT
        if variant_id:
            state.variant_select.set_value(variant_id)

            state.variant_id = variant_id

        # OUTLET
        if outlet_id:
            state.outlet_select.set_value(outlet_id)

        # EXECUTIVE
        if exec_id:
            state.exec_select.set_value(exec_id)

        # Delivery Date
        if delivery_date and state.delivery_date:
            state.delivery_date.set_value(delivery_date)
        if registration_date and state.regn_date:
            state.regn_date.set_value(registration_date)
        if registration_number and state.vehicle_regn_no:
            state.vehicle_regn_no.set_value(registration_number)

    finally:
        state.is_hydrating = False
        _fs_revalidate(state)


# FORM SECTION BUILDERS
FORM_COLUMNS = 3


def build_vehicle_section(state: FormState) -> None:
    car_opts = {
        car["id"]: car["name"]
        for car in sorted(state.cars, key=lambda x: x["name"].lower())
    }
    outlet_opts = {
        outlet["id"]: outlet["name"]
        for outlet in sorted(state.outlets, key=lambda x: x["name"].lower())
    }
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
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.variant_select = (
                ui.select(
                    options={},
                    with_input=True,
                    label="Variant *",
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.car_color = (
                ui.input(label="Car Colour").classes("w-full").props("outlined dense")
            )
            state.exec_select = (
                ui.select(
                    options=exec_opts,
                    with_input=True,
                    label="Team Leader *",
                )
                .classes("w-full")
                .props("outlined dense")
            )
            if state.form_mode not in ["complaint_create", "complaint_edit"]:
                state.cust_file_no = (
                    ui.input(label="Customer File No *")
                    .classes("w-full")
                    .props("outlined dense")
                )
                state.model_year = (
                    ui.input(
                        label="Model Year *",
                        value="2026",
                        placeholder="e.g. 2024",
                        validation={
                            "Must be 4 digits": lambda value: (
                                len(str(value)) == 4 and str(value).isdigit()
                            )
                        },
                    )
                    .classes("w-full")
                    .props("outlined dense")
                )
                state.outlet_select = (
                    ui.select(
                        options=outlet_opts,
                        label="Outlet *",
                    )
                    .classes("w-full")
                    .props("outlined dense")
                )

            if state.stage == "delivery":
                state.vin_no = (
                    ui.input(
                        label="VIN Number *",
                        placeholder="XXX000000XXX00000",
                        validation={
                            "Invalid VIN Number": lambda v: bool(
                                vin_regex.match(str(v))
                            )
                        },
                    )
                    .classes("w-full uppercase")
                    .props("outlined dense")
                )
                state.delivery_date = (
                    ui.input(
                        label="Delivery Date *",
                        validation={
                            "Enter valid date": lambda v: bool(
                                v
                            )  # browser already validates
                        },
                    )
                    .classes("w-full")
                    .props('type="date" outlined dense')
                )
                state.engine_no = (
                    ui.input(
                        label="Engine Number *",
                        validation={
                            "Enter 10–20 alphanumeric characters": lambda v: (
                                10 <= len(str(v).strip()) <= 20
                                and str(v).strip().isalnum()
                            )
                        },
                    )
                    .classes("w-full uppercase")
                    .props("outlined dense")
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
                        validation={"Enter valid date": lambda v: not v or bool(v)},
                    )
                    .classes("w-full")
                    .props('outlined dense type="date"')
                )


def build_customer_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("👤").classes("text-[20px] select-none")
            ui.label("Customer Details").classes("text-[15px] font-bold text-gray-900")

        # Basic Info
        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
            state.cust_name = (
                ui.input(label="Name *", placeholder="Full name")
                .classes("w-full")
                .props("outlined dense")
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
            )
            state.cust_city = (
                ui.input(label="City *").classes("w-full").props("outlined dense")
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
            )

            state.cust_aadhar = (
                ui.input(
                    label="Aadhar",
                    placeholder="12 digits",
                    validation={
                        "Must be 12 digits": lambda v: (
                            len(re.sub(r"\D", "", v or "")) == 12
                        )
                    },
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.cust_other_id = (
                ui.input(label="Other ID Proof")
                .classes("w-full")
                .props("outlined dense")
            )


def build_conditions_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        # Header
        with ui.row().classes(
            "w-full items-center gap-2 mb-0 pb-2 border-b border-gray-100"
        ):
            ui.label("☑️").classes("text-[20px] select-none")
            ui.label("Sale Conditions").classes("text-[15px] font-bold text-gray-900")

        # Sections
        for section_name, conditions in CONDITION_KEYS.items():
            # Section Title
            ui.label(section_name).classes("text-[14px] font-bold mt-0 mb-0")

            ui.separator().classes("m-0")

            # Checkbox Grid
            with ui.grid(columns=FORM_COLUMNS + 1).classes("w-full gap-y-2 mb-0"):
                for key, label in conditions:
                    state.condition_cbs[key] = (
                        ui.checkbox(label)
                        .props("dense color=primary")
                        .classes("text-gray-700 font-medium")
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
                    ui.checkbox(label, value=False)
                    .props("dense color=primary")
                    .classes("text-gray-700 font-medium")
                )


def build_booking_section(state: FormState):
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        # Header
        _section_header(
            emoji="📖",
            title="Booking Details",
            subtitle="Record booking details",
            icon_bg="bg-blue-50",
        )

        # Basic Info
        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
            state.booking_date = (
                ui.input(
                    label="Booking Date *",
                    value=str(get_ist_today()),
                    validation={
                        "Enter valid date (DD-MM-YYYY)": lambda v: (
                            bool(v) and is_valid_date(v)
                        )
                    },
                )
                .classes("w-full")
                .props("type='date' outlined dense")
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


# build_prices_section  — the single UI entry-point
def build_prices_section(state: FormState) -> None:
    """
    Render the unified Price, Discount, and Accessories card.

    Reads from state:
        stage ("booking" | "delivery")
        is_direct_delivery (bool)
        components (list of component dicts from /components API)
        booking_data (dict | None) — for delivery stage reference column
        conditions (dict) — current sale conditions (exchange, corporate…)
    """
    stage = getattr(state, "stage", "booking")
    is_delivery = stage == "delivery"
    is_direct = getattr(state, "is_direct_delivery", True)
    booking_data = getattr(state, "booking_data", None) or {}
    conditions = {
        key: cb.value
        for key, cb in getattr(
            state,
            "condition_cbs",
            {},
        ).items()
    }

    price_comps = sorted(
        [c for c in state.components if c.get("type") == "price"],
        key=lambda x: x.get("order", 99),
    )

    discount_comps = sorted(
        [c for c in state.components if c.get("type") == "discount"],
        key=lambda x: x.get("order", 99),
    )

    # For delivery stage, build a lookup of booking actuals for the ref column
    booking_actual_map: dict = {}
    if is_delivery and booking_data:
        booking_actual_map = {
            k.replace("_actual", "").strip(): v
            for k, v in booking_data.items()
            if k.endswith("_actual")
        }

    # OUTER CARD
    with ui.card().classes("w-full rounded-xl shadow-sm mb-4"):
        with ui.column().classes("w-full gap-0 p-5"):
            # CARD HEADER
            with ui.row().classes(
                "w-full items-center gap-2 pb-3 border-b border-gray-100 flex-nowrap"
            ):
                # Header
                _section_header(
                    emoji="💲",
                    title="Prices & Discount",
                    subtitle="Manage vehicle pricing, discounts, and adjustments",
                    icon_bg="bg-blue-50",
                )

                if is_delivery and not is_direct:
                    ui.badge("Delivery Stage", color="blue").classes(
                        "items-center"
                    ).props("outline")
                elif is_direct:
                    ui.badge("Direct Delivery", color="purple").classes(
                        "items-center"
                    ).props("outline")
                else:
                    ui.badge("Booking Stage", color="green").classes(
                        "items-center"
                    ).props("outline")

            # SECTION 1 — PRICE CHARGED AS PER BOOKS
            ui.label("Price charged as per books of accounts").classes(
                "text-[14px] font-semibold tracking-[0.9px] uppercase text-black mt-4 mb-1"
            )

            if not price_comps:
                ui.label("No price components — check /components API.").classes(
                    "text-xs text-gray-400 italic"
                )
            else:
                # Column headers
                with ui.row().classes(
                    "w-full items-center gap-2 pb-1 border-b border-gray-200"
                ):
                    ui.label("Particular").classes(f"{_HDR} flex-1 text-left")
                    ui.label("Price list").classes(f"{_HDR} w-28")
                    if is_delivery and not is_direct:
                        ui.label("Booking").classes(f"{_HDR} w-28")
                    ui.label("Match").classes(f"{_HDR} w-20 text-center")
                    ui.label("Charged").classes(f"{_HDR} w-36")
                    ui.label("Difference").classes(f"{_HDR} w-24")

                # One row per price component
                for comp in price_comps:
                    name = comp["name"]

                    with ui.row().classes(
                        "w-full items-center gap-2 py-1.5 border-b border-gray-50"
                    ) as row_el:
                        state.price_rows[name] = row_el

                        # Particular label
                        ui.label(name).classes(f"{_LABEL} flex-1")

                        # Listed price (populated later by populate_price_and_discount)
                        listed_lbl = ui.label("₹—").classes(f"{_MONO} w-28")
                        state.price_listed_labels[name] = listed_lbl

                        # Booking reference column (delivery only)
                        if is_delivery and not is_direct:
                            bk_val = booking_actual_map.get(name)
                            bk_txt = (
                                format_num_inr(bk_val) if bk_val is not None else "—"
                            )
                            ui.label(f"₹{bk_txt}").classes(
                                f"{_MONO} w-28 text-blue-400"
                            )

                        # Match toggle
                        with ui.element("div").classes("w-20 flex justify-center"):
                            toggle = (
                                ui.switch("").props("dense color=green").classes("m-0")
                            )
                            state.price_match_toggles[name] = toggle

                        # Charged input
                        inp = accounting_input(
                            "", placeholder="₹0", container_classes="w-36"
                        ).props("dense")
                        state.price_inputs[name] = inp

                        # Difference label
                        diff_lbl = ui.label("—").classes(
                            f"{_MONO_SM} w-24 text-gray-400"
                        )
                        state.price_diff_labels[name] = diff_lbl

            with ui.row().classes(
                "w-full items-center gap-3 mt-3 pt-3 border-t-2 border-gray-200"
            ):
                ui.label("Total on-road price").classes(
                    "text-[14px] font-bold uppercase tracking-wide text-gray-700 flex-1"
                )
                with ui.row().classes("items-baseline gap-1"):
                    ui.label("Listed").classes("text-[13px] text-black text-left")
                    state.lbl_total_listed_price = ui.label("₹—").classes(
                        "text-[15px] font-mono text-black-500 w-28 text-right"
                    )
                ui.element("div").classes("w-20")
                with ui.row().classes("items-baseline gap-1"):
                    ui.label("Charged").classes("text-[13px] text-black text-left")
                    state.lbl_total_charged_price = ui.label("₹—").classes(
                        "text-[15px] font-mono font-semibold text-black w-28 text-right"
                    )
                # ui.element("div").classes("w-20")
                with ui.row().classes("items-baseline gap-1"):
                    ui.label("Diff").classes("text-[10px] text-black text-left")
                    state.lbl_total_diff_price = ui.label("₹—").classes(
                        "text-[15px] font-mono w-20 text-right text-black"
                    )
                ui.element("div").classes("w-1")

            # Note: lbl_total_offered_price kept as alias so _fs_update_live
            # doesn't crash if called from old code referencing that attribute.
            state.lbl_total_offered_price = state.lbl_total_charged_price

            # SECTION 2 — DISCOUNTS

            ui.label("Discounts offered as per books of accounts").classes(
                "text-[14px] font-bold tracking-[0.9px] uppercase text-black mt-6 mb-1"
            )

            #  [A] Non-direct delivery: show booking-time discounts read-only
            # Auditors need to see what was agreed at booking without being able
            # to accidentally edit it during the delivery audit.
            if is_delivery or is_direct:
                booking_disc_map: dict = {}
                if booking_data:
                    # Pull Discount actuals from booking data.
                    for raw_k, raw_v in booking_data.items():
                        if raw_v is None:
                            continue
                        clean = raw_k.replace("_actual", "").strip()
                        # only keep keys that match a discount component name
                        for dc in discount_comps:
                            if dc["name"].lower() == clean.lower() or re.sub(
                                r"[^a-z0-9]", "", dc["name"].lower()
                            ) == re.sub(r"[^a-z0-9]", "", clean.lower()):
                                booking_disc_map[dc["name"]] = raw_v
                                break

                state.booking_discounts_actuals = booking_disc_map

                with ui.element("div").classes(
                    "w-full rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 mb-3"
                ):
                    ui.label("Discounts at time of booking").classes(
                        "text-[10px] font-bold uppercase tracking-wide text-blue-500 mb-2"
                    )
                    #  Price component differences (actual - allowed)
                    price_component_diff_total = 0

                    for comp in price_comps:
                        comp_name = comp["name"]

                        actual_val = float(booking_data.get(f"{comp_name}_actual") or 0)

                        allowed_val = float(
                            booking_data.get(f"{comp_name}_allowed") or 0
                        )
                        diff = allowed_val - actual_val

                        # only count excess charged amount
                        if diff > 0:
                            price_component_diff_total += diff

                    # merge discount_booking into map (without mutating original)
                    booking_disc_map_ui = dict(booking_disc_map or {})
                    # Other Discount
                    discount_booking_val = int(
                        booking_data.get("discount_booking") or 0
                    )

                    if discount_booking_val:
                        booking_disc_map_ui["Other Discount"] = discount_booking_val
                    # Differences
                    if price_component_diff_total > 0:
                        booking_disc_map_ui["Price Difference"] = (
                            price_component_diff_total
                        )
                    # Adjustment
                    adjustment_booking_val = int(
                        booking_data.get("adjustment_booking") or 0
                    )

                    if adjustment_booking_val:
                        booking_disc_map_ui["Adjustment"] = -adjustment_booking_val

                    if booking_disc_map_ui:
                        for disc_name, disc_val in booking_disc_map_ui.items():
                            cond_key = _condition_badge(disc_name, conditions)
                            with ui.row().classes(
                                "w-full items-center py-1 border-b border-blue-100"
                            ):
                                with ui.row().classes(
                                    "flex-1 items-center gap-2 min-w-0"
                                ):
                                    ui.label(disc_name).classes(
                                        "text-[13px] text-blue-800 truncate"
                                    )
                                    if cond_key:
                                        ui.badge(
                                            cond_key.replace("_", "").title()
                                        ).props("outline").classes(
                                            "text-[9px] shrink-0 text-blue-600"
                                        )
                                    with ui.element("div").classes(
                                        "flex-1 flex justify-end"
                                    ):
                                        ui.label(f"₹{int(disc_val):,}").classes(
                                            "text-[13px] font-mono font-semibold text-blue-700 w-24 text-right"
                                        )

                        # total INCLUDING booking file discount
                        booking_disc_total = sum(
                            int(v or 0) for v in booking_disc_map_ui.values()
                        )
                        with ui.row().classes("w-full items-center pt-2 mt-1"):
                            ui.label("Total booking discount").classes(
                                "flex-1 text-[12px] font-bold text-blue-700 uppercase tracking-wide"
                            )
                            ui.label(f"₹{booking_disc_total:,}").classes(
                                "text-[14px] font-mono font-bold text-blue-700 w-28 text-right"
                            )
                    else:
                        ui.label("No discount data from booking.").classes(
                            "text-[12px] text-blue-400 italic"
                        )

            with ui.row().classes(
                "w-full items-center gap-2 py-1 border-b border-gray-200 mt-2"
            ):
                ui.label("Particular").classes(f"{_HDR} flex-1 text-left")
                ui.label("Allowed").classes(f"{_HDR} w-28")
                ui.label("Match").classes(f"{_HDR} w-20 text-center")
                ui.label("Given").classes(f"{_HDR} w-36")
                ui.label("Difference").classes(f"{_HDR} w-24")

            for comp in discount_comps:
                name = comp["name"]
                is_default = name in _DEFAULT_DISC
                cond_key = _condition_badge(name, conditions)

                initially_visible = is_default or (
                    cond_key is not None and bool(conditions.get(cond_key))
                )

                with ui.row().classes(
                    "w-full items-center gap-2 py-1.5 border-b border-gray-50"
                ) as disc_row_el:
                    state.discount_rows[name] = disc_row_el
                    disc_row_el.set_visibility(initially_visible)

                    # Particular
                    with ui.row().classes("flex-1 items-center gap-2 min-w-0"):
                        ui.label(name).classes(f"{_LABEL} truncate")
                        if cond_key and not is_default:
                            ui.badge(cond_key.replace("_", " ").title()).props(
                                "outline"
                            ).classes("text-[9px] shrink-0")

                    # Allowed
                    allowed_lbl = ui.label("₹—").classes(f"{_MONO} w-28")
                    state.discount_listed_labels[name] = allowed_lbl

                    # Match toggle
                    with ui.element("div").classes("w-20 flex justify-center"):
                        toggle = ui.switch("").props("dense color=green").classes("m-0")
                        state.discount_match_toggles[name] = toggle

                    # Given input
                    inp = accounting_input(
                        "", placeholder="₹0", container_classes="w-36"
                    ).props("dense")
                    state.discount_inputs[name] = inp

                    # Difference
                    diff_lbl = ui.label("—").classes(
                        "text-[11px] font-mono w-24 text-right text-gray-400"
                    )
                    state.discount_diff_labels[name] = diff_lbl

            # [D] Other Discount Row
            with ui.row().classes(
                "w-full items-center gap-2 py-2.5 border-b border-dashed border-gray-200 mt-2"
            ):
                ui.label("Other discount").classes(f"{_LABEL} flex-1 font-medium")

                # spacer to align with table
                ui.label("—").classes(f"{_MONO} w-28")
                ui.element("div").classes("w-20")

                # NOTE:
                # total_discount_booking inputs
                # are now used as "other discount"

                if not is_delivery:
                    state.total_discount_booking = accounting_input(
                        "", placeholder="₹0", container_classes="w-36"
                    ).props("dense")

                # Renamed this to other discount in delivery
                else:
                    state.other_discount_delivery = accounting_input(
                        "", placeholder="₹0", container_classes="w-36"
                    ).props("dense")

                ui.element("div").classes("w-25")

            # [D] Adjustment Row
            with ui.row().classes(
                "w-full items-center gap-2 py-2.5 border-b border-dashed border-gray-200 mt-2"
            ):
                ui.label("Adjustment").classes(f"{_LABEL} flex-1 font-medium")

                # spacer to align with table
                ui.label("—").classes(f"{_MONO} w-28")
                ui.element("div").classes("w-20")

                state.adjustment_input = accounting_input(
                    "", placeholder="₹0", container_classes="w-36"
                ).props("dense")

                ui.element("div").classes("w-25")

            # SECTION 3 — DISCOUNT SUMMARY BAR
            with ui.row().classes(
                "w-full items-center gap-4 mt-3 pt-3 border-t-2 border-gray-200"
            ):
                ui.label("Discount summary").classes(
                    "text-[14px] font-bold uppercase tracking-wide text-black flex-1"
                )
                with ui.row().classes("items-baseline gap-1"):
                    ui.label("Allowed").classes("text-[13px] text-black")
                    state.total_allowed = ui.label("₹0").classes(
                        "text-[15px] font-mono text-black w-28 text-right"
                    )
                ui.element("div").classes("w-20")
                with ui.row().classes("items-baseline gap-1"):
                    ui.label("Given").classes("text-[13px] text-black")
                    state.total_given = ui.label("₹0").classes(
                        "text-[15px] font-mono text-black w-28 text-right"
                    )
                ui.element("div").classes("w-26")

            # EXCESS DISCOUNT CALLOUT
            with ui.row().classes(
                "w-full items-center justify-between mt-2 px-4 py-2.5 "
                "rounded-lg bg-gray-50 border border-gray-200"
            ) as _excess_bar:
                with ui.column().classes("gap-0"):
                    ui.label("Excess discount").classes(
                        "text-[14px] font-bold uppercase tracking-wide text-gray-500"
                    )
                    ui.label("Discount given minus allowed limit").classes(
                        "text-[12px] text-gray-400"
                    )
                state.lbl_excess_discount = ui.label("₹0").classes(
                    "text-[20px] font-bold font-mono text-gray-400"
                )
                # lbl_excess is the compact version used in the live bar elsewhere
                state.lbl_excess_lv = state.lbl_excess_discount


def build_accessories_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        # Header
        _section_header(
            emoji="🔧",
            title="Accessories",
            subtitle="Record accessories details",
            icon_bg="bg-blue-50",
        )

        options = {
            acc_id: f"{data['name']} (₹{data['listed_price']})"
            for acc_id, data in state.accessory_map.items()
        }

        # Visual List Display

        def update_total(e):
            selected = e.value or []
            total = sum(
                state.accessory_map.get(int(i), {}).get("listed_price", 0)
                for i in selected
            )
            state.acc_total_label.set_text(f"Total: ₹{total:,}")

            # auto-fill charged if empty
            if not state.acc_charged.value:
                state.acc_charged.set_value(total)

        # Multi-select
        with ui.grid(columns=3).classes("w-full items-center gap-4"):
            state.acc_select = (
                ui.select(
                    options=options,
                    label="Select Accessories",
                    multiple=True,
                    with_input=True,  # search enabled
                )
                .classes("w-full h-10")
                .props("outlined dense use-input")
            )

            # Total Display
            state.acc_total_label = (
                ui.label("Total: ₹0")
                .classes(
                    "text-lg text-bold vertical-align-center horizotal-align-center"
                )
                .props("dense")
            )

            # Charged Input
            state.acc_charged = accounting_input(label_text="Actual Charged (₹)")


def build_delivery_checklist_section(state: FormState) -> None:

    with ui.card().classes(
        "shadow-sm rounded-2xl p-6 mb-6 border border-gray-100 bg-white"
    ):
        # Header
        _section_header(
            emoji="✅",
            title="Delivery Checklist",
            subtitle="Verify all delivery requirements before vehicle handover",
            icon_bg="bg-emerald-50",
        )

        # Checklist Container
        with ui.column().classes(
            "w-full bg-gray-50 border border-gray-100 rounded-xl p-5 gap-4"
        ):
            ui.label("Pre-Delivery Verification").classes(
                "text-[13px] font-semibold text-gray-700"
            )

            ui.label(
                "Ensure all mandatory documents, accessories, and delivery "
                "formalities are completed."
            ).classes("text-[12px] text-gray-500 leading-5")

            # Checklist Grid
            with ui.grid(columns=5).classes("w-full gap-x-6 gap-y-4 pt-2"):
                for key, label in DELIVERY_CHECK_KEYS:
                    with ui.row().classes(
                        "items-center gap-2 bg-white border border-gray-100 "
                        "rounded-lg px-3 py-2 shadow-sm"
                    ):
                        state.delivery_cbs[key] = ui.checkbox(value=False).props(
                            "dense size='sm'"
                        )

                        ui.label(label).classes("text-[13px] text-gray-700")


def build_audit_section(state: FormState) -> None:

    with ui.card().classes(
        "shadow-sm rounded-2xl p-6 mb-6 border border-gray-100 bg-white"
    ):
        # Header
        _section_header(
            emoji="📋",
            title="Audit & Compliance",
            subtitle="Track observations and corrective actions",
            icon_bg="bg-purple-50",
        )

        with ui.grid(columns=2).classes("w-full gap-5 items-start"):
            # Observation Section
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-5 gap-3"
            ):
                ui.label("Observations").classes(
                    "text-[13px] font-semibold text-gray-700"
                )

                ui.label("Record discrepancies, issues, or audit findings.").classes(
                    "text-[12px] text-gray-500 leading-5"
                )

                state.audit_obs = (
                    ui.textarea(
                        label="Observations",
                        placeholder=(
                            "Enter audit observations, missing documents, "
                            "policy deviations, or other remarks..."
                        ),
                    )
                    .classes("w-full")
                    .props("outlined dense rows=6")
                )

            # Action Section
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-5 gap-3"
            ):
                ui.label("Follow-up Action").classes(
                    "text-[13px] font-semibold text-gray-700"
                )

                ui.label("Document corrective actions or next steps.").classes(
                    "text-[12px] text-gray-500 leading-5"
                )

                state.audit_action = (
                    ui.textarea(
                        label="Follow-up Action",
                        placeholder=(
                            "Enter corrective actions, approvals needed, "
                            "responsible person, or closure notes..."
                        ),
                    )
                    .classes("w-full")
                    .props("outlined dense rows=6")
                )


def build_file_status_section(state: FormState) -> None:

    is_booking = state.stage == "booking"

    with ui.card().classes(
        "shadow-sm rounded-2xl p-6 mb-6 border border-gray-100 bg-white"
    ):
        # Header
        _section_header(
            emoji="⏳",
            title="File Status",
            subtitle="Track incomplete documentation status",
            icon_bg="bg-amber-50",
        )

        with ui.grid(columns=2).classes("w-full gap-5 items-start"):
            # Status Card
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-5 gap-4"
            ):
                ui.label("Document Verification").classes(
                    "text-[13px] font-semibold text-gray-700"
                )

                if is_booking:
                    state.booking_file_incomplete = (
                        ui.checkbox("Booking File Incomplete")
                        .classes("w-full")
                        .props("dense")
                    )
                else:
                    state.delivery_file_incomplete = (
                        ui.checkbox("Delivery File Incomplete")
                        .classes("w-full")
                        .props("dense")
                    )

                ui.label(
                    "Mark this if required documents or approvals are pending."
                ).classes("text-[12px] text-gray-500 leading-5")

            # Remarks Section
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-5 gap-3"
            ):
                ui.label("Remarks / Reason").classes(
                    "text-[13px] font-semibold text-gray-700"
                )

                if is_booking:
                    state.booking_file_incomplete_remarks = (
                        ui.textarea(
                            "Reason For Incomplete",
                            placeholder="Explain missing documents, approvals, or pending actions...",
                        )
                        .classes("w-full")
                        .props("outlined dense rows=5")
                    )
                else:
                    state.delivery_file_incomplete_remarks = (
                        ui.textarea(
                            "Reason For Incomplete",
                            placeholder="Explain missing documents, approvals, or pending actions...",
                        )
                        .classes("w-full")
                        .props("outlined dense rows=5")
                    )


def _section_header(
    emoji: str,
    title: str,
    subtitle: str,
    icon_bg: str = "bg-gray-100",
) -> None:
    with ui.row().classes(
        "w-full items-center justify-between mb-5 pb-3 border-b border-gray-100"
    ):
        with ui.row().classes("items-center gap-3"):
            with ui.element("div").classes(
                f"w-10 h-10 rounded-xl {icon_bg} flex items-center justify-center"
            ):
                ui.label(emoji).classes("text-[18px]")

            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-[16px] font-bold text-gray-900")
                ui.label(subtitle).classes("text-[12px] text-gray-500")


def build_invoice_section(state: FormState) -> None:

    with ui.card().classes(
        "shadow-sm rounded-2xl p-6 mb-6 border border-gray-100 bg-white"
    ):
        # Header
        _section_header(
            emoji="🧾",
            title="Invoice Details",
            subtitle="Manage invoice pricing and taxation",
            icon_bg="bg-orange-50",
        )

        # Form
        with ui.grid(columns=3).classes("w-full gap-4 items-start"):
            # Invoice Meta
            state.invoice_number = (
                ui.input(label="Invoice Number")
                .classes("uppercase")
                .props("outlined dense")
            )

            state.invoice_date = ui.input(
                label="Invoice Date",
                validation={
                    "Enter valid date (DD-MM-YYYY)": (
                        lambda v: bool(v) and is_valid_date(v)
                    )
                },
            ).props('outlined dense type="date"')

            state.invoice_ex_showroom = accounting_input(label_text="Ex-Showroom Price")
            state.invoice_ex_showroom.props("readonly")

            # Pricing
            state.invoice_discount = accounting_input(
                label_text="Discount",
                placeholder="Enter discount or concession",
            )

            state.invoice_taxable_value = accounting_input(
                label_text="Taxable Value",
                placeholder="Enter taxable amount",
            )

            state.invoice_total = accounting_input(label_text="Total Invoice Value")

            # Tax Section
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-4 gap-3"
            ):
                ui.label("GST Components").classes(
                    "text-[13px] font-semibold text-gray-700"
                )

                state.invoice_cgst = accounting_input(label_text="CGST")
                state.invoice_sgst = accounting_input(label_text="SGST")

            # IGST Section
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-4 gap-3"
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("IGST").classes("text-[13px] font-semibold text-gray-700")
                    state.igst_toggle = ui.switch().props("dense")

                state.invoice_igst = accounting_input(label_text="IGST")

            # CESS Section
            with ui.column().classes(
                "w-full bg-gray-50 border border-gray-100 rounded-xl p-4 gap-3"
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("CESS").classes("text-[13px] font-semibold text-gray-700")
                    state.cess_toggle = ui.switch().props("dense")

                state.invoice_cess = accounting_input(label_text="CESS")


def _ledger_value(text: str, value: str = "₹ 0") -> ui.column:
    with (
        ui.column()
        .classes(
            "bg-gray-100 rounded-lg px-4 py-3 border border-gray-100 min-w-[180px]"
        )
        .props("elevated") as col
    ):
        ui.label(text).classes("text-[14px] font-bold  tracking-wide text-black-500")
        value_label = ui.label(value).classes("text-[20px] font-bold text-gray-900")

    col.value_label = value_label
    return col


def build_payment_section(state: FormState) -> None:
    with ui.card().classes(
        "shadow-sm rounded-2xl p-6 mb-6 border border-gray-100 bg-white"
    ):
        # Header
        with ui.row().classes(
            "w-full items-center justify-between mb-5 pb-3 border-b border-gray-100"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center"
                ):
                    ui.label("💳").classes("text-[18px]")

                with ui.column().classes("gap-0"):
                    ui.label("Payment Received").classes(
                        "text-[16px] font-bold text-gray-900"
                    )
                    ui.label("Capture all payment sources").classes(
                        "text-[12px] text-gray-500"
                    )

        # Inputs
        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-4"):
            state.payment_cash = accounting_input("Cash Payment")
            state.payment_bank = accounting_input("Bank Payment")
            state.payment_finance = accounting_input("Finance")
            state.payment_exchange = accounting_input("Exchange")


def build_ledger_section(state: FormState) -> None:

    with ui.card().classes(
        "shadow-sm rounded-2xl p-6 mb-6 border border-gray-100 bg-white"
    ):
        # Header
        _section_header(
            emoji="📒",
            title="Ledger Summary",
            subtitle="Real-time payment overview",
            icon_bg="bg-blue-50",
        )

        # Summary Cards
        with ui.grid(columns=3).classes("w-full gap-4 mb-5"):
            total_receivable_card = _ledger_value("Total Receivable")
            total_received_card = _ledger_value("Total Received")
            balance_card = _ledger_value("Balance Amount")

            state.total_receivable = total_receivable_card.value_label
            state.total_received = total_received_card.value_label
            state.balance_amount = balance_card.value_label

        # Adjustment Section
        with ui.column().classes(
            "w-full bg-gray-50 border border-gray-100 rounded-xl p-5 gap-4"
        ):
            with ui.row().classes("items-center justify-between w-full"):
                with ui.column().classes("gap-0"):
                    ui.label("Ledger Adjustment").classes(
                        "text-[13px] font-semibold text-gray-700"
                    )

                    ui.label("Apply manual debit or credit adjustments").classes(
                        "text-[12px] text-gray-500"
                    )

            with ui.grid(columns=3).classes("w-full gap-4 items-start"):
                # Positive / Negative
                with ui.column().classes("gap-1"):
                    ui.label("Adjustment Type").classes(
                        "text-[12px] font-semibold text-gray-700 ml-1"
                    )

                    state.adjustment_type = (
                        ui.select(
                            {
                                "positive": "➕ Positive",
                                "negative": "➖ Negative",
                            },
                            value="negative",
                        )
                        .props("outlined")
                        .classes("w-full")
                    )

                # Amount
                with ui.column().classes("gap-1"):
                    ui.label("Adjustment Amount").classes(
                        "text-[12px] font-semibold text-gray-700 ml-1"
                    )
                    state.ledger_adjustment = accounting_input(
                        "Adjustment Amount",
                        placeholder="Enter adjustment amount",
                        container_classes="w-full",
                    )
                    state.ledger_adjustment.props("style='min-height:46px'")

                # Remarks
                with ui.column().classes("gap-1 w-full"):
                    ui.label("Remarks / Reason").classes(
                        "text-[12px] font-semibold text-gray-700 ml-1"
                    )

                    state.ledger_adjustment_remarks = (
                        ui.textarea(placeholder=("Explain reason for adjustment..."))
                        .classes("w-full")
                        .props("outlined rows=2")
                    )


# Internal CSS helpers
_HDR = "text-[12px] font-semibold tracking-[0.9px] uppercase text-black-400 text-center"
_LABEL = "text-[13px] text-black-700 truncate"
_MONO = "text-[13px] font-mono text-black-500 text-center"
_MONO_SM = "text-[11px] font-mono text-center"

# Discount names that are always visible regardless of conditions
_DEFAULT_DISC = {
    "Cash Discount All Customers",
    "Additional Discount From Dealer",
    "Maximum benefit due to price increase",
}
_DEFAULT_PRICE = {"Ex Showroom Price", "TCS", "Registration", "Insurance"}

# Condition key → discount component name substring mapping
# Add more mappings as your domain grows
_CONDITION_DISC_MAP: dict[str, list[str]] = {
    "exchange": ["Exchange Bonus", "Exchange", "Green Bonus"],
    "corporate": ["Corporate"],
    "scrap": ["Scrappage", "Scrap"],
    "upgrade": ["Loyalty", "Upgrade"],
    "govt_employee": ["Govt", "Government"],
    "tr_case": ["TR Case", "TR"],
}


def _condition_badge(name: str, conditions: dict) -> str | None:
    """Return the condition key that controls this discount row, or None."""
    for cond_key, substrings in _CONDITION_DISC_MAP.items():
        if any(s.lower() in name.lower() for s in substrings):
            return cond_key
    return None


# populate_price_and_discount  — auto-fill from API data
def _build_component_map(booking_data: dict) -> dict:
    """
    Flatten booking_data into a name → value dict that tolerates:
    • raw component names           {"Ex Showroom Price": 629990}
    • _actual suffix keys           {"Ex Showroom Price_actual": 629990}
    • normalized (lowercase, no punctuation) fallback keys
    """
    component_map: dict = {}
    for raw_key, val in booking_data.items():
        clean_key = raw_key.replace("_actual", "").strip()
        component_map[clean_key] = val
        # Also store a normalized version for fuzzy matching
        norm_key = re.sub(r"[^a-z0-9]", "", clean_key.lower())
        component_map[norm_key] = val
    return component_map


# update_discount_visibility  — called when sale conditions change
def update_discount_visibility(state, conditions: dict) -> None:
    """
    Show or hide conditional discount rows based on active sale conditions.
    Call this whenever a condition checkbox changes.

    Also refreshes per-row Given/Diff labels so newly-visible rows show correct
    values immediately.

    Args:
        state:      FormState with discount_rows populated.
        conditions: dict of {condition_key: bool}, e.g. {"exchange": True}
    """
    for name, row in state.discount_rows.items():
        if name in _DEFAULT_DISC:
            row.set_visibility(True)
            continue
        cond_key = _condition_badge(name, conditions)
        if cond_key is not None:
            row.set_visibility(bool(conditions.get(cond_key, False)))


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
            state.lbl_allowed_lv = ui.label("₹0").classes(
                "text-[16px] font-bold text-white mono"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Discount Given:").classes("text-[11px] text-white/50")
            state.lbl_discount_lv = ui.label("₹0").classes(
                "text-[16px] font-bold text-white mono"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Excess Discount:").classes("text-[11px] text-white/50")
            state.lbl_excess_lv = ui.label("—").classes(
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
        ui.button(
            "← Back to MIS",
            on_click=lambda: ui.navigate.to(f"/{state.stage}-mis"),
        ).classes("text-gray-500 text-[13px] hover:text-gray-800").props("flat no-caps")

        submit_text = "Save Booking"

        if state.edit_mode:
            if state.form_mode == "booking_edit":
                submit_text = "Update Booking"

            elif state.form_mode == "delivery_from_booking":
                submit_text = "Convert to Delivery"

            elif state.form_mode == "delivery_edit":
                submit_text = "Update Delivery"

        elif state.stage == "delivery":
            submit_text = "Create Delivery"

        state.submit_btn = (
            ui.button(
                submit_text,
                on_click=lambda: _fs_handle_submit(state),
            )
            .classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            )
            .props("no-caps unelevated")
        )


# FORM EVENT HANDLERS
def handle_price_toggle(
    state: FormState,
    name: str,
):

    toggle = state.price_match_toggles.get(name)

    inp = state.price_inputs.get(name)

    if not toggle or not inp:
        return

    if toggle.value:
        src_val = state.listed_prices.get(
            name,
            0,
        )

        inp.set_value(format_num_inr(src_val))

        inp.set_enabled(False)

    else:
        inp.set_enabled(True)
        inp.set_value(None)

    _fs_update_live(state)


def handle_discount_toggle(
    state: FormState,
    name: str,
):

    toggle = state.discount_match_toggles.get(name)

    inp = state.discount_inputs.get(name)

    if not toggle or not inp:
        return

    if toggle.value:
        src_val = state.listed_prices.get(
            name,
            0,
        )

        inp.set_value(format_num_inr(src_val))

        inp.set_enabled(False)

    else:
        inp.set_enabled(True)
        inp.set_value(None)

    _fs_update_live(state)


def attach_form_handlers(state: FormState):

    if getattr(state, "handlers_attached", False):
        return

    state.handlers_attached = True

    # HELPERS
    def live_update(*_):

        if state.is_hydrating:
            return

        _fs_update_live(state)

    def revalidate(*_):

        if state.is_hydrating:
            return

        _fs_revalidate(state)

    # CUSTOMER
    if getattr(state, "cust_pan", None):

        def on_pan_change(e):

            if state.is_hydrating:
                return

            if isinstance(e.args, str):
                upper_val = e.args.upper()

                if upper_val != state.cust_pan.value:
                    state.cust_pan.set_value(upper_val)

            revalidate(state)

        state.cust_pan.on(
            "update:model-value",
            on_pan_change,
        )

    if getattr(state, "cust_mobile", None):
        state.cust_mobile.on_value_change(revalidate)

    if getattr(state, "cust_email", None):
        state.cust_email.on_value_change(revalidate)

    # CAR
    if getattr(state, "car_select", None):

        async def handle_car_change(e):

            if state.is_hydrating:
                return

            car_id = state.car_select.value

            await _fs_on_car_change(
                car_id,
                state,
                preserve_variant=False,
            )

        state.car_select.on(
            "update:model-value",
            lambda e: asyncio.create_task(handle_car_change(e)),
        )

    # VARIANT
    if getattr(state, "variant_select", None):

        async def handle_variant_change(e):

            if state.is_hydrating:
                return

            variant_id = state.variant_select.value
            await _fs_on_variant_change(
                variant_id,
                state,
            )

        state.variant_select.on(
            "update:model-value",
            lambda e: asyncio.create_task(handle_variant_change(e)),
        )

    # CONDITIONS
    for cb in getattr(state, "condition_cbs", {}).values():
        cb.on(
            "update:model-value",
            lambda e: (
                refresh_visibility(state),
                _fs_update_live(state),
                _fs_revalidate(state),
            ),
        )

    # CHECKLISTS
    for cb in getattr(state, "booking_cbs", {}).values():
        cb.on_value_change(revalidate)

    for cb in getattr(state, "delivery_cbs", {}).values():
        cb.on_value_change(revalidate)

    # PRICE INPUTS
    for inp in getattr(state, "price_inputs", {}).values():
        inp.on_value_change(live_update)

    # DISCOUNT INPUTS
    for inp in getattr(state, "discount_inputs", {}).values():
        inp.on_value_change(live_update)

    # ACCESSORIES
    if getattr(state, "acc_charged", None):
        state.acc_charged.on_value_change(live_update)

    # OTHER DISCOUNT
    if getattr(state, "total_discount_booking", None):
        state.total_discount_booking.on_value_change(live_update)

    if getattr(state, "other_discount_delivery", None):
        state.other_discount_delivery.on_value_change(live_update)

    if getattr(state, "adjustment_input", None):
        state.adjustment_input.on_value_change(live_update)

    # PRICE TOGGLES
    for name, toggle in getattr(
        state,
        "price_match_toggles",
        {},
    ).items():
        toggle.on(
            "update:model-value",
            lambda e, n=name: handle_price_toggle(
                state,
                n,
            ),
        )

    # DISCOUNT TOGGLES
    for name, toggle in getattr(
        state,
        "discount_match_toggles",
        {},
    ).items():
        toggle.on(
            "update:model-value",
            lambda e, n=name: handle_discount_toggle(
                state,
                n,
            ),
        )
    attach_invoice_handlers(state)

    # Payment Section
    if getattr(state, "payment_cash", None):
        state.payment_cash.on_value_change(live_update)
    if getattr(state, "payment_bank", None):
        state.payment_bank.on_value_change(live_update)
    if getattr(state, "payment_finance", None):
        state.payment_finance.on_value_change(live_update)
    if getattr(state, "payment_exchange", None):
        state.payment_exchange.on_value_change(live_update)
    if getattr(state, "adjustment_type", None):
        state.adjustment_type.on_value_change(live_update)
    if getattr(state, "ledger_adjustment", None):
        state.ledger_adjustment.on_value_change(live_update)


def attach_invoice_handlers(
    state: FormState,
):
    # taxable = getattr(state, "invoice_taxable_value", None)
    invoice_igst = getattr(state, "invoice_igst", None)
    invoice_cess = getattr(state, "invoice_cess", None)
    igst_toggle = getattr(state, "igst_toggle", None)
    cess_toggle = getattr(state, "cess_toggle", None)
    # Not Live calculating taxes, might do in future
    # if taxable:
    #     taxable.on_value_change(lambda e: calculate_invoice_taxes(state))

    if invoice_igst:
        invoice_igst.on_value_change(lambda e: calculate_invoice_total(state))

    if invoice_cess:
        invoice_cess.on_value_change(lambda e: calculate_invoice_total(state))

    if igst_toggle:
        igst_toggle.on(
            "update:model-value",
            lambda e: (
                update_invoice_tax_visibility(state),
                calculate_invoice_total(state),
            ),
        )

    if cess_toggle:
        cess_toggle.on(
            "update:model-value",
            lambda e: (
                update_invoice_tax_visibility(state),
                calculate_invoice_total(state),
            ),
        )


async def _fs_on_car_change(car_id, state, *, preserve_variant=False):
    state.car_id = car_id

    if state.variant_select is None:
        return

    # ONLY CLEAR DURING USER ACTIONS
    if not preserve_variant:
        state.variant_id = None
        state.variant_select.set_value(None)

    state.variant_select.options = {}
    state.variant_select.update()

    _fs_clear_prices(state)

    if not car_id:
        return

    try:
        variants = await api_get(f"/cars/{car_id}/variants")

        options = {
            v["id"]: v["full_variant_name"]
            for v in sorted(
                variants,
                key=lambda x: (x.get("full_variant_name") or "").lower(),
            )
        }

        state.variant_select.options = options
        state.variant_select.update()

    except UnauthorizedError:
        await logout_user()
        ui.notify("Session expired. Please Login again.", type="warning")
        ui.navigate.to("/login")
    except ConnectionFailedError:
        ui.notify("Unable to connect to the server. Please Try Again.", type="negative")
    except APIError:
        ui.notify("AN ERROR OCCURED", type="negative")
    except Exception as ex:
        _fs_show_error(state, f"Failed to load variants: {ex}")


async def _fs_on_variant_change(variant_id, state: FormState) -> None:
    state.variant_id = variant_id

    if variant_id:
        await _fs_try_price_preload(state)

    if getattr(state, "form_ready", False) and not getattr(
        state, "is_hydrating", False
    ):
        _fs_update_live(state)

        _fs_revalidate(state)


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
        #  Store listed prices (source of truth)
        state.listed_prices = preview or {}
        filled = 0

        for name, value in state.listed_prices.items():
            if value is None:
                continue

            formatted = f"₹{int(value):,}"

            #  Update Listed Price Labels
            if name in state.price_listed_labels:
                state.price_listed_labels[name].set_text(formatted)

            if name in state.discount_listed_labels:
                state.discount_listed_labels[name].set_text(formatted)

            #  Auto-fill ONLY if toggle is ON
            if name in state.price_match_toggles:
                toggle = state.price_match_toggles[name]
                inp = state.price_inputs.get(name)

                if toggle.value and inp and parsed_val(inp) in [None, "", 0]:
                    inp.set_value(int(value))
                    inp.props("readonly")
                    filled += 1

            if name in state.discount_match_toggles:
                toggle = state.discount_match_toggles[name]
                inp = state.discount_inputs.get(name)

                if toggle.value and inp and parsed_val(inp) in [None, "", 0]:
                    inp.set_value(int(value))
                    inp.props("readonly")
                    filled += 1

        if state.invoice_ex_showroom:
            # Match main.py line 1516
            val = state.listed_prices.get("Ex Showroom Price", 0)
            state.invoice_ex_showroom.set_value(val)

        if filled:
            ui.notify(
                f"✓ {filled} field{'s' if filled > 1 else ''} synced with listed price.",
                type="info",
                position="top-right",
                timeout=2500,
            )
    except Exception as e:
        print("ERROR: in preloading the price list: ", e)
        ui.notify("Price List not fetched", type="negative")
        pass  # best-effort; silently skip if endpoint missing


## Invoice calculation helpers
def update_invoice_tax_visibility(
    state: FormState,
):

    if state.invoice_igst:
        state.invoice_igst.set_enabled(
            bool(state.igst_toggle and state.igst_toggle.value)
        )

    if state.invoice_cess:
        state.invoice_cess.set_enabled(
            bool(state.cess_toggle and state.cess_toggle.value)
        )


def calculate_invoice_total(
    state: FormState,
):

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
    if state.invoice_total:
        state.invoice_total.set_value(format_num_inr(total))


def calculate_invoice_taxes(
    state: FormState,
):
    # Currently, this method is not used, DO NOT DELETE IT, we might need it in future
    taxable = parsed_val(state.invoice_taxable_value)

    cgst = taxable * 0.09
    sgst = taxable * 0.09

    if state.invoice_cgst:
        state.invoice_cgst.set_value(format_num_inr(cgst))

    if state.invoice_sgst:
        state.invoice_sgst.set_value(format_num_inr(sgst))

    calculate_invoice_total(state)


def _fs_update_live(state) -> None:
    # 1. PRICE TOTALS
    total_listed = 0
    total_charged = 0
    total_diff = 0

    for name, inp in state.price_inputs.items():
        is_visible = state.visible_price_rows.get(
            name,
            True,
        )

        listed_val = int(state.listed_prices.get(name) or 0)
        charged_val = int(parsed_val(inp))

        # visible rows participate in totals
        if is_visible:
            total_listed += listed_val
            total_charged += charged_val

        # UX interaction state
        toggle = state.price_match_toggles.get(name)

        is_active = (toggle.value if toggle else False) or str(
            inp.value
        ).strip() not in ["", "None"]

        dl = state.price_diff_labels.get(name)

        if not dl:
            continue

        # hidden row
        if not is_visible:
            dl.set_text("—")
            dl.style("color:#9CA3AF")
            continue

        # untouched row
        if not is_active:
            dl.set_text("—")
            dl.style("color:#9CA3AF")
            continue

        # active visible row
        diff = listed_val - charged_val
        if is_visible and is_active:
            total_diff += diff

        if diff > 0:
            dl.set_text(f"₹{diff:,}")
            dl.style("color:#DC2626; font-weight:600")
        else:
            dl.set_text("₹0")
            dl.style("color:#9CA3AF")
    # PRICE LABELS
    if getattr(state, "lbl_total_listed_price", None):
        state.lbl_total_listed_price.set_text(f"₹{total_listed:,}")

    if getattr(state, "lbl_total_charged_price", None):
        state.lbl_total_charged_price.set_text(f"₹{total_charged:,}")

    if getattr(state, "lbl_total_diff_price", None):
        if total_diff > 0:
            state.lbl_total_diff_price.set_text(f"₹{total_diff:,}")
            state.lbl_total_diff_price.style("color:#DC2626; font-weight:600")

        else:
            state.lbl_total_diff_price.set_text("₹0")
            state.lbl_total_diff_price.style("color:#9CA3AF")

    # 2. ACCESSORIES
    acc_listed = 0
    acc_charged = 0

    if getattr(state, "acc_total_label", None):
        try:
            raw = state.acc_total_label.text

            acc_listed = int(float(raw.split("₹")[-1].replace(",", "")))

        except Exception:
            acc_listed = 0

    if getattr(state, "acc_charged", None):
        acc_charged = int(parsed_val(state.acc_charged))

    acc_diff = acc_listed - acc_charged

    # 3. DISCOUNT TOTALS

    total_allowed_discount = 0
    total_given_discount = 0

    for name, inp in state.discount_inputs.items():
        is_visible = state.visible_discount_rows.get(
            name,
            True,
        )

        allowed_val = int(state.listed_prices.get(name) or 0)

        given_val = int(parsed_val(inp))

        # visible rows participate in totals
        if is_visible:
            total_allowed_discount += allowed_val
            total_given_discount += given_val

        # UX interaction state
        toggle = state.discount_match_toggles.get(name)

        is_active = (toggle.value if toggle else False) or str(
            inp.value
        ).strip() not in ["", "None"]

        dl = state.discount_diff_labels.get(name)

        if not dl:
            continue

        # hidden row
        if not is_visible:
            dl.set_text("—")
            dl.style("color:#9CA3AF")
            continue

        # untouched row
        if not is_active:
            dl.set_text("—")
            dl.style("color:#9CA3AF")
            continue

        # active visible row
        diff = given_val - allowed_val

        if diff > 0:
            dl.set_text(f"₹{diff:,}")
            dl.style("color:#DC2626; font-weight:600")
        else:
            dl.set_text("₹0")
            dl.style("color:#9CA3AF")

    # 4. EXCESS CALCULATION
    adjustment = int(float(parsed_val(getattr(state, "adjustment_input", None))))
    total_discount_given = int(
        total_diff
        + acc_diff
        + int(parsed_val(getattr(state, "total_discount_booking", None)))
        + int(parsed_val(getattr(state, "other_discount_delivery", None)))
        + total_given_discount
        - adjustment
    )

    excess = int(max(0, total_discount_given - total_allowed_discount))

    # CUSTOMER LEDGER CALC
    total_receivable = total_charged - total_discount_given
    total_received = (
        int(parsed_val(getattr(state, "payment_cash", None)))
        + int(parsed_val(getattr(state, "payment_bank", None)))
        + int(parsed_val(getattr(state, "payment_exchange", None)))
        + int(parsed_val(getattr(state, "payment_finance", None)))
    )

    balance_amount = total_receivable - total_received

    if state.adjustment_type:
        if state.adjustment_type.value == "positive" and state.ledger_adjustment:
            balance_amount += int(parsed_val(getattr(state, "ledger_adjustment", None)))

        elif state.adjustment_type.value == "negative" and state.ledger_adjustment:
            balance_amount -= int(parsed_val(getattr(state, "ledger_adjustment", None)))

    # 5. UPDATE LABELS
    if getattr(state, "total_receivable", None):
        state.total_receivable.set_text(f"₹{total_receivable:,}")

    if getattr(state, "total_received", None):
        state.total_received.set_text(f"₹{total_received:,}")

    if getattr(state, "balance_amount", None):
        state.balance_amount.set_text(f"₹{balance_amount:,}")

    if getattr(state, "total_allowed", None):
        state.total_allowed.set_text(f"₹{total_allowed_discount:,}")

    if getattr(state, "total_given", None):
        state.total_given.set_text(f"₹{total_discount_given:,}")

    if getattr(state, "lbl_allowed_lv", None):
        state.lbl_allowed_lv.set_text(f"₹{total_allowed_discount:,}")

    if getattr(state, "lbl_discount_lv", None):
        state.lbl_discount_lv.set_text(f"₹{total_discount_given:,}")

    if getattr(state, "lbl_excess_discount", None):
        state.lbl_excess_discount.set_text(f"₹{excess:,}")
        state.lbl_excess_discount.style(
            "color:#DC2626; font-weight:700" if excess > 0 else "color:#9CA3AF"
        )

    if getattr(state, "lbl_excess_lv", None):
        state.lbl_excess_lv.set_text(f"₹{excess:,}")
        state.lbl_excess_lv.style("color:#F87171" if excess > 0 else "color:#6EE7B7")


def get_conditions(state) -> dict:
    return {
        key: bool(cb.value) for key, cb in getattr(state, "condition_cbs", {}).items()
    }


def _fs_revalidate(state: FormState) -> None:
    if state.is_hydrating:
        return

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


async def _fs_handle_submit(
    state: FormState,
) -> None:

    if not state.error_banner or not state.error_msg_label:
        return

    # =====================================================
    # VALIDATION
    # =====================================================

    valid, msg = state.is_valid()

    if not valid:
        state.error_msg_label.set_text(msg)

        state.error_banner.set_visibility(True)

        return

    payload = build_payload(state)

    try:
        # HIDE OLD ERROR
        state.error_banner.set_visibility(False)

        # UPDATE FLOW
        if state.edit_mode and state.txn_id:
            await api_put(f"/transactions/{state.txn_id}", payload)

            if state.stage == "delivery":
                if state.form_mode == "delivery_from_booking":
                    ui.notify(
                        "Booking converted to Delivery successfully",
                        color="green",
                        type="positive",
                    )

                else:
                    ui.notify(
                        "Delivery updated successfully", color="green", type="positive"
                    )

            else:
                ui.notify(
                    "Booking updated successfully", color="green", type="positive"
                )

        # CREATE FLOW
        else:
            await api_post("/transactions", payload)

            if state.stage == "delivery":
                ui.notify(
                    "Delivery created successfully", color="green", type="positive"
                )

            else:
                ui.notify(
                    "Booking created successfully", color="green", type="positive"
                )

        # SUCCESS NAVIGATION
        ui.navigate.reload()

    except UnauthorizedError:
        await logout_user()
        ui.notify("Session expired. Please login again.", type="warning")
        ui.navigate.to("/login")

    except ConnectionFailedError as e:
        state.error_msg_label.set_text(str(e))
        state.error_banner.set_visibility(True)

    except APIError as e:
        print("FORM SUBMIT API ERROR:", e)
        state.error_msg_label.set_text(str(e))
        state.error_banner.set_visibility(True)

    except Exception as e:
        print("FORM SUBMIT ERROR:", e)
        state.error_msg_label.set_text(str(e))
        state.error_banner.set_visibility(True)


def build_payload(state: FormState) -> dict:

    def val(x):
        return x.value if x else None

    def lbl_val(x, chr_slice=1):
        val = x.text[chr_slice:].strip().replace(",", "").replace(".", "")
        return int(val) if val else None

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
                return int(eval(v_str))
            return int(v_str)
        except Exception:
            return 0

    # COMPONENTS (CRITICAL)
    actual_amounts = {}
    allowed_amounts = {}

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
            inp = state.discount_inputs.get(name)
            actual_amounts[name] = intval(inp) if inp else 0
        else:
            actual_amounts[name] = 0

    for name, value in state.listed_prices.items():
        price_row = state.price_rows.get(name)
        discount_row = state.discount_rows.get(name)

        # PRICE COMPONENT
        if price_row:
            if price_row.visible:
                allowed_amounts[name] = value  # ALWAYS include
            else:
                allowed_amounts[name] = 0

        # DISCOUNT COMPONENT
        elif discount_row:
            if discount_row.visible:
                allowed_amounts[name] = value
            else:
                allowed_amounts[name] = 0

        # SAFETY (unknown component)
        else:
            allowed_amounts[name] = value

    # CONDITIONS
    conditions = {key: (cb.value or False) for key, cb in state.condition_cbs.items()}
    user = get_user()
    # DELIVERY CHECKS
    delivery_checks = {
        key: (cb.value or False) for key, cb in state.delivery_cbs.items()
    }

    booking_checks = {key: (cb.value or False) for key, cb in state.booking_cbs.items()}

    # ACCESSORIES
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

    # INVOICE
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

    # PAYMENT
    payment_details = {
        "cash": intval(state.payment_cash),
        "bank": intval(state.payment_bank),
        "finance": intval(state.payment_finance),
        "exchange": intval(state.payment_exchange),
    }

    # MAIN PAYLOAD
    payload = {
        #  REQUIRED
        "variant_id": (state.variant_select.value if state.variant_select else None),
        "booking_date": val(state.booking_date),
        "booking_amt": intval(state.booking_amt),
        "booking_receipt_num": val(state.booking_receipt_num),
        "outlet_id": (state.outlet_select.value if state.outlet_select else None),
        "sales_executive_id": (state.exec_select.value if state.exec_select else None),
        "user_id": user.get("id"),
        #  CUSTOMER
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
        #  VEHICLE
        "customer_file_number": val(state.cust_file_no),
        "vin_number": val(state.vin_no),
        "color": val(state.car_color),
        "engine_number": val(state.engine_no),
        "model_year": val(state.model_year),
        "registration_number": val(state.vehicle_regn_no),
        "registration_date": val(state.regn_date),
        "price_adjustment": val(state.adjustment_input),
        #  CORE LOGIC
        "actual_amounts": actual_amounts,
        "allowed_amounts": allowed_amounts,
        "conditions": conditions,
        "delivery_checklist": delivery_checks,
        #  JSON SECTIONS
        "accessories_details": accessories_details,
        "accessory_ids": selected_acc_ids,  # Explicitly for TransactionService
        "invoice_details": invoice_details,
        "payment_details": payment_details,
        #  OPTIONAL FUTURE SAFE
        "finance_details": {},
        "exchange_details": {},
        #  AUDIT INFO
        "audit_info": {
            "observations": val(state.audit_obs),
            "actions": val(state.audit_action),
        },
    }

    if state.stage == "booking":
        payload["stage"] = "booking"
        payload["booking_checklist"] = booking_checks
        payload["booking_file_incomplete"] = val(state.booking_file_incomplete)
        payload["booking_file_incomplete_remarks"] = val(
            state.booking_file_incomplete_remarks
        )
        payload["discount_booking"] = intval(
            state.total_discount_booking
        )  # this is the discount given that doesn't fall under any head OTHER DISCOUNT

        payload["total_discount_booking"] = lbl_val(
            state.lbl_discount_lv
        )  # after adding differences and subtracting price adjustment
        payload["price_offered_booking"] = lbl_val(state.lbl_total_offered_price)
        payload["adjustment_booking"] = intval(state.adjustment_input)
        payload["excess_booking"] = lbl_val(state.lbl_excess_discount)

    elif state.stage == "delivery":
        payload["stage"] = "delivery"
        payload["booking_id"] = state.booking_id
        payload["delivery_date"] = val(state.delivery_date)
        payload["is_direct_delivery"] = state.is_direct_delivery
        payload["overrides"] = state.overrides
        payload["delivery_file_incomplete"] = val(state.delivery_file_incomplete)
        payload["delivery_file_incomplete_remarks"] = val(
            state.delivery_file_incomplete_remarks
        )
        payload["adjustment_delivery"] = intval(state.adjustment_input)
        payload["other_discount_delivery"] = intval(state.other_discount_delivery)
        payload["total_receivable"] = lbl_val(state.total_receivable)
        payload["total_received"] = lbl_val(state.total_received)
        payload["balance_amount"] = lbl_val(state.balance_amount)
        payload["ledger_adjustment"] = intval(state.ledger_adjustment)
        payload["ledger_adjustment_remarks"] = val(state.ledger_adjustment_remarks)
        payload["total_actual_discount"] = lbl_val(state.total_given)
        payload["total_allowed_discount"] = lbl_val(state.total_allowed)
        payload["total_excess_discount"] = lbl_val(state.lbl_excess_discount)

    return payload


def refresh_visibility(state: FormState) -> None:

    def is_checked(key: str) -> bool:
        cb = state.condition_cbs.get(key)
        return bool(cb and cb.value)

    def norm(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

    discount_visibility_rules = {
        norm("Additional For POI /Corporate Customers"): is_checked("corporate")
        or is_checked("govt_employee"),
        norm("Micro Segment (Solar Roof Top)"): is_checked("micro_segment"),
        norm("SBI Yono"): is_checked("sbi_yono"),
        norm("Power of 12"): is_checked("power_of_twelve"),
        norm("Shop Share Smile (SSS)"): is_checked("sss"),
        norm("Alliance Offer"): is_checked("alliance_offer"),
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
        norm("Insurance (With Depreciation Cover)"): not is_checked("self_insurance"),
        norm("Insurance"): not is_checked("self_insurance"),
    }

    # 2. Set row visibility and update rows/labels
    for name, row in state.discount_rows.items():
        n_name = norm(name)
        is_default = name in _DEFAULT_DISC
        visible = is_default or discount_visibility_rules.get(n_name, False)
        row.set_visibility(visible)
        state.visible_discount_rows[name] = visible
        row.update()
        # Also update child labels if present
        if (
            hasattr(state, "discount_diff_labels")
            and name in state.discount_diff_labels
        ):
            state.discount_diff_labels[name].update()
        if (
            hasattr(state, "discount_given_labels")
            and name in state.discount_given_labels
        ):
            state.discount_given_labels[name].update()
        if (
            hasattr(state, "discount_listed_labels")
            and name in state.discount_listed_labels
        ):
            state.discount_listed_labels[name].update()

    for name, row in state.price_rows.items():
        n_name = norm(name)
        visible = price_visibility_rules.get(
            n_name,
            True,
        )
        row.set_visibility(visible)
        state.visible_price_rows[name] = visible
        row.update()
        if hasattr(state, "price_diff_labels") and name in state.price_diff_labels:
            state.price_diff_labels[name].update()
        if hasattr(state, "price_listed_labels") and name in state.price_listed_labels:
            state.price_listed_labels[name].update()

    # 3. Revalidate if needed
    if getattr(state, "form_ready", False) and not getattr(
        state, "is_hydrating", False
    ):
        _fs_revalidate(state)
        _fs_update_live(state)


async def load_reference_data(state: FormState):

    ref = await fetch_reference_data()
    if not isinstance(ref, dict):
        ui.notify("Failed to fetch reference data from backend", type="negative")
        return
    state.cars = ref["cars"]
    state.variants = ref["variants"]
    state.components = ref["components"]
    state.outlets = ref["outlets"]
    state.executives = ref["executives"]

    state.accessory_map = {acc["id"]: acc for acc in ref["accessories"]}


async def load_transaction(state: FormState):

    if not state.transaction_id:
        return

    try:
        txn = await api_get(f"/transactions/{state.transaction_id}")

        state.transaction_data = txn
        state.booking_data = txn

    except UnauthorizedError:
        await logout_user()
        ui.notify("Session expired. Please Login again.")
        ui.navigate.to("/login")
    except ConnectionFailedError:
        ui.notify("Unable to connect to the server. Please Try again.")
    except Exception as e:
        print("ERROR: in loading the transaction: ", str(e))
        ui.notify("Failed to load entry", type="negative")


def build_form(state: FormState):

    if state.form_mode in [
        "booking_create",
        "booking_edit",
    ]:
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("Booking MIS Form").classes("text-2xl text-bold mb-5")

        build_vehicle_section(state)
        build_booking_section(state)
        build_customer_section(state)
        build_conditions_section(state)
        build_accessories_section(state)
        build_prices_section(state)
        build_booking_checklist_section(state)
        build_file_status_section(state)
        build_audit_section(state)

    elif state.form_mode == "delivery_direct_create":
        ui.label("Direct Delivery MIS Form").classes("text-2xl text-bold mb-5")

        build_vehicle_section(state)
        build_booking_section(state)
        build_customer_section(state)
        build_conditions_section(state)
        build_accessories_section(state)
        build_prices_section(state)
        build_delivery_checklist_section(state)
        build_file_status_section(state)
        build_invoice_section(state)
        build_payment_section(state)
        build_ledger_section(state)
        build_audit_section(state)

    elif state.form_mode in [
        "delivery_from_booking",
        "delivery_edit",
    ]:
        title = (
            "Delivery (From Booking)"
            if state.form_mode == "delivery_from_booking"
            else "Edit Delivery Entry"
        )

        ui.label(title).classes("text-2xl text-bold mb-5")

        build_vehicle_section(state)
        build_booking_section(state)
        build_customer_section(state)
        build_conditions_section(state)
        build_accessories_section(state)
        build_prices_section(state)
        build_delivery_checklist_section(state)
        build_file_status_section(state)
        build_invoice_section(state)
        build_payment_section(state)
        build_ledger_section(state)
        build_audit_section(state)

    build_live_bar(state)
    build_action_bar(state)


async def hydrate_form(state: FormState, txn: dict):
    if not txn:
        return

    state.is_hydrating = True

    try:
        # VEHICLE / CORE SELECTS
        outlet_id = txn.get("outlet_id")

        if outlet_id and state.outlet_select:
            state.outlet_select.set_value(outlet_id)

        exec_id = txn.get("sales_executive_id")

        if exec_id and state.exec_select:
            state.exec_select.set_value(exec_id)

        variant_id = txn.get("variant_id")

        car_id = None

        if variant_id:
            variant_obj = next(
                (v for v in state.variants if v["id"] == variant_id),
                None,
            )

            if variant_obj:
                car_id = variant_obj.get("car_id")

        if car_id and state.car_select:
            state.car_select.set_value(car_id)

            state.car_id = car_id

            await _fs_on_car_change(car_id, state, preserve_variant=True)

        if variant_id and state.variant_select:
            state.variant_select.set_value(variant_id)

            state.variant_id = variant_id

        if state.car_color:
            state.car_color.set_value(txn.get("color"))

        # BOOKING
        if state.booking_date:
            state.booking_date.set_value(txn.get("booking_date"))

        if state.booking_amt:
            state.booking_amt.set_value(txn.get("booking_amt"))

        if state.booking_receipt_num:
            state.booking_receipt_num.set_value(txn.get("booking_receipt_num"))

        # CUSTOMER
        customer_map = {
            state.cust_name: txn.get("customer_name"),
            state.cust_mobile: txn.get("mobile_number"),
            state.cust_email: txn.get("email"),
            state.cust_pan: txn.get("pan_number"),
            state.cust_aadhar: txn.get("aadhar_number"),
            state.cust_address: txn.get("address"),
            state.cust_city: txn.get("city"),
            state.cust_pincode: txn.get("pin_code"),
            state.vin_no: txn.get("vin_number"),
            state.engine_no: txn.get("engine_number"),
            state.vehicle_regn_no: txn.get("registration_number"),
            state.car_color: txn.get("color"),
            state.model_year: txn.get("model_year"),
            state.cust_file_no: txn.get("customer_file_number"),
        }

        for widget, value in customer_map.items():
            if widget and value not in [None, ""]:
                widget.set_value(value)

        # CONDITIONS
        for key, cb in getattr(state, "condition_cbs", {}).items():
            val = txn.get(f"cond_{key}", False)

            cb.set_value(bool(val))

        # BOOKING CHECKLIST
        for key, cb in state.booking_cbs.items():
            cb.set_value(bool(txn.get(f"bk_checks_{key}", False)))

        # DELIVERY CHECKLIST
        for key, cb in state.delivery_cbs.items():
            cb.set_value(bool(txn.get(f"del_checks_{key}", False)))

        # SUMMARY FIELDS
        if state.total_discount_booking:
            state.total_discount_booking.set_value(txn.get("discount_booking", 0))

        if getattr(state, "other_discount_delivery", None):
            state.other_discount_delivery.set_value(
                txn.get("other_discount_delivery", 0)
            )

        if state.adjustment_input:
            state.adjustment_input.set_value(txn.get("adjustment_booking", 0))
            state.adjustment_input.set_value(txn.get("adjustment_delivery", 0))

        await hydrate_vehicle_section(state, txn)

        hydrate_invoice_section(state, txn)
        hydrate_payment_section(state, txn)
        hydrate_audit_section(state, txn)
        hydrate_accessories_section(state, txn)
        hydrate_file_status_section(state, txn)
        hydrate_ledger_section(state, txn)

        # PRICE INPUTS
        await _fs_try_price_preload(state)

        for name, inp in getattr(state, "price_inputs", {}).items():
            val = txn.get(f"{name}_actual")

            if val not in [None, ""]:
                inp.set_value(val)
        # DISCOUNT INPUTS
        for name, inp in getattr(state, "discount_inputs", {}).items():
            val = txn.get(f"{name}_actual")

            if val not in [None, ""]:
                inp.set_value(val)

        # UI REFRESH
        refresh_visibility(state)

        _fs_update_live(state)

        _fs_revalidate(state)

    finally:
        state.is_hydrating = False


def hydrate_ledger_section(state: FormState, txn: dict):
    if state.ledger_adjustment:
        state.ledger_adjustment.set_value(txn.get("ledger_adjustment", 0))

    if state.ledger_adjustment_remarks:
        state.ledger_adjustment_remarks.set_value(
            txn.get("ledger_adjustment_remarks", "")
        )


def hydrate_invoice_section(
    state: FormState,
    txn: dict,
):

    mapping = {
        "invoice_number": state.invoice_number,
        "invoice_date": state.invoice_date,
        "ex_showroom_price": state.invoice_ex_showroom,
        "discount": state.invoice_discount,
        "taxable_value": state.invoice_taxable_value,
        "cgst": state.invoice_cgst,
        "sgst": state.invoice_sgst,
        "igst": state.invoice_igst,
        "cess": state.invoice_cess,
        "total": state.invoice_total,
    }

    for key, widget in mapping.items():
        if not widget:
            continue

        value = txn.get(
            key,
            "",
        )

        if value is None:
            value = ""

        widget.set_value(value)


def hydrate_file_status_section(
    state: FormState,
    txn: dict,
):
    try:
        if state.stage == "booking":
            if state.booking_file_incomplete:
                state.booking_file_incomplete.set_value(
                    txn.get("booking_file_incomplete", False)
                )
            if state.booking_file_incomplete_remarks:
                state.booking_file_incomplete_remarks.set_value(
                    txn.get("booking_file_incomplete_remarks", "")
                )
        else:
            if state.delivery_file_incomplete:
                state.delivery_file_incomplete.set_value(
                    txn.get("delivery_file_incomplete", False)
                )
            if state.delivery_file_incomplete_remarks:
                state.delivery_file_incomplete_remarks.set_value(
                    txn.get("delivery_file_incomplete_remarks", "")
                )
    except Exception as e:
        print("ERROR: WHILE FILE HYDRATE", e)


def hydrate_payment_section(
    state: FormState,
    txn: dict,
):

    payment = {k: v for k, v in txn.items() if k.startswith("payment_")}

    mapping = {
        "payment_cash": state.payment_cash,
        "payment_bank": state.payment_bank,
        "payment_finance": state.payment_finance,
        "payment_exchange": state.payment_exchange,
    }

    for key, widget in mapping.items():
        if widget:
            widget.set_value(
                payment.get(
                    key,
                    0,
                )
            )


def hydrate_audit_section(
    state: FormState,
    txn: dict,
):

    if state.audit_obs:
        state.audit_obs.set_value(
            txn.get(
                "audit_observations",
                "",
            )
        )

    if state.audit_action:
        state.audit_action.set_value(
            txn.get(
                "audit_actions",
                "",
            )
        )


def hydrate_accessories_section(
    state: FormState,
    txn: dict,
):

    accessories = txn.get(
        "accessories",
        [],
    )

    if not accessories:
        return

    selected_ids = []

    total = 0

    for acc in accessories:
        acc_id = acc.get("id")

        if acc_id:
            selected_ids.append(acc_id)

            total += acc.get(
                "listed_price",
                0,
            )

    if state.acc_select:
        state.acc_select.set_value(selected_ids)

    if state.acc_total_label:
        state.acc_total_label.set_text(f"Total: ₹{total:,}")

    charged = (
        txn.get(
            "Accessories_actual",
            0,
        )
        or total
    )

    if state.acc_charged:
        state.acc_charged.set_value(charged)


#   PAGE 2: FORM
@ui.page("/form")
@require_roles("admin", "audit_assistant")
async def form_page(
    stage: str = "booking", mode: str = "booking", transaction_id: int | None = None
) -> None:

    state = FormState()

    state.stage = stage
    state.mode = mode

    state.transaction_id = transaction_id
    state.txn_id = transaction_id

    state.is_edit_mode = bool(transaction_id)

    state.is_delivery = stage == "delivery"

    state.is_direct_delivery = mode == "direct"

    state.transaction_data = None

    # Detect edit mode from query param
    if state.booking_id:
        pass

    await load_reference_data(state)
    # TEMP explicit form mode resolution

    await resolve_form_mode(state, stage, transaction_id, mode)

    # Breadcrumb label
    bc = f"Edit Entry #{state.txn_id}" if state.edit_mode else "New Entry"
    render_topbar(bc)

    # Load transaction data
    await load_transaction(state)

    with ui.element("div").classes("max-w-[1200px] mx-auto p-6"):
        # MODE BANNER
        banner_modes = {
            "booking_edit": {
                "title": (f"✏️ Editing Booking #{state.txn_id}"),
                "color": ("bg-blue-100 text-blue-800 border-blue-200"),
            },
            "delivery_from_booking": {
                "title": (f"📦 Converting Booking #{state.txn_id} to Delivery"),
                "color": ("bg-amber-100 text-amber-800 border-amber-200"),
            },
            "delivery_edit": {
                "title": (f"✏️ Editing Delivery #{state.txn_id}"),
                "color": ("bg-green-100 text-green-800 border-green-200"),
            },
        }

        banner = banner_modes.get(state.form_mode)

        if banner:
            variant_label = state.transaction_data.get("variant_name") or ""

            with ui.row().classes("items-center gap-3 mb-4"):
                ui.label(
                    f"{banner['title']}"
                    f"{(' — ' + variant_label) if variant_label else ''}"
                ).classes(
                    f"{banner['color']} "
                    "border px-3 py-1 rounded-md "
                    "text-[12px] font-medium"
                )

                ui.label("Fields pre-filled from saved data").classes(
                    "text-[11px] text-gray-400"
                )

        build_form(state)

    # Hydrate form
    if state.transaction_data:
        await hydrate_form(state, state.transaction_data)

    update_invoice_tax_visibility(state)

    state.form_ready = True
    attach_form_handlers(state)

    refresh_visibility(state)

    _fs_update_live(state)

    _fs_revalidate(state)


# RUN
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
            # Selectors
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

            # Shared Logic
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
                except UnauthorizedError:
                    await logout_user()
                    ui.notify("Session Expired. Please Login again.", type="warning")
                    ui.navigate.to("/login")
                except ConnectionFailedError:
                    ui.notify("Unable to connect to the server", type="warning")

                except APIError as ex:
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

                except APIError as ex:
                    print(f"Error fetching outlets: {ex}")

            # Handlers
            def on_complainant_dealership_change(e):
                import asyncio

                asyncio.create_task(handle_complainant_change(e.value))

            def on_complainee_dealership_change(e):
                import asyncio

                asyncio.create_task(handle_complainee_change(e.value))

            # Bind Events
            state.complainant_dealership.on_value_change(
                on_complainant_dealership_change
            )

            state.complainee_dealership.on_value_change(on_complainee_dealership_change)

            #  SAVE HANDLERS FOR POPULATION (IMPORTANT)
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
            if not state.error_banner or not state.error_msg_label:
                return
            # VALIDATION
            valid, msg = state.is_valid()

            if not valid:
                state.error_msg_label.set_text(msg)
                state.error_banner.set_visibility(True)
                return

            payload = build_complaint_payload(state)

            try:
                # CLEAR OLD ERRORS
                state.error_banner.set_visibility(False)
                # SUBMIT
                await api_post("/complaints/save-complaint", payload)
                ui.notify(
                    "Complaint Submitted Successfully", color="green", type="positive"
                )

                # SUCCESS NAVIGATION
                ui.navigate.to("/")

            except UnauthorizedError:
                await logout_user()
                ui.notify("Session expired. Please login again.", type="warning")
                ui.navigate.to("/login")

            except ConnectionFailedError as e:
                state.error_msg_label.set_text(str(e))
                state.error_banner.set_visibility(True)

            except APIError as e:
                print("COMPLAINT SUBMIT API ERROR:", e)
                state.error_msg_label.set_text(str(e))
                state.error_banner.set_visibility(True)

            except Exception as e:
                print("COMPLAINT SUBMIT ERROR:", e)
                state.error_msg_label.set_text(str(e))
                state.error_banner.set_visibility(True)

        state.submit_btn = (
            ui.button("Submit Complaint", on_click=handle_complaint_submit)
            .classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            )
            .props("no-caps unelevated")
        )


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
                return int(eval(v_str))
            return int(v_str)
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


@require_roles("admin", "audit_assistant")
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
        except APIError as e:
            ui.notify(f"Failed to load complaint: {str(e)}", type="negative")


if __name__ in {"__main__", "__mp_main__"}:
    app.colors(primary="#e8402a")
    ui.run(
        title="AutoAudit",
        favicon="🚗",
        host="0.0.0.0",
        storage_secret=SECRET_KEY_FRONTEND,
        reload=True,  # make false at the time of deployement
        port=3000,
        reconnect_timeout=60,
    )
