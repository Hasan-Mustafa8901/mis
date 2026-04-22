from sqlmodel import Session, select, or_, and_, func, cast
from datetime import date, datetime
import pandas as pd
from sqlalchemy.orm import aliased
# Avoid conflicts with python built-ins
from db.models import Dealership, Outlet, Complaint, User, Customer, Transaction, DailyBooking, DailyDelivery, ComplaintStatus, ComplaintFlag, Remark
from services.utils import get_ist_today, get_ist_now

def get_all_dealerships(session: Session):
    return session.exec(select(Dealership)).all()

def get_outlets_by_dealership(session: Session, dealership_name: str):
    dealer = session.exec(select(Dealership).where(Dealership.name == dealership_name)).first()
    if dealer:
        return session.exec(select(Outlet.name).where(Outlet.dealership_id == dealer.id)).all()
    return []

def get_dealership_name_by_outlet_id(session: Session, outlet_id: int) -> str | None:
    result = session.exec(
        select(Dealership.name)
        .join(Outlet, Outlet.dealership_id == Dealership.id)
        .where(Outlet.id == outlet_id)
    ).first()
    return result

def generate_complaint_code(session: Session, complaint: Complaint):
    month = get_ist_now().month

    complainant_outlet = session.get(Outlet, complaint.complainant_outlet_id) if complaint.complainant_outlet_id else None
    complainant_code = complainant_outlet.name if complainant_outlet else "NA"

    complainee_outlet = session.get(Outlet, complaint.complainee_outlet_id) if complaint.complainee_outlet_id else None
    complainee_dealership = session.get(Dealership, complaint.complainee_dealership_id) if complaint.complainee_dealership_id else None

    if complainee_outlet:
        complainee_code = complainee_outlet.name
    elif complainee_dealership:
        complainee_code = str(complainee_dealership.name).split()[0] + "-X"
    else:
        complainee_code = "X"

    if complainant_outlet:
        last_month = complainant_outlet.last_serial_month or 0
        if last_month != month:
            complainant_outlet.last_serial_no = 1
            complainant_outlet.last_serial_month = month
        else:
            complainant_outlet.last_serial_no += 1
        serial_no = complainant_outlet.last_serial_no
    else:
        serial_no = 0

    code = f"{month:02d}/{complainant_code}/{complainee_code}/{serial_no}"
    return code, serial_no

def query_complaints(session: Session, filters=None, offset=0, limit=50):
    query = select(Complaint)
    if filters:
        if filters.get("dealer"):
            dealer_id = filters["dealer"]
            query = query.where(
                or_(Complaint.complainant_dealership_id == dealer_id,
                    Complaint.complainee_dealership_id == dealer_id)
            )
        if filters.get("outlet"):
            outlet_id = filters["outlet"]
            query = query.where(
                or_(Complaint.complainant_outlet_id == outlet_id,
                    Complaint.complainee_outlet_id == outlet_id)
            )
        if filters.get("status"):
            query = query.where(Complaint.status == filters["status"])

        if filters.get("from_date"):
            query = query.where(Complaint.raised_at >= filters["from_date"])
        if filters.get("to_date"):
            query = query.where(Complaint.raised_at <= filters["to_date"])

    total = len(session.exec(query).all())
    rows = session.exec(query.order_by(Complaint.raised_at).offset(offset).limit(limit)).all()
    return rows, total

def get_complaints_per_status(session: Session):
    today = get_ist_today()
    current_year, current_month = today.year, today.month
    
    complaints = session.exec(select(Complaint)).all()
    # Basic filtering in python since extract functions vary with DB dialect
    filtered = [c for c in complaints if c.raised_at and c.raised_at.year == current_year and c.raised_at.month == current_month]

    return {
        "total": len(filtered),
        "escalated": len([c for c in filtered if c.status == ComplaintStatus.ESCALATED]),
        "unresolved": len([c for c in filtered if c.status == ComplaintStatus.UNRESOLVED]),
        "resolved": len([c for c in filtered if c.status == ComplaintStatus.RESOLVED]),
        "pending_complainee": len([c for c in filtered if c.status == ComplaintStatus.PENDING_WITH_COMPLAINEE]),
        "pending_team": len([c for c in filtered if c.status == ComplaintStatus.PENDING_WITH_COMPLAINEE_STATION_TEAM]),
    }

