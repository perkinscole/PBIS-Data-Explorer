import streamlit as st
import pandas as pd
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    get_open_response_columns, normalize_column_name,
    compute_student_scores, detect_straightliners, detect_data_errors,
    detect_contradictions, compute_correlation_matrix,
    get_at_risk_indicators, analyze_open_response_sentiment,
    compute_group_comparison, generate_key_insights, LIKERT_MAP,
)
from utils.charts import (
    sentiment_histogram, correlation_heatmap, group_comparison_chart,
    sentiment_by_grade_chart,
)
from utils.theme import apply_theme, get_survey_type_filter, end_control_panel, filter_surveys_by_type, get_audience_label

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Insights & Analysis")

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
end_control_panel()
audience = get_audience_label(selected_type)
audience_cap = audience.capitalize()

if not surveys:
    st.info(f"No {selected_type} surveys loaded. Upload data or change the type filter.")
    st.stop()

st.markdown(
    f"Dig deeper into {audience} responses: detect outliers, track sentiment, "
    "discover patterns between groups, and flag concerning responses."
)

# Survey selector
survey_labels = [m["label"] for m in meta]
selected_idx = st.selectbox(
    "Select Survey",
    range(len(survey_labels)),
    format_func=lambda i: survey_labels[i],
)
df = surveys[selected_idx]

# ============================================================
# SECTION 1: RESPONSE QUALITY & OUTLIER DETECTION
# ============================================================
st.markdown("---")
st.markdown("## Response Quality Check")
st.markdown(
    "Before analyzing results, it helps to know which responses might not be reliable. "
    "This section automatically flags responses that look suspicious so you can decide "
    "whether to include or exclude them."
)

straightliners = detect_straightliners(df)
data_errors = detect_data_errors(df)
contradictions = detect_contradictions(df)

# Combine all flags
any_flag = straightliners | data_errors | contradictions
clean_count = (~any_flag).sum()
flagged_count = any_flag.sum()
quality_pct = clean_count / len(df) * 100 if len(df) > 0 else 100

# Color-coded quality panel
if quality_pct >= 90:
    panel_color = "#d5f5e3"  # green
    panel_border = "#27ae60"
    panel_icon = "checkmark"
elif quality_pct >= 75:
    panel_color = "#fef9e7"  # yellow
    panel_border = "#f39c12"
    panel_icon = "warning"
else:
    panel_color = "#fadbd8"  # red
    panel_border = "#e74c3c"
    panel_icon = "error"

st.markdown(
    f'<div style="background-color:{panel_color}; border-left: 5px solid {panel_border}; '
    f'padding: 16px 20px; border-radius: 6px; margin-bottom: 16px;">'
    f'<strong style="font-size: 1.2em;">{quality_pct:.0f}% of responses look reliable</strong><br>'
    f'{int(clean_count)} clean out of {len(df)} total &nbsp;|&nbsp; '
    f'{int(flagged_count)} flagged</div>',
    unsafe_allow_html=True,
)

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Responses", len(df))
col2.metric("Straight-liners", int(straightliners.sum()),
            help="Same answer for every question")
col3.metric("Data Errors", int(data_errors.sum()),
            help="Non-standard values in response columns")
col4.metric("Contradictions", int(contradictions.sum()),
            help="Highly inconsistent across categories")

# Expandable details for each flag type
with st.expander("What do these flags mean?"):
    st.markdown("""
**Straight-liners** picked the exact same answer for every single question
(e.g., "Strongly disagree" on everything). This usually means the respondent
clicked through without reading the questions.

**Data Errors** are responses that contain unexpected values like numbers
instead of "Strongly agree/disagree." These are typically form glitches
where the response didn't record properly.

**Contradictions** are responses where answers across different
topic areas are extremely inconsistent - for example, saying they love
everything about school but also that they feel completely unsafe and
disrespected. Some variation is normal, but extreme swings suggest the
respondent may not have been answering thoughtfully.
""")

if flagged_count > 0:
    with st.expander(f"View {flagged_count} flagged responses"):
        flagged_df = df[any_flag].copy()
        flagged_df["Flag"] = ""
        flagged_df.loc[straightliners, "Flag"] += "Straight-liner "
        flagged_df.loc[data_errors, "Flag"] += "Data Error "
        flagged_df.loc[contradictions, "Flag"] += "Contradiction "
        display_cols = ["Flag"] + (["_grade"] if "_grade" in df.columns else []) + [
            c for c in df.columns if not c.startswith("_") and c != "Timestamp"
        ]
        display_cols = [c for c in display_cols if c in flagged_df.columns]
        st.dataframe(flagged_df[display_cols], use_container_width=True)

