import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Precision Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Extreme micromanagement: Track every Campaign, Category, and Keyword with 2-decimal precision.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    df_raw = pd.read_csv(file, header=None)
    
    # Detect Header (Row 6 in your specific file)
    header_idx = 0
    for i, row in df_raw.iterrows():
        if 'METRICS_DATE' in row.values:
            header_idx = i
            break
            
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # Numeric Conversion
    numeric_cols = [
        'TOTAL_IMPRESSIONS', 'TOTAL_BUDGET', 'TOTAL_BUDGET_BURNT', 
        'TOTAL_CLICKS', 'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Date processing
    if 'METRICS_DATE' in df.columns:
        df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
        df['Day_of_Week'] = df['METRICS_DATE'].dt.day_name()
        df['Day_Num'] = df['METRICS_DATE'].dt.dayofweek # Mon=0, Sun=6
            
    return df

uploaded_file = st.file_uploader("Upload Swiggy Granular Report (CSV)", type=['csv'])

if uploaded_file:
    try:
        df = load_data_robust(uploaded_file)
        
        # --- Fixed Category Mapping ---
        def map_item_type(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'
        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)

        # Filters
        st.sidebar.header("Precision Filters")
        cities = st.sidebar.multiselect("Cities", options=sorted(df['CITY'].unique()), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=sorted(df['ITEM_TYPE'].unique()), default=df['ITEM_TYPE'].unique())
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # Tabs
        t1, t2, t3, t4, t5, t6 = st.tabs([
            "🌎 Global SKU View", "📍 Regional Analysis", "✅ Winning Keywords", 
            "🛑 Spend Wastage", "👻 Zero Visibility", "📅 Weekly Trends"
        ])

        with t6:
            st.subheader("Weekly Revenue & Investment Analysis")
            
            # Aggregate data by day
            weekly_perf = filtered.groupby(['Day_Num', 'Day_of_Week']).agg({
                'TOTAL_GMV': 'sum',
                'TOTAL_BUDGET_BURNT': 'sum'
            }).reset_index().sort_values('Day_Num')

            if not weekly_perf.empty:
                # Top Summary Metrics
                m1, m2 = st.columns(2)
                best_gmv_day = weekly_perf.loc[weekly_perf['TOTAL_GMV'].idxmax()]
                m1.success(f"💰 Best Sales Day: **{best_gmv_day['Day_of_Week']}** (₹{best_gmv_day['TOTAL_GMV']:,.2f})")
                m2.info(f"💸 Highest Spend Day: **{weekly_perf.loc[weekly_perf['TOTAL_BUDGET_BURNT'].idxmax()]['Day_of_Week']}**")

                # --- Chart 1: Daily GMV (Light Green/Teal) ---
                fig_gmv = go.Figure()
                fig_gmv.add_trace(go.Bar(
                    x=weekly_perf['Day_of_Week'], 
                    y=weekly_perf['TOTAL_GMV'],
                    name='Total GMV',
                    marker_color='#B7E4C7', # Light Mint Green
                    text=weekly_perf['TOTAL_GMV'].round(0),
                    textposition='auto',
                ))
                fig_gmv.update_layout(
                    title="Total GMV by Day (Sales Performance)",
                    template="plotly_white",
                    yaxis_title="GMV (₹)",
                    height=400
                )
                st.plotly_chart(fig_gmv, use_container_width=True)

                # --- Chart 2: Daily Spend (Light Blue) ---
                fig_spend = go.Figure()
                fig_spend.add_trace(go.Bar(
                    x=weekly_perf['Day_of_Week'], 
                    y=weekly_perf['TOTAL_BUDGET_BURNT'],
                    name='Total Spend',
                    marker_color='#A2D2FF', # Light Sky Blue
                    text=weekly_perf['TOTAL_BUDGET_BURNT'].round(0),
                    textposition='auto',
                ))
                fig_spend.update_layout(
                    title="Total Budget Burnt by Day (Investment)",
                    template="plotly_white",
                    yaxis_title="Spend (₹)",
                    height=400
                )
                st.plotly_chart(fig_spend, use_container_width=True)
                
                # Raw data comparison
                st.markdown("### 📊 Daily Efficiency Breakdown")
                weekly_perf['ROAS'] = (weekly_perf['TOTAL_GMV'] / weekly_perf['TOTAL_BUDGET_BURNT'].replace(0,1)).round(2)
                st.table(weekly_perf[['Day_of_Week', 'TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'ROAS']]
                         .rename(columns={'TOTAL_GMV':'GMV (₹)', 'TOTAL_BUDGET_BURNT':'Spend (₹)'}))
            else:
                st.info("No date-wise data found.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload the Swiggy report to start.")
