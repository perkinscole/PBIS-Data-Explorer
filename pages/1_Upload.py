import streamlit as st
import pandas as pd
import os
import shutil
from pathlib import Path
from utils.data_loader import load_survey_file, load_all_surveys, parse_filename
from utils.theme import apply_theme

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"

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
    st.success(f"Saved {len(uploaded_files)} file(s)!")
    st.session_state.surveys = []
    st.session_state.survey_meta = []

st.markdown("---")

# Show currently loaded data
st.markdown("### Current Data Files")

if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
    # Load all surveys if not cached
    if not st.session_state.surveys:
        all_data, all_meta = load_all_surveys(str(DATA_DIR))
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