# Let user choose to exclude flagged responses
exclude_flagged = st.checkbox(
    "Exclude flagged responses from analysis below",
    value=False,
    help="Check this to remove suspicious responses from the sentiment and pattern analysis",
)
if exclude_flagged:
    df = df[~any_flag]
    st.info(f"Analyzing {len(df)} clean responses (excluded {flagged_count}).")

# ============================================================
# SECTION 2: SENTIMENT SCORING
# ============================================================
st.markdown("---")
st.markdown("## Sentiment Overview")
st.markdown(
    f"Each respondent gets a **sentiment score** based on their average response across "
    f"all questions (1 = very negative, 4 = very positive). This gives you a quick "
    f"picture of overall {audience} satisfaction."
)

scores = compute_student_scores(df)
valid_scores = scores.dropna()

if len(valid_scores) > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Sentiment", f"{valid_scores.mean():.2f} / 4")
    col2.metric("Most Positive", f"{valid_scores.max():.2f}")
    col3.metric("Most Negative", f"{valid_scores.min():.2f}")
    below_2 = (valid_scores < 2.0).sum()
    col4.metric(f"{audience_cap} Below 2.0", int(below_2),
                help="Respondents averaging below 'Somewhat disagree' - may need attention")

    fig = sentiment_histogram(scores)
    st.plotly_chart(fig, use_container_width=True)

    # Sentiment by grade
    if "_grade" in df.columns:
        group_label = "Grade" if selected_type in ("Student", "All Types") else "Role"
        st.markdown(f"### Sentiment by {group_label}")
        fig = sentiment_by_grade_chart(df, scores, title=f"Sentiment by {group_label}")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

# At-risk indicators
st.markdown("### At-Risk Indicators")
st.markdown(
    f'{audience_cap} who answered **"Strongly disagree"** on critical questions may need '
    "follow-up. These are the questions most connected to wellbeing."
)

indicators = get_at_risk_indicators(df, survey_type=selected_type)
if indicators:
    cols = st.columns(min(len(indicators), 3))
    for i, (label, info) in enumerate(indicators.items()):
        col = cols[i % 3]
        pct = info["count"] / info["total"] * 100 if info["total"] > 0 else 0
        col.metric(
            label,
            f'{info["count"]} {audience}',
            f"{pct:.1f}% of respondents",
            delta_color="inverse",
        )
else:
    st.info("No at-risk indicator questions found in this survey.")

# ============================================================
# SECTION 3: CROSS-QUESTION PATTERNS
# ============================================================
st.markdown("---")
st.markdown("## Cross-Question Patterns")
st.markdown(
    "Discover how answers to one question relate to answers on other questions. "
    "This helps you understand which issues are connected - for example, students "
    "who don't feel safe might also report lower respect from peers."
)

# Auto-generated insights
insights = generate_key_insights(df, audience=audience)
if insights:
    st.markdown("### Key Findings")
    for insight in sorted(insights, key=lambda x: x["severity"], reverse=True):
        if insight["severity"] == "high":
            st.error(insight["text"])
        else:
            st.warning(insight["text"])

# Correlation heatmap
st.markdown("### Question Correlation Map")
st.markdown(
    "This map shows how strongly each pair of questions is connected. "
    f"**Dark green** = {audience} who score high on one tend to score high on the other. "
    "**Dark red** = opposite patterns. **Yellow** = no connection."
)

corr = compute_correlation_matrix(df)
if not corr.empty:
    fig = correlation_heatmap(corr)
    st.plotly_chart(fig, use_container_width=True)

# Group comparison tool
st.markdown("### Group Comparison Tool")
st.markdown(
    f'Pick a question and a response to see how that group of {audience} differs '
    f'from everyone else. For example: "How do {audience} who *don\'t feel safe* '
    f'answer all the other questions?"'
)

