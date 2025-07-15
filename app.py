
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

# Let user pick time range
timeframe_days = st.selectbox("Select APR Timeframe", [30, 14, 7, 3, 1])
end_time = df[time_col].max()
start_time = end_time - pd.Timedelta(days=timeframe_days)
df = df[df[time_col] >= start_time].copy()

# Calculate APR
df["Funding Rate (%)"] = df[funding_col] * funding_multiplier
df["APR (%)"] = df["Funding Rate (%)"] * (365 * 24 / interval_hours)

# Show Summary APRs
st.markdown("### 📌 APR Summary for Last {} Days".format(timeframe_days))

# Website-style APR
cumulative_return = (df["APR (%)"] / (365 * 24 / interval_hours) / 100 + 1).prod()
website_apr = (cumulative_return ** (365 / timeframe_days) - 1) * 100 if len(df) else 0

col1, col2 = st.columns(2)
col1.metric("📈 Website-Style APR (preferred)", f"{website_apr:.2f}%")
col2.metric("🧮 Average of Interval APRs", f"{df['APR (%)'].mean():.2f}%" if len(df) else "N/A")

# Line chart of APR
st.markdown("### 📈 APR (%) Over Time")
fig_apr = px.line(df, x=time_col, y="APR (%)")
st.plotly_chart(fig_apr, use_container_width=True)

# Visual square indicator
st.markdown("### 🟦 APR Visual Heatmap")
def apr_to_color(apr):
    if apr > 100:
        return "green"
    elif apr < -100:
        return "red"
    elif apr < 1:
        return "orange"
    elif apr > 1:
        return "blue"
    else:
        return "lightgray"

colors = [apr_to_color(apr) for apr in df["APR (%)"]]
square_html = "".join([f"<span style='display:inline-block;width:10px;height:10px;margin:1px;background:{c};border-radius:2px;'></span>" for c in colors])
st.markdown(square_html, unsafe_allow_html=True)

# Export
st.download_button("📥 Download CSV with APR", df.to_csv(index=False).encode(), "output_with_apr.csv", "text/csv")
