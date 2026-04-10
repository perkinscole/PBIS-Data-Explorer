import streamlit as st
from pathlib import Path
import base64

THEME_CSS = """
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }
    [data-testid="stSidebar"] * {
        color: #f0f0f0 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label {
        color: #f0f0f0 !important;
    }
    /* Dropdown option text should be black (readable on white background) */
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="select"] div[role="option"],
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * {
        color: #1a1a1a !important;
    }

    /* Sidebar nav links */
    [data-testid="stSidebarNav"] a {
        color: #f0f0f0 !important;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #8b1a1a !important;
    }
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #a62626 !important;
        font-weight: bold;
    }

    /* Uppercase the "app" nav item (home page) */
    [data-testid="stSidebarNav"] a[href="/"] span,
    [data-testid="stSidebarNav"] li:first-child a span {
        text-transform: uppercase;
    }

    /* Header bar */
    header[data-testid="stHeader"] {
        background-color: #8b1a1a;
    }

    /* Logo in header */
    .header-logo {
        position: fixed;
        top: 6px;
        left: 12px;
        z-index: 999999;
    }
    .header-logo img {
        height: 40px;
        width: 40px;
        border-radius: 50%;
    }

    /* Top accent line */
    .block-container {
        border-top: 4px solid #8b1a1a;
        padding-top: 2rem;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #fdf2f2;
        border: 1px solid #e8c4c4;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetric"] label {
        color: #1a1a1a !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #8b1a1a !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #8b1a1a;
        color: white;
        border: none;
        border-radius: 6px;
    }
    .stButton > button:hover {
        background-color: #a62626;
        color: white;
        border: none;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        color: #1a1a1a;
    }
    .stTabs [aria-selected="true"] {
        border-bottom-color: #8b1a1a !important;
        color: #8b1a1a !important;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #fdf2f2;
        border-radius: 6px;
    }

    /* Links */
    a {
        color: #8b1a1a !important;
    }


</style>
"""


def _get_logo_b64():
    """Load and base64-encode the logo for embedding in HTML."""
    logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return None


ALL_SURVEY_TYPES = ["All Types", "Student", "Staff", "Parents and Family"]


def apply_theme(collapse_nav=False):
    """Apply the RAMS CARE red/black theme to the current page."""
    logo_b64 = _get_logo_b64()

    # Inject CSS
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Logo in top-left of header bar
    if logo_b64:
        st.markdown(
            f'<div class="header-logo">'
            f'<img src="data:image/png;base64,{logo_b64}" alt="RAMS Logo">'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Optionally collapse all nav sections (used on Home page)
    if collapse_nav:
        st.html("""
            <script>
            function collapseNav() {
                const doc = window.parent.document;
                const details = doc.querySelectorAll('[data-testid="stSidebarNav"] details[open]');
                details.forEach(el => el.removeAttribute('open'));
            }
            collapseNav();
            setTimeout(collapseNav, 100);
            setTimeout(collapseNav, 300);
            setTimeout(collapseNav, 600);
            </script>
        """)



def get_filter_container():
    """Return a bordered st.container for filter widgets. Use with `with` block."""
    st.subheader("Survey Selector")
    return st.container(border=True)


def get_survey_type_filter():
    """Add a survey type filter as horizontal radio buttons.
    Returns the selected type string, or 'All Types'."""
    selected = st.radio(
        "Survey Type",
        ALL_SURVEY_TYPES,
        horizontal=True,
        key="survey_type_filter",
    )
    return selected


def end_control_panel():
    """Legacy no-op."""
    pass


def _infer_survey_type(meta):
    """Infer the survey type from metadata, handling old numeric types
    and auto-detecting from label/filename keywords."""
    survey_type = meta.get("survey_num")

    # Already a recognized string type
    if survey_type in ("Student", "Staff", "Parents and Family"):
        return survey_type

    # Old numeric types (1, 2, 3) from the original Student surveys
    if survey_type in (1, 2, 3):
        return "Student"

    # Try to detect from label or source file
    label = str(meta.get("label", "")).lower()
    source = str(meta.get("source_file", "")).lower()
    text = label + " " + source

    if "student" in text:
        return "Student"
    elif "staff" in text:
        return "Staff"
    elif "parent" in text or "family" in text:
        return "Parents and Family"
    return None


def filter_surveys_by_type(surveys, meta, selected_type):
    """Filter surveys and metadata by the selected survey type.
    Returns (filtered_surveys, filtered_meta)."""
    if selected_type == "All Types":
        return surveys, meta

    filtered_surveys = []
    filtered_meta = []
    for df, m in zip(surveys, meta):
        inferred = _infer_survey_type(m)
        if inferred == selected_type:
            filtered_surveys.append(df)
            filtered_meta.append(m)

    return filtered_surveys, filtered_meta


def get_audience_label(selected_type):
    """Return the human-friendly audience label for display text.
    E.g., 'students', 'staff members', 'parents and families'."""
    labels = {
        "Student": "students",
        "Staff": "staff members",
        "Parents and Family": "parents and families",
        "All Types": "respondents",
    }
    return labels.get(selected_type, "respondents")
