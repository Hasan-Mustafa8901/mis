from nicegui import ui
from form.state import FormState
from form.logic.mapping import _fs_handle_submit

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
        ui.button("← Back to Dashboard", on_click=lambda: ui.navigate.to("/")).classes(
            "text-gray-500 text-[13px] hover:text-gray-800"
        ).props("flat no-caps")
        state.submit_btn = (
            ui.button(
                "Save Entry" if not state.edit_mode else "Update Entry",
                on_click=lambda: _fs_handle_submit(state),
            )
            .classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            )
            .props("no-caps unelevated")
        )

def build_complaint_action_bar(state: FormState) -> None:
    from services.api import api_post
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
            valid, msg = state.is_valid()
            if not valid:
                state.error_msg_label.set_text(msg)
                state.error_banner.set_visibility(True)
                return

            from form.logic.mapping import build_complaint_payload
            payload = build_complaint_payload(state)
            try:
                await api_post("/complaints/save-complaint", payload)
                ui.notify(
                    "Complaint Submitted Successfully", color="green", type="positive"
                )
                ui.navigate.to("/")
            except Exception as e:
                state.error_msg_label.set_text(str(e))
                state.error_banner.set_visibility(True)

        state.submit_btn = (
            ui.button("Submit Complaint", on_click=handle_complaint_submit)
            .classes(
                "bg-gradient-to-r from-[#E8402A] to-[#c73019] text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-red-500/20"
            )
            .props("no-caps unelevated")
        )

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
            state.lbl_allowed = ui.label("₹0").classes(
                "text-[16px] font-bold text-white mono"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Discount Given:").classes("text-[11px] text-white/50")
            state.lbl_discount = ui.label("₹0").classes(
                "text-[16px] font-bold text-white mono"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Excess Discount:").classes("text-[11px] text-white/50")
            state.lbl_excess = ui.label("—").classes(
                "text-[16px] font-bold text-white/30 mono"
            )
