import streamlit as st
import pandas as pd

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Precision Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Extreme micromanagement: Track every Campaign, Category, and Keyword with 2-decimal precision.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    is_excel = file.name.endswith(('.xlsx', '.xls'))
    if is_excel:
        df_raw = pd.read_excel(file, header=None)
    else:
        df_raw = pd.read_csv(file, header=None)

    # Detect Header (skipping Swiggy metadata rows automatically)
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
        'TOTAL_CLICKS', 'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS', 
        'TOTAL_DIRECT_GMV_7_DAYS'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

# --- 1. File Uploader ---
uploaded_file = st.file_uploader("Upload Swiggy Granular Report (CSV or Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = load_data_robust(uploaded_file)
        
        # --- Fixed Category Mapping (Priority: Palappam) ---
        def map_item_type(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        
        # --- Strategy Calculations ---
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)
        df['CPC'] = (df['TOTAL_BUDGET_BURNT'] / df['TOTAL_CLICKS'].replace(0, 1)).round(2)

        # --- Sidebar Precision Filters ---
        st.sidebar.header("Precision Filters")
        all_camps = sorted(df['CAMPAIGN_NAME'].unique())
        selected_camps = st.sidebar.multiselect("Exact Campaign Names", options=all_camps, default=all_camps)
        
        sorted_cats = sorted(df['ITEM_TYPE'].unique())
        cities = st.sidebar.multiselect("Cities", options=sorted(df['CITY'].unique()), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=sorted_cats, default=sorted_cats)
        
        filtered = df[
            (df['CITY'].isin(cities)) & 
            (df['ITEM_TYPE'].isin(cats)) & 
            (df['CAMPAIGN_NAME'].isin(selected_camps))
        ]

        # --- Top KPI Summary ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.2f}")
        k2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        total_roas = (filtered['TOTAL_GMV'].sum() / filtered['TOTAL_BUDGET_BURNT'].sum()).round(2) if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        k3.metric("Combined ROAS", f"{total_roas}x")
        k4.metric("Conversions", int(filtered['TOTAL_CONVERSIONS'].sum()))

        # --- Main Navigation Tabs ---
        t1, t2, t3, t4, t5 = st.tabs([
            "🌎 Global SKU View", 
            "📍 Regional Analysis", 
            "✅ Winning Keywords", 
            "🛑 Spend Wastage", 
            "👻 Zero Visibility"
        ])

        with t1:
            st.subheader("National SKU Performance (Consolidated)")
            global_sku = filtered.groupby(['ITEM_TYPE', 'PRODUCT_NAME']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 
                'TOTAL_A2C': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index()
            global_sku['ROAS'] = (global_sku['TOTAL_GMV'] / global_sku['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
            st.dataframe(global_sku.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        with t2:
            st.subheader("Regional Performance (City x Category)")
            reg = filtered.groupby(['CITY', 'ITEM_TYPE']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index().round(2)
            reg['ROAS'] = (reg['TOTAL_GMV'] / reg['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
            st.dataframe(reg.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        with t3:
            st.subheader("Performing Keywords (Campaign + Category Level)")
            # UPDATED: Added CAMPAIGN_NAME to Winning Keywords
            perf_kw = filtered[filtered['TOTAL_GMV'] > 0].groupby(['ITEM_TYPE', 'CAMPAIGN_NAME', 'KEYWORD']).agg({
                'TOTAL_GMV': 'sum', 'ROAS': 'mean', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index().round(2)
            st.dataframe(perf_kw.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        with t4:
            st.subheader("Budget Burned with Zero Sales")
            # GMV=0 and Spend > 0
            wastage = filtered[(filtered['TOTAL_GMV'] == 0) & (filtered['TOTAL_BUDGET_BURNT'] > 0)].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                'TOTAL_BUDGET_BURNT': 'sum',
                'TOTAL_CLICKS': 'sum'
            }).reset_index().round(2)
            st.dataframe(wastage.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)
            st.metric("Total Money Burnt", f"₹{wastage['TOTAL_BUDGET_BURNT'].sum():,.2f}")

        with t5:
            st.subheader("Keywords with Zero Impressions (Zero Reach)")
            # Impressions = 0
            zero_imp = filtered[filtered['TOTAL_IMPRESSIONS'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).size().reset_index(name='City Count')
            st.dataframe(zero_imp, use_container_width=True)

        # --- Deep-Dive Funnel Analysis ---
        st.divider()
        st.subheader("⚡ Strategy Funnel: Add-to-Cart (A2C) Analysis")
        funnel = filtered.groupby('ITEM_TYPE').agg({
            'TOTAL_CLICKS': 'sum', 'TOTAL_A2C': 'sum', 'TOTAL_CONVERSIONS': 'sum'
        }).reset_index()
        funnel['Click_to_A2C_%'] = (funnel['TOTAL_A2C'] / funnel['TOTAL_CLICKS'] * 100).round(2)
        funnel['A2C_to_Purchase_%'] = (funnel['TOTAL_CONVERSIONS'] / funnel['TOTAL_A2C'].replace(0, 1) * 100).round(2)
        st.table(funnel)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload the Swiggy report to start.")
