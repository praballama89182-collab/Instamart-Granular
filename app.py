import streamlit as st
import pandas as pd
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="Swiggy Instamart Precision Strategy", layout="wide")

st.title("🚀 Swiggy Instamart: Precision Strategy & Efficiency Dashboard")
st.markdown("Automated auditing for Spend Wastage, Reach, and Weekly Trends.")

# --- Robust Data Engine ---
def load_data_expert(file):
    try:
        raw_data = pd.read_csv(file, header=None, encoding='latin1')
        header_row_idx = -1
        for i, row in raw_data.iterrows():
            if any("METRICS_DATE" in str(cell).upper() for cell in row.values):
                header_row_idx = i
                break
        
        if header_row_idx == -1:
            st.error("❌ Invalid Format: Could not find 'METRICS_DATE'.")
            return None

        file.seek(0)
        df = pd.read_csv(file, skiprows=header_row_idx, encoding='latin1')
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Clean numeric data
        num_cols = ['TOTAL_GMV', 'TOTAL_BUDGET_BURNT', 'TOTAL_CONVERSIONS', 'TOTAL_IMPRESSIONS', 'TOTAL_CLICKS']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        # Date processing
        if 'METRICS_DATE' in df.columns:
            df['METRICS_DATE'] = pd.to_datetime(df['METRICS_DATE'], errors='coerce')
            df = df.dropna(subset=['METRICS_DATE'])
            df['Day_Name'] = df['METRICS_DATE'].dt.day_name()
            df['Day_Num'] = df['METRICS_DATE'].dt.dayofweek
            
        return df
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        return None

# --- Main App ---
uploaded_file = st.file_uploader("Upload Swiggy Granular CSV Report", type=['csv'])

if uploaded_file:
    df = load_data_expert(uploaded_file)
    
    if df is not None:
        # Category Mapping
        def map_item_type(name):
            n = str(name).lower()
            if 'palappam' in n: return 'INSTANT PALAPPAM'
            if any(x in n for x in ['matta vadi', 'unda matta', 'matta unda']): return 'MATTA RICE'
            if 'puttu podi' in n: return 'PUTTU PODI'
            if any(x in n for x in ['appam', 'idiyappam', 'pathiri']): return 'APPAM, IDIYAPPAM'
            return 'OTHERS'
        df['ITEM_TYPE'] = df['PRODUCT_NAME'].apply(map_item_type)

        # Sidebar Filters
        st.sidebar.header("Strategy Filters")
        cities = sorted(df['CITY'].unique())
        sel_cities = st.sidebar.multiselect("Cities", cities, default=cities)
        cats = sorted(df['ITEM_TYPE'].unique())
        sel_cats = st.sidebar.multiselect("Categories", cats, default=cats)
        
        # Apply filters
        filtered = df[(df['CITY'].isin(sel_cities)) & (df['ITEM_TYPE'].isin(sel_cats))]

        # Top KPI Metrics
        m1, m2, m3, m4 = st.columns(4)
        total_gmv = filtered['TOTAL_GMV'].sum()
        total_spend = filtered['TOTAL_BUDGET_BURNT'].sum()
        m1.metric("Total GMV", f"₹{total_gmv:,.2f}")
        m2.metric("Total Spend", f"₹{total_spend:,.2f}")
        m3.metric("Combined ROAS", f"{(total_gmv/total_spend if total_spend > 0 else 0):.2f}x")
        m4.metric("Orders", int(filtered['TOTAL_CONVERSIONS'].sum()))

        # Navigation Tabs
        t1, t2, t3, t4, t5 = st.tabs([
            "📅 Weekly Trends", 
            "🛑 Spend Wastage", 
            "👻 Zero Reach", 
            "✅ Winning Keywords", 
            "📍 Regional View"
        ])

        with t1:
            st.subheader("Revenue vs Investment by Day")
            weekly = filtered.groupby(['Day_Num', 'Day_Name']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum'}).reset_index().sort_values('Day_Num')
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

            fig1 = px.bar(weekly, x='Day_Name', y='TOTAL_GMV', title="Daily Revenue (GMV)", category_orders={"Day_Name": day_order}, text_auto='.2s')
            fig1.update_traces(marker_color='#B7E4C7')
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = px.bar(weekly, x='Day_Name', y='TOTAL_BUDGET_BURNT', title="Daily Spend", category_orders={"Day_Name": day_order}, text_auto='.2s')
            fig2.update_traces(marker_color='#A2D2FF')
            st.plotly_chart(fig2, use_container_width=True)

        with t2:
            st.subheader("🛑 Spend Wastage (By Campaign & Keyword)")
            st.error("Budget spent on Keywords that generated ₹0 Sales.")
            # Added CAMPAIGN_NAME to group to avoid confusion
            wastage = filtered[filtered['TOTAL_GMV'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_IMPRESSIONS': 'sum', 'TOTAL_CLICKS': 'sum'
            }).reset_index()
            
            if not wastage.empty:
                st.dataframe(wastage.sort_values('TOTAL_BUDGET_BURNT', ascending=False), use_container_width=True)
            else:
                st.success("No wastage found!")

        with t3:
            st.subheader("👻 Zero Reach (Low Bid Warning)")
            st.warning("Keywords with 0 Impressions (not getting shown to users).")
            # Added CAMPAIGN_NAME here too
            zero_reach = filtered[filtered['TOTAL_IMPRESSIONS'] == 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).size().reset_index(name='Occurrences')
            if not zero_reach.empty:
                st.dataframe(zero_reach, use_container_width=True)
            else:
                st.info("✅ All active keywords are receiving reach.")

        with t4:
            st.subheader("✅ Winning Keywords (By Campaign & Keyword)")
            st.success("Keywords that successfully generated Sales.")
            # Added CAMPAIGN_NAME to group to show specifically which campaign won
            winners = filtered[filtered['TOTAL_GMV'] > 0].groupby(['CAMPAIGN_NAME', 'KEYWORD']).agg({
                'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'
            }).reset_index()
            
            if not winners.empty:
                winners['ROAS'] = (winners['TOTAL_GMV'] / winners['TOTAL_BUDGET_BURNT']).round(2)
                st.dataframe(winners.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)
            else:
                st.warning("No converting keywords found.")

        with t5:
            st.subheader("📍 Performance by City & Category")
            reg = filtered.groupby(['CITY', 'ITEM_TYPE']).agg({'TOTAL_GMV': 'sum', 'TOTAL_BUDGET_BURNT': 'sum', 'TOTAL_CONVERSIONS': 'sum'}).reset_index()
            st.dataframe(reg.sort_values('TOTAL_GMV', ascending=False), use_container_width=True)

    else:
        st.info("Please upload a valid Swiggy report.")
else:
    st.info("Upload Swiggy Granular CSV to begin.")
