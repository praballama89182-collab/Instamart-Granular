import streamlit as st
import pandas as pd

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Strategy Analytics", layout="wide")

st.title("🚀 Swiggy Instamart: Performance & Funnel Dashboard")
st.markdown("Precision tracking of GMV, Spend efficiency, and Purchase Intent.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    is_excel = file.name.endswith(('.xlsx', '.xls'))
    if is_excel:
        df_raw = pd.read_excel(file, header=None)
    else:
        df_raw = pd.read_csv(file, header=None)

    # Detect Header (skipping metadata headers)
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
        'TOTAL_CLICKS', 'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS', 
        'TOTAL_DIRECT_GMV_7_DAYS'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

# --- 1. File Uploader ---
uploaded_file = st.file_uploader("Upload Swiggy Granular Report", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = load_data_robust(uploaded_file)
        
        # --- Robust Category Mapping (Priority Check for Palappam) ---
        def map_item_type(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        
        # --- Calculated Metrics ---
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)
        df['CPC'] = (df['TOTAL_BUDGET_BURNT'] / df['TOTAL_CLICKS'].replace(0, 1)).round(2)

        # --- Sidebar Filters ---
        st.sidebar.header("Global Filters")
        sorted_cats = sorted(df['ITEM_TYPE'].unique())
        cities = st.sidebar.multiselect("Cities", options=sorted(df['CITY'].unique()), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=sorted_cats, default=sorted_cats)
        
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # --- Top KPI Summary ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.2f}")
        k2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        total_roas = (filtered['TOTAL_GMV'].sum() / filtered['TOTAL_BUDGET_BURNT'].sum()).round(2) if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        k3.metric("Combined ROAS", f"{total_roas}x")
        k4.metric("Conversions", int(filtered['TOTAL_CONVERSIONS'].sum()))

        # --- Tabbed Section ---
        tab1, tab2, tab3 = st.tabs(["🌎 Global SKU View", "📍 Regional Analysis", "🔍 Keyword Analysis"])

        with tab1:
            st.subheader("National SKU Overview (with A2C)")
            # Tab 1 retains A2C for global intent monitoring
            global_df = filtered.groupby(['ITEM_TYPE', 'PRODUCT_NAME']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 
                'TOTAL_CONVERSIONS': 'sum', 'TOTAL_A2C': 'sum'
            }).reset_index()
            global_df['ROAS'] = (global_df['TOTAL_GMV'] / global_df['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
            st.dataframe(global_df.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        with tab2:
            st.subheader("Regional Performance (A2C Removed)")
            # Tab 2 focuses purely on region sales efficiency
            reg = filtered.groupby(['CITY', 'ITEM_TYPE']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index().round(2)
            reg['ROAS'] = (reg['TOTAL_GMV'] / reg['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
            st.dataframe(reg.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            
            # Regional Micromanagement Metrics
            st.divider()
            m1, m2 = st.columns(2)
            top_city = reg.groupby('CITY')['ROAS'].mean().idxmax()
            m1.metric("Highest Efficiency City (ROI)", top_city)
            city_cpc = filtered.groupby('CITY')['CPC'].mean().round(2)
            m2.metric("Most Expensive City (Avg CPC)", f"₹{city_cpc.max()} ({city_cpc.idxmax()})")

        with tab3:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("✅ Performing Keywords")
                # Category included, A2C removed
                perf_kw = filtered[filtered['TOTAL_GMV'] > 0].groupby(['ITEM_TYPE', 'KEYWORD']).agg({
                    'TOTAL_GMV': 'sum', 'ROAS': 'mean', 'TOTAL_CONVERSIONS': 'sum'
                }).reset_index().round(2)
                st.dataframe(perf_kw.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            
            with col_b:
                st.subheader("🛑 Wastage (0 GMV Keywords)")
                # A2C removed
                non_perf = filtered[filtered['TOTAL_GMV'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                    'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CLICKS': 'sum'
                }).reset_index().round(2)
                st.dataframe(non_perf.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)
            
            # Keyword Micromanagement Metrics
            st.divider()
            w1, w2 = st.columns(2)
            wastage_val = filtered[filtered['TOTAL_GMV'] == 0]['TOTAL_BUDGET_BURNT'].sum()
            wastage_pct = (wastage_val / filtered['TOTAL_BUDGET_BURNT'].sum() * 100).round(2) if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
            w1.metric("Budget Wastage %", f"{wastage_pct}%")
            top_kw = filtered.groupby('KEYWORD')['TOTAL_GMV'].sum().idxmax()
            w2.metric("Top Revenue Driver", top_kw)

        # --- Deep Dive Funnel (Bottom Section) ---
        st.divider()
        st.subheader("⚡ Strategy Insights: The Purchase Intent Funnel")
        funnel = filtered.groupby('ITEM_TYPE').agg({
            'TOTAL_CLICKS': 'sum', 'TOTAL_A2C': 'sum', 'TOTAL_CONVERSIONS': 'sum'
        }).reset_index()
        funnel['Click_to_A2C_%'] = (funnel['TOTAL_A2C'] / funnel['TOTAL_CLICKS'] * 100).round(2)
        funnel['A2C_to_Purchase_%'] = (funnel['TOTAL_CONVERSIONS'] / funnel['TOTAL_A2C'].replace(0, 1) * 100).round(2)
        st.table(funnel)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload report to start.")
