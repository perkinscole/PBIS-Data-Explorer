import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from utils.data_loader import load_all_surveys, get_likert_columns
from utils.benchmarks import (
    DEFAULT_BENCHMARKS, compute_rams_percentages,
    load_benchmarks, save_benchmarks, parse_mwahs_pdf,
)
from utils.theme import apply_theme, get_survey_type_filter, filter_surveys_by_type

apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("Regional Benchmarks")
st.markdown(
    "Compare RAMS CARE survey results against the **MetroWest Adolescent Health Survey (MWAHS)** "
    "regional benchmarks. The MWAHS surveys 11,000+ middle school students across 25 communities."
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

# Filter to student surveys only (MWAHS is student-focused)
selected_type = get_survey_type_filter()
surveys, meta = filter_surveys_by_type(
    st.session_state.surveys, st.session_state.survey_meta, selected_type
)

# Load benchmarks
benchmarks = load_benchmarks(str(DATA_DIR))

if not surveys:
    st.info(
        f"No {selected_type} surveys loaded. The MWAHS benchmarks compare best with **Student** surveys. "
        "Upload student survey data or change the type filter."
    )
    st.stop()

# Let user pick which survey to compare
survey_labels = [m["label"] for m in meta]
selected_idx = st.sidebar.selectbox(
    "Compare Survey",
    range(len(survey_labels)),
    format_func=lambda i: survey_labels[i],
)
df = surveys[selected_idx]
survey_label = meta[selected_idx]["label"]

# Compute RAMS percentages
rams_pcts = compute_rams_percentages(df)

if not rams_pcts:
    st.warning(
        "Could not match any RAMS survey questions to the MWAHS benchmarks. "
        "This comparison works best with Student surveys that include questions about "
        "safety, belonging, teacher fairness, and adult support."
    )
    st.stop()

# ============================================================
# SECTION 1: Side-by-side comparison chart
# ============================================================
st.markdown("---")
st.markdown("## RAMS vs. Regional Benchmark")
st.markdown(
    f"Comparing **{survey_label}** against the "
    f"**{benchmarks.get('source', 'MWAHS')}** regional averages."
)

# Build comparison data
compare_rows = []
for indicator, bench_data in benchmarks["indicators"].items():
    if indicator in rams_pcts:
        rams = rams_pcts[indicator]
        compare_rows.append({
            "Indicator": indicator,
            "RAMS %": rams["pct"],
            "MWAHS %": bench_data["mwahs_pct"],
            "Difference": round(rams["pct"] - bench_data["mwahs_pct"], 1),
            "RAMS Question": rams["question"],
            "MWAHS Question": bench_data["mwahs_question"],
            "n": rams["n"],
        })

if compare_rows:
    compare_df = pd.DataFrame(compare_rows)

    # Grouped bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=compare_df["Indicator"],
        x=compare_df["RAMS %"],
        name=f"RAMS ({survey_label})",
        orientation="h",
        marker_color="#8b1a1a",
        text=[f"{v:.0f}%" for v in compare_df["RAMS %"]],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        y=compare_df["Indicator"],
        x=compare_df["MWAHS %"],
        name=f"MWAHS Regional ({benchmarks.get('year', '')})",
        orientation="h",
        marker_color="#3498db",
        text=[f"{v:.0f}%" for v in compare_df["MWAHS %"]],
        textposition="auto",
    ))
    fig.update_layout(
        barmode="group",
        title="% of Students Who Agree/Strongly Agree",
        xaxis_title="Percentage",
        xaxis=dict(range=[0, 105]),
        yaxis=dict(automargin=True),
        height=max(350, len(compare_df) * 70),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ============================================================
    # SECTION 2: Detailed breakdown
    # ============================================================
    st.markdown("---")
    st.markdown("## Detailed Breakdown")

    for _, row in compare_df.iterrows():
        diff = row["Difference"]
        if diff > 5:
            color = "#27ae60"
            icon = "above"
            bg = "#d5f5e3"
        elif diff < -5:
            color = "#e74c3c"
            icon = "below"
            bg = "#fadbd8"
        else:
            color = "#f39c12"
            icon = "similar to"
            bg = "#fef9e7"

        st.markdown(
            f'<div style="background-color:{bg}; border-left: 5px solid {color}; '
            f'padding: 12px 16px; border-radius: 6px; margin-bottom: 12px;">'
            f'<strong>{row["Indicator"]}</strong><br>'
            f'RAMS: <strong>{row["RAMS %"]:.0f}%</strong> &nbsp;|&nbsp; '
            f'MWAHS Regional: <strong>{row["MWAHS %"]:.0f}%</strong> &nbsp;|&nbsp; '
            f'<span style="color:{color}; font-weight:bold;">'
            f'{"+" if diff > 0 else ""}{diff:.1f}% ({icon} benchmark)</span><br>'
            f'<small>RAMS question: "{row["RAMS Question"]}" (n={row["n"]})<br>'
            f'MWAHS question: "{row["MWAHS Question"]}"</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Summary
    above = len(compare_df[compare_df["Difference"] > 5])
    below = len(compare_df[compare_df["Difference"] < -5])
    similar = len(compare_df) - above - below

    st.markdown("### Summary")
    cols = st.columns(3)
    cols[0].metric("Above Benchmark", above, help="More than 5% above MWAHS regional average")
    cols[1].metric("At Benchmark", similar, help="Within 5% of MWAHS regional average")
    cols[2].metric("Below Benchmark", below, help="More than 5% below MWAHS regional average")

    avg_diff = compare_df["Difference"].mean()
    if avg_diff > 3:
        st.success(f"Overall, RAMS is **{avg_diff:.1f}% above** the regional average across matched indicators.")
    elif avg_diff < -3:
        st.error(f"Overall, RAMS is **{abs(avg_diff):.1f}% below** the regional average across matched indicators.")
    else:
        st.info(f"Overall, RAMS is **within {abs(avg_diff):.1f}%** of the regional average across matched indicators.")

else:
    st.warning("No indicators could be matched between your survey and the benchmarks.")

# ============================================================
# SECTION 3: Upload new benchmarks
# ============================================================
st.markdown("---")
st.markdown("## Manage Benchmark Data")
st.markdown(
    "The app ships with **2023 MWAHS** data. When new reports are published, "
    "upload the PDF here to update the benchmarks."
)

# Show current benchmark info
with st.expander("Current benchmark data"):
    st.markdown(f"**Source:** {benchmarks.get('source', 'Unknown')}")
    st.markdown(f"**Year:** {benchmarks.get('year', 'Unknown')}")
    if benchmarks.get("sample_size"):
        st.markdown(f"**Sample size:** {benchmarks['sample_size']:,} students")
    st.markdown("**Indicators:**")
    for indicator, data in benchmarks["indicators"].items():
        st.markdown(f"- {indicator}: **{data['mwahs_pct']}%** — *\"{data['mwahs_question']}\"*")

# Upload new MWAHS report
uploaded_pdf = st.file_uploader(
    "Upload a MWAHS Report PDF",
    type=["pdf"],
    help="Upload a MetroWest Adolescent Health Survey report PDF to extract updated benchmarks",
)

if uploaded_pdf:
    # Save temporarily and parse
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded_pdf.getbuffer())
        tmp_path = tmp.name

    with st.spinner("Extracting benchmark data from PDF..."):
        parsed = parse_mwahs_pdf(tmp_path)

    import os
    os.unlink(tmp_path)

    if parsed and parsed.get("indicators"):
        st.success(f"Extracted {len(parsed['indicators'])} indicators from the report!")

        st.markdown("#### Verify Extracted Data")
        st.markdown("Review the values below and adjust if needed before saving.")

        # Editable table
        edit_rows = []
        for indicator, data in parsed["indicators"].items():
            edit_rows.append({
                "Indicator": indicator,
                "Percentage": data["mwahs_pct"],
                "Question": data["mwahs_question"],
            })

        edited_df = st.data_editor(
            pd.DataFrame(edit_rows),
            use_container_width=True,
            num_rows="dynamic",
            key="benchmark_editor",
        )

        col1, col2 = st.columns(2)
        with col1:
            new_year = st.number_input(
                "Report Year",
                value=parsed.get("year") or 2023,
                min_value=2006,
                max_value=2035,
            )
        with col2:
            new_sample = st.number_input(
                "Sample Size (if known)",
                value=parsed.get("sample_size") or 0,
                min_value=0,
            )

        if st.button("Save Updated Benchmarks", type="primary"):
            # Build updated benchmarks from edited table
            updated = {
                "source": f"{new_year} MetroWest Adolescent Health Survey (MWAHS)",
                "year": new_year,
                "sample_size": new_sample if new_sample > 0 else None,
                "description": f"Updated from uploaded MWAHS {new_year} report",
                "indicators": {},
            }
            for _, row in edited_df.iterrows():
                updated["indicators"][row["Indicator"]] = {
                    "mwahs_question": row["Question"],
                    "mwahs_pct": int(row["Percentage"]),
                    "mwahs_trend": {},
                }
            save_benchmarks(str(DATA_DIR), updated)
            st.success("Benchmarks updated! Refresh the page to see the new comparison.")
            st.rerun()
    else:
        st.warning(
            "Could not automatically extract benchmark data from this PDF. "
            "You can enter the data manually below."
        )

        # Manual entry fallback
        st.markdown("#### Enter Benchmarks Manually")
        st.markdown("Enter the percentage of students who agree/strongly agree for each indicator.")

        manual_rows = []
        for indicator in DEFAULT_BENCHMARKS["indicators"]:
            manual_rows.append({
                "Indicator": indicator,
                "Percentage": DEFAULT_BENCHMARKS["indicators"][indicator]["mwahs_pct"],
                "Question": DEFAULT_BENCHMARKS["indicators"][indicator]["mwahs_question"],
            })

        manual_df = st.data_editor(
            pd.DataFrame(manual_rows),
            use_container_width=True,
            num_rows="dynamic",
            key="manual_benchmark_editor",
        )

        col1, col2 = st.columns(2)
        with col1:
            manual_year = st.number_input("Report Year", value=2023, min_value=2006, max_value=2035, key="manual_year")
        with col2:
            manual_sample = st.number_input("Sample Size", value=0, min_value=0, key="manual_sample")

        if st.button("Save Manual Benchmarks", type="primary"):
            manual_benchmarks = {
                "source": f"{manual_year} MetroWest Adolescent Health Survey (MWAHS)",
                "year": manual_year,
                "sample_size": manual_sample if manual_sample > 0 else None,
                "description": f"Manually entered MWAHS {manual_year} data",
                "indicators": {},
            }
            for _, row in manual_df.iterrows():
                manual_benchmarks["indicators"][row["Indicator"]] = {
                    "mwahs_question": row["Question"],
                    "mwahs_pct": int(row["Percentage"]),
                    "mwahs_trend": {},
                }
            save_benchmarks(str(DATA_DIR), manual_benchmarks)
            st.success("Benchmarks saved! Refresh the page to see the new comparison.")
            st.rerun()

# Reset to defaults
if (DATA_DIR / "_benchmarks.json").exists():
    st.markdown("---")
    if st.button("Reset to Default 2023 Benchmarks", type="secondary"):
        (DATA_DIR / "_benchmarks.json").unlink()
        st.success("Reset to default 2023 MWAHS benchmarks.")
        st.rerun()
