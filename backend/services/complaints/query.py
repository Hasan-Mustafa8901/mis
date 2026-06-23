from sqlmodel import Session, select, or_, func
from datetime import datetime, date
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

# Avoid conflicts with python built-ins
from db.models import (
    Dealership,
    Outlet,
    Complaint,
    User,
    UserRole,
    Customer,
    ComplaintStatus,
    ComplaintFlag,
    Remark,
    Variant,
)
from services.utils import get_ist_today, get_ist_now


def get_all_dealerships(session: Session):
    return session.exec(select(Dealership)).all()


def get_outlets_by_dealership(session: Session, dealership_name: str):
    dealer = session.exec(
        select(Dealership).where(Dealership.name == dealership_name)
    ).first()
    if dealer:
        return session.exec(
            select(Outlet.name).where(Outlet.dealership_id == dealer.id)
        ).all()
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

    complainant_outlet = (
        session.get(Outlet, complaint.complainant_outlet_id)
        if complaint.complainant_outlet_id
        else None
    )
    complainant_code = complainant_outlet.code if complainant_outlet else "X"

    complainee_outlet = (
        session.get(Outlet, complaint.complainee_outlet_id)
        if complaint.complainee_outlet_id
        else None
    )
    complainee_dealership = (
        session.get(Dealership, complaint.complainee_dealership_id)
        if complaint.complainee_dealership_id
        else None
    )

    if complainee_outlet:
        complainee_code = complainee_outlet.code
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


def add_history_event(complaint: Complaint, actor: str, description: str) -> None:

    history = list(complaint.history or [])
    print("HISTORY BEFORE APPEND:", len(complaint.history or []))

    history.append(
        {
            "actor": actor,
            "timestamp": get_ist_now().strftime("%d %b %I:%M %p"),
            "description": description,
        }
    )

    complaint.history = history
    print("HISTORY AFTER APPEND:", len(history))


def serialize_complaint_rows(c: Complaint):
    complaint_row = {
        "id": c.id,
        "complaint_code": c.complaint_code,
        "status": c.status,
        "customer_name": c.customer.name if c.customer else None,
        "customer_mobile": c.customer.mobile_number if c.customer else None,
        "date_of_complaint": c.date_of_complaint.isoformat()
        if c.date_of_complaint
        else None,
        "car_name": c.variant.car.name if c.variant and c.variant.car else None,
        "variant_name": c.variant.full_variant_name if c.variant else None,
        "complainant_dealership": (
            c.complainant_dealership.name if c.complainant_dealership else None
        ),
        "complainant_outlet": (
            c.complainant_outlet.name if c.complainant_outlet else None
        ),
        "complainee_dealership": (
            c.complainee_dealership.name if c.complainee_dealership else None
        ),
        "complainee_outlet": (
            c.complainee_outlet.name if c.complainee_outlet else None
        ),
        "raised_by": c.raised_by_user.name if c.raised_by else None,
        "raised_at": (c.raised_at.isoformat() if c.raised_at else None),
    }
    return complaint_row


