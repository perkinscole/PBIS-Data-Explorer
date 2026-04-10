import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.data_loader import (
    load_all_surveys, get_likert_columns, get_yes_no_columns,
    get_open_response_columns, compute_likert_summary,
    compute_agreement_score, normalize_column_name, match_category,
    get_at_risk_indicators, generate_key_insights, LIKERT_MAP,
    QUESTION_CATEGORIES,
)
from utils.benchmarks import compute_rams_percentages, load_benchmarks
from utils.theme import apply_theme, get_survey_type_filter, end_control_panel, get_filter_container, filter_surveys_by_type, get_audience_label

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Report Generator")
st.markdown(
    "Generate a printable summary report of your survey results. "
    "Download as HTML and open in your browser to print or save as PDF."
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
    audience = get_audience_label(selected_type)

    if not surveys:
        st.info(f"No {selected_type} surveys loaded. Upload data or change the type filter.")
        st.stop()

    survey_labels = [m["label"] for m in meta]
    selected_idx = st.selectbox(
        "Select survey for report",
        range(len(survey_labels)),
        format_func=lambda i: survey_labels[i],
    )
df = surveys[selected_idx]
info = meta[selected_idx]

# Section picker
st.markdown("### Report Sections")
st.markdown("Choose which sections to include:")

col1, col2 = st.columns(2)
with col1:
    inc_overview = st.checkbox("Overview & Response Count", value=True)
    inc_agreement = st.checkbox("Agreement Levels (all questions)", value=True)
    inc_categories = st.checkbox("CARE Category Scores", value=True)
    inc_grade = st.checkbox("Grade/Role Breakdown", value=True)
with col2:
    inc_benchmark = st.checkbox("Benchmark Comparison (MWAHS)", value=True)
    inc_atrisk = st.checkbox("At-Risk Indicators", value=True)
    inc_insights = st.checkbox("Key Insights", value=True)
    inc_open = st.checkbox("Open Response Highlights", value=True)

report_title = st.text_input("Report Title", value=f"RAMS CARE Survey Report: {info['label']}")

st.markdown("---")

if st.button("Generate Report", type="primary"):
    with st.spinner("Building report..."):
        likert_cols = get_likert_columns(df)
        yes_no_cols = get_yes_no_columns(df)
        open_cols = get_open_response_columns(df)

        # Build HTML report
        html_parts = []

        # Header and styles
        html_parts.append(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{report_title}</title>
<style>
    body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 30px; color: #1a1a1a; }}
    h1 {{ color: #8b1a1a; border-bottom: 3px solid #8b1a1a; padding-bottom: 10px; }}
    h2 {{ color: #8b1a1a; margin-top: 30px; }}
    h3 {{ color: #333; }}
    .header {{ text-align: center; margin-bottom: 30px; }}
    .header p {{ color: #666; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 15px 0; }}
    .metric {{ background: #fdf2f2; border: 1px solid #e8c4c4; border-radius: 8px; padding: 15px; text-align: center; }}
    .metric .value {{ font-size: 1.8em; font-weight: bold; color: #8b1a1a; }}
    .metric .label {{ font-size: 0.85em; color: #666; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    th {{ background: #8b1a1a; color: white; padding: 10px; text-align: left; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
    tr:nth-child(even) {{ background: #fdf2f2; }}
    .card {{ border-left: 4px solid; padding: 12px 16px; margin: 10px 0; border-radius: 4px; }}
    .card-green {{ border-color: #27ae60; background: #d5f5e3; }}
    .card-yellow {{ border-color: #f39c12; background: #fef9e7; }}
    .card-red {{ border-color: #e74c3c; background: #fadbd8; }}
    .bar-container {{ background: #eee; border-radius: 4px; height: 20px; margin: 3px 0; }}
    .bar {{ height: 20px; border-radius: 4px; text-align: right; padding-right: 6px; color: white; font-size: 0.8em; line-height: 20px; }}
    .footer {{ text-align: center; margin-top: 40px; color: #999; font-size: 0.85em; border-top: 1px solid #eee; padding-top: 15px; }}
    @media print {{ body {{ padding: 15px; }} }}
</style></head><body>""")

        # Title
        html_parts.append(f"""
<div class="header">
    <h1>{report_title}</h1>
    <p>Generated {datetime.now().strftime('%B %d, %Y')} | {len(df)} responses | RAMS CARE Data Viewer</p>
</div>""")

        # Overview
        if inc_overview:
            html_parts.append(f"""
<h2>Overview</h2>
<div class="metric-grid">
    <div class="metric"><div class="value">{len(df)}</div><div class="label">Total Responses</div></div>
    <div class="metric"><div class="value">{len(likert_cols)}</div><div class="label">Likert Questions</div></div>
    <div class="metric"><div class="value">{len(yes_no_cols)}</div><div class="label">Yes/No Questions</div></div>
    <div class="metric"><div class="value">{len(open_cols)}</div><div class="label">Open-Ended</div></div>
</div>""")

            if "_grade" in df.columns:
                grade_counts = df["_grade"].dropna().value_counts().sort_index()
                if len(grade_counts) > 0:
                    html_parts.append("<h3>Response Distribution</h3><div class='metric-grid'>")
                    for grade, count in grade_counts.items():
                        html_parts.append(f'<div class="metric"><div class="value">{count}</div><div class="label">{grade}</div></div>')
                    html_parts.append("</div>")

        # Agreement levels
        if inc_agreement and likert_cols:
            html_parts.append("<h2>Agreement Levels</h2>")
            html_parts.append("<table><tr><th>Question</th><th>% Positive</th><th></th></tr>")
            for col in likert_cols:
                valid = df[col].dropna()
                if len(valid) > 0:
                    pos = valid.isin(["Strongly agree", "Somewhat agree"]).sum()
                    pct = pos / len(valid) * 100
                    color = "#27ae60" if pct >= 75 else "#f39c12" if pct >= 50 else "#e74c3c"
                    html_parts.append(
                        f'<tr><td>{normalize_column_name(col)[:70]}</td>'
                        f'<td><strong>{pct:.0f}%</strong></td>'
                        f'<td><div class="bar-container"><div class="bar" style="width:{pct}%;background:{color};">{pct:.0f}%</div></div></td></tr>'
                    )
            html_parts.append("</table>")

        if inc_agreement and yes_no_cols:
            html_parts.append("<h3>Yes/No Questions</h3>")
            html_parts.append("<table><tr><th>Question</th><th>% Yes</th><th></th></tr>")
            for col in yes_no_cols:
                valid = df[col].dropna()
                if len(valid) > 0:
                    pos = (valid == "Yes").sum()
                    pct = pos / len(valid) * 100
                    color = "#27ae60" if pct >= 75 else "#f39c12" if pct >= 50 else "#e74c3c"
                    html_parts.append(
                        f'<tr><td>{normalize_column_name(col)[:70]}</td>'
                        f'<td><strong>{pct:.0f}%</strong></td>'
                        f'<td><div class="bar-container"><div class="bar" style="width:{pct}%;background:{color};">{pct:.0f}%</div></div></td></tr>'
                    )
            html_parts.append("</table>")

        # CARE Categories
        if inc_categories and likert_cols:
            html_parts.append("<h2>CARE Category Scores</h2>")
            cat_scores = {}
            for col in likert_cols:
                cat = match_category(col)
                if cat:
                    mapped = df[col].map(LIKERT_MAP).dropna()
                    if len(mapped) > 0:
                        cat_scores.setdefault(cat, []).append(mapped.mean())
            cat_avgs = {c: sum(v)/len(v) for c, v in cat_scores.items()}

            html_parts.append("<table><tr><th>Category</th><th>Score (1-4)</th><th>% Scale</th></tr>")
            for cat, avg in sorted(cat_avgs.items(), key=lambda x: x[1], reverse=True):
                pct = avg / 4 * 100
                label = cat.replace("_", " ").title()
                html_parts.append(
                    f'<tr><td>{label}</td><td><strong>{avg:.2f}</strong></td>'
                    f'<td><div class="bar-container"><div class="bar" style="width:{pct}%;background:#8b1a1a;">{pct:.0f}%</div></div></td></tr>'
                )
            html_parts.append("</table>")

        # Grade breakdown
        if inc_grade and "_grade" in df.columns and likert_cols:
            html_parts.append("<h2>Breakdown by Grade/Role</h2>")
            html_parts.append("<table><tr><th>Group</th><th>Avg Score</th><th>Responses</th></tr>")
            for grade in sorted(df["_grade"].dropna().astype(str).unique()):
                grade_df = df[df["_grade"].astype(str) == grade]
                scores = []
                for col in likert_cols:
                    mapped = grade_df[col].map(LIKERT_MAP).dropna()
                    if len(mapped) > 0:
                        scores.append(mapped.mean())
                if scores:
                    avg = sum(scores) / len(scores)
                    html_parts.append(f'<tr><td>{grade}</td><td>{avg:.2f} / 4.0</td><td>{len(grade_df)}</td></tr>')
            html_parts.append("</table>")

        # Benchmarks
        if inc_benchmark:
            try:
                benchmarks = load_benchmarks(str(DATA_DIR))
                rams_pcts = compute_rams_percentages(df)
                if rams_pcts:
                    html_parts.append(f"<h2>Regional Benchmark Comparison</h2>")
                    html_parts.append(f"<p>Compared against {benchmarks.get('source', 'MWAHS')}</p>")
                    html_parts.append("<table><tr><th>Indicator</th><th>RAMS</th><th>Regional</th><th>Difference</th></tr>")
                    for indicator, bench in benchmarks["indicators"].items():
                        if indicator in rams_pcts:
                            rams = rams_pcts[indicator]["pct"]
                            mwahs = bench["mwahs_pct"]
                            diff = rams - mwahs
                            color = "#27ae60" if diff > 5 else "#e74c3c" if diff < -5 else "#f39c12"
                            html_parts.append(
                                f'<tr><td>{indicator}</td><td>{rams:.0f}%</td><td>{mwahs}%</td>'
                                f'<td style="color:{color};font-weight:bold;">{diff:+.1f}%</td></tr>'
                            )
                    html_parts.append("</table>")
            except Exception:
                pass

        # At-risk
        if inc_atrisk:
            indicators = get_at_risk_indicators(df, survey_type=selected_type)
            if indicators:
                html_parts.append("<h2>At-Risk Indicators</h2>")
                html_parts.append(f'<p>{audience.capitalize()} who answered "Strongly disagree" or "No" on critical questions:</p>')
                html_parts.append("<div class='metric-grid'>")
                for label, info_at in indicators.items():
                    pct = info_at["count"] / info_at["total"] * 100 if info_at["total"] > 0 else 0
                    html_parts.append(
                        f'<div class="metric"><div class="value">{info_at["count"]}</div>'
                        f'<div class="label">{label} ({pct:.1f}%)</div></div>'
                    )
                html_parts.append("</div>")

        # Key insights
        if inc_insights:
            insights = generate_key_insights(df, audience=audience)
            if insights:
                html_parts.append("<h2>Key Insights</h2>")
                for ins in insights:
                    card_class = "card-red" if ins["severity"] == "high" else "card-yellow"
                    text = ins["text"].replace("**", "<strong>").replace("**", "</strong>")
                    # Fix markdown bold
                    import re
                    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', ins["text"])
                    html_parts.append(f'<div class="card {card_class}">{text}</div>')

        # Open responses
        if inc_open and open_cols:
            html_parts.append("<h2>Open Response Highlights</h2>")
            for col in open_cols[:2]:
                responses = df[col].dropna().astype(str)
                responses = responses[responses.str.len() > 5]
                if len(responses) > 0:
                    html_parts.append(f"<h3>{normalize_column_name(col)[:70]}</h3>")
                    html_parts.append(f"<p><em>{len(responses)} responses. Sample:</em></p><ul>")
                    for resp in responses.head(10):
                        html_parts.append(f"<li>{resp[:200]}</li>")
                    html_parts.append("</ul>")

        # Footer
        html_parts.append(f"""
<div class="footer">
    Generated by RAMS CARE Data Viewer | {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
    Data from: {info['label']} ({len(df)} responses)
</div></body></html>""")

        report_html = "\n".join(html_parts)

    st.success("Report generated!")
    st.markdown("**Download your report below.** Open the HTML file in your browser, then use Print → Save as PDF.")

    st.download_button(
        "Download Report (HTML)",
        report_html,
        file_name=f"RAMS_CARE_Report_{info['label'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
        mime="text/html",
        type="primary",
    )

    # Also offer CSV export
    st.markdown("---")
    st.markdown("### Data Export")
    st.markdown("Download the raw survey data as a spreadsheet.")

    display_cols = [c for c in df.columns if not c.startswith("_")]
    csv = df[display_cols].to_csv(index=False)
    st.download_button(
        "Download Raw Data (CSV)",
        csv,
        file_name=f"RAMS_CARE_Data_{info['label'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    # Preview
    with st.expander("Preview report"):
        st.components.v1.html(report_html, height=800, scrolling=True)
