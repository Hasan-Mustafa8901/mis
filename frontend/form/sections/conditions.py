from nicegui import ui
from form.state import FormState
from utils.constants import CONDITION_KEYS, FORM_COLUMNS

def build_conditions_section(state: FormState) -> None:
    from form.logic.validation import _fs_revalidate
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("☑️").classes("text-[20px] select-none")
            ui.label("Sale Conditions").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=FORM_COLUMNS + 2).classes("w-full"):
            for key, label in CONDITION_KEYS:
                state.condition_cbs[key] = (
                    ui.checkbox(label)
                    .props("dense color=primary")
                    .classes("text-gray-700 font-medium")
                    .on_value_change(lambda _: _fs_revalidate(state))
                )
