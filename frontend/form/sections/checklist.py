from nicegui import ui
from form.state import FormState
from form.logic.validation import _fs_revalidate
from utils.constants import BOOKING_CHECK_KEYS, DELIVERY_CHECK_KEYS, FORM_COLUMNS

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
