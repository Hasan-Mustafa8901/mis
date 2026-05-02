from nicegui import ui, app
from utils.constants import HEAD_HTML

# Import pages to register routes
from pages.login import login_page
from pages.dashboard import dashboard_page
from pages.daily_reporting import daily_reporting_page
from pages.mis import booking_mis_page, delivery_mis_page, complaints_table_page
from pages.form import form_page
from pages.complaint import complaint_form_page

# Global Styles
ui.add_head_html(HEAD_HTML, shared=True)
ui.add_head_html(
    """
<style>
.sticky-col {
    position: sticky;
    left: 0;
    background: white;
    z-index: 1;
}
/* Ensure cards have a consistent shadow */
.shadow-sm {
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
}
/* Refined rounded corners */
.rounded-xl {
    border-radius: 12px !important;
}
</style>
""",
    shared=True,
)

if __name__ in {"__main__", "__mp_main__"}:
    app.colors(primary="#e8402a")
    ui.run(
        title="AutoAudit MIS",
        favicon="🚗",
        host="0.0.0.0",
        storage_secret="super-secret-key-123",
        reload=True,
        port=3000,
    )
