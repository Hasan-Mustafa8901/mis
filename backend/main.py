from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, SQLModel, select
from typing import List, Dict, Any
from datetime import date
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from db.session import engine, get_session
from db.models import (
    Transaction,
    Car,
    Variant,
    Outlet,
    Employee,
    DiscountComponent,
    Accessory,
    Dealership,
)
from services.ingestion.price_seed_service import PriceListIngestionService
from services.discount.discount_service import DiscountService
from services.transaction.transaction_service import TransactionService
from services.price_list.price_list_service import PriceListService
from services.auth.dependencies import get_current_user

from schemas.mis import DealershipCreate, EmployeeCreate, OutletCreate

from routes.edit_routes import router as edit_requests_router
from routes.auth_routes import router as auth_router
from routes.complaint_routes import router as complaints_router
from routes.daily_reporting_routes import router as daily_reporting_router

from rich import print


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    # Initial tables created via reset_db script but ensure metadata is ready
    SQLModel.metadata.create_all(engine)
    yield
    # Shutdown logic (optional)
    pass


app = FastAPI(title="Automobile Sales Audit MIS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(edit_requests_router)
app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(daily_reporting_router)  # daily reporting routes


@app.get("/")
def read_root():
    return {"message": "Automobile Sales Audit MIS API"}


@app.get("/cars", response_model=List[Car])
def api_list_cars(session: Session = Depends(get_session)):
    return session.exec(select(Car)).all()


@app.get("/variants", response_model=List[Variant])
def api_list_all_variants(session: Session = Depends(get_session)):
    return session.exec(select(Variant)).all()


@app.get("/cars/{car_id}/variants", response_model=List[Variant])
def api_list_variants(car_id: int, session: Session = Depends(get_session)):
    return session.exec(select(Variant).where(Variant.car_id == car_id)).all()


@app.get("/components")
def get_components(session: Session = Depends(get_session)):
    return PriceListService.get_all_components(session)


@app.post("/dealership")
def create_dealership(
    payload: DealershipCreate, session: Session = Depends(get_session)
):
    obj = Dealership(**payload.dict())

    try:
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return {"id": obj.id, "name": obj.name}
    except Exception:
        session.rollback()
        raise HTTPException(400, "Dealership with same name/code already exists")


@app.get("/dealerships")
def api_list_dealerships(session: Session = Depends(get_session)):
    dealerships = session.exec(select(Dealership)).all()
    return [{"id": d.id, "name": d.name} for d in dealerships]


@app.get("/outlets")
def api_list_outlets(session: Session = Depends(get_session)):
    outlets = session.exec(select(Outlet)).all()
    return [
        {"id": o.id, "name": o.name, "dealership_id": o.dealership_id} for o in outlets
    ]


@app.post("/outlets")
def create_outlet(payload: OutletCreate, session: Session = Depends(get_session)):

    # Validate dealership exists
    if not session.get(Dealership, payload.dealership_id):
        raise HTTPException(400, "Invalid dealership_id")

    obj = Outlet(**payload.dict())

    try:
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return {"id": obj.id, "name": obj.name}
    except Exception:
        session.rollback()
        raise HTTPException(400, "Outlet already exists")


@app.get("/sales-executives")
def api_list_sales_executives(session: Session = Depends(get_session)):
    executives = session.exec(select(Employee)).all()
    return [{"id": e.id, "name": e.name} for e in executives]


@app.post("/sales-executive")
def create_employee(payload: EmployeeCreate, session: Session = Depends(get_session)):

    # Validate outlet exists
    if not session.get(Outlet, payload.outlet_id):
        raise HTTPException(400, "Invalid outlet_id")

    obj = Employee(**payload.dict())

    session.add(obj)
    session.commit()
    session.refresh(obj)

    return {"id": obj.id, "name": obj.name}


@app.get("/price-list/preview")
def api_price_list_preview(
    variant_id: int,
    booking_date: date,
    model_year: int,
    session: Session = Depends(get_session),
):
    active_price_list = PriceListService.get_active_price_list(
        session, booking_date, model_year
    )
    print("\nActive Price List:", active_price_list)
    if not active_price_list:
        raise HTTPException(status_code=404, detail="Active Price List not found")

    allowed_amounts = PriceListService.get_allowed_amounts(
        session, active_price_list.id, variant_id, {}
    )
    print("\nAllowed Amounts:", allowed_amounts)

    result = {}
    comps = session.exec(
        select(DiscountComponent).where(
            (DiscountComponent.type == "price") | (DiscountComponent.type == "discount")
        )
    ).all()
    print("\nPrice Components in DB:", [c.name for c in comps])
    comp_map = {c.id: " ".join(c.name.split()) for c in comps}
    print("\nComponent ID to Name Map:", comp_map)

    for comp_id, amount in allowed_amounts.items():
        if comp_id in comp_map:
            name = comp_map[comp_id]
            result[name] = amount
    print("\nFinal Mapped Result:", result)

    return result


@app.post("/price-list/upload")
async def upload_price_list(
    file: UploadFile = File(...),
    sheet_name: str = Form("0"),
    model_year: int = Form(...),
    valid_from: date = Form(...),
    valid_to: date = Form(None),
    session: Session = Depends(get_session),
):
    # Save file temporarily
    file_path = f"tmp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        parsed_sheet = int(sheet_name) if sheet_name.isdigit() else sheet_name
        result = PriceListIngestionService.seed_from_excel(
            session,
            file_path,
            model_year,
            sheet_name=parsed_sheet,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        import os

        if os.path.exists(file_path):
            os.remove(file_path)


@app.delete("/transactions/{transaction_id}")
def delete_transaction_api(
    transaction_id: int,
    session: Session = Depends(get_session),
):
    return TransactionService.delete_transaction(session, transaction_id)


@app.post("/transactions/calculate")
def api_calculate_audit(
    transaction: Transaction,
    actual_amounts: Dict[str, float],
    conditions: Dict[str, bool],
    session: Session = Depends(get_session),
):
    try:
        result = DiscountService.calculate_discount(
            session, transaction, actual_amounts, conditions
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/transactions")
def api_create_transaction(
    payload: dict[str, Any],
    session: Session = Depends(get_session),
):

    stage = payload.get("stage", "booking")

    if stage == "booking":
        return TransactionService.create_booking_transaction(session, payload)

    elif stage == "delivery":
        return TransactionService.create_delivery_transaction(session, payload)

    else:
        raise HTTPException(status_code=400, detail="Invalid mode")


@app.put("/transactions/{transaction_id}")
def api_update_transaction(
    transaction_id: int,
    payload: dict[str, Any],
    session: Session = Depends(get_session),
):
    stage = payload.get("stage", "booking")

    if stage == "delivery":
        return TransactionService.convert_to_delivery(session, transaction_id, payload)

    else:
        raise HTTPException(status_code=400, detail="Invalid mode")


@app.post("/transactions/{transaction_id}/calculate")
def api_recalculate_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
):
    """
    Re-calculates the audit for an existing transaction.
    """
    try:
        # 1. Fetch Transaction
        tx = session.get(Transaction, transaction_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # 2. Reconstruct actual_amounts directly from the TransactionItems stored in DB
        # This is more reliable than using the 'recon' flat dict
        from db.models import TransactionItem

        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction_id
            )
        ).all()
        actual_amounts = {item.component_name: item.actual_amount for item in items}

        # 3. Run calculate_audit
        audit_result = DiscountService.calculate_discount(
            session=session,
            transaction=tx,
            actual_amounts=tx.get("actual_amounts", {}),
            conditions=tx.get("conditions", {}),
        )

        # 4. Update transaction again
        updated_tx = TransactionService.update_transaction_with_audit(
            session, transaction_id, audit_result
        )

        return {
            "id": updated_tx.id,
            "status": updated_tx.status,
            "summary": audit_result,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @app.get("/transactions")
# def get_all_transactions(
#     showroom_id: int | None,
#     dealership_id: int | None,
#     session: Session = Depends(get_session),
# ):
#     txs = session.exec(select(Transaction)).all()

#     return [
#         TransactionService.get_transaction_reconstruction(session, tx.id)
#         for tx in txs
#         if tx.id
#     ]


@app.get("/transactions")
def get_all_transactions(
    showroom_id: int | None = None,
    dealership_id: int | None = None,
    stage: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(Transaction)

    if showroom_id:
        stmt = stmt.where(Transaction.outlet_id == showroom_id)

    elif dealership_id:
        stmt = stmt.join(Outlet).where(Outlet.dealership_id == dealership_id)

    if stage:
        stmt = stmt.where(Transaction.stage == stage)

    txs = session.exec(stmt).all()

    return [
        TransactionService.get_transaction_reconstruction(session, tx.id)
        for tx in txs
        if tx.id
    ]


@app.get("/accessories")
def get_accessories(session: Session = Depends(get_session)):
    accs = session.exec(select(Accessory)).all()
    return accs


@app.get("/transactions/{transaction_id}")
def api_get_transaction(transaction_id: int, session: Session = Depends(get_session)):
    reconstruction = TransactionService.get_transaction_reconstruction(
        session, transaction_id
    )
    if not reconstruction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return reconstruction


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
