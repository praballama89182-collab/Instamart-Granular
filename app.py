import streamlit as st
import pandas as pd
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="Swiggy Instamart Precision Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Unified view: Ad Performance + Warehouse GRN Inventory.")

# --- Helper: Map Facility to City ---
def map_facility_to_city(fac):
    f = str(fac).upper()
    if 'MUM' in f: return 'Mumbai'
    if 'BLR' in f: return 'Bangalore'
    if 'CHE' in f or 'CHN' in f: return 'Chennai'
    if 'DLH' in f or 'GGN' in f: return 'Delhi/Gurgaon'
    if 'HYD' in f: return 'Hyderabad'
    if 'PUN' in f: return 'Pune'
    return 'Other'

# --- Data Loaders ---
def load_ad_data(file):
    raw_data = pd.read_csv(file, header=None, encoding='latin1')
    header_idx = -1
    for i, row in raw_data.iterrows():
        if any("METRICS_DATE" in str(cell).upper() for cell in row.values):
            header_idx = i
            break
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, encoding='latin1')
    df.columns = [str(c).strip().upper() for c in df.columns]
    num_cols = ['TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'TOTAL_CONVERSIONS', 'TOTAL_IMPRESSIONS']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    if 'METRICS_DATE' in df.columns:
        df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
        df['Day_Name'] = df['METRICS_DATE'].dt.day_name()
        df['Day_Num'] = df['METRICS_DATE'].dt.dayofweek
    return df

def load_grn_data(file):
    df = pd.read_csv(file)
    df['Mapped_City'] = df['FacilityName'].apply(map_facility_to_city)
    return df

# --- File Uploaders ---
c1, c2 = st.columns(2)
ad_file = c1.file_uploader("Upload Ad Report (Granular CSV)", type=['csv'], key="ad")
grn_file = c2.file_uploader("Upload GRN Report (Inventory CSV)", type=['csv'], key="grn")

if ad_file and grn_file:
    df_ad = load_ad_data(ad_file)
    df_grn = load_grn_data(grn_file)
    
    if df_ad is not None and df_grn is not None:
        # Category Mapping Logic
        def map_cat(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if 'matta' in n: return 'MATTA RICE'
            if 'puttu' in n: return 'PUTTU PODI'
            return 'OTHERS'
        
        df_ad['ITEM_TYPE'] = df_ad['PRODUCT_NAME'].apply(map_cat)
        df_grn['ITEM_TYPE'] = df_grn['SkuDescription'].apply(map_cat)

        # Filters
        st.sidebar.header("Strategy Filters")
        sel_cities = st.sidebar.multiselect("Cities", sorted(df_ad['CITY'].unique()), default=df_ad['CITY'].unique())
        filtered_ad = df_ad[df_ad['CITY'].isin(sel_cities)]

        # --- Tab Navigation (Reordered as requested) ---
        t1, t2, t3, t4, t5 = st.tabs([
            "📍 Regional Stock & GMV", 
            "🛑 Spend Wastage", 
            "✅ Winning Keywords", 
            "📅 Weekly Trends (Best Days)", 
            "👻 Zero Reach"
        ])

        with t1:
            st.subheader("Regional Inventory vs. Revenue")
            
            # Aggregate Ad Data (Sales)
            sales_city = filtered_ad.groupby('CITY').agg({
                'TOTAL_GMV': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index().rename(columns={'TOTAL_CONVERSIONS': 'Qty Sold'})
            
            # Aggregate GRN Data (Stock)
            stock_city = df_grn.groupby('Mapped_City').agg({
                'ReceivedQty': 'sum'
            }).reset_index().rename(columns={'Mapped_City': 'CITY'})
            
            # Merge for comparison
            comparison = pd.merge(sales_city, stock_city, on='CITY', how='outer').fillna(0)
            
            st.dataframe(comparison.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            
            fig = px.bar(comparison, x='CITY', y=['ReceivedQty', 'Qty Sold'], barmode='group',
                         title="Stock Received vs. Quantity Sold by Region",
                         color_discrete_map={'ReceivedQty': '#A2D2FF', 'Qty Sold': '#B7E4C7'})
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            st.subheader("🛑 Spend Wastage")
            wastage = filtered_ad[filtered_ad['TOTAL_GMV'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                'TOTAL_BUDGET_BURNT': 'sum'
            }).reset_index()
            st.dataframe(wastage.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)

        with t3:
            st.subheader("✅ Winning Keywords")
            winners = filtered_ad[filtered_ad['TOTAL_GMV'] > 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'
            }).reset_index()
            st.dataframe(winners.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

        with t4:
            st.subheader("📅 Weekly Trends (Best Days)")
            weekly = filtered_ad.groupby(['Day_Num', 'Day_Name']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'}).reset_index().sort_values('Day_Num')
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            st.plotly_chart(px.bar(weekly, x='Day_Name', y='TOTAL_GMV', category_orders={"Day_Name": day_order}, color_discrete_sequence=['#B7E4C7']), use_container_width=True)
            st.plotly_chart(px.bar(weekly, x='Day_Name', y='TOTAL_BUDGET_BURNT', category_orders={"Day_Name": day_order}, color_discrete_sequence=['#A2D2FF']), use_container_width=True)

        with t5:
            st.subheader("👻 Zero Reach")
            zero = filtered_ad[filtered_ad['TOTAL_IMPRESSIONS'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).size().reset_index(name='Count')
            st.dataframe(zero, use_container_width=True)

else:
    st.info("Please upload BOTH the Ad Report and the GRN Report to see the Regional Stock analysis.")
