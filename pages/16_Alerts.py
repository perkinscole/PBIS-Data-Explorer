import streamlit as st
import pandas as pd
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    match_category, normalize_column_name, QUESTION_CATEGORIES,
)
from utils.alerts import load_alerts, save_alerts, check_alerts
from utils.theme import apply_theme, get_survey_type_filter, get_filter_container, filter_surveys_by_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Alerts")
st.markdown("Set thresholds for key indicators. When data crosses a threshold, alerts fire.")

if not st.session_state.get("surveys"):
    if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
        all_data, all_meta = load_all_surveys(str(DATA_DIR))
        st.session_state.surveys = all_data
        st.session_state.survey_meta = all_meta
    else:
        st.warning("No data loaded. Go to the Upload page first.")
        st.stop()

with get_filter_container():
    selected_type = get_survey_type_filter()
    surveys, meta = filter_surveys_by_type(
        st.session_state.surveys, st.session_state.survey_meta, selected_type
    )

if not surveys:
    st.info(f"No {selected_type} surveys loaded.")
    st.stop()

# Compute current % positive for all indicators (latest survey)
df = surveys[-1]
cat_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}
current_pcts = {}

# Category-level
cat_vals = {}
for col in get_likert_columns(df):
    cat = match_category(col)
    valid = df[col].dropna()
    if len(valid) > 0:
        pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
        pct = pos / len(valid) * 100
        q_name = normalize_column_name(col)[:60]
        current_pcts[q_name] = round(pct, 1)
        if cat:
            cat_vals.setdefault(cat, []).append(pct)

for col in get_yes_no_columns(df):
    cat = match_category(col)
    valid = df[col].dropna()
    if len(valid) > 0:
        pos = (valid == "Yes").sum()
        pct = pos / len(valid) * 100
        q_name = normalize_column_name(col)[:60]
        current_pcts[q_name] = round(pct, 1)
        if cat:
            cat_vals.setdefault(cat, []).append(pct)

for cat, vals in cat_vals.items():
    current_pcts[cat_labels[cat]] = round(sum(vals) / len(vals), 1)

# Load and check alerts
alerts = load_alerts(str(DATA_DIR))
results = check_alerts(alerts, current_pcts)

# Show alert status
if results:
    fired = [(a, v) for a, f, v in results if f is True]
    passing = [(a, v) for a, f, v in results if f is False]
    no_data = [(a, v) for a, f, v in results if f is None]

    cols = st.columns(3)
    cols[0].metric("Fired", len(fired), help="Alerts that crossed the threshold")
    cols[1].metric("Passing", len(passing), help="Indicators within safe range")
    if no_data:
        cols[2].metric("No Data", len(no_data))

    st.markdown("---")

    if fired:
        st.markdown("### Fired Alerts")
        for alert, current in fired:
            st.markdown(
                f'<div style="background-color:#fadbd8; border-left:5px solid #e74c3c; '
                f'padding:12px 16px; border-radius:6px; margin-bottom:8px;">'
                f'<strong>{alert["indicator"]}</strong> is at '
                f'<strong>{current:.0f}%</strong> '
                f'(threshold: {alert["direction"]} {alert["threshold"]}%)'
                f'</div>',
                unsafe_allow_html=True,
            )

    if passing:
        st.markdown("### Passing")
        for alert, current in passing:
            st.markdown(
                f'<div style="background-color:#d5f5e3; border-left:5px solid #27ae60; '
                f'padding:12px 16px; border-radius:6px; margin-bottom:8px;">'
                f'<strong>{alert["indicator"]}</strong> is at '
                f'<strong>{current:.0f}%</strong> '
                f'(threshold: {alert["direction"]} {alert["threshold"]}%)'
                f'</div>',
                unsafe_allow_html=True,
            )
else:
    st.info("No alerts set yet. Create your first alert below.")

# Manage alerts
st.markdown("---")
st.markdown("### Manage Alerts")

# Delete buttons
if alerts:
    for i, alert in enumerate(alerts):
        col1, col2 = st.columns([5, 1])
        col1.markdown(f"**{alert['indicator']}** — {alert['direction']} {alert['threshold']}%")
        if col2.button("Delete", key=f"del_alert_{i}"):
            alerts.pop(i)
            save_alerts(str(DATA_DIR), alerts)
            st.rerun()

# Add new alert
st.markdown("---")
st.markdown("### Add Alert")

all_indicators = sorted(current_pcts.keys())
with st.form("add_alert"):
    col1, col2, col3 = st.columns(3)
    with col1:
        indicator = st.selectbox("Indicator", all_indicators)
    with col2:
        direction = st.selectbox("Alert when", ["below", "above"])
    with col3:
        threshold = st.number_input("Threshold %", min_value=0, max_value=100, value=70)

    if st.form_submit_button("Add Alert", type="primary"):
        alerts.append({
            "indicator": indicator,
            "direction": direction,
            "threshold": threshold,
        })
        save_alerts(str(DATA_DIR), alerts)
        st.success(f"Alert added: {indicator} {direction} {threshold}%")
        st.rerun()
