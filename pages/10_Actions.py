import streamlit as st
import pandas as pd
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    compute_agreement_score, match_category, sort_periods,
    get_at_risk_indicators, LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.actions import generate_recommendations, STRATEGY_DATABASE
from utils.benchmarks import compute_rams_percentages, load_benchmarks
from utils.theme import apply_theme, get_survey_type_filter, end_control_panel, get_filter_container, filter_surveys_by_type, get_audience_label

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Action Recommendations")
st.markdown(
    "Data-driven suggestions for improving PBIS outcomes at RAMS. "
    "Recommendations are prioritized based on your survey results, trends, and benchmark comparisons."
)

# Load data
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
audience = get_audience_label(selected_type)

if not surveys:
    st.info(f"No {selected_type} surveys loaded. Upload data or change the type filter.")
    st.stop()

# Use the most recent survey for current state
sorted_meta = sorted(
    zip(surveys, meta),
    key=lambda x: sort_periods([x[1]["period"]])[0] if x[1]["period"] != "Unknown" else "",
)
df_latest = sorted_meta[-1][0]
meta_latest = sorted_meta[-1][1]

st.markdown(f"*Analyzing: **{meta_latest['label']}** ({len(df_latest)} responses)*")

# ============================================================
# Gather data signals
# ============================================================

# 1. Category scores from latest survey
category_scores = {}
likert_cols = get_likert_columns(df_latest)
for col in likert_cols:
    cat = match_category(col)
    if cat:
        mapped = df_latest[col].map(LIKERT_MAP).dropna()
        if len(mapped) > 0:
            category_scores.setdefault(cat, []).append(mapped.mean())
category_scores = {cat: sum(v)/len(v) for cat, v in category_scores.items()}

# 2. Trend changes (if multiple surveys)
trend_changes = None
if len(surveys) >= 2:
    first_df = sorted_meta[0][0]
    first_cats = {}
    for col in get_likert_columns(first_df):
        cat = match_category(col)
        if cat:
            mapped = first_df[col].map(LIKERT_MAP).dropna()
            if len(mapped) > 0:
                first_cats.setdefault(cat, []).append(mapped.mean())
    first_cats = {cat: sum(v)/len(v) for cat, v in first_cats.items()}

    trend_changes = {}
    for cat in category_scores:
        if cat in first_cats:
            trend_changes[cat] = category_scores[cat] - first_cats[cat]

# 3. Benchmark gaps
benchmark_gaps = None
try:
    benchmarks = load_benchmarks(str(DATA_DIR))
    rams_pcts = compute_rams_percentages(df_latest)
    if rams_pcts:
        benchmark_gaps = {}
        for indicator, bench in benchmarks["indicators"].items():
            if indicator in rams_pcts:
                benchmark_gaps[indicator] = rams_pcts[indicator]["pct"] - bench["mwahs_pct"]
except Exception:
    pass

# 4. At-risk indicators
at_risk = get_at_risk_indicators(df_latest, survey_type=selected_type)

# ============================================================
# Generate recommendations
# ============================================================
recommendations = generate_recommendations(
    category_scores=category_scores,
    trend_changes=trend_changes,
    benchmark_gaps=benchmark_gaps,
    at_risk=at_risk,
)

# ============================================================
# Display
# ============================================================
if recommendations:
    high = [r for r in recommendations if r["priority"] == "high"]
    medium = [r for r in recommendations if r["priority"] == "medium"]

    st.markdown("---")
    cols = st.columns(3)
    cols[0].metric("Total Recommendations", len(recommendations))
    cols[1].metric("High Priority", len(high))
    cols[2].metric("Medium Priority", len(medium))

    st.markdown("---")

    for rec in recommendations:
        if rec["priority"] == "high":
            color, bg, badge = "#e74c3c", "#fadbd8", "HIGH PRIORITY"
        else:
            color, bg, badge = "#f39c12", "#fef9e7", "MEDIUM PRIORITY"

        st.markdown(
            f'<div style="background-color:{bg}; border-left: 5px solid {color}; '
            f'padding: 16px 20px; border-radius: 6px; margin-bottom: 16px;">'
            f'<span style="background-color:{color}; color:white; padding: 2px 8px; '
            f'border-radius: 3px; font-size: 0.75em; font-weight:bold;">{badge}</span><br><br>'
            f'<strong style="font-size: 1.15em;">{rec["action"]}</strong><br><br>'
            f'<strong>What the data shows:</strong> {rec["finding"]}<br>'
            f'<strong>Why it matters:</strong> {rec["why"]}<br><br>'
            f'{rec["details"]}<br><br>'
            f'<small><strong>Resources:</strong> {rec["resources"]}</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Data context section
    st.markdown("---")
    st.markdown("## Data Behind These Recommendations")

    st.markdown("### Category Scores (Latest Survey)")
    cat_df = pd.DataFrame([
        {
            "Category": cat.replace("_", " ").title(),
            "Score": f"{score:.2f} / 4.0",
            "% Positive": f"{score / 4 * 100:.0f}%",
        }
        for cat, score in sorted(category_scores.items(), key=lambda x: x[1])
    ])
    st.dataframe(cat_df, use_container_width=True, hide_index=True)

    if trend_changes:
        st.markdown("### Trend Changes (First → Latest Survey)")
        trend_df = pd.DataFrame([
            {
                "Category": cat.replace("_", " ").title(),
                "Change": f"{change:+.2f}",
                "Direction": "Improved" if change > 0 else "Declined" if change < 0 else "No change",
            }
            for cat, change in sorted(trend_changes.items(), key=lambda x: x[1])
        ])
        st.dataframe(trend_df, use_container_width=True, hide_index=True)

else:
    st.success(
        "No urgent recommendations at this time! Your scores are looking strong. "
        "Keep doing what you're doing and continue monitoring through the Dashboard and Trends pages."
    )

# ============================================================
# Browse all strategies
# ============================================================
st.markdown("---")
st.markdown("## Strategy Library")
st.markdown("Browse all available PBIS strategies by category, regardless of your current data.")

for cat, strategies in sorted(STRATEGY_DATABASE.items()):
    cat_label = cat.replace("_", " ").title()
    with st.expander(f"{cat_label} ({len(strategies)} strategies)"):
        for s in strategies:
            st.markdown(f"**{s['title']}**")
            st.markdown(f"{s['description']}")
            st.caption(f"Resources: {s['resources']}")
            st.markdown("---")
