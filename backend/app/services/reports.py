"""Shared report authorization for report and annotation endpoints."""
import uuid
from fastapi import HTTPException
from app.models.report import AnalysisReport


def require_report(db, analysis_id, user):
    if db is None:
        raise HTTPException(503, "Database unavailable.")
    try:
        report = db.get(AnalysisReport, uuid.UUID(analysis_id))
    except ValueError:
        report = None
    if report is None or (str(report.owner_id) != user["sub"] and user["role"] != "admin"):
        raise HTTPException(404, "Report not found.")
    return report
