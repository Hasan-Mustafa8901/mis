from nicegui import ui
from form.state import FormState
from utils.formatting import accounting_input

from utils.constants import FORM_COLUMNS

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

        def toggle_fields():
            if state.condition_cbs.get("finance"):
                state.payment_finance.set_enabled(state.condition_cbs["finance"].value)
            if state.condition_cbs.get("exchange"):
                state.payment_exchange.set_enabled(state.condition_cbs["exchange"].value)

        for key in ["finance", "exchange"]:
            if key in state.condition_cbs:
                state.condition_cbs[key].on("update:model-value", lambda _: toggle_fields())

        toggle_fields()
