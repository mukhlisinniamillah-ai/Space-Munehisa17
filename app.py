# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core import (
    parse_broker_input,
    analyze_broker_summary,
    get_historical_data,
    get_technical_data,
    analyze_trend,
    analyze_sr,
    analyze_volume,
    analyze_rsi,
)

st.set_page_config(page_title="Chatbot Bandar + Teknikal (yFinance)", layout="wide")

st.title("📊 Chatbot Analisis Bandar + Teknikal (yFinance)")
st.markdown("Masukkan data broker summary (3 periode) dan kode saham untuk analisis.")

# ============ SIDEBAR INPUT ============
with st.sidebar:
    st.header("⚙️ Input Data")

    st.subheader("🔹 Data Broker Summary (3 periode)")

    def broker_inputs(role, period_key):
        st.markdown(f"**{role} - {period_key}**")
        brokers = []
        for i in range(1, 4):
            cols = st.columns([2, 2, 2])
            with cols[0]:
                broker = st.text_input(f"Broker {i}", key=f"{role}_{period_key}_{i}_broker")
            with cols[1]:
                lot = st.number_input(f"Lot {i}", min_value=0.0, step=1000.0, key=f"{role}_{period_key}_{i}_lot")
            with cols[2]:
                price = st.number_input(f"Harga {i}", min_value=0.0, step=10.0, key=f"{role}_{period_key}_{i}_price")
            brokers.append({"broker": broker, "lot": lot, "price": price})
        return brokers

    # Periode 1 minggu
    st.markdown("---")
    buyers_1w = broker_inputs("Top Buyer", "1 MINGGU")
    sellers_1w = broker_inputs("Top Seller", "1 MINGGU")

    # Periode 1 bulan
    st.markdown("---")
    buyers_1m = broker_inputs("Top Buyer", "1 BULAN")
    sellers_1m = broker_inputs("Top Seller", "1 BULAN")

    # Periode 3 bulan
    st.markdown("---")
    buyers_3m = broker_inputs("Top Buyer", "3 BULAN")
    sellers_3m = broker_inputs("Top Seller", "3 BULAN")

    st.markdown("---")
    symbol = st.text_input("🔹 Kode Saham (contoh: CARE.JK)", value="CARE.JK")
    period = st.selectbox("Periode Data", ["1mo", "3mo", "6mo", "1y"], index=1)
    support = st.number_input("Support (opsional)", min_value=0.0, step=10.0, value=0.0)
    resistance = st.number_input("Resistance (opsional)", min_value=0.0, step=10.0, value=0.0)

    analyze_btn = st.button("🚀 Analisis", type="primary", use_container_width=True)

