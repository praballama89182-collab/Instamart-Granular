import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Precision Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Extreme micromanagement: Track every Campaign, Category, and Keyword with 2-decimal precision.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    # Read the file to find the header row (typically row 6 in Swiggy reports)
    df_raw = pd.read_csv(file, header=None)
    
    header_idx = 0
    for i, row in df_raw.iterrows():
        if 'METRICS_DATE' in row.values:
            header_idx = i
            break
            
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # Numeric Conversion for precision calculations
    numeric_cols = [
        'TOTAL_IMPRESSIONS', 'TOTAL_BUDGET', 'TOTAL_BUDGET_BURNT', 
        'TOTAL_CLICKS', 'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Date processing for the "Best Days" analysis
    if 'METRICS_DATE' in df.columns:
        df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
        df['Day_of_Week'] = df['METRICS_DATE'].dt.day_name()
        df['Day_Num'] = df['METRICS_DATE'].dt.dayofweek # Monday=0 to Sunday=6
            
    return df

# --- 1. File Uploader ---
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
        
        # Strategy Calculations
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)

        # Sidebar Filters
        st.sidebar.header("Precision Filters")
        cities = st.sidebar.multiselect("Cities", options=sorted(df['CITY'].unique()), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=sorted(df['ITEM_TYPE'].unique()), default=df['ITEM_TYPE'].unique())
        
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # --- Main Navigation Tabs ---
        t1, t2, t3, t4, t5, t6 = st.tabs([
            "🌎 Global SKU View", "📍 Regional Analysis", "✅ Winning Keywords", 
            "🛑 Spend Wastage", "👻 Zero Visibility", "📅 Weekly Trends"
        ])

        # (Keeping your original logic for t1-t5 here...)
        with t1:
             st.subheader("National SKU Performance")
             st.dataframe(filtered.groupby('PRODUCT_NAME')[['TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'TOTAL_CONVERSIONS']].sum(), use_container_width=True)

        # --- NEW: Weekly Trends Logic ---
        with t6:
            st.subheader("Weekly Efficiency Analysis (Monday to Sunday)")
            
            # Aggregate data by day
            weekly_perf = filtered.groupby(['Day_Num', 'Day_of_Week']).agg({
                'TOTAL_CONVERSIONS': 'sum',
                'TOTAL_BUDGET_BURNT': 'sum'
            }).reset_index().sort_values('Day_Num')

            if not weekly_perf.empty:
                # Key Highlights
                best_day = weekly_perf.loc[weekly_perf['TOTAL_CONVERSIONS'].idxmax()]
                h1, h2 = st.columns(2)
                h1.metric("Highest Order Volume Day", f"{best_day['Day_of_Week']}")
                h2.metric("Total Weekly Conversions", f"{int(weekly_perf['TOTAL_CONVERSIONS'].sum())}")

                # Plotly Chart with Cool Tones
                fig = go.Figure()
                
                # Bars for Orders (Light Cool Teal)
                fig.add_trace(go.Bar(
                    x=weekly_perf['Day_of_Week'], 
                    y=weekly_perf['TOTAL_CONVERSIONS'],
                    name='Orders',
                    marker_color='#A2D2FF',
                    opacity=0.85
                ))
                
                # Line for Spend (Deep Cool Blue)
                fig.add_trace(go.Scatter(
                    x=weekly_perf['Day_of_Week'], 
                    y=weekly_perf['TOTAL_BUDGET_BURNT'],
                    name='Spend (₹)',
                    yaxis='y2',
                    line=dict(color='#219EBC', width=3)
                ))

                fig.update_layout(
                    template="plotly_white",
                    yaxis=dict(title="Number of Orders"),
                    yaxis2=dict(title="Spend (₹)", overlaying='y', side='right'),
                    legend=dict(x=0, y=1.1, orientation='h'),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Highlighted Data Table
                st.markdown("### 📊 Daily Summary Table")
                st.table(weekly_perf[['Day_of_Week', 'TOTAL_CONVERSIONS', 'TOTAL_BUDGET_BURNT']]
                         .rename(columns={'TOTAL_CONVERSIONS': 'Orders', 'TOTAL_BUDGET_BURNT': 'Total Spend'}))
            else:
                st.info("No date information found in the report.")

    except Exception as e:
        st.error(f"Analysis Error: {e}")
else:
    st.info("Please upload the Swiggy report to start.")
