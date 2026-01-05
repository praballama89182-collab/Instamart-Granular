import streamlit as st
import pandas as pd
import plotly.express as px

# --- App Configuration ---
st.set_page_config(page_title="Swiggy Instamart Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Unified Micromanagement: Advertising Performance + Product-Level Inventory Audit.")

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
        num_cols = ['TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'TOTAL_CONVERSIONS', 'TOTAL_IMPRESSIONS']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        if 'METRICS_DATE' in df.columns:
            df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
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

# --- Sidebar ---
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

            # --- TABS ---
            tabs = st.tabs([
                "📍 Regional Stock & GMV", 
                "🛑 Spend Wastage", 
                "✅ Winning Keywords", 
                "📅 Weekly Trends (Best Days)", 
                "👻 Zero Reach",
                "💡 Strategy Recommendations"
            ])

            with tabs[0]:
                st.subheader("Regional Performance Audit")
                sales_city = filtered_ad.groupby('CITY').agg({'TOTAL_GMV': 'sum', 'TOTAL_CONVERSIONS': 'sum'}).reset_index().rename(columns={'TOTAL_CONVERSIONS': 'Qty Sold'})
                
                if df_grn is not None:
                    # 1. High Level City View
                    stock_city = df_grn.groupby('Mapped_City').agg({'ReceivedQty': 'sum'}).reset_index().rename(columns={'Mapped_City': 'CITY'})
                    comparison = pd.merge(sales_city, stock_city, on='CITY', how='outer').fillna(0)
                    st.write("### City-Level Summary")
                    st.dataframe(comparison.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
                    
                    # 2. Detailed Product View per Region
                    st.divider()
                    st.write("### 📦 Top 10 Products by Stock (Per Region)")
                    
                    # Filter GRN to Top 10 products per Facility based on ReceivedQty
                    top_10_grn = df_grn.groupby(['Mapped_City', 'SkuDescription']).agg({'ReceivedQty': 'sum'}).reset_index()
                    top_10_grn = top_10_grn.sort_values(['Mapped_City', 'ReceivedQty'], ascending=[True, False]).groupby('Mapped_City').head(10)
                    
                    # Clean up descriptions for better display
                    top_10_grn['Product'] = top_10_grn['SkuDescription'].str[:50] + "..."
                    
                    fig_grn_prod = px.bar(top_10_grn, x='ReceivedQty', y='Product', color='Mapped_City',
                                          orientation='h', title="Top 10 Products Received per Region",
                                          labels={'Mapped_City': 'Region', 'ReceivedQty': 'Qty Received'},
                                          height=600, template="plotly_white",
                                          color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_grn_prod.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_grn_prod, use_container_width=True)
                    
                    st.write("Detailed GRN Product List (Top 10 per Facility):")
                    st.dataframe(top_10_grn[['Mapped_City', 'SkuDescription', 'ReceivedQty']].rename(columns={'Mapped_City': 'Region', 'SkuDescription': 'Product Name'}), use_container_width=True)
                else:
                    st.dataframe(sales_city.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
                    st.info("Upload GRN Report to unlock Product-Level Inventory View.")

            # (Other tabs t2-t6 remain as per your working code)
            with tabs[1]:
                wastage = filtered_ad[filtered_ad['TOTAL_GMV'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({'TOTAL_BUDGET_BURNT': 'sum'}).reset_index()
                st.dataframe(wastage.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)

            with tabs[2]:
                winners = filtered_ad[filtered_ad['TOTAL_GMV'] > 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'}).reset_index()
                st.dataframe(winners.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

            with tabs[3]:
                weekly = filtered_ad.groupby(['Day_Num', 'Day_Name']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'}).reset_index().sort_values('Day_Num')
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if not weekly.empty:
                    fig_gmv = px.bar(weekly, x='Day_Name', y='TOTAL_GMV', title="Revenue by Day", category_orders={"Day_Name": day_order}, color_discrete_sequence=['#B7E4C7'], template="plotly_white", text_auto='.2s')
                    st.plotly_chart(fig_gmv, use_container_width=True)
                    fig_spend = px.bar(weekly, x='Day_Name', y='TOTAL_BUDGET_BURNT', title="Spend by Day", category_orders={"Day_Name": day_order}, color_discrete_sequence=['#A2D2FF'], template="plotly_white", text_auto='.2s')
                    st.plotly_chart(fig_spend, use_container_width=True)

            with tabs[4]:
                zero = filtered_ad[filtered_ad['TOTAL_IMPRESSIONS'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).size().reset_index(name='Count')
                st.dataframe(zero, use_container_width=True)

            with tabs[5]:
                st.subheader("💡 Actionable Strategy Recommendations")
                weekly['ROAS'] = weekly['TOTAL_GMV'] / weekly['TOTAL_BUDGET_BURNT'].replace(0, 1)
                best_day = weekly.loc[weekly['ROAS'].idxmax()]
                st.info(f"🚀 **Scale Up:** Increase budget by 20% on **{best_day['Day_Name']}s** (Peak ROAS: {best_day['ROAS']:.2f}x).")
                
                top_wasted = wastage.sort_values('TOTAL_BUDGET_BURNT', ascending=False).head(5)
                if not top_wasted.empty:
                    st.warning(f"**Stop Loss:** Audit the top 5 wasted keywords below to save ₹{top_wasted['TOTAL_BUDGET_BURNT'].sum():,.0f} in potential leakage.")
                    st.table(top_wasted)

    else:
        st.error("Error parsing Ad Report.")
else:
    st.info("👋 Please upload your Ad Report to begin.")
