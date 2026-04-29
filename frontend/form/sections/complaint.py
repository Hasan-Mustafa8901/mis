from nicegui import ui
from form.state import FormState
from utils.formatting import accounting_input
from services.api import api_get

def build_complaint_dealership_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🏢").classes("text-[20px] select-none")
            ui.label("Dealership Details").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=2).classes("w-full gap-5"):
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

            def on_complainant_dealership_change(e):
                dlr = e.value
                if dlr:
                    filtered_dealerships = {"X": "X"}
                    for d in state.complaint_dealerships:
                        if d["name"] != dlr:
                            filtered_dealerships[d["name"]] = d["name"]
                    state.complainee_dealership.options = filtered_dealerships
                    state.complainee_dealership.update()

                    import asyncio
                    async def fetch_outlets():
                        try:
                            outs = await api_get(f"/complaints/dealerships/{dlr}/outlets")
                            if outs:
                                state.complainant_showroom.options = {o: o for o in outs}
                                state.complainant_showroom.update()
                        except Exception as ex:
                            print(f"Error fetching outlets: {ex}")
                    asyncio.create_task(fetch_outlets())
                else:
                    complainee_options = {"X": "X"}
                    for d in state.complaint_dealerships:
                        complainee_options[d["name"]] = d["name"]
                    state.complainee_dealership.options = complainee_options
                    state.complainee_dealership.update()
                    state.complainant_showroom.options = {}
                    state.complainant_showroom.update()

            def on_complainee_dealership_change(e):
                dlr = e.value
                if dlr == "X":
                    state.complainee_showroom.options = {"X": "X"}
                    state.complainee_showroom.update()
                elif dlr:
                    import asyncio
                    async def fetch_outlets():
                        try:
                            outs = await api_get(f"/complaints/dealerships/{dlr}/outlets")
                            if outs:
                                showroom_options = {"X": "X"}
                                for o in outs:
                                    showroom_options[o] = o
                                state.complainee_showroom.options = showroom_options
                                state.complainee_showroom.update()
                        except Exception as ex:
                            print(f"Error fetching outlets: {ex}")
                    asyncio.create_task(fetch_outlets())
                else:
                    state.complainee_showroom.options = {"X": "X"}
                    state.complainee_showroom.update()

            state.complainant_dealership.on_value_change(on_complainant_dealership_change)
            state.complainee_dealership.on_value_change(on_complainee_dealership_change)


def build_complaint_quotation_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📋").classes("text-[20px] select-none")
            ui.label("Complaint Quotation Details").classes("text-[15px] font-bold text-gray-900")
        with ui.grid(columns=3).classes("w-full gap-5"):
            state.comp_quotation_no = ui.input(label="Quotation Number").classes("w-full").props("outlined dense")
            state.comp_quotation_date = ui.input(label="Quotation Date").classes("w-full").props('outlined dense type="date"')
            state.comp_tcs = accounting_input(label_text="TCS")
            state.comp_total_offered = accounting_input(label_text="Total Offered Price")
            state.comp_net_offered = accounting_input(label_text="Net Offered Price")


def build_complaint_booking_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📝").classes("text-[20px] select-none")
            ui.label("Complaint Booking Details").classes("text-[15px] font-bold text-gray-900")
        with ui.grid(columns=3).classes("w-full gap-5"):
            state.comp_booking_file_no = ui.input(label="Booking File Number").classes("w-full").props("outlined dense")
            state.comp_receipt_no = ui.input(label="Receipt Number").classes("w-full").props("outlined dense")
            state.comp_booking_amt = accounting_input(label_text="Booking Amount")
            state.comp_mode_of_payment = ui.input(label="Mode of Payment").classes("w-full").props("outlined dense")
            state.comp_instrument_date = ui.input(label="Instrument Date").classes("w-full").props('outlined dense type="date"')
            state.comp_instrument_no = ui.input(label="Instrument Number").classes("w-full").props("outlined dense")
            state.comp_bank_name = ui.input(label="Bank Name").classes("w-full").props("outlined dense")


def build_complaint_remarks_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("💬").classes("text-[20px] select-none")
            ui.label("Remarks").classes("text-[15px] font-bold text-gray-900")
        with ui.grid(columns=2).classes("w-full gap-5"):
            state.complaint_date = ui.input(label="Date of Complaint Raised").classes("w-full").props('outlined dense type="date"')
            state.complainee_aa_name = ui.input(label="Audit Assistant Name at Complainee").classes("w-full").props("outlined dense")
            state.complainant_remarks = ui.textarea(label="Remarks by Complainant *").classes("w-full").props("outlined dense rows=3")
            state.complainant_aa_remarks = ui.textarea(label="Remarks by Audit Assistant at Complainant").classes("w-full").props("outlined dense rows=3")



