# routes/report_routes.py
# REVIEW THIS
from datetime import date
import os
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlmodel import Session, select
from db.models import User, UserRole, ExportJob, ExportStatus
from db.session import get_session
from services.auth.dependencies import get_current_user
from services.auth.scope import get_allowed_outlets, validate_outlet_access
from services.reports.daily.service import DailyReportService
from services.reports.monthly.service import MonthlyReportService

from services.reports.daily.daily_report_generator import generate_daily_report
from services.reports.monthly.generator import generate_monthly_report
from services.reports.export_query import get_export_transactions_count
from services.reports.export_service import ExportService
from services.reports.daily.combined_report_service import CombinedReportService
from services.reports.daily.combined_report_generator import CombinedReportGenerator
from schemas.mis import MISExportRequest

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
def download_daily_report(
    start_date: date,
    end_date: date,
    dealership_id: int | None = None,
    outlet_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    # ADMIN
    if current_user.role == UserRole.ADMIN:
        report_data = DailyReportService.generate(
            session=session,
            start_date=start_date,
            end_date=end_date,
            dealership_id=dealership_id,
            outlet_id=outlet_id,
        )

        buffer, filename = generate_daily_report(backend_data=report_data)

        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": (f'attachment; filename="{filename}"')},
        )

    # NON ADMIN USERS
    allowed_outlets = get_allowed_outlets(current_user)

    # USER REQUESTED SPECIFIC OUTLET
    if outlet_id:
        validate_outlet_access(current_user, outlet_id)

        report_data = DailyReportService.generate(
            session=session,
            start_date=start_date,
            end_date=end_date,
            outlet_id=outlet_id,
        )

    # MULTI OUTLET REPORT
    else:
        report_data = DailyReportService.generate(
            session=session,
            start_date=start_date,
            end_date=end_date,
            outlet_ids=allowed_outlets,
        )

    # GENERATE FILE
    buffer, filename = generate_daily_report(backend_data=report_data)

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": (f'attachment; filename="{filename}"')},
    )


@router.get("/combined")
def download_combined_report(
    start_date: date,
    end_date: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only administrators can download combined reports"
        )

    report_data = CombinedReportService.generate(
        session=session, start_date=start_date, end_date=end_date
    )

    buffer, filename = CombinedReportGenerator(backend_data=report_data).generate()

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": (f'attachment; filename="{filename}"')},
    )


@router.get("/monthly")
def download_monthly_report(
    start_date: date,
    end_date: date,
    dealership_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can download combined reports",
        )
    report = MonthlyReportService.generate(
        session=session,
        start_date=start_date,
        end_date=end_date,
        dealership_id=dealership_id,
    )

    buffer, filename = generate_monthly_report(report)

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/mis/export")
def trigger_mis_export(
    background_tasks: BackgroundTasks,
    payload: MISExportRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger background generation of MIS report Excel.
    If month is provided (e.g. "2026-06"), dates are overridden for that calendar month.
    """
    print(
        payload.start_date,
        payload.end_date,
        payload.month,
        payload.outlet_id,
        payload.dealership_id,
        payload.stage,
    )
    # 1. Resolve calendar payload.month filter
    if payload.month:
        try:
            year, m = map(int, payload.month.split("-"))
            import calendar

            last_day = calendar.monthrange(year, m)[1]
            payload.start_date = date(year, m, 1)
            payload.end_date = date(year, m, last_day)
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid month format. Expected YYYY-MM."
            )

    # 2. Date Range Validation (max 1 year)
    if payload.start_date and payload.end_date:
        if payload.start_date > payload.end_date:
            raise HTTPException(
                status_code=400, detail="Start date cannot be after end_date."
            )
        if (payload.end_date - payload.start_date).days > 366:
            raise HTTPException(
                status_code=400, detail="Export date range cannot exceed 1 year."
            )

    # Default to last 30 days if no dates and no month selected to prevent huge scans
    if not payload.start_date and not payload.end_date:
        from datetime import timedelta

        payload.end_date = date.today()
        payload.start_date = payload.end_date - timedelta(days=30)

    # 3. Security scoping
    allowed_outlets = get_allowed_outlets(current_user)
    if current_user.role == UserRole.ADMIN:
        allowed_outlet_ids = None
    else:
        allowed_outlet_ids = allowed_outlets
        if payload.outlet_id:
            validate_outlet_access(current_user, payload.outlet_id)
            allowed_outlet_ids = [payload.outlet_id]
            payload.outlet_id = None  # query_export expects outlet_id to be cleared to override with list

    # 4. Count matching rows for safety control
    count = get_export_transactions_count(
        session=session,
        start_date=payload.start_date,
        end_date=payload.end_date,
        outlet_id=payload.outlet_id,
        dealership_id=payload.dealership_id,
        stage=payload.stage,
        allowed_outlet_ids=allowed_outlet_ids,
    )

    if count == 0:
        raise HTTPException(
            status_code=400,
            detail="No transaction records match the specified filters.",
        )

    if count > 50000:
        raise HTTPException(
            status_code=400,
            detail=f"Export row count ({count}) exceeds maximum limit of 50,000 rows. Please apply narrower filters.",
        )

    # 5. Check for active job from the same user
    active_job_stmt = select(ExportJob).where(
        ExportJob.created_by == current_user.id,
        ExportJob.status.in_([ExportStatus.PENDING, ExportStatus.PROCESSING]),
    )

    if session.exec(active_job_stmt).first():
        raise HTTPException(
            status_code=409,
            detail="An export is already in progress. Please wait for it to complete before starting a new one.",
        )

    # Create export job
    filters = {
        "start_date": payload.start_date.isoformat() if payload.start_date else None,
        "end_date": payload.end_date.isoformat() if payload.end_date else None,
        "outlet_id": payload.outlet_id,
        "dealership_id": payload.dealership_id,
        "stage": payload.stage,
        "allowed_outlet_ids": allowed_outlet_ids,
    }

    job = ExportService.create_export_job(
        session=session, created_by=current_user.id, filters=filters
    )

    # 6. Queue background execution
    background_tasks.add_task(ExportService.generate_export_file_task, job_id=job.id)

    job.total_rows = count
    session.add(job)
    session.commit()
    session.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status,
        "row_count": count,
    }


@router.get("/mis/export/jobs")
def get_export_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent MIS export jobs created by the current user.
    """
    jobs = ExportService.get_recent_jobs(session, current_user.id)
    return [
        {
            "id": job.id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "row_count": job.row_count,
            "filters": json.loads(job.filters) if job.filters else {},
        }
        for job in jobs
    ]


@router.get("/mis/download/{job_id}")
def download_export_file(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Download generated Excel file if export is complete.
    """
    job = session.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found.")

    # Security check: Non-admin can only download their own exports
    if current_user.role != UserRole.ADMIN and job.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to download this export.",
        )

    if job.status == ExportStatus.FAILED:
        raise HTTPException(
            status_code=400, detail=f"Export generation failed: {job.error_message}"
        )
    if job.status in (ExportStatus.PENDING, ExportStatus.PROCESSING):
        raise HTTPException(
            status_code=400, detail="Export file is still being generated. Please wait."
        )
    if (
        job.status == ExportStatus.EXPIRED
        or not job.file_path
        or not os.path.exists(job.file_path)
    ):
        raise HTTPException(
            status_code=410, detail="Export file has expired or is no longer available."
        )

    filename = job.file_name or os.path.basename(job.file_path)
    return FileResponse(
        path=job.file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
