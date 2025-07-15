
import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

st.title("📈 Isolated Funding Rate APR Viewer (v10.3)")

st.markdown("""
Upload a single funding file (Bybit, WOOX, Hyperliquid, or compatible).

- Select timestamp and funding rate columns
- Set funding interval (e.g., 4 hours, 1 hour)
- Choose timeframe (1 to 90 days)
- Manually confirm funding rate format
- View accurate vs legacy APR calculations
- Export enriched CSV and APR logic
""")

uploaded_file = st.file_uploader("Upload funding file (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    exchange = st.selectbox("Select Exchange", ["Bybit", "WOOX", "Other"])

    # Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("📄 Raw Data Preview:", df.head())
    st.write("📌 Columns detected:", list(df.columns))

    time_col = st.selectbox("🕒 Select Timestamp Column", options=df.columns)
    funding_col = st.selectbox("💸 Select Funding Rate Column", options=df.columns)

    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df = df.sort_values(by=time_col)

    if len(df) > 1:
        detected_interval = (df[time_col].iloc[1] - df[time_col].iloc[0]).total_seconds() / 3600
    else:
        detected_interval = 4
    interval_hours = st.number_input("⏱ Funding Interval (Hours)", value=round(detected_interval), step=1)

    funding_format = st.radio("💱 Funding Rate Format", ["Decimal (e.g. 0.0001)", "Percent (e.g. 0.01%)"])

    df[funding_col] = df[funding_col].astype(str).str.replace('%', '', regex=False)
    df[funding_col] = pd.to_numeric(df[funding_col], errors='coerce')
    df = df.dropna(subset=[funding_col])

    if funding_format == "Percent (e.g. 0.01%)":
        df[funding_col] = df[funding_col] / 100

    df['Funding (%)'] = df[funding_col] * 100
    df['APR (%)'] = df[funding_col] * (365 * 24 / interval_hours) * 100

    days = st.number_input("📆 Select APR Timeframe (1-90 days)", min_value=1, max_value=90, value=30)
    cutoff_time = df[time_col].max() - timedelta(days=days)
    df_filtered = df[df[time_col] >= cutoff_time]

    # --- Row count validator ---
    expected_rows = int((24 / interval_hours) * days)
    actual_rows = len(df_filtered)
    if actual_rows < expected_rows:
        st.warning(f"⚠️ Only {actual_rows} rows found in timeframe — expected ~{expected_rows}. Results may be less reliable.")

    avg_funding_rate = df_filtered[funding_col].mean()
    annualized_apr_clean = avg_funding_rate * 365 * 24 * 100
    average_apr_legacy = df_filtered["APR (%)"].mean()

    st.subheader(f"📌 APR Summary for Last {days} Days")
    st.metric(label="📈 Website-Style APR (preferred)", value=f"{annualized_apr_clean:.2f}%", help="Based on average funding rate × 8760 × 100")
    st.metric(label="🧮 Average of Interval APRs", value=f"{average_apr_legacy:.2f}%", help="Average of each row's APR (legacy method)")

    # Plot APR chart
    st.subheader("📈 APR (%) Over Time")
    st.line_chart(df_filtered.set_index(time_col)['APR (%)'])

    # Visual Squares with daily separator
    st.subheader("🟦 APR Threshold Squares")
    def apr_to_color(apr):
        if apr > 100:
            return "green"
        elif apr < -100:
            return "red"
        elif apr < 1:
            return "orange"
        else:
            return "blue"

    colors = df_filtered['APR (%)'].apply(apr_to_color)
    dates = df_filtered[time_col].dt.date.tolist()
    square_html = ""
    last_day = None
    for color, day in zip(colors, dates):
        if last_day is not None and day != last_day:
            square_html += "<span style='display:inline-block;width:4px;height:10px;margin:1px;background:none;'>-</span>"
        square_html += f"<span style='display:inline-block;width:10px;height:10px;margin:1px;background:{color};border-radius:2px;'></span>"
        last_day = day
    st.markdown(square_html, unsafe_allow_html=True)

    st.subheader("💹 Funding Rate (%) Over Time")
    st.line_chart(df_filtered.set_index(time_col)['Funding (%)'])

    st.subheader("📊 APR Per Funding Interval")
    st.bar_chart(df_filtered.set_index(time_col)['APR (%)'])

    # --- Export CSVs ---
    output = io.BytesIO()
    df.to_csv(output, index=False)
    st.download_button(
        label="📤 Download CSV with APR",
        data=output.getvalue(),
        file_name=f"{exchange.lower()}_with_apr.csv",
        mime="text/csv"
    )

    # --- Logic snapshot CSV ---
    logic_df = pd.DataFrame({
        "Exchange": [exchange],
        "Funding Interval (H)": [interval_hours],
        "APR Timeframe (Days)": [days],
        "Funding Format": [funding_format],
        "Funding Rows Used": [actual_rows],
        "Expected Rows": [expected_rows],
        "Website-Style APR": [annualized_apr_clean],
        "Legacy APR Avg": [average_apr_legacy],
    })
    logic_buf = io.BytesIO()
    logic_df.to_csv(logic_buf, index=False)
    st.download_button(
        label="📄 Download APR Logic Summary",
        data=logic_buf.getvalue(),
        file_name=f"{exchange.lower()}_apr_logic_summary.csv",
        mime="text/csv"
    )
