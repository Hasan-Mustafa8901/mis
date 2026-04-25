# reports/complaint_flash_report.py
from services.complaints.report.base_report import BaseReport
import time

def timer_dec(base_fn):
    def enhanced_fn(*args,**kwargs):
        start = time.time()
        result = base_fn(*args, **kwargs)
        end = time.time()
        print(f"Time taken= {end-start} seconds.")
        return result
    return enhanced_fn


class ComplaintFlashReport(BaseReport):

        PAGE_HEIGHT = 297
        FOOTER_HEIGHT = 30
        BOTTOM_MARGIN = 20
        MAX_Y = PAGE_HEIGHT - BOTTOM_MARGIN - FOOTER_HEIGHT

        def ensure_one_pager(self):
                if self.get_y() > self.MAX_Y:
                        raise ValueError(
                                "Flash Report exceeds. Please shorten the content."
                        )
                
        def draw_footer_block(self, data):
               self.set_y(self.MAX_Y + 5) # Jump to reserved footer zone

               self.set_font('Times','B', 10)
               self.cell(0, 6, 'Prepared by:', ln=0)
               self.cell(0, 6, 'Reviewed by:', align='R', ln=True)

               self.ln(4)

               self.set_font('Times', size=10)
               self.cell(0, 6, data['complainant_aa'])
               self.cell(0, 6, data['reviewer'] or 'CA Sahil Dua', align='R',ln=True)

               self.set_font('Times', 'B', 9)
               self.cell(0, 4, data['complainant_aa_designation'] or '(Audit Assistant)')
               self.cell(0, 4, data['reviewer_designation'] or '(Project Lead)', align='R')
        
        @timer_dec
        def build(self, data: dict):
                self.add_page()

                self.ln(1)
                # Complaint meta
                self.key_value_row("Complaint No", data["complaint_no"])
                self.key_value_row("Date of Complaint", data["date_of_complaint"])
                self.key_value_row("Date of Resolution", data["date_of_resolution"])

                # Details of Complaint
                self.section_title("1. Details of Complaint")
                self.key_value_row("Dealer", data["dealer"])
                self.key_value_row("Showroom", data["showroom"])
                self.key_value_row("Point of Complaint", data["point_of_complaint"])
                self.key_value_row("Booking Date", data["booking_date"])
                self.key_value_row("Complainant Name", data["complainant_name"])
                self.key_value_row("Designation of Complainant", data["designation_complainant"])
                self.key_value_row("Customer Name", data["customer_name"])
                self.key_value_row("Car Name", data["car_name"])
                self.key_value_row("Price Offered by Complainant", data["price_offered"])
                self.key_value_row("Name of Audit Assistant (AA) stationed at Complainant", data["complainant_aa"])

                # Audit sections
                self.section_title("2. Audit Procedure")
                self.section_content(data["audit_procedure"])
                self.ensure_one_pager()

                self.section_title("3. Audit Findings")
                self.section_content(data["audit_findings"])
                self.ensure_one_pager()

                self.section_title("4. Audit Evidence")
                self.section_content(data["audit_evidence"])
                self.ensure_one_pager()

                self.section_title("5. Conclusion")
                self.section_content(data["conclusion"])
                self.ensure_one_pager()

                self.draw_footer_block(data)

                # self.ln(10)
                # self.set_font(family="Times",style="B")
                # self.cell(0, 8, "Prepared by:")
                # self.cell(0, 8, "Reviewed by:",align="R",ln=True)
                # self.ln(4)
                # self.set_font(family="Times")
                # self.cell(0, 8, f"{data["complainant_aa"]}")
                # self.cell(0,8,data["reviewer"] or "CA Sahil Dua",align="R",ln=True)
                # self.set_font(family="Times",style="B")
                # self.cell(0,2, data["complainant_aa_designation"] or "(Audit Assitant)")
                # self.cell(0,2, data["reviewer_designation"] or "(Project Lead)",align="R")