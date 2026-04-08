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


def apply_theme():
    """Apply the RAMS CARE red/black theme to the current page."""
    logo_b64 = _get_logo_b64()

    # Inject CSS (use .format since we have { } escaped braces in the template)
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Logo in top-left of header bar
    if logo_b64:
        st.markdown(
            f'<div class="header-logo">'
            f'<img src="data:image/png;base64,{logo_b64}" alt="RAMS Logo">'
            f'</div>',
            unsafe_allow_html=True,
        )
