import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    get_open_response_columns, compute_likert_summary,
    compute_agreement_score, normalize_column_name,
)
from utils.charts import (
    likert_heatmap, grade_comparison_chart, yes_no_chart,
    category_radar_chart,
)
from utils.theme import apply_theme, get_survey_type_filter, filter_surveys_by_type, get_audience_label
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

# Type filter
selected_type = get_survey_type_filter()
surveys, meta = filter_surveys_by_type(
    st.session_state.surveys, st.session_state.survey_meta, selected_type
)
audience = get_audience_label(selected_type)

if not surveys:
    st.info(f"No {selected_type} surveys loaded. Upload data or change the type filter.")
    st.stop()

# Survey selector
survey_labels = [m["label"] for m in meta]
selected_idx = st.sidebar.selectbox(
    "Select Survey",
    range(len(survey_labels)),
    format_func=lambda i: survey_labels[i],
)

df = surveys[selected_idx]
info = meta[selected_idx]

# Grade/role filter
if "_grade" in df.columns:
    unique_vals = sorted(df["_grade"].dropna().astype(str).unique())
    if unique_vals:
        filter_label = "Filter by Grade" if selected_type in ("Student", "All Types") else "Filter by Role"
        selected_vals = st.sidebar.multiselect(filter_label, unique_vals, default=unique_vals)
        df = df[df["_grade"].astype(str).isin(selected_vals)]

st.markdown(f"**{info['label']}** | {len(df)} responses")

# Classify columns
likert_cols = get_likert_columns(df)
yes_no_cols = get_yes_no_columns(df)
open_cols = get_open_response_columns(df)

# Overview metrics
st.markdown("### Overview")
cols = st.columns(4)
cols[0].metric("Total Responses", len(df))
cols[1].metric("Likert Questions", len(likert_cols))
cols[2].metric("Yes/No Questions", len(yes_no_cols))
cols[3].metric("Open-Ended Questions", len(open_cols))

# Grade/role distribution
if "_grade" in df.columns:
    grade_vals = df["_grade"].dropna()
    if len(grade_vals) > 0:
        dist_label = "Grade Distribution" if selected_type in ("Student", "All Types") else "Role Distribution"
        st.markdown(f"### {dist_label}")
        grade_counts = grade_vals.value_counts().sort_index().reset_index()
        grade_counts.columns = ["Group", "Count"]
        fig = px.bar(grade_counts, x="Group", y="Count", color="Count",
                     color_continuous_scale="Viridis")
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# Likert questions (Agree/Disagree scale)
# ============================================================
if likert_cols:
    st.markdown("### Agreement Levels")
    summary = compute_likert_summary(df, likert_cols)
    fig = likert_heatmap(summary, title=f"How {audience} responded to each question")
    st.plotly_chart(fig, use_container_width=True)

    # Category radar
    st.markdown("### CARE Category Scores")
    scores = compute_agreement_score(df, likert_cols)
    fig = category_radar_chart(scores)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No questions matched the CARE categories for this survey.")

    # Grade/role comparison for Likert
    if "_grade" in df.columns:
        compare_label = "Compare by Grade" if selected_type in ("Student", "All Types") else "Compare by Role"
        st.markdown(f"### {compare_label}")
        full_df = surveys[selected_idx]
        selected_q = st.selectbox(
            "Select question",
            likert_cols,
            format_func=lambda c: normalize_column_name(c)[:80],
        )
        fig = grade_comparison_chart(full_df, selected_q)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# Yes/No questions
# ============================================================
if yes_no_cols:
    st.markdown("### Yes/No Questions")
    fig = yes_no_chart(df, yes_no_cols, title=f"How {audience} responded to Yes/No questions")
    st.plotly_chart(fig, use_container_width=True)

    # Yes rate summary table
    st.markdown("#### Response Summary")
    yn_summary = []
    for col in yes_no_cols:
        counts = df[col].value_counts()
        total = counts.sum()
        yes_count = counts.get("Yes", 0)
        no_count = counts.get("No", 0)
        yes_pct = (yes_count / total * 100) if total > 0 else 0
        yn_summary.append({
            "Question": normalize_column_name(col)[:70],
            "Yes": int(yes_count),
            "No": int(no_count),
            "Yes %": f"{yes_pct:.0f}%",
            "Total": int(total),
        })
    yn_df = pd.DataFrame(yn_summary).sort_values("Yes %", ascending=False)

    def color_yes_pct(val):
        try:
            pct = int(val.replace("%", ""))
            if pct >= 75:
                return "background-color: #d5f5e3"
            elif pct >= 50:
                return "background-color: #fef9e7"
            else:
                return "background-color: #fadbd8"
        except Exception:
            return ""

    st.dataframe(
        yn_df.style.map(color_yes_pct, subset=["Yes %"]),
        use_container_width=True,
        hide_index=True,
    )

    # Yes/No by grade/role breakdown
    if "_grade" in df.columns and len(yes_no_cols) > 0:
        grade_vals = df["_grade"].dropna().unique()
        if len(grade_vals) > 1:
            compare_label = "Compare by Grade" if selected_type in ("Student", "All Types") else "Compare by Role"
            st.markdown(f"### {compare_label} (Yes/No)")
            selected_yn_q = st.selectbox(
                "Select question",
                yes_no_cols,
                format_func=lambda c: normalize_column_name(c)[:70],
                key="yn_grade_q",
            )
            yn_grade_data = df[["_grade", selected_yn_q]].dropna()
            yn_grade_data = yn_grade_data[yn_grade_data[selected_yn_q].isin(["Yes", "No"])]
            if len(yn_grade_data) > 0:
                ct = yn_grade_data.groupby(["_grade", selected_yn_q]).size().reset_index(name="Count")
                fig = px.bar(
                    ct,
                    x="_grade",
                    y="Count",
                    color=selected_yn_q,
                    barmode="group",
                    color_discrete_map={"Yes": "#2ecc71", "No": "#e74c3c"},
                    title=normalize_column_name(selected_yn_q)[:70],
                )
                fig.update_layout(xaxis_title="Group", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)

# ============================================================
# Open responses
# ============================================================
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

# No questions at all
if not likert_cols and not yes_no_cols and not open_cols:
    st.warning("No survey questions detected in this file. Check that the file format is correct.")
