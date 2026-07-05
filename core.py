# core.py
import yfinance as yf
import pandas as pd
import numpy as np

# Daftar broker smart money (case-insensitive)
BANDAR_FOREIGN = {"ak", "bk", "zp", "yu", "tp", "bq", "xa"}
BANDAR_DOMESTIK = {"mg", "rf", "hp", "if", "sq", "ni"}


# ==================== FUNGSI INPUT BROKER ====================
def parse_broker_input(broker_list):
    """
    Menerima list of dict dengan keys: broker, lot, price
    return list of tuples (broker, lot, price)
    """
    result = []
    for item in broker_list:
        broker = item.get("broker", "").strip().upper()
        try:
            lot = float(item.get("lot", 0))
            price = float(item.get("price", 0))
        except:
            lot, price = 0, 0
        if broker and lot > 0 and price > 0:
            result.append((broker, lot, price))
    return result


# ==================== FUNGSI ANALISIS BANDAR ====================
def weighted_average_price(data):
    total_lot = sum(lot for _, lot, _ in data)
    if total_lot == 0:
        return 0
    total_value = sum(lot * price for _, lot, price in data)
    return total_value / total_lot


def find_consistent_brokers(data_periods):
    if not data_periods:
        return set()
    sets = [set(broker for broker, _, _ in period) for period in data_periods]
    return set.intersection(*sets) if sets else set()


def classify(brokers):
    foreign = [b for b in brokers if b.lower() in BANDAR_FOREIGN]
    domestik = [b for b in brokers if b.lower() in BANDAR_DOMESTIK]
    other = [b for b in brokers if b.lower() not in BANDAR_FOREIGN and b.lower() not in BANDAR_DOMESTIK]
    return foreign, domestik, other


def analyze_broker_summary(buyers_1w, sellers_1w, buyers_1m, sellers_1m, buyers_3m, sellers_3m):
    consistent_buyers = find_consistent_brokers([buyers_1w, buyers_1m, buyers_3m])
    consistent_sellers = find_consistent_brokers([sellers_1w, sellers_1m, sellers_3m])

    foreign_buyers, dom_buyers, other_buyers = classify(consistent_buyers)
    foreign_sellers, dom_sellers, other_sellers = classify(consistent_sellers)

    if foreign_buyers or dom_buyers:
        status = "AKUMULASI"
        bandar_text = []
        if foreign_buyers:
            bandar_text.append(f"Foreign: {', '.join(foreign_buyers)}")
        if dom_buyers:
            bandar_text.append(f"Domestik: {', '.join(dom_buyers)}")
        bandar_text = "; ".join(bandar_text)
        risk = "HIGH (aksi bandar)"
        korban = "Top seller tidak konsisten (ritel atau bandar lain)"
    elif foreign_sellers or dom_sellers:
        status = "DISTRIBUSI"
        bandar_text = []
        if foreign_sellers:
            bandar_text.append(f"Foreign: {', '.join(foreign_sellers)}")
        if dom_sellers:
            bandar_text.append(f"Domestik: {', '.join(dom_sellers)}")
        bandar_text = "; ".join(bandar_text)
        risk = "HIGH (aksi bandar distribusi)"
        korban = "Top buyer tidak konsisten (ritel atau bandar lain)"
    elif other_buyers:
        status = "AKUMULASI LOW RISK"
        bandar_text = f"Non-bandar: {', '.join(other_buyers)}"
        risk = "LOW (bukan bandar utama)"
        korban = "-"
    elif other_sellers:
        status = "DISTRIBUSI LOW RISK"
        bandar_text = f"Non-bandar: {', '.join(other_sellers)}"
        risk = "LOW (bukan bandar utama)"
        korban = "-"
    else:
        status = "TIDAK JELAS / SIDEWAYS"
        bandar_text = "-"
        risk = "-"
        korban = "-"

    avg_buy = weighted_average_price(buyers_3m) if buyers_3m else 0
    avg_sell = weighted_average_price(sellers_3m) if sellers_3m else 0

    return {
        "status": status,
        "bandar_text": bandar_text,
        "risk": risk,
        "korban": korban,
        "avg_buy": avg_buy,
        "avg_sell": avg_sell
    }