def get_complaint_reconstruction(session: Session, complaint_id: int) -> dict:
    complaint = session.exec(
        select(Complaint)
        .where(Complaint.id == complaint_id)
        .options(
            joinedload(Complaint.customer),
            joinedload(Complaint.remark),
            joinedload(Complaint.complainant_dealership),
            joinedload(Complaint.complainant_outlet),
            joinedload(Complaint.complainee_dealership),
            joinedload(Complaint.complainee_outlet),
            joinedload(Complaint.variant).joinedload(Variant.car),
        )
    ).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    data = complaint.model_dump()

    # CUSTOMER
    if complaint.customer:
        data.update(
            {
                "customer_name": complaint.customer.name,
                "customer_mobile": complaint.customer.mobile_number,
                "customer_address": complaint.customer.address,
                "customer_city": complaint.customer.city,
                "customer_aadhar": complaint.customer.aadhar_number,
                "customer_pan": complaint.customer.pan_number,
                "customer_pin": complaint.customer.pin_code,
                "customer_email": complaint.customer.email,
                "customer_relative": complaint.customer.relative_name,
                "customer_other_id": complaint.customer.other_id,
            }
        )

    # REMARKS
    if complaint.remark:
        data.update(
            {
                "name_aa_complainee": complaint.remark.aa_complainee,
                "remarks_complainant": (complaint.remark.remarks_complainant),
                "remarks_complainant_aa": (complaint.remark.remarks_complainant_aa),
            }
        )

    # DEALERSHIPS
    data.update(
        {
            "complainant_dealer_name": (
                complaint.complainant_dealership.name
                if complaint.complainant_dealership
                else None
            ),
            "complainant_showroom_name": (
                complaint.complainant_outlet.name
                if complaint.complainant_outlet
                else None
            ),
            "complainee_dealer_name": (
                complaint.complainee_dealership.name
                if complaint.complainee_dealership
                else complaint.complainee_dealer_text
            ),
            "complainee_showroom_name": (
                complaint.complainee_outlet.name
                if complaint.complainee_outlet
                else complaint.complainee_showroom_text
            ),
        }
    )

    # VARIANT / CAR
    if complaint.variant:
        data.update(
            {
                "car_name": (
                    complaint.variant.car.name if complaint.variant.car else None
                ),
                "variant_name": (complaint.variant.full_variant_name),
            }
        )

    # DATES
    data["date_of_complaint"] = (
        complaint.date_of_complaint.isoformat() if complaint.date_of_complaint else None
    )

    data["quotation_date"] = (
        complaint.quotation_date.isoformat() if complaint.quotation_date else None
    )

    data["instrument_date"] = (
        complaint.instrument_date.isoformat() if complaint.instrument_date else None
    )

    # HISTORY

    data["history"] = complaint.history
    data["raised_at"] = complaint.raised_at.isoformat() if complaint.raised_at else None
    data["updated_at"] = (
        complaint.updated_at.isoformat()
        if getattr(complaint, "updated_at", None)
        else None
    )
    data["status"] = complaint.status
    data["flag"] = complaint.flag

    return data


# We need seperate setup for all the c
def query_complaints(session: Session, filters=None, offset=0, limit=50):
    try:
        query = select(Complaint).options(
            joinedload(Complaint.customer),
            joinedload(Complaint.remark),
            joinedload(Complaint.complainant_dealership),
            joinedload(Complaint.complainant_outlet),
            joinedload(Complaint.complainee_dealership),
            joinedload(Complaint.complainee_outlet),
            joinedload(Complaint.variant).joinedload(Variant.car),
        )
        if filters:
            if filters.get("dealer"):
                dealer_id = filters["dealer"]
                query = query.where(
                    or_(
                        Complaint.complainant_dealership_id == dealer_id,
                        Complaint.complainee_dealership_id == dealer_id,
                    )
                )
            if filters.get("outlet"):
                outlet_id = filters["outlet"]
                query = query.where(
                    or_(
                        Complaint.complainant_outlet_id == outlet_id,
                        Complaint.complainee_outlet_id == outlet_id,
                    )
                )
            if filters.get("status"):
                query = query.where(Complaint.status == filters["status"])

            if filters.get("from_date"):
                query = query.where(Complaint.raised_at >= filters["from_date"])
            if filters.get("to_date"):
                query = query.where(Complaint.raised_at <= filters["to_date"])

        total = len(session.exec(query).all())
        rows = session.exec(
            query.order_by(Complaint.raised_at).offset(offset).limit(limit)
        ).all()

        result = []
        for row in rows:
            item = row.model_dump()

            # Flatten customer details
            if row.customer:
                item["customer_name"] = row.customer.name
                item["customer_mobile"] = row.customer.mobile_number
                item["customer_address"] = row.customer.address
                item["customer_city"] = row.customer.city
                item["customer_aadhar"] = row.customer.aadhar_number
                item["customer_pan"] = row.customer.pan_number
                item["customer_pin"] = row.customer.pin_code
                item["customer_email"] = row.customer.email
                item["customer_relative"] = row.customer.relative_name
                item["customer_other_id"] = row.customer.other_id
            else:
                item["customer_name"] = None
                item["customer_mobile"] = None
                item["customer_address"] = None
                item["customer_city"] = None
                item["customer_pin"] = None

            # Flatten remarks
            if row.remark:
                item["name_aa_complainee"] = row.remark.aa_complainee
                item["remarks_complainant"] = row.remark.remarks_complainant
                item["remarks_complainant_aa"] = row.remark.remarks_complainant_aa

            else:
                item["remarks_complainant"] = None
                item["remarks_complainee_aa"] = None
                item["remark_admin"] = None

            # Flatten dealerships and outlets
            item["complainant_dealer_name"] = (
                row.complainant_dealership.name if row.complainant_dealership else None
            )
            item["complainant_showroom_name"] = (
                row.complainant_outlet.name if row.complainant_outlet else None
            )
            # For complainee: prefer FK name, fall back to plain-text override (e.g. "X")
            item["complainee_dealer_name"] = (
                row.complainee_dealership.name
                if row.complainee_dealership
                else row.complainee_dealer_text
            )
            item["complainee_showroom_name"] = (
                row.complainee_outlet.name
                if row.complainee_outlet
                else row.complainee_showroom_text
            )

            # Flatten car_color
            item["car_color"] = row.car_color

            # Flatten Quotation and Booking details
            item["quotation_number"] = row.quotation_number
            item["quotation_date"] = row.quotation_date if row.quotation_date else None
            item["tcs_amount"] = row.tcs_amount if row.tcs_amount else None
            item["total_offered_price"] = row.total_offered_price
            item["net_offered_price"] = row.net_offered_price

            # Flatten booking details
            item["booking_file_number"] = row.booking_file_number
            item["receipt_number"] = row.receipt_number
            item["booking_amount"] = row.booking_amount
            item["mode_of_payment"] = row.mode_of_payment
            item["instrument_date"] = (
                row.instrument_date if row.instrument_date else None
            )
            item["instrument_number"] = row.instrument_number
            item["bank_name"] = row.bank_name

            item["date_of_complaint"] = (
                row.date_of_complaint.isoformat() if row.date_of_complaint else None
            )

            # Not Needed To be deleted later on
            # Flatten price info
            item["ex_showroom_price"] = row.ex_showroom_price
            item["insurance"] = row.insurance
            item["registration_road_tax"] = row.registration_road_tax
            item["discount"] = row.discount
            item["accessories_charged"] = row.accessories_charged

            # Flatten car model and variant
            if row.variant:
                item["car_name"] = row.variant.car.name if row.variant.car else None
                item["variant_name"] = row.variant.full_variant_name
            else:
                item["car_name"] = None
                item["variant_name"] = None

            result.append(item)

        return result, total
    except Exception as e:
        print("ERROR:", str(e))


