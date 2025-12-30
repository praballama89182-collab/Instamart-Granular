import streamlit as st
import pandas as pd
import plotly.express as px

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Analysis", layout="wide")

st.title("🚀 Swiggy Instamart Granular Performance Dashboard")
st.markdown("Precision tracking for GMV, Spends, and ROAS across campaigns.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    is_excel = file.name.endswith(('.xlsx', '.xls'))
    if is_excel:
        df_raw = pd.read_excel(file, header=None)
    else:
        df_raw = pd.read_csv(file, header=None)

    # Detect Header (skipping metadata rows)
    header_idx = 0
    for i, row in df_raw.iterrows():
        if 'METRICS_DATE' in row.values:
            header_idx = i
            break
            
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # Numeric Conversion
    numeric_cols = ['TOTAL_IMPRESSIONS', 'TOTAL_BUDGET_BURNT', 'TOTAL_CLICKS', 
                    'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS', 'TOTAL_ROI']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Percentage Cleaning
    for col in ['TOTAL_CTR', 'A2C_RATE']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.rstrip('%').astype(float) / 100.0
            
    return df

# --- 1. File Uploader ---
uploaded_file = st.file_uploader("Upload Granular CSV or Excel", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = load_data_robust(uploaded_file)
        
        # Category Mapping
        def map_item_type(name):
            n = str(name).lower()
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        
        # ROAS Calculation & Rounding to 2 decimal places
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)
        
        cols_to_round = ['TOTAL_BUDGET_BURNT', 'TOTAL_GMV', 'ROAS', 'TOTAL_ROI', 'TOTAL_CTR', 'A2C_RATE']
        for col in cols_to_round:
            if col in df.columns:
                df[col] = df[col].astype(float).round(2)

        # --- Sidebar Filters ---
        st.sidebar.header("Global Filters")
        cities = st.sidebar.multiselect("Cities", options=df['CITY'].unique(), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=df['ITEM_TYPE'].unique(), default=df['ITEM_TYPE'].unique())
        
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # --- KPI Row ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.2f}")
        c2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        total_roas = (filtered['TOTAL_GMV'].sum() / filtered['TOTAL_BUDGET_BURNT'].sum()).round(2) if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        c3.metric("Combined ROAS", f"{total_roas}x")
        c4.metric("Total Conversions", int(filtered['TOTAL_CONVERSIONS'].sum()))

        # --- Section 1: Region & Product Performance ---
        st.subheader("📍 Region-wise Performance (Product Level)")
        reg_perf = filtered.groupby(['CITY', 'ITEM_TYPE', 'PRODUCT_NAME']).agg({
            'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
        }).reset_index()
        reg_perf['ROAS'] = (reg_perf['TOTAL_GMV'] / reg_perf['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
        st.dataframe(reg_perf.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        # --- Section 2: Top Keywords ---
        st.subheader("🔍 Top Performing Keywords")
        kw_perf = filtered.groupby(['ITEM_TYPE', 'KEYWORD']).agg({
            'TOTAL_GMV': 'sum', 'TOTAL_CONVERSIONS': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'
        }).reset_index()
        kw_perf['ROAS'] = (kw_perf['TOTAL_GMV'] / kw_perf['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
        st.dataframe(kw_perf.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        # --- Section 3: Non-Performing Keywords ---
        st.subheader("🛑 Non-Performing Keywords (by Campaign)")
        # Filter for instances with 0 GMV and group by Campaign + Keyword
        non_perf = filtered[filtered['TOTAL_GMV'] == 0].groupby(['CITY', 'CAMPAIGN_NAME', 'KEYWORD']).agg({
            'TOTAL_GMV': 'sum', # Displays 0.00
            'TOTAL_BUDGET_BURNT': 'sum', 
            'TOTAL_IMPRESSIONS': 'sum', 
            'TOTAL_CLICKS': 'sum'
        }).reset_index()
        non_perf['ROAS'] = 0.00
        
        # Round non-performing table values
        non_perf['TOTAL_BUDGET_BURNT'] = non_perf['TOTAL_BUDGET_BURNT'].round(2)
        
        st.warning("Analysis by Campaign Name: Identify specific campaigns where keywords are underperforming.")
        st.dataframe(non_perf.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)

        # --- Section 4: Export Options ---
        st.subheader("📥 Export Reports")
        col_ex1, col_ex2 = st.columns(2)
        col_ex1.download_button("Download Region Sales Report", reg_perf.to_csv(index=False), "region_report.csv")
        col_ex2.download_button("Download Non-Performing Keywords", non_perf.to_csv(index=False), "wastage_report.csv")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload your Swiggy Instamart CSV or Excel file to begin.")
