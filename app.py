import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os

# --- PAGE CONFIGURATION & UI THEME ---
st.set_page_config(page_title="Institutional Sniper Premium v12.0", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: 800; color: #00E676; margin-bottom: 0px; }
    .sub-title { font-size: 15px; color: #90A4AE; margin-bottom: 25px; }
    .metric-card { background-color: #1E293B; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; }
    .stButton>button { border-radius: 8px; font-weight: 700; background-color: #00E676 !important; color: black !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🎯 ONE-CLICK INSTITUTIONAL SCANNER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Simplified Delivery & Macro Structure Engine (No Broker Login Required)</p>', unsafe_allow_html=True)

# --- LOCAL SECTOR DATA LOADER ---
@st.cache_data(ttl=86400)
def load_all_nse_segments():
    segments = {}
    def get_tickers(local_file):
        if os.path.exists(local_file):
            try:
                df = pd.read_csv(local_file)
                # Append .NS extension for standard Yahoo Finance formatting
                return (df['Symbol'].astype(str).str.strip() + ".NS").tolist()
            except: pass
        return []

    segments["NIFTY 50 (Mega Cap)"] = get_tickers("ind_nifty50list.csv")
    segments["NIFTY 100 (Large Cap)"] = get_tickers("ind_nifty100list.csv")
    segments["NIFTY Midcap 100"] = get_tickers("ind_niftymidcap100list.csv")
    segments["NIFTY Smallcap 250"] = get_tickers("ind_niftysmallcap250list.csv")
    segments["Full NIFTY 500"] = get_tickers("ind_nifty500list.csv")
    
    fallback = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "TATAMOTORS.NS", "SBIN.NS", "ITC.NS"]
    for k in list(segments.keys()):
        if not segments[k]: segments[k] = fallback
    return segments

all_segments = load_all_nse_segments()

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("🎛️ Scanner Settings")
    market_segment = st.selectbox("🎯 Select Market Segment", list(all_segments.keys()))
    scan_range = st.radio("Scan Range", ["Full Segment Scan", "Quick Test (First 5 Stocks)"])
    
    st.divider()
    # PURE DELIVERY & MACRO RESOLUTION ONLY (NO INTRADAY)
    tf_display = st.selectbox("⏳ Timeframe Chart", ["1D (Daily)", "1W (Weekly)", "1M (Monthly)", "3M (Quarterly)", "6M (Half-Yearly)", "1Y (Yearly)"])
    
    zone_type = st.selectbox("📉 Order Type", ["Bullish Demand Zone", "Bearish Supply Zone"])
    state_filter = st.selectbox("Filter by Zone Condition", ["All Valid Zones", "Just Approaching (Nearing Edge)", "In the Zone (1-6 Candles Formed)", "Unmitigated (100% Completely Fresh)"])
    
    st.divider()
    st.markdown("### 🕯️ Advanced Candle Rules")
    base_limit = st.slider("Max Base Candles Allowed", 1, 6, 4)
    min_legout = st.slider("Min Leg-Out Candles Required", 1, 4, 2)
    min_legout_size_pct = st.slider("Minimum Leg-Out Candle Body Size (%)", 51, 100, 55)

base_list = all_segments[market_segment]
symbols_to_scan = base_list[:5] if "Quick Test" in scan_range else base_list

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

# --- CORE SCANNING ENGINE ---
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

# --- INSTANT RUN ELEMENT ---
if st.button("⚡ RUN NATIVE LIVE MARKET SCAN", type="primary", use_container_width=True):
    results = []
    
    # Map selection to native parameters
    if tf_display == "1D (Daily)": period, interval = "3y", "1d"
    elif tf_display == "1W (Weekly)": period, interval = "5y", "1wk"
    else: period, interval = "max", "1mo" # Used for 1M, 3M, 6M, and 1Y analytics

    with st.spinner(f"Downloading matrix data package for {len(symbols_to_scan)} charts simultaneously..."):
        try:
            raw_data = yf.download(
                tickers=symbols_to_scan,
                period=period,
                interval=interval,
                group_by='ticker',
                threads=True,
                progress=False,
                timeout=15
            )
        except Exception as e:
            st.error(f"Data stream connection interrupted. Please try clicking the button again. Info: {e}")
            st.stop()

    if raw_data.empty:
        st.error("Data matrix came back blank from the exchange. Please tap scan again.")
    else:
        # Re-index single ticker inputs to match MultiIndex matrix standard
        if len(symbols_to_scan) == 1:
            raw_data.columns = pd.MultiIndex.from_product([[symbols_to_scan[0]], raw_data.columns])

        progress_bar = st.progress(0, text="Analyzing downloaded chart parameters locally...")
        total_symbols = len(symbols_to_scan)
        
        for idx, ticker in enumerate(symbols_to_scan):
            progress_bar.progress((idx + 1) / total_symbols, text=f"Analyzing {ticker.replace('.NS','')} Local Data...")
            
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
            
            if df_display.empty: st.warning("No active institutional zones match your exact state selection right now.")
            else:
                st.markdown(f"### 📈 Real-Time Setup Matrix ({len(df_display)} Positions Uncovered)")
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning("No institutional setups detected matching these current parameters.")
