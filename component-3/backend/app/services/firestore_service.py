"""
Component 3 - Firestore Service
Save input/output + retrieve history
"""

from datetime import datetime
from app.config import get_db


def save_optimization_request(input_data: dict) -> str:
    """Save input data to Firestore optimization_requests collection."""
    try:
        db = get_db()
        if not db:
            return None
        doc_ref = db.collection("optimization_requests").add({
            **input_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        return doc_ref[1].id
    except Exception as e:
        print(f"Firestore save request error: {e}")
        return None


def save_optimization_result(result_data: dict) -> str:
    """Save output result to Firestore optimization_results collection."""
    try:
        db = get_db()
        if not db:
            return None
        doc_ref = db.collection("optimization_results").add({
            **result_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        return doc_ref[1].id
    except Exception as e:
        print(f"Firestore save result error: {e}")
        return None


def get_optimization_history(limit: int = 20) -> list:
    """Retrieve past optimization results from Firestore."""
    try:
        db = get_db()
        if not db:
            return []
        docs = (
            db.collection("optimization_results")
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        print(f"Firestore get history error: {e}")
        return []
