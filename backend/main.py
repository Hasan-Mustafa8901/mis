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
)
from services.ingestion.price_seed_service import PriceListIngestionService
from services.discount.discount_service import DiscountService
from services.transaction.transaction_service import TransactionService
from services.price_list.price_list_service import PriceListService

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


@app.get("/")
def read_root():
    return {"message": "Automobile Sales Audit MIS API"}


@app.get("/cars", response_model=List[Car])
def api_list_cars(session: Session = Depends(get_session)):
    return session.exec(select(Car)).all()


@app.get("/cars/{car_id}/variants", response_model=List[Variant])
def api_list_variants(car_id: int, session: Session = Depends(get_session)):
    return session.exec(select(Variant).where(Variant.car_id == car_id)).all()


@app.get("/components")
def get_components(session: Session = Depends(get_session)):
    return PriceListService.get_all_components(session)


@app.get("/outlets")
def api_list_outlets(session: Session = Depends(get_session)):
    outlets = session.exec(select(Outlet)).all()
    return [{"id": o.id, "name": o.name} for o in outlets]


@app.get("/sales-executives")
def api_list_sales_executives(session: Session = Depends(get_session)):
    executives = session.exec(select(Employee)).all()
    return [{"id": e.id, "name": e.name} for e in executives]


@app.get("/price-list/preview")
def api_price_list_preview(
    variant_id: int, booking_date: date, session: Session = Depends(get_session)
):
    active_price_list = PriceListService.get_active_price_list(session, booking_date)
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


@app.post("/transactions/calculate")
def api_calculate_audit(
    variant_id: int,
    booking_date: date,
    actual_amounts: Dict[str, float],
    conditions: Dict[str, bool],
    session: Session = Depends(get_session),
):
    try:
        result = DiscountService.calculate_discount(
            session, variant_id, booking_date, actual_amounts, conditions
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/transactions")
def api_create_transaction(
    payload: Dict[str, Any],
    session: Session = Depends(get_session),
):
    try:
        result = TransactionService.create_full_transaction(session, payload)
        return result

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


# @app.post("/transactions")
# def api_create_transaction(
#     payload: Dict[str, Any],
#     session: Session = Depends(get_session),
# ):
#     """
#     Creates a full MIS transaction following the correct workflow:
#     1. Create RAW transaction data first.
#     2. Perform discount audit.
#     3. Update transaction + items with audit results.
#     """
#     try:
#         # STEP 0: Payload Validation
#         required = ["variant_id", "booking_date", "outlet_id", "sales_executive_id"]
#         missing = [f for f in required if not payload.get(f)]
#         if missing or not isinstance(payload.get("actual_amounts"), dict):
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Invalid input: Missing {', '.join(missing)} and actual_amounts (dict) must exist",
#             )

#         # STEP 0.5: Normalize Conditions and Delivery Checks
#         payload["conditions"] = {
#             k: bool(v) for k, v in payload.get("conditions", {}).items()
#         }
#         payload["delivery_checks"] = {
#             k: bool(v) for k, v in payload.get("delivery_checks", {}).items()
#         }

#         # STEP 0.6: Accessories Variance Computation
#         acc = payload.get("accessories_details", {})
#         if acc:
#             charged = acc.get("charged_amount", 0)
#             allowed = acc.get("allowed_amount", 0)
#             acc["variance"] = charged - allowed
#             payload["accessories_details"] = acc

#         # Convert date strings to date objects
#         from datetime import datetime

#         if isinstance(payload.get("booking_date"), str):
#             payload["booking_date"] = datetime.strptime(
#                 payload["booking_date"], "%Y-%m-%d"
#             ).date()
#         if isinstance(payload.get("delivery_date"), str):
#             payload["delivery_date"] = datetime.strptime(
#                 payload["delivery_date"], "%Y-%m-%d"
#             ).date()
#         if isinstance(payload.get("registration_date"), str):
#             payload["registration_date"] = datetime.strptime(
#                 payload["registration_date"], "%Y-%m-%d"
#             ).date()

#         # STEP 1: Save RAW transaction data first
#         transaction = TransactionService.create_transaction_raw(session, payload)

#         # STEP 2: Perform discount audit
#         audit_result = DiscountService.calculate_audit(
#             session,
#             transaction.variant_id,
#             transaction.booking_date,
#             payload.get("actual_amounts", {}),
#             transaction.conditions,
#         )

#         # STEP 3: Update existing transaction and its items
#         transaction = TransactionService.update_transaction_with_audit(
#             session, transaction.id, audit_result
#         )

#         return {
#             "id": transaction.id,
#             "status": transaction.status,
#             "summary": audit_result,
#         }

#     except Exception as e:
#         import traceback

#         print(traceback.format_exc())
#         raise HTTPException(status_code=400, detail=str(e))


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
            session,
            tx.variant_id,
            tx.id,
            tx.booking_date,
            actual_amounts,
            tx.conditions,
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


@app.get("/transactions")
def get_all_transactions(session: Session = Depends(get_session)):
    txs = session.exec(select(Transaction)).all()

    return [
        TransactionService.get_transaction_reconstruction(session, tx.id)
        for tx in txs
        if tx.id
    ]


@app.get("/accessories")
def get_accessories(session: Session = Depends(get_session)):
    accs = session.exec(select(Accessory)).all()
    return accs


# @app.get("/transactions")
# def get_all_transactions(session: Session = Depends(get_session)):
#     transactions = session.exec(select(Transaction)).all()

#     result = []

#     for txn in transactions:
#         # use reconstruction
#         data = TransactionService.get_transaction_reconstruction(session, txn.id)

#         # FLATTEN everything into ONE row
#         flat = {}
#         flat["customer_name"] = data.get("customer_name")
#         flat["mobile"] = data.get("mobile_number")

#         flat["variant"] = data.get("variant_name")

#         # --- CUSTOMER ---
#         flat["customer_name"] = data.get("customer", {}).get("name")
#         flat["mobile"] = data.get("customer", {}).get("mobile_number")

#         # --- VEHICLE ---
#         flat["variant"] = data.get("vehicle", {}).get("variant_name")
#         flat["booking_date"] = data.get("booking_date")

#         # --- COMPONENTS ---
#         for item in data.get("components", []):
#             name = item["component_name"]
#             flat[name] = item["actual_amount"]

#         # --- CONDITIONS ---
#         for k, v in data.get("conditions", {}).items():
#             flat[k] = v

#         # --- ACCESSORIES ---
#         acc = data.get("accessories_details", {})
#         flat["accessories_list"] = acc.get("items")
#         flat["accessories_charged"] = acc.get("charged_amount")

#         # --- DELIVERY CHECKS ---
#         for k, v in data.get("delivery_checks", {}).items():
#             flat[k] = v

#         # --- AUDIT ---
#         flat["observations"] = data.get("audit_info", {}).get("observations")

#         # --- TOTALS ---
#         flat["total_discount"] = data.get("total_actual_discount")
#         flat["excess_discount"] = data.get("total_excess_discount")
#         flat["status"] = data.get("status")

#         # --- ID ---
#         flat["id"] = txn.id

#         result.append(flat)

#     return result


# @app.get("/transactions", response_model=List[Transaction])
# def api_list_transactions(session: Session = Depends(get_session)):
#     return TransactionService.list_transactions(session)


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
