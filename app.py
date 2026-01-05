import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy Dashboard")
st.markdown("Micromanagement view: Tracking Campaign, Category, and Keyword efficiency.")

# --- Robust Data Loading Engine ---
def load_data_resilient(file):
    try:
        # Read first few rows to detect header index
        # We search for the row containing 'METRICS_DATE'
        df_header_check = pd.read_csv(file, header=None, nrows=50)
        file.seek(0) # Reset file pointer for full read
        
        header_idx = -1
        for i, row in df_header_check.iterrows():
            if any('METRICS_DATE' in str(val).upper() for val in row.values):
                header_idx = i
                break
        
        if header_idx == -1:
            st.error("Could not find the 'METRICS_DATE' header in the report. Please check the file format.")
            return pd.DataFrame()

        # Load data starting from the correct row
        df = pd.read_csv(file, skiprows=header_idx)
        
        # 1. Clean Column Names
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # 2. Fix Dates
        if 'METRICS_DATE' in df.columns:
            df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
            df = df.dropna(subset=['METRICS_DATE']) # Remove meta/total rows at the bottom
            df['Day_of_Week'] = df['METRICS_DATE'].dt.day_name()
            df['Day_Num'] = df['METRICS_DATE'].dt.dayofweek # Mon=0, Sun=6
            
        # 3. Numeric Conversions
        numeric_cols = [
            'TOTAL_IMPRESSIONS', 'TOTAL_BUDGET_BURNT', 'TOTAL_CLICKS', 
            'TOTAL_A2C', 'TOTAL_GMV', 'TOTAL_CONVERSIONS'
        ]
        for col in numeric_cols:
            if col in df.columns:
                # Handle potential strings like '1,200.50'
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                
        return df
    except Exception as e:
        st.error(f"Loading Error: {e}")
        return pd.DataFrame()

# --- 1. File Upload ---
uploaded_file = st.file_uploader("Upload Swiggy Raw Granular Report (CSV)", type=['csv'])

