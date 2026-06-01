import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
import io
import os

# --- PAGE CONFIGURATION & UI THEME ---
st.set_page_config(page_title="Institutional Sniper v5.0", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .main-title { font-size: 40px; font-weight: 800; color: #00E676; margin-bottom: 0px; letter-spacing: 1px; }
    .sub-title { font-size: 16px; color: #90A4AE; margin-bottom: 30px; }
    .metric-card { background-color: #1E293B; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; }
    .stButton>button { border-radius: 8px; font-weight: 700; letter-spacing: 0.5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">⚡ INSTITUTIONAL SNIPER ENGINE v5.0</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Anti-Deadlock Sequential Engine & Browser-Spoofing Data Loader</p>', unsafe_allow_html=True)

# --- BULLETPROOF SECTOR DATA LOADER ---
@st.cache_data(ttl=86400)
def load_all_nse_segments():
    segments = {}
    
    # Disguise the app as a standard Google Chrome browser to bypass NSE blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def get_tickers(url, local_file):
        # Method 1: Try to read the local CSV if you uploaded it successfully
        if os.path.exists(local_file):
            try:
                df = pd.read_csv(local_file)
                return (df['Symbol'].astype(str).str.strip() + ".NS").tolist()
            except: pass
            
        # Method 2: If no local file, spoof a web browser and download it live
        try:
            res = requests.get(url, headers=headers, timeout=5)
            df = pd.read_csv(io.StringIO(res.text))
            return (df['Symbol'].astype(str).str.strip() + ".NS").tolist()
        except:
            return []

    segments["NIFTY 50 (Mega Cap)"] = get_tickers("https://archives.nseindia.com/content/indices/ind_nifty50list.csv", "ind_nifty50list.csv")
    segments["NIFTY 100 (Large Cap)"] = get_tickers("https://archives.nseindia.com/content/indices/ind_nifty100list.csv", "ind_nifty100list.csv")
    segments["NIFTY Midcap 100"] = get_tickers("https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv", "ind_niftymidcap100list.csv")
    segments["NIFTY Smallcap 250"] = get_tickers("https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv", "ind_niftysmallcap250list.csv")
    segments["Full NIFTY 500"] = get_tickers("https://archives.nseindia.com/content/indices/ind_nifty500list.csv", "ind_nifty500list.csv")
    
    # Method 3: Ultimate Fallback just in case everything fails
    fallback = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "TATAMOTORS.NS", "SBIN.NS", "ITC.NS"]
    for k in list(segments.keys()):
        if not segments[k]:
            segments[k] = fallback
            
    return segments

all_segments = load_all_nse_segments()

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("🎛️ Strategic Controls")
    market_segment = st.selectbox("🎯 Select Market Segment", list(all_segments.keys()))
    scan_range = st.radio("Scan Target Length", ["Full Segment Scan", "Quick Test (First 5 Stocks)"])
    
    st.divider()
    st.markdown("### 📈 Trading Profile Pre-sets")
    profile = st.selectbox("Choose Profile", ["Custom", "Intraday Trading", "Swing Trading", "Long-Term Investing"])
    
    if profile == "Intraday Trading":
        timeframe = st.selectbox("⏳ Timeframe", ["15m", "75m", "125m"])
    elif profile == "Swing Trading":
        timeframe = st.selectbox("⏳ Timeframe", ["1d", "1wk"])
    elif profile == "Long-Term Investing":
        timeframe = st.selectbox("⏳ Timeframe", ["1wk", "1mo", "3mo"])
    else:
        timeframe = st.selectbox("⏳ Timeframe", ["15m", "75m", "125m", "1d", "1wk", "1mo", "3mo"])
        
    zone_type = st.selectbox("📉 Order Type", ["Bullish Demand Zone", "Bearish Supply Zone"])
    
    st.divider()
    st.markdown("### 🎯 Zone State Filter")
    state_filter = st.selectbox("Filter by Zone Condition", [
        "All Valid Zones",
        "Just Approaching (Nearing Edge)",
        "In the Zone (1-6 Candles Formed)",
        "Unmitigated (100% Completely Fresh)"
    ])
    
    st.divider()
    st.markdown("### 🕯️ Advanced Candle Strictness")
    base_limit = st.slider("Max Base Candles Allowed", 1, 6, 4)
    min_legout = st.slider("Min Leg-Out Candles Required", 1, 4, 2)
    min_legout_size_pct = st.slider("Minimum Leg-Out Candle Body Size (%)", 51, 100, 55)

base_list = all_segments[market_segment]
symbols_to_scan = base_list[:5] if "Quick Test" in scan_range else base_list

# --- RESAMPLING HELPER ---
def resample_dataframe(df, tf):
    if len(df) < 20: return None
    if tf in ["75m", "125m"]:
        group_size = 5 if tf == "75m" else 25
        df['Date'] = df.index.date
        df['block'] = df.groupby('Date').cumcount() // group_size
        
        resampled = df.groupby(['Date', 'block']).agg({
            'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'
        }).dropna()
        
        resampled.index = df.groupby(['Date', 'block']).apply(lambda x: x.index[0])
        return resampled
    return df

# --- ANTI-DEADLOCK SEQUENTIAL DOWNLOADER ---
@st.cache_data(ttl=600)
def fetch_safe_sequential_data(tickers, tf):
    if tf in ["15m", "75m", "125m"]:
        period, interval = '60d', '15m' if tf != "125m" else '5m'
    elif tf in ["1d", "1wk"]:
        period, interval = '3y', tf
    else:
        period, interval = '10y', tf

    processed_dict = {}
    holder = st.empty()
    
    # We loop through ONE by ONE to ensure Yahoo Finance never freezes the connection
    for i, ticker in enumerate(tickers):
        holder.info(f"Downloading historical data for {ticker} ({i+1}/{len(tickers)})...")
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval, timeout=3)
            if not df.empty and len(df) >= 20:
                resampled = resample_dataframe(df, tf)
                if resampled is not None:
                    processed_dict[ticker] = resampled
        except Exception:
            pass # Silently skip broken tickers instead of freezing
            
        time.sleep(0.1) # A tiny breathing pause to respect Yahoo's servers
        
    holder.empty()
    return processed_dict

# --- CORE STRICT ALGORITHM ENGINE ---
def scan_zones(ticker, df, mode, max_base, min_leg, min_size_threshold):
    try:
        current_price = round(df['Close'].iloc[-1], 2)
        
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['Range'] = df['High'] - df['Low']
        df['Range'] = np.where(df['Range'] == 0, 0.0001, df['Range'])
        df['Body_Pct'] = (df['Body'] / df['Range']) * 100.0
        
        df['Is_Base'] = df['Body_Pct'] < 50.0
        
        ratio_threshold = float(min_size_threshold)
        if mode == "Bullish Demand Zone":
            df['Is_Strong'] = (df['Close'] > df['Open']) & (df['Body_Pct'] >= ratio_threshold)
        else:
            df['Is_Strong'] = (df['Close'] < df['Open']) & (df['Body_Pct'] >= ratio_threshold)
            
        matches = []
        i = 1
        while i < len(df) - min_leg - 1:
            if df['Is_Base'].iloc[i]:
                base_start = i
                base_end = i
                while base_end + 1 < len(df) and df['Is_Base'].iloc[base_end + 1]:
                    base_end += 1
                
                base_count = base_end - base_start + 1
                if base_count <= max_base:
                    legout_start = base_end + 1
                    legout_count = 0
                    while legout_start + legout_count < len(df) and df['Is_Strong'].iloc[legout_start + legout_count]:
                        legout_count += 1
                        
                    if legout_count >= min_leg:
                        future_data = df.iloc[legout_start + legout_count :]
                        
                        if mode == "Bullish Demand Zone":
                            z_ceil = round(max(df['Open'].iloc[base_start : base_end + 1].max(), df['Close'].iloc[base_start : base_end + 1].max()), 2)
                            z_floor = round(df['Low'].iloc[base_start : base_end + 1].min(), 2)
                            
                            zone_size = abs(z_ceil - z_floor) if abs(z_ceil - z_floor) != 0 else 0.01
                            penetration_limit = z_ceil - (zone_size * 0.10)
                            
                            if future_data.empty:
                                state = "Unmitigated 🟢"
                            else:
                                lowest_since = future_data['Low'].min()
                                if lowest_since < penetration_limit:
                                    state = "Deeply Mitigated 🔴"
                                elif lowest_since <= z_ceil:
                                    candles_in_zone = ((future_data['Low'] <= z_ceil) & (future_data['High'] >= z_floor)).sum()
                                    state = "In the Zone (1-6 Candles) 🟡" if 1 <= candles_in_zone <= 6 else "Deeply Mitigated 🔴"
                                else:
                                    state = "Unmitigated 🟢"
                                    
                            proximity = "Just Approaching 🎯" if state == "Unmitigated 🟢" and (z_ceil < current_price <= z_ceil * 1.015) else ("Inside Zone ⚡" if "In the Zone" in state else "Normal")
                                
                        else: # Bearish Supply Zone
                            z_ceil = round(df['High'].iloc[base_start : base_end + 1].max(), 2)
                            z_floor = round(min(df['Open'].iloc[base_start : base_end + 1].min(), df['Close'].iloc[base_start : base_end + 1].min()), 2)
                            
                            zone_size = abs(z_ceil - z_floor) if abs(z_ceil - z_floor) != 0 else 0.01
                            penetration_limit = z_floor + (zone_size * 0.10)
                            
                            if future_data.empty:
                                state = "Unmitigated 🟢"
                            else:
                                highest_since = future_data['High'].max()
                                if highest_since > penetration_limit:
                                    state = "Deeply Mitigated 🔴"
                                elif highest_since >= z_floor:
                                    candles_in_zone = ((future_data['High'] >= z_floor) & (future_data['Low'] <= z_ceil)).sum()
                                    state = "In the Zone (1-6 Candles) 🟡" if 1 <= candles_in_zone <= 6 else "Deeply Mitigated 🔴"
                                else:
                                    state = "Unmitigated 🟢"
                                    
                            proximity = "Just Approaching 🎯" if state == "Unmitigated 🟢" and (z_floor * 0.985 <= current_price < z_floor) else ("Inside Zone ⚡" if "In the Zone" in state else "Normal")

                        if state != "Deeply Mitigated 🔴":
                            date_detected = df.index[legout_start].strftime('%Y-%m-%d %H:%M') if hasattr(df.index[legout_start], 'strftime') else str(df.index[legout_start])
                            matches.append({
                                "Ticker": ticker.replace('.NS', ''),
                                "Formation Date": date_detected,
                                "Leg-Out Count": legout_count,
                                "Leg-Out Strength": f"{round(df['Body_Pct'].iloc[legout_start], 1)}%",
                                "Base": base_count,
                                "Proximal (Ceiling)": z_ceil,
                                "Distal (Floor)": z_floor,
                                "Current Price": current_price,
                                "Zone State": state,
                                "Live Alignment": proximity
                            })
                i = legout_start + legout_count
            else:
                i += 1
        return matches
    except:
        return None

# --- SCANNER RUNNER EXECUTION ---
if st.button("🔍 Run Institutional Alignment Scan", type="primary", use_container_width=True):
    results = []
    
    # 1. SEQUENTIAL DOWNLOAD PHASE (Bypasses the freeze)
    all_market_data = fetch_safe_sequential_data(symbols_to_scan, timeframe)
    
    if not all_market_data:
        st.error("Network streaming failed. Please check your internet connection or try again.")
    else:
        # 2. LOCAL CALCULATION PHASE
        progress_bar = st.progress(0, text="Evaluating institutional zone strictness...")
        total_symbols = len(symbols_to_scan)
        
        for idx, ticker in enumerate(symbols_to_scan):
            progress_bar.progress((idx + 1) / total_symbols, text=f"Analyzing {ticker} Structure ({idx+1}/{total_symbols})...")
            
            if ticker in all_market_data:
                res = scan_zones(ticker, all_market_data[ticker], zone_type, base_limit, min_legout, min_legout_size_pct)
                if res:
                    results.extend(res)
                
        progress_bar.empty()
        
        if results:
            df_display = pd.DataFrame(results)
            df_display = df_display.sort_values(by="Formation Date", ascending=False).drop_duplicates(subset=["Ticker"], keep="first")
            
            if state_filter == "Just Approaching (Nearing Edge)":
                df_display = df_display[df_display['Live Alignment'] == "Just Approaching 🎯"]
            elif state_filter == "In the Zone (1-6 Candles Formed)":
                df_display = df_display[df_display['Zone State'] == "In the Zone (1-6 Candles) 🟡"]
            elif state_filter == "Unmitigated (100% Completely Fresh)":
                df_display = df_display[df_display['Zone State'] == "Unmitigated 🟢"]
                
            if df_display.empty:
                st.warning("No institutional zones matched your exact state filter conditions at this moment.")
            else:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"<div class='metric-card'><b>Total Formations:</b><br><span style='font-size:24px;'>{len(df_display)}</span></div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div class='metric-card' style='border-left-color:#00E676;'><b>100% Unmitigated:</b><br><span style='font-size:24px;'>{len(df_display[df_display['Zone State'] == 'Unmitigated 🟢'])}</span></div>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<div class='metric-card' style='border-left-color:#FFD600;'><b>Active Plays:</b><br><span style='font-size:24px;'>{len(df_display[df_display['Live Alignment'] != 'Normal'])}</span></div>", unsafe_allow_html=True)
                    
                st.markdown("<br>", unsafe_allow_html=True)
                
                def highlight_live_state(val):
                    if "Approaching" in str(val): return 'background-color: #1B5E20; color: white;'
                    if "Inside" in str(val): return 'background-color: #E65100; color: white;'
                    return ''
                    
                st.dataframe(
                    df_display.style.map(highlight_live_state, subset=['Live Alignment']),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.warning("No institutional setups detected matching these core settings within the selected market segment.")
