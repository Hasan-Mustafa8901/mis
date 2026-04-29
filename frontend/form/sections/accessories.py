from nicegui import ui
from form.state import FormState
from utils.formatting import accounting_input

from utils.constants import FORM_COLUMNS

def build_accessories_section(state: FormState) -> None:
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🔧").classes("text-[20px] select-none")
            ui.label("Accessories").classes("text-[15px] font-bold text-gray-900")

        options = {
            acc_id: f"{data['name']} (₹{data['listed_price']})"
            for acc_id, data in state.accessory_map.items()
        }

        selection_display = ui.column().classes("w-full mt-2 gap-1 col-span-3")

        def update_total(e):
            selected = e.value or []
            total = sum(
                state.accessory_map.get(int(i), {}).get("listed_price", 0)
                for i in selected
            )

            state.acc_total_label.set_text(f"Total: ₹{total:,.0f}")

            if not state.acc_charged.value:
                state.acc_charged.set_value(total)

            selection_display.clear()
            with selection_display:
                if selected:
                    ui.label("Selected Accessories:").classes(
                        "text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1"
                    )
                    for i in selected:
                        acc = state.accessory_map.get(int(i))
                        if acc:
                            with ui.row().classes(
                                "items-center gap-2 bg-gray-50/50 px-3 py-1.5 rounded-lg border border-gray-100 w-full"
                            ):
                                ui.label(f"ID: {acc['id']}").classes(
                                    "text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded"
                                )
                                ui.label(acc["name"]).classes(
                                    "text-[12px] text-gray-700 font-medium"
                                )
                                ui.label(f"₹{acc['listed_price']:,}").classes(
                                    "text-[11px] text-gray-400 mono ml-auto"
                                )

        with ui.grid(columns=FORM_COLUMNS).classes("w-full items-center gap-4"):
            state.acc_select = (
                ui.select(
                    options=options,
                    label="Select Accessories",
                    multiple=True,
                    with_input=True,
                    on_change=update_total,
                )
                .classes("w-full h-10")
                .props("outlined dense use-input")
            )

            state.acc_total_label = (
                ui.label("Total: ₹0")
                .classes("text-sm text-bold vertical-align-center")
                .props("dense")
            )

            state.acc_charged = accounting_input(label_text="Actual Charged (₹)")
