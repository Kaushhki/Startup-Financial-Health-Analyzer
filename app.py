"""
Ledger Lens
-----------
A clear view into your startup's financial health. Upload a monthly
financials CSV/Excel file and get a runway, growth, and burn-efficiency
analysis rolled into a single Health Score, with an interactive dashboard.

Run with:
    streamlit run app.py
"""

import io

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from analyzer import (
    load_and_prepare,
    compute_core_metrics,
    compute_summary,
    DataValidationError,
    REQUIRED_COLUMNS,
)
from scoring import compute_health_score, generate_insights

st.set_page_config(
    page_title="Ledger Lens",
    page_icon="🔍",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar — data input
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Ledger Lens")
st.sidebar.caption("A clear view into your startup's financial health.")
st.sidebar.markdown(
    "Upload monthly financials and get an instant health check: "
    "runway, growth, margins, and burn efficiency."
)

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or Excel file", type=["csv", "xlsx", "xls"]
)
use_sample = st.sidebar.button("Or load sample data")

with st.sidebar.expander("Expected columns"):
    st.markdown(
        "**Required:** `month`, `revenue`, `cogs`, `opex`, `cash_balance`\n\n"
        "**Optional (unlocks more metrics):** `customers`, `new_customers`, "
        "`churned_customers`, `cac_spend`"
    )

df_raw = None
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
elif use_sample:
    df_raw = pd.read_csv("sample_data.csv")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🔍 Ledger Lens")
st.caption("A clear view into your startup's financial health.")

if df_raw is None:
    st.info(
        "👈 Upload a monthly financials file, or click **Load sample data** "
        "in the sidebar to see a demo."
    )
    st.subheader("What this tool does")
    st.markdown(
        """
        This dashboard turns a plain spreadsheet of monthly financials into
        the metrics investors and operators actually track:

        - **Runway** — how many months of cash are left at the current burn rate
        - **MoM Growth** — revenue growth trend, month over month
        - **Gross Margin** — how much of revenue is left after cost of goods sold
        - **Burn Multiple** — how much is spent to generate each new dollar of revenue
        - **Health Score** — a single 0-100 score combining all of the above

        Download the sample data below to see the expected format.
        """
    )
    try:
        with open("sample_data.csv", "rb") as f:
            st.download_button(
                "Download sample_data.csv", f, file_name="sample_data.csv"
            )
    except FileNotFoundError:
        pass
    st.stop()

try:
    df = load_and_prepare(df_raw)
    df = compute_core_metrics(df)
    summary = compute_summary(df)
    score = compute_health_score(summary)
    insights = generate_insights(summary, score)
except DataValidationError as e:
    st.error(str(e))
    st.markdown(f"Required columns: `{'`, `'.join(REQUIRED_COLUMNS)}`")
    st.stop()

# --- Health score banner --------------------------------------------------
grade_colors = {"A": "#2e7d32", "B": "#66bb6a", "C": "#fbc02d", "D": "#f57c00", "F": "#c62828"}
col_score, col_breakdown = st.columns([1, 2])

with col_score:
    st.markdown("### Overall Health Score")
    st.markdown(
        f"<div style='font-size:64px; font-weight:800; color:{grade_colors[score['grade']]};'>"
        f"{score['overall']}<span style='font-size:32px;'> / 100</span></div>"
        f"<div style='font-size:28px; font-weight:700; color:{grade_colors[score['grade']]};'>"
        f"Grade: {score['grade']}</div>",
        unsafe_allow_html=True,
    )

with col_breakdown:
    st.markdown("### Score Breakdown")
    breakdown_df = pd.DataFrame(
        {"Category": list(score["breakdown"].keys()), "Score": list(score["breakdown"].values())}
    )
    fig_breakdown = px.bar(
        breakdown_df, x="Score", y="Category", orientation="h", range_x=[0, 100],
        color="Score", color_continuous_scale=["#c62828", "#fbc02d", "#2e7d32"],
    )
    fig_breakdown.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False)
    st.plotly_chart(fig_breakdown, use_container_width=True)

st.divider()

# --- KPI cards -------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Cash Balance", f"${summary['current_cash']:,.0f}")
runway_display = "∞ (profitable)" if summary["profitable"] else f"{summary['runway_months']:.1f} mo"
k2.metric("Runway", runway_display)
growth_val = summary["avg_mom_growth"]
k3.metric("Avg MoM Growth", f"{growth_val*100:.1f}%" if pd.notna(growth_val) else "N/A")
margin_val = summary["avg_gross_margin"]
k4.metric("Avg Gross Margin", f"{margin_val*100:.1f}%" if pd.notna(margin_val) else "N/A")
bm_val = summary["avg_burn_multiple"]
k5.metric("Avg Burn Multiple", f"{bm_val:.2f}x" if pd.notna(bm_val) else "N/A")

st.divider()

# --- Insights ---------------------------------------------------------------
st.markdown("### Key Insights")
for line in insights:
    st.markdown(f"- {line}")

st.divider()

# --- Charts ------------------------------------------------------------------
st.markdown("### Revenue vs. Expenses")
fig_rev_exp = go.Figure()
fig_rev_exp.add_trace(go.Scatter(x=df["month_label"], y=df["revenue"], name="Revenue", mode="lines+markers"))
fig_rev_exp.add_trace(go.Scatter(x=df["month_label"], y=df["cogs"] + df["opex"], name="Total Costs", mode="lines+markers"))
fig_rev_exp.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig_rev_exp, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("### Cash Balance Over Time")
    fig_cash = px.area(df, x="month_label", y="cash_balance")
    fig_cash.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_cash, use_container_width=True)

with c2:
    st.markdown("### Net Burn Over Time")
    colors = ["#c62828" if v > 0 else "#2e7d32" for v in df["net_burn"]]
    fig_burn = go.Figure(go.Bar(x=df["month_label"], y=df["net_burn"], marker_color=colors))
    fig_burn.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_burn, use_container_width=True)

st.markdown("### Revenue Growth (Month over Month)")
fig_growth = px.bar(df, x="month_label", y="revenue_growth_mom")
fig_growth.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis_tickformat=".0%")
st.plotly_chart(fig_growth, use_container_width=True)

if "cac" in df.columns:
    st.markdown("### Customer Acquisition Cost (CAC)")
    fig_cac = px.line(df, x="month_label", y="cac", markers=True)
    fig_cac.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_cac, use_container_width=True)

# --- Raw data / export -------------------------------------------------------
with st.expander("View underlying data"):
    st.dataframe(df, use_container_width=True)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button("Download analyzed data as CSV", csv_buffer.getvalue(), file_name="analyzed_financials.csv")
