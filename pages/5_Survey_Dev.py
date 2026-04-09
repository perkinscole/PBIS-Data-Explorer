import streamlit as st
import pandas as pd
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    get_open_response_columns, normalize_column_name, classify_column,
    compute_agreement_score, QUESTION_CATEGORIES, LIKERT_MAP,
)
from utils.theme import apply_theme, get_survey_type_filter, filter_surveys_by_type
from pathlib import Path

apply_theme()

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

# Type filter
selected_type = get_survey_type_filter()
surveys, meta = filter_surveys_by_type(
    st.session_state.surveys, st.session_state.survey_meta, selected_type
)

if not surveys:
    st.info(f"No {selected_type} surveys loaded. Upload data or change the type filter.")
    st.stop()

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

# --- Section 5: Survey Generator ---
st.markdown("---")
st.markdown("### Survey Generator")
st.markdown(
    "Build a new survey from your existing questions and suggested additions. "
    "The output is formatted so you can copy it directly into **Google Forms**."
)

# Question bank: pull from all existing questions + new suggestions
SUGGESTED_NEW_QUESTIONS = {
    "School Belonging": [
        ("I feel like my opinions are heard and valued at RAMS.", "likert"),
        ("I feel welcome when I walk into RAMS each day.", "likert"),
    ],
    "Safety": [
        ("I feel safe in the hallways and common areas at RAMS.", "likert"),
        ("I feel safe in my classrooms at RAMS.", "likert"),
    ],
    "Success": [
        ("My teachers help me set goals for my learning.", "likert"),
        ("I believe I can be successful at RAMS.", "likert"),
    ],
    "Teacher Respect": [
        ("Teachers listen to students when they have concerns.", "likert"),
        ("I feel that teachers care about me as a person.", "likert"),
    ],
    "Student Respect": [
        ("Students at RAMS are kind to each other online and on social media.", "likert"),
    ],
    "Social-Emotional Learning": [
        ("I have learned strategies to manage my emotions at RAMS.", "likert"),
        ("I know how to resolve conflicts peacefully.", "likert"),
        ("I feel comfortable asking for help when I need it.", "likert"),
    ],
    "CARE Values": [
        ("I can explain what the RAMS CARE values mean to me.", "likert"),
    ],
    "Behavior Support": [
        ("The reward system at RAMS motivates me to show positive behavior.", "likert"),
    ],
    "Peer Connections": [
        ("I have at least one friend at RAMS I can count on.", "likert"),
    ],
    "School Environment": [
        ("RAMS is a clean and well-maintained school.", "likert"),
        ("I feel proud to be a student at RAMS.", "likert"),
    ],
    "Family & Community": [
        ("My family feels welcome at RAMS.", "likert"),
        ("RAMS does a good job communicating with my family.", "likert"),
    ],
}

# Survey type selector
survey_audience = st.selectbox(
    "Who is this survey for?",
    ["Student", "Staff", "Parents and Family"],
    key="gen_audience",
)

st.markdown("#### Select Questions")
st.markdown(
    "Check the questions you want to include. "
    "Existing questions come from your uploaded surveys. "
    "New suggested questions are marked with a star."
)

selected_questions = []

# Tab layout: existing vs new
tab_existing, tab_new, tab_custom = st.tabs([
    "Existing Questions", "Suggested New Questions", "Write Your Own"
])

with tab_existing:
    st.markdown("*Questions from your uploaded surveys:*")

    # Group existing questions by category
    existing_by_cat = {}
    for q, info in all_questions.items():
        cat = None
        q_lower = q.lower()
        for category, patterns in QUESTION_CATEGORIES.items():
            for p in patterns:
                if p.lower() in q_lower:
                    cat = category.replace("_", " ").title()
                    break
            if cat:
                break
        if not cat:
            cat = "Other"
        existing_by_cat.setdefault(cat, []).append((q, info["type"]))

    for cat in sorted(existing_by_cat.keys()):
        st.markdown(f"**{cat}**")
        for q, qtype in existing_by_cat[cat]:
            if st.checkbox(q[:80], key=f"eq_{hash(q)}", value=True):
                selected_questions.append({
                    "question": q,
                    "type": qtype,
                    "source": "existing",
                })

