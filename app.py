import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

st.title("📈 Isolated Funding Rate APR Viewer")

st.markdown("""
Upload a single funding file (Bybit, WOOX, Hyperliquid, or compatible).

- Select timestamp and funding rate columns
- Set funding interval (e.g., 4 hours, 1 hour)
- Choose timeframe (30, 14, 7, 3, 1 days)
- Manually confirm funding rate format
- View accurate vs legacy APR calculations
- Export enriched CSV
""")

uploaded_file = st.file_uploader("Upload funding file (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    exchange = st.selectbox("Select Exchange", ["Bybit", "WOOX", "Other"])

    # Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("Raw Data Preview:", df.head())
    st.write("Columns detected in file:", list(df.columns))

    # Manual column selection
    time_col = st.selectbox("Select Timestamp Column", options=df.columns)
    funding_col = st.selectbox("Select Funding Rate Column", options=df.columns)

    # Convert timestamp
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df = df.sort_values(by=time_col)

    # Detect or override funding interval
    if len(df) > 1:
        detected_interval = (df[time_col].iloc[1] - df[time_col].iloc[0]).total_seconds() / 3600
    else:
        detected_interval = 4
    interval_hours = st.number_input("Funding Interval (Hours)", value=round(detected_interval), step=1)

    # Ask user for funding rate format
    funding_format = st.radio("Funding Rate Format", ["Decimal (e.g. 0.0001)", "Percent (e.g. 0.01%)"])

    # Clean and parse funding rate column
    df[funding_col] = df[funding_col].astype(str).str.replace('%', '', regex=False)
    df[funding_col] = pd.to_numeric(df[funding_col], errors='coerce')
    df = df.dropna(subset=[funding_col])

    if funding_format == "Percent (e.g. 0.01%)":
        df[funding_col] = df[funding_col] / 100

    # Calculate APR
    df['Funding (%)'] = df[funding_col] * 100
    df['APR (%)'] = df[funding_col] * (365 * 24 / interval_hours) * 100

    # Select timeframe
    days = st.selectbox("Select APR Timeframe", [30, 14, 7, 3, 1])
    cutoff_time = df[time_col].max() - timedelta(days=days)
    df_filtered = df[df[time_col] >= cutoff_time]

    # Method 1: Website-style APR (preferred)
    avg_funding_rate = df_filtered[funding_col].mean()
    annualized_apr_clean = avg_funding_rate * 365 * 24 * 100

    # Method 2: Legacy per-row APR average
    average_apr_legacy = df_filtered["APR (%)"].mean()

    st.subheader(f"📌 APR Summary for Last {days} Days")
    st.metric(label="📈 Website-Style APR (preferred)", value=f"{annualized_apr_clean:.2f}%", help="Based on average funding rate × 8760 × 100")
    st.metric(label="🧮 Average of Interval APRs", value=f"{average_apr_legacy:.2f}%", help="Average of each row's APR (legacy method)")

    # Charts
    st.subheader("📈 APR (%) Over Time")
    st.line_chart(df_filtered.set_index(time_col)['APR (%)'])

    st.subheader("💹 Funding Rate (%) Over Time")
    st.line_chart(df_filtered.set_index(time_col)['Funding (%)'])

    st.subheader("📊 APR Per Funding Interval")
    st.bar_chart(df_filtered.set_index(time_col)['APR (%)'])

    # CSV download
    output = io.BytesIO()
    df.to_csv(output, index=False)
    st.download_button(
        label="📤 Download CSV with APR",
        data=output.getvalue(),
        file_name=f"{exchange.lower()}_with_apr.csv",
        mime="text/csv"
    )
# === 📉 APR Chart with EMA + RSI ===
st.subheader("📉 APR (%) Over Time with EMA(10/30) and RSI(14)")

from plotly.subplots import make_subplots

if "APR (%)" in df.columns and "time" in df.columns:
    df_sorted = df_filtered.sort_values("time")
    df_sorted["EMA_10"] = df_sorted["APR (%)"].ewm(span=10, adjust=False).mean()
    df_sorted["EMA_30"] = df_sorted["APR (%)"].ewm(span=30, adjust=False).mean()
    delta = df_sorted["APR (%)"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df_sorted["RSI_14"] = 100 - (100 / (1 + rs))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
                        subplot_titles=["APR (%) + EMA", "RSI (14) on APR"])

    fig.add_scatter(x=df_sorted["time"], y=df_sorted["APR (%)"], name="APR (%)", row=1, col=1)
    fig.add_scatter(x=df_sorted["time"], y=df_sorted["EMA_10"], name="EMA 10", row=1, col=1)
    fig.add_scatter(x=df_sorted["time"], y=df_sorted["EMA_30"], name="EMA 30", row=1, col=1)
    fig.add_scatter(x=df_sorted["time"], y=df_sorted["RSI_14"], name="RSI (14)", row=2, col=1)
    fig.add_hline(y=70, line=dict(dash='dash'), row=2, col=1)
    fig.add_hline(y=30, line=dict(dash='dash'), row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
