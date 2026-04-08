import pandas as pd
import os
import re
from pathlib import Path

# Likert-scale response values for scoring (4-point scale used in RAMS surveys)
LIKERT_MAP = {
    "Strongly agree": 4,
    "Somewhat agree": 3,
    "Somewhat disagree": 2,
    "Strongly disagree": 1,
}

YES_NO_MAP = {
    "Yes": 1,
    "No": 0,
}

# Canonical question categories for cross-survey comparison
QUESTION_CATEGORIES = {
    "school_belonging": [
        "I like school",
        "I feel like I fit in at RAMS",
        "I feel connected to others at RAMS",
        "Most days I look forward to going to school",
    ],
    "safety": [
        "RAMS is a place where I feel safe",
    ],
    "success": [
        "I feel successful at RAMS",
        "I feel like RAMS has high standards for academic achievement",
    ],
    "teacher_respect": [
        "Teachers treat me with respect",
        "Adults in this school treat all students with respect",
        "Teachers treat all students fairly",
        "I feel that teachers know their students and provide them with what they need to be successful",
    ],
    "student_respect": [
        "Students at RAMS treat each other with respect",
        "Students show respect to other students regardless of their academic",
        "Students at RAMS are treated fairly by other students regardless of race",
        "All students in RAMS are treated fairly, regardless of their appearance",
        "Students in RAMS are welcoming to new students",
    ],
    "care_values": [
        "The RAMS CARE values of COMPASSION, ACCEPTANCE, RESPECT, EFFORT are",
        "Are the RAMS CARE behavior expectations meaningful to you",
        "Do you know what positive behaviors you are supposed to show at RAMS",
    ],
    "behavior_support": [
        "In the past week, did you see teachers/staff praise or reward other students",
        "In the past week, did teachers/staff praise or reward YOU",
        "Do you think RAMS' use of",
    ],
    "peer_connections": [
        "I know (at least one) student at RAMS that I can talk to",
        "I know (at least one) adult at RAMS that I can talk with",
    ],
    "school_environment": [
        "RAMS sets clear rules for behavior",
        "Do you think the RAMS school community takes pride in keeping RAMS",
    ],
}


def parse_filename(filename):
    """Extract survey type and date from filename."""
    name = Path(filename).stem
    survey_match = re.search(r"Student #(\d)", name)
    survey_num = int(survey_match.group(1)) if survey_match else None

    date_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December|May-June)\s+(\d{4})",
        name,
    )
    if date_match:
        month_str = date_match.group(1)
        year = date_match.group(2)
        period = f"{month_str} {year}"
    else:
        period = "Unknown"

    return {
        "survey_num": survey_num,
        "period": period,
        "label": f"Survey #{survey_num} - {period}" if survey_num else name,
    }


def classify_column(col_name):
    """Classify a column as likert, yes_no, open_response, or metadata."""
    col_lower = col_name.lower().strip()
    if col_lower in ("timestamp", "what grade am i in?"):
        return "metadata"

    open_keywords = [
        "one thing",
        "name one",
        "what types of prizes",
        "please tell us why",
    ]
    if any(kw in col_lower for kw in open_keywords):
        return "open_response"

    yes_no_keywords = [
        "are the rams care behavior expectations",
        "do you know what positive behaviors",
        "in the past week",
        "have you traded",
    ]
    if any(kw in col_lower for kw in yes_no_keywords):
        return "yes_no"

    return "likert"


def normalize_column_name(col_name):
    """Create a short normalized version of a column name for matching."""
    return re.sub(r"\s+", " ", col_name.strip().rstrip(".").rstrip("?")).strip()


def match_category(col_name):
    """Match a column name to a question category."""
    normalized = normalize_column_name(col_name).lower()
    for category, patterns in QUESTION_CATEGORIES.items():
        for pattern in patterns:
            if pattern.lower() in normalized:
                return category
    return None


