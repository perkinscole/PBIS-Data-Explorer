import streamlit as st
from pathlib import Path
from utils.theme import apply_theme

apply_theme()

logo_path = Path(__file__).parent.parent / "assets" / "logo.png"

col1, col2 = st.columns([1, 4])
with col1:
    if logo_path.exists():
        st.image(str(logo_path), width=120)
with col2:
    st.markdown("# RAMS CARE Data Viewer")
    st.markdown("*PBIS Survey Analysis & Insights*")

st.markdown("""
---

Welcome to the **RAMS CARE Data Viewer**! This tool helps the CARE team upload survey
spreadsheets, visualize results, track trends over time, and develop stronger survey questions.

**Get started** by uploading your survey files, then explore the pages in the sidebar.

**Data** — Upload your survey files

**Analysis** — Survey Dashboard, Trends, Cohorts, 1:1 Compare, MetroWest Benchmarks, Insights

**Planning** — Survey Development, Goals, Actions, Report

**Support** — Feedback & bug reports
""")
