from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from datetime import date, datetime


def generate_daily_report(backend_data=None):
    """
    Generate a formatted Excel daily report and return (BytesIO, filename).

    All data is supplied via backend_data. Structure expected:

    backend_data = {
        "report_date": "30/04/2026",          # str dd/mm/yyyy  OR  date/datetime object

        "booking": {
            "Total Cases Reported":                             <int>,
            "Files Received":                                   <int>,
            "Files Pending":                                    <int>,
            "Files Incomplete":                                 <int>,
            "Files Verified":                                   <int>,
            "Files Approved":                                   <int>,
            "Files Rejected":                                   <int>,
            "Verification Completion %":                        <float 0-1>,
            "Total Discount Given":                             <int/float>,
            "Discount as per Approved Scheme":                  <int/float>,
            "Net Excess Discount Amount":                       <int/float>,
            "Highest Discount Car Model":                       <str>,
            "Highest Discount Value":                           <int/float>,
            "Excess Discount Cases":                            <int>,
            "Allowable Discount Cases (out of Verified cases)": <int>,
            "Excess Discount Cases(out of Verified cases)":     <int>,
            "Zero Discount Cases(out of Verified cases)":       <int>,
        },

        "delivery": {
            # same keys as "booking" above
        },

        "files_pending": [
            # one dict per row, up to 10 rows displayed
            {
                "sno":  <int>,    # Serial number
                "date": <str>,    # e.g. "26/01/2026"
                "name": <str>,    # Customer name
                "pan":  <str>,    # PAN card number
                "type": <str>,    # "Booking" or "Delivery"
            },
            ...
        ],

        "docs_pending": [
            # one dict per row, up to 10 rows displayed
            {
                "sno":  <int>,    # Serial number
                "date": <str>,    # e.g. "26/01/2026"
                "name": <str>,    # Customer name
                "pan":  <str>,    # PAN card number
                "docs": <str>,    # e.g. "Ledger, Insurance, RTO"
            },
            ...
        ],
    }
    """
    if backend_data is None:
        backend_data = {}

    # ── Resolve report date ───────────────────────────────────────────────────
    raw_date = backend_data.get("report_date", "")
    if isinstance(raw_date, (date, datetime)):
        date_str = raw_date.strftime("%d/%m/%Y")
    elif raw_date:
        date_str = str(raw_date)
    else:
        date_str = ""

    booking       = backend_data.get("booking",       {})
    delivery      = backend_data.get("delivery",      {})
    files_pending = backend_data.get("files_pending", [])
    docs_pending  = backend_data.get("docs_pending",  [])

    # ── Workbook / sheet ──────────────────────────────────────────────────────
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Report"

    # ── Styles ────────────────────────────────────────────────────────────────
    font_bold   = Font(name="Times New Roman", bold=True,  color="000000")
    font_head   = Font(name="Times New Roman", bold=True,  size=15, color="000000")
    font_normal = Font(name="Times New Roman",             color="000000")

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left   = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    align_right  = Alignment(horizontal="right",  vertical="center")

    med = Side(style="medium")
    thn = Side(style="thin")

    fill_grey     = PatternFill("solid", fgColor="E7E6E6")
    fill_blue_hdr = PatternFill("solid", fgColor="9BC2E6")
    fill_blue_sub = PatternFill("solid", fgColor="D9E1F2")
    fill_red      = PatternFill("solid", fgColor="FF6D6D")

    # ── Column widths ─────────────────────────────────────────────────────────
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 33
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20

    # ── Helpers ───────────────────────────────────────────────────────────────
    def write_title(row_start):
        ws.merge_cells(f"A{row_start}:E{row_start + 1}")
        c = ws.cell(row=row_start, column=1,
                    value=f"Daily Report As on ({date_str})")
        c.font      = font_head
        c.alignment = align_center
        c.fill      = fill_grey
        for r in range(row_start, row_start + 2):
            ws.row_dimensions[r].height = 20
            for col in range(1, 6):
                ws.cell(row=r, column=col).border = Border(
                    left   = med if col == 1           else Side(style=None),
                    right  = med if col == 5           else Side(style=None),
                    top    = med if r == row_start     else Side(style=None),
                    bottom = med if r == row_start + 1 else Side(style=None),
                )

    def write_section_header(row, title):
        ws.merge_cells(f"A{row}:E{row}")
        c = ws.cell(row=row, column=1, value=title)
        c.font      = font_bold
        c.alignment = align_center
        c.fill      = fill_blue_hdr
        ws.row_dimensions[row].height = 18
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = Border(
                left   = med if col == 1 else Side(style=None),
                right  = med if col == 5 else Side(style=None),
                top    = med, bottom = med,
            )

    def write_col_headers_merged(row, d_label="Booking", e_label="Delivery"):
        ws.merge_cells(f"A{row}:C{row}")
        ws.row_dimensions[row].height = 16
        for col in range(1, 6):
            c = ws.cell(row=row, column=col)
            c.font      = font_bold
            c.alignment = align_center
            c.fill      = fill_blue_sub
            c.border    = Border(
                left   = med if col == 1 else thn,
                right  = med if col == 5 else thn,
                top    = thn, bottom = thn,
            )
        ws.cell(row=row, column=1).value = "Particulars"
        ws.cell(row=row, column=4).value = d_label
        ws.cell(row=row, column=5).value = e_label

    def write_data_row(row, label, b_val, d_val, highlight=False, is_last=False):
        bottom = med if is_last else thn
        bg     = fill_red if highlight else PatternFill(fill_type=None)
        ws.row_dimensions[row].height = 15

        ws.merge_cells(f"A{row}:C{row}")
        lc = ws.cell(row=row, column=1, value=label)
        lc.font      = font_normal
        lc.alignment = align_left
        lc.fill      = bg
        lc.border    = Border(left=med, right=thn, top=thn, bottom=bottom)
        for col in [2, 3]:
            ws.cell(row=row, column=col).border = Border(
                left=thn, right=thn, top=thn, bottom=bottom)
            ws.cell(row=row, column=col).fill = bg

        dc = ws.cell(row=row, column=4, value=b_val)
        dc.font      = font_normal
        dc.alignment = align_right if isinstance(b_val, (int, float)) else align_center
        dc.fill      = bg
        dc.border    = Border(left=thn, right=thn, top=thn, bottom=bottom)

        ec = ws.cell(row=row, column=5, value=d_val)
        ec.font      = font_normal
        ec.alignment = align_right if isinstance(d_val, (int, float)) else align_center
        ec.fill      = bg
        ec.border    = Border(left=thn, right=med, top=thn, bottom=bottom)

        return lc, dc, ec

    def write_list_col_headers(row, headers):
        ws.row_dimensions[row].height = 16
        for col, val in enumerate(headers, start=1):
            c = ws.cell(row=row, column=col, value=val)
            c.font      = font_bold
            c.alignment = align_center
            c.fill      = fill_blue_sub
            c.border    = Border(
                left   = med if col == 1 else thn,
                right  = med if col == 5 else thn,
                top    = thn, bottom = thn,
            )

    def write_list_data_rows(start_row, data_list, num_rows, value_keys):
        for i in range(num_rows):
            r        = start_row + i
            is_last  = (i == num_rows - 1)
            bottom   = med if is_last else thn
            ws.row_dimensions[r].height = 15
            row_data = data_list[i] if i < len(data_list) else {}
            vals     = [row_data.get(k, "") for k in value_keys]
            for col in range(1, 6):
                val = vals[col - 1] if col - 1 < len(vals) else ""
                c = ws.cell(row=r, column=col, value=val)
                c.font      = font_normal
                c.alignment = align_center
                c.fill      = PatternFill(fill_type=None)
                c.border    = Border(
                    left   = med if col == 1 else thn,
                    right  = med if col == 5 else thn,
                    top    = thn, bottom = bottom,
                )

    # ── Layout ────────────────────────────────────────────────────────────────

    # Title — rows 1-2
    write_title(1)

    # Table 1: Files Reconciliation — rows 4-13
    write_section_header(4, "Files Reconciliation")
    write_col_headers_merged(5)

    recon_rows = [
        ("Total Cases Reported",       False),
        ("Files Received",             False),
        ("Files Pending",              True),
        ("Files Incomplete",           True),
        ("Files Verified",             False),
        ("Files Approved",             False),
        ("Files Rejected",             True),
        ("Verification Completion %",  False),
    ]
    for i, (item, highlight) in enumerate(recon_rows):
        r       = 6 + i
        is_last = (i == len(recon_rows) - 1)
        b_val   = booking.get(item,  "")
        d_val   = delivery.get(item, "")
        lc, dc, ec = write_data_row(r, item, b_val, d_val, highlight, is_last)
        if item == "Verification Completion %":
            dc.number_format = '0%'
            ec.number_format = '0%'

    # Table 2: Discount Summary — rows 16-26
    write_section_header(16, "Discount Summary")
    write_col_headers_merged(17)

    discount_rows = [
        ("Total Discount Given",                             False),
        ("Discount as per Approved Scheme",                  False),
        ("Net Excess Discount Amount",                       False),
        ("Highest Discount Car Model",                       False),
        ("Highest Discount Value",                           False),
        ("Excess Discount Cases",                            False),
        ("Allowable Discount Cases (out of Verified cases)", False),
        ("Excess Discount Cases(out of Verified cases)",     True),
        ("Zero Discount Cases(out of Verified cases)",       False),
    ]
    for i, (item, highlight) in enumerate(discount_rows):
        r       = 18 + i
        is_last = (i == len(discount_rows) - 1)
        b_val   = booking.get(item,  "")
        d_val   = delivery.get(item, "")
        lc, dc, ec = write_data_row(r, item, b_val, d_val, highlight, is_last)
        if any(kw in item for kw in ("Amount", "Value", "Discount Given", "Approved Scheme")):
            dc.number_format = '##,##,##0'
            ec.number_format = '##,##,##0'

    # List 1: Files Pending — rows 28-39
    write_section_header(28, "List of Booking and Delivery Customer Files Pending")
    write_list_col_headers(29, ["S.no", "File Date", "Customer Name", "Pan No.", "File Type"])
    write_list_data_rows(
        start_row  = 30,
        data_list  = files_pending,
        num_rows   = 10,
        value_keys = ["sno", "date", "name", "pan", "type"],
    )

    # List 2: Documents Pending — rows 40-51
    write_section_header(40, "List of Documents Pending")
    write_list_col_headers(41, ["S.no", "File Date", "Customer Name", "Pan No.", "List of Pending Doc"])
    write_list_data_rows(
        start_row  = 42,
        data_list  = docs_pending,
        num_rows   = 10,
        value_keys = ["sno", "date", "name", "pan", "docs"],
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    safe_date = date_str.replace("/", "-") if date_str else "no-date"
    file_name = f"Daily-Report-{safe_date}.xlsx"
    return buffer, file_name