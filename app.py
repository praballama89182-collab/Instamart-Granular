import streamlit as st
import pandas as pd

# ... (Include the load_data_robust and map_item_type functions from previous steps) ...

if uploaded_file:
    df = load_data_robust(uploaded_file)
    df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
    
    # Precise Calculations
    df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)
    
    st.tabs(["City-wise View", "Global/Consolidated View"])
    
    # Inside "Global/Consolidated View" Tab:
    st.subheader("🌎 National Product Performance (All Regions Summed)")
    global_df = df.groupby(['ITEM_TYPE', 'PRODUCT_NAME']).agg({
        'TOTAL_IMPRESSIONS': 'sum',
        'TOTAL_BUDGET_BURNT': 'sum',
        'TOTAL_GMV': 'sum',
        'TOTAL_CONVERSIONS': 'sum'
    }).reset_index()
    global_df['GLOBAL_ROAS'] = (global_df['TOTAL_GMV'] / global_df['TOTAL_BUDGET_BURNT']).round(2)
    
    st.dataframe(global_df.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
