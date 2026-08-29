import os
import csv
import re
import time
from datetime import datetime
from pathlib import Path

import requests
import serial

# Load .env file if present (python-dotenv).  Falls back to real
# environment variables or the original defaults if .env is absent.
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "backend" / ".env")
except ImportError:
    pass  # python-dotenv not installed — plain os.environ only


# ==================================================
# CONFIGURATION
# ==================================================

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyACM0")
BAUD_RATE   = int(os.getenv("BAUD_RATE", "9600"))

# ESP32-CAM
CAMERA_URL = os.getenv("CAMERA_URL", "http://10.156.150.180/capture")

# FastAPI backend (Component 1, port 8001)
GENERAL_BACKEND_URL = os.getenv("GENERAL_BACKEND_URL", "http://localhost:8001/waste/predict")
EWASTE_BACKEND_URL  = os.getenv("EWASTE_BACKEND_URL",  "http://localhost:8001/ewaste/analyze")

# Weight thresholds
TRIGGER_WEIGHT_G = 20.0
RESET_WEIGHT_G = 5.0

# General waste confidence thresholds
MIN_WASTE_CONFIDENCE = 0.60
MIN_CONDITION_CONFIDENCE = 0.60


# ==================================================
# PATHS
# ==================================================

BASE_DIR = Path.home() / "waste_sorting"

OUTPUT_DIR = BASE_DIR / "captures"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

GENERAL_LOG_FILE = BASE_DIR / "waste_results.csv"
EWASTE_LOG_FILE = BASE_DIR / "ewaste_results.csv"


# ==================================================
# MODE SELECTION
# ==================================================

print("\n================================")
print(" Smart Waste Assessment System ")
print("================================")
print("1 = General Waste")
print("2 = E-Waste")
print("================================")

mode_choice = input(
    "Select mode (1 or 2): "
).strip()

if mode_choice == "1":
    SYSTEM_MODE = "GENERAL"

elif mode_choice == "2":
    SYSTEM_MODE = "EWASTE"

else:
    print("Invalid mode selected.")
    raise SystemExit(1)


# ==================================================
# CAPTURE IMAGE
# ==================================================

def capture_image(weight):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    if SYSTEM_MODE == "EWASTE":
        prefix = "ewaste"
    else:
        prefix = "waste"

    filename = (
        f"{prefix}_{timestamp}_"
        f"{weight:.2f}g.jpg"
    )

    output_path = OUTPUT_DIR / filename

    print(
        "\nCapturing image from ESP32-CAM..."
    )

    response = requests.get(
        CAMERA_URL,
        timeout=20
    )

    response.raise_for_status()

    if not response.content.startswith(
        b"\xff\xd8"
    ):
        raise ValueError(
            "Camera did not return a valid JPEG image"
        )

    output_path.write_bytes(
        response.content
    )

    print("\nPhoto captured successfully")
    print(f"Saved to: {output_path}")

    return output_path


# ==================================================
# GENERAL WASTE ANALYSIS
# ==================================================

def analyze_general_waste(
    image_path,
    weight
):

    print(
        "\nSending image to General Waste AI..."
    )

    with open(
        image_path,
        "rb"
    ) as image_file:

        response = requests.post(
            GENERAL_BACKEND_URL,
            files={
                "image": (
                    image_path.name,
                    image_file,
                    "image/jpeg"
                )
            },
            timeout=60
        )

    response.raise_for_status()

    result = response.json()

    waste_type = result.get(
        "waste_type",
        "Unknown"
    )

    waste_confidence = float(
        result.get(
            "waste_confidence",
            0
        )
    )

    condition = result.get(
        "condition",
        "Unknown"
    )

    condition_confidence = float(
        result.get(
            "condition_confidence",
            0
        )
    )

    final_grade = result.get(
        "final_grade",
        "Unknown"
    )


    needs_review = (
        waste_confidence
        < MIN_WASTE_CONFIDENCE
        or
        condition_confidence
        < MIN_CONDITION_CONFIDENCE
    )

    if needs_review:

        display_grade = "REVIEW"
        log_status = "REVIEW"

        status = (
            "Low confidence - "
            "manual verification required"
        )

    else:

        display_grade = final_grade
        log_status = "ACCEPTED"
        status = "Prediction accepted"


    print("\n================================")
    print("     GENERAL WASTE ASSESSMENT")
    print("================================")

    print(
        f"Weight       : "
        f"{weight:.2f} g"
    )

    print(
        f"Waste Type   : "
        f"{waste_type} "
        f"({waste_confidence * 100:.2f}%)"
    )

    print(
        f"Condition    : "
        f"{condition} "
        f"({condition_confidence * 100:.2f}%)"
    )

    print(
        f"Final Grade  : "
        f"{display_grade}"
    )

    print(
        f"Status       : "
        f"{status}"
    )

    print("================================\n")


    result["log_status"] = log_status
    result["display_grade"] = display_grade

    return result


