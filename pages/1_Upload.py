import streamlit as st
import pandas as pd
import json
import os
import shutil
from pathlib import Path
from utils.data_loader import load_survey_file, load_all_surveys, parse_filename
from utils.theme import apply_theme

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
META_FILE = DATA_DIR / "_metadata.json"

MONTHS = [
    "January", "February", "March", "April", "May", "May-June",
    "June", "July", "August", "September", "October", "November", "December",
]

SURVEY_TYPES = [None, 1, 2, 3]


def save_overrides(overrides):
    """Save period/survey overrides to a JSON file alongside the data."""
    DATA_DIR.mkdir(exist_ok=True)
    META_FILE.write_text(json.dumps(overrides, indent=2))


def load_overrides():
    """Load saved overrides."""
    if META_FILE.exists():
        return json.loads(META_FILE.read_text())
    return {}


st.title("Upload Survey Data")

# Load sample data option (only show if sample_data folder exists locally)
if SAMPLE_DIR.exists() and list(SAMPLE_DIR.glob("*.xlsx")):
    st.markdown("### Quick Start")
    if st.button("Load Sample Data", help="Load the included example survey files"):
        DATA_DIR.mkdir(exist_ok=True)
        for f in SAMPLE_DIR.glob("*.xlsx"):
            shutil.copy2(f, DATA_DIR / f.name)
        st.session_state.surveys = []
        st.session_state.survey_meta = []
        st.success(f"Loaded {len(list(SAMPLE_DIR.glob('*.xlsx')))} sample survey files!")
        st.rerun()
    st.markdown("---")

# File upload
st.markdown("### Upload Survey Files")
uploaded_files = st.file_uploader(
    "Drop survey spreadsheets here (.xlsx or .csv)",
    type=["xlsx", "csv"],
    accept_multiple_files=True,
)

if uploaded_files:
    DATA_DIR.mkdir(exist_ok=True)
    for f in uploaded_files:
        dest = DATA_DIR / f.name
        with open(dest, "wb") as out:
            out.write(f.getbuffer())

    # Show confirmation UI for newly uploaded files
    st.markdown("---")
    st.markdown("### Confirm Survey Details")
    st.markdown(
        "We auto-detected the survey period from each filename. "
        "**Verify or change** the details below, then click **Confirm**."
    )

    overrides = load_overrides()

    for f in uploaded_files:
        detected = parse_filename(f.name)
        st.markdown(f"**{f.name}**")

        col1, col2, col3 = st.columns(3)

        # Month picker
        detected_month = None
        if detected["period"] != "Unknown":
            month_str = detected["period"].rsplit(" ", 1)[0]
            if month_str in MONTHS:
                detected_month = MONTHS.index(month_str)

        with col1:
            month = st.selectbox(
                "Month",
                MONTHS,
                index=detected_month if detected_month is not None else 0,
                key=f"month_{f.name}",
            )

        # Year picker
        detected_year = None
        if detected["period"] != "Unknown":
            try:
                detected_year = int(detected["period"].rsplit(" ", 1)[1])
            except (ValueError, IndexError):
                pass

        with col2:
            year = st.number_input(
                "Year",
                min_value=2020,
                max_value=2035,
                value=detected_year or 2026,
                key=f"year_{f.name}",
            )

        # Survey type
        with col3:
            survey_type = st.selectbox(
                "Survey Type",
                SURVEY_TYPES,
                index=SURVEY_TYPES.index(detected["survey_num"]) if detected["survey_num"] in SURVEY_TYPES else 0,
                format_func=lambda x: f"Student #{x}" if x else "Auto-detect",
                key=f"type_{f.name}",
            )

        overrides[f.name] = {
            "period": f"{month} {year}",
            "survey_num": survey_type,
        }

    if st.button("Confirm & Load", type="primary"):
        save_overrides(overrides)
        st.session_state.surveys = []
        st.session_state.survey_meta = []
        st.success(f"Saved {len(uploaded_files)} file(s) with confirmed details!")
        st.rerun()

st.markdown("---")

# Show currently loaded data
st.markdown("### Current Data Files")

if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
    # Load overrides for label display
    overrides = load_overrides()

    # Load all surveys if not cached
    if not st.session_state.get("surveys"):
        all_data, all_meta = load_all_surveys(str(DATA_DIR))

        # Apply any saved overrides
        for i, (df, meta) in enumerate(zip(all_data, all_meta)):
            fname = df["_source_file"].iloc[0] if len(df) > 0 else ""
            if fname in overrides:
                ov = overrides[fname]
                meta["period"] = ov["period"]
                if ov.get("survey_num"):
                    meta["survey_num"] = ov["survey_num"]
                meta["label"] = (
                    f"Survey #{meta['survey_num']} - {meta['period']}"
                    if meta["survey_num"]
                    else meta["period"]
                )
                # Update the DataFrame internal columns too
                all_data[i]["_period"] = meta["period"]
                all_data[i]["_label"] = meta["label"]
                if ov.get("survey_num"):
                    all_data[i]["_survey_num"] = meta["survey_num"]

        st.session_state.surveys = all_data
        st.session_state.survey_meta = all_meta

    for i, (df, meta) in enumerate(zip(st.session_state.surveys, st.session_state.survey_meta)):
        with st.expander(f"{meta['label']} ({len(df)} responses)"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Responses", len(df))
            with col2:
                if "_grade" in df.columns:
                    grades = df["_grade"].value_counts()
                    st.metric("Grade Levels", len(grades))

            st.markdown("**Preview:**")
            display_cols = [c for c in df.columns if not c.startswith("_")]
            st.dataframe(df[display_cols].head(10), use_container_width=True)
else:
    st.info("No data loaded yet. Upload survey files above to get started.")

# Clear data option
if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
    st.markdown("---")
    if st.button("Clear All Data", type="secondary"):
        for f in DATA_DIR.glob("*"):
            f.unlink()
        st.session_state.surveys = []
        st.session_state.survey_meta = []
        st.rerun()
