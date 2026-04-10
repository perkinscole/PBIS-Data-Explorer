import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    compute_agreement_score, normalize_column_name, match_category,
    get_at_risk_indicators, generate_key_insights, sort_periods,
    LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.benchmarks import compute_rams_percentages, load_benchmarks
from utils.actions import generate_recommendations
from utils.theme import apply_theme, get_survey_type_filter, get_filter_container, filter_surveys_by_type, get_audience_label

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Data Dialogue")
st.markdown(
    "A guided walkthrough for your CARE team meetings. "
    "Follow the **Notice → Wonder → Act** framework to turn data into action."
)

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
        st.info(f"No {selected_type} surveys loaded.")
        st.stop()

    survey_labels = [m["label"] for m in meta]
    selected_idx = st.selectbox("Select Survey", range(len(survey_labels)),
                                format_func=lambda i: survey_labels[i])
    df = surveys[selected_idx]

# Compute data for auto-findings
likert_cols = get_likert_columns(df)
cat_scores = {}
for col in likert_cols:
    cat = match_category(col)
    if cat:
        mapped = df[col].map(LIKERT_MAP).dropna()
        if len(mapped) > 0:
            cat_scores.setdefault(cat, []).append(mapped.mean())
cat_avgs = {c: sum(v)/len(v) for c, v in cat_scores.items()}

cat_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}
indicators = get_at_risk_indicators(df, survey_type=selected_type)
insights = generate_key_insights(df, audience=audience)

