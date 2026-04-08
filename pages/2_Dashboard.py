import streamlit as st
import pandas as pd
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    get_open_response_columns, compute_likert_summary,
    compute_agreement_score, normalize_column_name,
)
from utils.charts import (
    likert_heatmap, grade_comparison_chart, yes_no_chart,
    category_radar_chart,
)
from utils.theme import apply_theme
from pathlib import Path

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Survey Dashboard")

# Load data if needed
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

# Survey selector
survey_labels = [m["label"] for m in meta]
selected_idx = st.sidebar.selectbox(
    "Select Survey",
    range(len(survey_labels)),
    format_func=lambda i: survey_labels[i],
)

df = surveys[selected_idx]
info = meta[selected_idx]

# Grade filter
if "_grade" in df.columns:
    grades = sorted(df["_grade"].unique())
    selected_grades = st.sidebar.multiselect("Filter by Grade", grades, default=grades)
    df = df[df["_grade"].isin(selected_grades)]

st.markdown(f"**{info['label']}** | {len(df)} responses")

# Overview metrics
st.markdown("### Overview")
cols = st.columns(4)
likert_cols = get_likert_columns(df)
yes_no_cols = get_yes_no_columns(df)
open_cols = get_open_response_columns(df)

cols[0].metric("Total Responses", len(df))
cols[1].metric("Likert Questions", len(likert_cols))
cols[2].metric("Yes/No Questions", len(yes_no_cols))
cols[3].metric("Open-Ended Questions", len(open_cols))

# Grade distribution
if "_grade" in df.columns:
    st.markdown("### Grade Distribution")
    grade_counts = df["_grade"].value_counts().sort_index().reset_index()
    grade_counts.columns = ["Grade", "Count"]
    import plotly.express as px
    fig = px.bar(grade_counts, x="Grade", y="Count", color="Count",
                 color_continuous_scale="Viridis")
    st.plotly_chart(fig, use_container_width=True)

# Likert response heatmap
if likert_cols:
    st.markdown("### Agreement Levels")
    summary = compute_likert_summary(df, likert_cols)
    fig = likert_heatmap(summary, title="How students responded to each question")
    st.plotly_chart(fig, use_container_width=True)

# Category radar
if likert_cols:
    st.markdown("### CARE Category Scores")
    scores = compute_agreement_score(df, likert_cols)
    fig = category_radar_chart(scores)
    st.plotly_chart(fig, use_container_width=True)

# Grade comparison
if likert_cols and "_grade" in df.columns:
    st.markdown("### Compare by Grade")
    # Use the original unfiltered data for grade comparison
    full_df = surveys[selected_idx]
    selected_q = st.selectbox(
        "Select question",
        likert_cols,
        format_func=lambda c: normalize_column_name(c)[:80],
    )
    fig = grade_comparison_chart(full_df, selected_q)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# Yes/No questions
if yes_no_cols:
    st.markdown("### Yes/No Questions")
    fig = yes_no_chart(df, yes_no_cols)
    st.plotly_chart(fig, use_container_width=True)

# Open responses
if open_cols:
    st.markdown("### Open-Ended Responses")
    selected_open = st.selectbox(
        "Select question",
        open_cols,
        format_func=lambda c: normalize_column_name(c)[:80],
        key="open_q",
    )
    responses = df[selected_open].dropna().astype(str)
    responses = responses[responses.str.len() > 2]

    # Word cloud
    if len(responses) > 0:
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt

            text = " ".join(responses)
            wc = WordCloud(
                width=800, height=400,
                background_color="white",
                colormap="viridis",
                max_words=100,
            ).generate(text)

            fig_wc, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig_wc)
        except Exception:
            pass

    # Searchable response list
    search = st.text_input("Search responses", key="search_open")
    if search:
        responses = responses[responses.str.contains(search, case=False, na=False)]

    st.markdown(f"**{len(responses)} responses:**")
    for i, resp in enumerate(responses.head(50)):
        st.markdown(f"- {resp}")
    if len(responses) > 50:
        st.caption(f"Showing 50 of {len(responses)} responses")
