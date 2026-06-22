from datetime import datetime, date
from nicegui import ui

# from main import get_user, FormState

# helper functions


def expandable_remark(text: str):
    LIMIT = 120

    if not text:
        ui.label("-")

    if len(text) <= LIMIT:
        ui.label(text)

    with ui.column().classes("gap-1"):
        preview = ui.label(text[:LIMIT] + "...")

        full = ui.label(text)
        full.visible = False

        def toggle():
            full.visible = not full.visible
            preview.visible = not preview.visible

            btn.text = "Show Less" if full.visible else "See More"

        btn = ui.button("See More", on_click=toggle).props("flat dense")


def render_timeline(history: list):
    if not history:
        with (
            ui.column()
            .classes("w-full items-center justify-center p-8")
            .style("min-height: 300px;")
        ):
            ui.icon("history").classes("text-6xl text-grey-5")

            ui.label("No History Available").classes(
                "text-lg font-medium text-grey-7 mt-4"
            )

            ui.label("Activity related to this complaint will appear here.").classes(
                "text-sm text-grey-6 text-center"
            )

        return
    with ui.timeline(side="right"):
        for item in reversed(history):
            actor = item.get("actor", "Unknown")
            timestamp = item.get("timestamp", "")
            remarks = item.get("remarks", "")

            with ui.timeline_entry(title=actor):
                ui.label(timestamp).classes("text-caption text-grey-700")
                expandable_remark(remarks)


def build_timeline_drawer(state):

    with ui.right_drawer(value=False, elevated=True) as drawer:
        drawer.props("width=500")

        with ui.column().classes("w-full h-full gap-0"):
            # Sticky Header
            with (
                ui.row()
                .classes("w-full items-center justify-between")
                .style(
                    """
                position: sticky;
                top: 0;
                z-index: 10;
                background: white;
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
                """
                )
            ):
                ui.label("Complaint History").classes("text-lg font-bold")

                ui.button(icon="close", on_click=drawer.toggle).props("flat round")

            with ui.scroll_area().classes("w-full flex-grow"):
                render_timeline(state.complaint_history)

    return drawer
