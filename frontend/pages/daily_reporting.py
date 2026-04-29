from datetime import date, timedelta
import calendar
from nicegui import ui
from auth.auth import protected_page
from components.layout import render_topbar, sidebar
from services.api import api_get

@ui.page("/daily-reporting")
@protected_page
async def daily_reporting_page() -> None:
    render_topbar("Daily Reporting")

    # ── In-memory state ──────────────────────────────────────
    # row_data stores user-typed values per (tt, date)
    row_data: dict = {}  # (tt, date) → {total_count, files_received, file_incomplete, files_in_mis}
    # dialog_data stores rows for the popup tables (pending & incomplete dialogs)
    dialog_data: dict = {}  # (tt, date, col) → [{date, name, pan, remarks}, …]
    label_refs: dict = {}  # (tt, date, col) → ui.label  for computed cells
    total_refs: dict = {}  # (tt, col) → ui.label  for footer totals

    # ── Transactions ─────────────────────────────────────────
    try:
        all_transactions: list = await api_get("/transactions")
    except Exception:
        all_transactions = []

    today_str = date.today().isoformat()

    def mis_count(tt: str, d: str) -> int:
        field = "booking_date" if tt == "booking" else "delivery_date"
        return sum(1 for t in all_transactions if (t.get(field) or "")[:10] == d)

    def get_all_txn_dates(tt: str) -> set:
        field = "booking_date" if tt == "booking" else "delivery_date"
        return {
            (t.get(field) or "")[:10]
            for t in all_transactions
            if (t.get(field) or "")[:10]
        }

    def get_stored(tt: str, d: str) -> dict:
        return row_data.get((tt, d), {})

    # ── Computed cell values ──────────────────────────────────
    def compute_row(tt: str, d: str) -> dict:
        s = get_stored(tt, d)
        tc = int(s.get("total_count", 0) or 0)
        fr = int(s.get("files_received", 0) or 0)
        fi = len(dialog_data.get((tt, d, "files_incomplete"), []))
        fm = int(s.get("files_in_mis", 0) or 0)
        fp = max(0, tc - fr)  # Files Pending  = Total Count - Files Received
        fv = int(s.get("files_verified", 0) or 0)
        diff = fv - fm  # Difference     = Files Verified - Files in MIS
        return dict(tc=tc, fr=fr, fi=fi, fm=fm, fp=fp, fv=fv, diff=diff)

    # ── Totals recompute ─────────────────────────────────────
    def recompute_totals(tt: str, dates: list) -> None:
        sums = {
            c: 0
            for c in [
                "total_count",
                "files_received",
                "files_pending",
                "file_incomplete",
                "files_verified",
                "files_in_mis",
                "difference",
            ]
        }
        for d in dates:
            r = compute_row(tt, d)
            sums["total_count"] += r["tc"]
            sums["files_received"] += r["fr"]
            sums["files_pending"] += r["fp"]
            sums["file_incomplete"] += r["fi"]
            sums["files_verified"] += r["fv"]
            sums["files_in_mis"] += r["fm"]
            sums["difference"] += r["diff"]
        for col, total in sums.items():
            lbl = total_refs.get((tt, col))
            if lbl:
                lbl.set_text(str(total))

    def refresh_computed_row(tt: str, d: str, dates: list) -> None:
        r = compute_row(tt, d)

        # Files Pending label
        lbl_fp = label_refs.get((tt, d, "files_pending"))
        if lbl_fp:
            color = "#92400E" if r["fp"] > 0 else "#10B981"
            weight = "700" if r["fp"] > 0 else "600"
            lbl_fp.set_text(str(r["fp"]))
            lbl_fp.style(
                f"font-family:monospace;font-size:15px;font-weight:{weight};color:{color};text-align:center"
            )

        # Files Incomplete label
        lbl_fi = label_refs.get((tt, d, "file_incomplete"))
        if lbl_fi:
            fi_color = "#92400E" if r["fi"] > 0 else "#10B981"
            fi_weight = "700" if r["fi"] > 0 else "600"
            lbl_fi.set_text(str(r["fi"]))
            lbl_fi.style(
                f"font-family:monospace;font-size:15px;font-weight:{fi_weight};color:{fi_color};text-align:center"
            )

        # Files Verified label
        lbl_fv = label_refs.get((tt, d, "files_verified"))
        if lbl_fv:
            lbl_fv.set_text(str(r["fv"]))

        # Difference label
        lbl_diff = label_refs.get((tt, d, "difference"))
        if lbl_diff:
            color = (
                "#EF4444"
                if r["diff"] < 0
                else ("#10B981" if r["diff"] == 0 else "#F59E0B")
            )
            lbl_diff.set_text(str(r["diff"]))
            lbl_diff.style(
                f"font-family:monospace;font-size:15px;font-weight:700;color:{color};text-align:center"
            )

        recompute_totals(tt, dates)

    # ── Generic detail dialog (Pending & Incomplete) ─────────
    _dlg_state: dict = {
        "tt": None,
        "d": None,
        "col": None,
        "title_el": None,
        "body_el": None,
        "dates": [],
    }

    def refresh_detail_dialog(rows: list = []) -> None:
        _dlg_state["body_el"].clear()

        TH = (
            "border:1px solid #D1D5DB;padding:9px 13px;text-align:center;"
            "font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:.06em;color:#6B7280;background:#F9FAFB;white-space:nowrap"
        )
        TD = (
            "border:1px solid #E5E7EB;padding:8px 12px;"
            "font-size:13px;vertical-align:middle;text-align:center"
        )

        with _dlg_state["body_el"]:
            with ui.element("table").style(
                "width:100%;border-collapse:collapse;min-width:680px"
            ):
                with ui.element("thead"):
                    with ui.element("tr"):
                        for h, w in [
                            ("S.No", "60px"),
                            ("Date", "130px"),
                            ("Customer Name", ""),
                            ("PAN Card", "130px"),
                            ("Remarks", "180px"),
                        ]:
                            with ui.element("th").style(
                                TH + (f";width:{w}" if w else "")
                            ):
                                ui.label(h)

                with ui.element("tbody"):
                    if not rows:
                        with ui.element("tr"):
                            with (
                                ui.element("td")
                                .props('colspan="5"')
                                .style(
                                    "border:1px solid #E5E7EB;padding:40px;"
                                    "text-align:center;color:#9CA3AF;font-size:13px"
                                )
                            ):
                                with ui.column().classes("items-center gap-2"):
                                    ui.label("📭").style("font-size:28px")
                                    ui.label("No records found for this date").style(
                                        "color:#9CA3AF;font-size:13px"
                                    )
                    else:
                        for i, row in enumerate(rows):
                            row_bg = "#FFFFFF" if i % 2 == 0 else "#F9FAFB"
                            with ui.element("tr").style(f"background:{row_bg}"):
                                # S.No
                                with ui.element("td").style(
                                    TD + ";font-family:monospace;font-weight:700;"
                                    "color:#6366F1;background:#EEF2FF;width:60px"
                                ):
                                    ui.label(str(i + 1))

                                # Date
                                with ui.element("td").style(TD + ";width:130px"):
                                    ui.label(row.get("date", "—")).style(
                                        "font-size:13px;color:#374151;font-weight:500"
                                    )

                                # Customer Name
                                with ui.element("td").style(TD):
                                    ui.label(row.get("customer_name", "—")).style(
                                        "font-size:13px;color:#111827;font-weight:600"
                                    )

                                # PAN Card
                                with ui.element("td").style(TD + ";width:130px"):
                                    ui.label(row.get("pan_number", "—")).style(
                                        "font-family:monospace;font-size:13px;"
                                        "color:#374151;letter-spacing:.04em"
                                    )

                                # Remarks
                                with ui.element("td").style(TD + ";width:180px"):
                                    ui.label(row.get("remarks", "—")).style(
                                        "font-size:13px;color:#6B7280"
                                    )

    # Build dialog once
    with (
        ui.dialog() as detail_dlg,
        ui.card().classes("w-[860px] max-w-[96vw] p-6 rounded-xl shadow-2xl"),
    ):
        with ui.row().classes("w-full items-center justify-between mb-4"):
            title_el = ui.label("Details").classes(
                "text-[15px] font-bold text-gray-900"
            )
            _dlg_state["title_el"] = title_el
            ui.button(icon="close", on_click=detail_dlg.close).props("flat round dense")

        body_el = (
            ui.element("div")
            .classes("w-full overflow-x-auto")
            .style("max-height:450px;overflow-y:auto")
        )
        _dlg_state["body_el"] = body_el

        with ui.row().classes(
            "w-full justify-between items-center mt-4 pt-4 border-t border-gray-100"
        ):
            dlg_count_label = ui.label("0 records").classes(
                "text-[12px] font-semibold text-gray-400"
            )
            _dlg_state["count_label"] = dlg_count_label

            with ui.row().classes("gap-2"):
                async def _refresh_dlg():
                    await _fetch_and_show_dialog()

                ui.button("↻ Refresh", on_click=_refresh_dlg).props(
                    "outline no-caps"
                ).classes("text-[13px] border-gray-300 text-gray-600")
                ui.button("Close", on_click=detail_dlg.close).props(
                    "unelevated no-caps"
                ).classes("bg-[#E8402A] text-white text-[13px] px-5")

    async def _fetch_and_show_dialog() -> None:
        """Fetch records from backend and populate the dialog."""
        tt = _dlg_state["tt"]
        d = _dlg_state["d"]
        col = _dlg_state["col"]

        _dlg_state["body_el"].clear()
        with _dlg_state["body_el"]:
            with ui.row().classes("w-full justify-center items-center gap-3 py-10"):
                ui.spinner(size="md", color="primary")
                ui.label("Loading records…").style("color:#9CA3AF;font-size:13px")

        try:
            endpoint = (
                f"/daily-report/pending?type={tt}&date={d}"
                if col == "files_pending"
                else f"/daily-report/incomplete?type={tt}&date={d}"
            )
            rows: list = await api_get(endpoint)
        except Exception:
            rows = []

        count_lbl = _dlg_state.get("count_label")
        if count_lbl:
            count_lbl.set_text(f"{len(rows)} record{'s' if len(rows) != 1 else ''}")

        if col == "files_incomplete":
            k = (tt, d, "files_incomplete")
            dialog_data[k] = rows
            refresh_computed_row(tt, d, _dlg_state["dates"])

        refresh_detail_dialog(rows)

    def open_detail_dialog(tt: str, d: str, col: str, dates: list = []) -> None:
        _dlg_state["tt"] = tt
        _dlg_state["d"] = d
        _dlg_state["col"] = col
        _dlg_state["dates"] = dates
        ttype = "Booking" if tt == "booking" else "Delivery"
        col_label = "Files Pending" if col == "files_pending" else "Files Incomplete"
        _dlg_state["title_el"].set_text(f"📋 {col_label} — {d}  ({ttype})")
        detail_dlg.open()
        ui.timer(0.05, _fetch_and_show_dialog, once=True)

    # ── Shared cell styles ───────────────────────────────────
    TH_S = (
        "border:1px solid #D1D5DB;padding:9px 14px;text-align:center;"
        "font-size:12px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.07em;color:#6B7280;background:#F9FAFB;white-space:nowrap"
    )
    TD_S = (
        "border:1px solid #E5E7EB;padding:6px 10px;"
        "font-size:15px;vertical-align:middle;text-align:center"
    )
    TF_S = (
        "border:1px solid #D1D5DB;padding:9px 14px;text-align:center;"
        "font-size:15px;font-weight:700;background:#ECEEF2;color:#111827"
    )

    # ── Table builder ────────────────────────────────────────
    def build_table(tt: str, dates: list, parent) -> None:
        with parent:
            with ui.element("table").style(
                "width:100%;border-collapse:collapse;border:1px solid #D1D5DB;"
                "table-layout:auto;font-family:Inter,sans-serif"
            ):
                with ui.element("thead"):
                    with ui.element("tr"):
                        headers = [
                            ("Date", "140px"),
                            ("Total Count", "130px"),
                            ("Files Received", "130px"),
                            ("Files Pending", "130px"),
                            ("Files Incomplete", "130px"),
                            ("Files Verified", "130px"),
                            ("Files in MIS", "130px"),
                            ("Difference", "120px"),
                        ]
                        for hdr, w in headers:
                            with ui.element("th").style(TH_S + f";width:{w}"):
                                ui.label(hdr)

                with ui.element("tbody"):
                    for idx_d, d in enumerate(dates):
                        r = compute_row(tt, d)
                        is_today = d == today_str

                        if is_today:
                            row_bg = "background:#EFF6FF"
                        elif idx_d % 2 == 1:
                            row_bg = "background:#FAFAFA"
                        else:
                            row_bg = "background:#FFFFFF"

                        with ui.element("tr").style(row_bg):
                            with ui.element("td").style(TD_S + ";white-space:nowrap"):
                                if is_today:
                                    with ui.row().classes("items-center justify-center gap-1.5"):
                                        ui.label(d).style("font-weight:700;color:#2563EB;font-size:14px")
                                        ui.label("TODAY").style(
                                            "background:#DBEAFE;color:#1D4ED8;font-size:10px;"
                                            "padding:1px 7px;border-radius:10px;font-weight:800;"
                                            "letter-spacing:.04em"
                                        )
                                else:
                                    ui.label(d).style("font-weight:500;color:#374151;font-size:14px")

                            with ui.element("td").style(TD_S):
                                ui.input(
                                    value=str(r["tc"]) if r["tc"] else "",
                                    placeholder="0",
                                    on_change=lambda e, _tt=tt, _d=d: (
                                        row_data.setdefault((_tt, _d), {}).__setitem__(
                                            "total_count", int(e.value) if (e.value or "").isdigit() else 0
                                        ),
                                        refresh_computed_row(_tt, _d, dates),
                                    ),
                                ).props('type="number" min="0" step="1" outlined dense').classes("w-full text-center").style(
                                    "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                )

                            with ui.element("td").style(TD_S):
                                ui.input(
                                    value=str(r["fr"]) if r["fr"] else "",
                                    placeholder="0",
                                    on_change=lambda e, _tt=tt, _d=d: (
                                        row_data.setdefault((_tt, _d), {}).__setitem__(
                                            "files_received", int(e.value) if (e.value or "").isdigit() else 0
                                        ),
                                        refresh_computed_row(_tt, _d, dates),
                                    ),
                                ).props('type="number" min="0" step="1" outlined dense').classes("w-full text-center").style(
                                    "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                )

                            fp_color = "#92400E" if r["fp"] > 0 else "#10B981"
                            fp_weight = "700" if r["fp"] > 0 else "600"
                            with (
                                ui.element("td")
                                .style(TD_S + ";cursor:pointer;background:#FFF7ED" if r["fp"] > 0 else TD_S + ";cursor:pointer")
                                .on("click", lambda _, _tt=tt, _d=d: open_detail_dialog(_tt, _d, "files_pending"))
                            ):
                                fp_lbl = ui.label(str(r["fp"])).style(
                                    f"font-family:monospace;font-size:15px;"
                                    f"font-weight:{fp_weight};color:{fp_color};text-align:center"
                                )
                                label_refs[(tt, d, "files_pending")] = fp_lbl

                            fi_color = "#92400E" if r["fi"] > 0 else "#10B981"
                            fi_weight = "700" if r["fi"] > 0 else "600"
                            with (
                                ui.element("td")
                                .style(TD_S + ";cursor:pointer;background:#FFF7ED" if r["fi"] > 0 else TD_S + ";cursor:pointer")
                                .on("click", lambda _, _tt=tt, _d=d, _dates=dates: open_detail_dialog(_tt, _d, "files_incomplete", _dates))
                            ):
                                fi_lbl = ui.label(str(r["fi"])).style(
                                    f"font-family:monospace;font-size:15px;"
                                    f"font-weight:{fi_weight};color:{fi_color};text-align:center"
                                )
                                label_refs[(tt, d, "file_incomplete")] = fi_lbl

                            with ui.element("td").style(TD_S):
                                ui.input(
                                    value=str(r["fv"]) if r["fv"] else "",
                                    placeholder="0",
                                    on_change=lambda e, _tt=tt, _d=d: (
                                        row_data.setdefault((_tt, _d), {}).__setitem__(
                                            "files_verified", int(e.value) if (e.value or "").isdigit() else 0
                                        ),
                                        refresh_computed_row(_tt, _d, dates),
                                    ),
                                ).props('type="number" min="0" step="1" outlined dense').classes("w-full text-center").style(
                                    "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                )

                            with ui.element("td").style(TD_S):
                                ui.input(
                                    value=str(r["fm"]) if r["fm"] else "",
                                    placeholder="0",
                                    on_change=lambda e, _tt=tt, _d=d: (
                                        row_data.setdefault((_tt, _d), {}).__setitem__(
                                            "files_in_mis", int(e.value) if (e.value or "").isdigit() else 0
                                        ),
                                        refresh_computed_row(_tt, _d, dates),
                                    ),
                                ).props('type="number" min="0" step="1" outlined dense').classes("w-full text-center").style(
                                    "font-family:monospace;font-size:15px;font-weight:600;text-align:center"
                                )

                            diff_color = "#EF4444" if r["diff"] < 0 else ("#10B981" if r["diff"] == 0 else "#F59E0B")
                            with ui.element("td").style(TD_S):
                                diff_lbl = ui.label(str(r["diff"])).style(
                                    f"font-family:monospace;font-size:15px;"
                                    f"font-weight:700;color:{diff_color};text-align:center"
                                )
                                label_refs[(tt, d, "difference")] = diff_lbl

                with ui.element("tfoot"):
                    with ui.element("tr").style("background:#ECEEF2;border-top:2px solid #D1D5DB"):
                        with ui.element("td").style(TF_S):
                            ui.label("TOTAL").style("font-size:12px;font-weight:800;letter-spacing:.06em;color:#374151")
                        for col_key in ["total_count", "files_received", "files_pending", "file_incomplete", "files_verified", "files_in_mis", "difference"]:
                            with ui.element("td").style(TF_S):
                                lbl = ui.label("0").style("font-family:monospace;font-size:15px;font-weight:700;color:#111827")
                                total_refs[(tt, col_key)] = lbl

        recompute_totals(tt, dates)

    # ── Date range helpers ────────────────────────────────────
    _today = date.today()
    _yester = _today - timedelta(days=1)
    _RANGE_OPTIONS = {
        "today": f"Today ({_today.strftime('%d-%m-%Y')})",
        "yesterday": f"Yesterday ({_yester.strftime('%d-%m-%Y')})",
        "last7": "Last 7 Days",
        "last15": "Last 15 Days",
        "custom": "Custom Date Range",
    }

    def _dates_for_range(selection: str, tt: str, from_date: str = "", to_date: str = "") -> list[str]:
        if selection == "today":
            base = {_today.isoformat()}
        elif selection == "yesterday":
            base = {_yester.isoformat()}
        elif selection == "last7":
            base = {(_today - timedelta(days=i)).isoformat() for i in range(7)}
        elif selection == "last15":
            base = {(_today - timedelta(days=i)).isoformat() for i in range(15)}
        else:  # custom range
            if from_date and to_date and from_date <= to_date:
                try:
                    fd = date.fromisoformat(from_date)
                    td_ = date.fromisoformat(to_date)
                    delta = (td_ - fd).days
                    base = {(fd + timedelta(days=i)).isoformat() for i in range(delta + 1)}
                except ValueError:
                    base = {today_str}
            elif from_date:
                base = {from_date}
            else:
                txn_dates = get_all_txn_dates(tt)
                return sorted(txn_dates | {today_str}, reverse=True)
        txn_dates = get_all_txn_dates(tt)
        return sorted(base | (txn_dates & base), reverse=True)

    def _rebuild(selection: str, from_date: str = "", to_date: str = "") -> None:
        label_refs.clear()
        total_refs.clear()
        b_dates = _dates_for_range(selection, "booking", from_date, to_date)
        d_dates = _dates_for_range(selection, "delivery", from_date, to_date)
        booking_wrap.clear()
        delivery_wrap.clear()
        build_table("booking", b_dates, booking_wrap)
        build_table("delivery", d_dates, delivery_wrap)

    # ── Page layout ───────────────────────────────────────────
    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        with ui.column().classes("w-[220px] shrink-0 bg-white border-r border-gray-200 py-4 pb-10 sticky top-[52px] h-[calc(100vh-52px)] overflow-y-auto"):
            ui.label("Quick Nav").classes("text-[9px] font-bold tracking-[1.3px] uppercase text-gray-500 px-4 mb-1.5 mt-4.5")
            ui.link("📊 Dashboard", "/").classes("flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline")
            ui.link("📅 Daily Reporting", "/daily-reporting").classes("flex px-4 py-2 text-[12.5px] font-semibold text-[#E8402A] bg-[#FEF2F0] border-l-3 border-[#E8402A] no-underline")
            ui.link("📋 Booking MIS", "/booking-mis").classes("flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline")
            ui.link("🚚 Delivery MIS", "/delivery-mis").classes("flex items-center justify-between px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 hover:text-gray-900 transition-all no-underline")
            ui.link("📑 Complaints Table", "/complaints-table").classes("flex px-4 py-2 text-[12.5px] font-medium text-gray-600 border-l-3 border-transparent hover:bg-gray-50 no-underline")
            sidebar()

        with ui.column().classes("flex-1 min-w-0 p-6 px-7 pb-16 overflow-x-hidden gap-6"):
            with ui.row().classes("w-full items-start justify-between mb-1"):
                with ui.column().classes("gap-1"):
                    ui.label("Daily Reporting").classes("text-[18px] font-bold text-gray-900 leading-none")
                    ui.label("Track booking & delivery file status by date").classes("text-[12px] text-gray-400")

                with ui.column().classes("gap-2 items-end"):
                    range_select = ui.select(options=_RANGE_OPTIONS, value="custom", label="Date Range").classes("w-52").props("outlined dense").style("font-size:13px;font-weight:500;border-radius:8px")
                    custom_range_row = ui.row().classes("items-center gap-2")
                    with custom_range_row:
                        ui.label("From:").classes("text-[12px] text-gray-500 whitespace-nowrap")
                        from_inp = ui.input(label="", value=today_str).props('type="date" outlined dense').classes("w-36")
                        ui.label("To:").classes("text-[12px] text-gray-500 whitespace-nowrap")
                        to_inp = ui.input(label="", value=today_str).props('type="date" outlined dense').classes("w-36")

            with ui.card().classes("w-full shadow-sm rounded-xl p-0 overflow-hidden"):
                with ui.row().classes("w-full items-center justify-between px-5 py-3 border-b border-gray-100 bg-white"):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes("w-2.5 h-2.5 rounded-full bg-[#6366F1]")
                        ui.label("Booking Details").classes("text-[13px] font-bold text-gray-800")
                    ui.label("Click 'Files Pending' or on 'Files Incomplete' to see details").classes("text-[11px] text-gray-400")
                booking_wrap = ui.element("div").classes("w-full overflow-x-auto").style("padding:0")

            with ui.card().classes("w-full shadow-sm rounded-xl p-0 overflow-hidden"):
                with ui.row().classes("w-full items-center justify-between px-5 py-3 border-b border-gray-100 bg-white"):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes("w-2.5 h-2.5 rounded-full bg-[#10B981]")
                        ui.label("Delivery Details").classes("text-[13px] font-bold text-gray-800")
                delivery_wrap = ui.element("div").classes("w-full overflow-x-auto").style("padding:0")

            # Initial build
            _rebuild("custom", today_str, today_str)

            # Link controls
            range_select.on_value_change(lambda e: (
                custom_range_row.set_visibility(e.value == "custom"),
                _rebuild(e.value, from_inp.value, to_inp.value)
            ))
            from_inp.on_value_change(lambda e: _rebuild(range_select.value, e.value, to_inp.value))
            to_inp.on_value_change(lambda e: _rebuild(range_select.value, from_inp.value, e.value))