# ============================================================
# STEP 1: NOTICE
# ============================================================
st.markdown("---")
st.markdown(
    '<div style="background-color:#ebf5fb; border-left:5px solid #3498db; '
    'padding:16px 20px; border-radius:6px;">'
    '<h2 style="color:#2980b9; margin:0;">Step 1: What Do We Notice?</h2>'
    '<p>Look at the data. What stands out? What patterns do you see?</p>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("#### Auto-Generated Findings")

# Highest and lowest categories
if cat_avgs:
    sorted_cats = sorted(cat_avgs.items(), key=lambda x: x[1])
    lowest = sorted_cats[0]
    highest = sorted_cats[-1]
    st.markdown(f"- **Strongest area:** {cat_labels.get(highest[0], highest[0])} ({highest[1]:.2f}/4)")
    st.markdown(f"- **Area needing attention:** {cat_labels.get(lowest[0], lowest[0])} ({lowest[1]:.2f}/4)")

# At-risk counts
if indicators:
    for label, info in indicators.items():
        if info["count"] > 0:
            pct = info["count"] / info["total"] * 100
            st.markdown(f"- **{info['count']} {audience}** ({pct:.1f}%) flagged for: {label}")

# Benchmark comparison
try:
    benchmarks = load_benchmarks(str(DATA_DIR))
    rams_pcts = compute_rams_percentages(df)
    below_bench = []
    for ind, bench in benchmarks["indicators"].items():
        if ind in rams_pcts and rams_pcts[ind]["pct"] < bench["mwahs_pct"] - 5:
            below_bench.append(f"{ind} ({rams_pcts[ind]['pct']:.0f}% vs {bench['mwahs_pct']}% regional)")
    if below_bench:
        st.markdown("- **Below MetroWest benchmark:** " + ", ".join(below_bench))
except Exception:
    pass

# AI insights
for ins in insights[:3]:
    st.markdown(f"- {ins['text']}")

st.markdown("#### Your Team's Observations")
notice_notes = st.text_area(
    "What else does your team notice? Add your observations here.",
    key="notice_notes",
    height=100,
    placeholder="We noticed that...",
)

# ============================================================
# STEP 2: WONDER
# ============================================================
st.markdown("---")
st.markdown(
    '<div style="background-color:#fef9e7; border-left:5px solid #f39c12; '
    'padding:16px 20px; border-radius:6px;">'
    '<h2 style="color:#e67e22; margin:0;">Step 2: What Do We Wonder?</h2>'
    '<p>What questions does the data raise? What do you want to know more about?</p>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("#### Suggested Questions")

# Generate wonder questions from the data
wonder_prompts = []
if cat_avgs:
    sorted_cats = sorted(cat_avgs.items(), key=lambda x: x[1])
    lowest_cat = cat_labels.get(sorted_cats[0][0], sorted_cats[0][0])
    wonder_prompts.append(f"Why is **{lowest_cat}** our lowest-scoring area? What's driving that?")

if "_grade" in df.columns:
    wonder_prompts.append("Are there differences between grade levels? Is one grade struggling more?")

if indicators:
    top_indicator = max(indicators.items(), key=lambda x: x[1]["count"])
    wonder_prompts.append(f"What's behind the **{top_indicator[0]}** numbers? What are those {audience} experiencing?")

wonder_prompts.extend([
    "Has this changed from last year? Are we trending up or down?",
    "What are we already doing well that we should keep doing?",
    "Are there specific times/places where issues come up most?",
    "What would our open-ended responses tell us about this?",
])

for prompt in wonder_prompts:
    st.markdown(f"- {prompt}")

st.markdown("#### Your Team's Questions")
wonder_notes = st.text_area(
    "What does your team wonder about? Add your questions here.",
    key="wonder_notes",
    height=100,
    placeholder="We wonder...",
)

# ============================================================
# STEP 3: ACT
# ============================================================
st.markdown("---")
st.markdown(
    '<div style="background-color:#d5f5e3; border-left:5px solid #27ae60; '
    'padding:16px 20px; border-radius:6px;">'
    '<h2 style="color:#1e8449; margin:0;">Step 3: What Will We Do?</h2>'
    '<p>Based on what you noticed and wondered, what actions will your team take?</p>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("#### Suggested Actions")
recs = generate_recommendations(cat_avgs)
if recs:
    for rec in recs[:5]:
        priority_color = "#e74c3c" if rec["priority"] == "high" else "#f39c12"
        st.markdown(
            f'<div style="border-left:4px solid {priority_color}; padding:8px 14px; margin-bottom:8px;">'
            f'<strong>{rec["action"]}</strong><br>'
            f'<small>{rec["finding"]}</small>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No urgent actions suggested based on current data.")

st.markdown("#### Your Team's Action Plan")
action_notes = st.text_area(
    "What will your team commit to doing? Be specific.",
    key="action_notes",
    height=100,
    placeholder="We will...",
)

# ============================================================
# EXPORT
# ============================================================
st.markdown("---")
st.markdown("### Export Dialogue Summary")

if st.button("Generate Summary", type="primary"):
    lines = [
        f"RAMS CARE Data Dialogue Summary",
        f"{'=' * 50}",
        f"Date: {datetime.now().strftime('%B %d, %Y')}",
        f"Survey: {meta[selected_idx]['label']}",
        f"Responses: {len(df)}",
        f"",
        f"STEP 1: WHAT DO WE NOTICE?",
        f"-" * 30,
    ]
    if cat_avgs:
        sorted_cats = sorted(cat_avgs.items(), key=lambda x: x[1])
        lines.append(f"Strongest: {cat_labels.get(sorted_cats[-1][0], sorted_cats[-1][0])} ({sorted_cats[-1][1]:.2f}/4)")
        lines.append(f"Weakest: {cat_labels.get(sorted_cats[0][0], sorted_cats[0][0])} ({sorted_cats[0][1]:.2f}/4)")
    if notice_notes:
        lines.append(f"\nTeam observations:\n{notice_notes}")

    lines.extend([f"", f"STEP 2: WHAT DO WE WONDER?", f"-" * 30])
    if wonder_notes:
        lines.append(f"Team questions:\n{wonder_notes}")

    lines.extend([f"", f"STEP 3: WHAT WILL WE DO?", f"-" * 30])
    if recs:
        for rec in recs[:5]:
            lines.append(f"[{rec['priority']}] {rec['action']}: {rec['finding'].replace('**','')}")
    if action_notes:
        lines.append(f"\nTeam commitments:\n{action_notes}")

    summary = "\n".join(lines)
    st.download_button(
        "Download Summary",
        summary,
        file_name=f"Data_Dialogue_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )
    with st.expander("Preview"):
        st.text(summary)
