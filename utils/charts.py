import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.data_loader import LIKERT_MAP, normalize_column_name

LIKERT_COLORS = {
    "Strongly agree": "#2ecc71",
    "Somewhat agree": "#82e0aa",
    "Somewhat disagree": "#f5b041",
    "Strongly disagree": "#e74c3c",
}

LIKERT_ORDER = ["Strongly disagree", "Somewhat disagree", "Somewhat agree", "Strongly agree"]


def likert_heatmap(summary_df, title="Response Distribution"):
    """Create a diverging stacked bar chart for Likert responses."""
    pivot = summary_df.pivot_table(
        index="Question", columns="Response", values="Percentage", fill_value=0
    )
    for col in LIKERT_ORDER:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[LIKERT_ORDER]

    # Sort by agreement rate (SA + A)
    pivot["_agree"] = pivot["Strongly agree"] + pivot["Somewhat agree"]
    pivot = pivot.sort_values("_agree", ascending=True)
    pivot = pivot.drop("_agree", axis=1)

    # Shorten question labels
    labels = [q[:80] + "..." if len(q) > 80 else q for q in pivot.index]

    fig = go.Figure()
    for response in LIKERT_ORDER:
        fig.add_trace(go.Bar(
            y=labels,
            x=pivot[response],
            name=response,
            orientation="h",
            marker_color=LIKERT_COLORS[response],
            hovertemplate="%{y}<br>%{x:.1f}%<extra>" + response + "</extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title=title,
        xaxis_title="Percentage",
        yaxis=dict(automargin=True),
        height=max(400, len(pivot) * 35),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=20),
    )
    return fig


def grade_comparison_chart(df, question, title=None):
    """Bar chart comparing a single question's responses by grade."""
    if "_grade" not in df.columns:
        return None

    grade_data = df[["_grade", question]].dropna()
    grade_data["score"] = grade_data[question].map(LIKERT_MAP)
    avg_by_grade = grade_data.groupby("_grade")["score"].mean().reset_index()
    avg_by_grade.columns = ["Grade", "Average Score"]
    avg_by_grade = avg_by_grade.sort_values("Grade")

    fig = px.bar(
        avg_by_grade,
        x="Grade",
        y="Average Score",
        title=title or normalize_column_name(question),
        color="Average Score",
        color_continuous_scale=["#e74c3c", "#f9e79f", "#2ecc71"],
        range_color=[1, 5],
    )
    fig.update_layout(yaxis_range=[0, 5.5])
    return fig


def trend_line_chart(trend_data, title="Agreement Scores Over Time"):
    """Line chart showing how scores change across survey periods."""
    fig = px.line(
        trend_data,
        x="Period",
        y="Score",
        color="Question",
        markers=True,
        title=title,
    )
    fig.update_layout(
        yaxis_range=[1, 5],
        yaxis_title="Average Agreement (1-5)",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=-0.4),
    )
    return fig


def response_count_chart(meta_list):
    """Bar chart of response counts per survey."""
    data = pd.DataFrame(meta_list)
    fig = px.bar(
        data,
        x="label",
        y="count",
        title="Response Counts by Survey",
        color="count",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis_title="Survey", yaxis_title="Responses")
    return fig


def yes_no_chart(df, columns, title="Yes/No Responses"):
    """Grouped bar chart for Yes/No questions."""
    rows = []
    for col in columns:
        counts = df[col].value_counts(normalize=True) * 100
        for response in ["Yes", "No"]:
            rows.append({
                "Question": normalize_column_name(col)[:60],
                "Response": response,
                "Percentage": counts.get(response, 0),
            })

    chart_df = pd.DataFrame(rows)
    fig = px.bar(
        chart_df,
        x="Percentage",
        y="Question",
        color="Response",
        orientation="h",
        barmode="group",
        title=title,
        color_discrete_map={"Yes": "#2ecc71", "No": "#e74c3c"},
    )
    fig.update_layout(
        height=max(300, len(columns) * 50),
        yaxis=dict(automargin=True),
    )
    return fig


def category_radar_chart(scores_dict, title="CARE Category Scores"):
    """Radar chart showing average scores by question category."""
    cat_scores = {}
    for q, info in scores_dict.items():
        cat = info["category"]
        if cat != "other":
            cat_scores.setdefault(cat, []).append(info["mean"])

    categories = []
    values = []
    for cat, s in sorted(cat_scores.items()):
        categories.append(cat.replace("_", " ").title())
        values.append(sum(s) / len(s))

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(46, 204, 113, 0.3)",
        line_color="#2ecc71",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[1, 5])),
        title=title,
        height=500,
    )
    return fig
