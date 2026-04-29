from nicegui import ui
from form.state import FormState
from utils.formatting import format_num_inr, accounting_input
from form.logic.calculations import _fs_update_live

def _build_delivery_prices_section(state: FormState) -> None:
    price_comps = sorted(
        [c for c in state.components if c.get("type") == "price"],
        key=lambda x: x.get("order", 99),
    )
    booking_map = {
        k.replace("_actual", "").strip(): v
        for k, v in (state.booking_data or {}).items()
        if k.endswith("_actual")
    }
    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        ui.label("💰 Price Comparison (Booking vs Delivery)").classes("text-[15px] font-bold mb-2")
        if price_comps:
            with ui.column().classes("w-full gap-2"):
                for comp in price_comps:
                    name = comp["name"]
                    with ui.row().classes("w-full items-center h-10 gap-2"):
                        ui.label(name).classes("w-52 text-sm")
                        listed_label = ui.label("₹—").classes("w-28 text-gray-500 text-sm")
                        state.price_listed_labels[name] = listed_label
                        booking_val = booking_map.get(name)
                        booking_input = (
                            ui.input(value=format_num_inr(booking_val) if booking_val else "")
                            .props("readonly dense")
                            .classes("w-36")
                        )
                        toggle = ui.switch("Same as Booking").props("dense color=green")
                        inp = accounting_input("", placeholder="Delivery Price", container_classes="w-36").props("dense")
                        state.price_inputs[name] = inp
                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = booking_map.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)
                            _fs_update_live(state)
                        toggle.on("update:model-value", on_toggle)
                        inp.on_value_change(lambda _: _fs_update_live(state))
        else:
            ui.label("No price components found").classes("text-xs text-gray-400")

def _build_direct_delivery_prices_section(state: FormState) -> None:
    price_comps = sorted([pc for pc in state.components if pc.get("type") == "price"], key=lambda x: x.get("order", 99))
    discount_comps = sorted([dc for dc in state.components if dc.get("type") == "discount"], key=lambda x: x.get("order", 99))

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes("w-full items-center gap-2 pb-2 border-b border-gray-100"):
            ui.label("💰").classes("text-lg select-none")
            ui.label("Price & Discounts (Direct Delivery)").classes("text-[15px] font-bold text-gray-900")

        ui.label("Price Charged as per Books of Accounts").classes("text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mt-4")
        ui.separator().classes("mt-0")
        if price_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in price_comps:
                    name = comp["name"]
                    with ui.row().classes("w-full items-center h-10") as row_element:
                        state.price_rows[name] = row_element
                        ui.label(name).classes("w-60 text-sm")
                        listed_label = ui.label("₹—").classes("w-32 text-gray-500 text-sm")
                        state.price_listed_labels[name] = listed_label
                        toggle = ui.switch("Match Listed Price").props('dense icon="check" color="green"')
                        inp = accounting_input("", placeholder="Enter Charged Price", container_classes="w-60").props("dense")
                        state.price_inputs[name] = inp
                        state.price_match_toggles[name] = toggle
                        diff_label = ui.label("₹0").classes("w-32 text-gray-500 text-sm ml-2")
                        state.price_diff_labels[name] = diff_label
                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)
                                inp.set_value(None)
                            _fs_update_live(state)
                        toggle.on("update:model-value", on_toggle)
                        inp.on_value_change(lambda _: _fs_update_live(state))

        ui.label("Discounts Allowed as per Books of Accounts").classes("text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mt-6")
        ui.separator().classes("mt-0")
        if discount_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in discount_comps:
                    name = comp["name"]
                    is_default = name in ["Cash Discount All Customers", "Additional Discount From Dealer", "Maximum benefit due to price increase"]
                    with ui.row().classes("w-full items-center h-10") as row_element:
                        state.discount_rows[name] = row_element
                        row_element.set_visibility(is_default)
                        ui.label(name).classes("w-60 text-sm")
                        listed_label = ui.label("₹—").classes("w-32 text-gray-500 text-sm")
                        state.discount_listed_labels[name] = listed_label
                        toggle = ui.switch("Match Listed Discount").props('dense icon="check" color="green"')
                        inp = accounting_input("", placeholder="Enter Discount", container_classes="w-60").props("dense")
                        state.discount_inputs[name] = inp
                        state.discount_match_toggles[name] = toggle
                        def on_toggle_disc(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)
                                inp.set_value(None)
                            _fs_update_live(state)
                        toggle.on("update:model-value", on_toggle_disc)
                        inp.on_value_change(lambda _: _fs_update_live(state))

        with ui.grid(columns=1).classes("w-full align-center mt-4 pt-4 border-t"):
            with ui.row().classes("w-full items-center h-10"):
                ui.label("Totals").classes("text-lg font-bold tracking-[0.9px] uppercase")
                state.lbl_total_listed_price = ui.label("₹—").classes("w-32 text-lg")
                state.lbl_total_offered_price = ui.label("₹—").classes("w-32 text-lg")
                state.lbl_total_diff_price = ui.label("₹—").classes("w-32 text-lg ml-2")
                state.lbl_excess_discount = ui.label("₹0").classes("ml-auto text-lg font-bold")