def get_complaints_per_status(session: Session):
    today = get_ist_today()
    current_year, current_month = today.year, today.month

    complaints = session.exec(select(Complaint)).all()
    # Basic filtering in python since extract functions vary with DB dialect
    filtered = [
        c
        for c in complaints
        if c.raised_at
        and c.raised_at.year == current_year
        and c.raised_at.month == current_month
    ]

    return {
        "total": len(filtered),
        "escalated": len(
            [c for c in filtered if c.status == ComplaintStatus.ESCALATED]
        ),
        "unresolved": len(
            [c for c in filtered if c.status == ComplaintStatus.UNRESOLVED]
        ),
        "resolved": len([c for c in filtered if c.status == ComplaintStatus.RESOLVED]),
        "pending_complainee": len(
            [c for c in filtered if c.status == ComplaintStatus.PENDING_WITH_COMPLAINEE]
        ),
        "pending_team": len(
            [
                c
                for c in filtered
                if c.status == ComplaintStatus.PENDING_WITH_COMPLAINEE_STATION_TEAM
            ]
        ),
    }


def update_complaint_status(
    session: Session, complaint_code: str, status: ComplaintStatus, current_user: User
):
    complaint = session.exec(
        select(Complaint).where(Complaint.complaint_code == complaint_code)
    ).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    add_history_event(
        complaint,
        current_user.name,
        description=f"Status updated to {ComplaintStatus(status).title()}",
    )

    complaint.status = status
    session.add(complaint)
    session.commit()
    session.refresh(complaint)

    return complaint


def update_complaint_flag(
    session: Session, complaint_code: str, flag: ComplaintFlag, current_user: User
):
    complaint = session.exec(
        select(Complaint).where(Complaint.complaint_code == complaint_code)
    ).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    add_history_event(
        complaint,
        current_user.name,
        description=f"Flag Updated to {ComplaintFlag(flag).title()}",
    )

    complaint.flag = flag
    session.add(complaint)

    print(
        f"UPDATE COMPLAINT FLAG CALLED\nLENGTH OF UPDATED HISTORY LIST: {len(complaint.history)}"
    )
    session.commit()
    session.refresh(complaint)

    return complaint


