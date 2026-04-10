import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    match_category, LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.theme import apply_theme
from utils.theme import _infer_survey_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Perception Gaps")
st.markdown(
    "Compare how **students, staff, and families** see the same PBIS topics differently. "
    "Gaps reveal where conversations need to happen."
)

if not st.session_state.get("surveys"):
    if DATA_DIR.exists() and list(DATA_DIR.glob("*.xlsx")):
        all_data, all_meta = load_all_surveys(str(DATA_DIR))
        st.session_state.surveys = all_data
        st.session_state.survey_meta = all_meta
    else:
        st.warning("No data loaded. Go to the Upload page first.")
        st.stop()

# Group surveys by type
type_groups = {}
for df, m in zip(st.session_state.surveys, st.session_state.survey_meta):
    stype = _infer_survey_type(m)
    if stype:
        type_groups.setdefault(stype, []).append((df, m))

available_types = sorted(type_groups.keys())

if len(available_types) < 2:
    st.info(
        f"Currently loaded: **{', '.join(available_types) if available_types else 'none'}**. "
        "Upload surveys from at least **2 different groups** (e.g., Student and Staff) "
        "to see perception gaps."
    )
    st.stop()

st.success(f"Comparing: **{' vs '.join(available_types)}**")

cat_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}

# Compute category-level % positive for each type
type_cat_pcts = {}
for stype, survey_list in type_groups.items():
    cat_vals = {}
    for df, m in survey_list:
        likert_cols = get_likert_columns(df)
        yn_cols = get_yes_no_columns(df)
        for col in likert_cols:
            cat = match_category(col)
            if cat:
                valid = df[col].dropna()
                if len(valid) > 0:
                    pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
                    cat_vals.setdefault(cat, []).append(pos / len(valid) * 100)
        for col in yn_cols:
            cat = match_category(col)
            if cat:
                valid = df[col].dropna()
                if len(valid) > 0:
                    pos = (valid == "Yes").sum()
                    cat_vals.setdefault(cat, []).append(pos / len(valid) * 100)
    type_cat_pcts[stype] = {cat: round(sum(v)/len(v), 1) for cat, v in cat_vals.items()}

# Find shared categories
all_cat_sets = [set(pcts.keys()) for pcts in type_cat_pcts.values()]
shared_cats = all_cat_sets[0]
for cs in all_cat_sets[1:]:
    shared_cats = shared_cats & cs

if not shared_cats:
    st.warning("No shared PBIS categories found across survey types.")
    st.stop()

# Build comparison data
rows = []
for cat in sorted(shared_cats):
    row = {"Category": cat_labels.get(cat, cat)}
    pcts = []
    for stype in available_types:
        val = type_cat_pcts[stype].get(cat, 0)
        row[stype] = val
        pcts.append(val)
    row["Gap"] = round(max(pcts) - min(pcts), 1)
    rows.append(row)

gap_df = pd.DataFrame(rows).sort_values("Gap", ascending=False)

# Diverging bar chart
st.markdown("---")
st.markdown("### Category Comparison")

TYPE_COLORS = {
    "Student": "#8b1a1a",
    "Staff": "#3498db",
    "Parents and Family": "#27ae60",
}

fig = go.Figure()
for stype in available_types:
    fig.add_trace(go.Bar(
        y=gap_df["Category"],
        x=gap_df[stype],
        name=stype,
        orientation="h",
        marker_color=TYPE_COLORS.get(stype, "#95a5a6"),
        text=[f"{v:.0f}%" for v in gap_df[stype]],
        textposition="auto",
    ))

fig.update_layout(
    barmode="group",
    title="% Positive by Group and PBIS Category",
    xaxis=dict(range=[0, 105], title="% Positive"),
    yaxis=dict(automargin=True),
    height=max(400, len(gap_df) * 60),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
)
st.plotly_chart(fig, use_container_width=True)

# Gap analysis
st.markdown("---")
st.markdown("### Biggest Perception Gaps")

for _, row in gap_df.iterrows():
    if row["Gap"] < 5:
        continue
    pct_vals = {stype: row[stype] for stype in available_types}
    highest = max(pct_vals, key=pct_vals.get)
    lowest = min(pct_vals, key=pct_vals.get)
    gap = row["Gap"]

    if gap >= 15:
        color, bg = "#e74c3c", "#fadbd8"
    elif gap >= 10:
        color, bg = "#f39c12", "#fef9e7"
    else:
        color, bg = "#3498db", "#ebf5fb"

    # Generate insight
    cat_lower = row["Category"].lower()
    insights = {
        "teacher respect": f"**{highest}** rate teacher respect much higher than **{lowest}**. This may indicate different experiences or expectations around how respect is shown.",
        "behavior support": f"**{highest}** view the behavior support system more positively than **{lowest}**. Consider whether the system is working equally well for all groups.",
        "safety": f"**{highest}** feel safer than **{lowest}**. Explore what specific safety concerns exist for the lower-scoring group.",
        "school belonging": f"**{highest}** feel more connected to RAMS than **{lowest}**. Look into what's driving the disconnect.",
        "care values": f"**{highest}** see the CARE values as more meaningful than **{lowest}**. The values may need to be communicated differently to each group.",
        "school environment": f"**{highest}** are more positive about the school environment than **{lowest}**. Consider what each group experiences differently.",
    }
    insight = insights.get(cat_lower,
        f"**{highest}** rate this area higher than **{lowest}**. This gap suggests different experiences worth exploring.")

    st.markdown(
        f'<div style="background-color:{bg}; border-left:5px solid {color}; '
        f'padding:14px 18px; border-radius:6px; margin-bottom:12px;">'
        f'<strong>{row["Category"]}</strong> — '
        f'Gap of <strong>{gap:.0f}%</strong><br>'
        f'{highest}: {pct_vals[highest]:.0f}% &nbsp;|&nbsp; '
        f'{lowest}: {pct_vals[lowest]:.0f}%<br><br>'
        f'<em>{insight}</em>'
        f'</div>',
        unsafe_allow_html=True,
    )

# Areas of agreement
st.markdown("---")
st.markdown("### Areas of Agreement")
st.markdown("Categories where all groups see things similarly (gap < 5%).")

aligned = gap_df[gap_df["Gap"] < 5]
if len(aligned) > 0:
    for _, row in aligned.iterrows():
        avg = sum(row[stype] for stype in available_types) / len(available_types)
        st.markdown(f"- **{row['Category']}** — all groups around {avg:.0f}% positive")
else:
    st.info("No categories with strong alignment across groups. There are perception gaps in every area.")

# Summary table
st.markdown("---")
st.markdown("### Full Comparison Table")
display_df = gap_df.copy()
for stype in available_types:
    display_df[stype] = display_df[stype].apply(lambda x: f"{x:.0f}%")
display_df["Gap"] = display_df["Gap"].apply(lambda x: f"{x:.0f}%")
st.dataframe(display_df, use_container_width=True, hide_index=True)
