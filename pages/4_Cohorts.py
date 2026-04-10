import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    normalize_column_name, match_category, sort_periods,
    LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.theme import apply_theme, get_survey_type_filter, end_control_panel, filter_surveys_by_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Cohort Tracking")
st.markdown(
    "Follow the same group of students as they progress through RAMS. "
    "6th graders in 2024 become 7th graders in 2025 and 8th graders in 2026."
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

selected_type = get_survey_type_filter()
surveys, meta = filter_surveys_by_type(
    st.session_state.surveys, st.session_state.survey_meta, selected_type
)
end_control_panel()

if len(surveys) < 2:
    st.info("Need at least 2 surveys to track cohorts. Upload more data or change the type filter.")
    st.stop()

# ============================================================
# Cohort detection logic
# ============================================================
GRADE_NUM = {
    "6th grade": 6, "7th grade": 7, "8th grade": 8,
    "grade 6": 6, "grade 7": 7, "grade 8": 8,
}
MONTH_TO_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "may-june": 5, "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}

def get_school_year(period):
    parts = period.rsplit(" ", 1)
    if len(parts) != 2:
        return None
    month_str, year_str = parts
    try:
        year = int(year_str)
    except ValueError:
        return None
    month_num = MONTH_TO_NUM.get(month_str.lower(), 0)
    if month_num >= 8:
        return f"{year}-{year + 1}"
    else:
        return f"{year - 1}-{year}"

def get_graduation_year(grade_num, school_year):
    if not school_year or not grade_num:
        return None
    start_year = int(school_year.split("-")[0])
    years_until_8th = 8 - grade_num
    return start_year + years_until_8th + 1

# Build per-student-group data for each survey+grade combo
cohort_data = []  # list of {cohort, grade, grade_num, period, school_year, df_slice}

for df, m in zip(surveys, meta):
    if "_grade" not in df.columns:
        continue
    school_year = get_school_year(m["period"])
    if not school_year:
        continue

    for grade_str in df["_grade"].dropna().astype(str).unique():
        grade_lower = grade_str.lower().strip()
        grade_num = GRADE_NUM.get(grade_lower)
        if not grade_num:
            continue

        grad_year = get_graduation_year(grade_num, school_year)
        if not grad_year:
            continue

        grade_df = df[df["_grade"].astype(str).str.lower().str.strip() == grade_lower]
        if len(grade_df) < 3:
            continue

        cohort_data.append({
            "cohort": f"Class of {grad_year}",
            "grade": f"{grade_num}th Grade",
            "grade_num": grade_num,
            "period": m["period"],
            "school_year": school_year,
            "label": f"{grade_num}th Grade ({m['period']})",
            "df": grade_df,
            "n": len(grade_df),
        })

if not cohort_data:
    st.info("No grade-level data found for cohort tracking. This works best with Student surveys.")
    st.stop()

# Find cohorts that appear in multiple surveys
cohort_names = set(c["cohort"] for c in cohort_data)
multi_cohorts = []
for name in cohort_names:
    entries = [c for c in cohort_data if c["cohort"] == name]
    if len(entries) > 1:
        multi_cohorts.append(name)

if not multi_cohorts:
    st.info(
        "Need surveys from at least **2 different school years** to track cohorts. "
        "Upload more survey data spanning multiple years."
    )
    st.stop()

multi_cohorts = sorted(multi_cohorts)
st.success(f"Found **{len(multi_cohorts)} cohorts** with data across multiple survey periods.")

# Cohort selector
selected_cohorts = st.multiselect(
    "Select Cohorts",
    multi_cohorts,
    default=multi_cohorts,
)

if not selected_cohorts:
    st.info("Select at least one cohort from the sidebar.")
    st.stop()

# View mode
view_mode = st.radio(
    "View by",
    ["Overall", "PBIS Category", "Individual Question"],
    horizontal=True,
)

category_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}

# ============================================================
# OVERALL VIEW
# ============================================================
if view_mode == "Overall":
    st.markdown("### Overall Positivity by Cohort")
    st.markdown("Average % of positive responses (agree/strongly agree) across all questions.")

    rows = []
    for entry in cohort_data:
        if entry["cohort"] not in selected_cohorts:
            continue
        likert_cols = get_likert_columns(entry["df"])
        if not likert_cols:
            continue
        pcts = []
        for col in likert_cols:
            valid = entry["df"][col].dropna()
            if len(valid) > 0:
                pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
                pcts.append(pos / len(valid) * 100)
        if pcts:
            rows.append({
                "Cohort": entry["cohort"],
                "Label": entry["label"],
                "Grade": entry["grade"],
                "Period": entry["period"],
                "% Positive": round(sum(pcts) / len(pcts), 1),
                "Students": entry["n"],
            })

    if rows:
        plot_df = pd.DataFrame(rows)
        fig = px.line(
            plot_df, x="Label", y="% Positive", color="Cohort",
            markers=True, title="Overall Positivity Over Time",
        )
        fig.update_layout(yaxis_range=[0, 105], yaxis_title="% Positive", height=450)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(plot_df[["Cohort", "Grade", "Period", "% Positive", "Students"]],
                      use_container_width=True, hide_index=True)