# ==================================================
# E-WASTE ANALYSIS
# ==================================================

def analyze_ewaste(
    image_path,
    weight
):

    print(
        "\nSending image to E-Waste AI..."
    )

    with open(
        image_path,
        "rb"
    ) as image_file:

        response = requests.post(
            EWASTE_BACKEND_URL,
            files={
                "image": (
                    image_path.name,
                    image_file,
                    "image/jpeg"
                )
            },
            timeout=60
        )

    response.raise_for_status()

    result = response.json()


    if not result.get(
        "detected",
        False
    ):

        print("\n================================")
        print("       E-WASTE ASSESSMENT")
        print("================================")

        print(
            f"Weight       : "
            f"{weight:.2f} g"
        )

        print(
            "Detection    : "
            "No supported e-waste object"
        )

        print(
            "Status       : REVIEW"
        )

        print("================================\n")

        result["log_status"] = "REVIEW"

        return result


    primary = result.get(
        "primary_detection",
        {}
    )

    detected_type = primary.get(
        "detected_type",
        "Unknown"
    )

    confidence = float(
        primary.get(
            "confidence",
            0
        )
    )

    hazard_level = primary.get(
        "screening_hazard_level",
        "UNKNOWN"
    )

    possible_hazards = primary.get(
        "possible_hazards",
        []
    )

    recommended_ppe = primary.get(
        "recommended_ppe",
        []
    )

    handling = primary.get(
        "handling_instructions",
        []
    )

    certainty_note = primary.get(
        "certainty_note",
        "N/A"
    )


    print("\n================================")
    print("       E-WASTE ASSESSMENT")
    print("================================")

    print(
        f"Weight       : "
        f"{weight:.2f} g"
    )

    print(
        f"Detected Type: "
        f"{detected_type}"
    )

    print(
        f"Confidence   : "
        f"{confidence * 100:.2f}%"
    )

    print(
        f"Hazard Level : "
        f"{hazard_level}"
    )


    print("\nPossible Hazards:")

    for item in possible_hazards:
        print(
            f"  - {item}"
        )


    print("\nRecommended PPE:")

    for item in recommended_ppe:
        print(
            f"  - {item}"
        )


    print("\nHandling Instructions:")

    for item in handling:
        print(
            f"  - {item}"
        )


    print("\nCertainty Note:")

    print(
        f"  {certainty_note}"
    )


    print("\n================================")

    print(
        "Hazard guidance is retrieved from "
        "the knowledge base."
    )

    print(
        "Chemical composition is not "
        "visually confirmed by YOLO."
    )

    print("================================\n")


    result["log_status"] = "DETECTED"

    return result


# ==================================================
# GENERAL WASTE CSV LOG
# ==================================================

