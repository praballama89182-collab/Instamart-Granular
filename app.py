import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Analysis", layout="wide")

st.title("🚀 Swiggy Instamart Granular Performance Dashboard")
st.markdown("Upload your report to automatically analyze region, product, and keyword performance.")

# --- Helper: Robust Data Loading ---
def load_data_robust(file):
    # Determine if it's CSV or Excel
    is_excel = file.name.endswith(('.xlsx', '.xls'))
    
    if is_excel:
        # For Excel, we read and look for the header
        df_raw = pd.read_excel(file, header=None)
    else:
        # For CSV, we read and look for the header
        df_raw = pd.read_csv(file, header=None)

    # Find the row containing 'METRICS_DATE' to use as the header
    header_idx = 0
    for i, row in df_raw.iterrows():
        if 'METRICS_DATE' in row.values:
            header_idx = i
            break
            
    # Re-read or slice the dataframe starting from the detected header
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # Ensure numeric columns are converted correctly
    numeric_cols = ['TOTAL_IMPRESSIONS', 'TOTAL_BUDGET_BURNT', 'TOTAL_CLICKS', 
                    'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS', 'TOTAL_ROI']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Clean percentage columns
    for col in ['TOTAL_CTR', 'A2C_RATE']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.rstrip('%').astype(float) / 100.0
            
    return df

# --- 1. File Uploader ---
uploaded_file = st.file_uploader("Upload Granular CSV or Excel", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = load_data_robust(uploaded_file)
        
        # --- Category Mapping ---
        def map_item_type(name):
            n = str(name).lower()
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        df['ROAS'] = df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 1)

        # --- Sidebar Filters ---
        st.sidebar.header("Filters")
        cities = st.sidebar.multiselect("Cities", options=df['CITY'].unique(), default=df['CITY'].unique())
        cats = st.sidebar.multiselect("Categories", options=df['ITEM_TYPE'].unique(), default=df['ITEM_TYPE'].unique())
        
        filtered = df[(df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(cats))]

        # --- KPI Row ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.0f}")
        c2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        c3.metric("Conversions", int(filtered['TOTAL_CONVERSIONS'].sum()))
        total_roas = filtered['TOTAL_GMV'].sum() / filtered['TOTAL_BUDGET_BURNT'].sum() if filtered['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        c4.metric("Total ROAS", f"{total_roas:.2f}x")

        # --- Analysis Tables ---
        st.divider()
        
        # Region & Product
        st.subheader("📍 Region-wise Product Performance")
        reg_perf = filtered.groupby(['CITY', 'ITEM_TYPE', 'PRODUCT_NAME']).agg({
            'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
        }).reset_index().sort_values('TOTAL_GMV', ascending=False)
        st.dataframe(reg_perf, use_container_width=True)
        st.download_button("Export Region Data", reg_perf.to_csv(index=False), "region_performance.csv")

        # Top Keywords
        st.subheader("🔍 Top Performing Keywords")
        kw_perf = filtered.groupby(['ITEM_TYPE', 'KEYWORD']).agg({
            'TOTAL_GMV': 'sum', 'TOTAL_CONVERSIONS': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'
        }).reset_index()
        kw_perf['ROAS'] = kw_perf['TOTAL_GMV'] / kw_perf['TOTAL_BUDGET_BURNT'].replace(0, 1)
        st.dataframe(kw_perf.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
        st.download_button("Export Keyword Data", kw_perf.to_csv(index=False), "keyword_performance.csv")

        # Non-Performers
        st.subheader("🛑 Non-Performing Keywords (Zero GMV)")
        non_perf = filtered[filtered['TOTAL_GMV'] == 0].groupby('KEYWORD').agg({
            'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_IMPRESSIONS': 'sum', 'TOTAL_CLICKS': 'sum'
        }).reset_index().sort_values('TOTAL_BUDGET_BURNT', ascending=False)
        st.dataframe(non_perf, use_container_width=True)
        st.download_button("Export Non-Performers", non_perf.to_csv(index=False), "non_performers.csv")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload your CSV or Excel file to begin.")
