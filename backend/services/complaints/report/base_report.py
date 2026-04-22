# reports/base_report.py
from fpdf import FPDF
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
ASSET_DIR = BASE_DIR / "assets"
LETTER_HEAD = ASSET_DIR / "letter_head.png"

class BaseReport(FPDF):
    def __init__(self,) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")

        # Define margins
        self.set_left_margin(15)
        self.set_right_margin(15)
        # self.set_top_margin(40)
        self.set_auto_page_break(auto=False, margin=20)

    def header(self):
        if LETTER_HEAD.exists():
            self.image(str(LETTER_HEAD), x=15, y=10, w=180)
        else:
            print(f"Letterhead missing at {LETTER_HEAD}")
        self.ln(30)
        self.set_font("Times", "BU", 14)
        self.cell(0, 10, "Flash Report (Complaint & Resolution Summary)", ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-10)
        self.set_font("Times", size=8)
        self.cell(0, 8, f"Generated on {datetime.now().strftime('%d-%m-%Y')}", align="C")

    def section_title(self, title):
        self.ln(2)
        self.set_font("Times", "BU", 12)
        self.cell(0, 8, title, ln=True)
        self.ln(1)

    def section_content(self, text):
        # self.ln(2)
        self.set_font("Times",size=10)
        self.multi_cell(0,5, text=text)
        # self.ln(1)

    def key_value_row(self, key, value):
        self.set_font("Times", "", 10)
        self.cell(90, 6, key, border=1)
        self.cell(0, 6, value or "-",align="C", border=1, ln=True)
    
