import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import base64

st.set_page_config(page_title="APR Visualizer", layout="wide")

st.title("📈 Crypto Funding Rate APR Analyzer v10.3")

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    # Load data
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📄 Raw Preview")
    st.dataframe(df.head(10))

    # Select relevant columns
    time_col = st.selectbox("Select time column", df.columns, index=0)
    fund_col = st.selectbox("Select funding rate column", df.columns, index=1)
    interval_hours = st.number_input("Funding interval (hours)", min_value=1, max_value=24, value=4)
    num_days = st.number_input("Custom timeframe (days)", min_value=1, max_value=90, value=30)

    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col, ascending=False)

    # Convert funding
    df['Funding Rate (%)'] = pd.to_numeric(df[fund_col].astype(str).str.replace('%','').str.strip(), errors='coerce')
    df.dropna(subset=['Funding Rate (%)'], inplace=True)
    df['Funding Rate (decimal)'] = df['Funding Rate (%)'] / 100

    rows_expected = int((num_days * 24) / interval_hours)
    df_selected = df.head(rows_expected)
    actual_rows = len(df_selected)

    # APR Calculations
    annual_factor = 365 * 24 / interval_hours
    df_selected['APR Interval (%)'] = df_selected['Funding Rate (decimal)'] * annual_factor * 100
    website_style_apr = df_selected['Funding Rate (decimal)'].sum() * annual_factor * 100
    avg_interval_apr = df_selected['APR Interval (%)'].mean()

    # Show results
    st.subheader(f"📊 Results for Last {num_days} Days")
    st.markdown(f"**📈 Website-Style APR (preferred):** `{website_style_apr:.2f}%`")
    st.markdown(f"**🧮 Average of Interval APRs:** `{avg_interval_apr:.2f}%`")

    # Data completeness check
    if actual_rows < rows_expected:
        st.warning(f"⚠️ Only {actual_rows} of {rows_expected} expected rows found. Results may be incomplete.")
    else:
        st.success(f"✅ Using {actual_rows} funding intervals for {num_days} days @ {interval_hours}h")

    # Chart: APR Over Time
    st.subheader("📈 APR (%) Over Time")
    st.line_chart(df_selected.set_index(time_col)['APR Interval (%)'])

    # Visual indicator with spacing
    st.subheader("🟩 APR Interval Visual Map")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.ticker as ticker

    fig, ax = plt.subplots(figsize=(min(24, len(df_selected)), 1))
    colors = []
    for val in df_selected['APR Interval (%)']:
        if val > 100:
            colors.append("green")
        elif val < -100:
            colors.append("red")
        elif abs(val) < 1:
            colors.append("orange")
        else:
            colors.append("blue")

    for i, color in enumerate(colors):
        ax.add_patch(mpatches.Rectangle((i + (i // (24//interval_hours)), 0), 1, 1, color=color))

    ax.set_xlim(0, len(colors) + len(colors)//(24//interval_hours))
    ax.set_ylim(0, 1)
    ax.axis('off')
    st.pyplot(fig)

    # Export APR breakdown
    st.subheader("⬇️ Export APR Logic Breakdown")
    df_selected_export = df_selected[[time_col, 'Funding Rate (%)', 'Funding Rate (decimal)', 'APR Interval (%)']].copy()
    df_selected_export['Interval Hours'] = interval_hours
    df_selected_export['Days Selected'] = num_days
    df_selected_export['Cumulative Funding'] = df_selected['Funding Rate (decimal)'].cumsum()
    df_selected_export['Website-Style APR'] = website_style_apr
    df_selected_export['Average Interval APR'] = avg_interval_apr

    csv = df_selected_export.to_csv(index=False).encode('utf-8')
    st.download_button("📤 Download Full APR Logic CSV", csv, f"full_apr_logic_{num_days}d.csv", "text/csv")
