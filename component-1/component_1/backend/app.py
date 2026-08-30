from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

import tensorflow as tf
import numpy as np
from PIL import Image
from ultralytics import YOLO

import io
import os
import json


app = FastAPI(
    title="Waste Assessment Service",
    version="1.2"
)


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WASTE_MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "resnet50_waste_type_final.keras"
)

CONDITION_MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "resnet50_condition_final.keras"
)

EWASTE_MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "ewaste_yolov8n_best.pt"
)

EWASTE_KB_PATH = os.path.join(
    BASE_DIR,
    "knowledge_base",
    "ewaste_hazards.json"
)


# --------------------------------------------------
# CLASS NAMES
# --------------------------------------------------

WASTE_CLASSES = [
    "Plastic",
    "Glass",
    "Metal",
    "Paper",
    "Cardboard"
]

CONDITION_CLASSES = [
    "Clean",
    "Contaminated",
    "Damaged"
]


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

EWASTE_CONFIDENCE_THRESHOLD = 0.50


# --------------------------------------------------
# LOAD GENERAL WASTE MODELS
# --------------------------------------------------

missing_general_models = []

if os.path.isfile(WASTE_MODEL_PATH):
    print("Loading waste type model...")
    waste_model = tf.keras.models.load_model(WASTE_MODEL_PATH)
else:
    waste_model = None
    missing_general_models.append(os.path.basename(WASTE_MODEL_PATH))

if os.path.isfile(CONDITION_MODEL_PATH):
    print("Loading condition model...")
    condition_model = tf.keras.models.load_model(CONDITION_MODEL_PATH)
else:
    condition_model = None
    missing_general_models.append(os.path.basename(CONDITION_MODEL_PATH))

if missing_general_models:
    print(
        "General waste models unavailable:",
        ", ".join(missing_general_models)
    )


# --------------------------------------------------
# LOAD E-WASTE MODEL
# --------------------------------------------------

print("Loading e-waste YOLO model...")

ewaste_model = YOLO(
    EWASTE_MODEL_PATH
)


# --------------------------------------------------
# LOAD E-WASTE KNOWLEDGE BASE
# --------------------------------------------------

print("Loading e-waste knowledge base...")

with open(
    EWASTE_KB_PATH,
    "r",
    encoding="utf-8"
) as f:
    ewaste_knowledge_base = json.load(f)


print("All models and knowledge base loaded successfully.")


# --------------------------------------------------
# IMAGE PREPARATION
# --------------------------------------------------

def prepare_full_image(image_bytes):
    """
    Full original image.
    Used by the Condition model.
    """

    img = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    img = img.resize(
        (224, 224)
    )

    arr = np.asarray(
        img,
        dtype=np.float32
    )

    arr = np.expand_dims(
        arr,
        axis=0
    )

    return arr


def prepare_waste_roi(image_bytes):
    """
    Center ROI crop.
    Used by the Waste Type model.
    """

    img = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    width, height = img.size

    left = int(width * 0.10)
    right = int(width * 0.90)
    top = int(height * 0.05)
    bottom = int(height * 0.95)

    img = img.crop(
        (
            left,
            top,
            right,
            bottom
        )
    )

    img = img.resize(
        (224, 224)
    )

    arr = np.asarray(
        img,
        dtype=np.float32
    )

    arr = np.expand_dims(
        arr,
        axis=0
    )

    return arr


def prepare_ewaste_image(image_bytes):
    """
    Full RGB image for YOLO e-waste detection.
    """

    img = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    return np.asarray(img)


# --------------------------------------------------
# GRADE LOGIC
# --------------------------------------------------

def calculate_grade(condition):

    if condition == "Clean":
        return "A"

    elif condition == "Contaminated":
        return "B"

    elif condition == "Damaged":
        return "C"

    return "Unknown"


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "waste-assessment-service",
        "version": "1.2",
        "general_waste": "ready" if not missing_general_models else "unavailable",
        "ewaste": "ready"
    }


# --------------------------------------------------
# GENERAL WASTE PREDICTION
# --------------------------------------------------

