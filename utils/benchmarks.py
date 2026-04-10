import json
import re
from pathlib import Path
from utils.data_loader import get_likert_columns, get_yes_no_columns, normalize_column_name

# 2023 MWAHS Regional Benchmarks (Middle School, Grades 7-8)
# Source: 2023 MetroWest Adolescent Health Survey Regional Highlights Report
# and School Connectedness Infographic
# n = 11,352 students across 30 middle schools in 24 districts
DEFAULT_BENCHMARKS = {
    "source": "2023 MetroWest Adolescent Health Survey (MWAHS)",
    "year": 2023,
    "sample_size": 11352,
    "description": "Regional benchmarks from 25 MetroWest communities (Grades 7-8)",
    "indicators": {
        "School Belonging": {
            "mwahs_question": "I feel like I am part of this school",
            "mwahs_pct": 64,
            "mwahs_trend": {"2006": 71, "2008": 70, "2010": 69, "2012": 68, "2014": 67, "2016": 67, "2018": 65, "2021": 64, "2023": 64},
        },
        "Peer Closeness": {
            "mwahs_question": "I feel close to people at this school",
            "mwahs_pct": 65,
            "mwahs_trend": {},
        },
        "Happy at School": {
            "mwahs_question": "I am happy to be at this school",
            "mwahs_pct": 55,
            "mwahs_trend": {"2021": 58, "2023": 55},
        },
        "Teacher Fairness": {
            "mwahs_question": "The teachers at this school treat students fairly",
            "mwahs_pct": 56,
            "mwahs_trend": {"2021": 62, "2023": 56},
        },
        "School Safety": {
            "mwahs_question": "I feel safe in my school",
            "mwahs_pct": 70,
            "mwahs_trend": {"2021": 73, "2023": 70},
        },
        "Adult Support at School": {
            "mwahs_question": "Have an adult at school to talk to about a problem",
            "mwahs_pct": 69,
            "mwahs_trend": {"2006": 68, "2008": 69, "2010": 69, "2012": 70, "2014": 71, "2016": 72, "2018": 72, "2021": 66, "2023": 69},
        },
    },
}

# Map MWAHS indicators to RAMS CARE survey question patterns
# Each indicator maps to a list of substrings to search for in column names
BENCHMARK_QUESTION_MAP = {
    "School Belonging": [
        "feel like i fit in",
        "feel connected to others",
        "feel like i am part",
        "part of this school",
    ],
    "Peer Closeness": [
        "feel connected to others",
        "feel close to people",
        "welcoming to new students",
    ],
    "Happy at School": [
        "i like school",
        "look forward to going to school",
        "happy to be at",
    ],
    "Teacher Fairness": [
        "teachers treat me with respect",
        "teachers treat all students fairly",
        "adults in this school treat all students",
        "treat students fairly",
    ],
    "School Safety": [
        "feel safe",
    ],
    "Adult Support at School": [
        "adult.*talk",
        "adult at rams that i can talk",
        "adult support",
    ],
}


def compute_rams_percentages(df):
    """Convert RAMS Likert/Yes-No responses to % positive for benchmark comparison.
    For Likert: % who answered 'Strongly agree' or 'Somewhat agree'
    For Yes/No: % who answered 'Yes'
    Returns dict: {indicator_name: {'pct': float, 'question': str, 'n': int}}
    """
    likert_cols = get_likert_columns(df)
    yes_no_cols = get_yes_no_columns(df)
    all_cols = likert_cols + yes_no_cols

    results = {}
    for indicator, patterns in BENCHMARK_QUESTION_MAP.items():
        matched_col = None
        for col in all_cols:
            col_lower = col.lower()
            for pattern in patterns:
                if re.search(pattern, col_lower):
                    matched_col = col
                    break
            if matched_col:
                break

        if matched_col:
            valid = df[matched_col].dropna()
            n = len(valid)
            if n > 0:
                if matched_col in likert_cols:
                    positive = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
                else:
                    positive = (valid == "Yes").sum()
                pct = positive / n * 100
                results[indicator] = {
                    "pct": round(pct, 1),
                    "question": normalize_column_name(matched_col),
                    "n": n,
                }

    return results


