import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from fyers_apiv3 import fyersModel

# --- PAGE CONFIGURATION & UI THEME ---
st.set_page_config(page_title="Fyers Institutional Sniper v7.0", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .main-title { font-size: 40px; font-weight: 800; color: #00E676; margin-bottom: 0px; letter-spacing: 1px; }
    .sub-title { font-size: 16px; color: #90A4AE; margin-bottom: 30px; }
    .metric-card { background-color: #1E293B; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; }
    .stButton>button { border-radius: 8px; font-weight: 700; letter-spacing: 0.5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">⚡ FYERS INSTITUTIONAL SNIPER v7.0</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Broker API Powered High-Speed Custom Timeframe Scanner</p>', unsafe_allow_html=True)

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
        if not segments[k]:
            segments[k] = fallback
    return segments

all_segments = load_all_nse_segments()

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("🔑 Fyers API Authentication")
    
    # 1. Permanent Keys
    fyers_app_id = st.text_input("Fyers App ID (Client ID)", value="6905Y3PB5A-100", type="password")
    fyers_secret_id = st.text_input("Fyers Secret ID", value="FLBIZOXZD2", type="password")
    redirect_uri = "https://trade.fyers.in/"
    
    st.divider()
    st.markdown("### ☀️ Morning Activation")
    
    # Generate the login link dynamically
    login_url = f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={fyers_app_id}&redirect_uri={redirect_uri}&response_type=code&state=scanner"
    st.markdown(f'[👉 **Step 1: Click Here to Login & Get Code**]({login_url})')
    
    auth_code = st.text_input("Step 2: Paste the 'code' from URL here", type="password")
    
    st.divider()
    st.header("🎛️ Strategic Controls")
    market_segment = st.selectbox("🎯 Select Market Segment", list(all_segments.keys()))
    scan_range = st.radio("Scan Target Length", ["Full Segment Scan", "Quick Test (First 5 Stocks)"])
    
    st.divider()
    tf_display = st.selectbox("⏳ Native Resolution Timeframe", ["15m", "75m", "125m", "1d", "1wk", "1mo"])
    tf_map = {"15m": "15", "75m": "75", "125m": "125", "1d": "D", "1wk": "W", "1mo": "M"}
    timeframe = tf_map[tf_display]
    
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
                            date_detected = df.index[legout_start].strftime('%Y-%m-%d %H:%M')
                            matches.append({
                                "Ticker": ticker,
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
if st.button("🔍 Run FYERS Institutional Scan", type="primary", use_container_width=True):
    if not auth_code:
        st.error("Authentication Error: Please complete Step 1 and Step 2 in the sidebar to retrieve your morning authorization code.")
    else:
        results = []
        
        # AUTOMATICALLY EXCHANGE AUTH CODE FOR ACCESS TOKEN
        try:
            session_model = fyersModel.SessionModel(
                client_id=fyers_app_id,
                secret_key=fyers_secret_id,
                redirect_uri=redirect_uri,
                response_type='code',
                grant_type='authorization_code'
            )
            session_model.set_token(auth_code)
            token_response = session_model.generate_token()
            access_token = token_response.get("access_token")
            
            fyers = fyersModel.FyersModel(client_id=fyers_app_id, token=access_token, is_async=False, log_path="")
        except Exception as e:
            st.error(f"Fyers Handshake Failed: Ensure your Auth Code is fresh. Details: {e}")
            st.stop()
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        if timeframe in ["15", "75", "125"]:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

        progress_bar = st.progress(0, text="Streaming native arrays from FYERS production data vaults...")
        total_symbols = len(symbols_to_scan)
        
        for idx, symbol in enumerate(symbols_to_scan):
            fyers_symbol = f"NSE:{symbol}-EQ"
            progress_bar.progress((idx + 1) / total_symbols, text=f"Scanning {symbol} ({idx+1}/{total_symbols})...")
            
            try:
                data = {
                    "symbol": fyers_symbol,
                    "resolution": timeframe,
                    "date_format": "1",
                    "range_from": start_date,
                    "range_to": end_date,
                    "cont_flag": "1"
                }
                
                response = fyers.history(data=data)
                
                if response and response.get('s') == 'ok' and response.get('candles'):
                    df = pd.DataFrame(response['candles'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
                    df.set_index('Timestamp', inplace=True)
                    
                    res = scan_zones(symbol, df, zone_type, base_limit, min_legout, min_legout_size_pct)
                    if res:
                        results.extend(res)
            except Exception:
                continue
                
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
            st.warning("No institutional setups detected matching these settings within the downloaded parameters.")