def get_complaint_flags():
    return [{"label": flag.name, "value": flag.value} for flag in ComplaintFlag]


def get_complaint_status():
    return [{"label": status.name, "value": status.value} for status in ComplaintStatus]


def submit_remarks(
    session: Session, remark: str, code: str, submitted_by: UserRole, user: User
) -> bool:
    if not remark or not code:
        return False

    now = get_ist_now().strftime("%d %b %I:%M %p")
    complaint = session.exec(
        select(Complaint).where(Complaint.complaint_code == code)
    ).first()

    if not complaint:
        return False

    if submitted_by == UserRole.ADMIN:
        complaint.remark_admin = remark
    elif submitted_by == UserRole.AUDIT_ASST:
        new_entry = f"{user.name} ({now}): {remark}" if user.name else remark
        if complaint.remark_complainee_aa is None:
            complaint.remark_complainee_aa = new_entry
        else:
            complaint.remark_complainee_aa += f"\\n{new_entry}"
    else:
        return False

    add_history_event(complaint, user.name, description=remark)

    session.add(complaint)
    session.commit()
    return True


def get_dealership_id_by_name(session: Session, name: str):
    if not name:
        return None
    dealer = session.exec(select(Dealership).where(Dealership.name == name)).first()
    return dealer.id if dealer else None


def get_dealership_by_outlet(session: Session, name_or_id: str | int) -> dict:
    if isinstance(name_or_id, int):
        outlet = session.get(Outlet, name_or_id)
    else:
        outlet = session.exec(
            select(Outlet).where(Outlet.name == str(name_or_id).strip())
        ).first()

    if not outlet:
        return None

    # FIND DEALERSHIP
    dealership = session.get(Dealership, outlet.dealership_id)
    if not dealership:
        return None

    return {"id": dealership.id, "name": dealership.name}


def normalize_outlet_name(value: str) -> str:
    return (
        str(value).strip().lower().replace("–", "-").replace("—", "-").replace(" ", "")
    )


def get_outlet_id_by_name(
    session: Session, name: str, dealership_id: int | None = None
):

    if not name:
        return None

    cleaned = normalize_outlet_name(name)
    outlets = session.exec(select(Outlet)).all()

    for outlet in outlets:
        db_name = normalize_outlet_name(outlet.name)

        if db_name == cleaned:
            if dealership_id and outlet.dealership_id != dealership_id:
                continue

            return outlet.id

    return None


