import re
from nicegui import ui
from utils.formatting import format_num_inr
from utils.parsing import parsed_val
from utils.formatting import accounting_input
from form.logic.calculations import _fs_update_live
from form.logic.validation import _fs_revalidate

def populate_from_booking(state, data: dict):
    if not data:
        return

    # ── Basic ────────────────────
    if state.cust_name:
        state.cust_name.set_value(data.get("customer_name", ""))

    if state.cust_mobile:
        state.cust_mobile.set_value(data.get("mobile_number", ""))

    if state.cust_email:
        state.cust_email.set_value(data.get("email", ""))

    if state.cust_address:
        state.cust_address.set_value(data.get("address", ""))

    if state.cust_city:
        state.cust_city.set_value(data.get("city", ""))

    if state.cust_pincode:
        state.cust_pincode.set_value(data.get("pin_code", ""))

    # ── Vehicle ──────────────────
    if state.cust_file_no:
        state.cust_file_no.set_value(data.get("customer_file_number", ""))

    if state.vin_no:
        state.vin_no.set_value(data.get("vin_number", ""))

    if state.engine_no:
        state.engine_no.set_value(data.get("engine_number", ""))

    if state.vehicle_regn_no:
        state.vehicle_regn_no.set_value(data.get("registration_number", ""))

    if state.regn_date:
        state.regn_date.set_value(data.get("registration_date", ""))

    # ── Variant / Car ────────────
    _map_car_and_variant(state, data)

    # ── Conditions ───────────────
    conditions = data.get("conditions", {})
    for key, cb in state.condition_cbs.items():
        cb.set_value(conditions.get(key, False))

    # ── Trigger recalculation ────
    _fs_update_live(state)
    _fs_revalidate(state)


def _map_car_and_variant(state, data):
    car_name = data.get("car_name")
    variant_name = data.get("variant_name")

    car_id = None
    for car in state.cars:
        if car["name"].strip().lower() == (car_name or "").strip().lower():
            car_id = car["id"]
            break

    if not car_id:
        return

    state.car_select.set_value(car_id)
    state.car_id = car_id

    variants = [v for v in state.variants if v["car_id"] == car_id]
    options = {v["id"]: v["variant_name"] for v in variants}

    state.variant_select.clear()
    state.variant_select.options = options
    state.variant_select.update()

    variant_id = None
    for v in variants:
        if (
            variant_name
            and variant_name.strip().lower() in v["variant_name"].strip().lower()
        ):
            variant_id = v["id"]
            break

    if not variant_id:
        return

    ui.timer(0.05, lambda: state.variant_select.set_value(variant_id), once=True)
    state.variant_id = variant_id


def populate_price_and_discount(state, booking_data: dict):
    from utils.utils import build_component_map_from_booking # Keep old util for now
    component_map = build_component_map_from_booking(booking_data)

    # Prices
    for name, inp in state.price_inputs.items():
        val = component_map.get(name)
        if val is None:
            norm_name = re.sub(r"[^a-z0-9]", "", name.lower())
            val = component_map.get(norm_name)
        if val is not None:
            inp.set_value(format_num_inr(val))

    # Discounts
    for name, inp in state.discount_inputs.items():
        val = component_map.get(name)
        if val is not None:
            inp.set_value(format_num_inr(val))


