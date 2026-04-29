from nicegui import ui
from auth.auth import protected_page
from components.layout import render_topbar
from services.api import api_get
from services.reference_data import fetch_reference_data
from form.state import FormState
from form.sections.vehicle import build_vehicle_section
from form.sections.booking import build_booking_section
from form.sections.customer import build_customer_section
from form.sections.prices import build_prices_section
from form.sections.accessories import build_accessories_section
from form.sections.invoice import build_invoice_section
from form.sections.payment import build_payment_section
from form.sections.checklist import build_booking_checklist_section, build_delivery_section
from form.sections.conditions import build_conditions_section
from form.sections.audit import build_audit_section
from form.sections.action_bar import build_action_bar, build_live_bar
from form.logic.mapping import populate_from_booking, _fs_prefill
from form.logic.validation import _fs_revalidate

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

        try:
            txn_data = await api_get(f"/transactions/{transaction_id}")
            state.booking_data = txn_data
        except Exception:
            ui.notify("Failed to load booking data", type="negative")

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
        if state.edit_mode and txn_data:
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
