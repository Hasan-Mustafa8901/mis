from nicegui import ui

def clear_label(column_name: str):
    """
    Cleans up column names for display.
    """
    return (
        column_name.replace("_", " ")
        .replace("actual", "(Actual)")
        .replace("allowed", "(Allowed)")
        .replace("diff", "(Diff)")
        .title()
    )

def build_ordered_columns(row: dict, stage: str = "combined"):
    """
    Build ordered columns for the MIS table.
    """
    keys = list(row.keys())

    def pick(prefix):
        return [k for k in keys if k.startswith(prefix)]

    ordered = []

    # 1. Core info
    ordered += [
        "id",
        "customer_name",
        "mobile_number",
        "variant_name",
        "booking_date",
    ]
    if stage == "delivery":
        ordered.append("delivery_date")

    # 2. Price components
    ordered += pick("Ex ") + pick("Insurance") + pick("Registration")

    # 3. Discount components
    ordered += [k for k in keys if "_actual" in k and "Discount" in k]

    # 5. Conditions
    ordered += pick("cond_")

    # 6. Accessories / finance / exchange
    ordered += pick("accessories_")
    ordered += pick("finance_")
    ordered += pick("exchange_")

    # 7. Checklist
    ordered += pick("checklist_")

    # 8. Audit
    ordered += pick("audit_")

    # 9. Totals
    ordered += [
        "net_receivable",
        "total_received",
        "balance_amount",
        "total_actual_discount",
        "total_allowed_discount",
        "total_excess_discount",
        "status",
    ]

    # remove duplicates + preserve order
    seen = set()
    ordered = [x for x in ordered if not (x in seen or seen.add(x))]

    return ordered

def render_table(transactions, stage: str = "delivery"):
    """
    Renders the MIS transaction table using AG Grid (ui.aggrid).
    """
    if not transactions:
        with ui.card().classes("w-full").style("padding:48px;text-align:center"):
            ui.label("📭").style("font-size:36px")
            ui.label("No transactions yet").style(
                "font-size:14px;font-weight:500;color:#6B7280;margin-top:8px"
            )
            ui.label("Click 'New Entry' to add the first record.").style(
                "font-size:12px;color:#9CA3AF;margin-top:4px"
            )
        return

    ordered_keys = build_ordered_columns(transactions[0], stage=stage)

    NUMERIC_KEYS = {
        k
        for k in ordered_keys
        if any(
            tok in k
            for tok in (
                "_actual",
                "total_",
                "price",
                "amount",
                "discount",
                "excess",
                "payment",
                "invoice_",
                "net_",
            )
        )
    }
    pin_cols = {
        "id",
        "customer_name",
        "mobile_number",
        "variant_name",
        "booking_date",
        "delivery_date",
    }

    CUSTOM_WIDTHS = {
        "id": 10,
        "customer_name": 100,
        "mobile_number": 100,
        "variant_name": 100,
        "booking_date": 100,
        "delivery_date": 100,
    }

    col_defs = []
    for key in ordered_keys:
        is_num = key in NUMERIC_KEYS
        is_status = key == "status"

        col: dict = {
            "field": key,
            "headerName": clear_label(key),
            "filter": "agNumberColumnFilter" if is_num else "agTextColumnFilter",
        }

        if key in CUSTOM_WIDTHS:
            col["width"] = CUSTOM_WIDTHS[key]

        if is_num:
            col[":valueFormatter"] = (
                "params.value != null"
                " ? '₹' + Number(params.value).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})"
                " : '—'"
            )
            col["type"] = "numericColumn"

        if is_status:
            col[":cellStyle"] = (
                "params.value === 'Excess'"
                " ? {background:'#FEE2E2', color:'#991B1B', fontWeight:'600', borderRadius:'4px'}"
                " : {background:'#D1FAE5', color:'#065F46', fontWeight:'600', borderRadius:'4px'}"
            )

        if key in pin_cols:
            col["pinned"] = "left"

        col_defs.append(col)

    grid = (
        ui.aggrid(
            {
                "columnDefs": col_defs,
                "rowData": transactions,
                "defaultColDef": {
                    "flex": 0,
                    "minWidth": 70,
                    "sortable": True,
                    "filter": True,
                    "floatingFilter": True,
                    "resizable": True,
                },
                "domLayout": "normal",
                "suppressColumnVirtualization": False,
                "animateRows": True,
                "pagination": True,
                "paginationPageSize": 25,
                "rowSelection": "single",
                "rowHeight": 30,
                "suppressCellFocus": True,
            },
            theme="balham",
            auto_size_columns=False,
        )
        .classes("w-full h-100")
        .style("font-family:Inter,sans-serif;font-size:13px;")
    )

    async def on_cell_clicked(e):
        row = e.args.get("data", {})
        txn_id = row.get("id")
        if txn_id:
            ui.navigate.to(f"/form?transaction_id={txn_id}&stage={stage}")

    grid.on("cellClicked", on_cell_clicked)