def populate_from_complaint(state, complaint: dict):
    if not complaint:
        return

    if state.cust_name: state.cust_name.set_value(complaint.get("customer_name", ""))
    if state.cust_mobile: state.cust_mobile.set_value(complaint.get("customer_mobile", ""))
    if state.cust_email: state.cust_email.set_value(complaint.get("email", ""))
    if state.cust_address: state.cust_address.set_value(complaint.get("customer_address", ""))
    if state.cust_city: state.cust_city.set_value(complaint.get("customer_city", ""))
    if state.cust_pincode: state.cust_pincode.set_value(complaint.get("customer_pin", ""))
    if state.cust_pan: state.cust_pan.set_value(complaint.get("pan_number", ""))
    if state.cust_aadhar: state.cust_aadhar.set_value(complaint.get("aadhar_number", ""))

    if state.vin_no: state.vin_no.set_value(complaint.get("vin_number", ""))
    if state.engine_no: state.engine_no.set_value(complaint.get("engine_number", ""))
    if state.vehicle_regn_no: state.vehicle_regn_no.set_value(complaint.get("registration_number", ""))
    if state.regn_date: state.regn_date.set_value(complaint.get("registration_date", ""))
    if state.car_color: state.car_color.set_value(complaint.get("car_color", ""))

    def get_item(items, id):
        for item in items:
            if item.get("id") == id: return item
        return None

    if state.complainant_dealership:
        item = get_item(state.complaint_dealerships, complaint.get("complainant_dealership_id"))
        if item: state.complainant_dealership.set_value(item.get("name"))

    if state.complainant_showroom:
        if complaint.get("complainant_showroom_name"):
            state.complainant_showroom.set_value(complaint["complainant_showroom_name"])

    if state.complainee_dealership:
        item = get_item(state.complaint_dealerships, complaint.get("complainee_dealership_id"))
        if item: state.complainee_dealership.set_value(item.get("name"))

    if state.complainee_showroom:
        if complaint.get("complainee_showroom_name"):
            state.complainee_showroom.set_value(complaint["complainee_showroom_name"])

    if state.complaint_date: state.complaint_date.set_value(complaint.get("date_of_complaint", ""))
    if state.complainant_remarks: state.complainant_remarks.set_value(complaint.get("remarks_complainant", ""))
    if state.complainee_aa_name: state.complainee_aa_name.set_value(complaint.get("remark_complainee_aa", ""))
    if state.complainant_aa_remarks: state.complainant_aa_remarks.set_value(complaint.get("remark_admin", ""))
    if state.complaint_status: state.complaint_status.set_value(complaint.get("status", ""))


from services.api import api_post, api_put
from form.logic.calculations import _fs_update_live

async def _fs_handle_submit(state) -> None:
    if not state.error_banner or not state.error_msg_label:
        return

    valid, msg = state.is_valid()
    if not valid:
        state.error_msg_label.set_text(msg)
        state.error_banner.set_visibility(True)
        return

    payload = build_payload(state)

    try:
        if state.stage == "delivery":
            if state.txn_id:
                await api_put(f"/transactions/{state.txn_id}", payload)
                ui.notify("Delivery Data saved", color="green", type="positive")
            else:
                await api_post("/transactions", payload)
                ui.notify(
                    "Delivery Created Successfully", color="green", type="positive"
                )
        else:
            await api_post("/transactions", payload)
            ui.notify("Booking Created Successfully", color="green", type="positive")

    except Exception as e:
        state.error_msg_label.set_text(str(e))
        state.error_banner.set_visibility(True)


async def _fs_prefill(state, txn: dict) -> None:
    """
    Populate all form fields from a fetched transaction dict.
    Called after the UI is fully built in edit mode.
    """
    # Customer
    cust = txn.get("customer", {})
    if state.cust_name:
        state.cust_name.set_value(cust.get("name", ""))
    if state.cust_mobile:
        state.cust_mobile.set_value(cust.get("mobile_number", ""))
    if state.cust_email:
        state.cust_email.set_value(cust.get("email", "") or "")

    # Booking date
    bd = txn.get("booking_date")
    if bd and state.booking_date:
        state.booking_date.set_value(bd)

    # Outlet / executive
    if txn.get("outlet_id") and state.outlet_select:
        state.outlet_select.set_value(txn["outlet_id"])
        state.outlet_id = txn["outlet_id"]
    if txn.get("sales_executive_id") and state.exec_select:
        state.exec_select.set_value(txn["sales_executive_id"])
        state.executive_id = txn["sales_executive_id"]

    # Car → triggers variant dropdown load
    car_id = txn.get("car_id")
    if car_id and state.car_select:
        state.car_select.set_value(car_id)
        state.car_id = car_id
        # Load variants for this car
        try:
            variants = await api_get(f"/cars/{car_id}/variants")
            state.variant_select.options = {
                v["id"]: v["full_variant_name"] for v in variants
            }
            state.variant_select.update()
        except Exception:
            pass

    # Variant
    variant_id = txn.get("variant_id")
    if variant_id and state.variant_select:
        state.variant_select.set_value(variant_id)
        state.variant_id = variant_id

    # Conditions
    conds = txn.get("conditions", {})
    for key, cb in state.condition_cbs.items():
        cb.set_value(bool(conds.get(key, False)))

    # Actual amounts → fill price
    amounts = txn.get("actual_amounts", {})
    for name, inp in state.price_inputs.items():
        if name in amounts:
            inp.set_value(amounts[name])
            if amounts[name] > 0 and name in state.price_match_toggles:
                state.price_match_toggles[name].set_value(True)

    # Accessories
    acc_details = txn.get("accessories_details", {})
    if state.acc_select:
        selected_ids = [acc["id"] for acc in txn.get("accessories", [])]
        state.acc_select.set_value(selected_ids)

    if state.acc_charged:
        state.acc_charged.set_value(acc_details.get("charged_amount", 0))

    if state.accessory_allowed:
        state.accessory_allowed.set_value(acc_details.get("allowed_amount", 0))

    # Delivery checks
    delv = txn.get("delivery_checks", {})
    for key, cb in state.delivery_cbs.items():
        cb.set_value(bool(delv.get(key, False)))

    # Audit
    audit = txn.get("audit_info", {})
    if state.audit_obs:
        state.audit_obs.set_value(audit.get("observations", ""))
    if state.audit_action:
        state.audit_action.set_value(audit.get("follow_up_action", ""))

    # Refresh live calc
    _fs_update_live(state)
    _fs_revalidate(state)


