# Component 1 — AI Waste Assessment (Shehan)
# ---------------------------------------------------------------------------
# Runtime: Python 3.11 (no version pin found in the project; 3.11 satisfies
# tensorflow, ultralytics/YOLOv8, and pillow used by app.py).
# Entry point: app.py -> FastAPI instance named `app` (uvicorn app:app).
#
# KNOWN ISSUE — see integration-analysis.md / integration/INTEGRATION_STATUS.md:
# app.py loads resnet50_waste_type_final.keras and resnet50_condition_final.keras
# at MODULE IMPORT TIME (not lazily). These two files are NOT present in
# models/ in this repository (only ewaste_yolov8n_best.pt is). The image
# builds successfully, but the container WILL CRASH on startup with
# FileNotFoundError until both .keras files are placed in models/ before
# building, or volume-mounted into the container at that path.
#
# The Raspberry Pi hardware acquisition script (raspberry_pi/weight_camera.py)
# is intentionally NOT included here — it runs on the physical Pi, outside
# Docker, and talks to this container over the network.

FROM python:3.11-slim

WORKDIR /app

# libgl1/libglib2.0-0: required by opencv-python (a ultralytics dependency).
# curl: used by the HEALTHCHECK below.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY models/ ./models/
COPY knowledge_base/ ./knowledge_base/

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
