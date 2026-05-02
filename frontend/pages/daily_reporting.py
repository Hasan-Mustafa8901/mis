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

    row_data: dict = {}
    dialog_data: dict = {}
    label_refs: dict = {}
    total_refs: dict = {}

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
        return {(t.get(field) or "")[:10] for t in all_transactions if (t.get(field) or "")[:10]}

    def compute_row(tt: str, d: str) -> dict:
        s = row_data.get((tt, d), {})
        tc = int(s.get("total_count", 0) or 0)
        fr = int(s.get("files_received", 0) or 0)
        fi = len(dialog_data.get((tt, d, "files_incomplete"), []))
        fm = mis_count(tt, d)
        fp = max(0, tc - fr)
        fv = int(s.get("files_verified", 0) or 0)
        diff = fv - fm
        return dict(tc=tc, fr=fr, fi=fi, fm=fm, fp=fp, fv=fv, diff=diff)

    def recompute_totals(tt: str, dates: list) -> None:
        sums = {c: 0 for c in ["tc", "fr", "fp", "fi", "fv", "fm", "diff"]}
        for d in dates:
            r = compute_row(tt, d)
            for k in sums: sums[k] += r[k]
        for col, key in zip(["total_count", "files_received", "files_pending", "file_incomplete", "files_verified", "files_in_mis", "difference"], ["tc", "fr", "fp", "fi", "fv", "fm", "diff"]):
            lbl = total_refs.get((tt, col))
            if lbl: lbl.set_text(str(sums[key]))

    def refresh_computed_row(tt: str, d: str, dates: list) -> None:
        r = compute_row(tt, d)
        for col, val in [("files_pending", r["fp"]), ("file_incomplete", r["fi"]), ("files_verified", r["fv"]), ("difference", r["diff"])]:
            lbl = label_refs.get((tt, d, col))
            if not lbl: continue
            lbl.set_text(str(val))
        recompute_totals(tt, dates)

    # Simplified table builder for cleaner look
    def build_table(tt: str, dates: list, parent) -> None:
        with parent:
            with ui.element("table").classes("w-full border-collapse bg-white"):
                with ui.element("thead"):
                    with ui.element("tr").classes("bg-gray-50 border-b border-gray-200"):
                        for h in ["Date", "Total Count", "Files Received", "Pending", "Incomplete", "Verified", "In MIS", "Diff"]:
                            ui.element("th").classes("px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase tracking-wider").set_text(h)
                with ui.element("tbody"):
                    for d in dates:
                        r = compute_row(tt, d)
                        with ui.element("tr").classes("border-b border-gray-100 hover:bg-gray-50 transition-colors"):
                            ui.element("td").classes("px-4 py-3 text-sm font-medium text-gray-700").set_text(d)
                            # inputs would go here, using labels for display for now in this refactor
                            ui.element("td").classes("px-4 py-3 text-sm mono").set_text(str(r["tc"]))
                            ui.element("td").classes("px-4 py-3 text-sm mono").set_text(str(r["fr"]))

                            fp_lbl = ui.element("td").classes("px-4 py-3 text-sm mono font-bold")
                            fp_lbl.set_text(str(r["fp"]))
                            label_refs[(tt, d, "files_pending")] = fp_lbl

                            fi_lbl = ui.element("td").classes("px-4 py-3 text-sm mono font-bold")
                            fi_lbl.set_text(str(r["fi"]))
                            label_refs[(tt, d, "file_incomplete")] = fi_lbl

                            ui.element("td").classes("px-4 py-3 text-sm mono").set_text(str(r["fv"]))
                            ui.element("td").classes("px-4 py-3 text-sm mono").set_text(str(r["fm"]))

                            diff_lbl = ui.element("td").classes("px-4 py-3 text-sm mono font-bold")
                            diff_lbl.set_text(str(r["diff"]))
                            label_refs[(tt, d, "difference")] = diff_lbl
                with ui.element("tfoot"):
                    with ui.element("tr").classes("bg-gray-100 font-bold"):
                        ui.element("td").classes("px-4 py-3 text-sm").set_text("TOTAL")
                        for col in ["total_count", "files_received", "files_pending", "file_incomplete", "files_verified", "files_in_mis", "difference"]:
                            lbl = ui.element("td").classes("px-4 py-3 text-sm mono")
                            lbl.set_text("0")
                            total_refs[(tt, col)] = lbl
        recompute_totals(tt, dates)

    with ui.row().classes("w-full no-wrap items-stretch min-h-[calc(100vh-52px)]"):
        with ui.column().classes("w-[240px] shrink-0 bg-white border-r border-gray-200 py-4 sticky top-[52px] h-[calc(100vh-52px)]"):
            sidebar()

        with ui.column().classes("flex-1 min-w-0 p-8 bg-[#F8F9FC] gap-8"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-1"):
                    ui.label("Daily Operations Report").classes("text-2xl font-bold text-gray-900")
                    ui.label("Audit file tracking and reconciliation").classes("text-sm text-gray-500")

            with ui.card().classes("w-full p-0 overflow-hidden rounded-xl shadow-sm border-none"):
                ui.label("Booking Status").classes("px-6 py-4 text-lg font-bold border-b border-gray-100")
                b_wrap = ui.element("div")
                build_table("booking", sorted(list(get_all_txn_dates("booking")) or [today_str], reverse=True)[:7], b_wrap)

            with ui.card().classes("w-full p-0 overflow-hidden rounded-xl shadow-sm border-none"):
                ui.label("Delivery Status").classes("px-6 py-4 text-lg font-bold border-b border-gray-100")
                d_wrap = ui.element("div")
                build_table("delivery", sorted(list(get_all_txn_dates("delivery")) or [today_str], reverse=True)[:7], d_wrap)
