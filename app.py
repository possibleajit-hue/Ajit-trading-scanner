import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import io
import requests

# --- ENTERPRISE NETWORK SESSION SETUP ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
})

# --- PAGE CONFIGURATION & UI THEME ---
st.set_page_config(page_title="Institutional Sniper Master v16.0", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: 800; color: #00E676; margin-bottom: 0px; letter-spacing: 0.5px; }
    .sub-title { font-size: 15px; color: #90A4AE; margin-bottom: 25px; }
    .metric-card { background-color: #1E293B; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; }
    .status-panel { background-color: #0F172A; border: 1px solid #1E293B; padding: 15px; border-radius: 8px; margin-bottom: 25px; }
    .stButton>button { border-radius: 8px; font-weight: 700; background-color: #00E676 !important; color: black !important; width: 100%; height: 50px; font-size: 16px; letter-spacing: 0.5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🎯 ONE-CLICK NATIVE MACRO SCANNER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Multi-Threaded Parallel Cloud Architecture — No Local Files or Logins Required</p>', unsafe_allow_html=True)

# --- CLOUD LIVE TICKER FETCH MATRIX ---
@st.cache_data(ttl=43200) # Caches for 12 hours to stay incredibly fast
def fetch_live_index_constituents():
    segments = {}
    
    def download_nse_csv(url):
        try:
            response = session.get(url, timeout=8)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                df.columns = [str(c).strip() for c in df.columns]
                
                symbol_col = None
                for col in df.columns:
                    if 'symbol' in col.lower() or 'ticker' in col.lower():
                        symbol_col = col
                        break
                if symbol_col is None and not df.empty:
                    symbol_col = df.columns[0]
                    
                if symbol_col in df.columns:
                    raw_tickers = df[symbol_col].dropna().astype(str).str.strip().tolist()
                    return [f"{t.upper().replace('.NS','')}.NS" for t in raw_tickers if t and t.upper() not in ["SYMBOL", "TICKER"]]
        except:
            pass
        return []

    # Stream real-time lists directly from the official index index directories
    segments["NIFTY 50 (Mega Cap)"] = download_nse_csv("https://archives.nseindia.com/content/indices/ind_nifty50list.csv")
    segments["NIFTY 100 (Large Cap)"] = download_nse_csv("https://archives.nseindia.com/content/indices/ind_nifty100list.csv")
    segments["NIFTY Midcap 100"] = download_nse_csv("https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv")
    segments["NIFTY 500 (Full Market Matrix)"] = download_nse_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")
    
    # Solid structural backup system to prevent blank views under internet dropouts
    emergency_fallback = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "TATAMOTORS.NS", "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "LT.NS"]
    for segment_name in list(segments.keys()):
        if not segments[segment_name] or len(segments[segment_name]) < 5:
            segments[segment_name] = emergency_fallback
            
    return segments

# Synchronize segments with cloud databases
all_index_segments = fetch_live_index_constituents()

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("🎛️ Strategic Controls")
    market_segment = st.selectbox("🎯 Target Index Segment", list(all_index_segments.keys()))
    scan_range = st.radio("Scan Scope Profile", ["Full Segment Scan", "Quick Test (First 5 Stocks)"])
    
    st.divider()
    tf_display = st.selectbox("⏳ Timeframe Horizon", ["1D (Daily)", "1W (Weekly)", "1M (Monthly)", "3M (Quarterly)", "6M (Half-Yearly)", "1Y (Yearly)"])
    zone_type = st.selectbox("📉 Strategy Mode", ["Bullish Demand Zone", "Bearish Supply Zone"])
    state_filter = st.selectbox("Zone State Filter", ["All Valid Zones", "Just Approaching (Nearing Edge)", "In the Zone (1-6 Candles Formed)", "Unmitigated (100% Completely Fresh)"])
    
    st.divider()
    st.markdown("### 🕯️ Advanced Candle Rules")
    base_limit = st.slider("Max Base Candles Allowed", 1, 6, 4)
    min_legout = st.slider("Min Leg-Out Candles Required", 1, 4, 2)
    min_legout_size_pct = st.slider("Minimum Leg-Out Candle Body Size (%)", 51, 100, 55)

symbols_to_scan = all_index_segments[market_segment]
if "Quick Test" in scan_range:
    symbols_to_scan = symbols_to_scan[:5]

# --- VISUAL INTERFACE TELEMETRY PANEL ---
st.markdown(f"""
<div class="status-panel">
    🌐 <b>Live Connection Matrix Status:</b> Connected to server registries.<br>
    📈 <b>Selected Universe Content:</b> Loaded <b>{len(all_index_segments[market_segment])}</b> official stock positions for <b>{market_segment}</b>.<br>
    ⚡ <b>Engine Run Status:</b> Press the button below to stream data and scan <b>{len(symbols_to_scan)}</b> active assets simultaneously.
</div>
""", unsafe_allow_html=True)

# --- LOCAL CALENDAR MACRO RESAMPLER ---
def resample_dataframe(df, tf_disp):
    if df.empty or len(df) < 3: return None
    if tf_disp == "3M (Quarterly)":
        return df.resample("3ME").agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    elif tf_disp == "6M (Half-Yearly)":
        return df.resample("6ME").agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    elif tf_disp == "1Y (Yearly)":
        return df.resample("YE").agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    return df

# --- CORE ALGORITHM COMPUTATION ENGINE ---
def scan_zones(ticker, df, mode, max_base, min_leg, min_size_threshold):
    try:
        current_price = round(df['Close'].iloc[-1], 2)
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['Range'] = np.where((df['High'] - df['Low']) == 0, 0.0001, df['High'] - df['Low'])
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
                base_start, base_end = i, i
                while base_end + 1 < len(df) and df['Is_Base'].iloc[base_end + 1]:
                    base_end += 1
                
                base_count = base_end - base_start + 1
                if base_count <= max_base:
                    legout_start, legout_count = base_end + 1, 0
                    while legout_start + legout_count < len(df) and df['Is_Strong'].iloc[legout_start + legout_count]:
                        legout_count += 1
                        
                    if legout_count >= min_leg:
                        future_data = df.iloc[legout_start + legout_count :]
                        
                        if mode == "Bullish Demand Zone":
                            z_ceil = round(max(df['Open'].iloc[base_start : base_end + 1].max(), df['Close'].iloc[base_start : base_end + 1].max()), 2)
                            z_floor = round(df['Low'].iloc[base_start : base_end + 1].min(), 2)
                            zone_size = abs(z_ceil - z_floor) if abs(z_ceil - z_floor) != 0 else 0.01
                            penetration_limit = z_ceil - (zone_size * 0.10)
                            
                            if future_data.empty: state = "Unmitigated 🟢"
                            else:
                                lowest_since = future_data['Low'].min()
                                if lowest_since < penetration_limit: state = "Deeply Mitigated 🔴"
                                elif lowest_since <= z_ceil:
                                    candles_in_zone = ((future_data['Low'] <= z_ceil) & (future_data['High'] >= z_floor)).sum()
                                    state = "In the Zone (1-6 Candles) 🟡" if 1 <= candles_in_zone <= 6 else "Deeply Mitigated 🔴"
                                else: state = "Unmitigated 🟢"
                            proximity = "Just Approaching 🎯" if state == "Unmitigated 🟢" and (z_ceil < current_price <= z_ceil * 1.015) else ("Inside Zone ⚡" if "In the Zone" in state else "Normal")
                                
                        else: # Bearish Supply Zone
                            z_ceil = round(df['High'].iloc[base_start : base_end + 1].max(), 2)
                            z_floor = round(min(df['Open'].iloc[base_start : base_end + 1].min(), df['Close'].iloc[base_start : base_end + 1].min()), 2)
                            zone_size = abs(z_ceil - z_floor) if abs(z_ceil - z_floor) != 0 else 0.01
                            penetration_limit = z_floor + (zone_size * 0.10)
                            
                            if future_data.empty: state = "Unmitigated 🟢"
                            else:
                                highest_since = future_data['High'].max()
                                if highest_since > penetration_limit: state = "Deeply Mitigated 🔴"
                                elif highest_since >= z_floor:
                                    candles_in_zone = ((future_data['High'] >= z_floor) & (future_data['Low'] <= z_ceil)).sum()
                                    state = "In the Zone (1-6 Candles) 🟡" if 1 <= candles_in_zone <= 6 else "Deeply Mitigated 🔴"
                                else: state = "Unmitigated 🟢"
                            proximity = "Just Approaching 🎯" if state == "Unmitigated 🟢" and (z_floor * 0.985 <= current_price < z_floor) else ("Inside Zone ⚡" if "In the Zone" in state else "Normal")

                        if state != "Deeply Mitigated 🔴":
                            matches.append({
                                "Ticker": ticker.replace('.NS', ''), "Formation Date": df.index[legout_start].strftime('%Y-%m-%d'),
                                "Leg-Out Count": legout_count, "Leg-Out Strength": f"{round(df['Body_Pct'].iloc[legout_start], 1)}%",
                                "Base": base_count, "Proximal (Ceiling)": z_ceil, "Distal (Floor)": z_floor,
                                "Current Price": current_price, "Zone State": state, "Live Alignment": proximity
                            })
                i = legout_start + legout_count
            else: i += 1
        return matches
    except: return None

# --- PARALLEL EXECUTION TRIGGER BLOCK ---
if st.button("⚡ RUN NATIVE LIVE MARKET SCAN", type="primary", use_container_width=True):
    results = []
    
    # Establish dynamic time depth depending on macro horizon
    if tf_display == "1D (Daily)": period, interval = "3y", "1d"
    elif tf_display == "1W (Weekly)": period, interval = "5y", "1wk"
    else: period, interval = "max", "1mo"

    # SINGLE PASS SECURE PARALLEL BATCH DOWNLOAD
    with st.spinner(f"Downloading high-speed multi-threaded chart packets for all {len(symbols_to_scan)} stocks..."):
        try:
            raw_data = yf.download(
                tickers=symbols_to_scan,
                period=period,
                interval=interval,
                group_by='ticker',
                threads=True,
                progress=False,
                session=session,
                timeout=25
            )
        except Exception as e:
            st.error(f"Cloud connection dropped by the exchange gateways. Please tap scan again. Info: {e}")
            st.stop()

    if raw_data.empty:
        st.error("Data packet came back blank. Please try running the scan again.")
    else:
        if len(symbols_to_scan) == 1:
            raw_data.columns = pd.MultiIndex.from_product([[symbols_to_scan[0]], raw_data.columns])

        progress_bar = st.progress(0, text="Executing math matrices internally...")
        total_symbols = len(symbols_to_scan)
        
        # Local loops iterate inside system RAM (Cannot lock up or freeze)
        for idx, ticker in enumerate(symbols_to_scan):
            progress_bar.progress((idx + 1) / total_symbols, text=f"Processing {ticker.replace('.NS','')} Matrix ({idx+1}/{total_symbols})...")
            
            if ticker in raw_data.columns.get_level_values(0):
                df = raw_data[ticker].dropna(how='all').copy()
                if len(df) >= 5:
                    processed_df = resample_dataframe(df, tf_display)
                    if processed_df is not None and not processed_df.empty:
                        res = scan_zones(ticker, processed_df, zone_type, base_limit, min_legout, min_legout_size_pct)
                        if res: results.extend(res)
                        
        progress_bar.empty()
        
        if results:
            df_display = pd.DataFrame(results).sort_values(by="Formation Date", ascending=False).drop_duplicates(subset=["Ticker"], keep="first")
            
            if state_filter == "Just Approaching (Nearing Edge)": df_display = df_display[df_display['Live Alignment'] == "Just Approaching 🎯"]
            elif state_filter == "In the Zone (1-6 Candles Formed)": df_display = df_display[df_display['Zone State'] == "In the Zone (1-6 Candles) 🟡"]
            elif state_filter == "Unmitigated (100% Completely Fresh)": df_display = df_display[df_display['Zone State'] == "Unmitigated 🟢"]
            
            if df_display.empty: 
                st.warning("No active institutional blocks match your exact selection filter right now.")
            else:
                c1, c2, c3 = st.columns(3)
                with c1: st.markdown(f"<div class='metric-card'><b>Total Formations:</b><br><span style='font-size:24px;'>{len(df_display)}</span></div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='metric-card' style='border-left-color:#00E676;'><b>100% Unmitigated:</b><br><span style='font-size:24px;'>{len(df_display[df_display['Zone State'] == 'Unmitigated 🟢'])}</span></div>", unsafe_allow_html=True)
                with c3: st.markdown(f"<div class='metric-card' style='border-left-color:#FFD600;'><b>Active Plays:</b><br><span style='font-size:24px;'>{len(df_display[df_display['Live Alignment'] != 'Normal'])}</span></div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning("No supply or demand zones matching your parameters were found.")