likert_cols = get_likert_columns(df)
if likert_cols:
    col1, col2 = st.columns(2)
    with col1:
        selected_q = st.selectbox(
            "Choose a question",
            likert_cols,
            format_func=lambda c: normalize_column_name(c)[:70],
            key="group_q",
        )
    with col2:
        response_options = ["Strongly disagree", "Somewhat disagree", "Somewhat agree", "Strongly agree"]
        selected_r = st.selectbox("Choose a response", response_options, key="group_r")

    group_count = (df[selected_q] == selected_r).sum()
    if group_count > 0:
        st.markdown(
            f'**{group_count} {audience}** answered "{selected_r}" on this question. '
            f"Here's how they compare to everyone else:"
        )

        comparison = compute_group_comparison(df, selected_q, selected_r)
        if not comparison.empty:
            fig = group_comparison_chart(
                comparison,
                group_label=f'"{selected_r}"',
                title=f'{audience_cap} who answered "{selected_r}" vs. Everyone Else',
            )
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Show biggest differences
            biggest_gaps = comparison.reindex(comparison["Difference"].abs().sort_values(ascending=False).index).head(5)
            if not biggest_gaps.empty:
                st.markdown("**Biggest differences:**")
                for _, row in biggest_gaps.iterrows():
                    direction = "lower" if row["Difference"] < 0 else "higher"
                    st.markdown(
                        f'- **{abs(row["Difference"]):.2f} points {direction}** on "{row["Question"]}"'
                    )
    else:
        st.info(f'No {audience} answered "{selected_r}" on this question.')

# Grade comparison
if "_grade" in df.columns and likert_cols:
    profile_label = "Grade-Level Profiles" if selected_type in ("Student", "All Types") else "Group Profiles"
    st.markdown(f"### {profile_label}")
    st.markdown("See how each grade's overall sentiment profile compares.")

    grade_profiles = []
    for grade in sorted(df["_grade"].dropna().astype(str).unique()):
        grade_df = df[df["_grade"] == grade]
        grade_scores = compute_student_scores(grade_df)
        valid = grade_scores.dropna()
        if len(valid) > 0:
            grade_profiles.append({
                "Grade": grade,
                "Avg Sentiment": round(valid.mean(), 2),
                "Students": len(grade_df),
                "Below 2.0": int((valid < 2.0).sum()),
                "Above 3.0": int((valid > 3.0).sum()),
            })

    if grade_profiles:
        grade_df_display = pd.DataFrame(grade_profiles)
        st.dataframe(grade_df_display, use_container_width=True, hide_index=True)

# ============================================================
# SECTION 4: OPEN RESPONSE SENTIMENT
# ============================================================
st.markdown("---")
st.markdown("## Open Response Analysis")
st.markdown(
    "Automatic analysis of free-text responses to spot positive themes, "
    "negative themes, and responses that may need follow-up attention."
)

sentiment_df = analyze_open_response_sentiment(df)

if not sentiment_df.empty:
    # Overall sentiment breakdown
    sent_counts = sentiment_df["sentiment"].value_counts()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Responses Analyzed", len(sentiment_df))
    col2.metric("Positive", int(sent_counts.get("positive", 0)),
                help="More positive than negative words")
    col3.metric("Negative", int(sent_counts.get("negative", 0)),
                help="More negative than positive words")
    col4.metric("Needs Review", int(sentiment_df["has_concern"].sum()),
                help="Contains words related to safety, bullying, or wellbeing concerns")

    # Flagged concerns
    concerns = sentiment_df[sentiment_df["has_concern"]]
    if len(concerns) > 0:
        st.markdown("### Responses That May Need Follow-Up")
        st.markdown(
            "These responses contain words related to **safety, bullying, harassment, "
            "or mental health**. They may warrant a closer look from the CARE team."
        )
        for _, row in concerns.iterrows():
            keywords = ", ".join(row["concern_words"])
            st.warning(f'**[{row["question"][:50]}]** "{row["text"][:200]}..." '
                       f'(flagged: {keywords})'
                       if len(row["text"]) > 200
                       else f'**[{row["question"][:50]}]** "{row["text"]}" '
                       f'(flagged: {keywords})')

    # Positive vs negative themes
    st.markdown("### Response Themes")
    tab1, tab2 = st.tabs(["Positive Responses", "Negative Responses"])

    with tab1:
        positive = sentiment_df[sentiment_df["sentiment"] == "positive"]
        if len(positive) > 0:
            st.markdown(f"**{len(positive)} positive responses.** Sample:")
            for _, row in positive.head(15).iterrows():
                st.markdown(f'- *"{row["text"][:150]}"*')
        else:
            st.info("No clearly positive responses detected.")

    with tab2:
        negative = sentiment_df[sentiment_df["sentiment"] == "negative"]
        if len(negative) > 0:
            st.markdown(f"**{len(negative)} negative responses.** Sample:")
            for _, row in negative.head(15).iterrows():
                st.markdown(f'- *"{row["text"][:150]}"*')
        else:
            st.info("No clearly negative responses detected.")
else:
    st.info("No open-ended responses found in this survey.")
