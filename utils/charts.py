import plotly.express as px
import plotly.graph_objects as go
import numpy as np
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


# --- New charts for Student Insights page ---

def sentiment_histogram(scores, title="Student Sentiment Distribution"):
    """Histogram of per-student sentiment scores with color zones."""
    fig = go.Figure()

    # Color zones: red (1-2), yellow (2-3), green (3-4)
    bins = np.linspace(1, 4, 31)
    counts, edges = np.histogram(scores.dropna(), bins=bins)

    colors = []
    for edge in edges[:-1]:
        mid = edge + (edges[1] - edges[0]) / 2
        if mid < 2.0:
            colors.append("#e74c3c")
        elif mid < 3.0:
            colors.append("#f5b041")
        else:
            colors.append("#2ecc71")

    fig.add_trace(go.Bar(
        x=[(edges[i] + edges[i + 1]) / 2 for i in range(len(counts))],
        y=counts,
        marker_color=colors,
        width=(edges[1] - edges[0]) * 0.9,
        hovertemplate="Score: %{x:.2f}<br>Students: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Average Sentiment Score (1 = very negative, 4 = very positive)",
        yaxis_title="Number of Students",
        xaxis=dict(range=[0.8, 4.2]),
        height=400,
        shapes=[
            dict(type="rect", x0=1, x1=2, y0=0, y1=max(counts) * 1.1,
                 fillcolor="rgba(231,76,60,0.08)", line_width=0, layer="below"),
            dict(type="rect", x0=2, x1=3, y0=0, y1=max(counts) * 1.1,
                 fillcolor="rgba(245,176,65,0.08)", line_width=0, layer="below"),
            dict(type="rect", x0=3, x1=4, y0=0, y1=max(counts) * 1.1,
                 fillcolor="rgba(46,204,113,0.08)", line_width=0, layer="below"),
        ],
        annotations=[
            dict(x=1.5, y=max(counts) * 1.05, text="Negative", showarrow=False,
                 font=dict(color="#e74c3c", size=11)),
            dict(x=2.5, y=max(counts) * 1.05, text="Mixed", showarrow=False,
                 font=dict(color="#f5b041", size=11)),
            dict(x=3.5, y=max(counts) * 1.05, text="Positive", showarrow=False,
                 font=dict(color="#2ecc71", size=11)),
        ],
    )
    return fig


def correlation_heatmap(corr_matrix, title="Question Correlation Map"):
    """Heatmap showing correlations between Likert questions."""
    labels = [name[:40] + "..." if len(name) > 40 else name for name in corr_matrix.columns]

    fig = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=labels,
        y=labels,
        colorscale="RdYlGn",
        zmin=-1, zmax=1,
        hovertemplate="%{y}<br>vs %{x}<br>Correlation: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        height=max(500, len(labels) * 30),
        width=max(600, len(labels) * 30),
        xaxis=dict(tickangle=-45, automargin=True),
        yaxis=dict(automargin=True),
    )
    return fig


def group_comparison_chart(comparison_df, group_label, title="Group Comparison"):
    """Side-by-side bar chart comparing a subgroup vs rest of school."""
    if comparison_df.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=comparison_df["Question"],
        x=comparison_df["Group Avg"],
        name=group_label,
        orientation="h",
        marker_color="#e74c3c",
    ))
    fig.add_trace(go.Bar(
        y=comparison_df["Question"],
        x=comparison_df["Rest Avg"],
        name="Everyone Else",
        orientation="h",
        marker_color="#3498db",
    ))
    fig.update_layout(
        barmode="group",
        title=title,
        xaxis_title="Average Score (1-4)",
        xaxis=dict(range=[0, 4.5]),
        yaxis=dict(automargin=True),
        height=max(400, len(comparison_df) * 40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


def sentiment_by_grade_chart(df, scores, title="Sentiment by Grade"):
    """Box plot showing sentiment score distribution per grade."""
    if "_grade" not in df.columns:
        return None

    plot_df = pd.DataFrame({"Grade": df["_grade"], "Sentiment Score": scores}).dropna()
    plot_df = plot_df.sort_values("Grade")

    fig = px.box(
        plot_df,
        x="Grade",
        y="Sentiment Score",
        color="Grade",
        title=title,
        points="outliers",
    )
    fig.update_layout(yaxis_range=[0.5, 4.5], showlegend=False, height=400)
    return fig
