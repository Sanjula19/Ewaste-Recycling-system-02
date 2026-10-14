"""
Predictions API -- ML gas classification from latest MQTT reading.

On every call:
  1. Fetch the latest raw reading from the DB
  2. Convert raw ADC values -> ppm using calibration constants
  3. Run single-label + multi-label Random Forest prediction
  4. Evaluate WHO/OSHA thresholds -> create Alert in DB if exceeded
  5. Return full prediction result with gas name, confidence, alerts

Alert naming:
  AMMONIA -> "NH3 (Ammonia)" in alert gas_name
  LPG     -> "LPG (Smoke/Flammable)" in alert gas_name
  etc.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models import RawReadingDB, AlertDB
from app.services.ml_service import ml_service
from app.knowledge_base import WHO_LIMITS, GAS_INFO

logger = logging.getLogger(__name__)
router = APIRouter()

# ── ADC → ppm calibration ──────────────────────────────────────────────────
# Uses MQ sensor power-law formula: ppm = A * (Rs/R0)^B
# Rs = RL * (Vref - Vout) / Vout,  Vout = (adc / 4095) * 3.3
# Constants from your firmware main.ino + datasheet values
_ADC_MAX  = 4095.0
_VREF     = 3.3

def _adc_to_ppm(adc_raw: Optional[int],
                rl: float, r0: float,
                a: float,  b: float) -> float:
    """Convert raw ESP32 ADC reading to ppm. Returns 0.0 on bad input."""
    if adc_raw is None or adc_raw <= 0:
        return 0.0
    adc_val = min(float(adc_raw), _ADC_MAX - 1)
    v_out   = (adc_val / _ADC_MAX) * _VREF
    if v_out <= 0:
        return 0.0
    rs      = rl * (_VREF - v_out) / v_out
    ratio   = rs / r0
    if ratio <= 0:
        return 0.0
    ppm = a * (ratio ** b)
    return max(0.0, round(ppm, 4))

# MQ-2: LPG / Smoke  (RL=5kΩ, R0=9.83, A=574.25, B=-2.222)
def mq2_to_ppm(adc):  return _adc_to_ppm(adc, 5.0,  9.83,  574.25, -2.222)
# MQ-7: CO           (RL=10kΩ, R0=10.0, A=99.042, B=-1.518)
def mq7_to_ppm(adc):  return _adc_to_ppm(adc, 10.0, 10.0,  99.042, -1.518)
# MQ-135: Benzene/NH3/VOC  (RL=20kΩ, R0=76.63, A=110.47, B=-2.862)
def mq135_to_ppm(adc): return _adc_to_ppm(adc, 20.0, 76.63, 110.47, -2.862)
# MQ-136: H2S        (RL=10kΩ, R0=15.0, A=36.737, B=-3.536)
def mq136_to_ppm(adc): return _adc_to_ppm(adc, 10.0, 15.0,  36.737, -3.536)


# ── Human-readable gas name mapping ────────────────────────────────────────
GAS_DISPLAY_NAMES = {
    "AMMONIA": "NH3 (Ammonia)",
    "BENZENE": "C6H6 (Benzene)",
    "CO":      "CO (Carbon Monoxide)",
    "H2S":     "H2S (Hydrogen Sulfide)",
    "LPG":     "LPG (Smoke / Flammable Gas)",
    "CLEAN":   "Clean Air",
}

# Alert threshold: YELLOW = 50% of WHO limit, RED = 100%
def _evaluate_who(gas_class: str, ppm_values: dict) -> List[dict]:
    """Return list of threshold violations for a classified gas."""
    violations = []
    info = WHO_LIMITS.get(gas_class)
    if not info:
        return violations

    sensor_field = info["sensor_field"]           # e.g. "mq7_ppm"
    measured     = ppm_values.get(sensor_field, 0.0)
    limit        = info["limit"]

    if measured <= 0 or limit <= 0:
        return violations

    pct = (measured / limit) * 100.0

    if pct >= 50.0:
        risk = "RED" if pct >= 100.0 else "YELLOW"
        violations.append({
            "gas_name":       GAS_DISPLAY_NAMES.get(gas_class, gas_class),
            "gas_class":      gas_class,
            "ppm_value":      measured,
            "who_limit":      limit,
            "unit":           info["unit"],
            "exceeded_by_pct": round(max(0.0, pct - 100.0), 2),
            "risk_level":     risk,
            "health_risks":   info["health_risks"],
            "safety_actions": info["safety_actions"],
        })
    return violations


# ── Pydantic models ─────────────────────────────────────────────────────────
class PpmValues(BaseModel):
    mq2_ppm:   float
    mq7_ppm:   float
    mq135_ppm: float
    mq136_ppm: float

class AlertDetail(BaseModel):
    gas_name:        str
    risk_level:      str          # "YELLOW" | "RED"
    ppm_value:       float
    who_limit:       float
    unit:            str
    exceeded_by_pct: float
    health_risks:    List[str]
    safety_actions:  List[str]

class PredictionResult(BaseModel):
    available:           bool
    reading_id:          Optional[str]   = None
    received_at:         Optional[str]   = None
    ppm:                 Optional[PpmValues] = None
    gas_class:           Optional[str]   = None   # "AMMONIA", "CO", etc.
    gas_display_name:    Optional[str]   = None   # "NH3 (Ammonia)", etc.
    confidence:          Optional[float] = None
    detected_gases:      List[str]       = []      # multi-label list
    alerts_created:      int             = 0
    alerts:              List[AlertDetail] = []
    model_version:       Optional[str]   = None
    reason:              Optional[str]   = None
    model_data_warning:  Optional[str]   = None


# ── Core prediction logic ───────────────────────────────────────────────────
async def _run_prediction(db: AsyncSession) -> PredictionResult:
    """Fetch latest reading, run ML, create alerts, return result."""

    # 1. Get latest reading
    result = await db.execute(
        select(RawReadingDB)
        .order_by(RawReadingDB.received_at.desc(), RawReadingDB.id.desc())
        .limit(1)
    )
    reading = result.scalar_one_or_none()

    if not reading:
        return PredictionResult(
            available=False,
            reason="No sensor readings in database yet. Power on ESP32 and wait for MQTT data."
        )

    if not ml_service.is_loaded:
        return PredictionResult(
            available=False,
            reason="ML models not loaded. Check that random_forest_v1.pkl, scaler.pkl, label_encoder.pkl exist in backend/ml_models/."
        )

    # 2. Convert ADC -> ppm
    mq2   = mq2_to_ppm(reading.mq2_raw)
    mq7   = mq7_to_ppm(reading.mq7_raw)
    mq135 = mq135_to_ppm(reading.mq135_raw)
    mq136 = mq136_to_ppm(reading.mq136_raw)
    temp  = reading.temperature_c or 28.0
    hum   = reading.humidity_pct  or 65.0

    ppm_values = {
        "mq2_ppm":   mq2,
        "mq7_ppm":   mq7,
        "mq135_ppm": mq135,
        "mq136_ppm": mq136,
    }

    logger.info(
        f"[PREDICT] rid={reading.reading_id[:8]} "
        f"MQ2={mq2:.1f} MQ7={mq7:.1f} MQ135={mq135:.1f} MQ136={mq136:.4f} "
        f"T={temp:.1f} H={hum:.1f}"
    )

    # 3. Single-label classification
    clf = ml_service.classify(mq2, mq7, mq135, mq136, temp, hum)
    gas_class   = clf.get("gas_class", "UNKNOWN")
    confidence  = clf.get("confidence", 0.0)
    ml_warning  = clf.get("model_data_warning", "")

    # 4. Multi-label (detected gases list)
    detected = ml_service.classify_multilabel(mq2, mq7, mq135, mq136, temp, hum)

    # 5. WHO threshold evaluation + DB alert creation
    violations = _evaluate_who(gas_class, ppm_values)

    # Also check any multi-label gases
    for g in detected:
        if g != gas_class:
            for v in _evaluate_who(g, ppm_values):
                if not any(x["gas_class"] == v["gas_class"] for x in violations):
                    violations.append(v)

    alerts_created = 0
    alert_details  = []

    for v in violations:
        # Check if an un-acknowledged alert for this gas already exists for this reading
        existing = (await db.execute(
            select(AlertDB).where(
                AlertDB.raw_reading_id == reading.id,
                AlertDB.gas_name       == v["gas_name"],
            )
        )).scalar_one_or_none()

        if not existing:
            new_alert = AlertDB(
                alert_id        = str(uuid.uuid4()),
                raw_reading_id  = reading.id,
                device_id       = reading.device_id,
                timestamp       = datetime.now(timezone.utc),
                gas_name        = v["gas_name"],
                ppm_value       = v["ppm_value"],
                who_limit       = v["who_limit"],
                unit            = v["unit"],
                exceeded_by_pct = v["exceeded_by_pct"],
                risk_level      = v["risk_level"],
                health_risks    = v["health_risks"],
                safety_actions  = v["safety_actions"],
                acknowledged    = False,
            )
            db.add(new_alert)
            alerts_created += 1
            logger.warning(
                f"[ALERT] {v['risk_level']} | {v['gas_name']} "
                f"{v['ppm_value']:.2f} ppm (limit {v['who_limit']} ppm) "
                f"rid={reading.reading_id[:8]}"
            )

        alert_details.append(AlertDetail(**{
            k: v[k] for k in AlertDetail.model_fields
        }))

    if alerts_created > 0:
        await db.commit()

    return PredictionResult(
        available        = True,
        reading_id       = reading.reading_id,
        received_at      = reading.received_at.isoformat() if reading.received_at else None,
        ppm              = PpmValues(
            mq2_ppm=mq2, mq7_ppm=mq7, mq135_ppm=mq135, mq136_ppm=mq136
        ),
        gas_class        = gas_class,
        gas_display_name = GAS_DISPLAY_NAMES.get(gas_class, gas_class),
        confidence       = round(confidence * 100, 1) if confidence else None,
        detected_gases   = detected,
        alerts_created   = alerts_created,
        alerts           = alert_details,
        model_version    = ml_service.version,
        model_data_warning = ml_warning or None,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────
@router.post("", response_model=PredictionResult)
async def predict(db: AsyncSession = Depends(get_db)):
    """
    Run ML classification on latest MQTT reading.
    Creates DB alerts automatically if WHO thresholds exceeded.
    """
    return await _run_prediction(db)


@router.get("/status", response_model=PredictionResult)
async def prediction_status(db: AsyncSession = Depends(get_db)):
    """Same as POST /predict — returns current classification status."""
    return await _run_prediction(db)
