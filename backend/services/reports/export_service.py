# backend\services\reports\export_service.py
import os
import time
import logging
import json
from datetime import timedelta, date
from typing import Dict, Any, Optional, List
from sqlmodel import Session, select, desc

from db.session import engine
from db.models import ExportJob, ExportStatus
from services.utils import get_ist_now
from services.reports.excel_writer import export_mis_excel_incremental

logger = logging.getLogger(__name__)


class ExportService:
    @staticmethod
    def create_export_job(
        session: Session, created_by: Optional[int], filters: Dict[str, Any]
    ) -> ExportJob:
        """
        Creates a new export job in the pending state.
        """
        job = ExportJob(
            created_by=created_by,
            status=ExportStatus.PENDING,
            filters=json.dumps(filters),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    @staticmethod
    def generate_export_file_task(job_id: int):
        """
        Background task to perform the incremental Excel generation and update job status.
        Runs in a separate database session.
        """
        # Get backend root absolute directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.dirname(os.path.dirname(current_dir))
        exports_dir = os.path.join(backend_root, "exports")

        os.makedirs(exports_dir, exist_ok=True)
        file_name = f"mis_export_{job_id}_{int(time.time())}.xlsx"
        file_path = os.path.join(exports_dir, file_name)

        start_time = get_ist_now()

        with Session(engine) as session:
            # 1. Clean up old exports first
            try:
                ExportService.cleanup_old_exports(session)
            except Exception as e:
                logger.error(f"Error during old exports cleanup: {e}", exc_info=True)

            # 2. Get the job
            job = session.get(ExportJob, job_id)
            if not job:
                logger.error(f"Export job {job_id} not found in background task.")
                return

            query_args = json.loads(job.filters or "{}")
            print("QUERY_ARGS:", query_args)

            if query_args.get("start_date"):
                query_args["start_date"] = date.fromisoformat(query_args["start_date"])

            if query_args.get("end_date"):
                query_args["end_date"] = date.fromisoformat(query_args["end_date"])

            # Update status to processing
            job.status = ExportStatus.PROCESSING
            job.started_at = get_ist_now()
            job.file_name = file_name
            session.add(job)
            session.commit()
            session.refresh(job)

            # 3. Generate file
            try:
                logger.info(f"Starting Excel generation for job {job_id}...")
                row_count = export_mis_excel_incremental(
                    session=session, file_path=file_path, query_args=query_args
                )

                if not os.path.exists(file_path):
                    raise RuntimeError("Export file was not generated.")

                if os.path.getsize(file_path) == 0:
                    raise RuntimeError("Generated export file is empty.")

                duration = get_ist_now() - start_time
                logger.info(
                    f"Export job {job_id} completed. Rows: {row_count}. Duration: {duration}"
                )

                completed_at = get_ist_now()

                job.status = ExportStatus.COMPLETED
                job.file_name = file_name
                job.file_path = file_path
                job.completed_at = completed_at
                job.expires_at = completed_at + timedelta(hours=24)
                job.row_count = row_count

                session.add(job)
                session.commit()

            except Exception as e:
                session.rollback()
                logger.error(f"Export job {job_id} failed: {e}", exc_info=True)

                # Cleanup file if partially created
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                job = session.get(ExportJob, job_id)
                job.status = ExportStatus.FAILED
                job.completed_at = get_ist_now()
                job.error_message = str(e)
                session.add(job)
                session.commit()

    @staticmethod
    def cleanup_old_exports(session: Session, retention_hours: int = 24):
        """
        Deletes files and marks ExportJob status as expired for jobs older than `retention_hours` hours.
        """
        statement = select(ExportJob).where(
            ExportJob.expires_at.is_not(None),
            ExportJob.expires_at < get_ist_now(),
            ExportJob.status != ExportStatus.EXPIRED,
        )
        expired_jobs = session.exec(statement).all()

        for job in expired_jobs:
            if job.file_path and os.path.exists(job.file_path):
                try:
                    os.remove(job.file_path)
                    logger.info(f"Deleted expired export file: {job.file_path}")
                except Exception as e:
                    logger.error(
                        f"Failed to delete expired export file {job.file_path}: {e}"
                    )

            job.status = ExportStatus.EXPIRED
            job.file_path = None
            job.file_name = None
            session.add(job)

        if expired_jobs:
            session.commit()
            logger.info(f"Cleaned up {len(expired_jobs)} expired export jobs.")

    @staticmethod
    def get_recent_jobs(
        session: Session, user_id: int, limit: int = 10
    ) -> List[ExportJob]:
        """
        Fetches the recent export jobs created by a user.
        """
        statement = (
            select(ExportJob)
            .where(ExportJob.created_by == user_id)
            .order_by(desc(ExportJob.created_at))
            .limit(limit)
        )
        return list(session.exec(statement).all())
