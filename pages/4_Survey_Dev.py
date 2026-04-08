import streamlit as st
import pandas as pd
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    get_open_response_columns, normalize_column_name, classify_column,
    compute_agreement_score, QUESTION_CATEGORIES, LIKERT_MAP,
)
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Survey Development Tool")
st.markdown("Analyze survey questions across versions and identify opportunities for improvement.")

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

# --- Section 1: Question Evolution ---
st.markdown("### Question Evolution Across Surveys")
st.markdown("See which questions were added, removed, or modified between survey versions.")

# Build question presence matrix
all_questions = {}
for df, m in zip(surveys, meta):
    cols = [c for c in df.columns if not c.startswith("_") and c != "Timestamp"]
    for c in cols:
        normalized = normalize_column_name(c)
        if normalized not in all_questions:
            all_questions[normalized] = {"type": classify_column(c), "surveys": []}
        all_questions[normalized]["surveys"].append(m["label"])

# Display as a presence matrix
survey_labels = [m["label"] for m in meta]
presence_data = []
for q, info in sorted(all_questions.items()):
    row = {"Question": q[:80], "Type": info["type"]}
    for label in survey_labels:
        row[label] = "Yes" if label in info["surveys"] else ""
    presence_data.append(row)

presence_df = pd.DataFrame(presence_data)

# Filter options
q_filter = st.radio(
    "Show",
    ["All Questions", "Added/Removed Only", "Present in All Surveys"],
    horizontal=True,
)

if q_filter == "Added/Removed Only":
    presence_df = presence_df[
        presence_df[survey_labels].apply(
            lambda row: not all(row == "Yes") and not all(row == ""), axis=1
        )
    ]
elif q_filter == "Present in All Surveys":
    presence_df = presence_df[
        presence_df[survey_labels].apply(lambda row: all(row == "Yes"), axis=1)
    ]

st.dataframe(
    presence_df.style.map(
        lambda v: "background-color: #d5f5e3" if v == "Yes" else "",
        subset=survey_labels,
    ),
    use_container_width=True,
    height=400,
)

# --- Section 2: Low Variance Questions ---
st.markdown("---")
st.markdown("### Low-Variance Questions")
st.markdown(
    "Questions where almost everyone gives the same answer may not be capturing "
    "useful variation. Consider rewording or replacing these."
)

selected_survey = st.selectbox(
    "Analyze survey",
    range(len(survey_labels)),
    format_func=lambda i: survey_labels[i],
    key="var_survey",
)

df = surveys[selected_survey]
likert_cols = get_likert_columns(df)

if likert_cols:
    variance_data = []
    for col in likert_cols:
        mapped = df[col].map(LIKERT_MAP).dropna()
        if len(mapped) > 0:
            variance_data.append({
                "Question": normalize_column_name(col)[:70],
                "Mean": round(mapped.mean(), 2),
                "Std Dev": round(mapped.std(), 2),
                "% Top Response": round(df[col].value_counts(normalize=True).iloc[0] * 100, 1),
                "Top Response": df[col].value_counts().index[0],
                "N": len(mapped),
            })

    var_df = pd.DataFrame(variance_data).sort_values("Std Dev")

    # Color low variance rows
    def highlight_low_var(row):
        if row["Std Dev"] < 0.7:
            return ["background-color: #fadbd8"] * len(row)
        return [""] * len(row)

    st.dataframe(
        var_df.style.apply(highlight_low_var, axis=1),
        use_container_width=True,
    )

    low_var = var_df[var_df["Std Dev"] < 0.7]
    if len(low_var) > 0:
        st.warning(
            f"**{len(low_var)} questions** have very low variance (Std Dev < 0.7). "
            "These questions might not be differentiating between students effectively."
        )

# --- Section 3: Category Coverage ---
st.markdown("---")
st.markdown("### PBIS Framework Coverage")
st.markdown(
    "Check how well your surveys cover the key areas of the PBIS framework. "
    "Gaps suggest areas where new questions could be added."
)

category_coverage = {}
for cat, patterns in QUESTION_CATEGORIES.items():
    label = cat.replace("_", " ").title()
    matched = []
    for q in all_questions:
        q_lower = q.lower()
        for p in patterns:
            if p.lower() in q_lower:
                matched.append(q)
                break
    category_coverage[label] = {
        "count": len(matched),
        "questions": matched,
    }

coverage_df = pd.DataFrame([
    {"Category": cat, "Questions": info["count"]}
    for cat, info in category_coverage.items()
]).sort_values("Questions", ascending=True)

import plotly.express as px

fig = px.bar(
    coverage_df,
    x="Questions",
    y="Category",
    orientation="h",
    title="Number of Questions per PBIS Category",
    color="Questions",
    color_continuous_scale=["#e74c3c", "#f9e79f", "#2ecc71"],
)
st.plotly_chart(fig, use_container_width=True)

# Show details per category
for cat, info in sorted(category_coverage.items()):
    with st.expander(f"{cat} ({info['count']} questions)"):
        if info["questions"]:
            for q in info["questions"]:
                st.markdown(f"- {q}")
        else:
            st.markdown("*No questions in this category yet.*")

# --- Section 4: Suggested Improvements ---
st.markdown("---")
st.markdown("### Suggested Improvements")

suggestions = []

# Check for low-coverage categories
for cat, info in category_coverage.items():
    if info["count"] < 2:
        suggestions.append(
            f"**{cat}** has only {info['count']} question(s). "
            "Consider adding more questions to better capture this dimension."
        )

# Check for missing categories in specific surveys
for df, m in zip(surveys, meta):
    likert = get_likert_columns(df)
    if not any("safe" in c.lower() for c in likert):
        suggestions.append(
            f"**{m['label']}** may be missing a question about student safety. "
            "The 'I feel safe' question is important for PBIS assessment."
        )

# General suggestions
suggestions.extend([
    "Consider adding questions about **student voice and agency** - "
    "e.g., 'I feel my opinions are valued at RAMS.'",
    "Consider adding questions about **social-emotional learning** - "
    "e.g., 'I have learned strategies to manage my emotions at RAMS.'",
    "Consider adding questions about **family/community connection** - "
    "e.g., 'My family feels welcome at RAMS.'",
    "Consider differentiating between **in-class** and **outside-class** experiences - "
    "students may feel differently about hallways, cafeteria, etc. vs. classrooms.",
])

for i, s in enumerate(suggestions, 1):
    st.markdown(f"{i}. {s}")
