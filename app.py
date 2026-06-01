import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from fyers_apiv3 import fyersModel

# --- PAGE CONFIGURATION & UI THEME ---
st.set_page_config(page_title="Fyers Institutional Sniper v10.0", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .main-title { font-size: 40px; font-weight: 800; color: #00E676; margin-bottom: 0px; letter-spacing: 1px; }
    .sub-title { font-size: 16px; color: #90A4AE; margin-bottom: 30px; }
    .metric-card { background-color: #1E293B; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; }
    .stButton>button { border-radius: 8px; font-weight: 700; letter-spacing: 0.5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">⚡ FYERS REAL-TIME SNIPER SCANNER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Fully Automated Token Interception Gateway — High-Speed Live Market Scanner</p>', unsafe_allow_html=True)

# --- AUTOMATIC TOKEN INTERCEPTION ---
# Streamlit reads its own web URL bar to intercept the token from Fyers automatically!
fyers_app_id = "6905Y3PB5A-100"
fyers_secret_id = "FLBIZOXZD2"
my_streamlit_url = "https://ajit-trading-scanner-nubpmrvxg2ggshwrrqwpk.streamlit.app/"

captured_code = st.query_params.get("code", None)
if captured_code:
    st.session_state["fyers_auth_code"] = captured_code
    st.success("🎯 FYERS Security Access Token intercepted successfully! Connection is live.")

# --- LOCAL SECTOR DATA LOADER ---
@st.cache_data
def load_all_nse_segments():
    segments = {}
    def get_tickers(local_file):
        if os.path.exists(local_file):
            try:
                df = pd.read_csv(local_file)
                return df['Symbol'].astype(str).str.strip().tolist()
            except: pass
        return []

    segments["NIFTY 50 (Mega Cap)"] = get_tickers("ind_nifty50list.csv")
    segments["NIFTY 100 (Large Cap)"] = get_tickers("ind_nifty100list.csv")
    segments["NIFTY Midcap 100"] = get_tickers("ind_niftymidcap100list.csv")
    segments["NIFTY Smallcap 250"] = get_tickers("ind_niftysmallcap250list.csv")
    segments["Full NIFTY 500"] = get_tickers("ind_nifty500list.csv")
    
    fallback = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "TATAMOTORS", "SBIN", "ITC"]
    for k in list(segments.keys()):
        if not segments[k]: segments[k] = fallback
    return segments

all_segments = load_all_nse_segments()

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("🔑 Broker Authentication State")
    
    if "fyers_auth_code" not in st.session_state:
        st.warning("Status: Disconnected 🔴")
        login_url = f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={fyers_app_id}&redirect_uri={my_streamlit_url}&response_type=code&state=scanner"
        st.markdown(f'<a href="{login_url}" target="_self" style="background-color:#00E676;color:black;padding:10px 20px;text-decoration:none;border-radius:5px;font-weight:bold;display:inline-block;text-align:center;width:100%;">👉 CLICK HERE TO ACTIVATE SCANNER</a>', unsafe_allow_html=True)
        st.caption("This will log you into Fyers securely and link back to your app instantly.")
    else:
        st.success("Status: Connected 🟢 (Ready All Day)")
        if st.button("Disconnect App Session"):
            st.session_state.pop("fyers_auth_code", None)
            st.rerun()

    st.divider()
    st.header("🎛️ Scanner Settings")
    market_segment = st.selectbox("🎯 Select Market Segment", list(all_segments.keys()))
    scan_range = st.radio("Scan Range", ["Full Segment Scan", "Quick Test (First 5 Stocks)"])
    
    st.divider()
    tf_display = st.selectbox("⏳ Timeframe Chart", ["15m", "75m", "125m", "1d", "1wk", "1mo", "3mo", "6mo", "1yr"])
    tf_map = {"15m": "15", "75m": "75", "125m": "125", "1d": "D", "1wk": "W", "1mo": "M", "3mo": "M", "6mo": "M", "1yr": "M"}
    timeframe = tf_map[tf_display]
    
    zone_type = st.selectbox("📉 Order Type", ["Bullish Demand Zone", "Bearish Supply Zone"])
    state_filter = st.selectbox("Filter by Zone Condition", ["All Valid Zones", "Just Approaching (Nearing Edge)", "In the Zone (1-6 Candles Formed)", "Unmitigated (100% Completely Fresh)"])
    
    st.divider()
    st.markdown("### 🕯️ Candle Rules")
    base_limit = st.slider("Max Base Candles Allowed", 1, 6, 4)
    min_legout = st.slider("Min Leg-Out Candles Required", 1, 4, 2)
    min_legout_size_pct = st.slider("Minimum Leg-Out Candle Body Size (%)", 51, 100, 55)

base_list = all_segments[market_segment]
symbols_to_scan = base_list[:5] if "Quick Test" in scan_range else base_list

# --- RESAMPLING PIPELINE ---
def resample_dataframe(df, tf_disp):
    if df.empty or len(df) < 3: return None
    if tf_disp in ["75m", "125m"]:
        group_size = 5 if tf_disp == "75m" else 25
        df['Date'] = df.index.date
        df['block'] = df.groupby('Date').cumcount() // group_size
        resampled = df.groupby(['Date', 'block']).agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
        resampled.index = df.groupby(['Date', 'block']).apply(lambda x: x.index[0])
        return resampled
    elif tf_disp in ["3mo", "6mo", "1yr"]:
        rule = "3M" if tf_disp == "3mo" else ("6M" if tf_disp == "6mo" else "12M")
        return df.resample(rule).agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    return df

# --- SCANNING CORE ENGINE ---
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
                                "Ticker": ticker, "Formation Date": df.index[legout_start].strftime('%Y-%m-%d'),
                                "Leg-Out Count": legout_count, "Leg-Out Strength": f"{round(df['Body_Pct'].iloc[legout_start], 1)}%",
                                "Base": base_count, "Proximal (Ceiling)": z_ceil, "Distal (Floor)": z_floor,
                                "Current Price": current_price, "Zone State": state, "Live Alignment": proximity
                            })
                i = legout_start + legout_count
            else: i += 1
        return matches
    except: return None

# --- RUN SCANNER execution ---
if "fyers_auth_code" in st.session_state:
    if st.button("🔍 Run Live Institutional Market Scan", type="primary", use_container_width=True):
        results = []
        try:
            fyers = fyersModel.FyersModel(client_id=fyers_app_id, token=st.session_state["fyers_auth_code"], is_async=False, log_path="")
        except Exception as e:
            st.error(f"Handshake Expired: Tap the green button to refresh your broker login session. Details: {e}")
            st.stop()
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        if tf_display in ["15m", "75m", "125m"]:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        elif tf_display in ["3mo", "6mo", "1yr"]:
            start_date = (datetime.now() - timedelta(days=5475)).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%d")

        progress_bar = st.progress(0, text="Streaming native price matrices...")
        total_symbols = len(symbols_to_scan)
        
        for idx, symbol in enumerate(symbols_to_scan):
            progress_bar.progress((idx + 1) / total_symbols, text=f"Scanning {symbol} ({idx+1}/{total_symbols})...")
            try:
                response = fyers.history(data={"symbol": f"NSE:{symbol}-EQ", "resolution": timeframe, "date_format": "1", "range_from": start_date, "range_to": end_date, "cont_flag": "1"})
                if response and response.get('s') == 'ok' and response.get('candles'):
                    df = pd.DataFrame(response['candles'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
                    df.set_index('Timestamp', inplace=True)
                    
                    processed_df = resample_dataframe(df, tf_display)
                    if processed_df is not None and not processed_df.empty:
                        res = scan_zones(symbol, processed_df, zone_type, base_limit, min_legout, min_legout_size_pct)
                        if res: results.extend(res)
            except: continue
            
        progress_bar.empty()
        
        if results:
            df_display = pd.DataFrame(results).sort_values(by="Formation Date", ascending=False).drop_duplicates(subset=["Ticker"], keep="first")
            if state_filter == "Just Approaching (Nearing Edge)": df_display = df_display[df_display['Live Alignment'] == "Just Approaching 🎯"]
            elif state_filter == "In the Zone (1-6 Candles Formed)": df_display = df_display[df_display['Zone State'] == "In the Zone (1-6 Candles) 🟡"]
            elif state_filter == "Unmitigated (100% Completely Fresh)": df_display = df_display[df_display['Zone State'] == "Unmitigated 🟢"]
            
            if df_display.empty: st.warning("No live levels match your advanced criteria filter right now.")
            else:
                st.markdown(f"### 📈 Live Institutional Setup Ledger ({len(df_display)} Found)")
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning("No institutional zones detected in this current segment snapshot.")
else:
    st.info("💡 App Idle: Complete your 1-click login activation button on the sidebar to display the main action interface.")