def render_complaints_table(complaints):
    """
    Renders the Complaints table using AG Grid.
    """
    if not complaints:
        with ui.card().classes("w-full").style("padding:48px;text-align:center"):
            ui.label("📭").style("font-size:36px")
            ui.label("No complaints yet").style(
                "font-size:14px;font-weight:500;color:#6B7280;margin-top:8px"
            )
            return

    # Define columns for complaints table
    col_defs = [
        {
            "field": "complaint_code",
            "headerName": "Complaint Code",
            "pinned": "left",
            "width": 120,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "date_of_complaint",
            "headerName": "Complaint Date",
            "width": 120,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "car_model",
            "headerName": "Car Model",
            "width": 130,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "car_variant",
            "headerName": "Variant",
            "width": 160,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "complainant_dealer_name",
            "headerName": "Complainant Dealer",
            "width": 150,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "complainant_showroom_name",
            "headerName": "Complainant Showroom",
            "width": 150,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "complainee_dealer_name",
            "headerName": "Complainee Dealer",
            "width": 150,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "complainee_showroom_name",
            "headerName": "Complainee Showroom",
            "width": 150,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "customer_name",
            "headerName": "Customer",
            "width": 140,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "customer_mobile",
            "headerName": "Customer Number",
            "width": 130,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "customer_address",
            "headerName": "Address",
            "width": 150,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "customer_city",
            "headerName": "City",
            "width": 100,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "customer_pin",
            "headerName": "PIN",
            "width": 80,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "car_color",
            "headerName": "Car Colour",
            "width": 120,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "quotation_number",
            "headerName": "Quotation No",
            "width": 130,
        },
        {
            "field": "total_offered_price",
            "headerName": "Total Offered",
            "width": 120,
            "valueFormatter": "Math.floor(value).toLocaleString()",
        },
        {
            "field": "net_offered_price",
            "headerName": "Net Offered",
            "width": 120,
            "valueFormatter": "Math.floor(value).toLocaleString()",
        },
        {
            "field": "booking_file_number",
            "headerName": "Booking File No",
            "width": 140,
        },
        {
            "field": "booking_amount",
            "headerName": "Booking Amt",
            "width": 120,
            "valueFormatter": "Math.floor(value).toLocaleString()",
        },
        {
            "field": "status",
            "headerName": "Status",
            "width": 120,
            "filter": "agTextColumnFilter",
            ":cellStyle": (
                "params.value === 'ESCALATED'"
                " ? {background:'#FEE2E2', color:'#991B1B', fontWeight:'600', borderRadius:'4px'}"
                " : {background:'#D1FAE5', color:'#065F46', fontWeight:'600', borderRadius:'4px'}"
            ),
        },
        {
            "field": "ex_showroom_price",
            "headerName": "Ex-Showroom",
            "width": 120,
            "valueFormatter": "Math.floor(value).toLocaleString()",
        },
        {
            "field": "insurance",
            "headerName": "Insurance",
            "width": 120,
            "valueFormatter": "Math.floor(value).toLocaleString()",
        },
        {
            "field": "discount",
            "headerName": "Discount",
            "width": 100,
        },
        {
            "field": "remarks_complainant",
            "headerName": "Complainant Remarks",
            "width": 200,
        },
        {
            "field": "remark_complainee_aa",
            "headerName": "AA/Complainee Remarks",
            "width": 200,
        },
        {
            "field": "remark_admin",
            "headerName": "Admin Remarks",
            "width": 200,
        },
        {
            "field": "flag",
            "headerName": "Flag",
            "width": 80,
            "filter": "agTextColumnFilter",
        },
    ]

    grid = (
        ui.aggrid(
            {
                "columnDefs": col_defs,
                "rowData": complaints,
                "defaultColDef": {
                    "flex": 0,
                    "minWidth": 70,
                    "sortable": True,
                    "filter": True,
                    "floatingFilter": True,
                    "resizable": True,
                },
                "domLayout": "normal",
                "suppressColumnVirtualization": False,
                "animateRows": True,
                "pagination": True,
                "paginationPageSize": 25,
                "rowSelection": "single",
                "rowHeight": 30,
                "suppressCellFocus": True,
            },
            theme="balham",
            auto_size_columns=False,
        )
        .classes("w-full h-100")
        .style("font-family:Inter,sans-serif;font-size:13px;")
    )

    async def on_cell_clicked(e):
        row = e.args.get("data", {})
        complaint_code = row.get("complaint_code")
        if complaint_code:
            ui.navigate.to(f"/complaint-form?complaint_code={complaint_code}")

    grid.on("cellClicked", on_cell_clicked)