@app.post("/waste/predict")
async def predict_waste(
    image: UploadFile = File(...)
):

    try:

        if missing_general_models:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "General waste models are unavailable",
                    "missing_models": missing_general_models
                }
            )

        image_bytes = await image.read()

        if not image_bytes:

            return JSONResponse(
                status_code=400,
                content={
                    "error": "Empty image file"
                }
            )


        # ------------------------------
        # Prepare images
        # ------------------------------

        waste_img = prepare_waste_roi(
            image_bytes
        )

        condition_img = prepare_full_image(
            image_bytes
        )


        # ------------------------------
        # Waste Type Prediction
        # ------------------------------

        waste_pred = waste_model.predict(
            waste_img,
            verbose=0
        )

        waste_index = int(
            np.argmax(
                waste_pred[0]
            )
        )

        waste_type = WASTE_CLASSES[
            waste_index
        ]

        waste_confidence = float(
            waste_pred[0][waste_index]
        )


        # ------------------------------
        # Condition Prediction
        # ------------------------------

        condition_pred = condition_model.predict(
            condition_img,
            verbose=0
        )

        condition_index = int(
            np.argmax(
                condition_pred[0]
            )
        )

        condition = CONDITION_CLASSES[
            condition_index
        ]

        condition_confidence = float(
            condition_pred[0][condition_index]
        )


        # ------------------------------
        # Grade
        # ------------------------------

        final_grade = calculate_grade(
            condition
        )


        # ------------------------------
        # Response
        # ------------------------------

        return {
            "waste_type": waste_type,
            "waste_confidence": round(
                waste_confidence,
                4
            ),
            "condition": condition,
            "condition_confidence": round(
                condition_confidence,
                4
            ),
            "final_grade": final_grade,
            "preprocessing": {
                "waste_type": "center_roi",
                "condition": "full_image"
            }
        }


    except Exception as e:

        print(
            "General waste prediction error:",
            str(e)
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e)
            }
        )


# --------------------------------------------------
# E-WASTE ANALYSIS
# --------------------------------------------------

@app.post("/ewaste/analyze")
async def analyze_ewaste(
    image: UploadFile = File(...)
):

    try:

        # ------------------------------
        # Read image
        # ------------------------------

        image_bytes = await image.read()

        if not image_bytes:

            return JSONResponse(
                status_code=400,
                content={
                    "error": "Empty image file"
                }
            )


        # ------------------------------
        # Prepare image
        # ------------------------------

        ewaste_img = prepare_ewaste_image(
            image_bytes
        )


        # ------------------------------
        # YOLO Prediction
        # ------------------------------

        results = ewaste_model.predict(
            source=ewaste_img,
            conf=EWASTE_CONFIDENCE_THRESHOLD,
            imgsz=640,
            verbose=False
        )


        detections = []


        # ------------------------------
        # Process detections
        # ------------------------------

        for result in results:

            for box in result.boxes:

                class_id = int(
                    box.cls[0].item()
                )

                confidence = float(
                    box.conf[0].item()
                )

                class_name = ewaste_model.names[
                    class_id
                ]

                xyxy = box.xyxy[0].tolist()

                hazard_info = (
                    ewaste_knowledge_base.get(
                        class_name,
                        {}
                    )
                )


                detection = {

                    "class_id": class_id,

                    "detected_type": class_name,

                    "confidence": round(
                        confidence,
                        4
                    ),

                    "bbox": {
                        "x1": round(xyxy[0], 2),
                        "y1": round(xyxy[1], 2),
                        "x2": round(xyxy[2], 2),
                        "y2": round(xyxy[3], 2)
                    },

                    "screening_hazard_level":
                        hazard_info.get(
                            "screening_hazard_level",
                            "UNKNOWN"
                        ),

                    "possible_components":
                        hazard_info.get(
                            "possible_components",
                            []
                        ),

                    "possible_hazards":
                        hazard_info.get(
                            "possible_hazards",
                            []
                        ),

                    "recommended_ppe":
                        hazard_info.get(
                            "recommended_ppe",
                            []
                        ),

                    "handling_instructions":
                        hazard_info.get(
                            "handling_instructions",
                            []
                        ),

                    "escalation_rule":
                        hazard_info.get(
                            "escalation_rule",
                            "N/A"
                        ),

                    "certainty_note":
                        hazard_info.get(
                            "certainty_note",
                            "N/A"
                        )
                }

                detections.append(
                    detection
                )


        # Highest confidence first
        detections.sort(
            key=lambda x: x["confidence"],
            reverse=True
        )


        # ------------------------------
        # No Detection
        # ------------------------------

        if not detections:

            return {
                "detected": False,
                "message": (
                    "No supported e-waste object "
                    "detected above the confidence threshold."
                ),
                "confidence_threshold":
                    EWASTE_CONFIDENCE_THRESHOLD,
                "detections": []
            }


        # ------------------------------
        # Successful Response
        # ------------------------------

        return {

            "detected": True,

            "confidence_threshold":
                EWASTE_CONFIDENCE_THRESHOLD,

            "primary_detection":
                detections[0],

            "detections":
                detections,

            "model_scope": (
                "YOLO detects the e-waste device or "
                "component class. Hazard information "
                "is retrieved from the knowledge base "
                "and is not a visual confirmation of "
                "chemical composition."
            )
        }


    except Exception as e:

        print(
            "E-waste analysis error:",
            str(e)
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e)
            }
        )
