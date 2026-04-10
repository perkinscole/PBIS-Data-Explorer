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

# --- Section 4: Suggested Improvements (type-aware) ---
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

# Type-specific suggestions
SUGGESTIONS_BY_TYPE = {
    "Student": [
        "Consider adding questions about **student voice and agency** - "
        "e.g., 'I feel my opinions are valued at RAMS.'",
        "Consider adding questions about **social-emotional learning** - "
        "e.g., 'I have learned strategies to manage my emotions at RAMS.'",
        "Consider adding questions about **family/community connection** - "
        "e.g., 'My family feels welcome at RAMS.'",
        "Consider differentiating between **in-class** and **outside-class** experiences - "
        "students may feel differently about hallways, cafeteria, etc. vs. classrooms.",
        "Consider adding a question about **peer relationships online** - "
        "e.g., 'Students at RAMS are kind to each other on social media.'",
    ],
    "Staff": [
        "Consider adding questions about **professional development** - "
        "e.g., 'I have received adequate training on PBIS practices.'",
        "Consider adding questions about **collaboration** - "
        "e.g., 'Staff at RAMS work together to support student behavior.'",
        "Consider adding questions about **administrative support** - "
        "e.g., 'I feel supported by administrators when handling behavior issues.'",
        "Consider adding questions about **staff wellbeing** - "
        "e.g., 'I feel valued as a member of the RAMS community.'",
        "Consider adding questions about **consistency** - "
        "e.g., 'RAMS CARE expectations are applied consistently across classrooms.'",
        "Consider adding questions about **data use** - "
        "e.g., 'I use behavior data (Kickboard) to inform my teaching practices.'",
    ],
    "Parents and Family": [
        "Consider adding questions about **communication quality** - "
        "e.g., 'I understand the behavior expectations at RAMS.'",
        "Consider adding questions about **engagement opportunities** - "
        "e.g., 'RAMS provides meaningful ways for families to be involved.'",
        "Consider adding questions about **home-school connection** - "
        "e.g., 'I know how to support the CARE values at home.'",
        "Consider adding questions about **transparency** - "
        "e.g., 'I am kept informed about my child's behavioral progress.'",
        "Consider adding questions about **accessibility** - "
        "e.g., 'RAMS communication is available in languages my family speaks.'",
        "Consider adding questions about **trust** - "
        "e.g., 'I trust that my child is treated fairly at RAMS.'",
    ],
}

# Add type-specific suggestions
type_suggestions = SUGGESTIONS_BY_TYPE.get(selected_type, [])
if not type_suggestions and selected_type == "All Types":
    type_suggestions = SUGGESTIONS_BY_TYPE["Student"]
suggestions.extend(type_suggestions)

# Check for missing safety questions across survey types
for df_check, m in zip(surveys, meta):
    likert = get_likert_columns(df_check)
    all_cols = [c.lower() for c in likert]
    if not any("safe" in c for c in all_cols):
        suggestions.append(
            f"**{m['label']}** may be missing a question about safety. "
            "Safety questions are a key PBIS indicator across all survey types."
        )

for i, s in enumerate(suggestions, 1):
    st.markdown(f"{i}. {s}")

# --- Section 5: Survey Generator ---
st.markdown("---")
st.markdown("### Survey Generator")
st.markdown(
    "Build a new survey from your existing questions and suggested additions. "
    "The output is formatted so you can copy it directly into **Google Forms**."
)

# Question bank organized by survey type
SUGGESTED_STUDENT_QUESTIONS = {
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
}

