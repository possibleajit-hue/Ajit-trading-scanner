import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# --- PAGE SETUP & COLORS ---
st.set_page_config(page_title="Pro Institutional Scanner", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .main-title { font-size: 42px; font-weight: 800; color: #1E88E5; margin-bottom: 0px; }
    .sub-title { font-size: 18px; color: #607D8B; margin-bottom: 25px; }
    .stProgress .st-bo { background-color: #1E88E5; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">⚡ Elite Institutional Zone Scanner</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Sniper Engine: Approaching & First-Touch / Light-Touch Filtering.</p>', unsafe_allow_html=True)

# --- AUTOMATED NIFTY 500 SEGMENT LOADER ---
@st.cache_data(ttl=86400)
def load_nifty_segments():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df = pd.read_csv(url)
        df['Ticker'] = df['Symbol'].astype(str).str.strip() + ".NS"
        
        nifty100 = df.head(100)['Ticker'].tolist()
        midcap150 = df.iloc[100:250]['Ticker'].tolist()
        smallcap250 = df.iloc[250:]['Ticker'].tolist()
        full500 = df['Ticker'].tolist()
        
        return {"Full NIFTY 500": full500, "NIFTY 100 (Large Cap)": nifty100, "NIFTY Midcap 150": midcap150, "NIFTY Smallcap 250": smallcap250}
    except Exception:
        fallback = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "TATAMOTORS.NS", "ITC.NS", "SBIN.NS"]
        return {"Full NIFTY 500": fallback, "NIFTY 100 (Large Cap)": fallback}

segments = load_nifty_segments()

# --- SIDEBAR CONTROL MENU ---
with st.sidebar:
    st.header("🎛️ Scanner Settings")
    market_segment = st.selectbox("🎯 Select Market Segment", list(segments.keys()))
    scan_mode = st.radio("Scan Range", ["Full Segment Scan", "Test Scan (First 5 Stocks)"])
    
    st.divider()
    timeframe = st.selectbox("⏳ Timeframe", ["1d", "1wk", "1mo", "3mo", "6mo", "12mo"])
    zone_type = st.selectbox("📈 Zone Type", ["Bullish Demand Zone", "Bearish Supply Zone"])
    
    st.divider()
    st.markdown("### 🎯 Sniper Action Filter")
    # THE NEW SNIPER TOGGLE
    only_approaching_fresh = st.checkbox("Show ONLY 'Approaching & Valid' Zones", value=False, help="Hides deeply mitigated zones. Shows only Completely Fresh zones OR zones with a previous 'Light Touch', where price is approaching today.")
    
    # NEW SLIDER: Define what a "Light Touch" is
    mitigation_tolerance = st.slider("Max Previous Zone Penetration Allowed (%)", 1, 50, 25, help="If a previous touch went deeper than this % into the zone, it is considered 'Deeply Mitigated' and invalid. If it touched but stayed above this %, it is a 'Light Touch' and still valid.")
    
    st.divider()
    st.markdown("### 🕯️ Candle Strictness")
    base_limit = st.slider("Max Base Candles Allowed", 1, 6, 5)
    min_legout, max_legout = st.slider("Leg-Out Candles (Min - Max)", 1, 6, (1, 3))
    min_leg_pct, max_leg_pct = st.slider("Leg-Out Body Size (%)", 51, 100, (60, 100))

base_list = segments[market_segment]
symbols_to_scan = base_list[:5] if "Test" in scan_mode else base_list

# --- CORE MATRICES ALGORITHM ---
def scan_zones(ticker, tf, mode, max_base, min_leg, max_leg, min_leg_pct, max_leg_pct, tolerance):
    try:
        t = yf.Ticker(ticker)
        if tf in ["6mo", "12mo"]:
            df = t.history(period='15y', interval='1mo', timeout=1.5)
            if len(df) < 12: return None
            df['Year'] = df.index.year
            if tf == "6mo":
                df['Half'] = (df.index.month - 1) // 6
                df = df.groupby(['Year', 'Half']).agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'})
                df.index = [pd.Timestamp(year=y, month=1 if h==0 else 7, day=1) for y, h in df.index]
            else:
                df = df.groupby('Year').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'})
                df.index = [pd.Timestamp(year=y, month=1, day=1) for y in df.index]
        else:
            df = t.history(period='10y', interval=tf, timeout=1.5)
            if len(df) < 15: return None
        
        current_price = round(df['Close'].iloc[-1], 2)
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['Range'] = df['High'] - df['Low']
        
        df['Is_Base'] = df['Body'] < (0.5 * df['Range'])
        
        min_body_req = (min_leg_pct / 100.0) * df['Range']
        max_body_req = (max_leg_pct / 100.0) * df['Range']
        
        if mode == "Bullish Demand Zone":
            df['Is_Strong'] = (df['Close'] > df['Open']) & (df['Body'] >= min_body_req) & (df['Body'] <= max_body_req)
        else:
            df['Is_Strong'] = (df['Close'] < df['Open']) & (df['Body'] >= min_body_req) & (df['Body'] <= max_body_req)
            
        matches = []
        i = 1
        while i < len(df) - min_leg:
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
                        
                    if min_leg <= legout_count <= max_leg:
                        leg_in_idx = base_start - 1
                        if leg_in_idx >= 0:
                            base_opens = df['Open'].iloc[base_start : base_end + 1]
                            base_closes = df['Close'].iloc[base_start : base_end + 1]
                            
                            future_data = df.iloc[legout_start + legout_count : -1]
                            
                            if mode == "Bullish Demand Zone":
                                leg_in_bullish = df['Close'].iloc[leg_in_idx] > df['Open'].iloc[leg_in_idx]
                                pattern = "RBR 🚀" if leg_in_bullish else "DBR 📉🚀"
                                
                                z_ceil = round(max(base_opens.max(), base_closes.max()), 2)
                                z_floor = round(df['Low'].iloc[base_start : base_end + 1].min(), 2)
                                zone_size = z_ceil - z_floor
                                penetration_limit = z_ceil - (zone_size * (tolerance / 100.0))
                                
                                # Deep Mitigation vs Light Touch Logic
                                if future_data.empty:
                                    status = "Completely Fresh 🟢"
                                else:
                                    lowest_since = future_data['Low'].min()
                                    if lowest_since < penetration_limit:
                                        status = "Deeply Mitigated 🔴"
                                    elif lowest_since <= z_ceil:
                                        status = "Light Touch 🟡"
                                    else:
                                        status = "Completely Fresh 🟢"
                                
                                # Action Status: Is it approaching now, and is it valid?
                                if current_price <= (z_ceil * 1.03) and current_price >= penetration_limit:
                                    action_status = "Approaching / Valid 🎯"
                                else:
                                    action_status = "Away or Invalid ⏳"
                                    
                            else:
                                leg_in_bearish = df['Close'].iloc[leg_in_idx] < df['Open'].iloc[leg_in_idx]
                                pattern = "DBD 🩸" if leg_in_bearish else "RBD 🚀🩸"
                                
                                z_ceil = round(df['High'].iloc[base_start : base_end + 1].max(), 2)
                                z_floor = round(min(base_opens.min(), base_closes.min()), 2)
                                zone_size = z_ceil - z_floor
                                penetration_limit = z_floor + (zone_size * (tolerance / 100.0))
                                
                                # Deep Mitigation vs Light Touch Logic
                                if future_data.empty:
                                    status = "Completely Fresh 🟢"
                                else:
                                    highest_since = future_data['High'].max()
                                    if highest_since > penetration_limit:
                                        status = "Deeply Mitigated 🔴"
                                    elif highest_since >= z_floor:
                                        status = "Light Touch 🟡"
                                    else:
                                        status = "Completely Fresh 🟢"
                                
                                # Action Status
                                if current_price >= (z_floor * 0.97) and current_price <= penetration_limit:
                                    action_status = "Approaching / Valid 🎯"
                                else:
                                    action_status = "Away or Invalid ⏳"

                            date_detected = df.index[legout_start].strftime('%Y-%m-%d') if hasattr(df.index[legout_start], 'strftime') else str(df.index[legout_start])
                            matches.append({
                                "Ticker": ticker.replace('.NS', ''),
                                "Date Detected": date_detected,
                                "Zone Status": status,
                                "Exact Pattern": pattern,
                                "Base Candles": base_count,
                                "Leg-Outs": legout_count,
                                "Ceiling (Proximal)": z_ceil,
                                "Floor (Distal)": z_floor,
                                "Current Price": current_price,
                                "Trade Status": action_status
                            })
                i = base_end + 1
            else:
                i += 1
        return matches
    except Exception:
        return None

# --- SCAN RUNNER EXECUTION ---
if st.button("🔍 Execute Sniper Scan", type="primary", use_container_width=True):
    results = []
    
    st.toast("Starting sniper-throttled scan engine. Do not change options until complete.", icon="⚠️")
    
    progress_text = "Scanning selected segment... Please wait."
    bar = st.progress(0, text=progress_text)
    
    total_symbols = len(symbols_to_scan)
    
    for idx, ticker in enumerate(symbols_to_scan):
        bar.progress((idx + 1) / total_symbols, text=f"Processing {ticker} ({idx+1}/{total_symbols})...")
        time.sleep(0.05)
        
        res = scan_zones(ticker, timeframe, zone_type, base_limit, min_legout, max_legout, min_leg_pct, max_leg_pct, mitigation_tolerance)
        if res:
            results.extend(res)
            
    bar.empty()
    
    if results:
        df_display = pd.DataFrame(results)
        df_display['Date Detected'] = pd.to_datetime(df_display['Date Detected'])
        df_display = df_display.sort_values(by="Date Detected", ascending=False)
        df_display['Date Detected'] = df_display['Date Detected'].dt.strftime('%Y-%m-%d')
        
        # APPLY THE STRICT SNIPER FILTER
        if only_approaching_fresh:
            df_display = df_display[
                (df_display['Trade Status'] == "Approaching / Valid 🎯") & 
                (df_display['Zone Status'].isin(["Completely Fresh 🟢", "Light Touch 🟡"]))
            ]
            
        if df_display.empty:
            st.warning("No valid untouched zones are currently being approached right now. Try adjusting the tolerance or expanding the market segment.")
        else:
            c1, c2 = st.columns(2)
            c1.success(f"🎯 Loaded **{len(df_display)}** Valid Formations.")
            c2.info(f"🟢 Found **{len(df_display[df_display['Zone Status'] == 'Completely Fresh 🟢'])}** 100% Untouched Zones.")
            
            def highlight_actionable(val):
                return 'background-color: #004d00' if val == "Approaching / Valid 🎯" else ''
                
            st.dataframe(df_display.style.map(highlight_actionable, subset=['Trade Status']), use_container_width=True, hide_index=True)
    else:
        st.warning("No institutional zones matched your parameters inside this segment.")
