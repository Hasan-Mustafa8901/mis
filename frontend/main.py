"""
Automobile Sales Audit MIS — NiceGUI Frontend  (v3)
Two-page architecture:
  /      → Dashboard + Persistent MIS Transaction Table
  /form  → Data Entry Form (New + Edit mode)

Backend: FastAPI at http://localhost:8000
"""

import re

# from attrs import field
import httpx
from datetime import date
from nicegui import ui

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
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; }

  body, .q-page, .nicegui-content {
    font-family: 'DM Sans', sans-serif !important;
    background: #ECEEF5 !important;
    color: #1A1D2E !important;
  }

  /* ── Top nav bar ── */
  .topbar {
    background: #1A1D2E;
    border-bottom: 3px solid #E8402A;
    padding: 0 28px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 200;
  }
  .topbar-left  { display: flex; align-items: center; gap: 10px; }
  .topbar-brand { font-size: 15px; font-weight: 700; color: #fff; letter-spacing: -.2px; }
  .topbar-sub   { font-size: 10px; color: rgba(255,255,255,.4); letter-spacing: .8px;
                  text-transform: uppercase; margin-top: 1px; }
  .topbar-divider { width: 1px; height: 22px; background: rgba(255,255,255,.12); margin: 0 14px; }
  .topbar-breadcrumb { font-size: 12px; color: rgba(255,255,255,.5); }
  .topbar-breadcrumb b { color: rgba(255,255,255,.9); font-weight: 500; }

  /* ── Page wrapper ── */
  .page-wrap { max-width: 1320px; margin: 0 auto; padding: 22px 24px 48px; }

  /* ── Dashboard stat cards ── */
  .dash-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 20px; }
  .dash-card {
    background: #fff; border-radius: 10px; border: 1px solid #E0E3EF;
    padding: 18px 22px; box-shadow: 0 1px 4px rgba(0,0,0,.05);
    display: flex; align-items: center; gap: 16px;
  }
  .dash-card-icon {
    width: 42px; height: 42px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; flex-shrink: 0;
  }
  .dash-card-body { flex: 1; min-width: 0; }
  .dash-card-label { font-size: 10.5px; font-weight: 600; letter-spacing: .9px;
                     text-transform: uppercase; color: #6B7280; margin-bottom: 3px; }
  .dash-card-value { font-size: 24px; font-weight: 700; font-family: 'DM Mono', monospace;
                     color: #1A1D2E; line-height: 1; }
  .dash-card-value.red   { color: #DC2626; }
  .dash-card-value.green { color: #059669; }

  /* ── MIS Table card ── */
  .table-card {
    background: #fff; border-radius: 10px; border: 1px solid #E0E3EF;
    box-shadow: 0 1px 4px rgba(0,0,0,.05); overflow: hidden;
  }
  .table-card-header {
    padding: 14px 20px;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #F0F2F8;
  }
  .table-card-title { font-size: 13px; font-weight: 600; color: #1A1D2E; }
  .table-card-count { font-size: 11px; color: #9CA3AF; margin-top: 1px; }

  /* ── Quasar table ── */
  .q-table thead th {
    background: #F4F6FC !important;
    font-size: 10.5px !important; font-weight: 700 !important;
    letter-spacing: .7px !important; text-transform: uppercase !important;
    color: #6B7280 !important; white-space: nowrap;
    border-bottom: 2px solid #E8EAF0 !important;
  }
  .q-table tbody td {
    font-size: 12.5px !important; font-family: 'DM Mono', monospace !important;
    padding: 9px 14px !important;
  }
  .q-table tbody tr { cursor: pointer; transition: background .1s; }
  .q-table tbody tr:hover td { background: #F4F6FC !important; }
  .row-excess td { background: #FFF8F8 !important; }
  .row-excess:hover td { background: #FFF0F0 !important; }

  /* ── Status pills ── */
  .pill {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 9px; border-radius: 20px;
    font-size: 10.5px; font-weight: 700; letter-spacing: .3px;
    font-family: 'DM Sans', sans-serif;
  }
  .pill-ok     { background: #D1FAE5; color: #065F46; }
  .pill-excess { background: #FEE2E2; color: #991B1B; }

  /* ── Add button ── */
  .btn-add {
    background: #E8402A !important; color: #fff !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important; font-size: 13px !important;
    padding: 7px 18px !important; border-radius: 7px !important;
    box-shadow: 0 3px 8px rgba(232,64,42,.28) !important;
  }

  /* ══════════════════════════════
     FORM PAGE
  ══════════════════════════════ */
  .form-page-wrap { max-width: 1100px; margin: 0 auto; padding: 18px 22px 48px; }

  /* Form section cards */
  .fs-card {
    background: #fff; border-radius: 9px; border: 1px solid #E0E3EF;
    padding: 14px 18px 12px; margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
  }
  .fs-title {
    font-size: 9.5px; font-weight: 700; letter-spacing: 1.1px;
    text-transform: uppercase; color: #E8402A;
    margin-bottom: 10px; padding-bottom: 7px;
    border-bottom: 1px solid #F0F2F8;
    display: flex; align-items: center; gap: 6px;
  }
  .fs-subtitle {
    font-size: 9px; font-weight: 700; letter-spacing: .9px;
    text-transform: uppercase; color: #9CA3AF;
    margin: 10px 0 8px; padding-bottom: 5px;
    border-bottom: 1px dashed #E8EAF0;
  }

  /* Compact field overrides */
  .q-field__label    { font-size: 11px !important; font-weight: 500 !important; color: #6B7280 !important; }
  .q-field__native   { font-size: 13px !important; font-family: 'DM Sans', sans-serif !important; }
  .q-checkbox__label { font-size: 12px !important; color: #374151 !important; }
  .q-field--outlined .q-field__control         { border-radius: 6px !important; }
  .q-field--outlined .q-field__control:hover:before { border-color: #2D3561 !important; }
  .q-field--focused  .q-field__control:before  { border-color: #E8402A !important; border-width: 2px !important; }
  .q-field--error    .q-field__control:before  { border-color: #EF4444 !important; }
  .q-field--error    .q-field__messages        { color: #EF4444 !important; font-size: 10.5px !important; }
  .q-field--dense    .q-field__control         { min-height: 36px !important; }
  .num-input .q-field__native { text-align: right !important; font-family: 'DM Mono', monospace !important; }

  /* ── Live bar ── */
  .live-bar {
    background: #1A1D2E; color: #fff; border-radius: 8px;
    padding: 10px 18px; margin-bottom: 10px;
    display: flex; align-items: center; gap: 28px; flex-wrap: wrap;
  }
  .live-label { font-size: 11px; color: rgba(255,255,255,.5); }
  .live-value { font-size: 15px; font-weight: 700; font-family: 'DM Mono', monospace;
                color: #fff; margin-left: 5px; }
  .live-value.excess { color: #FCA5A5; }
  .live-value.ok     { color: #6EE7B7; }

  /* ── Action bar (bottom of form) ── */
  .form-action-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0 4px;
  }
  .btn-submit {
    background: linear-gradient(135deg, #E8402A, #c73019) !important;
    color: #fff !important; font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important; font-size: 13.5px !important;
    padding: 9px 30px !important; border-radius: 7px !important;
    box-shadow: 0 4px 10px rgba(232,64,42,.28) !important;
  }
  .btn-submit[disabled] { opacity: .45 !important; }
  .btn-back {
    color: #6B7280 !important; font-size: 13px !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  /* ── Error banner ── */
  .error-banner {
    background: #FEF2F2; border: 1px solid #FECACA; border-radius: 7px;
    padding: 9px 14px; color: #991B1B; font-size: 12.5px; margin-bottom: 10px;
  }

  /* ── Edit mode badge ── */
  .edit-badge {
    background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;
    border-radius: 6px; padding: 5px 12px; font-size: 12px; font-weight: 500;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: #ECEEF5; }
  ::-webkit-scrollbar-thumb { background: #C4C8D8; border-radius: 3px; }
  .q-notification { font-family: 'DM Sans', sans-serif !important; border-radius: 7px !important; }
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
        ("accessories", "accessories", []),
    ]:
        try:
            result[key] = await api_get(path)
        except Exception:
            result[key] = fallback
    return result


# ══════════════════════════════════════════════════════════════
# TOPBAR  (shared component for both pages)
# ══════════════════════════════════════════════════════════════
def render_topbar(page_label: str) -> None:
    """Injects sticky top nav. page_label is shown as breadcrumb."""
    ui.add_head_html(HEAD_HTML)
    ui.add_body_html(
        f'<div class="topbar">'
        f'  <div class="topbar-left">'
        f"    <div>"
        f'      <div class="topbar-brand">🚗 AutoAudit MIS</div>'
        f'      <div class="topbar-sub">Automobile Sales Audit System</div>'
        f"    </div>"
        f'    <div class="topbar-divider"></div>'
        f'    <div class="topbar-breadcrumb"><b>{page_label}</b></div>'
        f"  </div>"
        f'  <div style="background:#E8402A;color:#fff;font-size:10px;font-weight:700;'
        f'       letter-spacing:.6px;padding:3px 10px;border-radius:20px;">AUDIT PORTAL</div>'
        f"</div>"
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
    ordered += [k for k in keys if "_allowed" in k]
    ordered += [k for k in keys if "_diff" in k]

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
    if not transactions:
        ui.label("No data available")
        return

    ordered_keys = build_ordered_columns(transactions[0])
    # Dynamic columns (NO hardcoding)
    cols = [
        {"name": key, "label": clear_label(key), "field": key, "align": "left"}
        for key in ordered_keys
        if transactions[0]
    ]

    # Table container with horizontal scroll
    with ui.element("div").style("overflow-x: auto; width: 100%;"):
        table = ui.table(
            columns=cols,
            rows=transactions,
            row_key="id",
        ).classes("w-full")

    # Row coloring (status highlight)
    table.add_slot(
        "body",
        """
        <q-tr :props="props"
              :class="props.row.status === 'Excess' ? 'bg-red-2' : 'bg-green-1'">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ props.row[col.field] }}
            </q-td>
        </q-tr>
        """,
    )


# ══════════════════════════════════════════════════════════════
#                        PAGE 1: DASHBOARD
# ══════════════════════════════════════════════════════════════
@ui.page("/")
async def dashboard_page() -> None:
    render_topbar("Dashboard")

    # ── fetch all transactions ─────────────────────────────
    try:
        transactions: list = await api_get("/transactions")
    except Exception:
        transactions = []

    # ── aggregate dashboard stats ─────────────────────────
    total_entries = len(transactions)
    total_discount = sum(t.get("total_discount", 0) or 0 for t in transactions)
    total_excess = sum(t.get("excess_discount", 0) or 0 for t in transactions)

    with ui.element("div").classes("page-wrap"):
        # ── Dashboard stat cards ───────────────────────────
        ui.html(f"""
        <div class="dash-grid">
          <div class="dash-card">
            <div class="dash-card-icon" style="background:#EEF2FF">📋</div>
            <div class="dash-card-body">
              <div class="dash-card-label">Total Entries</div>
              <div class="dash-card-value">{total_entries}</div>
            </div>
          </div>
          <div class="dash-card">
            <div class="dash-card-icon" style="background:#F0FDF4">💸</div>
            <div class="dash-card-body">
              <div class="dash-card-label">Total Discount</div>
              <div class="dash-card-value green">₹{total_discount:,.0f}</div>
            </div>
          </div>
          <div class="dash-card">
            <div class="dash-card-icon" style="background:#FFF5F5">⚠️</div>
            <div class="dash-card-body">
              <div class="dash-card-label">Total Excess Discount</div>
              <div class="dash-card-value {"red" if total_excess > 0 else "green"}">
                ₹{total_excess:,.0f}
              </div>
            </div>
          </div>
        </div>
        """)

        # ── Table card ─────────────────────────────────────
        with ui.element("div").classes("table-card"):
            # Header row: title + Add button
            with ui.element("div").classes("table-card-header"):
                with ui.element("div"):
                    ui.html('<div class="table-card-title">All Transactions</div>')
                    ui.html(
                        f'<div class="table-card-count">{total_entries} record{"s" if total_entries != 1 else ""}</div>'
                    )
                # Add new entry button
                with (
                    ui.button(on_click=lambda: ui.navigate.to("/form"))
                    .classes("btn-add")
                    .props("no-caps unelevated")
                ):
                    ui.icon("add")
                    ui.label("New Entry")

            # ── MIS table ─────────────────────────────────
            render_table(transactions)


# ══════════════════════════════════════════════════════════════
#                        PAGE 1: SETTINGS
# ══════════════════════════════════════════════════════════════


@ui.page("/settings")
def settings_page():
    render_topbar("Settings")

    with ui.card().classes("page-wrap w-full"):
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

                    payload = {
                        # "sheet_name": "0",
                        "valid_from": valid_from.value,
                    }

                    if valid_to.value:
                        payload["valid_to"] = valid_to.value

                    # USE SHARED FILE API
                    await api_post_file("/price-list/upload", file, payload)

                    status_label.text = "✅ Price list uploaded successfully"
                    status_label.classes("text-green-600")

                except Exception as ex:
                    status_label.text = f"❌ {str(ex)}"
                    status_label.classes("text-red-600")

            ui.upload(
                on_upload=handle_upload,
                auto_upload=True,
            ).classes("")

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
        self.txn_id: int | None = None  # set when editing
        self.edit_mode: bool = False

        # Reference data (populated by fetch_reference_data)
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
        self.acc_list: ui.textarea | None = None
        self.acc_charged: ui.number | None = None
        self.acc_total_label: ui.label | None = None
        self.acc_select: ui.select | None = None
        self.accessory_allowed: ui.number | None = None
        self.audit_obs: ui.textarea | None = None
        self.audit_action: ui.textarea | None = None
        self.accessory_select: ui.select | None = None
        self.accessory_charged: ui.number | None = None
        self.accessory_total_label: ui.label | None = None

        self.accessory_map: dict = {}  # {id: {name, price}}

        # UI element refs — actions
        self.submit_btn: ui.button | None = None
        self.error_banner: ui.html | None = None

        # Component toggles: to track state of toggle switches
        self.price_match_toggles: dict[str, ui.switch] = {}
        self.discount_match_toggles: dict[str, ui.switch] = {}

        self.listed_prices: dict[str, int] = {}
        self.price_listed_labels: dict[str, ui.label] = {}
        self.discount_listed_labels: dict[str, ui.label] = {}

        # Component inputs: name → ui.number
        self.price_inputs: dict[str, ui.number] = {}
        self.discount_inputs: dict[str, ui.number] = {}

        # Checkboxes
        self.condition_cbs: dict[str, ui.checkbox] = {}
        self.delivery_cbs: dict[str, ui.checkbox] = {}

        # Invoice Section
        self.invoice_number: ui.input | None = None
        self.invoice_date: ui.input | None = None
        self.invoice_ex_showroom: ui.number | None = None
        self.invoice_discount: ui.number | None = None
        self.invoice_taxable_value: ui.number | None = None
        self.invoice_cgst: ui.number | None = None
        self.invoice_sgst: ui.number | None = None
        self.invoice_igst: ui.number | None = None
        self.invoice_cess: ui.number | None = None
        self.invoice_total: ui.number | None = None

        # Payment Section
        self.payment_cash: ui.number | None = None
        self.payment_bank: ui.number | None = None
        self.payment_finance: ui.number | None = None
        self.payment_exchange: ui.number | None = None

        # Live calc labels
        self.lbl_discount: ui.label | None = None
        self.lbl_excess: ui.label | None = None

    # ── computed ─────────────────────────────────────────
    @property
    def all_component_inputs(self) -> dict[str, ui.number]:
        return {**self.price_inputs, **self.discount_inputs}

    @property
    def live_discount(self) -> int:
        return sum(int(inp.value or 0) for inp in self.discount_inputs.values())

    def is_valid(self) -> tuple[bool, str]:
        def _val(f):
            return (f.value or "").strip() if f else ""

        def _val_upper(f):
            return (f.value or "").strip().upper() if f else ""

        if not self.variant_id:
            return False, "Please select a Car and Variant."

        name = _val(self.cust_name)
        if not name:
            return False, "Customer name is required."

        mob = _val(self.cust_mobile)
        if not re.fullmatch(r"[6-9]\d{9}", mob):
            return False, "Mobile must be 10 digits starting with 6–9."

        if not _val(self.cust_address):
            return False, "Address is required."

        if not _val(self.cust_city):
            return False, "City is required."

        if not re.fullmatch(r"\d{6}", _val(self.cust_pincode)):
            return False, "Valid 6-digit PIN code required."

        if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", _val_upper(self.cust_pan)):
            return False, "Valid PAN required."

        if not re.fullmatch(r"\d{12}", _val(self.cust_aadhar)):
            return False, "Valid Aadhar required."

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

        year = _val(self.model_year)
        if not year or not str(year).isdigit():
            return False, "Valid Model Year is required."

        return True, ""


# ══════════════════════════════════════════════════════════════
# FORM SECTION BUILDERS
# ══════════════════════════════════════════════════════════════
def build_form_sec_vehicle(state: FormState) -> None:
    car_opts = {car["id"]: car["name"] for car in state.cars}
    outlet_opts = {outlet["id"]: outlet["name"] for outlet in state.outlets}
    exec_opts = {executive["id"]: executive["name"] for executive in state.executives}

    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">🚙 &nbsp;Vehicle &amp; Delivery Details</div>')
        with ui.grid(columns=5).classes("w-full gap-2"):
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
                    # with_input=True,
                    label="Variant *",
                    on_change=lambda e: _fs_on_variant_change(e.value, state),
                )
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )
            state.booking_date = (
                ui.input(
                    label="Booking Date *",
                    value=str(date.today()),
                    on_change=lambda _: _fs_try_price_preload(state),
                )
                .classes("w-full")
                .props('type="date" outlined dense')
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )
            # TODO: Get outlet from user profile once auth is implemented, and make this non-editable for most users
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
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )

            state.vin_no = (
                ui.input(label="VIN Number *")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )

            state.engine_no = (
                ui.input(label="Engine Number *")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )

            state.model_year = (
                ui.input(label="Model Year *", placeholder="e.g. 2024")
                .classes("w-full")
                .props('outlined dense type="number"')
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )
            state.vehicle_regn_no = (
                ui.input(label="Vehicle Regn Number")
                .classes("w-full")
                .props("outlined dense")
            )

            state.regn_date = (
                ui.input(label="Date of Registration")
                .classes("w-full")
                .props('outlined dense type="date"')
            )
        # Set defaults for outlet / exec
        if state.outlets:
            state.outlet_select.set_value(state.outlets[0]["id"])
            state.outlet_id = state.outlets[0]["id"]
        if state.executives:
            state.exec_select.set_value(state.executives[0]["id"])
            state.executive_id = state.executives[0]["id"]


# def build_form_sec_customer(state: FormState) -> None:
#     with ui.element("div").classes("fs-card"):
#         ui.html('<div class="fs-title">👤 &nbsp;Customer</div>')
#         with ui.grid(columns=3).classes("w-full gap-2"):
#             state.cust_name = (
#                 ui.input(label="Name *", placeholder="Full name")
#                 .classes("w-full")
#                 .props("outlined dense")
#                 .on("blur", lambda: _fs_revalidate(state))
#             )
#             state.cust_mobile = (
#                 ui.input(label="Mobile *", placeholder="10-digit")
#                 .classes("w-full")
#                 .props("outlined dense")
#                 .on("blur", lambda: _fs_validate_mobile(state))
#             )
#             state.cust_email = (
#                 ui.input(label="Email", placeholder="optional")
#                 .classes("w-full")
#                 .props("outlined dense")
#             )
def build_form_sec_customer(state: FormState) -> None:
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">👤 &nbsp;Customer</div>')

        # ── Basic Info ─────────────────────────────
        with ui.grid(columns=3).classes("w-full gap-2"):
            state.cust_name = (
                ui.input(label="Name *", placeholder="Full name")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )
            state.cust_mobile = (
                ui.input(label="Mobile *", placeholder="10-digit")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_validate_mobile(state))
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
                ui.input(label="Address *")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )

            state.cust_city = (
                ui.input(label="City *")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_revalidate(state))
            )

            state.cust_pincode = (
                ui.input(label="Pin Code *", placeholder="6 digits")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_validate_pincode(state))
            )

            state.cust_pan = (
                ui.input(label="PAN *", placeholder="ABCDE1234F")
                .classes("w-full")
                .props("outlined dense")
                .on(
                    "update:model-value",
                    lambda e: (
                        state.cust_pan.set_value(e.value.upper()),
                        _fs_validate_pan(state),
                    ),
                )
            )

            state.cust_aadhar = (
                ui.input(label="Aadhar *", placeholder="12 digits")
                .classes("w-full")
                .props("outlined dense")
                .on("update:model-value", lambda _: _fs_validate_aadhar(state))
            )

            # ── Conditional Field (TR Case) ────────────
            state.cust_other_id = (
                ui.input(label="Other ID Proof")
                .classes("w-full")
                .props("outlined dense")
            )


def build_form_sec_conditions(state: FormState) -> None:
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">☑️ &nbsp;Sale Conditions</div>')
        with ui.row().classes("flex-wrap gap-4"):
            for key, label in CONDITION_KEYS:
                state.condition_cbs[key] = (
                    ui.checkbox(label)
                    .props("dense")
                    .on("update:model-value", lambda _: _fs_revalidate(state))
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

    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">💰 &nbsp;Price &amp; Discounts</div>')

        ui.html('<div class="fs-subtitle">Price Charged</div>')
        if price_comps:
            with ui.grid(columns=1).classes("w-full gap-2"):
                for comp in price_comps:
                    name = comp["name"]

                    with ui.row().classes("w-full items-center gap-2"):
                        # Label
                        ui.label(name).classes("w-40 text-xs")

                        # Listed price display
                        listed_label = ui.label("₹—").classes(
                            "w-32 text-gray-500 text-xs"
                        )
                        state.price_listed_labels[name] = listed_label

                        # Toggle (Match Listed Price)
                        toggle = (
                            ui.switch("Match Listed Price")
                            .classes("m-10")
                            .props('dense icon="check" color="green"')
                        )

                        # Input
                        inp = (
                            ui.number(
                                placeholder="Enter Charged Price", format="%.0f", min=0
                            )
                            .classes("w-60 num-input")
                            .props("outlined dense")
                        )

                        state.price_inputs[name] = inp
                        state.price_match_toggles[name] = toggle

                        # def on_toggle(e, name=name, inp=inp):
                        #     if e.args:
                        #         # copy listed price
                        #         val = state.listed_prices.get(name, 0)
                        #         inp.set_value(val)
                        #         inp.props("readonly")
                        #     else:
                        #         inp.set_value(None)
                        #         inp.props("remove=disable")

                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(val)
                                inp.set_enabled(False)  # ✅ disable input
                            else:
                                inp.set_enabled(True)  # ✅ re-enable input
                                inp.set_value(None)  # optional: clear

                        toggle.on("update:model-value", on_toggle)

        else:
            ui.label("No price components — check /components endpoint.").classes(
                "text-xs text-gray-400"
            )

        ui.html(
            '<div class="fs-subtitle" style="margin-top:12px">Discounts Offered</div>'
        )
        if discount_comps:
            with ui.grid(columns=1).classes("w-full gap-2"):
                for comp in discount_comps:
                    name = comp["name"]

                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(name).classes("w-40 text-xs")

                        listed_label = ui.label("₹—").classes(
                            "w-32 text-gray-500 text-xs"
                        )
                        state.discount_listed_labels[name] = listed_label

                        toggle = (
                            ui.switch("Standard Discount")
                            .props("dense icon=check color=green")
                            .classes("m-10")
                        )

                        inp = (
                            ui.number(placeholder="₹", format="%.0f", min=0)
                            .classes("w-60 num-input")
                            .props("outlined dense")
                            .on("update:model-value", lambda: _fs_update_live(state))
                        )

                        state.discount_inputs[name] = inp
                        state.discount_match_toggles[name] = toggle

                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(val)
                                inp.set_enabled(False)  # ✅ disable input
                            else:
                                inp.set_enabled(True)  # ✅ re-enable input
                                inp.set_value(None)  # optional: clear

                        toggle.on("update:model-value", on_toggle)

        else:
            ui.label("No discount components — check /components endpoint.").classes(
                "text-xs text-gray-400"
            )


def build_form_sec_accessories(state: FormState) -> None:
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">🔧 &nbsp;Accessories</div>')

        # Placeholder options (replace with dynamic from state.accessory_map)
        # state.accessory_map = {
        #     1: {"name": "Floor Mats", "price": 2000},
        #     2: {"name": "Seat Covers", "price": 5000},
        #     3: {"name": "Car Cover", "price": 3000},
        #     4: {"name": "Roof Rack", "price": 4500},
        # }

        options = {
            acc_id: f"{data['name']} (₹{data['price']})"
            for acc_id, data in state.accessory_map.items()
        }

        def update_total(e):
            selected = e.value or []
            total = sum(
                state.accessory_map[int(i)]["price"]
                for i in selected
                if int(i) in state.accessory_map
            )

            state.acc_total_label.set_text(f"₹{total:,.0f}")

            # auto-fill charged if empty
            if not state.acc_charged.value:
                state.acc_charged.set_value(total)

        # ── Multi-select ───────────────────────────
        with ui.grid(columns=3).classes("items-center gap-4"):
            state.acc_select = (
                ui.select(
                    options=options,
                    label="Select Accessories",
                    multiple=True,
                    with_input=True,  # search enabled
                    on_change=update_total,
                )
                .classes("w-full")
                .props("outlined dense use-input")
            )

            # ── Total Display ──────────────────────────
            state.acc_total_label = ui.label("₹0").classes("text-sm text-gray-600")

            # ── Charged Input ─────────────────────────
            state.acc_charged = (
                ui.number(label="Actual Charged (₹)", format="%.0f", min=0)
                .classes("w-full num-input")
                .props("outlined dense")
            )


# def build_form_sec_accessories(state: FormState) -> None:
#     with ui.element("div").classes("fs-card"):
#         ui.html('<div class="fs-title">🔧 &nbsp;Accessories</div>')
#         with ui.grid(columns=3).classes("w-full gap-2"):
#             with ui.element("div").classes("col-span-1"):
#                 state.acc_list = (
#                     ui.textarea(label="Accessories List", placeholder="One per line")
#                     .classes("w-full")
#                     .props("outlined dense rows=2")
#                 )
#             state.accessory_charged = (
#                 ui.number(label="Charged (₹)", placeholder="0", format="%.0f", min=0)
#                 .classes("w-full num-input")
#                 .props("outlined dense")
#             )
#             state.accessory_allowed = (
#                 ui.number(label="Allowed (₹)", placeholder="0", format="%.0f", min=0)
#                 .classes("w-full num-input")
#                 .props("outlined dense")
#             )


def build_form_sec_delivery(state: FormState) -> None:
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">✅ &nbsp;Delivery Checklist</div>')
        with ui.grid(columns=5).classes("w-full gap-y-2"):
            for key, label in DELIVERY_CHECK_KEYS:
                state.delivery_cbs[key] = ui.checkbox(label).props("dense")


def build_form_sec_audit(state: FormState) -> None:
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">📋 &nbsp;Audit</div>')
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
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">🧾 &nbsp;Invoice Details</div>')

        with ui.grid(columns=3).classes("w-full gap-2"):
            state.invoice_number = ui.input(label="Invoice Number").props(
                "outlined dense"
            )
            state.invoice_date = ui.input(label="Invoice Date").props(
                'outlined dense type="date"'
            )

            state.invoice_ex_showroom = ui.number(
                label="Ex-Showroom Price", format="%.0f"
            ).props("outlined dense readonly")

            state.invoice_discount = ui.number(label="Discount", format="%.0f").props(
                "outlined dense"
            )
            state.invoice_taxable_value = ui.number(
                label="Taxable Value", format="%.0f"
            ).props("outlined dense")
            state.invoice_cgst = ui.number(label="CGST", format="%.0f").props(
                "outlined dense"
            )

            state.invoice_sgst = ui.number(label="SGST", format="%.0f").props(
                "outlined dense"
            )
            state.invoice_igst = ui.number(label="IGST", format="%.0f").props(
                "outlined dense"
            )
            state.invoice_cess = ui.number(label="CESS", format="%.0f").props(
                "outlined dense"
            )

            state.invoice_total = ui.number(
                label="Total Invoice Value", format="%.0f"
            ).props("outlined dense")


def build_form_sec_payment(state: FormState) -> None:
    with ui.element("div").classes("fs-card"):
        ui.html('<div class="fs-title">💳 &nbsp;Payment Received</div>')

        with ui.grid(columns=4).classes("w-full gap-2"):
            state.payment_cash = ui.number(label="Cash Payment", format="%.0f").props(
                "outlined dense"
            )

            state.payment_bank = ui.number(label="Bank Payment", format="%.0f").props(
                "outlined dense"
            )

            state.payment_finance = ui.number(label="Finance", format="%.0f").props(
                "outlined dense"
            )

            state.payment_exchange = ui.number(label="Exchange", format="%.0f").props(
                "outlined dense"
            )

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
    with ui.element("div").classes("live-bar w-full"):
        ui.html(
            '<span style="font-size:9px;font-weight:700;letter-spacing:1px;color:rgba(255,255,255,.35);text-transform:uppercase">Live Totals</span>'
        )
        ui.html('<span style="color:rgba(255,255,255,.15);font-size:18px">|</span>')
        with ui.row().classes("items-center"):
            ui.html('<span class="live-label">Total Discount:</span>')
            state.lbl_discount = ui.label("₹0").classes("live-value")
        with ui.row().classes("items-center"):
            ui.html('<span class="live-label">Excess (after save):</span>')
            state.lbl_excess = (
                ui.label("—")
                .classes("live-value")
                .style("color:rgba(255,255,255,.3);font-size:13px")
            )


def build_form_sec_action_bar(state: FormState) -> None:
    state.error_banner = ui.html("").classes("w-full")
    with ui.element("div").classes("form-action-bar w-full"):
        ui.button("← Back to Dashboard", on_click=lambda: ui.navigate.to("/")).classes(
            "btn-back"
        ).props("flat no-caps")
        state.submit_btn = (
            ui.button(
                "Save Entry" if not state.edit_mode else "Update Entry",
                on_click=lambda: _fs_handle_submit(state),
            )
            .classes("btn-submit")
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
        print("Price preload skipped: missing variant or booking date")
        return

    try:
        booking_date = state.booking_date.value
        print(
            f"Attempting price preload for variant {state.variant_id} on {booking_date}"
        )

        preview = await api_get(
            f"/price-list/preview?variant_id={state.variant_id}&booking_date={booking_date}"
        )
        print(f"API returned price preview: {preview}")

        # ── Store listed prices (source of truth) ──
        state.listed_prices = preview or {}
        print(f"Listed prices set in state: {state.listed_prices}")
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


# async def _fs_try_price_preload(state: FormState) -> None:
#     """Call GET /price-list/preview when both variant + date are known."""
#     if not state.variant_id or not (state.booking_date and state.booking_date.value):
#         return
#     try:
#         booking_date = state.booking_date.value
#         preview = await api_get(
#             f"/price-list/preview?variant_id={state.variant_id}&date={booking_date}"
#         )
#         state.listed_prices = preview
#         for name, value in preview.items():
#             formatted = f"₹{int(value):,}"

#             # update price labels
#             if name in state.price_listed_labels:
#                 state.price_listed_labels[name].set_text(formatted)

#             # update discount labels
#             if name in state.discount_listed_labels:
#                 state.discount_listed_labels[name].set_text(formatted)
#         filled = 0
#         for name, inp in state.all_component_inputs.items():
#             if name in preview and preview[name] is not None:
#                 value = preview[name]

#                 # update listed price
#                 if name in state.price_match_toggles:
#                     pass
#                 inp.set_value(value)
#             if name in preview and preview[name] is not None:
#                 inp.set_value(preview[name])
#                 filled += 1

#         _fs_update_live(state)

#         if filled:
#             ui.notify(
#                 f"✓ {filled} field{'s' if filled > 1 else ''} auto-filled from price list.",
#                 type="info",
#                 position="top-right",
#                 timeout=2500,
#             )
#     except Exception:
#         pass  # best-effort; silently skip if endpoint missing


def _fs_update_live(state: FormState) -> None:
    if not state.lbl_discount:
        return
    total = state.live_discount
    state.lbl_discount.set_text(f"₹{total:,.0f}")
    # Sync Ex-showroom → Invoice
    if state.invoice_ex_showroom and "Ex Showroom Price" in state.price_inputs:
        val = state.price_inputs["Ex Showroom Price"].value or 0
        state.invoice_ex_showroom.set_value(val)


def _fs_validate_mobile(state: FormState) -> None:
    if state.cust_mobile is None:
        return
    mob = (state.cust_mobile.value or "").strip()
    if mob and not re.fullmatch(r"[6-9]\d{9}", mob):
        state.cust_mobile.props("error error-message='Must be 10 digits starting 6–9'")
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


# def _fs_revalidate(state: FormState) -> None:
#     ok, _ = state.is_valid()
#     if state.submit_btn:
#         state.submit_btn.set_enabled(ok)
def _fs_revalidate(state: FormState) -> None:
    ok, msg = state.is_valid()
    print(f"Form validation: {ok}, {msg}")

    if state.submit_btn:
        state.submit_btn.set_enabled(ok)

    if state.error_banner:
        if not ok:
            state.error_banner.set_content(f'<div class="error-banner">⚠ {msg}</div>')
        else:
            state.error_banner.set_content("")


def _fs_clear_prices(state: FormState) -> None:
    for inp in state.price_inputs.values():
        inp.set_value(None)


def _fs_show_error(state: FormState, msg: str) -> None:
    if state.error_banner:
        state.error_banner.set_content(f'<div class="error-banner">⚠ &nbsp;{msg}</div>')


def _fs_clear_error(state: FormState) -> None:
    if state.error_banner:
        state.error_banner.set_content("")


# ══════════════════════════════════════════════════════════════
# SUBMIT HANDLER
# ══════════════════════════════════════════════════════════════
async def _fs_handle_submit(state: FormState) -> None:
    valid, msg = state.is_valid()
    if not valid:
        state.error_banner.set_content(msg)
        return

    payload = build_payload(state)

    try:
        await api_post("/transactions", payload)
        ui.notify("✅ Transaction saved", color="green")
        ui.navigate.to("/")
    except Exception as e:
        state.error_banner.set_content(str(e))


def build_payload(state: FormState) -> dict:
    def val(x):
        return x.value if x else None

    def intval(x):
        return int(x.value or 0) if x else 0

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
    accessories_details = {
        "items": [
            {
                "id": state.accessory_select.value,
                "name": state.accessory_map.get(state.accessory_select.value, {}).get(
                    "name"
                ),
                "price": intval(state.accessory_charged),
            }
        ]
        if state.accessory_select and state.accessory_select.value
        else [],
        "charged_amount": intval(state.accessory_charged),
        "allowed_amount": intval(state.accessory_allowed),
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
    acc = txn.get("accessories_details", {})
    if state.acc_list:
        state.acc_list.set_value(acc.get("list", ""))
    if state.accessory_charged:
        state.accessory_charged.set_value(acc.get("charged", 0))
    if state.accessory_allowed:
        state.accessory_allowed.set_value(acc.get("allowed", 0))

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

    with ui.element("div").classes("form-page-wrap"):
        # ── Edit mode indicator ──────────────────────────
        if state.edit_mode:
            variant_label = txn_data.get("variant", "") if txn_data else ""
            ui.html(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'  <span class="edit-badge">✏️  Editing Transaction #{state.txn_id}'
                f"  {(' — ' + variant_label) if variant_label else ''}</span>"
                f'  <span style="font-size:11px;color:#9CA3AF">All fields pre-filled from saved data</span>'
                f"</div>"
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
ui.run(
    title="AutoAudit",
    favicon="🚗",
    host="0.0.0.0",
    port=3000,
    reload=True,
)