SUGGESTED_STAFF_QUESTIONS = {
    "PBIS Implementation": [
        ("I have received adequate training on PBIS/RAMS CARE practices.", "likert"),
        ("I feel confident implementing RAMS CARE expectations in my classroom.", "likert"),
        ("I have had input into developing our school-wide behavior expectations.", "yes_no"),
    ],
    "Collaboration & Support": [
        ("Staff at RAMS work together to support student behavior.", "likert"),
        ("I feel supported by administrators when handling behavior issues.", "likert"),
        ("I feel valued as a member of the RAMS community.", "likert"),
    ],
    "Consistency": [
        ("RAMS CARE expectations are applied consistently across classrooms.", "likert"),
        ("I teach and reteach behavior expectations regularly.", "yes_no"),
        ("I use the RAMS CARE language when acknowledging positive behavior.", "yes_no"),
    ],
    "Acknowledgement & Recognition": [
        ("I feel recognized for my efforts to promote positive behavior.", "likert"),
        ("The student acknowledgement system (Kickboard) is effective.", "likert"),
        ("I positively acknowledge students at least daily.", "yes_no"),
    ],
    "Data & Improvement": [
        ("I use behavior data to inform my teaching practices.", "yes_no"),
        ("Our team reviews behavior data regularly to make decisions.", "yes_no"),
    ],
    "Staff Wellbeing": [
        ("I feel safe at RAMS.", "likert"),
        ("I would recommend RAMS as a place to work.", "likert"),
    ],
    "Open Feedback": [
        ("What barriers do you face in implementing RAMS CARE expectations?", "open_response"),
        ("What is working well with our PBIS approach that we should continue?", "open_response"),
    ],
}

SUGGESTED_FAMILY_QUESTIONS = {
    "Safety & Wellbeing": [
        ("My child feels safe at RAMS.", "likert"),
        ("My child feels safe traveling to and from RAMS.", "likert"),
        ("My child feels successful at RAMS.", "likert"),
    ],
    "School Climate": [
        ("All students are treated fairly at RAMS.", "likert"),
        ("RAMS has high standards for academic achievement.", "likert"),
        ("RAMS sets clear rules for behavior.", "likert"),
        ("School rules are consistently enforced at RAMS.", "likert"),
    ],
    "Communication & Engagement": [
        ("RAMS staff communicate well with parents and caregivers.", "likert"),
        ("I feel comfortable talking to teachers at RAMS.", "likert"),
        ("I am kept informed about my child's behavioral progress.", "likert"),
        ("RAMS provides meaningful ways for families to be involved.", "likert"),
    ],
    "CARE Values": [
        ("I understand the RAMS CARE values (Compassion, Acceptance, Respect, Effort).", "likert"),
        ("I know how to support the CARE values at home.", "likert"),
        ("My child is recognized for good behavior at RAMS.", "likert"),
    ],
    "Respect & Trust": [
        ("Administrators at RAMS treat all students with respect.", "likert"),
        ("I trust that my child is treated fairly at RAMS.", "likert"),
    ],
    "Accessibility": [
        ("RAMS communication is available in languages my family speaks.", "likert"),
        ("I attend open-house and other events hosted by RAMS.", "likert"),
    ],
    "Open Feedback": [
        ("What is RAMS doing well to support your child?", "open_response"),
        ("What could RAMS improve to better support families?", "open_response"),
    ],
}

