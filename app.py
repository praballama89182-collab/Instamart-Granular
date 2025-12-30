import streamlit as st
import pandas as pd
import plotly.express as px

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Precision Analytics", layout="wide")

st.title("🚀 Swiggy Instamart: Growth & Efficiency Dashboard")
st.markdown("Micromanage your campaigns with granular insights and SKU-level performance tracking.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    is_excel = file.name.endswith(('.xlsx', '.xls'))
    if is_excel:
        df_raw = pd.read_excel(file, header=None)
    else:
        df_raw = pd.read_csv(file, header=None)

    # Detect Header (skipping metadata rows dynamically)
    header_idx = 0
    for i, row in df_raw.iterrows():
        if 'METRICS_DATE' in row.values:
            header_idx = i
            break
            
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # Numeric Conversion
    numeric_cols = ['TOTAL_IMPRESSIONS', 'TOTAL_BUDGET', 'TOTAL_BUDGET_BURNT', 
                    'TOTAL_CLICKS', 'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS', 
                    'TOTAL_ROI', 'TOTAL_DIRECT_GMV_7_DAYS']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Percentage Cleaning
    for col in ['TOTAL_CTR', 'A2C_RATE']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.rstrip('%').astype(float) / 100.0
            
    return df

# --- 1. File Uploader ---
uploaded_file = st.file_uploader("Upload Swiggy Granular Report (CSV or Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = load_data_robust(uploaded_file)
        
        # --- Category Mapping Logic ---
        def map_item_type(name):
            n = str(name).lower()
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        
        # --- Advanced Micro-Management Metrics ---
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001))
        df['CPC'] = (df['TOTAL_BUDGET_BURNT'] / df['TOTAL_CLICKS'].replace(0, 1))
        df['CVR'] = (df['TOTAL_CONVERSIONS'] / df['TOTAL_CLICKS'].replace(0, 1))
        df['CPA2C'] = (df['TOTAL_BUDGET_BURNT'] / df['TOTAL_A2C'].replace(0, 1))
        df['DIRECT_RATIO'] = (df['TOTAL_DIRECT_GMV_7_DAYS'] / df['TOTAL_GMV'].replace(0, 1))

        # Precision: Round everything to 2 decimal places
        cols_to_round = ['TOTAL_BUDGET_BURNT', 'TOTAL_GMV', 'ROAS', 'CPC', 'CVR', 'CPA2C', 'DIRECT_RATIO']
        for col in cols_to_round:
            df[col] = df[col].astype(float).round(2)

        # --- Global Filters ---
        st.sidebar.header("Global Filters")
        cities = st.sidebar.multiselect("Cities", options=df['CITY'].unique(), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=df['ITEM_TYPE'].unique(), default=df['ITEM_TYPE'].unique())
        
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # --- KPI Row ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.2f}")
        k2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        k3.metric("Conversions", int(filtered['TOTAL_CONVERSIONS'].sum()))
        total_roas = (filtered['TOTAL_GMV'].sum() / filtered['TOTAL_BUDGET_BURNT'].sum()).round(2) if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        k4.metric("Total ROAS", f"{total_roas}x")

        # --- Tabbed Navigation ---
        tab_global, tab_city, tab_kw = st.tabs(["🌎 Global/SKU View", "📍 City-wise Analysis", "🔍 Keyword Strategy"])

        with tab_global:
            st.subheader("National SKU Performance (Consolidated)")
            global_df = filtered.groupby(['ITEM_TYPE', 'PRODUCT_NAME']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum', 'TOTAL_A2C': 'sum'
            }).reset_index()
            global_df['GLOBAL_ROAS'] = (global_df['TOTAL_GMV'] / global_df['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
            st.dataframe(global_df.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            st.download_button("Export Global Report", global_df.to_csv(index=False), "national_performance.csv")

        with tab_city:
            st.subheader("Regional Product Breakdown")
            reg_perf = filtered.groupby(['CITY', 'ITEM_TYPE', 'PRODUCT_NAME']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'ROAS': 'mean', 'CVR': 'mean'
            }).reset_index().round(2)
            st.dataframe(reg_perf.sort_values(['CITY', 'TOTAL_GMV'], ascending=[True, False]), use_container_width=True)

        with tab_kw:
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader("✅ Performing Keywords")
                perf_kw = filtered[filtered['TOTAL_GMV'] > 0].groupby(['KEYWORD']).agg({
                    'TOTAL_GMV': 'sum', 'ROAS': 'mean', 'TOTAL_CONVERSIONS': 'sum'
                }).reset_index().round(2)
                st.dataframe(perf_kw.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            
            with col_right:
                st.subheader("🛑 Non-Performing Keywords (by Campaign)")
                # segmented by campaign name for micromanagement
                non_perf = filtered[filtered['TOTAL_GMV'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                    'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CLICKS': 'sum'
                }).reset_index().round(2)
                non_perf['ROAS'] = 0.00
                st.dataframe(non_perf.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)

        # --- Micro-Efficiency Grid ---
        st.divider()
        st.subheader("⚡ Micro-Management Efficiency Metrics")
        eff_col1, eff_col2 = st.columns(2)
        
        with eff_col1:
            # Check Match Type Efficiency
            match_perf = filtered.groupby('MATCH_TYPE').agg({'TOTAL_GMV':'sum', 'TOTAL_BUDGET_BURNT':'sum'}).reset_index()
            match_perf['ROAS'] = (match_perf['TOTAL_GMV'] / match_perf['TOTAL_BUDGET_BURNT']).round(2)
            st.write("**Match Type Efficiency**")
            st.table(match_perf)

        with eff_col2:
            st.write("**Direct Attribution Analysis**")
            st.info("Direct Ratio measures how many sales happened immediately vs. later discovery.")
            st.metric("Direct Sales Ratio (Avg)", f"{filtered['DIRECT_RATIO'].mean():.2%}")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Waiting for data upload...")
