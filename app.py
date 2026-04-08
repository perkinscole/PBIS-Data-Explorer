import streamlit as st

st.set_page_config(
    page_title="RAMS CARE Data Explorer",
    page_icon="🐏",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("RAMS CARE Data Explorer")
st.markdown("### PBIS Survey Analysis & Development Tool")

st.markdown("""
Welcome to the RAMS CARE Data Explorer! This tool helps the RAMS CARE team:

- **Upload** survey spreadsheets (.xlsx or .csv)
- **Visualize** survey results with interactive charts
- **Track trends** across survey periods
- **Develop** better survey questions

---

**Get started** by navigating to a page in the sidebar:

1. **Upload Data** - Load your survey files
2. **Dashboard** - Explore visualizations of survey results
3. **Trends** - Compare results across survey periods
4. **Survey Development** - Analyze and improve survey questions
""")

# Initialize session state for shared data
if "surveys" not in st.session_state:
    st.session_state.surveys = []
if "survey_meta" not in st.session_state:
    st.session_state.survey_meta = []

st.sidebar.markdown("---")
st.sidebar.caption("RAMS CARE (PBIS) Data Explorer v1.0")