if uploaded_file:
    df = load_data_resilient(uploaded_file)
    
    if not df.empty:
        # --- 2. Category Mapping (Priority: Palappam) ---
        def map_item_type(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'

        if 'PRODUCT_NAME' in df.columns:
            df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)
        else:
            df['ITEM_TYPE'] = 'UNKNOWN'

        # ROAS Calculation
        df['ROAS'] = (df['TOTAL_GMV'] / df['TOTAL_BUDGET_BURNT'].replace(0, 0.0001)).round(2)

        # --- 3. Sidebar Filters ---
        st.sidebar.header("Strategy Filters")
        
        # Cities
        all_cities = sorted(df['CITY'].unique()) if 'CITY' in df.columns else []
        selected_cities = st.sidebar.multiselect("Select Cities", options=all_cities, default=all_cities)
        
        # Categories (Including OTHERS by default)
        all_cats = sorted(df['ITEM_TYPE'].unique())
        selected_cats = st.sidebar.multiselect("Select Categories", options=all_cats, default=all_cats)
        
        # Campaigns
        all_camps = sorted(df['CAMPAIGN_NAME'].unique()) if 'CAMPAIGN_NAME' in df.columns else []
        selected_camps = st.sidebar.multiselect("Select Campaigns", options=all_camps, default=all_camps)

        # Apply Filters
        mask = (df['ITEM_TYPE'].isin(selected_cats))
        if 'CITY' in df.columns: mask &= df['CITY'].isin(selected_cities)
        if 'CAMPAIGN_NAME' in df.columns: mask &= df['CAMPAIGN_NAME'].isin(selected_camps)
        
        filtered = df[mask].copy()

        # --- 4. Dashboard Layout ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total GMV", f"₹{filtered['TOTAL_GMV'].sum():,.2f}")
        k2.metric("Total Spend", f"₹{filtered['TOTAL_BUDGET_BURNT'].sum():,.2f}")
        
        tot_spend = filtered['TOTAL_BUDGET_BURNT'].sum()
        total_roas = (filtered['TOTAL_GMV'].sum() / tot_spend).round(2) if tot_spend > 0 else 0
        k3.metric("Combined ROAS", f"{total_roas}x")
        k4.metric("Orders", int(filtered['TOTAL_CONVERSIONS'].sum()))

        # --- 5. Navigation Tabs ---
        t1, t2, t3, t4, t5, t6 = st.tabs([
            "🌎 SKU View", "📍 Regional", "✅ Winning Keywords", 
            "🛑 Spend Wastage", "👻 Zero Reach", "📅 Weekly Trends"
        ])

        with t1:
            st.subheader("Performance by Product")
            sku_view = filtered.groupby('PRODUCT_NAME').agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index().sort_values('TOTAL_GMV', ascending=False)
            st.dataframe(sku_view, use_container_width=True)

        with t2:
            st.subheader("Performance by City")
            city_view = filtered.groupby('CITY').agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index().sort_values('TOTAL_GMV', ascending=False)
            st.dataframe(city_view, use_container_width=True)

        with t6:
            st.subheader("Day-of-Week Strategy Analysis")
            
            # Group by Day
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            weekly = filtered.groupby(['Day_Num', 'Day_of_Week']).agg({
                'TOTAL_GMV': 'sum',
                'TOTAL_BUDGET_BURNT': 'sum'
            }).reset_index().sort_values('Day_Num')

            if not weekly.empty:
                # Chart 1: Total GMV (Mint Green)
                fig_gmv = go.Figure()
                fig_gmv.add_trace(go.Bar(
                    x=weekly['Day_of_Week'], y=weekly['TOTAL_GMV'],
                    name='Daily GMV', marker_color='#B7E4C7',
                    text=weekly['TOTAL_GMV'].apply(lambda x: f"₹{x:,.0f}"), textposition='outside'
                ))
                fig_gmv.update_layout(
                    title="Revenue Trend: Total GMV by Day",
                    template="plotly_white", yaxis_title="GMV (₹)",
                    xaxis={'categoryorder':'array', 'categoryarray':day_order},
                    margin=dict(t=50, b=50)
                )
                st.plotly_chart(fig_gmv, use_container_width=True)

                # Chart 2: Total Spend (Sky Blue)
                fig_spend = go.Figure()
                fig_spend.add_trace(go.Bar(
                    x=weekly['Day_of_Week'], y=weekly['TOTAL_BUDGET_BURNT'],
                    name='Daily Spend', marker_color='#A2D2FF',
                    text=weekly['TOTAL_BUDGET_BURNT'].apply(lambda x: f"₹{x:,.0f}"), textposition='outside'
                ))
                fig_spend.update_layout(
                    title="Investment Trend: Total Spend by Day",
                    template="plotly_white", yaxis_title="Spend (₹)",
                    xaxis={'categoryorder':'array', 'categoryarray':day_order},
                    margin=dict(t=50, b=50)
                )
                st.plotly_chart(fig_spend, use_container_width=True)
                
                # Summary Table
                st.markdown("### Weekly Performance Data")
                weekly['ROAS'] = (weekly['TOTAL_GMV'] / weekly['TOTAL_BUDGET_BURNT'].replace(0, 1)).round(2)
                st.table(weekly[['Day_of_Week', 'TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'ROAS']]
                         .rename(columns={'TOTAL_GMV':'GMV (₹)', 'TOTAL_BUDGET_BURNT':'Spend (₹)'}))
            else:
                st.info("No date-wise data available for the current filters.")

        # --- Footer Debug ---
        with st.expander("Data Inspection (First 5 Rows)"):
            st.write(filtered.head())
    else:
        st.warning("The file was loaded but no data was found. Please check if the report is empty.")
else:
    st.info("Please upload the Swiggy Granular Report to start analysis.")
