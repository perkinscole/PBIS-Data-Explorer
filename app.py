import streamlit as st
from pathlib import Path
from utils.theme import apply_theme

st.set_page_config(
    page_title="RAMS CARE Data Viewer",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

logo_path = Path(__file__).parent / "assets" / "logo.png"

# --- Main page ---
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

**Get started** using the sidebar:

1. **Upload Data** -- Load your survey files
2. **Dashboard** -- Explore visualizations of survey results
3. **Trends** -- Compare results across survey periods
4. **Cohorts** -- Track grade cohorts over time (per question, per category)
5. **Insights** -- Outlier detection, sentiment analysis, and cross-question patterns
6. **Survey Development** -- Analyze and improve survey questions
7. **Benchmarks** -- Compare RAMS results against MetroWest regional data
8. **Compare** -- Side-by-side before/after survey comparison
9. **Report** -- Generate downloadable summary reports
10. **Goals (Beta)** -- Set and track progress toward PBIS targets
11. **Actions** -- Data-driven recommendations for improvement
12. **Feedback** -- Report bugs or request new features
""")

# Initialize session state for shared data
if "surveys" not in st.session_state:
    st.session_state.surveys = []
if "survey_meta" not in st.session_state:
    st.session_state.survey_meta = []

st.sidebar.caption("RAMS CARE Data Viewer v1.1")
