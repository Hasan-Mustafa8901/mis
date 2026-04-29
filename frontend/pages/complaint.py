from nicegui import ui
from auth.auth import protected_page
from components.layout import render_topbar
from services.api import api_get
from services.reference_data import fetch_reference_data
from form.state import FormState
from form.sections.complaint import (
    build_complaint_dealership_section,
    build_complaint_quotation_section,
    build_complaint_booking_section,
    build_complaint_remarks_section,
)
from form.sections.action_bar import build_complaint_action_bar
from form.sections.customer import build_customer_section
from form.sections.vehicle import build_vehicle_section
from form.logic.mapping import populate_from_complaint

@ui.page("/complaint-form")
@protected_page
async def complaint_form_page(
    transaction_id: int | None = None, complaint_code: str | None = None
) -> None:
    state = FormState()
    state.stage = "complaint"
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

    # Load existing complaint data if complaint_code is provided
    if complaint_code:
        try:
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

    with ui.element("div").classes("max-w-[1100px] mx-auto p-6"):
        ui.label("Complaint MIS Form").classes("text-2xl font-bold mb-5")

        build_complaint_dealership_section(state)
        build_customer_section(state)
        build_vehicle_section(state)
        build_complaint_quotation_section(state)
        build_complaint_booking_section(state)
        build_complaint_remarks_section(state)
        build_complaint_action_bar(state)