def load_benchmarks(data_dir):
    """Load custom benchmarks from JSON if available, otherwise return defaults."""
    benchmarks_file = Path(data_dir) / "_benchmarks.json"
    if benchmarks_file.exists():
        try:
            custom = json.loads(benchmarks_file.read_text())
            # Merge: custom overrides default, but keep any indicators not in custom
            merged = DEFAULT_BENCHMARKS.copy()
            merged.update(custom)
            if "indicators" in custom:
                merged_indicators = DEFAULT_BENCHMARKS["indicators"].copy()
                merged_indicators.update(custom["indicators"])
                merged["indicators"] = merged_indicators
            return merged
        except Exception:
            pass
    return DEFAULT_BENCHMARKS


def save_benchmarks(data_dir, benchmarks):
    """Save benchmark data to JSON."""
    benchmarks_file = Path(data_dir) / "_benchmarks.json"
    Path(data_dir).mkdir(exist_ok=True)
    benchmarks_file.write_text(json.dumps(benchmarks, indent=2))


def parse_mwahs_pdf(filepath):
    """Extract benchmark percentages from a MWAHS report PDF.
    Returns a dict of parsed indicators or None if parsing fails."""
    try:
        import fitz
    except ImportError:
        return None

    doc = fitz.open(filepath)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()

    # Search patterns for key indicators with their percentages
    parse_patterns = {
        "School Belonging": [
            r"(?:feel like I am part of this school|feel like part of this school)[^\d]*?(\d{1,2})%",
            r"(\d{1,2})%\s*(?:feel like I am part|Feel like part of this school)",
        ],
        "Peer Closeness": [
            r"(?:feel close to people at (?:this )?school)[^\d]*?(\d{1,2})%",
            r"(\d{1,2})%\s*(?:Feel close to people at (?:this )?school)",
        ],
        "Happy at School": [
            r"(?:happy to be at (?:this|their) school)[^\d]*?(\d{1,2})%",
            r"(\d{1,2})%\s*(?:(?:Are |I am )?happy to be at (?:this|their) school)",
        ],
        "Teacher Fairness": [
            r"(?:teachers?\s+(?:at this school\s+)?treat students fairly)[^\d]*?(\d{1,2})%",
            r"(\d{1,2})%\s*(?:Feel teachers? treat students fairly)",
        ],
        "School Safety": [
            r"(?:feel safe in (?:their|my) school)[^\d]*?(\d{1,2})%",
            r"(\d{1,2})%\s*(?:Feel safe in (?:their|my) school)",
        ],
        "Adult Support at School": [
            r"(?:adult (?:at school )?(?:support|to talk))[^\d]*?(\d{1,2})%",
            r"adult support at school[^\d]*?(\d{1,2})%",
            r"(\d{1,2})%.*adult support at school",
        ],
    }

    parsed = {}
    for indicator, patterns in parse_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                pct = int(match.group(1))
                if 10 <= pct <= 100:  # sanity check
                    parsed[indicator] = pct
                    break

    if not parsed:
        return None

    # Try to extract year
    year_match = re.search(r"(20\d{2})\s+MetroWest Adolescent Health Survey", full_text)
    year = int(year_match.group(1)) if year_match else None

    # Try to extract sample size
    sample_match = re.search(r"([\d,]+)\s+students?\s+in\s+grades?\s+(?:6|7)", full_text)
    sample_size = int(sample_match.group(1).replace(",", "")) if sample_match else None

    return {
        "source": f"{year or 'Unknown'} MetroWest Adolescent Health Survey (MWAHS)",
        "year": year,
        "sample_size": sample_size,
        "description": f"Parsed from uploaded MWAHS report",
        "indicators": {
            indicator: {
                "mwahs_question": DEFAULT_BENCHMARKS["indicators"].get(indicator, {}).get("mwahs_question", indicator),
                "mwahs_pct": pct,
                "mwahs_trend": {},
            }
            for indicator, pct in parsed.items()
        },
    }
