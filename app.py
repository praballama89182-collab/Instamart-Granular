import streamlit as st
import pandas as pd
import plotly.express as px

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Unified Micromanagement: Advertising Performance + Optional GRN Inventory Audit.")

# --- Helper: Facility Mapping ---
def map_facility_to_city(fac):
    f = str(fac).upper()
    if 'MUM' in f: return 'Mumbai'
    if 'BLR' in f: return 'Bangalore'
    if 'CHE' in f or 'CHN' in f: return 'Chennai'
    if 'DLH' in f or 'GGN' in f: return 'Delhi/Gurgaon'
    if 'HYD' in f: return 'Hyderabad'
    if 'PUN' in f: return 'Pune'
    return 'Other'

# --- Robust Data Loaders ---
def load_ad_data(file):
    try:
        raw_data = pd.read_csv(file, header=None, encoding='latin1')
        header_idx = -1
        for i, row in raw_data.iterrows():
            if any("METRICS_DATE" in str(cell).upper() for cell in row.values):
                header_idx = i
                break
        if header_idx == -1: return None
        file.seek(0)
        df = pd.read_csv(file, skiprows=header_idx, encoding='latin1')
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Clean numeric data
        num_cols = ['TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'TOTAL_CONVERSIONS', 'TOTAL_IMPRESSIONS']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # Process Dates
        if 'METRICS_DATE' in df.columns:
            df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
            df = df.dropna(subset=['METRICS_DATE'])
            df['Day_Name'] = df['METRICS_DATE'].dt.day_name()
            df['Day_Num'] = df['METRICS_DATE'].dt.dayofweek
        return df
    except: return None

def load_grn_data(file):
    try:
        df = pd.read_csv(file)
        if 'FacilityName' in df.columns:
            df['Mapped_City'] = df['FacilityName'].apply(map_facility_to_city)
        return df
    except: return None

# --- Sidebar Uploaders ---
st.sidebar.header("📁 Data Upload Center")
ad_file = st.sidebar.file_uploader("1. Advertising Report (Required)", type=['csv'])
grn_file = st.sidebar.file_uploader("2. GRN Inventory Report (Optional)", type=['csv'])

if ad_file:
    df_ad = load_ad_data(ad_file)
    df_grn = load_grn_data(grn_file) if grn_file else None
    
    if df_ad is not None:
        def map_cat(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if 'matta' in n: return 'MATTA RICE'
            if 'puttu' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'
        
        df_ad['ITEM_TYPE'] = df_ad['PRODUCT_NAME'].apply(map_cat)
        
        # Filters
        st.sidebar.divider()
        st.sidebar.header("🎯 Strategy Filters")
        sel_cities = st.sidebar.multiselect("Select Cities", sorted(df_ad['CITY'].unique()), default=df_ad['CITY'].unique())
        sel_cats = st.sidebar.multiselect("Select Categories", sorted(df_ad['ITEM_TYPE'].unique()), default=df_ad['ITEM_TYPE'].unique())
        
        filtered_ad = df_ad[(df_ad['CITY'].isin(sel_cities)) & (df_ad['ITEM_TYPE'].isin(sel_cats))]

        # --- EXECUTIVE OVERVIEW ---
        st.header("📊 Executive Overview")
        if not filtered_ad.empty:
            o1, o2, o3, o4 = st.columns(4)
            total_gmv = filtered_ad['TOTAL_GMV'].sum()
            total_spend = filtered_ad['TOTAL_BUDGET_BURNT'].sum()
            total_qty = int(filtered_ad['TOTAL_CONVERSIONS'].sum())
            combined_roas = (total_gmv/total_spend if total_spend > 0 else 0)
            
            o1.metric("Total Revenue (GMV)", f"₹{total_gmv:,.2f}")
            o2.metric("Total Ad Spend", f"₹{total_spend:,.2f}")
            o3.metric("Combined ROAS", f"{combined_roas:.2f}x")
            o4.metric("Quantity Sold", f"{total_qty} units")

            if df_grn is not None:
                st.success("✅ GRN Data Integrated. Inventory Audit is active.")

            # --- TABS (Corrected Reordered Sequence) ---
            t1, t2, t3, t4, t5 = st.tabs([
                "📍 Regional Stock & GMV", 
                "🛑 Spend Wastage", 
                "✅ Winning Keywords", 
                "📅 Weekly Trends (Best Days)", 
                "👻 Zero Reach"
            ])

            with t1:
                st.subheader("Regional Performance Audit")
                sales_city = filtered_ad.groupby('CITY').agg({'TOTAL_GMV': 'sum', 'TOTAL_CONVERSIONS': 'sum'}).reset_index().rename(columns={'TOTAL_CONVERSIONS': 'Qty Sold'})
                
                if df_grn is not None:
                    stock_city = df_grn.groupby('Mapped_City').agg({'ReceivedQty': 'sum'}).reset_index().rename(columns={'Mapped_City': 'CITY'})
                    comparison = pd.merge(sales_city, stock_city, on='CITY', how='outer').fillna(0)
                    st.dataframe(comparison.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
                    
                    fig_st = px.bar(comparison, x='CITY', y=['ReceivedQty', 'Qty Sold'], barmode='group',
                                    title="Stock Received vs Qty Sold by Region",
                                    color_discrete_map={'ReceivedQty': '#A2D2FF', 'Qty Sold': '#B7E4C7'},
                                    template="plotly_white")
                    st.plotly_chart(fig_st, use_container_width=True)
                else:
                    st.dataframe(sales_city.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

            with t2:
                st.subheader("🛑 Spend Wastage (0 Sales)")
                wastage = filtered_ad[filtered_ad['TOTAL_GMV'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({'TOTAL_BUDGET_BURNT': 'sum'}).reset_index()
                st.dataframe(wastage.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)

            with t3:
                st.subheader("✅ Winning Keywords")
                winners = filtered_ad[filtered_ad['TOTAL_GMV'] > 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'}).reset_index()
                st.dataframe(winners.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

            with t4:
                st.subheader("📅 Weekly Efficiency Trends")
                weekly = filtered_ad.groupby(['Day_Num', 'Day_Name']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'}).reset_index().sort_values('Day_Num')
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                
                if not weekly.empty:
                    # Revenue Chart
                    fig_gmv = px.bar(weekly, x='Day_Name', y='TOTAL_GMV', title="Revenue by Day (GMV)",
                                     category_orders={"Day_Name": day_order},
                                     color_discrete_sequence=['#B7E4C7'], template="plotly_white", text_auto='.2s')
                    st.plotly_chart(fig_gmv, use_container_width=True)

                    # Spend Chart
                    fig_spend = px.bar(weekly, x='Day_Name', y='TOTAL_BUDGET_BURNT', title="Investment by Day (Spend)",
                                       category_orders={"Day_Name": day_order},
                                       color_discrete_sequence=['#A2D2FF'], template="plotly_white", text_auto='.2s')
                    st.plotly_chart(fig_spend, use_container_width=True)

                    # --- RECOMMENDATIONS ---
                    st.divider()
                    st.subheader("💡 Smart Strategy Recommendations")
                    weekly['ROAS'] = weekly['TOTAL_GMV'] / weekly['TOTAL_BUDGET_BURNT'].replace(0, 1)
                    best_roas = weekly.loc[weekly['ROAS'].idxmax()]
                    peak_sales = weekly.loc[weekly['TOTAL_GMV'].idxmax()]
                    
                    r1, r2 = st.columns(2)
                    r1.info(f"🚀 **Efficiency Champion:** **{best_roas['Day_Name']}** delivers the highest ROAS ({best_roas['ROAS']:.2f}x). Scale budgets here.")
                    r2.success(f"💰 **Revenue Peak:** **{peak_sales['Day_Name']}** brings the most volume. Ensure 100% stock availability.")
                else:
                    st.info("No weekly data found for this selection.")

            with t5:
                st.subheader("👻 Zero Reach Audit")
                zero = filtered_ad[filtered_ad['TOTAL_IMPRESSIONS'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).size().reset_index(name='Count')
                st.dataframe(zero, use_container_width=True)
        else:
            st.warning("No data matches your filter selection.")
    else:
        st.error("Error: Could not parse Advertising Report.")
else:
    st.info("👋 Please upload your Advertising Report in the sidebar to begin.")