def build_payload(state) -> dict:
    def val(x):
        return x.value if x else None

    def intval(x):
        if not x: return 0
        v = x.value
        if not v: return 0
        try:
            v_str = str(v).replace(",", "").strip()
            if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
                return int(float(eval(v_str)))
            return int(float(v_str))
        except:
            return 0

    actual_amounts = {}
    for name, inp in state.price_inputs.items():
        row = state.price_rows.get(name)
        if row is not None and not row.visible:
            actual_amounts[name] = 0
        else:
            actual_amounts[name] = intval(inp)

    for name, row in state.discount_rows.items():
        if row.visible:
            if state.stage == "delivery" and state.is_direct_delivery:
                actual_amounts[name] = intval(state.discount_inputs.get(name))
            else:
                actual_amounts[name] = state.listed_prices.get(name, 0)
        else:
            actual_amounts[name] = 0

    conditions = {key: (cb.value or False) for key, cb in state.condition_cbs.items()}
    delivery_checks = {key: (cb.value or False) for key, cb in state.delivery_cbs.items()}

    selected_acc_ids = state.acc_select.value or []
    items_list = []
    for aid in selected_acc_ids:
        acc_info = state.accessory_map.get(int(aid))
        if acc_info:
            items_list.append({"id": aid, "name": acc_info["name"], "price": acc_info["listed_price"]})

    total_listed = sum(item["price"] for item in items_list)
    accessories_details = {
        "items": items_list,
        "charged_amount": intval(state.acc_charged),
        "allowed_amount": total_listed,
    }

    invoice_details = {
        "invoice_number": val(state.invoice_number),
        "invoice_date": val(state.invoice_date),
        "ex_showroom_price": intval(state.invoice_ex_showroom),
        "discount": intval(state.invoice_discount),
        "taxable_value": intval(state.invoice_taxable_value),
        "cgst": intval(state.invoice_cgst),
        "sgst": intval(state.invoice_sgst),
        "igst": intval(state.invoice_igst),
        "cess": intval(state.invoice_cess),
        "total": intval(state.invoice_total),
    }

    payment_details = {
        "cash": intval(state.payment_cash),
        "bank": intval(state.payment_bank),
        "finance": intval(state.payment_finance),
        "exchange": intval(state.payment_exchange),
    }

    payload = {
        "variant_id": state.variant_id,
        "booking_date": val(state.booking_date),
        "booking_amt": val(state.booking_amt),
        "booking_receipt_num": val(state.booking_receipt_num),
        "outlet_id": state.outlet_id,
        "sales_executive_id": state.executive_id,
        "customer": {
            "name": val(state.cust_name),
            "mobile_number": val(state.cust_mobile),
            "email": val(state.cust_email),
            "pan_number": val(state.cust_pan),
            "aadhar_number": val(state.cust_aadhar),
            "address": val(state.cust_address),
            "city": val(state.cust_city),
            "pin_code": val(state.cust_pincode),
        },
        "customer_file_number": val(state.cust_file_no),
        "vin_number": val(state.vin_no),
        "engine_number": val(state.engine_no),
        "registration_number": val(state.vehicle_regn_no),
        "registration_date": val(state.regn_date),
        "actual_amounts": actual_amounts,
        "conditions": conditions,
        "delivery_checks": delivery_checks,
        "accessories_details": accessories_details,
        "accessory_ids": selected_acc_ids,
        "invoice_details": invoice_details,
        "payment_details": payment_details,
        "finance_details": {},
        "exchange_details": {},
        "audit_info": {
            "observations": val(state.audit_obs),
            "actions": val(state.audit_action),
        },
    }
    if state.stage == "booking":
        payload["stage"] = "booking"
        payload["booking_checklist"] = {k: v.value for k, v in state.booking_cbs.items()}
    elif state.stage == "delivery":
        payload["stage"] = "delivery"
        payload["booking_id"] = state.booking_id
        payload["delivery_date"] = val(state.delivery_date)
        payload["is_direct_delivery"] = state.is_direct_delivery
        payload["overrides"] = state.overrides

    return payload


