"""Run YOLO without importing TensorFlow in the same process."""

import io
import json
import os
import sys

import numpy as np
from PIL import Image
from ultralytics import YOLO


base_dir = os.path.dirname(os.path.abspath(__file__))
model = YOLO(os.path.join(base_dir, "models", "ewaste_yolov8n_best.pt"))
image = np.asarray(Image.open(io.BytesIO(sys.stdin.buffer.read())).convert("RGB"))
results = model.predict(source=image, conf=0.50, imgsz=640, verbose=False, device="cpu")

detections = []
for result in results:
    for box in result.boxes:
        class_id = int(box.cls[0].item())
        detections.append(
            {
                "class_id": class_id,
                "detected_type": model.names[class_id],
                "confidence": float(box.conf[0].item()),
                "xyxy": box.xyxy[0].tolist(),
            }
        )

sys.stdout.write(json.dumps(detections))
