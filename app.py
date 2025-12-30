import streamlit as st
import pandas as pd
import plotly.express as px

# Configuration
st.set_page_config(page_title="Swiggy Instamart Analysis", layout="wide")

@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    # Basic Cleaning
    df['TOTAL_CTR'] = df['TOTAL_CTR'].str.rstrip('%').astype('float') / 100.0
    
    # Mapping Categories
    def map_cat(name):
        name = name.lower()
        if 'matta' in name: return 'MATTA RICE'
        if 'puttu' in name: return 'PUTTU PODI'
        if 'appam' in name or 'idiyappam' in name: return 'APPAM, IDIYAPPAM'
        return 'OTHER'
    
    df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_cat)
    df['ROAS'] = df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 1)
    return df

# Load your data
try:
    data = load_data('IM_GRANULAR_DATA.csv')
    st.title("🚀 Swiggy Instamart Performance Dashboard")

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    city_filter = st.sidebar.multiselect("Select City", options=data['CITY'].unique(), default=data['CITY'].unique())
    cat_filter = st.sidebar.multiselect("Select Category", options=data['ITEM_TYPE'].unique(), default=data['ITEM_TYPE'].unique())
    
    filtered_df = data[(data['CITY'].isin(city_filter)) & (data['ITEM_TYPE'].isin(cat_filter))]

    # --- KPI Row ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total GMV", f"₹{filtered_df['TOTAL_GMV'].sum():,.0f}")
    col2.metric("Total Spend", f"₹{filtered_df['TOTAL_BUDGET_BURNT'].sum():,.0f}")
    overall_roas = filtered_df['TOTAL_GMV'].sum() / filtered_df['TOTAL_BUDGET_BURNT'].sum()
    col3.metric("Overall ROAS", f"{overall_roas:.2f}x")
    col4.metric("Conversions", int(filtered_df['TOTAL_CONVERSIONS'].sum()))

    # --- Section 1: Region & Product Performance ---
    st.header("📍 Region-wise Performance")
    reg_perf = filtered_df.groupby('CITY').agg({'TOTAL_GMV':'sum', 'TOTAL_BUDGET_BURNT':'sum', 'ROAS':'mean'}).reset_index()
    fig_city = px.bar(reg_perf, x='CITY', y='TOTAL_GMV', color='ROAS', title="GMV by City (Color = Avg ROAS)")
    st.plotly_chart(fig_city, use_container_width=True)

    # --- Section 2: Product wise (Combined) ---
    st.header("📦 Product Performance")
    prod_perf = filtered_df.groupby('PRODUCT_NAME').agg({'TOTAL_GMV':'sum', 'TOTAL_CONVERSIONS':'sum', 'ROAS':'mean'}).sort_values('TOTAL_GMV', ascending=False)
    st.dataframe(prod_perf.style.background_gradient(cmap='Blues'))

    # --- Section 3: Keyword Analysis ---
    st.header("🔍 Keyword Efficiency")
    tab1, tab2 = st.tabs(["Top Keywords", "Non-Performing Keywords"])
    
    with tab1:
        top_kw = filtered_df.groupby('KEYWORD').agg({'TOTAL_GMV':'sum', 'TOTAL_CONVERSIONS':'sum', 'ROAS':'mean'}).sort_values('TOTAL_GMV', ascending=False).head(10)
        st.table(top_kw)
        
    with tab2:
        non_perf = filtered_df[filtered_df['TOTAL_GMV'] == 0].groupby('KEYWORD').agg({'TOTAL_BUDGET_BURNT':'sum', 'TOTAL_IMPRESSIONS':'sum'}).sort_values('TOTAL_BUDGET_BURNT', ascending=False).head(10)
        st.warning("The following keywords are burning budget without any sales:")
        st.dataframe(non_perf)

except Exception as e:
    st.error(f"Please upload the correct CSV file. Error: {e}")
