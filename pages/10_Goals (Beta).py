import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    compute_agreement_score, normalize_column_name, match_category,
    sort_periods, LIKERT_MAP, QUESTION_CATEGORIES,
)
from utils.goals import load_goals, save_goals, compute_goal_progress
from utils.theme import apply_theme, get_survey_type_filter, end_control_panel, filter_surveys_by_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Goal Tracking")
st.markdown(
    "Set targets for PBIS indicators and track your progress over time. "
    "Goals are color-coded so you can quickly see what's on track."
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

selected_type = get_survey_type_filter()
surveys, meta = filter_surveys_by_type(
    st.session_state.surveys, st.session_state.survey_meta, selected_type
)
end_control_panel()

if not surveys:
    st.info(f"No {selected_type} surveys loaded. Upload data or change the type filter.")
    st.stop()

# Build % positive by period for each category and question
category_labels = {c: c.replace("_", " ").title() for c in QUESTION_CATEGORIES}
pcts_by_period = {}
available_indicators = set()

for df, m in zip(surveys, meta):
    period = m["period"]
    likert_cols = get_likert_columns(df)
    yes_no_cols = get_yes_no_columns(df)

    period_pcts = {}

    # Category-level percentages
    cat_vals = {}
    for col in likert_cols:
        cat = match_category(col)
        valid = df[col].dropna()
        n = len(valid)
        if n > 0:
            positive = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
            pct = positive / n * 100
            # Store question-level
            q_name = normalize_column_name(col)[:60]
            period_pcts[q_name] = round(pct, 1)
            available_indicators.add(q_name)
            if cat:
                cat_vals.setdefault(cat, []).append(pct)

    for col in yes_no_cols:
        cat = match_category(col)
        valid = df[col].dropna()
        n = len(valid)
        if n > 0:
            positive = (valid == "Yes").sum()
            pct = positive / n * 100
            q_name = normalize_column_name(col)[:60]
            period_pcts[q_name] = round(pct, 1)
            available_indicators.add(q_name)
            if cat:
                cat_vals.setdefault(cat, []).append(pct)

    for cat, vals in cat_vals.items():
        label = category_labels[cat]
        period_pcts[label] = round(sum(vals) / len(vals), 1)
        available_indicators.add(label)

    pcts_by_period[period] = period_pcts

sorted_periods_list = sort_periods(list(pcts_by_period.keys()))

# Load goals
goals = load_goals(str(DATA_DIR))

# Compute progress for each goal
goal_results = []
for goal in goals:
    progress = compute_goal_progress(goal, pcts_by_period)
    goal_results.append((goal, progress))

# ============================================================
# Summary cards
# ============================================================
if goal_results:
    achieved = sum(1 for _, p in goal_results if p["status"] == "achieved")
    close = sum(1 for _, p in goal_results if p["status"] == "close")
    behind = sum(1 for _, p in goal_results if p["status"] == "behind")
    no_data = sum(1 for _, p in goal_results if p["status"] == "no_data")

    cols = st.columns(4)
    cols[0].metric("Achieved", achieved, help="Met or exceeded target")
    cols[1].metric("Almost There", close, help="Within 5% of target")
    cols[2].metric("Needs Work", behind, help="More than 5% below target")
    if no_data:
        cols[3].metric("No Data", no_data, help="No matching survey data found")

st.markdown("---")

# ============================================================
# Goal cards
# ============================================================
if goal_results:
    for i, (goal, progress) in enumerate(goal_results):
        status = progress["status"]
        current = progress["current_pct"]
        target = progress["target_pct"]
        gap = progress["gap"]

        if status == "achieved":
            color, bg, icon = "#27ae60", "#d5f5e3", "Achieved"
        elif status == "close":
            color, bg, icon = "#f39c12", "#fef9e7", "Almost There"
        elif status == "behind":
            color, bg, icon = "#e74c3c", "#fadbd8", "Needs Work"
        else:
            color, bg, icon = "#95a5a6", "#f2f3f4", "No Data"

        with st.container():
            st.markdown(
                f'<div style="background-color:{bg}; border-left: 5px solid {color}; '
                f'padding: 14px 18px; border-radius: 6px; margin-bottom: 14px;">'
                f'<strong style="font-size: 1.1em;">{goal["indicator"]}</strong> '
                f'<span style="color:{color}; font-weight:bold; float:right;">{icon}</span><br>'
                f'<small>{goal.get("description", "")}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                if current is not None:
                    st.metric("Current", f"{current:.0f}%")
                else:
                    st.metric("Current", "—")
            with col2:
                st.metric("Target", f"{target:.0f}%")
            with col3:
                if gap is not None:
                    st.metric("Gap", f"{gap:+.1f}%", delta_color="normal")
                else:
                    st.metric("Gap", "—")
            with col4:
                if st.button("Delete", key=f"del_goal_{i}", type="secondary"):
                    goals.pop(i)
                    save_goals(str(DATA_DIR), goals)
                    st.rerun()

            # Sparkline trend
            if len(progress["history"]) > 1:
                hist_df = pd.DataFrame(progress["history"])
                hist_df["period"] = pd.Categorical(
                    hist_df["period"],
                    categories=[p for p in sorted_periods_list if p in hist_df["period"].values],
                    ordered=True,
                )
                hist_df = hist_df.sort_values("period")

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_df["period"].astype(str),
                    y=hist_df["pct"],
                    mode="lines+markers",
                    line=dict(color=color, width=2),
                    marker=dict(size=8),
                ))
                fig.add_hline(y=target, line_dash="dash", line_color="#95a5a6",
                              annotation_text=f"Target: {target}%")
                fig.update_layout(
                    height=200, margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="", yaxis_title="% Positive",
                    yaxis=dict(range=[0, 105]),
                )
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No goals set yet. Add your first goal below!")

# ============================================================
# Add new goal
# ============================================================
st.markdown("---")
st.markdown("## Add a Goal")

sorted_indicators = sorted(available_indicators)
category_options = sorted([category_labels[c] for c in QUESTION_CATEGORIES])
all_options = category_options + ["---"] + [q for q in sorted_indicators if q not in category_options]

with st.form("add_goal"):
    col1, col2 = st.columns([3, 1])
    with col1:
        indicator = st.selectbox(
            "What do you want to track?",
            all_options,
            help="Pick a PBIS category (broader) or a specific survey question",
        )
    with col2:
        target_pct = st.number_input("Target %", min_value=10, max_value=100, value=80)

    description = st.text_input(
        "Description (optional)",
        placeholder="e.g., 80% of students feel safe by June 2026",
    )

    submitted = st.form_submit_button("Add Goal", type="primary")
    if submitted and indicator != "---":
        new_goal = {
            "indicator": indicator,
            "target_pct": target_pct,
            "description": description,
        }
        goals.append(new_goal)
        save_goals(str(DATA_DIR), goals)
        st.success(f"Goal added: {indicator} → {target_pct}%")
        st.rerun()
