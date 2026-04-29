import re

def is_valid_logic(state) -> tuple[bool, str]:
    def _val(f):
        return (f.value or "").strip() if f else ""

    def _val_upper(f):
        return (f.value or "").strip().upper() if f else ""

    if not state.variant_id:
        return False, "Please select a Car and Variant."

    if not _val(state.cust_name):
        return False, "Customer name is required."

    mob = _val(state.cust_mobile)
    if not re.fullmatch(r"[6-9]\d{9}", mob):
        return False, "Mobile must be 10 digits starting with 6–9."

    if not _val(state.cust_address):
        return False, "Address is required."

    if not _val(state.cust_city):
        return False, "City is required."

    pan_val = _val_upper(state.cust_pan)
    if pan_val and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_val):
        return False, "Valid PAN required."

    # TR Case condition
    if state.condition_cbs.get("tr_case") and state.condition_cbs["tr_case"].value:
        if not _val(state.cust_other_id):
            return False, "Other ID Proof required for TR Case."

    year_val = _val(state.model_year)
    if not year_val or not year_val.isdigit():
        return False, "Valid Model Year is required."

    if state.stage == "delivery":
        if not _val(state.vin_no):
            return False, "VIN Number is required."
        if not _val(state.engine_no):
            return False, "Engine Number is required."

    return True, ""

def _fs_revalidate(state) -> None:
    from form.logic.calculations import _fs_update_visibility
    _fs_update_visibility(state)
    ok, msg = state.is_valid()

    if state.submit_btn:
        state.submit_btn.set_enabled(ok)

    if state.error_banner and state.error_msg_label:
        if not ok:
            state.error_msg_label.set_text(msg)
            state.error_banner.set_visibility(True)
        else:
            state.error_banner.set_visibility(False)

def _fs_validate_mobile(state) -> None:
    if state.cust_mobile is None:
        return
    mob = (state.cust_mobile.value or "").strip()
    if mob and not re.fullmatch(r"[6-9]\d{9}", mob):
        state.cust_mobile.props(
            "error error-message='Must be 10 digits starting 6 to 9'"
        )
    else:
        state.cust_mobile.props(remove="error")
    _fs_revalidate(state)

def _fs_validate_pincode(state) -> None:
    if state.cust_pincode is None:
        return
    val = (state.cust_pincode.value or "").strip()
    if not re.fullmatch(r"\d{6}", val):
        state.cust_pincode.props("error error-message='Must be 6 digits'")
    else:
        state.cust_pincode.props(remove="error")
    _fs_revalidate(state)

def _fs_validate_pan(state) -> None:
    if state.cust_pan is None:
        return
    val = (state.cust_pan.value or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", val):
        state.cust_pan.props("error error-message='Invalid PAN format'")
    else:
        state.cust_pan.props(remove="error")
    _fs_revalidate(state)

def _fs_validate_aadhar(state) -> None:
    if state.cust_aadhar is None:
        return
    val = (state.cust_aadhar.value or "").strip()
    if not re.fullmatch(r"\d{12}", val):
        state.cust_aadhar.props("error error-message='Must be 12 digits'")
    else:
        state.cust_aadhar.props(remove="error")
    _fs_revalidate(state)
