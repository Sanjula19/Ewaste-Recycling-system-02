"""
Component 3 - Report Generation routes
Reports are built from real optimization_results (Firestore) — same data
source as /api/history — filtered and aggregated, then saved so they can be
listed, re-opened, and deleted later.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services import report_service

router = APIRouter()


class GenerateReportRequest(BaseModel):
    report_type: str
    title: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    category: Optional[str] = None
    material_name: Optional[str] = None
    waste_type: Optional[str] = None
    safety_status: Optional[str] = None
    created_by: Optional[str] = None


@router.post("/api/reports/generate")
def generate_report(request: GenerateReportRequest):
    """Build a report from real data, save it, and return the full report (rows included)."""
    try:
        report = report_service.build_report(
            report_type=request.report_type,
            date_from=request.date_from,
            date_to=request.date_to,
            category=request.category,
            material_name=request.material_name,
            waste_type=request.waste_type,
            safety_status=request.safety_status,
            created_by=request.created_by,
            title=request.title,
        )
        doc_id = report_service.save_report(report)
        report["id"] = doc_id
        return report
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/reports")
def get_reports(limit: int = 50):
    """List saved reports (metadata + summary, no row detail) for the History table."""
    reports = report_service.list_reports(limit=limit)
    return {"count": len(reports), "reports": reports}


@router.get("/api/reports/filter-options")
def get_filter_options():
    """Real, distinct filter values pulled from actual optimization data."""
    return report_service.get_report_filter_options()


@router.get("/api/reports/{report_id}")
def get_report(report_id: str):
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/api/reports/{report_id}")
def delete_report(report_id: str):
    ok = report_service.delete_report(report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Report not found or could not be deleted")
    return {"status": "deleted", "id": report_id}