def _build_booking_prices_section(state: FormState) -> None:
    price_comps = sorted([pc for pc in state.components if pc.get("type") == "price"], key=lambda x: x.get("order", 99))
    discount_comps = sorted([dc for dc in state.components if dc.get("type") == "discount"], key=lambda x: x.get("order", 99))

    with ui.card().classes("shadow-sm rounded-xl p-6 mb-6"):
        with ui.row().classes("w-full items-center gap-2 pb-2 border-b border-gray-100"):
            ui.label("💰").classes("text-lg select-none")
            ui.label("Price & Discounts").classes("text-[15px] font-bold text-gray-900")

        ui.label("Price Charged as per Books of Accounts").classes("text-sm font-bold tracking-[0.9px] uppercase text-gray-400 ")
        ui.separator().classes("mt-0")
        if price_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in price_comps:
                    name = comp["name"]
                    with ui.row().classes("w-full items-center h-10") as row_element:
                        state.price_rows[name] = row_element
                        ui.label(name).classes("w-60 text-sm")
                        listed_label = ui.label("₹—").classes("w-32 text-gray-500 text-sm")
                        state.price_listed_labels[name] = listed_label
                        toggle = ui.switch("Match Listed Price").props('dense icon="check" color="green"')
                        inp = accounting_input("", placeholder="Enter Charged Price", container_classes="w-60").props("dense")
                        state.price_inputs[name] = inp
                        state.price_match_toggles[name] = toggle
                        diff_label = ui.label("₹0").classes("w-32 text-gray-500 text-sm ml-2")
                        state.price_diff_labels[name] = diff_label
                        def on_toggle(_, name=name, inp=inp, toggle=toggle):
                            if toggle.value:
                                val = state.listed_prices.get(name, 0)
                                inp.set_value(format_num_inr(val))
                                inp.set_enabled(False)
                            else:
                                inp.set_enabled(True)
                                inp.set_value(None)
                            _fs_update_live(state)
                        toggle.on("update:model-value", on_toggle)
                        inp.on_value_change(lambda _: _fs_update_live(state))
        
        with ui.grid(columns=1).classes("w-full align-center"):
            with ui.row().classes("w-full items-center h-10"):
                ui.label("Total On-Road Price").classes("text-lg font-bold tracking-[0.9px] uppercase mb-1 mt-1 pt-1")
                state.lbl_total_listed_price = ui.label("₹—").classes("w-32 text-lg")
                state.lbl_total_offered_price = ui.label("₹—").classes("w-32 text-lg")
                state.lbl_total_diff_price = ui.label("₹—").classes("w-32 text-lg ml-2")

        ui.label("Discounts Offered as per Books of Accounts").classes("text-sm font-bold tracking-[0.9px] uppercase text-gray-400 mb-1 mt-1 pt-1")
        ui.separator().classes("mt-0 my-2")
        with ui.row().classes("w-full items-center pt-2 border-t border-gray-100"):
            ui.label("Total Discount as per booking file").classes("text-sm font-bold tracking-[0.9px]")
            state.total_discount_input = accounting_input("", placeholder="₹0", container_classes="w-60")
        
        if discount_comps:
            with ui.grid(columns=1).classes("w-full align-center"):
                for comp in discount_comps:
                    name = comp["name"]
                    with ui.row().classes("w-full align-center h-10") as row_element:
                        ui.label(name).classes("w-60 text-sm")
                        listed_label = ui.label("₹—").classes("w-32 text-gray-500 text-sm")
                        state.discount_listed_labels[name] = listed_label
                        state.discount_rows[name] = row_element
                
                with ui.row().classes("w-full items-center h-12 mt-2 pt-2 border-t border-gray-100"):
                    ui.label("Adjustments").classes("w-60 text-lg font-bold tracking-[0.9px] uppercase")
                    with ui.button_group().classes("ml-auto"):
                        ui.button().props("dense color=primary icon=add")
                        ui.button().props("dense color=primary icon=remove")
                    state.addjustment_input = accounting_input("", placeholder="₹0", container_classes="w-60")
                    ui.label("Excess Discount").classes("w-60 text-lg font-bold tracking-[0.9px] uppercase")
                    ui.label("").classes("w-32")
                    state.lbl_excess_discount = ui.label("₹0").classes("text-lg font-bold ml-2")
        else:
            ui.label("No discount components — check /components endpoint.").classes("text-xs text-gray-400")

def build_prices_section(state: FormState) -> None:
    if state.stage == "delivery":
        if state.is_direct_delivery:
            _build_direct_delivery_prices_section(state)
        else:
            _build_delivery_prices_section(state)
    else:
        _build_booking_prices_section(state)
