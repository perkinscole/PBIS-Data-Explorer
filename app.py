import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="RAMS CARE Data Viewer",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for shared data
if "surveys" not in st.session_state:
    st.session_state.surveys = []
if "survey_meta" not in st.session_state:
    st.session_state.survey_meta = []

# Define pages with section grouping
pages = {
    "": [
        st.Page("pages/00_Home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Data": [
        st.Page("pages/01_Upload.py", title="Upload", icon=":material/upload_file:"),
    ],
    "Analysis": [
        st.Page("pages/02_Survey_Dashboard.py", title="Survey Dashboard", icon=":material/dashboard:"),
        st.Page("pages/03_Trends.py", title="Trends", icon=":material/trending_up:"),
        st.Page("pages/04_Cohorts.py", title="Cohorts", icon=":material/group:"),
        st.Page("pages/05_1:1_Compare.py", title="1:1 Compare", icon=":material/compare_arrows:"),
        st.Page("pages/06_MetroWest_Benchmarks.py", title="MetroWest Benchmarks", icon=":material/leaderboard:"),
        st.Page("pages/07_Insights.py", title="Insights", icon=":material/psychology:"),
    ],
    "Planning": [
        st.Page("pages/08_Survey_Dev.py", title="Survey Development", icon=":material/edit_note:"),
        st.Page("pages/09_Goals_(Beta).py", title="Goals (Beta)", icon=":material/flag:"),
        st.Page("pages/10_Actions.py", title="Actions", icon=":material/checklist:"),
        st.Page("pages/11_Report.py", title="Report", icon=":material/description:"),
    ],
    "Support": [
        st.Page("pages/12_Feedback.py", title="Feedback", icon=":material/feedback:"),
    ],
}

pg = st.navigation(pages)

# Sidebar extras
st.sidebar.markdown("---")
st.sidebar.caption("RAMS CARE Data Viewer v1.1")

pg.run()
