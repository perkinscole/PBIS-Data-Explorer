import streamlit as st
import pandas as pd
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    compute_agreement_score, normalize_column_name,
    sort_periods, match_category, LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.charts import trend_line_chart
from utils.theme import apply_theme, get_survey_type_filter, filter_surveys_by_type, get_audience_label
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Trend Analysis")
st.markdown("Track how survey responses change over time.")

# Load data
if not st.session_state.get("surveys"):
    if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
        all_data, all_meta = load_all_surveys(str(DATA_DIR))
        st.session_state.surveys = all_data
        st.session_state.survey_meta = all_meta
    else:
        st.warning("No data loaded. Go to the Upload page first.")
        st.stop()

# Type filter
selected_type = get_survey_type_filter()
surveys, meta = filter_surveys_by_type(
    st.session_state.surveys, st.session_state.survey_meta, selected_type
)
audience = get_audience_label(selected_type)

if len(surveys) < 2:
    st.info(
        f"Need at least 2 {selected_type} surveys to show trends. "
        "Upload more data or change the type filter."
    )
    # Still allow cross-survey comparison below even with <2 of one type
    if selected_type != "All Types":
        pass  # Fall through to cross-survey section
    else:
        st.stop()

# Build trend data: for each survey, compute agreement scores
if len(surveys) >= 2:
    trend_rows = []
    for df, m in zip(surveys, meta):
        likert_cols = get_likert_columns(df)
        scores = compute_agreement_score(df, likert_cols)
        for q, info in scores.items():
            trend_rows.append({
                "Period": m["period"],
                "Label": m["label"],
                "Question": q,
                "Score": info["mean"],
                "StdDev": info["std"],
                "N": info["n"],
                "Category": info["category"],
            })

    trend_df = pd.DataFrame(trend_rows)
    sorted_periods = sort_periods(trend_df["Period"].unique().tolist())
    trend_df["Period"] = pd.Categorical(trend_df["Period"], categories=sorted_periods, ordered=True)
    trend_df = trend_df.sort_values("Period")

    # Filters
    st.sidebar.markdown("### Filters")

    # Period selector
    selected_periods = st.sidebar.multiselect(
        "Survey Periods",
        sorted_periods,
        default=sorted_periods,
        help="Select which survey periods to include in the trend analysis",
    )
    trend_df = trend_df[trend_df["Period"].isin(selected_periods)]
    sorted_periods = [p for p in sorted_periods if p in selected_periods]

    # Category filter
    categories = sorted(trend_df["Category"].unique())
    category_labels = {c: c.replace("_", " ").title() for c in categories}
    selected_cats = st.sidebar.multiselect(
        "Question Categories",
        categories,
        default=[c for c in categories if c != "other"],
        format_func=lambda c: category_labels.get(c, c),
    )

    filtered = trend_df[trend_df["Category"].isin(selected_cats)]

    # Overall trend by category
    st.markdown("### Average Scores by Category Over Time")
    cat_trend = filtered.groupby(["Period", "Category"])["Score"].mean().reset_index()
    cat_trend["Category Label"] = cat_trend["Category"].map(category_labels)

    fig = px.line(
        cat_trend,
        x="Period",
        y="Score",
        color="Category Label",
        markers=True,
        title=f"Category Trends Across {selected_type} Surveys",
    )
    fig.update_layout(yaxis_range=[1, 5], yaxis_title="Average Agreement (1-4)", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Individual question trends
    st.markdown("### Individual Question Trends")
    questions = sorted(filtered["Question"].unique())
    selected_questions = st.multiselect(
        "Select questions to compare",
        questions,
        default=questions[:3] if len(questions) >= 3 else questions,
        format_func=lambda q: q[:70] + "..." if len(q) > 70 else q,
    )

    if selected_questions:
        q_filtered = filtered[filtered["Question"].isin(selected_questions)]
        fig = trend_line_chart(q_filtered, title="Question Score Trends")
        st.plotly_chart(fig, use_container_width=True)

    # Change analysis
    st.markdown("### Biggest Changes")
    st.markdown("Questions with the largest score changes between first and last survey.")

    if len(sorted_periods) >= 2:
        first_period = sorted_periods[0]
        last_period = sorted_periods[-1]

        first_scores = filtered[filtered["Period"] == first_period].set_index("Question")["Score"]
        last_scores = filtered[filtered["Period"] == last_period].set_index("Question")["Score"]

        common_q = first_scores.index.intersection(last_scores.index)
        if len(common_q) > 0:
            changes = (last_scores[common_q] - first_scores[common_q]).sort_values()

            change_df = pd.DataFrame({
                "Question": changes.index,
                "Change": changes.values,
                "Direction": ["Improved" if c > 0 else "Declined" for c in changes.values],
            })

            fig = px.bar(
                change_df,
                x="Change",
                y="Question",
                orientation="h",
                color="Direction",
                color_discrete_map={"Improved": "#2ecc71", "Declined": "#e74c3c"},
                title=f"Score Changes: {first_period} to {last_period}",
            )
            fig.update_layout(
                height=max(400, len(change_df) * 30),
                yaxis=dict(automargin=True),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Highlight top movers - only show actual improvements/declines
            improved = change_df[change_df["Change"] > 0].nlargest(5, "Change")
            declined = change_df[change_df["Change"] < 0].nsmallest(5, "Change")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Most Improved**")
                if len(improved) > 0:
                    for _, row in improved.iterrows():
                        st.markdown(f"- **+{row['Change']:.2f}** {row['Question'][:60]}")
                else:
                    st.markdown("*No questions improved between these periods.*")
            with col2:
                st.markdown("**Most Declined**")
                if len(declined) > 0:
                    for _, row in declined.iterrows():
                        st.markdown(f"- **{row['Change']:.2f}** {row['Question'][:60]}")
                else:
                    st.markdown("*No questions declined between these periods.*")

# ============================================================
# CROSS-SURVEY TYPE COMPARISON
# ============================================================
st.markdown("---")
st.markdown("## Cross-Survey Comparison")
st.markdown(
    "Compare how different groups (students, staff, parents) respond to **similar themes**. "
    "This helps you see where perspectives align and where they diverge."
)

# Use ALL surveys regardless of the type filter above
all_surveys = st.session_state.surveys
all_meta = st.session_state.survey_meta

# Group surveys by type
surveys_by_type = {}
for df, m in zip(all_surveys, all_meta):
    stype = str(m.get("survey_num", "Unknown"))
    if stype and stype not in ("None", "Unknown", "Auto-detect"):
        surveys_by_type.setdefault(stype, []).append((df, m))

if len(surveys_by_type) < 2:
    st.info(
        "Upload surveys from at least **2 different types** (e.g., Student and Staff) "
        "to see cross-survey comparisons. Make sure to set the survey type on the Upload page."
    )
else:
    # For each type, compute average scores on all Likert questions
    type_scores = {}
    for stype, survey_list in surveys_by_type.items():
        all_scores = {}
        for df, m in survey_list:
            likert_cols = get_likert_columns(df)
            scores = compute_agreement_score(df, likert_cols)
            for q, info in scores.items():
                if pd.notna(info["mean"]):
                    all_scores.setdefault(q, []).append(info["mean"])
        # Average across surveys of same type
        type_scores[stype] = {q: sum(vals) / len(vals) for q, vals in all_scores.items()}

    # Find questions that appear in multiple types (fuzzy match by normalized name)
    all_type_names = list(type_scores.keys())
    all_q_sets = [set(type_scores[t].keys()) for t in all_type_names]

    # Find shared questions (exact match on normalized name)
    shared_questions = all_q_sets[0]
    for qs in all_q_sets[1:]:
        shared_questions = shared_questions & qs

    if shared_questions:
        st.markdown(f"### Shared Questions ({len(shared_questions)} questions in common)")
        st.markdown(
            "These questions appear across multiple survey types, allowing direct comparison."
        )

        # Build comparison dataframe
        compare_rows = []
        for q in sorted(shared_questions):
            for stype in all_type_names:
                compare_rows.append({
                    "Question": q[:60],
                    "Survey Type": stype,
                    "Score": type_scores[stype][q],
                })

        compare_df = pd.DataFrame(compare_rows)

        fig = px.bar(
            compare_df,
            x="Score",
            y="Question",
            color="Survey Type",
            barmode="group",
            orientation="h",
            title="Score Comparison Across Survey Types",
        )
        fig.update_layout(
            xaxis=dict(range=[0, 4.5]),
            xaxis_title="Average Score (1-4)",
            yaxis=dict(automargin=True),
            height=max(400, len(shared_questions) * 40),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Biggest perception gaps
        st.markdown("### Biggest Perception Gaps")
        st.markdown(
            "Questions where different groups see things most differently."
        )

        gaps = []
        for q in shared_questions:
            scores_for_q = [type_scores[t][q] for t in all_type_names]
            gap = max(scores_for_q) - min(scores_for_q)
            highest_type = all_type_names[scores_for_q.index(max(scores_for_q))]
            lowest_type = all_type_names[scores_for_q.index(min(scores_for_q))]
            gaps.append({
                "Question": q[:60],
                "Gap": round(gap, 2),
                "Most Positive": f"{highest_type} ({max(scores_for_q):.2f})",
                "Least Positive": f"{lowest_type} ({min(scores_for_q):.2f})",
            })

        gap_df = pd.DataFrame(gaps).sort_values("Gap", ascending=False)
        st.dataframe(gap_df, use_container_width=True, hide_index=True)

        if len(gap_df) > 0:
            top_gap = gap_df.iloc[0]
            st.markdown(
                f"**Biggest gap:** \"{top_gap['Question']}\" - "
                f"{top_gap['Most Positive']} vs {top_gap['Least Positive']} "
                f"(gap of {top_gap['Gap']} points)"
            )
    else:
        st.info(
            "No questions with matching wording found across survey types. "
            "The comparison works best when different survey types share some of the same questions."
        )

    # Overall sentiment comparison by type
    st.markdown("### Overall Sentiment by Survey Type")
    overall_rows = []
    for stype, survey_list in surveys_by_type.items():
        for df, m in survey_list:
            likert_cols = get_likert_columns(df)
            if likert_cols:
                numeric = df[likert_cols].apply(lambda col: col.map(LIKERT_MAP))
                avg = numeric.mean().mean()
                overall_rows.append({
                    "Survey Type": stype,
                    "Period": m["period"],
                    "Label": m["label"],
                    "Average Score": round(avg, 2),
                    "Responses": len(df),
                })

    if overall_rows:
        overall_df = pd.DataFrame(overall_rows)
        fig = px.bar(
            overall_df,
            x="Label",
            y="Average Score",
            color="Survey Type",
            title="Overall Sentiment Across All Surveys",
        )
        fig.update_layout(
            yaxis_range=[0, 4.5],
            yaxis_title="Average Score (1-4)",
            xaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)
