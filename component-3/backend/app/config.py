import firebase_admin
from firebase_admin import credentials, firestore
import os

db = None
_initialized = False


def initialize_firebase():
    global db, _initialized

    if _initialized:
        return

    try:
        # firebase_key.json path
        key_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "firebase_key.json"
        )

        if not os.path.exists(key_path):
            print(f"  firebase_key.json not found at: {key_path}")
            return

        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        _initialized = True
        print("  Firebase connected!")

    except Exception as e:
        print(f"  Firebase error: {e}")


def get_db():
    return db


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

RECYCLING_BENCHMARK_PATH = os.path.join(DATA_DIR, "recycling_benchmark.csv")
SAFETY_RULES_PATH        = os.path.join(DATA_DIR, "safety_rules.json")
CHEMICAL_AGENT_MAP_PATH  = os.path.join(DATA_DIR, "chemical_agent_map.json")