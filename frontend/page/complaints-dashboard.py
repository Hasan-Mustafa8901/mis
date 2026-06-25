from nicegui import ui
from auth import protected_page
from main import render_topbar, get_user, render_complaints_table
from api import api_get, api_post


# PAGE: COMPLAINTS DASHBOARD
@ui.page("/complaints-dashboard")
@protected_page
async def complaints_dashboard_page():
    def sidebar(): ...

    render_topbar("Complaints Dashboard")

    # Fetch all complaints
    try:
        response: dict = await api_get("/complaints/table")
        all_complaints = response.get("rows", [])
    except Exception:
        all_complaints = []

    # Get current user's dealership name (adjust based on your auth system)
    current_user = get_user()  # You may need to modify this to get dealer name

    # Split complaints based on current user
    complaints_against = []
    complaints_raised_by = []

    for complaint in all_complaints:
        # Complaint AGAINST current user (they are the complainee)
        if complaint.get("complainee_dealer_name") == current_user.get("name"):
            complaints_against.append(complaint)

        # Complaint RAISED BY current user (they are the complainant)
        if complaint.get("complainant_dealer_name") == current_user.get("name"):
            complaints_raised_by.append(complaint)

    # State for selected complaint
    selected_complaint = {"data": None}
    remarks_display = ui.column().classes("w-full")

    def render_remarks_section():
        """Render the remarks section for selected complaint"""
        remarks_display.clear()

        if not selected_complaint["data"]:
            with remarks_display:
                with ui.card().classes("w-full p-8 text-center"):
                    ui.icon("info", size="xl").classes("text-gray-300 mb-2")
                    ui.label("Select a complaint to view and add remarks").classes(
                        "text-gray-400 text-sm"
                    )
            return

        complaint = selected_complaint["data"]

        with remarks_display:
            # Complaint Details Header
            with ui.card().classes(
                "w-full p-5 mb-4 bg-gradient-to-r from-red-50 to-orange-50 border-l-4 border-red-500"
            ):
                with ui.row().classes("w-full items-start justify-between"):
                    with ui.column().classes("gap-1"):
                        ui.label(
                            f"Complaint: {complaint.get('complaint_code', 'N/A')}"
                        ).classes("text-lg font-bold text-gray-900")
                        ui.label(
                            f"Customer: {complaint.get('customer_name', 'N/A')}"
                        ).classes("text-sm text-gray-600")
                        ui.label(
                            f"Date: {complaint.get('date_of_complaint', 'N/A')}"
                        ).classes("text-xs text-gray-500")

                    # Status badge
                    status = complaint.get("status", "OPEN")
                    status_colors = {
                        "OPEN": "bg-blue-100 text-blue-800",
                        "IN_PROGRESS": "bg-yellow-100 text-yellow-800",
                        "RESOLVED": "bg-green-100 text-green-800",
                        "CLOSED": "bg-gray-100 text-gray-800",
                        "ESCALATED": "bg-red-100 text-red-800",
                    }
                    ui.label(status).classes(
                        f"px-3 py-1 rounded-full text-xs font-bold {status_colors.get(status, 'bg-gray-100 text-gray-800')}"
                    )

            # Existing Remarks Display
            with ui.card().classes("w-full p-5 mb-4"):
                ui.label("Existing Remarks").classes(
                    "text-sm font-bold text-gray-700 mb-3"
                )

                # Complainant Remarks
                with ui.row().classes("w-full mb-3 pb-3 border-b"):
                    with ui.column().classes("w-full gap-1"):
                        ui.label("Complainant Remarks:").classes(
                            "text-xs font-bold text-gray-500 uppercase"
                        )
                        ui.label(
                            complaint.get("remarks_complainant") or "No remarks"
                        ).classes("text-sm text-gray-700")

                # AA Remarks
                with ui.row().classes("w-full mb-3 pb-3 border-b"):
                    with ui.column().classes("w-full gap-1"):
                        ui.label("Audit Assistant Remarks:").classes(
                            "text-xs font-bold text-gray-500 uppercase"
                        )
                        ui.label(
                            complaint.get("remark_complainee_aa") or "No remarks"
                        ).classes("text-sm text-gray-700")

                # Admin Remarks
                with ui.row().classes("w-full"):
                    with ui.column().classes("w-full gap-1"):
                        ui.label("Admin Remarks:").classes(
                            "text-xs font-bold text-gray-500 uppercase"
                        )
                        ui.label(complaint.get("remark_admin") or "No remarks").classes(
                            "text-sm text-gray-700"
                        )

            # Add New Remark Section
            with ui.card().classes("w-full p-5"):
                ui.label("Add Your Remark").classes(
                    "text-sm font-bold text-gray-700 mb-3"
                )

                remark_input = (
                    ui.textarea(
                        label="Your Response/Remark",
                        placeholder="Enter your remark here...",
                    )
                    .props("outlined rows=4")
                    .classes("w-full")
                )

                async def submit_remark():
                    if not remark_input.value or not remark_input.value.strip():
                        ui.notify("Please enter a remark", type="warning")
                        return

                    try:
                        await api_post(
                            "/complaints/remarks",
                            {
                                "complaint_code": complaint.get("complaint_code"),
                                "remarks": remark_input.value.strip(),
                            },
                        )
                        ui.notify("Remark added successfully", type="positive")
                        remark_input.set_value("")

                        # Refresh the complaint data
                        try:
                            response = await api_get("/complaints/")
                            all_complaints_updated = response.get("data", [])
                            updated_complaint = next(
                                (
                                    c
                                    for c in all_complaints_updated
                                    if c.get("complaint_code")
                                    == complaint.get("complaint_code")
                                ),
                                None,
                            )
                            if updated_complaint:
                                selected_complaint["data"] = updated_complaint
                                render_remarks_section()
                        except:
                            pass

                    except Exception as e:
                        ui.notify(f"Failed to add remark: {str(e)}", type="negative")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button(
                        "Clear", on_click=lambda: remark_input.set_value("")
                    ).props("outline color=grey")
                    ui.button("Submit Remark", on_click=submit_remark).props(
                        "color=primary"
                    ).classes("bg-[#E8402A]")

    # Modified render function for complaints against table
    def render_complaints_against_table(complaints):
        """Render complaints table with click to select"""
        if not complaints:
            with ui.card().classes("w-full").style("padding:48px;text-align:center"):
                ui.label("📭").style("font-size:36px")
                ui.label("No complaints against you").style(
                    "font-size:14px;font-weight:500;color:#6B7280;margin-top:8px"
                )
            return

        # Simplified column definitions for horizontal layout
        col_defs = [
            {
                "field": "complaint_code",
                "headerName": "Code",
                "pinned": "left",
                "width": 130,
            },
            {
                "field": "date_of_complaint",
                "headerName": "Date",
                "width": 120,
                ":valueFormatter": "params.value ? new Date(params.value).toLocaleDateString() : '—'",
            },
            {
                "field": "status",
                "headerName": "Status",
                "width": 130,
                ":cellStyle": (
                    "params.value === 'ESCALATED'"
                    " ? {background:'#FEE2E2', color:'#991B1B', fontWeight:'600'}"
                    " : {background:'#D1FAE5', color:'#065F46', fontWeight:'600'}"
                ),
            },
            {"field": "customer_name", "headerName": "Customer", "width": 160},
            {"field": "customer_mobile", "headerName": "Mobile", "width": 130},
            {"field": "car_model", "headerName": "Model", "width": 150},
            {
                "field": "complainant_dealer_name",
                "headerName": "Complainant Dealer",
                "width": 180,
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
                    "paginationPageSize": 10,
                    "rowSelection": "single",
                    "rowHeight": 30,
                    "suppressCellFocus": True,
                },
                theme="balham",
                auto_size_columns=False,
            )
            .classes("w-full h-96")
            .style("font-family:Inter,sans-serif;font-size:13px;")
        )

        async def on_cell_clicked(e):
            row = e.args.get("data", {})
            if row:
                selected_complaint["data"] = row
                render_remarks_section()

        grid.on("cellClicked", on_cell_clicked)
        return grid

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        # ── SIDEBAR ─────────────────────────────────────────
        with ui.column().classes(
            "w-[220px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"
        ):
            ui.label("Quick Nav").classes(
                "text-[9px] font-bold tracking-[1.3px] uppercase text-gray-400 px-4 mb-1.5 mt-4.5"
            )
            ui.link("📊 Dashboard", "/").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("📅 Daily Reporting", "/daily-reporting").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("📋 Booking MIS", "/booking-mis").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            ui.link("📊 Complaints Dashboard", "/complaints-dashboard").classes(
                "flex px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] no-underline"
            )
            ui.link("📑 Complaints Control Panel", "/complaints-ctrl").classes(
                "flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline"
            )
            sidebar()

        # ── MAIN CONTENT ─────────────────────────────────────
        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden"):
            # Page header
            with ui.row().classes("w-full items-center justify-between mb-5"):
                with ui.column().classes("gap-1"):
                    ui.label("Complaints Dashboard").classes(
                        "text-[18px] font-bold text-gray-900 leading-none"
                    )
                    ui.label(
                        f"{len(complaints_against)} against you · {len(complaints_raised_by)} raised by you"
                    ).classes("text-[12px] text-gray-400")

                with (
                    ui.button(on_click=lambda: ui.navigate.to("/complaint-form"))
                    .classes(
                        "bg-[#E8402A] text-white font-semibold text-[13px] px-4.5 py-2 rounded-[7px] shadow-sm"
                    )
                    .props("no-caps unelevated")
                ):
                    ui.icon("add").classes("text-white text-lg text-weight-bold")
                    ui.label("New Complaint").classes("text-weight-bold pl-2")

            # ── HORIZONTAL LAYOUT: Tables Side by Side ──
            with ui.row().classes("w-full gap-4 mb-6"):
                # Left: Complaints Against You
                with ui.column().classes("flex-1 min-w-0"):
                    with ui.card().classes("w-full p-0 shadow-sm rounded-xl h-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between px-5 py-3 border-b border-gray-100 bg-red-50"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("warning", size="sm").classes("text-red-600")
                                ui.label("Complaints Against You").classes(
                                    "text-[14px] font-bold text-red-900"
                                )
                            ui.label(f"{len(complaints_against)} total").classes(
                                "text-[11px] font-bold text-red-700 bg-red-100 px-2 py-1 rounded"
                            )

                        render_complaints_against_table(complaints_against)

                # Right: Complaints Raised By You
                with ui.column().classes("flex-1 min-w-0"):
                    with ui.card().classes("w-full p-0 shadow-sm rounded-xl h-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between px-5 py-3 border-b border-gray-100 bg-blue-50"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("flag", size="sm").classes("text-blue-600")
                                ui.label("Complaints Raised By You").classes(
                                    "text-[14px] font-bold text-blue-900"
                                )
                            ui.label(f"{len(complaints_raised_by)} total").classes(
                                "text-[11px] font-bold text-blue-700 bg-blue-100 px-2 py-1 rounded"
                            )

                        render_complaints_table(complaints_raised_by)

            # ── REMARKS SECTION (Full Width Below) ──
            with ui.card().classes("w-full p-0 shadow-sm rounded-xl"):
                with ui.row().classes(
                    "w-full items-center px-5 py-3 border-b border-gray-100 bg-purple-50"
                ):
                    ui.icon("chat", size="sm").classes("text-purple-600")
                    ui.label("Complaint Details & Remarks").classes(
                        "text-[14px] font-bold text-purple-900"
                    )

                with ui.column().classes("w-full p-5"):
                    remarks_display

            # Initial render
            render_remarks_section()
