from nicegui import ui

class FormState:
    """
    All mutable state for a single /form session.
    Instantiated inside form_page() — never shared across sessions.
    """

    def __init__(self):
        # --- Delivery Related ---
        self.delivery_date: ui.input | None = None
        self.is_direct_delivery: bool = False
        self.delivery_mode = None
        self.vin_no: ui.input | None = None
        self.engine_no: ui.input | None = None
        self.vehicle_regn_no: ui.input | None = None
        self.regn_date: ui.input | None = None
        self.delivery_cbs: dict[str, ui.checkbox] = {}
        
        # Invoice Section
        self.invoice_number: ui.input | None = None
        self.invoice_date: ui.input | None = None
        self.invoice_ex_showroom: ui.input | None = None
        self.invoice_discount: ui.input | None = None
        self.invoice_taxable_value: ui.input | None = None
        self.invoice_cgst: ui.input | None = None
        self.invoice_sgst: ui.input | None = None
        self.invoice_igst: ui.input | None = None
        self.invoice_cess: ui.input | None = None
        self.invoice_total: ui.input | None = None

        # Payment Section
        self.payment_cash: ui.input | None = None
        self.payment_bank: ui.input | None = None
        self.payment_finance: ui.input | None = None
        self.payment_exchange: ui.input | None = None

        # Audit
        self.audit_obs: ui.textarea | None = None
        self.audit_action: ui.textarea | None = None
        
        self.overrides = {
            "customer": False,
            "vehicle": False,
            "price": False,
        }

        # --- Booking Related ---
        self.booking_id: int | None = None
        self.booking_date: ui.input | None = None
        self.booking_amt: ui.input | None = None
        self.booking_receipt_num: ui.input | None = None
        self.booking_data: dict = {}
        self.booking_cbs: dict[str, ui.checkbox] = {}
        self.booking_select = None

        # --- Complaint Related ---
        self.complaint_dealerships: list = []
        self.complainant_outlets: list = []
        self.complainee_outlets: list = []

        self.complainant_dealership: ui.select | None = None
        self.complainant_showroom: ui.select | None = None
        self.complainee_dealership: ui.select | None = None
        self.complainee_showroom: ui.select | None = None
        self.complaint_status: ui.select | None = None

        self.comp_quotation_no: ui.input | None = None
        self.comp_quotation_date: ui.input | None = None
        self.comp_total_offered: ui.input | None = None
        self.comp_net_offered: ui.input | None = None
        self.comp_tcs: ui.input | None = None

        self.comp_booking_file_no: ui.input | None = None
        self.comp_receipt_no: ui.input | None = None
        self.comp_booking_amt: ui.input | None = None
        self.comp_mode_of_payment: ui.input | None = None
        self.comp_instrument_date: ui.input | None = None
        self.comp_instrument_no: ui.input | None = None
        self.comp_bank_name: ui.input | None = None

        self.complainant_remarks: ui.textarea | None = None
        self.complainee_aa_name: ui.input | None = None
        self.complainant_aa_remarks: ui.textarea | None = None
        self.complaint_date: ui.input | None = None

        # --- Common / Others ---
        self.txn_id: int | None = None
        self.edit_mode: bool = False
        self.stage: str = "booking"  # booking | delivery
        self.mode: str = "booking"  # booking | book-and-delivery
        
        # Reference data
        self.cars: list = []
        self.variants: list = []
        self.components: list = []
        self.outlets: list = []
        self.executives: list = []

        # Selected foreign keys
        self.car_id: int | None = None
        self.variant_id: int | None = None
        self.outlet_id: int | None = None
        self.executive_id: int | None = None

        # UI element refs — vehicle
        self.car_select: ui.select | None = None
        self.variant_select: ui.select | None = None
        self.outlet_select: ui.select | None = None
        self.exec_select: ui.select | None = None
        self.cust_file_no: ui.input | None = None
        self.model_year: ui.input | None = None
        self.car_color: ui.input | None = None

        # UI element refs — customer
        self.cust_name: ui.input | None = None
        self.cust_mobile: ui.input | None = None
        self.cust_email: ui.input | None = None
        self.cust_relative: ui.input | None = None
        self.cust_address: ui.input | None = None
        self.cust_city: ui.input | None = None
        self.cust_pincode: ui.input | None = None
        self.cust_pan: ui.input | None = None
        self.cust_aadhar: ui.input | None = None
        self.cust_other_id: ui.input | None = None

        # UI element refs — accessories / audit
        self.acc_select: ui.select | None = None
        self.acc_charged: ui.number | None = None
        self.acc_total_label: ui.label | None = None
        self.accessory_allowed: ui.number | None = None
        self.accessory_map: dict = {}

        # UI element refs — actions
        self.submit_btn: ui.button | None = None
        self.error_banner: ui.html | None = None

        # Component toggles
        self.price_match_toggles: dict[str, ui.switch] = {}
        self.price_diff_labels: dict[str, ui.label] = {}
        self.discount_match_toggles: dict[str, ui.switch] = {}
        self.lbl_total_diff_price: ui.label | None = None
        self.lbl_excess_discount: ui.label | None = None

        self.listed_prices: dict[str, int] = {}
        self.price_listed_labels: dict[str, ui.label] = {}
        self.discount_listed_labels: dict[str, ui.label] = {}

        # Component inputs
        self.price_inputs: dict[str, ui.input] = {}
        self.price_rows: dict[str, ui.row] = {}
        self.discount_inputs: dict[str, ui.input] = {}
        self.discount_rows: dict[str, ui.row] = {}

        # Checkboxes
        self.condition_cbs: dict[str, ui.checkbox] = {}

        # Live calc labels
        self.lbl_allowed: ui.label | None = None
        self.lbl_discount: ui.label | None = None
        self.lbl_excess: ui.label | None = None
        self.lbl_total_listed_price: ui.label | None = None
        self.lbl_total_offered_price: ui.label | None = None
        self.stage_toggle = None

    @property
    def all_component_inputs(self) -> dict[str, ui.input]:
        return {**self.price_inputs, **self.discount_inputs}

    @property
    def live_discount(self) -> int:
        """Sum of allowed discounts for all currently visible discount rows."""
        total = 0
        if not hasattr(self, "listed_prices") or not self.listed_prices:
            return 0
        for name, row in self.discount_rows.items():
            if row.visible:
                val = self.listed_prices.get(name)
                if val is not None:
                    total += int(val)
        return total

    def is_valid(self) -> tuple[bool, str]:
        # This will be implemented in validation.py but kept as a method proxy or moved entirely
        from form.logic.validation import is_valid_logic
        return is_valid_logic(self)

    def reset(self):
        """Reset the entire form state to defaults."""
        ui.navigate.to("/form") # Simple way to reset is to reload page or re-init
