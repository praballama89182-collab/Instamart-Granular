import streamlit as st
import pandas as pd

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Precision Analytics", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy Dashboard")
st.markdown("Micromanage your funnel from Impression to Add-to-Cart (A2C) to final Conversion.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    is_excel = file.name.endswith(('.xlsx', '.xls'))
    if is_excel:
        df_raw = pd.read_excel(file, header=None)
    else:
        df_raw = pd.read_csv(file, header=None)

    # Detect Header (Finding 'METRICS_DATE' dynamically to skip Swiggy metadata)
    header_idx = 0
    for i, row in df_raw.iterrows():
        if 'METRICS_DATE' in row.values:
            header_idx = i
            break
            
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # Numeric Conversion (Using correct Swiggy field names)
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
        
        # --- FIXED Category Mapping (Priority Check) ---
        def map_item_type(name):
            n = str(name).lower()
            # Check most specific first
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        
        # --- Metrics Calculation & 2-Decimal Rounding ---
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)
        df['CPA2C'] = (df['TOTAL_BUDGET_BURNT'] / df['TOTAL_A2C'].replace(0, 1)).round(2)
        df['A2C_RATE_CALC'] = (df['TOTAL_A2C'] / df['TOTAL_CLICKS'].replace(0, 1) * 100).round(2)

        # --- Sidebar Filters ---
        st.sidebar.header("Global Filters")
        sorted_cats = sorted(df['ITEM_TYPE'].unique())
        cities = st.sidebar.multiselect("Cities", options=sorted(df['CITY'].unique()), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=sorted_cats, default=sorted_cats)
        
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # --- KPI Row ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.2f}")
        k2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        k3.metric("Total A2C", int(filtered['TOTAL_A2C'].sum()))
        total_roas = (filtered['TOTAL_GMV'].sum() / filtered['TOTAL_BUDGET_BURNT'].sum()).round(2) if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        k4.metric("Total ROAS", f"{total_roas}x")

        # --- Navigation Tabs ---
        tab1, tab2, tab3 = st.tabs(["🌎 Global SKU View", "📍 Regional Breakdown", "🔍 Keyword Analysis"])

        with tab1:
            st.subheader("Performance by Product Category")
            summary = filtered.groupby('ITEM_TYPE').agg({
                'TOTAL_GMV': 'sum', 
                'TOTAL_BUDGET_BURNT': 'sum',
                'TOTAL_A2C': 'sum',
                'TOTAL_CONVERSIONS': 'sum'
            }).reset_index()
            summary['ROAS'] = (summary['TOTAL_GMV'] / summary['TOTAL_BUDGET_BURNT']).round(2)
            summary['Cost_Per_A2C'] = (summary['TOTAL_BUDGET_BURNT'] / summary['TOTAL_A2C'].replace(0, 1)).round(2)
            st.dataframe(summary.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        with tab2:
            st.subheader("Regional Efficiency")
            reg = filtered.groupby(['CITY', 'ITEM_TYPE']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_A2C': 'sum'
            }).reset_index().round(2)
            st.dataframe(reg, use_container_width=True)

        with tab3:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("✅ Performing Keywords")
                st.dataframe(filtered[filtered['TOTAL_GMV'] > 0][['KEYWORD', 'TOTAL_GMV', 'ROAS', 'TOTAL_A2C']].sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            with col_b:
                st.subheader("🛑 Wastage (0 GMV Keywords)")
                st.dataframe(filtered[filtered['TOTAL_GMV'] == 0][['CAMPAIGN_NAME', 'KEYWORD', 'TOTAL_BUDGET_BURNT', 'TOTAL_A2C']].sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)

        # --- Strategy Insights: The Purchase Intent Funnel ---
        st.divider()
        st.subheader("⚡ Strategy Insights: Add-to-Cart (A2C) Funnel Analysis")
        st.info("High A2C with Low GMV indicates high interest but a friction point at checkout (Price, Delivery Time, or Out-of-Stock).")
        
        # New Funnel Data
        funnel_data = filtered.groupby('ITEM_TYPE').agg({
            'TOTAL_CLICKS': 'sum',
            'TOTAL_A2C': 'sum',
            'TOTAL_CONVERSIONS': 'sum'
        }).reset_index()
        funnel_data['Click_to_A2C_%'] = (funnel_data['TOTAL_A2C'] / funnel_data['TOTAL_CLICKS'] * 100).round(2)
        funnel_data['A2C_to_Purchase_%'] = (funnel_data['TOTAL_CONVERSIONS'] / funnel_data['TOTAL_A2C'].replace(0, 1) * 100).round(2)
        
        st.table(funnel_data)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload the Swiggy granular report to begin analysis.")
