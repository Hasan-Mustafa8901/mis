import re
from nicegui import ui
from utils.formatting import format_num_inr
from utils.parsing import parsed_val
from form.state import FormState
from services.api import api_get

async def _fs_try_price_preload(state: FormState) -> None:
    """Call GET /price-list/preview when both variant + date are known."""
    booking_date = None
    if state.booking_date and state.booking_date.value:
        booking_date = state.booking_date.value
    elif state.delivery_date and state.delivery_date.value:
        booking_date = state.delivery_date.value

    if not state.variant_id or not booking_date:
        return

    try:
        booking_date = state.booking_date.value
        preview = await api_get(
            f"/price-list/preview?variant_id={state.variant_id}&booking_date={booking_date}"
        )

        state.listed_prices = preview or {}
        filled = 0

        for name, value in state.listed_prices.items():
            if value is None:
                continue

            formatted = f"₹{int(value):,}"

            if name in state.price_listed_labels:
                state.price_listed_labels[name].set_text(formatted)

            if name in state.discount_listed_labels:
                state.discount_listed_labels[name].set_text(formatted)

            if name in state.price_match_toggles:
                toggle = state.price_match_toggles[name]
                inp = state.price_inputs.get(name)

                if toggle.value and inp:
                    inp.set_value(int(value))
                    inp.props("readonly")
                    filled += 1

            if name in state.discount_match_toggles:
                toggle = state.discount_match_toggles[name]
                inp = state.discount_inputs.get(name)

                if toggle.value and inp:
                    inp.set_value(int(value))
                    inp.props("readonly")
                    filled += 1

        if state.invoice_ex_showroom:
            val = state.listed_prices.get("Ex Showroom Price", 0)
            state.invoice_ex_showroom.set_value(val)

        _fs_update_live(state)

        if filled:
            ui.notify(
                f"✓ {filled} field{'s' if filled > 1 else ''} synced with listed price.",
                type="info",
                position="top-right",
                timeout=2500,
            )

    except Exception:
        pass


