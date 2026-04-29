from nicegui import ui

def open_new_entry_dialog():
    with ui.dialog() as dialog, ui.card().classes("p-6 w-80"):
        ui.label("Create New Entry").classes("text-lg font-bold mb-2")

        ui.button(
            "Booking",
            on_click=lambda: (dialog.close(), ui.navigate.to("/form?stage=booking")),
        ).classes("w-full mb-2")

        ui.button(
            "Delivery",
            on_click=lambda: (
                dialog.close(),
                ui.navigate.to("/form?stage=delivery&mode=direct"),
            ),
        ).classes("w-full")

    dialog.open()