def log_general_result(
    image_path,
    weight,
    result
):

    file_exists = GENERAL_LOG_FILE.exists()

    waste_confidence = float(
        result.get(
            "waste_confidence",
            0
        )
    )

    condition_confidence = float(
        result.get(
            "condition_confidence",
            0
        )
    )

    with open(
        GENERAL_LOG_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.writer(
            csv_file
        )

        if not file_exists:

            writer.writerow([
                "timestamp",
                "image_name",
                "weight_g",
                "waste_type",
                "waste_confidence",
                "condition",
                "condition_confidence",
                "final_grade",
                "status"
            ])

        writer.writerow([
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            image_path.name,

            round(
                weight,
                2
            ),

            result.get(
                "waste_type",
                "Unknown"
            ),

            round(
                waste_confidence,
                4
            ),

            result.get(
                "condition",
                "Unknown"
            ),

            round(
                condition_confidence,
                4
            ),

            result.get(
                "final_grade",
                "Unknown"
            ),

            result.get(
                "log_status",
                "UNKNOWN"
            )
        ])

    print(
        f"General waste result logged to: "
        f"{GENERAL_LOG_FILE}\n"
    )


# ==================================================
# E-WASTE CSV LOG
# ==================================================

def log_ewaste_result(
    image_path,
    weight,
    result
):

    file_exists = EWASTE_LOG_FILE.exists()

    primary = result.get(
        "primary_detection",
        {}
    )

    detected_type = primary.get(
        "detected_type",
        "Unknown"
    )

    confidence = float(
        primary.get(
            "confidence",
            0
        )
    )

    hazard_level = primary.get(
        "screening_hazard_level",
        "UNKNOWN"
    )

    hazards = " | ".join(
        primary.get(
            "possible_hazards",
            []
        )
    )

    ppe = " | ".join(
        primary.get(
            "recommended_ppe",
            []
        )
    )

    handling = " | ".join(
        primary.get(
            "handling_instructions",
            []
        )
    )


    with open(
        EWASTE_LOG_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.writer(
            csv_file
        )

        if not file_exists:

            writer.writerow([
                "timestamp",
                "image_name",
                "weight_g",
                "detected_type",
                "confidence",
                "screening_hazard_level",
                "possible_hazards",
                "recommended_ppe",
                "handling_instructions",
                "status"
            ])

        writer.writerow([
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            image_path.name,

            round(
                weight,
                2
            ),

            detected_type,

            round(
                confidence,
                4
            ),

            hazard_level,

            hazards,

            ppe,

            handling,

            result.get(
                "log_status",
                "UNKNOWN"
            )
        ])

    print(
        f"E-waste result logged to: "
        f"{EWASTE_LOG_FILE}\n"
    )


# ==================================================
# SYSTEM START
# ==================================================

print("\n================================")

if SYSTEM_MODE == "GENERAL":

    print(" Mode: GENERAL WASTE")

    print(
        f"Backend: "
        f"{GENERAL_BACKEND_URL}"
    )

else:

    print(" Mode: E-WASTE")

    print(
        f"Backend: "
        f"{EWASTE_BACKEND_URL}"
    )

print(
    f"Trigger weight: "
    f"{TRIGGER_WEIGHT_G} g"
)

print(
    f"Camera: "
    f"{CAMERA_URL}"
)

print("================================")

print(
    "\nPlace an item on the load cell\n"
)


armed = True


# ==================================================
# SERIAL / LOAD CELL LOOP
# ==================================================

try:

    with serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=2
    ) as arduino:

        # Arduino may restart when serial opens
        time.sleep(2)


        while True:

            line = (
                arduino
                .readline()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
                .strip()
            )

            if not line:
                continue


            print(line)


            # Expected:
            # Weight: 45.69 g

            match = re.search(
                r"Weight:\s*"
                r"(-?\d+(?:\.\d+)?)"
                r"\s*g",
                line
            )

            if not match:
                continue


            weight = float(
                match.group(1)
            )


            if abs(weight) < 1.0:
                weight = 0.0


            # ======================================
            # ITEM DETECTED
            # ======================================

            if (
                armed
                and
                weight >= TRIGGER_WEIGHT_G
            ):

                print(
                    f"\nItem detected: "
                    f"{weight:.2f} g"
                )


                try:

                    image_path = capture_image(
                        weight
                    )


                    if SYSTEM_MODE == "GENERAL":

                        result = (
                            analyze_general_waste(
                                image_path,
                                weight
                            )
                        )

                        log_general_result(
                            image_path,
                            weight,
                            result
                        )


                    else:

                        result = (
                            analyze_ewaste(
                                image_path,
                                weight
                            )
                        )

                        log_ewaste_result(
                            image_path,
                            weight,
                            result
                        )


                    armed = False


                except (
                    requests
                    .exceptions
                    .RequestException
                ) as error:

                    print(
                        "\nNetwork/API error: "
                        f"{error}"
                    )

                    armed = False


                except Exception as error:

                    print(
                        "\nProcessing failed: "
                        f"{error}"
                    )

                    armed = False


            # ======================================
            # ITEM REMOVED
            # ======================================

            elif (
                not armed
                and
                weight <= RESET_WEIGHT_G
            ):

                print(
                    "\nItem removed"
                )

                print(
                    "System ready for "
                    "the next item\n"
                )

                armed = True


# ==================================================
# STOP / ERRORS
# ==================================================

except KeyboardInterrupt:

    print(
        "\nSystem stopped by user"
    )


except serial.SerialException as error:

    print(
        "Arduino serial error: "
        f"{error}"
    )


except Exception as error:

    print(
        "System error: "
        f"{error}"
    )