# Pick the right question bank based on generator audience
SUGGESTED_QUESTIONS_BY_TYPE = {
    "Student": SUGGESTED_STUDENT_QUESTIONS,
    "Staff": SUGGESTED_STAFF_QUESTIONS,
    "Parents and Family": SUGGESTED_FAMILY_QUESTIONS,
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

selected_demographics = []
selected_questions = []

# Tab layout
tab_demo, tab_existing, tab_new, tab_custom = st.tabs([
    "Demographics", "Existing Questions", "Suggested New Questions", "Write Your Own"
])

# --- Demographics tab ---
DEMOGRAPHICS_BY_TYPE = {
    "Student": [
        {"question": "What grade am I in?", "type": "multiple_choice", "options": "6th Grade, 7th Grade, 8th Grade", "default": True},
        {"question": "What is your gender?", "type": "multiple_choice", "options": "Male, Female, Non-binary, Prefer not to say", "default": False},
        {"question": "What is your race/ethnicity?", "type": "multiple_choice", "options": "Asian, Black/African American, Hispanic/Latino, Native American, Pacific Islander, White, Two or more races, Prefer not to say", "default": False},
        {"question": "How long have you been a student at RAMS?", "type": "multiple_choice", "options": "This is my first year, 2 years, 3 years", "default": False},
        {"question": "Do you receive free or reduced lunch?", "type": "multiple_choice", "options": "Yes, No, I'm not sure", "default": False},
        {"question": "Do you have an IEP or 504 plan?", "type": "multiple_choice", "options": "Yes, No, I'm not sure", "default": False},
    ],
    "Staff": [
        {"question": "What is your role?", "type": "multiple_choice", "options": "Teacher, Administrator, Counselor, Support Staff, Paraprofessional, Other", "default": True},
        {"question": "How many years have you worked at RAMS?", "type": "multiple_choice", "options": "Less than 1 year, 1-3 years, 4-6 years, 7-10 years, More than 10 years", "default": False},
        {"question": "What grade level(s) do you primarily work with?", "type": "checkboxes", "options": "6th Grade, 7th Grade, 8th Grade, All grades", "default": False},
        {"question": "What department or subject area do you work in?", "type": "short_text", "options": "", "default": False},
    ],
    "Parents and Family": [
        {"question": "What grade(s) is your student in?", "type": "checkboxes", "options": "6th Grade, 7th Grade, 8th Grade", "default": True},
        {"question": "How many students do you have at RAMS?", "type": "multiple_choice", "options": "1, 2, 3 or more", "default": False},
        {"question": "How long has your student attended RAMS?", "type": "multiple_choice", "options": "This is their first year, 2 years, 3 years", "default": False},
        {"question": "What is the primary language spoken at home?", "type": "multiple_choice", "options": "English, Spanish, Other", "default": False},
        {"question": "How would you describe your involvement at RAMS?", "type": "multiple_choice", "options": "Very involved, Somewhat involved, Not very involved, Not involved at all", "default": False},
    ],
}

with tab_demo:
    st.markdown(f"*Select demographic questions to include for **{survey_audience}** surveys:*")
    st.markdown(
        "Demographic questions appear at the beginning of the survey and help "
        "you break down results by group (e.g., by grade, role, or years at RAMS)."
    )

    demo_options = DEMOGRAPHICS_BY_TYPE.get(survey_audience, [])
    for demo in demo_options:
        checked = st.checkbox(
            demo["question"],
            value=demo["default"],
            key=f"demo_{hash(demo['question'])}",
        )
        if demo["options"]:
            st.caption(f"Options: {demo['options']}")
        if checked:
            selected_demographics.append(demo)

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
    suggested_qs = SUGGESTED_QUESTIONS_BY_TYPE.get(survey_audience, SUGGESTED_STUDENT_QUESTIONS)
    st.markdown(f"*Suggested additions for **{survey_audience}** surveys based on PBIS best practices:*")
    for cat, questions in suggested_qs.items():
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
total_q = len(selected_demographics) + len(selected_questions)
st.markdown(f"**{total_q} questions selected** for {survey_audience} survey ({len(selected_demographics)} demographic, {len(selected_questions)} survey)")

if selected_demographics or selected_questions:
    # Build the survey output
    lines = []
    lines.append(f"RAMS CARE Survey ({survey_audience})")
    lines.append("=" * 50)
    lines.append("")

    q_num = 1

    # Demographics section
    if selected_demographics:
        lines.append("--- DEMOGRAPHICS ---")
        lines.append("")
        for demo in selected_demographics:
            lines.append(f"{q_num}. {demo['question']}")
            type_label = {
                "multiple_choice": "Multiple choice (single answer)",
                "checkboxes": "Checkboxes (select all that apply)",
                "short_text": "Short answer text",
            }.get(demo["type"], demo["type"])
            lines.append(f"   Type: {type_label}")
            if demo["options"]:
                lines.append(f"   Options: {demo['options']}")
            lines.append("")
            q_num += 1

    if selected_questions:
        lines.append("--- SURVEY QUESTIONS ---")
        lines.append("")

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
    st.info("Select questions from the Demographics, Existing, or Suggested tabs to build your survey.")
