import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Demand Zone Scanner", layout="wide")

st.title("📈 Multi-Timeframe Demand Zone Scanner")
st.markdown("Scans stocks for a Leg-In, 1-5 Base Candles (Body < 50% of range), and a 2-Candle Strong Bullish Leg-Out.")

col1, col2 = st.columns(2)
with col1:
    timeframe = st.selectbox("Select Timeframe", ["1d", "1wk", "1mo", "3mo"])
with col2:
    tickers_input = st.text_area("Stock Symbols (Comma separated)", 
                                 "RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS, TATAMOTORS.NS, ITC.NS, SBIN.NS")

def analyze_demand_zones(ticker, tf):
    try:
        data = yf.Ticker(ticker.strip()).history(period='2y', interval=tf)
        if len(data) < 10: return None
        
        df = data.copy()
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['Range'] = df['High'] - df['Low']
        
        df['Is_Base'] = df['Body'] < (0.5 * df['Range'])
        df['Is_Strong_Bull'] = (df['Close'] > df['Open']) & (df['Body'] >= 0.6 * df['Range'])
        
        matches = []
        for i in range(5, len(df) - 2):
            if df['Is_Strong_Bull'].iloc[i+1] and df['Is_Strong_Bull'].iloc[i+2]:
                base_count = 0
                for check_idx in range(i, i-5, -1):
                    if df['Is_Base'].iloc[check_idx]:
                        base_count += 1
                    else:
                        break
                
                if 1 <= base_count <= 5:
                    matches.append({
                        "Ticker": ticker.strip(),
                        "Date Found": df.index[i+2].strftime('%Y-%m-%d'),
                        "Base Candles": base_count,
                        "Zone Low": round(df['Low'].iloc[i-base_count+1 : i+1].min(), 2),
                        "Zone High": round(df['Close'].iloc[i-base_count+1 : i+1].max(), 2)
                    })
        return matches
    except Exception as e:
        return None

if st.button("Run Scanner", type="primary"):
    ticker_list = [t.strip() for t in tickers_input.split(",")]
    all_results = []
    
    progress_text = "Scanning stocks. Please wait..."
    my_bar = st.progress(0, text=progress_text)
    
    for idx, stock in enumerate(ticker_list):
        my_bar.progress((idx + 1) / len(ticker_list), text=f"Scanning {stock}...")
        res = analyze_demand_zones(stock, timeframe)
        if res:
            all_results.extend(res)
            
    my_bar.empty()
    
    if all_results:
        st.success(f"Found {len(all_results)} Demand Zones!")
        results_df = pd.DataFrame(all_results)
        st.dataframe(results_df, use_container_width=True)
    else:
        st.warning("No Demand Zones found matching the strict criteria in this list.")