def build_complaint_payload(state) -> dict:
    from auth.auth import get_token
    def val(x): return x.value if x else None
    def intval(x):
        if not x: return 0
        v = x.value
        if not v: return 0
        try:
            v_str = str(v).replace(",", "").strip()
            if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
                return int(float(eval(v_str)))
            return int(float(v_str))
        except: return 0

    return {
        "stage": "complaint",
        "variant_id": state.variant_id,
        "employee_id": get_token() if get_token() else "unknown",
        "dealer_showroom_details": {
            "complainant_dealership": val(state.complainant_dealership),
            "complainant_showroom": val(state.complainant_showroom),
            "complainee_dealership": val(state.complainee_dealership),
            "complainee_showroom": val(state.complainee_showroom),
        },
        "customer_details": {
            "customer_name": val(state.cust_name),
            "contact_number": val(state.cust_mobile),
            "email": val(state.cust_email),
            "address": val(state.cust_address),
            "city": val(state.cust_city),
            "pin": val(state.cust_pincode),
            "pan": val(state.cust_pan),
            "aadhar": val(state.cust_relative),
        },
        "vehicle_details": {
            "vin_number": val(state.vin_no),
            "engine_number": val(state.engine_no),
            "registration_number": val(state.vehicle_regn_no),
            "registration_date": val(state.regn_date),
            "car_color": val(state.car_color),
        },
        "quotation_details": {
            "quotation_number": val(state.comp_quotation_no),
            "quotation_date": val(state.comp_quotation_date),
            "tcs_amount": intval(state.comp_tcs),
            "total_offered_price": intval(state.comp_total_offered),
            "net_offered_price": intval(state.comp_net_offered),
        },
        "booking_details": {
            "booking_file_number": val(state.comp_booking_file_no),
            "receipt_number": val(state.comp_receipt_no),
            "booking_amount": intval(state.comp_booking_amt),
            "mode_of_payment": val(state.comp_mode_of_payment),
            "instrument_date": val(state.comp_instrument_date),
            "instrument_number": val(state.comp_instrument_no),
            "bank_name": val(state.comp_bank_name),
        },
        "remarks_page": {
            "complaint_raised_date": val(state.complaint_date),
            "aa_name": val(state.complainee_aa_name),
            "remarks_by_complainant": val(state.complainant_remarks),
            "remarks_by_aa": val(state.complainant_aa_remarks),
        },
        "price_info": {
            "ex_showroom_price": intval(state.price_inputs.get("Ex Showroom Price") or state.price_inputs.get("Ex-Showroom Price")),
            "insurance": intval(state.price_inputs.get("Insurance")),
            "registration_road_tax": intval(state.price_inputs.get("Registration / Road Tax")),
            "discount": state.live_discount,
            "accessories_charged": intval(state.acc_charged),
        },
    }