def _fs_update_live(state: FormState) -> None:
    if not state.lbl_discount:
        return

    # 1. Sync Ex-showroom
    found_ex = None
    if "Ex Showroom Price" in state.price_inputs:
        found_ex = state.price_inputs["Ex Showroom Price"]
    elif "Ex-Showroom Price" in state.price_inputs:
        found_ex = state.price_inputs["Ex-Showroom Price"]

    if state.invoice_ex_showroom and found_ex:
        price_val = int(parsed_val(found_ex))
        if parsed_val(state.invoice_ex_showroom) != price_val:
            state.invoice_ex_showroom.set_value(format_num_inr(price_val))

    # 2. Sync Total Discount
    total_comp_discount = 0
    if state.stage == "delivery" and state.is_direct_delivery:
        for name, inp in state.discount_inputs.items():
            row = state.discount_rows.get(name)
            if row and row.visible:
                total_comp_discount += int(parsed_val(inp))
    else:
        total_comp_discount = state.live_discount

    if (
        state.invoice_discount
        and parsed_val(state.invoice_discount) != total_comp_discount
    ):
        state.invoice_discount.set_value(format_num_inr(total_comp_discount))

    allowed_discount = state.live_discount
    discount_given = total_comp_discount

    # 4. Update Labels
    if hasattr(state, "lbl_allowed") and state.lbl_allowed:
        state.lbl_allowed.set_text(f"₹{allowed_discount:,.0f}")

    if state.lbl_discount:
        state.lbl_discount.set_text(f"₹{discount_given:,.0f}")

    excess = discount_given - allowed_discount
    if state.lbl_excess:
        state.lbl_excess.set_text(f"₹{excess:,.0f}")
        if excess <= 0:
            state.lbl_excess.style("color:#6EE7B7")
        else:
            state.lbl_excess.style("color:#F87171")

    # 5. Update Total Price Labels
    total_listed = 0
    total_offered = 0

    for name, inp in state.price_inputs.items():
        row = state.price_rows.get(name)
        if row is not None and not row.visible:
            diff_label = state.price_diff_labels.get(name)
            if diff_label:
                diff_label.set_text("")
            continue

        toggle = state.price_match_toggles.get(name)
        is_toggled = toggle.value if toggle else False
        is_entered = bool(inp.value and str(inp.value).strip())

        if is_toggled or is_entered:
            listed_price = int(state.listed_prices.get(name) or 0)
            total_listed += listed_price
        else:
            listed_price = 0

        offered_price = 0
        try:
            offered_price = int(float(str(parsed_val(inp)).replace(",", "") or 0))
        except:
            pass
        total_offered += offered_price

        diff_label = state.price_diff_labels.get(name)
        if diff_label:
            if not is_toggled and not is_entered:
                diff_label.set_text("")
                diff_label.style("color: #9CA3AF")
            else:
                diff = listed_price - offered_price
                if diff > 0:
                    diff_label.set_text(f"₹{diff:,.2f}")
                    diff_label.style("color: #D41717")
                elif diff < 0:
                    diff_label.set_text("₹ 0")
                    diff_label.style("color: #1CC722")
                else:
                    diff_label.set_text("₹0")
                    diff_label.style("color: #9CA3AF")

    total_diff = total_listed - total_offered

    if state.lbl_total_listed_price:
        state.lbl_total_listed_price.set_text(f"₹{total_listed:,.2f}")
    if state.lbl_total_offered_price:
        state.lbl_total_offered_price.set_text(f"₹{total_offered:,.2f}")
    if state.lbl_total_diff_price:
        if total_diff > 0:
            state.lbl_total_diff_price.set_text(f"₹{abs(total_diff):,.2f}")
            state.lbl_total_diff_price.style("color: #D41717")
        elif total_diff < 0:
            state.lbl_total_diff_price.set_text(f"-₹{total_diff:,.2f}")
            state.lbl_total_diff_price.style("color: #1CC722")
        else:
            state.lbl_total_diff_price.set_text("₹0")
            state.lbl_total_diff_price.style("color: #9CA3AF")

    # ── Excess Discount Calculation ─────────────────
    if hasattr(state, "lbl_excess_discount") and state.lbl_excess_discount:
        current_allowed = 0
        if hasattr(state, "listed_prices") and state.listed_prices:
            for name, row in state.discount_rows.items():
                if row.visible:
                    val = state.listed_prices.get(name)
                    if val is not None:
                        current_allowed += int(val)

        excess_val = total_diff - current_allowed
        if excess_val < 0:
            excess_val = 0

        state.lbl_excess_discount.set_text(f"₹{excess_val:,.2f}")
        if excess_val > 0:
            state.lbl_excess_discount.style("color: #D41717")
        else:
            state.lbl_excess_discount.style("color: #9CA3AF")


def _fs_update_visibility(state: FormState) -> None:
    def is_checked(key: str) -> bool:
        cb = state.condition_cbs.get(key)
        return bool(cb and cb.value)

    def norm(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

    discount_visibility_rules = {
        norm("Extra Kitty On TR cases"): is_checked("tr_case"),
        norm("Additional For POI /Corporate Customers"): is_checked("corporate")
        or is_checked("govt_employee"),
        norm("Additional For Exchange Customers"): is_checked("exchange"),
        norm("Additional For Scrappage Customers"): is_checked("scrap"),
        norm("Additional For Upward Sales Customers"): is_checked("upgrade"),
    }

    price_visibility_rules = {
        norm("Accessories"): is_checked("acc_kit"),
        norm("FasTag"): is_checked("fastag"),
        norm("Extended Warranty"): is_checked("ext_warr"),
        norm("Shield Of Trust"): is_checked("shield"),
        norm("Insurance (With Depreciation Cover)"): not is_checked("self_insurance"),
        norm("Insurance"): not is_checked("self_insurance"),
    }

    for name, row in state.discount_rows.items():
        n_name = norm(name)
        if n_name in discount_visibility_rules:
            row.set_visibility(discount_visibility_rules[n_name])

    for name, row in state.price_rows.items():
        n_name = norm(name)
        if n_name in price_visibility_rules:
            row.set_visibility(price_visibility_rules[n_name])

    _fs_update_live(state)
