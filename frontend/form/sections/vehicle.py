from utils.constants import FORM_COLUMNS
from datetime import date
from nicegui import ui
from form.state import FormState
from form.logic.validation import _fs_revalidate
from form.logic.calculations import _fs_try_price_preload
from services.api import api_get


async def _fs_on_car_change(car_id, state: FormState) -> None:
    state.car_id = car_id
    state.variant_id = None
    if state.variant_select is None:
        return
    state.variant_select.set_value(None)
    state.variant_select.options = {}
    state.variant_select.update()

    # helper to clear prices
    for inp in state.price_inputs.values():
        inp.set_value(None)

    if not car_id:
        return
    try:
        variants = await api_get(f"/cars/{car_id}/variants")
        state.variant_select.options = {
            v["id"]: v["full_variant_name"] for v in variants
        }
        state.variant_select.update()
    except Exception as ex:
        if state.error_banner and state.error_msg_label:
            state.error_msg_label.set_text(f"Failed to load variants: {ex}")
            state.error_banner.set_visibility(True)


async def _fs_on_variant_change(variant_id, state: FormState) -> None:
    state.variant_id = variant_id
    await ui.run_javascript("")
    _fs_revalidate(state)
    if variant_id:
        await _fs_try_price_preload(state)


def build_vehicle_section(state: FormState) -> None:
    car_opts = {car["id"]: car["name"] for car in state.cars}
    outlet_opts = {outlet["id"]: outlet["name"] for outlet in state.outlets}
    exec_opts = {executive["id"]: executive["name"] for executive in state.executives}

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6 w-full"):
        with ui.row().classes(
            "w-full items-center gap-2 mb-4 pb-2 border-b border-gray-100"
        ):
            ui.label("🚙").classes("text-[20px] select-none")
            ui.label("Vehicle Details").classes("text-[15px] font-bold text-gray-900")

        with ui.grid(columns=FORM_COLUMNS).classes("w-full gap-5"):
            state.car_select = (
                ui.select(
                    options=car_opts,
                    label="Car *",
                    with_input=True,
                    on_change=lambda e: _fs_on_car_change(e.value, state),
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.variant_select = (
                ui.select(
                    options={},
                    with_input=True,
                    label="Variant *",
                    on_change=lambda e: _fs_on_variant_change(e.value, state),
                )
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            state.booking_date = (
                ui.input(
                    label="Booking Date"
                    if state.stage == "complaint"
                    else "Booking Date *",
                    value=str(date.today()),
                    on_change=lambda _: _fs_try_price_preload(state),
                )
                .classes("w-full")
                .props('type="date" outlined dense')
            )
            if state.stage != "complaint":
                state.booking_date.on_value_change(lambda _: _fs_revalidate(state))
            state.outlet_select = (
                ui.select(
                    options=outlet_opts,
                    label="Outlet",
                    on_change=lambda e: setattr(state, "outlet_id", e.value),
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.exec_select = (
                ui.select(
                    options=exec_opts,
                    label="Sales Executive",
                    on_change=lambda e: setattr(state, "executive_id", e.value),
                )
                .classes("w-full")
                .props("outlined dense")
            )
            state.cust_file_no = (
                ui.input(label="Customer File No *")
                .classes("w-full")
                .props("outlined dense")
                .on_value_change(lambda _: _fs_revalidate(state))
            )
            if state.stage in ["delivery", "complaint"]:
                if state.stage == "delivery":
                    state.vin_no = (
                        ui.input(label="VIN Number *")
                        .classes("w-full uppercase")
                        .props("outlined dense")
                        .on_value_change(lambda _: _fs_revalidate(state))
                    )
                    state.delivery_date = (
                        ui.input(label="Delivery Date *")
                        .classes("w-full")
                        .props('type="date" outlined dense')
                        .on_value_change(lambda _: _fs_revalidate(state))
                    )
                    state.engine_no = (
                        ui.input(label="Engine Number *")
                        .classes("w-full uppercase")
                        .props("outlined dense")
                        .on_value_change(lambda _: _fs_revalidate(state))
                    )
                    state.model_year = (
                        ui.input(label="Model Year *", placeholder="e.g. 2024")
                        .classes("w-full")
                        .props('outlined dense type="number"')
                        .on_value_change(lambda _: _fs_revalidate(state))
                    )
                    state.vehicle_regn_no = (
                        ui.input(label="Vehicle Regn Number")
                        .classes("w-full uppercase")
                        .props("outlined dense")
                    )
                    state.regn_date = (
                        ui.input(label="Date of Registration")
                        .classes("w-full")
                        .props('outlined dense type="date"')
                    )
                state.car_color = (
                    ui.input(label="Car Colour")
                    .classes("w-full")
                    .props("outlined dense")
                )
            state.model_year = (
                ui.input(label="Model Year *", placeholder="e.g. 2024")
                .classes("w-full")
                .props('outlined dense type="number"')
                .on_value_change(lambda _: _fs_revalidate(state))
            )

        if state.outlets:
            state.outlet_select.set_value(state.outlets[0]["id"])
            state.outlet_id = state.outlets[0]["id"]
        if state.executives:
            state.exec_select.set_value(state.executives[0]["id"])
            state.executive_id = state.executives[0]["id"]