with tab_new:
    st.markdown("*Suggested additions based on PBIS best practices:*")
    for cat, questions in SUGGESTED_NEW_QUESTIONS.items():
        st.markdown(f"**{cat}**")
        for q, qtype in questions:
            if st.checkbox(f"  {q}", key=f"nq_{hash(q)}"):
                selected_questions.append({
                    "question": q,
                    "type": qtype,
                    "source": "new",
                })

with tab_custom:
    st.markdown("*Add your own questions:*")
    custom_count = st.number_input(
        "How many custom questions?", min_value=0, max_value=20, value=0, key="custom_count"
    )
    for i in range(int(custom_count)):
        col1, col2 = st.columns([4, 1])
        with col1:
            q_text = st.text_input(f"Question {i+1}", key=f"cq_text_{i}")
        with col2:
            q_type = st.selectbox(
                "Type",
                ["likert", "yes_no", "open_response"],
                format_func=lambda x: {"likert": "Agree/Disagree", "yes_no": "Yes/No", "open_response": "Open-ended"}[x],
                key=f"cq_type_{i}",
            )
        if q_text.strip():
            selected_questions.append({
                "question": q_text.strip(),
                "type": q_type,
                "source": "custom",
            })

# Preview and export
st.markdown("---")
st.markdown("#### Survey Preview")
st.markdown(f"**{len(selected_questions)} questions selected** for {survey_audience} survey")

if selected_questions:
    # Build the survey output
    lines = []
    lines.append(f"RAMS CARE Survey ({survey_audience})")
    lines.append("=" * 50)
    lines.append("")

    # Always start with grade/role question
    if survey_audience == "Student":
        lines.append("1. What grade am I in?")
        lines.append("   Type: Multiple choice")
        lines.append("   Options: 6th Grade, 7th Grade, 8th Grade")
        lines.append("")
        q_num = 2
    elif survey_audience == "Staff":
        lines.append("1. What is your role?")
        lines.append("   Type: Multiple choice")
        lines.append("   Options: Teacher, Administrator, Counselor, Support Staff, Other")
        lines.append("")
        q_num = 2
    else:
        lines.append("1. What grade is your child in?")
        lines.append("   Type: Multiple choice")
        lines.append("   Options: 6th Grade, 7th Grade, 8th Grade, Multiple grades")
        lines.append("")
        q_num = 2

    for item in selected_questions:
        q = item["question"]
        qtype = item["type"]
        star = " (NEW)" if item["source"] == "new" else ""
        star = " (CUSTOM)" if item["source"] == "custom" else star

        lines.append(f"{q_num}. {q}{star}")

        if qtype == "likert":
            lines.append("   Type: Multiple choice (single answer)")
            lines.append("   Options: Strongly agree, Somewhat agree, Somewhat disagree, Strongly disagree")
        elif qtype == "yes_no":
            lines.append("   Type: Multiple choice (single answer)")
            lines.append("   Options: Yes, No")
        elif qtype == "open_response":
            lines.append("   Type: Long answer text")

        lines.append("")
        q_num += 1

    survey_text = "\n".join(lines)

    # Display preview
    st.text_area(
        "Survey (copy this into Google Forms)",
        survey_text,
        height=400,
        key="survey_preview",
    )

    # Copy-friendly summary
    st.markdown("#### Google Forms Instructions")
    st.markdown(f"""
1. Go to [forms.google.com](https://forms.google.com) and create a new blank form
2. Title it: **RAMS CARE Survey ({survey_audience})**
3. For each question above:
   - **Agree/Disagree** questions: Use "Multiple choice" and add the four options
   - **Yes/No** questions: Use "Multiple choice" with Yes and No
   - **Open-ended** questions: Use "Long answer"
4. Under Settings, turn on **"Limit to 1 response"** if using school accounts
5. Consider making all questions **required**

**Tip:** In Google Forms you can duplicate a question to quickly create
multiple Agree/Disagree questions with the same answer options.
""")

    # Download as text file
    st.download_button(
        "Download Survey as Text File",
        survey_text,
        file_name=f"RAMS_CARE_Survey_{survey_audience}_{pd.Timestamp.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )
else:
    st.info("Select questions from the tabs above to build your survey.")
