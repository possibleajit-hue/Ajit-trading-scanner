import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Nifty 500 Institutional Zone Scanner", layout="wide")

st.title("📈 NIFTY 500 Demand & Supply Zone Scanner")
st.markdown("Automated scanning across multiple timeframes based on strict body-to-range ratios.")

# --- Step 1: Automatically load the Nifty 500 Ticker List ---
@st.cache_data
def load_nifty500_symbols():
    try:
        # Fetch directly from NSE public data source
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df = pd.read_csv(url)
        # Convert NSE symbols to Yahoo Finance format (adding .NS)
        tickers = [str(symbol).strip() + ".NS" for symbol in df['Symbol'].tolist()]
        return tickers
    except Exception:
        # High-quality fallback list if download fails
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "TATAMOTORS.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "HINDUNILVR.NS"]

nifty500_list = load_nifty500_symbols()

# --- Controls Layout ---
col1, col2, col3 = st.columns(3)
with col1:
    timeframe = st.selectbox("Select Timeframe", ["1d", "1wk", "1mo", "3mo"])
with col2:
    zone_type = st.selectbox("Select Zone Type", ["Bullish Demand Zone", "Bearish Supply Zone"])
with col3:
    scan_mode = st.radio("Scan Range", ["Test Scan (First 10 Stocks)", "Full Scan (All NIFTY 500)"])

# Define scan targets based on selection
symbols_to_scan = nifty500_list[:10] if scan_mode == "Test Scan (First 10 Stocks)" else nifty500_list

# --- Core Technical Analysis Engine ---
def scan_zones(ticker, tf, mode):
    try:
        data = yf.Ticker(ticker).history(period='2y', interval=tf)
        if len(data) < 10: return None
        
        df = data.copy()
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['Range'] = df['High'] - df['Low']
        
        # Base candle condition: Body must be less than 50% of high-low range
        df['Is_Base'] = df['Body'] < (0.5 * df['Range'])
        
        matches = []
        
        # Scan backward from the most recent completed candles
        for i in range(5, len(df) - 2):
            if mode == "Bullish Demand Zone":
                # Leg-Out: Next 2 candles must be strong bullish (Close > Open and Body >= 60% of total range)
                legout_1 = (df['Close'].iloc[i+1] > df['Open'].iloc[i+1]) and (df['Body'].iloc[i+1] >= 0.6 * df['Range'].iloc[i+1])
                legout_2 = (df['Close'].iloc[i+2] > df['Open'].iloc[i+2]) and (df['Body'].iloc[i+2] >= 0.6 * df['Range'].iloc[i+2])
                
                if legout_1 and legout_2:
                    base_count = 0
                    for check_idx in range(i, i-5, -1):
                        if df['Is_Base'].iloc[check_idx]: base_count += 1
                        else: break
                    
                    if 1 <= base_count <= 5:
                        matches.append({
                            "Ticker": ticker,
                            "Pattern": "Drop-Base-Rally",
                            "Date Detected": df.index[i+2].strftime('%Y-%m-%d'),
                            "Base Candles": base_count,
                            "Zone Floor (Low)": round(df['Low'].iloc[i-base_count+1 : i+1].min(), 2),
                            "Zone Ceiling (High)": round(df['Close'].iloc[i-base_count+1 : i+1].max(), 2)
                        })
            else:
                # Bearish Supply Zone Leg-Out: Next 2 candles must be strong bearish (Close < Open and Body >= 60% of total range)
                legout_1 = (df['Close'].iloc[i+1] < df['Open'].iloc[i+1]) and (df['Body'].iloc[i+1] >= 0.6 * df['Range'].iloc[i+1])
                legout_2 = (df['Close'].iloc[i+2] < df['Open'].iloc[i+2]) and (df['Body'].iloc[i+2] >= 0.6 * df['Range'].iloc[i+2])
                
                if legout_1 and legout_2:
                    base_count = 0
                    for check_idx in range(i, i-5, -1):
                        if df['Is_Base'].iloc[check_idx]: base_count += 1
                        else: break
                    
                    if 1 <= base_count <= 5:
                        matches.append({
                            "Ticker": ticker,
                            "Pattern": "Rally-Base-Drop",
                            "Date Detected": df.index[i+2].strftime('%Y-%m-%d'),
                            "Base Candles": base_count,
                            "Zone Ceiling (High)": round(df['High'].iloc[i-base_count+1 : i+1].max(), 2),
                            "Zone Floor (Low)": round(df['Close'].iloc[i-base_count+1 : i+1].min(), 2)
                        })
        return matches
    except Exception:
        return None

# --- Run Action ---
if st.button("🚀 Start NIFTY Scan", type="primary"):
    st.info(f"Loaded {len(nifty500_list)} official NIFTY 500 symbols from index.")
    results = []
    
    progress_bar = st.progress(0, text="Initializing scan engine...")
    
    for idx, ticker in enumerate(symbols_to_scan):
        progress_bar.progress((idx + 1) / len(symbols_to_scan), text=f"Scanning {ticker} ({idx+1}/{len(symbols_to_scan)})")
        res = scan_zones(ticker, timeframe, zone_type)
        if res:
            results.extend(res)
            
    progress_bar.empty()
    
    if results:
        st.success(f"Scan complete! Identified {len(results)} institutional zones.")
        df_display = pd.DataFrame(results)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.warning("No matching institutional zones found with your exact configuration right now.")
