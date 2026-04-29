import re
from nicegui import ui
from form.state import FormState
from form.logic.validation import _fs_revalidate

from utils.constants import FORM_COLUMNS

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
