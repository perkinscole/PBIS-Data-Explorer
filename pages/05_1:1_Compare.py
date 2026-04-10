import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    normalize_column_name, match_category, LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.theme import apply_theme, get_survey_type_filter, end_control_panel, get_filter_container, filter_surveys_by_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Compare Surveys")
st.markdown(
    "Pick two surveys and see a clear before-and-after comparison. "
    "Great for presentations and quick check-ins."
)

# Load data
if not st.session_state.get("surveys"):
    if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
        all_data, all_meta = load_all_surveys(str(DATA_DIR))
        st.session_state.surveys = all_data
        st.session_state.survey_meta = all_meta
    else:
        st.warning("No data loaded. Go to the Upload page first.")
        st.stop()

with get_filter_container():
    selected_type = get_survey_type_filter()
    surveys, meta = filter_surveys_by_type(
        st.session_state.surveys, st.session_state.survey_meta, selected_type
    )

    if len(surveys) < 2:
        st.info("Need at least 2 surveys to compare. Upload more data or change the type filter.")
        st.stop()

    survey_labels = [m["label"] for m in meta]
    col1, col2 = st.columns(2)
    with col1:
        idx_a = st.selectbox("Survey A (Before)", range(len(survey_labels)),
                             format_func=lambda i: survey_labels[i], index=0)
    with col2:
        default_b = min(1, len(survey_labels) - 1)
        idx_b = st.selectbox("Survey B (After)", range(len(survey_labels)),
                             format_func=lambda i: survey_labels[i], index=default_b)

if idx_a == idx_b:
    st.warning("Please select two different surveys to compare.")
    st.stop()

df_a, df_b = surveys[idx_a], surveys[idx_b]
label_a, label_b = meta[idx_a]["label"], meta[idx_b]["label"]


def compute_pct_positive(df):
    """Compute % agree/strongly agree for each Likert question and % Yes for Yes/No."""
    results = {}
    for col in get_likert_columns(df):
        valid = df[col].dropna()
        if len(valid) > 0:
            pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
            results[normalize_column_name(col)] = {
                "pct": round(pos / len(valid) * 100, 1),
                "n": len(valid),
                "category": match_category(col) or "other",
            }
    for col in get_yes_no_columns(df):
        valid = df[col].dropna()
        if len(valid) > 0:
            pos = (valid == "Yes").sum()
            results[normalize_column_name(col)] = {
                "pct": round(pos / len(valid) * 100, 1),
                "n": len(valid),
                "category": match_category(col) or "other",
            }
    return results


pcts_a = compute_pct_positive(df_a)
pcts_b = compute_pct_positive(df_b)

# Find shared questions
shared = sorted(set(pcts_a.keys()) & set(pcts_b.keys()))

if not shared:
    st.warning("No matching questions found between these two surveys.")
    st.stop()

# Build comparison data
rows = []
for q in shared:
    a_pct = pcts_a[q]["pct"]
    b_pct = pcts_b[q]["pct"]
    diff = round(b_pct - a_pct, 1)
    rows.append({
        "Question": q[:65],
        "Before": a_pct,
        "After": b_pct,
        "Change": diff,
        "Category": pcts_a[q]["category"],
    })

comp_df = pd.DataFrame(rows).sort_values("Change", ascending=True)

# ============================================================
# Summary
# ============================================================
st.markdown("---")

improved = len(comp_df[comp_df["Change"] > 2])
declined = len(comp_df[comp_df["Change"] < -2])
stable = len(comp_df) - improved - declined

cols = st.columns(4)
cols[0].metric("Questions Compared", len(comp_df))
cols[1].metric("Improved", improved, help="More than 2% increase")
cols[2].metric("Declined", declined, help="More than 2% decrease")
cols[3].metric("Stable", stable, help="Within 2%")

avg_change = comp_df["Change"].mean()
if avg_change > 2:
    st.success(f"Overall: **{avg_change:+.1f}% average improvement** from {label_a} to {label_b}")
elif avg_change < -2:
    st.error(f"Overall: **{avg_change:+.1f}% average decline** from {label_a} to {label_b}")
else:
    st.info(f"Overall: **{avg_change:+.1f}% average change** from {label_a} to {label_b}")

# ============================================================
# Difference chart
# ============================================================
st.markdown("---")
st.markdown("### Question-by-Question Changes")

fig = go.Figure()
colors = ["#27ae60" if c > 2 else "#e74c3c" if c < -2 else "#95a5a6" for c in comp_df["Change"]]

fig.add_trace(go.Bar(
    y=comp_df["Question"],
    x=comp_df["Change"],
    orientation="h",
    marker_color=colors,
    text=[f"{c:+.1f}%" for c in comp_df["Change"]],
    textposition="outside",
))
fig.add_vline(x=0, line_color="#1a1a1a", line_width=2)
fig.update_layout(
    title=f"Change: {label_a} → {label_b}",
    xaxis_title="Change in % Positive",
    yaxis=dict(automargin=True),
    height=max(400, len(comp_df) * 35),
    margin=dict(l=20),
)
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# Side-by-side cards
# ============================================================
st.markdown("---")
st.markdown("### Detailed Comparison")

for _, row in comp_df.iterrows():
    diff = row["Change"]
    if diff > 2:
        arrow = "up"
        color = "#27ae60"
        bg = "#d5f5e3"
    elif diff < -2:
        arrow = "down"
        color = "#e74c3c"
        bg = "#fadbd8"
    else:
        arrow = "same"
        color = "#95a5a6"
        bg = "#f2f3f4"

    arrow_html = {
        "up": f'<span style="color:{color}; font-size:1.3em;">&#9650;</span>',
        "down": f'<span style="color:{color}; font-size:1.3em;">&#9660;</span>',
        "same": f'<span style="color:{color}; font-size:1.3em;">&#9654;</span>',
    }[arrow]

    st.markdown(
        f'<div style="background-color:{bg}; border-left: 4px solid {color}; '
        f'padding: 10px 16px; border-radius: 6px; margin-bottom: 8px; '
        f'display: flex; align-items: center; justify-content: space-between;">'
        f'<div style="flex: 3;"><strong>{row["Question"]}</strong></div>'
        f'<div style="flex: 1; text-align: center;">{row["Before"]:.0f}%</div>'
        f'<div style="flex: 0.5; text-align: center;">{arrow_html}</div>'
        f'<div style="flex: 1; text-align: center; font-weight: bold;">{row["After"]:.0f}%</div>'
        f'<div style="flex: 1; text-align: right; color: {color}; font-weight: bold;">{diff:+.1f}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ============================================================
# Category summary
# ============================================================
st.markdown("---")
st.markdown("### By PBIS Category")

cat_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}
cat_changes = comp_df.groupby("Category")["Change"].mean().to_dict()

cat_rows = []
for cat, change in sorted(cat_changes.items(), key=lambda x: x[1]):
    label = cat_labels.get(cat, cat.replace("_", " ").title())
    cat_rows.append({
        "Category": label,
        "Avg Change": f"{change:+.1f}%",
        "Direction": "Improved" if change > 2 else "Declined" if change < -2 else "Stable",
    })

if cat_rows:
    cat_summary = pd.DataFrame(cat_rows)

    def color_direction(val):
        if val == "Improved":
            return "background-color: #d5f5e3"
        elif val == "Declined":
            return "background-color: #fadbd8"
        return ""

    st.dataframe(
        cat_summary.style.map(color_direction, subset=["Direction"]),
        use_container_width=True,
        hide_index=True,
    )