def load_survey_file(filepath):
    """Load a single survey file and return processed DataFrame."""
    df = pd.read_excel(filepath, sheet_name=0)
    meta = parse_filename(os.path.basename(filepath))

    df["_source_file"] = os.path.basename(filepath)
    df["_survey_num"] = meta["survey_num"]
    df["_period"] = meta["period"]
    df["_label"] = meta["label"]

    grade_col = [c for c in df.columns if "grade" in c.lower()]
    if grade_col:
        df["_grade"] = df[grade_col[0]].astype(str).str.strip()

    return df, meta


def get_likert_columns(df):
    """Return columns that contain Likert scale responses."""
    return [c for c in df.columns if not c.startswith("_") and classify_column(c) == "likert"]


def get_yes_no_columns(df):
    """Return columns that contain Yes/No responses."""
    return [c for c in df.columns if not c.startswith("_") and classify_column(c) == "yes_no"]


def get_open_response_columns(df):
    """Return columns that contain open-ended text responses."""
    return [c for c in df.columns if not c.startswith("_") and classify_column(c) == "open_response"]


def compute_likert_summary(df, columns=None):
    """Compute percentage breakdown for each Likert question."""
    if columns is None:
        columns = get_likert_columns(df)

    results = []
    for col in columns:
        counts = df[col].value_counts(normalize=True) * 100
        for response in ["Strongly agree", "Somewhat agree", "Somewhat disagree", "Strongly disagree"]:
            results.append({
                "Question": normalize_column_name(col),
                "Response": response,
                "Percentage": counts.get(response, 0),
                "Category": match_category(col) or "other",
            })
    return pd.DataFrame(results)


def compute_agreement_score(df, columns=None):
    """Compute average agreement score (1-5) for each Likert question."""
    if columns is None:
        columns = get_likert_columns(df)

    scores = {}
    for col in columns:
        mapped = df[col].map(LIKERT_MAP)
        scores[normalize_column_name(col)] = {
            "mean": mapped.mean(),
            "std": mapped.std(),
            "n": mapped.count(),
            "category": match_category(col) or "other",
        }
    return scores


def load_all_surveys(directory):
    """Load all survey files from a directory."""
    all_data = []
    all_meta = []

    xlsx_files = sorted(Path(directory).glob("*.xlsx"))
    seen = set()
    for f in xlsx_files:
        # Skip duplicate files (the (1) copy)
        basename = f.stem.replace(" (1)", "")
        if basename in seen:
            continue
        seen.add(basename)

        try:
            df, meta = load_survey_file(str(f))
            all_data.append(df)
            all_meta.append(meta)
        except Exception as e:
            print(f"Error loading {f.name}: {e}")

    return all_data, all_meta


def get_common_questions(dataframes):
    """Find questions that appear across multiple surveys for trend analysis."""
    question_sets = []
    for df in dataframes:
        likert = set(normalize_column_name(c) for c in get_likert_columns(df))
        yes_no = set(normalize_column_name(c) for c in get_yes_no_columns(df))
        question_sets.append(likert | yes_no)

    if not question_sets:
        return set()

    common = question_sets[0]
    for qs in question_sets[1:]:
        common = common & qs
    return common


def get_all_questions(dataframes):
    """Get union of all questions across surveys."""
    all_q = set()
    for df in dataframes:
        for c in df.columns:
            if not c.startswith("_") and c not in ("Timestamp",):
                all_q.add(normalize_column_name(c))
    return all_q


def sort_periods(periods):
    """Sort survey periods chronologically."""
    month_order = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "May-June": 5.5, "June": 6, "July": 7,
        "August": 8, "September": 9, "October": 10,
        "November": 11, "December": 12,
    }

    def sort_key(p):
        parts = p.rsplit(" ", 1)
        if len(parts) == 2:
            month, year = parts
            return (int(year), month_order.get(month, 0))
        return (0, 0)

    return sorted(periods, key=sort_key)