# ============================================================
# CATEGORY VIEW
# ============================================================
elif view_mode == "PBIS Category":
    st.markdown("### Cohort Tracking by PBIS Category")

    # Let user pick categories
    available_cats = sorted(set(
        match_category(col)
        for entry in cohort_data
        for col in get_likert_columns(entry["df"])
        if match_category(col)
    ))
    selected_cats = st.multiselect(
        "Select categories",
        available_cats,
        default=available_cats[:3] if len(available_cats) >= 3 else available_cats,
        format_func=lambda c: category_labels.get(c, c),
    )

    if not selected_cats:
        st.info("Select at least one category.")
    else:
        for cat in selected_cats:
            cat_label = category_labels.get(cat, cat)
            st.markdown(f"#### {cat_label}")

            rows = []
            for entry in cohort_data:
                if entry["cohort"] not in selected_cohorts:
                    continue
                likert_cols = get_likert_columns(entry["df"])
                cat_cols = [c for c in likert_cols if match_category(c) == cat]
                if not cat_cols:
                    continue
                pcts = []
                for col in cat_cols:
                    valid = entry["df"][col].dropna()
                    if len(valid) > 0:
                        pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
                        pcts.append(pos / len(valid) * 100)
                if pcts:
                    rows.append({
                        "Cohort": entry["cohort"],
                        "Label": entry["label"],
                        "% Positive": round(sum(pcts) / len(pcts), 1),
                    })

            if rows:
                plot_df = pd.DataFrame(rows)
                fig = px.line(
                    plot_df, x="Label", y="% Positive", color="Cohort",
                    markers=True, title=f"{cat_label} - Cohort Comparison",
                )
                fig.update_layout(yaxis_range=[0, 105], height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption(f"No data for {cat_label} in selected cohorts.")

# ============================================================
# INDIVIDUAL QUESTION VIEW
# ============================================================
elif view_mode == "Individual Question":
    st.markdown("### Cohort Tracking by Question")

    # Get all questions across cohort data
    all_questions = set()
    for entry in cohort_data:
        if entry["cohort"] in selected_cohorts:
            for col in get_likert_columns(entry["df"]):
                all_questions.add(col)
            for col in get_yes_no_columns(entry["df"]):
                all_questions.add(col)

    all_questions = sorted(all_questions, key=lambda c: normalize_column_name(c))

    selected_q = st.selectbox(
        "Select question",
        all_questions,
        format_func=lambda c: normalize_column_name(c)[:75],
    )

    if selected_q:
        st.markdown(f"**{normalize_column_name(selected_q)}**")

        rows = []
        for entry in cohort_data:
            if entry["cohort"] not in selected_cohorts:
                continue
            if selected_q not in entry["df"].columns:
                continue
            valid = entry["df"][selected_q].dropna()
            if len(valid) == 0:
                continue

            # Compute % positive
            is_likert = selected_q in get_likert_columns(entry["df"])
            if is_likert:
                pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
            else:
                pos = (valid == "Yes").sum()
            pct = pos / len(valid) * 100

            rows.append({
                "Cohort": entry["cohort"],
                "Label": entry["label"],
                "Grade": entry["grade"],
                "Period": entry["period"],
                "% Positive": round(pct, 1),
                "Students": len(valid),
            })

        if rows:
            plot_df = pd.DataFrame(rows)
            fig = px.line(
                plot_df, x="Label", y="% Positive", color="Cohort",
                markers=True,
                title=f'"{normalize_column_name(selected_q)[:60]}" - Cohort Comparison',
            )
            fig.update_layout(yaxis_range=[0, 105], height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Also show response breakdown
            st.markdown("#### Response Breakdown by Cohort")
            for entry in cohort_data:
                if entry["cohort"] not in selected_cohorts:
                    continue
                if selected_q not in entry["df"].columns:
                    continue
                valid = entry["df"][selected_q].dropna()
                if len(valid) == 0:
                    continue
                counts = valid.value_counts()
                st.markdown(f"**{entry['cohort']}** - {entry['label']} (n={len(valid)})")
                for val, count in counts.items():
                    pct = count / len(valid) * 100
                    st.caption(f"  {val}: {count} ({pct:.0f}%)")
        else:
            st.info("This question isn't present in the selected cohorts' surveys.")

# ============================================================
# Cohort summary table
# ============================================================
st.markdown("---")
st.markdown("### Cohort Summary")

summary_rows = []
for cohort_name in selected_cohorts:
    entries = sorted(
        [c for c in cohort_data if c["cohort"] == cohort_name],
        key=lambda c: c["grade_num"],
    )
    if len(entries) < 2:
        continue

    # Compute overall % positive for first and last
    def overall_pct(entry):
        likert_cols = get_likert_columns(entry["df"])
        pcts = []
        for col in likert_cols:
            valid = entry["df"][col].dropna()
            if len(valid) > 0:
                pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
                pcts.append(pos / len(valid) * 100)
        return round(sum(pcts) / len(pcts), 1) if pcts else None

    first_pct = overall_pct(entries[0])
    last_pct = overall_pct(entries[-1])
    change = round(last_pct - first_pct, 1) if first_pct and last_pct else None

    summary_rows.append({
        "Cohort": cohort_name,
        "First Survey": entries[0]["label"],
        "Latest Survey": entries[-1]["label"],
        "Start %": f"{first_pct:.0f}%" if first_pct else "—",
        "Latest %": f"{last_pct:.0f}%" if last_pct else "—",
        "Change": f"{change:+.1f}%" if change is not None else "—",
    })

if summary_rows:
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