# ============ MAIN LOGIC ============
if analyze_btn:
    # Parse input broker
    buyers_1w_parsed = parse_broker_input(buyers_1w)
    sellers_1w_parsed = parse_broker_input(sellers_1w)
    buyers_1m_parsed = parse_broker_input(buyers_1m)
    sellers_1m_parsed = parse_broker_input(sellers_1m)
    buyers_3m_parsed = parse_broker_input(buyers_3m)
    sellers_3m_parsed = parse_broker_input(sellers_3m)

    # Analisis bandar
    broker_result = analyze_broker_summary(
        buyers_1w_parsed, sellers_1w_parsed,
        buyers_1m_parsed, sellers_1m_parsed,
        buyers_3m_parsed, sellers_3m_parsed
    )

    # Ambil data historis
    hist, err = get_historical_data(symbol, period=period)
    if err:
        st.error(err)
        st.stop()

    # Hitung teknikal
    tech_result, err2 = get_technical_data(hist)
    if err2:
        st.error(err2)
        st.stop()

    current_price = tech_result["current_price"]
    ma5 = tech_result["ma5"].iloc[-1]
    ma10 = tech_result["ma10"].iloc[-1]
    ma20 = tech_result["ma20"].iloc[-1]
    volume_today = tech_result["volume_today"]
    avg_volume_20 = tech_result["avg_volume_20"]
    rsi = tech_result["rsi"].iloc[-1]

    # ============ TAMPILKAN HASIL ============
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Broker Summary (Bandar)")
        st.write(f"**Status:** {broker_result['status']}")
        if broker_result['bandar_text'] != "-":
            st.write(f"**Pelaku utama:** {broker_result['bandar_text']}")
        st.write(f"**Risiko:** {broker_result['risk']}")
        if broker_result['korban'] != "-":
            st.write(f"**Korban:** {broker_result['korban']}")
        if broker_result['avg_buy'] > 0:
            st.write(f"**Rata-rata harga BELI bandar (3 bulan):** Rp {broker_result['avg_buy']:,.2f}")
        if broker_result['avg_sell'] > 0:
            st.write(f"**Rata-rata harga JUAL bandar (3 bulan):** Rp {broker_result['avg_sell']:,.2f}")

    with col2:
        st.subheader("📉 Teknikal (yFinance)")
        st.write(f"**Harga saat ini:** Rp {current_price:,.2f}")
        st.write(f"**MA5:** {ma5:,.2f}, **MA10:** {ma10:,.2f}, **MA20:** {ma20:,.2f}")
        st.write(f"**Volume hari ini:** {volume_today:,}, **Rata-rata 20 hari:** {avg_volume_20:,}")
        st.write(f"**RSI:** {rsi:.1f}")

    # ============ GRAFIK TEKNIKAL ============
    st.subheader("📉 Grafik Teknikal")

    # Candlestick + MA
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("Harga & MA", "Volume", "RSI")
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name="Candlestick"
        ),
        row=1, col=1
    )

    # Moving Averages
    fig.add_trace(go.Scatter(x=hist.index, y=tech_result["ma5"], name="MA5", line=dict(color="orange", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=tech_result["ma10"], name="MA10", line=dict(color="blue", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=tech_result["ma20"], name="MA20", line=dict(color="red", width=1)), row=1, col=1)

    # Volume
    colors = ['green' if close >= open else 'red' for close, open in zip(hist['Close'], hist['Open'])]
    fig.add_trace(
        go.Bar(x=hist.index, y=hist['Volume'], name="Volume", marker_color=colors),
        row=2, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(x=hist.index, y=tech_result["rsi"], name="RSI", line=dict(color="purple", width=1)),
        row=3, col=1
    )
    # Garis overbought/oversold
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(title_text="Tanggal", row=3, col=1)
    fig.update_yaxes(title_text="Harga", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # ============ ANALISIS TEKNIKAL ============
    trend = analyze_trend(current_price, ma5, ma10, ma20)
    sr_analysis = analyze_sr(current_price, support if support > 0 else None, resistance if resistance > 0 else None)
    vol_analysis = analyze_volume(volume_today, avg_volume_20)
    rsi_analysis = analyze_rsi(rsi)

    st.subheader("📊 Analisis Teknikal Detail")
    st.write(f"**Tren:** {trend}")
    st.write(sr_analysis)
    st.write(vol_analysis)
    st.write(rsi_analysis)

    # ============ KONFIRMASI SINYAL ============
    signal = "LEMAH"
    if "AKUMULASI" in broker_result["status"] and ("UPTREND" in trend):
        signal = "KUAT (bandar akumulasi + teknikal bullish)"
    elif "DISTRIBUSI" in broker_result["status"] and ("DOWNTREND" in trend):
        signal = "KUAT (bandar distribusi + teknikal bearish)"
    elif "AKUMULASI" in broker_result["status"] and ("SIDEWAYS" in trend or "UPTREND LEMAH" in trend):
        signal = "SEDANG"
    elif "DISTRIBUSI" in broker_result["status"] and ("SIDEWAYS" in trend or "DOWNTREND LEMAH" in trend):
        signal = "SEDANG"
    elif "LOW RISK" in broker_result["status"]:
        signal = "LEMAH (bukan bandar utama)"

    st.subheader("🔮 Konfirmasi Sinyal & Rekomendasi")
    st.write(f"**Sinyal:** {signal}")

    if "KUAT" in signal and "AKUMULASI" in broker_result["status"]:
        st.success("✅ REKOMENDASI: BUY ON WEAKNESS. Target resistance. Stop loss di bawah support.")
    elif "KUAT" in signal and "DISTRIBUSI" in broker_result["status"]:
        st.error("⚠️ REKOMENDASI: HINDARI atau SELL ON STRENGTH. Potensi koreksi.")
    elif "SEDANG" in signal and "AKUMULASI" in broker_result["status"]:
        st.info("📌 REKOMENDASI: Pantau. Beli hanya jika konfirmasi tren naik.")
    elif "LEMAH" in signal:
        st.info("📌 REKOMENDASI: Wait and see. Tidak ada sinyal kuat.")
    else:
        st.info("📌 REKOMENDASI: Analisis lebih lanjut diperlukan.")

else:
    st.info("👈 Masukkan data di sidebar, lalu klik 'Analisis'.")
