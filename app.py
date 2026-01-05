import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Swiggy Instamart Precision Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Unified Micromanagement: Ad Performance + Optional GRN Inventory Audit.")

# --- Facility Mapping ---
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
        df['Mapped_City'] = df['FacilityName'].apply(map_facility_to_city)
        return df
    except: return None

# --- Sidebar Uploaders ---
st.sidebar.header("📁 Upload Reports")
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
            return 'OTHERS'
        
        df_ad['ITEM_TYPE'] = df_ad['PRODUCT_NAME'].apply(map_cat)
        
        st.sidebar.divider()
        st.sidebar.header("🎯 Strategy Filters")
        sel_cities = st.sidebar.multiselect("Cities", sorted(df_ad['CITY'].unique()), default=df_ad['CITY'].unique())
        sel_cats = st.sidebar.multiselect("Categories", sorted(df_ad['ITEM_TYPE'].unique()), default=df_ad['ITEM_TYPE'].unique())
        
        filtered_ad = df_ad[(df_ad['CITY'].isin(sel_cities)) & (df_ad['ITEM_TYPE'].isin(sel_cats))]

        # --- EXECUTIVE OVERVIEW ---
        st.header("📊 Executive Overview")
        o1, o2, o3, o4 = st.columns(4)
        total_gmv = filtered_ad['TOTAL_GMV'].sum()
        total_spend = filtered_ad['TOTAL_BUDGET_BURNT'].sum()
        total_qty = int(filtered_ad['TOTAL_CONVERSIONS'].sum())
        
        o1.metric("Total Revenue (GMV)", f"₹{total_gmv:,.2f}")
        o2.metric("Total Ad Spend", f"₹{total_spend:,.2f}")
        o3.metric("Combined ROAS", f"{(total_gmv/total_spend if total_spend > 0 else 0):.2f}x")
        o4.metric("Qty Sold", f"{total_qty} units")

        if df_grn is not None:
            st.success("✅ GRN Data Integrated")
        
        # --- TABS ---
        t1, t2, t3, t4, t5 = st.tabs([
            "📍 Regional Stock & GMV", "🛑 Spend Wastage", "✅ Winning Keywords", "📅 Weekly Trends (Best Days)", "👻 Zero Reach"
        ])

        with t1:
            st.subheader("Regional Performance Audit")
            sales_city = filtered_ad.groupby('CITY').agg({'TOTAL_GMV': 'sum', 'TOTAL_CONVERSIONS': 'sum'}).reset_index().rename(columns={'TOTAL_CONVERSIONS': 'Qty Sold'})
            if df_grn is not None:
                stock_city = df_grn.groupby('Mapped_City').agg({'ReceivedQty': 'sum'}).reset_index().rename(columns={'Mapped_City': 'CITY'})
                comparison = pd.merge(sales_city, stock_city, on='CITY', how='outer').fillna(0)
                st.dataframe(comparison.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
                st.plotly_chart(px.bar(comparison, x='CITY', y=['ReceivedQty', 'Qty Sold'], barmode='group', title="Stock vs Sales by Region", color_discrete_map={'ReceivedQty': '#A2D2FF', 'Qty Sold': '#B7E4C7'}), use_container_width=True)
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
            st.subheader("📅 Combined Weekly Trends & Efficiency")
            weekly = filtered_ad.groupby(['Day_Num', 'Day_Name']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'}).reset_index().sort_values('Day_Num')
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            if not weekly.empty:
                # --- FIXED COMBINED CHART ---
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=weekly['Day_Name'], y=weekly['TOTAL_GMV'],
                    name='Total GMV', marker_color='#B7E4C7',
                    text=weekly['TOTAL_GMV'].apply(lambda x: f"₹{x/1000:.1f}k"), textposition='auto'
                ))
                fig.add_trace(go.Scatter(
                    x=weekly['Day_Name'], y=weekly['TOTAL_BUDGET_BURNT'],
                    name='Budget Spent', line=dict(color='#219EBC', width=4, shape='spline'),
                    yaxis='y2', mode='lines+markers'
                ))

                # Using explicit dictionary updates to avoid ValueError
                fig.update_layout(
                    title_text="Efficiency Analysis: Revenue (Bars) vs Investment (Trend Line)",
                    xaxis=dict(categoryorder='array', categoryarray=day_order),
                    yaxis=dict(title="GMV (Revenue ₹)", side="left", showgrid=True),
                    yaxis2=dict(title="Spend (Investment ₹)", side="right", overlaying="y", showgrid=False),
                    template="plotly_white",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for the selected filters.")

        with t5:
            st.subheader("👻 Zero Reach Audit")
            zero = filtered_ad[filtered_ad['TOTAL_IMPRESSIONS'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).size().reset_index(name='Count')
            st.dataframe(zero, use_container_width=True)
    else:
        st.error("Error: Could not parse Advertising Report. Please check the file header.")
else:
    st.info("👋 Welcome! Please upload your reports in the sidebar to begin.")