def submit_remarks(session: Session, remark: str, code: str, submitted_by: str, complainee_name: str | None = None) -> bool:
    if not remark or not code: return False

    now = get_ist_now().strftime("%d %b %I:%M %p")
    complaint = session.exec(select(Complaint).where(Complaint.complaint_code == code)).first()
    
    if not complaint:
        return False

    if submitted_by == "admin":
        complaint.remark_admin = remark
    elif submitted_by == "complainee":
        new_entry = f"{complainee_name} ({now}): {remark}" if complainee_name else remark
        if complaint.remark_complainee_aa is None:
            complaint.remark_complainee_aa = new_entry
        else:
            complaint.remark_complainee_aa += f"\\n{new_entry}"
    else:
        return False
        
    session.add(complaint)
    session.commit()
    return True

def get_dealership_id_by_name(session: Session, name: str):
    if not name: return None
    dealer = session.exec(select(Dealership).where(Dealership.name == name)).first()
    return dealer.id if dealer else None

def get_outlet_id_by_name(session: Session, name: str, dealership_id: int = None):
    if not name: return None
    query = select(Outlet).where(Outlet.name == name)
    if dealership_id:
        query = query.where(Outlet.dealership_id == dealership_id)
    outlet = session.exec(query).first()
    return outlet.id if outlet else None

def save_complaint(session: Session, data: dict):
    try:
        # --- Customer ---
        c = data.get("customer_details", {})
        if not c or not c.get("customer_name") or not c.get("contact_number") or not c.get("address"):
            return False, "Customer Details are required."
        
        customer = Customer(
            name=c["customer_name"],
            mobile_number=c["contact_number"],
            pan_number=c.get("pan"),
            aadhar_number=c.get("aadhar"),
            address=c["address"],
            city=c.get("city"),
            pin_code=c.get("pin")
        )
        session.add(customer)
        session.flush() # assign id without committing transaction yet

        # --- Remark ---
        r = data.get("remarks_page", {})
        remark_id = None
        if r:
            remark = Remark(
                id=f"R-{customer.id}",
                remarks_complainant=r.get("remarks_by_complainant"),
                remarks_complainant_aa=r.get("aa_name"),
                aa_complainee=r.get("remarks_by_aa")
            )
            session.add(remark)
            session.flush()
            remark_id = remark.id

        # --- Complaint ---
        d = data.get("dealer_showroom_details", {})
        if not d.get("complainant_dealership") or not d.get("complainant_showroom"):
            return False, "Dealership Details not provided (Enter your Dealership and Showroom)"
            
        complainant_dealership_id = get_dealership_id_by_name(session, d.get('complainant_dealership'))
        complainee_dealership_id = get_dealership_id_by_name(session, d.get('complainee_dealership'))
        complainant_outlet_id = get_outlet_id_by_name(session, d.get('complainant_showroom'), complainant_dealership_id)
        complainee_outlet_id = get_outlet_id_by_name(session, d.get('complainee_showroom'), complainee_dealership_id)
        
        date_of_complaint_str = data.get("remarks_page", {}).get("complaint_raised_date")
        comp_date = None
        if date_of_complaint_str:
            if isinstance(date_of_complaint_str, str):
                try:
                    comp_date = datetime.strptime(date_of_complaint_str, "%Y-%m-%d").date()
                except ValueError:
                    comp_date = get_ist_today()
            else:
                comp_date = date_of_complaint_str
        else:
            comp_date = get_ist_today()
        
        complaint = Complaint(
            complainant_dealership_id=complainant_dealership_id,
            complainant_outlet_id=complainant_outlet_id,
            complainee_dealership_id=complainee_dealership_id,
            complainee_outlet_id=complainee_outlet_id,
            customer_id=customer.id,
            remark_id=remark_id,
            raised_by=data.get("employee_id"),
            date_of_complaint=comp_date
        )
        
        code, serial = generate_complaint_code(session, complaint)
        complaint.complaint_code = code
        
        session.add(complaint)
        session.commit()

        return True, code
        
    except Exception as e:
        session.rollback()
        return False, str(e)
