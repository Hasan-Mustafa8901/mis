from nicegui import ui
from form.state import FormState

def build_audit_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("📋").classes("text-[20px] select-none")
            ui.label("Audit").classes("text-[15px] font-bold text-gray-900")
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
