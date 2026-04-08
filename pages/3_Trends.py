import streamlit as st
import pandas as pd
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    compute_agreement_score, normalize_column_name,
    sort_periods, match_category, LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.charts import trend_line_chart
from utils.theme import apply_theme
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

surveys = st.session_state.surveys
meta = st.session_state.survey_meta

if len(surveys) < 2:
    st.info("Need at least 2 surveys loaded to show trends. Upload more data on the Upload page.")
    st.stop()

# Build trend data: for each survey, compute agreement scores
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

# Category filter
st.sidebar.markdown("### Filters")
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
    title="Category Trends Across Surveys",
)
fig.update_layout(yaxis_range=[1, 5], yaxis_title="Average Agreement (1-5)", height=500)
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

        # Highlight top movers
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Most Improved**")
            top_improved = change_df.nlargest(5, "Change")
            for _, row in top_improved.iterrows():
                st.markdown(f"- **+{row['Change']:.2f}** {row['Question'][:60]}")
        with col2:
            st.markdown("**Most Declined**")
            top_declined = change_df.nsmallest(5, "Change")
            for _, row in top_declined.iterrows():
                st.markdown(f"- **{row['Change']:.2f}** {row['Question'][:60]}")
