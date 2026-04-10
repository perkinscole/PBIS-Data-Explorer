import streamlit as st
import pandas as pd
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    match_category, normalize_column_name, sort_periods,
    LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.benchmarks import compute_rams_percentages, load_benchmarks
from utils.theme import apply_theme, get_survey_type_filter, get_filter_container, filter_surveys_by_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Report Card")
st.markdown("A quick letter-grade snapshot of how RAMS is doing across all PBIS areas.")

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
    survey_labels = [m["label"] for m in meta]
    selected_idx = st.selectbox("Select Survey", range(len(survey_labels)),
                                format_func=lambda i: survey_labels[i])
    df = surveys[selected_idx]

def get_letter_grade(pct):
    if pct >= 90: return "A", "#27ae60"
    if pct >= 80: return "B", "#2ecc71"
    if pct >= 70: return "C", "#f39c12"
    if pct >= 60: return "D", "#e67e22"
    return "F", "#e74c3c"

def pct_positive(df, cols):
    pcts = []
    for col in cols:
        valid = df[col].dropna()
        if len(valid) > 0:
            if col in get_likert_columns(df):
                pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
            else:
                pos = (valid == "Yes").sum()
            pcts.append(pos / len(valid) * 100)
    return round(sum(pcts) / len(pcts), 1) if pcts else None

# Compute per-category grades
likert_cols = get_likert_columns(df)
yn_cols = get_yes_no_columns(df)
all_cols = likert_cols + yn_cols

cat_data = {}
for col in all_cols:
    cat = match_category(col)
    if cat:
        cat_data.setdefault(cat, []).append(col)

# Get previous survey for comparison if available
prev_grades = {}
if len(surveys) >= 2 and selected_idx > 0:
    prev_df = surveys[selected_idx - 1]
    for cat, cols in cat_data.items():
        prev_cols = [c for c in cols if c in prev_df.columns]
        if prev_cols:
            pct = pct_positive(prev_df, prev_cols)
            if pct is not None:
                prev_grades[cat] = pct

# Get benchmark data
benchmarks = {}
try:
    bench_data = load_benchmarks(str(DATA_DIR))
    rams_pcts = compute_rams_percentages(df)
    for indicator, bench in bench_data["indicators"].items():
        if indicator in rams_pcts:
            benchmarks[indicator] = bench["mwahs_pct"]
except Exception:
    pass

# Overall GPA
all_pcts = []
grades_rows = []
cat_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}

for cat, cols in sorted(cat_data.items()):
    pct = pct_positive(df, cols)
    if pct is None:
        continue
    all_pcts.append(pct)
    letter, color = get_letter_grade(pct)

    # Trend
    trend = ""
    if cat in prev_grades:
        diff = pct - prev_grades[cat]
        if diff > 2: trend = "up"
        elif diff < -2: trend = "down"
        else: trend = "same"

    grades_rows.append({
        "cat": cat,
        "label": cat_labels.get(cat, cat),
        "pct": pct,
        "letter": letter,
        "color": color,
        "trend": trend,
        "prev_pct": prev_grades.get(cat),
        "questions": len(cols),
    })

if not grades_rows:
    st.warning("No questions mapped to PBIS categories.")
    st.stop()

# Overall score
overall_pct = sum(all_pcts) / len(all_pcts)
overall_letter, overall_color = get_letter_grade(overall_pct)

st.markdown("---")
st.markdown(
    f'<div style="text-align:center; padding: 20px;">'
    f'<div style="display:inline-block; width:120px; height:120px; border-radius:50%; '
    f'background-color:{overall_color}; line-height:120px; text-align:center; '
    f'font-size:3em; font-weight:bold; color:white;">{overall_letter}</div>'
    f'<h2 style="margin-top:10px;">Overall: {overall_pct:.0f}% Positive</h2>'
    f'<p style="color:#666;">Across {len(grades_rows)} PBIS categories, {len(all_cols)} questions</p>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# Grade cards
for row in sorted(grades_rows, key=lambda r: r["pct"], reverse=True):
    trend_html = ""
    if row["trend"] == "up":
        trend_html = f' <span style="color:#27ae60;">&#9650; +{row["pct"] - row["prev_pct"]:.1f}%</span>'
    elif row["trend"] == "down":
        trend_html = f' <span style="color:#e74c3c;">&#9660; {row["pct"] - row["prev_pct"]:.1f}%</span>'
    elif row["trend"] == "same" and row["prev_pct"]:
        trend_html = f' <span style="color:#95a5a6;">&#9654; no change</span>'

    st.markdown(
        f'<div style="display:flex; align-items:center; padding:12px 16px; margin-bottom:8px; '
        f'border-radius:8px; border-left:6px solid {row["color"]}; background-color:#fafafa;">'
        f'<div style="width:50px; height:50px; border-radius:8px; background:{row["color"]}; '
        f'text-align:center; line-height:50px; font-size:1.5em; font-weight:bold; color:white; '
        f'margin-right:16px;">{row["letter"]}</div>'
        f'<div style="flex:3;"><strong>{row["label"]}</strong><br>'
        f'<small>{row["questions"]} questions</small></div>'
        f'<div style="flex:1; text-align:center; font-size:1.3em; font-weight:bold;">{row["pct"]:.0f}%</div>'
        f'<div style="flex:2; text-align:right;">{trend_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# Grading scale
with st.expander("Grading Scale"):
    st.markdown("""
| Grade | Range | Meaning |
|-------|-------|---------|
| **A** | 90%+ | Excellent — strong positive responses |
| **B** | 80-89% | Good — most respondents positive |
| **C** | 70-79% | Fair — room for improvement |
| **D** | 60-69% | Concerning — needs attention |
| **F** | <60% | Critical — requires immediate action |
""")
