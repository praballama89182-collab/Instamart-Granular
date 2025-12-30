import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Analytics", layout="wide")

st.title("📊 Swiggy Instamart Granular Performance Dashboard")
st.markdown("Upload your Granular Sales Report (CSV or Excel) to see Region, Product, and Keyword insights.")

# --- 1. File Uploader Section ---
uploaded_file = st.file_uploader("Upload Granular Data", type=['csv', 'xlsx'])

def get_csv_download_link(df, filename="report.csv"):
    """Generates a link to download the dataframe as a CSV file."""
    csv = df.to_csv(index=False)
    return csv

if uploaded_file is not None:
    # Handle both CSV and Excel
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # --- Data Cleaning ---
        if 'TOTAL_CTR' in df.columns and df['TOTAL_CTR'].dtype == object:
            df['TOTAL_CTR'] = df['TOTAL_CTR'].str.rstrip('%').astype('float') / 100.0
        
        # --- Robust Product Mapping Logic ---
        def map_category(product_name):
            name = str(product_name).lower()
            if any(x in name for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in name: return 'PUTTU PODI'
            if any(x in name for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            if 'palappam' in name: return 'INSTANT PALAPPAM'
            return 'OTHERS'

        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_category)
        df['ROAS'] = df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 1)

        # --- Sidebar Filters ---
        st.sidebar.header("Global Filters")
        cities = st.sidebar.multiselect("Filter by City", options=df['CITY'].unique(), default=df['CITY'].unique())
        categories = st.sidebar.multiselect("Filter by Category", options=df['ITEM_TYPE'].unique(), default=df['ITEM_TYPE'].unique())
        
        mask = (df['CITY'].isin(cities)) & (df['ITEM_TYPE'].isin(categories))
        filtered_df = df[mask]

        # --- Dashboard Metrics ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total GMV", f"₹{filtered_df['TOTAL_GMV'].sum():,.0f}")
        m2.metric("Total Spends", f"₹{filtered_df['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        roas = filtered_df['TOTAL_GMV'].sum() / filtered_df['TOTAL_BUDGET_BURNT'].sum() if filtered_df['TOTAL_BUDGET_BURNT'].sum() > 0 else 0
        m3.metric("Combined ROAS", f"{roas:.2f}x")
        m4.metric("Conversions", int(filtered_df['TOTAL_CONVERSIONS'].sum()))

        # --- Section 1: Region & Category Performance ---
        st.subheader("📍 Region-wise Product Performance")
        reg_data = filtered_df.groupby(['CITY', 'ITEM_TYPE']).agg({
            'TOTAL_GMV': 'sum',
            'TOTAL_BUDGET_BURNT': 'sum',
            'TOTAL_CONVERSIONS': 'sum'
        }).reset_index()
        reg_data['ROAS'] = reg_data['TOTAL_GMV'] / reg_data['TOTAL_BUDGET_BURNT'].replace(0, 1)
        
        st.dataframe(reg_data.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
        st.download_button("Export Region Performance", get_csv_download_link(reg_data), "region_performance.csv", "text/csv")

        # --- Section 2: Product & Keyword Performance ---
        st.subheader("📦 Product & Top Keywords")
        prod_kw = filtered_df.groupby(['PRODUCT_NAME', 'KEYWORD']).agg({
            'TOTAL_GMV': 'sum',
            'TOTAL_CONVERSIONS': 'sum',
            'TOTAL_BUDGET_BURNT': 'sum'
        }).reset_index()
        prod_kw['ROAS'] = prod_kw['TOTAL_GMV'] / prod_kw['TOTAL_BUDGET_BURNT'].replace(0, 1)
        
        st.dataframe(prod_kw.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
        st.download_button("Export Product-Keyword Data", get_csv_download_link(prod_kw), "product_keywords.csv", "text/csv")

        # --- Section 3: Non-Performing Keywords ---
        st.subheader("🛑 Non-Performing Keywords (Zero Sales)")
        non_perf = filtered_df[filtered_df['TOTAL_GMV'] == 0].groupby(['ITEM_TYPE', 'KEYWORD']).agg({
            'TOTAL_BUDGET_BURNT': 'sum',
            'TOTAL_IMPRESSIONS': 'sum',
            'TOTAL_CLICKS': 'sum'
        }).reset_index().sort_values('TOTAL_BUDGET_BURNT', ascending=False)
        
        st.warning("These keywords are consuming budget without generating revenue.")
        st.dataframe(non_perf, use_container_width=True)
        st.download_button("Export Non-Performers", get_csv_download_link(non_perf), "non_performing_keywords.csv", "text/csv")

        # --- Section 4: Visualizing ROAS vs Spend ---
        st.subheader("📈 Category Efficiency (Spend vs ROAS)")
        cat_chart_data = filtered_df.groupby('ITEM_TYPE').agg({'TOTAL_BUDGET_BURNT':'sum', 'TOTAL_GMV':'sum'}).reset_index()
        cat_chart_data['ROAS'] = cat_chart_data['TOTAL_GMV'] / cat_chart_data['TOTAL_BUDGET_BURNT'].replace(0, 1)
        
        fig = px.scatter(cat_chart_data, x="TOTAL_BUDGET_BURNT", y="ROAS", size="TOTAL_GMV", color="ITEM_TYPE",
                         hover_name="ITEM_TYPE", log_x=True, size_max=60, title="Bubble size represents GMV")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Waiting for file upload...")