# ==================== FUNGSI TEKNIKAL (yFinance) ====================
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_historical_data(symbol, period="3mo"):
    """
    Mengambil data historis lengkap (Open, High, Low, Close, Volume)
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            return None, "⚠️ Gagal mengambil data. Periksa kode saham."
        return hist, None
    except Exception as e:
        return None, f"⚠️ Error: {e}"


def get_technical_data(hist):
    """
    Menghitung MA5, MA10, MA20, RSI dari data historis
    """
    if hist is None or hist.empty:
        return None, "Data kosong"

    closes = hist['Close']
    volumes = hist['Volume']

    if len(closes) < 20:
        return None, "⚠️ Data kurang dari 20 hari."

    ma5 = closes.rolling(window=5).mean()
    ma10 = closes.rolling(window=10).mean()
    ma20 = closes.rolling(window=20).mean()
    rsi = calculate_rsi(closes)

    return {
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "rsi": rsi,
        "current_price": closes.iloc[-1],
        "volume_today": int(volumes.iloc[-1]) if not np.isnan(volumes.iloc[-1]) else 0,
        "avg_volume_20": int(volumes.rolling(window=20).mean().iloc[-1]) if not np.isnan(volumes.rolling(window=20).mean().iloc[-1]) else 0,
        "hist": hist
    }, None


# ==================== ANALISIS TEKNIKAL ====================
def analyze_trend(current_price, ma5, ma10, ma20):
    if current_price > ma5 > ma10 > ma20:
        return "UPTREND KUAT (harga > MA5 > MA10 > MA20)"
    elif current_price > ma5 and ma5 > ma10 and current_price > ma20:
        return "UPTREND (harga di atas MA, MA5 > MA10)"
    elif current_price > ma5 and current_price > ma10 and current_price > ma20:
        return "UPTREND LEMAH (harga di atas semua MA, tapi urutan MA belum sempurna)"
    elif current_price < ma5 < ma10 < ma20:
        return "DOWNTREND KUAT (harga < MA5 < MA10 < MA20)"
    elif current_price < ma5 and current_price < ma10 and current_price < ma20:
        return "DOWNTREND LEMAH"
    else:
        return "SIDEWAYS / KONSOLIDASI"


def analyze_sr(current_price, support, resistance):
    if support and resistance:
        if current_price <= support:
            return f"⚠️ Harga di bawah atau menyentuh support ({support}). Potensi rebound atau breakdown."
        elif current_price >= resistance:
            return f"⚠️ Harga di atas atau menyentuh resistance ({resistance}). Potensi koreksi atau breakout."
        else:
            return f"Harga ({current_price}) di antara support ({support}) dan resistance ({resistance})."
    elif support:
        return f"Support di {support}, resistance tidak diberikan."
    elif resistance:
        return f"Resistance di {resistance}, support tidak diberikan."
    else:
        return "Support dan resistance tidak diberikan."


def analyze_volume(today_volume, avg_volume_20):
    if avg_volume_20 == 0:
        return "Volume rata-rata 20 hari tidak valid."
    ratio = today_volume / avg_volume_20
    if ratio > 2:
        return f"Volume hari ini = {today_volume:,}, rata-rata 20 hari = {avg_volume_20:,} → Rasio {ratio:.2f}x. Volume sangat tinggi. Breakout atau aksi bandar."
    elif ratio > 1.2:
        return f"Volume hari ini = {today_volume:,}, rata-rata 20 hari = {avg_volume_20:,} → Rasio {ratio:.2f}x. Volume di atas rata-rata. Minat meningkat."
    elif ratio < 0.5:
        return f"Volume hari ini = {today_volume:,}, rata-rata 20 hari = {avg_volume_20:,} → Rasio {ratio:.2f}x. Volume rendah. Sideways atau kurang minat."
    else:
        return f"Volume hari ini = {today_volume:,}, rata-rata 20 hari = {avg_volume_20:,} → Rasio {ratio:.2f}x. Volume normal."


def analyze_rsi(rsi):
    if rsi > 70:
        return f"RSI {rsi:.1f} → Overbought. Potensi koreksi."
    elif rsi < 30:
        return f"RSI {rsi:.1f} → Oversold. Potensi rebound."
    else:
        return f"RSI {rsi:.1f} → Netral."
