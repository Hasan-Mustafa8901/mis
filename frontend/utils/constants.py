BASE_URL = "http://localhost:8000"
FORM_COLUMNS = 3

CONDITION_KEYS = [
    ("exchange", "Exchange"),
    ("corporate", "Corporate"),
    ("govt_employee", "Govt Employee"),
    ("scrap", "Scrap"),
    ("upgrade", "Upgrade"),
    ("self_insurance", "Self Insurance"),
    ("tr_case", "TR Case"),
    ("acc_kit", "Genuine Acc Kit"),
    ("fastag", "FasTag"),
    ("ext_warr", "Extended Warranty"),
    ("shield", "Shield Of Trust"),
]

DELIVERY_CHECK_KEYS = [
    ("customer_ledger", "Customer Ledger"),
    ("tax_invoice", "Tax Invoice"),
    ("accessories_indent", "Accessories Indent"),
    ("insurance", "Insurance"),
    ("rto", "RTO"),
    ("finance", "Finance"),
    ("evaluation_certificate", "Evaluation Certificate"),
]

BOOKING_CHECK_KEYS = [
    ("customer_kyc", "Customer KYC"),
    ("vehicle_details", "Vehicle Details"),
    ("price_quotation", "Price Quotation"),
    ("receipts", "Receipts"),
    ("accessories_indent", "Accessories Indent"),
    ("exchange_details", "Exchange Details"),
    ("md_reference", "MD Reference Approval"),
    ("corp_id", "Corp ID"),
    ("customer_sign", "Customer Sign"),
]

HEAD_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  body, .q-page {
    font-family: 'Inter', sans-serif !important;
    background: #F0F2F8 !important;
  }
  .mono { font-family: 'JetBrains Mono', monospace !important; }
  
  /* AG Grid Overrides */
  .ag-theme-alpine {
    --ag-font-family: 'Inter', sans-serif;
    --ag-header-background-color: #F8F9FC;
    --ag-odd-row-background-color: #FAFBFF;
  }
  
  /* Custom Scrollbar */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: #F0F2F8; }
  ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }
</style>
"""
