"""
Component 3 - Report Service
Builds reports from the SAME Firestore data already shown in /api/history —
no synthetic rows, no random numbers. A report is a filtered slice of real
optimization_results documents, plus aggregates computed over that slice.
"""

from datetime import datetime, timezone
from app.config import get_db

REPORTS_FETCH_LIMIT = 500  # optimization_results is small; fetch generously, filter in Python
REPORT_TYPES = ["Summary", "Safety", "Efficiency", "Material Breakdown"]


def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _fetch_all_results():
    db = get_db()
    if not db:
        return []
    docs = (
        db.collection("optimization_results")
        .order_by("timestamp", direction="DESCENDING")
        .limit(REPORTS_FETCH_LIMIT)
        .stream()
    )
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def _apply_filters(records, date_from=None, date_to=None, category=None,
                    material_name=None, waste_type=None, safety_status=None):
    dt_from = _parse_ts(date_from) if date_from else None
    dt_to = _parse_ts(date_to) if date_to else None

    out = []
    for r in records:
        ts = _parse_ts(r.get("timestamp"))
        if dt_from and (ts is None or ts < dt_from):
            continue
        if dt_to and (ts is None or ts > dt_to):
            continue
        if waste_type and r.get("waste_type") != waste_type:
            continue
        if material_name and r.get("material_name") != material_name:
            continue
        if safety_status and r.get("safety_status") != safety_status:
            continue
        out.append(r)
    return out


def _round(v, nd=2):
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return 0


def _compute_summary(records):
    total = len(records)
    if total == 0:
        return {
            "total_batches": 0, "total_weight_kg": 0, "total_energy_kwh": 0,
            "avg_efficiency_pct": 0, "avg_processing_time_min": 0,
            "safety_breakdown": {}, "method_breakdown": {},
            "moisture_source_breakdown": {}, "material_breakdown": {},
            "waste_type_breakdown": {}, "date_range": {"from": None, "to": None},
        }

    total_weight = sum(_round(r.get("weight_kg")) for r in records)
    total_energy = sum(_round(r.get("total_energy_kwh") or r.get("energy_kwh")) for r in records)
    avg_efficiency = sum(_round(r.get("recycling_efficiency_pct")) for r in records) / total
    avg_time = sum(_round(r.get("processing_time_min")) for r in records) / total

    def _breakdown(key):
        counts = {}
        for r in records:
            v = r.get(key) or "Unknown"
            counts[v] = counts.get(v, 0) + 1
        return {k: {"count": c, "pct": _round(c / total * 100, 1)} for k, c in counts.items()}

    timestamps = [t for t in (_parse_ts(r.get("timestamp")) for r in records) if t]

    return {
        "total_batches": total,
        "total_weight_kg": _round(total_weight),
        "total_energy_kwh": _round(total_energy),
        "avg_efficiency_pct": _round(avg_efficiency),
        "avg_processing_time_min": _round(avg_time),
        "safety_breakdown": _breakdown("safety_status"),
        "method_breakdown": _breakdown("recommended_method"),
        "moisture_source_breakdown": _breakdown("moisture_source"),
        "material_breakdown": _breakdown("material_name"),
        "waste_type_breakdown": _breakdown("waste_type"),
        "date_range": {
            "from": min(timestamps).isoformat() if timestamps else None,
            "to": max(timestamps).isoformat() if timestamps else None,
        },
    }


REPORT_ROW_FIELDS = [
    "id", "timestamp", "material_name", "waste_type", "weight_kg",
    "moisture_condition", "moisture_source", "recommended_method",
    "optimal_temp_c", "processing_time_min", "energy_kwh",
    "recycling_efficiency_pct", "safety_status", "grade", "batch_id",
]


def _project_rows(records):
    return [{k: r.get(k) for k in REPORT_ROW_FIELDS} for r in records]


def build_report(report_type, date_from=None, date_to=None, category=None,
                  material_name=None, waste_type=None, safety_status=None,
                  created_by=None, title=None):
    """Compute a report (summary + filtered rows) from real Firestore data."""
    all_records = _fetch_all_results()
    filtered = _apply_filters(
        all_records, date_from, date_to, category, material_name, waste_type, safety_status
    )
    summary = _compute_summary(filtered)

    return {
        "report_type": report_type,
        "title": title or f"{report_type} Report",
        "created_by": created_by or "Component 3 Operator",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "date_from": date_from, "date_to": date_to, "category": category,
            "material_name": material_name, "waste_type": waste_type,
            "safety_status": safety_status,
        },
        "summary": summary,
        "rows": _project_rows(filtered),
        "source_total_records": len(all_records),
        "status": "completed" if filtered or all_records else "no_data",
    }


def save_report(report: dict) -> str:
    """Persist a generated report to Firestore's `generated_reports` collection."""
    try:
        db = get_db()
        if not db:
            return None
        doc_ref = db.collection("generated_reports").add(report)
        return doc_ref[1].id
    except Exception as e:
        print(f"Firestore save report error: {e}")
        return None


def list_reports(limit: int = 50) -> list:
    """List saved reports — metadata + summary only, not the full row set (kept light for the history table)."""
    try:
        db = get_db()
        if not db:
            return []
        docs = (
            db.collection("generated_reports")
            .order_by("generated_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        out = []
        for doc in docs:
            data = doc.to_dict()
            data.pop("rows", None)
            out.append({"id": doc.id, **data})
        return out
    except Exception as e:
        print(f"Firestore list reports error: {e}")
        return []


def get_report(report_id: str) -> dict:
    """Full report (including rows) for preview / regenerate / export."""
    try:
        db = get_db()
        if not db:
            return None
        doc = db.collection("generated_reports").document(report_id).get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}
    except Exception as e:
        print(f"Firestore get report error: {e}")
        return None


def delete_report(report_id: str) -> bool:
    try:
        db = get_db()
        if not db:
            return False
        db.collection("generated_reports").document(report_id).delete()
        return True
    except Exception as e:
        print(f"Firestore delete report error: {e}")
        return False


def get_report_filter_options():
    """Real, distinct values pulled from actual data — used to populate the Generate Report form's dropdowns."""
    records = _fetch_all_results()
    materials = sorted({r.get("material_name") for r in records if r.get("material_name")})
    waste_types = sorted({r.get("waste_type") for r in records if r.get("waste_type")})
    safety_statuses = sorted({r.get("safety_status") for r in records if r.get("safety_status")})
    return {
        "materials": materials,
        "waste_types": waste_types,
        "safety_statuses": safety_statuses,
        "report_types": REPORT_TYPES,
    }