def save_complaint(session: Session, data: dict, user: User):
    try:
        # 1. Safely parse incoming string dates to date objects before writing to DB
        if isinstance(data.get("quotation_date"), str):
            data["quotation_date"] = date.fromisoformat(data["quotation_date"])

        if isinstance(data.get("instrument_date"), str):
            data["instrument_date"] = date.fromisoformat(data["instrument_date"])

        # 'date_of_complaint' is also required to be a date object
        if isinstance(data.get("date_of_complaint"), str):
            data["date_of_complaint"] = date.fromisoformat(data["date_of_complaint"])
        # --- Customer ---
        c = data.get("customer_details", {})
        if (
            not c
            or not c.get("customer_name")
            or not c.get("contact_number")
            or not c.get("address")
        ):
            return False, "Customer Details are required."

        customer = Customer(
            name=c["customer_name"],
            relative_name=c.get("relative_name"),
            other_id=c.get("other_id"),
            email=c.get("email"),
            mobile_number=c["contact_number"],
            pan_number=c.get("pan"),
            aadhar_number=c.get("aadhar"),
            address=c["address"],
            city=c.get("city"),
            pin_code=c.get("pin"),
        )
        session.add(customer)
        session.flush()  # assign id without committing transaction yet

        # --- Remark ---
        r = data.get("remarks_page", {})
        remark_id = None
        if r:
            remark = Remark(
                id=f"R-{customer.id}",
                remarks_complainant=r.get("remarks_by_complainant"),
                remarks_complainant_aa=r.get("remarks_by_aa"),
                aa_complainee=r.get("aa_name"),
            )
            session.add(remark)
            session.flush()
            remark_id = remark.id

        # --- Complaint ---
        d = data.get("dealer_showroom_details", {})
        if not d.get("complainant_dealership") or not d.get("complainant_showroom"):
            return (
                False,
                "Dealership Details not provided (Enter your Dealership and Showroom)",
            )

        complainee_dealer_name_raw = d.get("complainee_dealership")
        complainee_showroom_name_raw = d.get("complainee_showroom")

        complainant_dealership_id = get_dealership_id_by_name(
            session, d.get("complainant_dealership")
        )
        complainant_outlet_id = get_outlet_id_by_name(
            session, d.get("complainant_showroom"), complainant_dealership_id
        )

        # For complainee: if "X" or not a real dealership, store as plain text
        complainee_dealership_id = None
        complainee_outlet_id = None
        complainee_dealer_text = None
        complainee_showroom_text = None

        if complainee_dealer_name_raw and complainee_dealer_name_raw != "X":
            complainee_dealership_id = get_dealership_id_by_name(
                session, complainee_dealer_name_raw
            )
            if not complainee_dealership_id:
                complainee_dealer_text = complainee_dealer_name_raw
        elif complainee_dealer_name_raw == "X":
            complainee_dealer_text = "X"

        if complainee_showroom_name_raw and complainee_showroom_name_raw != "X":
            complainee_outlet_id = get_outlet_id_by_name(
                session, complainee_showroom_name_raw, complainee_dealership_id
            )
            if not complainee_outlet_id:
                complainee_showroom_text = complainee_showroom_name_raw
        elif complainee_showroom_name_raw == "X":
            complainee_showroom_text = "X"

        date_of_complaint_str = data.get("remarks_page", {}).get(
            "complaint_raised_date"
        )
        comp_date = None
        if date_of_complaint_str:
            if isinstance(date_of_complaint_str, str):
                try:
                    comp_date = datetime.strptime(
                        date_of_complaint_str, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    comp_date = get_ist_today()
            else:
                comp_date = date_of_complaint_str
        else:
            comp_date = get_ist_today()

        v = data.get("vehicle_details", {})
        q = data.get("quotation_details", {})
        b = data.get("booking_details", {})
        p = data.get("price_info", {})

        complaint = Complaint(
            complainant_dealership_id=complainant_dealership_id,
            complainant_outlet_id=complainant_outlet_id,
            complainee_dealership_id=complainee_dealership_id,
            complainee_outlet_id=complainee_outlet_id,
            complainee_dealer_text=complainee_dealer_text,
            complainee_showroom_text=complainee_showroom_text,
            employee_id=data.get("employee_id"),
            customer_id=customer.id,
            remark_id=remark_id,
            raised_by=user.id,
            date_of_complaint=comp_date,
            # Vehicle
            variant_id=data.get("variant_id"),
            vin_number=v.get("vin_number"),
            engine_number=v.get("engine_number"),
            registration_number=v.get("registration_number"),
            registration_date=v.get("registration_date"),
            car_color=v.get("car_color"),
            # Quotation
            quotation_number=q.get("quotation_number"),
            quotation_date=q.get("quotation_date"),
            tcs_amount=q.get("tcs_amount", 0),
            total_offered_price=q.get("total_offered_price", 0),
            net_offered_price=q.get("net_offered_price", 0),
            # Booking
            booking_file_number=b.get("booking_file_number"),
            receipt_number=b.get("receipt_number"),
            booking_amount=b.get("booking_amount", 0),
            mode_of_payment=b.get("mode_of_payment"),
            instrument_date=b.get("instrument_date"),
            instrument_number=b.get("instrument_number"),
            bank_name=b.get("bank_name"),
            # Price Info
            ex_showroom_price=p.get("ex_showroom_price", 0),
            insurance=p.get("insurance", 0),
            registration_road_tax=p.get("registration_road_tax", 0),
            discount=p.get("discount", 0.0),
            accessories_charged=p.get("accessories_charged", 0),
        )

        code, serial = generate_complaint_code(session, complaint)
        complaint.complaint_code = code

        description = f"Remarks by Complainant: {r.get('remarks_by_complainant')}<br>Remarks by Stationed AA: {r.get('remarks_by_aa')}"
        add_history_event(complaint, user.name, description=description)

        session.add(complaint)
        session.commit()

        return True, code

    except Exception as e:
        session.rollback()
        return False, str(e)
