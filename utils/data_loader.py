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


def classify_column(col_name, series=None):
    """Classify a column as likert, yes_no, open_response, or metadata.
    If a pandas Series is provided, uses actual values for smarter detection."""
    col_lower = col_name.lower().strip()

    # Metadata columns
    metadata_patterns = [
        "timestamp", "what grade am i in?", "what is your role",
        "what grade is your child", "please indicate the grade",
        "approximately, how frequently",
    ]
    if any(col_lower.startswith(p) or col_lower == p for p in metadata_patterns):
        return "metadata"

    # Open response keywords (questions asking for free text)
    open_keywords = [
        "one thing", "name one", "what types of prizes", "please tell us why",
        "how would you improve", "what are some barriers", "what are some",
        "what would you", "what do you suggest", "what else", "please describe",
        "please explain", "any other", "additional comments", "what changes",
    ]
    if any(kw in col_lower for kw in open_keywords):
        return "open_response"

    # If we have actual data, use it for smarter classification
    if series is not None:
        values = series.dropna().astype(str).str.strip()
        if len(values) > 0:
            unique_vals = set(values.str.lower().unique())
            # Check if values are Likert
            likert_vals = {"strongly agree", "somewhat agree", "somewhat disagree", "strongly disagree"}
            if unique_vals & likert_vals:
                return "likert"
            # Check if values are Yes/No
            yes_no_vals = {"yes", "no", "n/a", "n/a (non-applicable)"}
            if unique_vals and unique_vals.issubset(yes_no_vals | {""}):
                return "yes_no"
            # If most values are long text, it's open response
            avg_len = values.str.len().mean()
            if avg_len > 50:
                return "open_response"
            # If only Yes/No present even mixed with some other vals
            if len(unique_vals) <= 5 and unique_vals & {"yes", "no"}:
                return "yes_no"

    # Keyword-based fallback for yes/no
    yes_no_keywords = [
        "are the rams care behavior expectations",
        "do you know what positive behaviors",
        "in the past week",
        "have you traded",
        "did you", "have you", "do you use", "do you think",
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

    # Detect grade/role column (students: "What grade", parents: "indicate the grade", staff: role)
    grade_col = [c for c in df.columns if "grade" in c.lower() or "what is your role" in c.lower()]
    if grade_col:
        raw_grade = df[grade_col[0]].astype(str).str.strip()
        # Filter out junk: Likert responses, numeric garbage, NaN
        invalid_values = {
            "strongly agree", "somewhat agree", "somewhat disagree",
            "strongly disagree", "yes", "no", "nan", "none", "",
            "n/a", "n/a (non-applicable)", "never",
            "0-2 times/week", "3-5 times/week", "more than 5 times/week",
        }
        raw_grade = raw_grade.where(
            ~raw_grade.str.lower().isin(invalid_values), other=pd.NA
        )
        df["_grade"] = raw_grade

    return df, meta


def get_likert_columns(df):
    """Return columns that contain Likert scale responses."""
    return [c for c in df.columns if not c.startswith("_") and classify_column(c, df[c]) == "likert"]


def get_yes_no_columns(df):
    """Return columns that contain Yes/No responses."""
    return [c for c in df.columns if not c.startswith("_") and classify_column(c, df[c]) == "yes_no"]


def get_open_response_columns(df):
    """Return columns that contain open-ended text responses."""
    return [c for c in df.columns if not c.startswith("_") and classify_column(c, df[c]) == "open_response"]


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
    """Load all survey files from a directory, applying any saved overrides."""
    import json

    all_data = []
    all_meta = []

    dir_path = Path(directory)
    xlsx_files = sorted(dir_path.glob("*.xlsx"))

    # Load overrides if they exist
    meta_file = dir_path / "_metadata.json"
    overrides = {}
    if meta_file.exists():
        try:
            overrides = json.loads(meta_file.read_text())
        except Exception:
            pass

    seen = set()
    for f in xlsx_files:
        # Skip duplicate files (the (1) copy)
        basename = f.stem.replace(" (1)", "")
        if basename in seen:
            continue
        seen.add(basename)

        try:
            df, meta = load_survey_file(str(f))

            # Apply overrides from upload page
            fname = f.name
            if fname in overrides:
                ov = overrides[fname]
                if ov.get("period"):
                    meta["period"] = ov["period"]
                    df["_period"] = ov["period"]
                stype = ov.get("survey_num")
                if stype and stype != "Auto-detect":
                    meta["survey_num"] = stype
                    df["_survey_num"] = stype
                meta["label"] = (
                    f"{meta['survey_num']} - {meta['period']}"
                    if meta.get("survey_num") and str(meta["survey_num"]) not in ("None", "Auto-detect")
                    else meta["period"]
                )
                df["_label"] = meta["label"]

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


# --- Student-level analysis functions ---

# All valid structured response values (not just 4-point Likert)
VALID_LIKERT_VALUES = set(LIKERT_MAP.keys())
VALID_STRUCTURED_VALUES = VALID_LIKERT_VALUES | {
    "Never", "Sometimes", "Frequently", "Always",
    "Yes", "No", "N/A", "N/A (Non-applicable)",
    "never", "sometimes", "frequently", "always",
}

# School-context sentiment words for open response analysis
POSITIVE_WORDS = {
    "good", "great", "awesome", "amazing", "love", "like", "best", "helpful",
    "kind", "nice", "respect", "respectful", "fair", "safe", "happy", "fun",
    "caring", "supportive", "welcoming", "friendly", "encourage", "proud",
    "excellent", "wonderful", "positive", "better", "improve", "thank",
    "appreciate", "enjoy", "comfortable", "included", "belong", "success",
}

NEGATIVE_WORDS = {
    "bad", "hate", "worst", "mean", "bully", "bullying", "unfair", "scary",
    "afraid", "unsafe", "disrespect", "rude", "boring", "annoying", "terrible",
    "horrible", "angry", "fight", "fighting", "racist", "racism", "discriminat",
    "threat", "harass", "exclude", "ignored", "lonely", "sad", "depressed",
    "anxiety", "scared", "violent", "violence", "drug", "vape", "weapon",
}

CONCERN_KEYWORDS = {
    "bully", "bullying", "bullied", "threat", "threaten", "harass", "harassment",
    "unsafe", "scared", "afraid", "weapon", "fight", "drug", "vape", "suicide",
    "kill", "die", "hurt", "abuse", "violent", "violence", "racist", "racism",
    "depressed", "depression", "anxiety", "self-harm", "cutting",
}


def compute_student_scores(df):
    """Compute per-student average Likert score (1-4 scale)."""
    likert_cols = get_likert_columns(df)
    # Map only valid Likert values, everything else becomes NaN
    numeric = df[likert_cols].apply(lambda col: col.map(LIKERT_MAP))
    scores = numeric.mean(axis=1)
    return scores


def detect_straightliners(df):
    """Flag students who gave identical Likert answers for every question.
    Returns boolean Series (True = straightliner)."""
    likert_cols = get_likert_columns(df)
    if not likert_cols:
        return pd.Series(False, index=df.index)
    responses = df[likert_cols]
    nunique = responses.nunique(axis=1)
    return nunique <= 1


def detect_data_errors(df):
    """Flag rows that have unexpected values in structured response columns.
    Returns boolean Series (True = has errors)."""
    likert_cols = get_likert_columns(df)
    yes_no_cols = get_yes_no_columns(df)
    check_cols = likert_cols + yes_no_cols
    if not check_cols:
        return pd.Series(False, index=df.index)

    has_error = pd.Series(False, index=df.index)
    for col in check_cols:
        invalid = ~df[col].isin(VALID_STRUCTURED_VALUES) & df[col].notna()
        has_error = has_error | invalid
    return has_error


def detect_contradictions(df, threshold=2.5):
    """Flag students with highly inconsistent responses across related categories.
    Computes per-category averages and flags if the range across categories
    exceeds the threshold (on 1-4 scale, max possible range is 3).
    Returns boolean Series (True = contradictory)."""
    likert_cols = get_likert_columns(df)
    if not likert_cols:
        return pd.Series(False, index=df.index)

    cat_scores = {}
    for col in likert_cols:
        cat = match_category(col)
        if cat and cat != "other":
            mapped = df[col].map(LIKERT_MAP)
            cat_scores.setdefault(cat, []).append(mapped)

    if len(cat_scores) < 2:
        return pd.Series(False, index=df.index)

    cat_means = pd.DataFrame({
        cat: pd.concat(cols, axis=1).mean(axis=1)
        for cat, cols in cat_scores.items()
    })

    score_range = cat_means.max(axis=1) - cat_means.min(axis=1)
    return score_range > threshold


def compute_correlation_matrix(df):
    """Compute correlation matrix between Likert questions."""
    likert_cols = get_likert_columns(df)
    numeric = df[likert_cols].apply(lambda col: col.map(LIKERT_MAP))
    short_names = [normalize_column_name(c)[:50] for c in likert_cols]
    numeric.columns = short_names
    return numeric.corr()


AT_RISK_PATTERNS = {
    "Student": {
        "Don't feel safe": "feel safe",
        "Don't feel successful": "feel successful",
        "Don't like school": "i like school",
        "No trusted adult": "adult.*talk",
        "No trusted peer": "student.*talk",
        "Teachers don't treat with respect": "teachers treat me with respect",
    },
    "Staff": {
        "Expectations not meaningful": "expectations meaningful",
        "Don't teach expectations": "taught.*expectations",
        "Not acknowledged by admin": "acknowledged by.*administrator",
        "Not acknowledged by peers": "acknowledged by other adults",
        "Don't use CARE language": "use the language",
    },
    "Parents and Family": {
        "Child doesn't feel safe": "feel safe",
        "Child doesn't feel successful": "feel.?successful",
        "Rules not enforced fairly": "consistently enforced|treated fairly",
        "Poor communication": "communicate well",
        "Teachers lack respect": "treat.*with respect",
    },
}


def get_at_risk_indicators(df, survey_type=None):
    """Identify respondents showing concerning patterns on key questions."""
    indicators = {}
    likert_cols = get_likert_columns(df)
    yes_no_cols = get_yes_no_columns(df)
    all_cols = likert_cols + yes_no_cols

    # Pick patterns based on survey type, fall back to trying all
    if survey_type and survey_type in AT_RISK_PATTERNS:
        patterns = AT_RISK_PATTERNS[survey_type]
    else:
        patterns = AT_RISK_PATTERNS.get("Student", {})

    for label, pattern in patterns.items():
        matched_col = None
        for col in all_cols:
            if re.search(pattern, col, re.IGNORECASE):
                matched_col = col
                break
        if matched_col:
            # Check for negative responses (Strongly disagree for Likert, No for Yes/No)
            if matched_col in likert_cols:
                count = (df[matched_col] == "Strongly disagree").sum()
            else:
                count = (df[matched_col] == "No").sum()
            total = df[matched_col].notna().sum()
            indicators[label] = {"count": int(count), "total": int(total)}

    return indicators


def analyze_open_response_sentiment(df):
    """Analyze open-ended responses for positive/negative sentiment and concerns."""
    open_cols = get_open_response_columns(df)
    results = []

    for col in open_cols:
        responses = df[col].dropna().astype(str)
        responses = responses[responses.str.len() > 2]

        for idx, text in responses.items():
            words = set(text.lower().split())
            pos_count = len(words & POSITIVE_WORDS)
            neg_count = len(words & NEGATIVE_WORDS)
            concern_matches = words & CONCERN_KEYWORDS

            if pos_count > neg_count:
                sentiment = "positive"
            elif neg_count > pos_count:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            results.append({
                "index": idx,
                "question": normalize_column_name(col),
                "text": text,
                "sentiment": sentiment,
                "pos_words": pos_count,
                "neg_words": neg_count,
                "has_concern": len(concern_matches) > 0,
                "concern_words": list(concern_matches),
            })

    return pd.DataFrame(results) if results else pd.DataFrame()


def compute_group_comparison(df, question, response_value):
    """Compare how a subgroup (those who answered question=response_value)
    answered all other Likert questions vs. the rest of the students."""
    likert_cols = get_likert_columns(df)
    mask = df[question] == response_value
    group = df[mask]
    rest = df[~mask]

    comparison = []
    for col in likert_cols:
        if col == question:
            continue
        g_scores = group[col].map(LIKERT_MAP).dropna()
        r_scores = rest[col].map(LIKERT_MAP).dropna()
        if len(g_scores) > 0 and len(r_scores) > 0:
            diff = g_scores.mean() - r_scores.mean()
            comparison.append({
                "Question": normalize_column_name(col)[:60],
                "Group Avg": round(g_scores.mean(), 2),
                "Rest Avg": round(r_scores.mean(), 2),
                "Difference": round(diff, 2),
            })

    return pd.DataFrame(comparison).sort_values("Difference") if comparison else pd.DataFrame()


def generate_key_insights(df, audience="respondents"):
    """Auto-generate plain-English insight statements from the data."""
    insights = []
    likert_cols = get_likert_columns(df)

    # Find a key column to split on (safety, fairness, or first Likert)
    split_col = None
    for col in likert_cols:
        if any(kw in col.lower() for kw in ["feel safe", "treated fairly", "communicate well"]):
            split_col = col
            break

    if split_col:
        split_label = normalize_column_name(split_col)[:40]
        negative = df[df[split_col] == "Strongly disagree"]
        positive = df[df[split_col].isin(["Strongly agree", "Somewhat agree"])]

        for col in likert_cols:
            if col == split_col:
                continue
            neg_scores = negative[col].map(LIKERT_MAP).dropna()
            pos_scores = positive[col].map(LIKERT_MAP).dropna()
            if len(neg_scores) >= 3 and len(pos_scores) >= 3:
                diff = pos_scores.mean() - neg_scores.mean()
                if diff > 0.8:
                    q_short = normalize_column_name(col)[:50]
                    insights.append({
                        "text": f'{audience.capitalize()} who disagreed on "{split_label}" scored **{diff:.1f} points lower** on "{q_short}" compared to those who agreed.',
                        "severity": "high" if diff > 1.2 else "medium",
                    })

    # Grade/group-based insights
    if "_grade" in df.columns:
        scores = compute_student_scores(df)
        df_temp = df.copy()
        df_temp["_sentiment"] = scores
        valid = df_temp.dropna(subset=["_grade", "_sentiment"])
        grade_means = valid.groupby("_grade")["_sentiment"].mean()
        if len(grade_means) >= 2:
            best = grade_means.idxmax()
            worst = grade_means.idxmin()
            gap = grade_means[best] - grade_means[worst]
            if gap > 0.3:
                insights.append({
                    "text": f"**{best}** {audience} are the most positive overall (avg {grade_means[best]:.2f}/4), while **{worst}** are the least positive (avg {grade_means[worst]:.2f}/4) - a gap of {gap:.2f} points.",
                    "severity": "medium" if gap < 0.5 else "high",
                })

    return insights


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
