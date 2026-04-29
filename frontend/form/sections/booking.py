from datetime import date
from nicegui import ui
from form.state import FormState
from form.logic.validation import _fs_revalidate
from form.logic.calculations import _fs_try_price_preload

from utils.constants import FORM_COLUMNS

def build_booking_section(state: FormState):
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📖").classes("text-[20px] select-none")
            ui.label("Booking Details").classes("text-[15px] font-bold text-gray-900")

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
