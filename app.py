
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("💹 Funding Rate APR Tool")

uploaded_file = st.file_uploader("Upload a CSV or Excel funding file", type=["csv", "xlsx"])
if not uploaded_file:
    st.stop()

# Load the file
if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_excel(uploaded_file)

# Show preview
st.subheader("🔍 File Preview")
st.write(df.head())
st.text("Detected Columns: " + ", ".join([str(c) for c in df.columns]))

# Let user select columns
st.subheader("Select Columns")
time_col = st.selectbox("Select Timestamp Column", df.columns)
funding_col = st.selectbox("Select Funding Rate Column", df.columns)

# Let user define funding rate format
format_option = st.selectbox("Funding Rate Format", ["Percent (e.g., 0.01%)", "Decimal (e.g., 0.0001)"])
funding_multiplier = 1 if "Percent" in format_option else 100

# Parse time
df[time_col] = pd.to_datetime(df[time_col])
df = df.sort_values(by=time_col).reset_index(drop=True)

# Set funding interval
interval_hours = st.number_input("Funding Interval (Hours)", min_value=1, max_value=24, value=4)

# Let user input custom time range
timeframe_days = st.number_input("Select APR Timeframe (1–90 Days)", min_value=1, max_value=90, value=30)
end_time = df[time_col].max()
start_time = end_time - pd.Timedelta(days=timeframe_days)
df_filtered = df[df[time_col] >= start_time].copy()

# Calculate APR
df_filtered["Funding Rate (%)"] = pd.to_numeric(df_filtered[funding_col], errors="coerce")
df_filtered.dropna(subset=["Funding Rate (%)"], inplace=True)
df_filtered["Funding Rate (%)"] *= funding_multiplier
df_filtered["APR (%)"] = df_filtered["Funding Rate (%)"] * (365 * 24 / interval_hours)

# Summary
st.markdown("### 📌 APR Summary")
cumulative_return = (df_filtered["APR (%)"] / (365 * 24 / interval_hours) / 100 + 1).prod()
website_apr = (cumulative_return ** (365 / timeframe_days) - 1) * 100 if len(df_filtered) else 0

col1, col2 = st.columns(2)
col1.metric("📈 Website-Style APR (preferred)", f"{website_apr:.2f}%")
col2.metric("🧮 Average of Interval APRs", f"{df_filtered['APR (%)'].mean():.2f}%" if len(df_filtered) else "N/A")

# APR Over Time chart
st.subheader("📈 APR (%) Over Time")
fig_apr = px.line(df_filtered, x=time_col, y="APR (%)", title="APR Over Time")
st.plotly_chart(fig_apr, use_container_width=True)

# 🔲 Square indicator synced to timeframe
st.subheader("🟦 APR Threshold Squares")
def apr_to_color(apr):
    if apr > 100:
        return "green"
    elif apr < -100:
        return "red"
    elif abs(apr) < 1:
        return "orange"
    else:
        return "blue"

colors = df_filtered["APR (%)"].apply(apr_to_color).tolist()
timestamps = df_filtered[time_col].tolist()

html_blocks = []
for i, color in enumerate(colors):
    if i > 0 and timestamps[i].date() != timestamps[i - 1].date():
        html_blocks.append("<span style='display:inline-block;width:6px;height:10px;margin:1px;background:transparent;'></span>")
    html_blocks.append(f"<span style='display:inline-block;width:10px;height:10px;margin:1px;background:{color};border-radius:2px;'></span>")

square_html = ''.join(html_blocks)
st.markdown(square_html, unsafe_allow_html=True)

# Raw Funding Chart
st.subheader("📊 APR Per Funding Interval")
st.line_chart(df_filtered.set_index(time_col)['APR (%)'])

st.subheader("💹 Funding Rate (%) Over Time")
st.line_chart(df_filtered.set_index(time_col)['Funding Rate (%)'])

# Export
st.download_button("📥 Download CSV with APR", df_filtered.to_csv(index=False).encode(), "output_with_apr.csv", "text/csv")
