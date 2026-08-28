from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = Path.home() / "waste_sorting"
CSV_FILE = BASE_DIR / "waste_results.csv"
CAPTURE_DIR = BASE_DIR / "captures"

st.set_page_config(
    page_title="AI Waste Assessment Dashboard",
    page_icon="♻️",
    layout="wide"
)

# Refresh every 2 seconds
st_autorefresh(interval=2000, key="waste_dashboard_refresh")

st.title("♻️ Live AI Waste Assessment Dashboard")
st.caption("Real-time Waste Type, Condition, Weight and Decision Monitoring")

# -----------------------------
# LOAD DATA
# -----------------------------
if not CSV_FILE.exists():
    st.warning("No waste assessment results found yet.")
    st.stop()

try:
    df = pd.read_csv(CSV_FILE)
except Exception as e:
    st.error(f"Could not read results file: {e}")
    st.stop()

if df.empty:
    st.warning("The results file is empty.")
    st.stop()

latest = df.iloc[-1]

# -----------------------------
# LATEST IMAGE
# -----------------------------
st.subheader("Latest Waste Assessment")

left, right = st.columns([1, 2])

with left:
    image_name = str(latest.get("image_name", ""))
    image_path = CAPTURE_DIR / image_name

    if image_path.exists():
        st.image(
            str(image_path),
            caption="Latest Captured Waste Image",
            use_container_width=True
        )
    else:
        st.info("Latest captured image not found.")

with right:
    weight = latest.get("weight_g", 0)
    waste_type = latest.get("waste_type", "Unknown")
    waste_conf = latest.get("waste_confidence", 0)
    condition = latest.get("condition", "Unknown")
    condition_conf = latest.get("condition_confidence", 0)
    grade = latest.get("final_grade", "Unknown")
    status = latest.get("status", "Unknown")

    try:
        waste_conf_pct = float(waste_conf) * 100
    except:
        waste_conf_pct = 0

    try:
        condition_conf_pct = float(condition_conf) * 100
    except:
        condition_conf_pct = 0

    row1 = st.columns(3)

    row1[0].metric(
        "⚖️ Weight",
        f"{float(weight):.2f} g"
    )

    row1[1].metric(
        "🗑️ Waste Type",
        str(waste_type)
    )

    row1[2].metric(
        "Waste Confidence",
        f"{waste_conf_pct:.1f}%"
    )

    row2 = st.columns(3)

    row2[0].metric(
        "🔎 Condition",
        str(condition)
    )

    row2[1].metric(
        "Condition Confidence",
        f"{condition_conf_pct:.1f}%"
    )

    display_grade = grade

    if str(status).upper() == "REVIEW":
        display_grade = "REVIEW"

    row2[2].metric(
        "🏷️ Final Decision",
        str(display_grade)
    )

    if str(status).upper() == "ACCEPTED":
        st.success("✅ Status: ACCEPTED")
    elif str(status).upper() == "REVIEW":
        st.warning("⚠️ Status: REVIEW - Manual verification required")
    else:
        st.info(f"Status: {status}")

# -----------------------------
# SUMMARY
# -----------------------------
st.divider()
st.subheader("Assessment Summary")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Total Assessments",
    len(df)
)

accepted_count = (
    df["status"].astype(str).str.upper().eq("ACCEPTED").sum()
    if "status" in df.columns else 0
)

review_count = (
    df["status"].astype(str).str.upper().eq("REVIEW").sum()
    if "status" in df.columns else 0
)

c2.metric(
    "Accepted",
    int(accepted_count)
)

c3.metric(
    "Review",
    int(review_count)
)

if "weight_g" in df.columns:
    avg_weight = pd.to_numeric(
        df["weight_g"],
        errors="coerce"
    ).mean()

    c4.metric(
        "Average Weight",
        f"{avg_weight:.2f} g"
    )

# -----------------------------
# MATERIAL COUNTS
# -----------------------------
if "waste_type" in df.columns:
    st.subheader("Waste Type Distribution")

    waste_counts = (
        df["waste_type"]
        .value_counts()
        .rename_axis("Waste Type")
        .reset_index(name="Count")
    )

    st.bar_chart(
        waste_counts.set_index("Waste Type")
    )

# -----------------------------
# RECENT RESULTS
# -----------------------------
st.subheader("Recent Assessments")

columns_to_show = [
    "timestamp",
    "weight_g",
    "waste_type",
    "waste_confidence",
    "condition",
    "condition_confidence",
    "final_grade",
    "status"
]

available_columns = [
    c for c in columns_to_show
    if c in df.columns
]

recent = df[available_columns].tail(10).copy()
recent = recent.iloc[::-1]

if "waste_confidence" in recent.columns:
    recent["waste_confidence"] = (
        pd.to_numeric(
            recent["waste_confidence"],
            errors="coerce"
        ) * 100
    ).round(1)

if "condition_confidence" in recent.columns:
    recent["condition_confidence"] = (
        pd.to_numeric(
            recent["condition_confidence"],
            errors="coerce"
        ) * 100
    ).round(1)

st.dataframe(
    recent,
    use_container_width=True,
    hide_index=True
)

st.caption("Dashboard automatically refreshes every 2 seconds.")
