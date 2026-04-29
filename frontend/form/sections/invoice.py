from nicegui import ui
from form.state import FormState
from utils.formatting import format_num_inr, accounting_input
from utils.parsing import parsed_val
from form.logic.calculations import _fs_update_live

from utils.constants import FORM_COLUMNS

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
            parsed_val(state.igst_toggle)
            if state.igst_toggle and state.igst_toggle.value
            else 0
        )
        # Correcting igst/cess logic from main.py lines 4198-4207
        igst_val = parsed_val(state.invoice_igst) if state.igst_toggle and state.igst_toggle.value else 0
        cess_val = parsed_val(state.invoice_cess) if state.cess_toggle and state.cess_toggle.value else 0

        total = taxable + cgst + sgst + igst_val + cess_val
        state.invoice_total.set_value(format_num_inr(total))

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🧾").classes("text-[20px] select-none")
            ui.label("Invoice Details").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
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
