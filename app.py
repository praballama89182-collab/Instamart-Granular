import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

# 1. PAGE SETUP
st.set_page_config(page_title="Swiggy Granular Summary by Prabal", layout="wide")

# Professional Theme Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_headers=True)

def clean_numeric(val):
    """Handles raw report strings like '0.00%' or 'NA' and converts them to floats."""
    if pd.isna(val) or val == 'NA' or val == '':
        return 0.0
    if isinstance(val, str):
        val = val.replace('%', '').replace(',', '')
    try:
        return float(val)
    except:
        return 0.0

def main():
    st.title("🚀 Swiggy Granular Summary by Prabal")
    st.markdown("### Strategic Performance & Regional Intelligence Dashboard")

    # 2. SIDEBAR - PARAMETERS
    st.sidebar.header("🎯 Strategy Parameters")
    target_roas = st.sidebar.slider("ROAS Threshold (Global Target)", 0.5, 10.0, 1.4, step=0.1)
    min_spend_waste = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    # 3. FILE UPLOADER
    uploaded_files = st.file_uploader("Upload Granular Reports (CSV/XLSX)", type=['csv', 'xlsx'], accept_multiple_files=True)

    if not uploaded_files:
        st.info("👋 Welcome! Please upload your reports to begin the analysis.")
        return

    # 4. DATA PROCESSING
    all_dfs = []
    for file in uploaded_files:
        try:
            if file.name.endswith('.xlsx'):
                xl = pd.ExcelFile(file)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(file, sheet_name=sheet)
                    all_dfs.append(df)
            else:
                # Dynamic Header Detection (Skips metadata automatically)
                content = file.read().decode('utf-8', errors='ignore')
                file.seek(0)
                lines = content.split('\n')
                header_row = 0
                for i, line in enumerate(lines[:20]):
                    check_line = line.upper()
                    if sum(1 for k in ["METRICS_DATE", "CAMPAIGN_NAME", "TOTAL_GMV", "TOTAL_BUDGET", "KEYWORD"] if k in check_line) >= 2:
                        header_row = i
                        break
                df = pd.read_csv(file, skiprows=header_row)
                all_dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    if all_dfs:
        master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
        master_df.columns = master_df.columns.str.strip()
        
        # --- COMPREHENSIVE MAPPING ---
        mapping = {
            'METRICS_DATE': 'date_ist', 
            'CAMPAIGN_NAME': 'Campaign Name',
            'TOTAL_GMV': 'Direct Sales', 
            'TOTAL_BUDGET_BURNT': 'Estimated Budget Consumed',
            'eCPM': 'CPM', 
            'TOTAL_ROI': 'Direct RoAS', 
            'TOTAL_IMPRESSIONS': 'Impressions',
            'TOTAL_CONVERSIONS': 'Conversions', 
            'TOTAL_CLICKS': 'Clicks',
            'TOTAL_CTR': 'STR (%)', 
            'CITY': 'Region', 
            'PRODUCT_NAME': 'Product Name', 
            'KEYWORD': 'Keyword'
        }
        master_df = master_df.rename(columns=mapping)

        # Unified Target Hierarchy
        if 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
        elif 'Product Name' in master_df.columns: master_df['Target'] = master_df['Product Name']
        else: master_df['Target'] = "Unknown"

        # --- DATA CLEANING & DERIVED METRICS ---
        numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions', 'Conversions', 'Clicks', 'STR (%)']
        for col in numeric_cols:
            if col in master_df.columns:
                master_df[col] = master_df[col].apply(clean_numeric)

        # Calculate CVR (%)
        master_df['CVR (%)'] = (master_df['Conversions'] / master_df['Clicks'].replace(0, 1)) * 100

        # Date & Weekly Alignment
        if 'date_ist' in master_df.columns:
            master_df['date_ist'] = pd.to_datetime(master_df['date_ist'], errors='coerce')
            master_df = master_df.dropna(subset=['date_ist'])
            master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

        # --- FILTERS ---
        all_camps = sorted([str(x) for x in master_df['Campaign Name'].dropna().unique()])
        selected_campaign = st.sidebar.selectbox("Select Campaign", ["All Campaigns"] + all_camps)
        plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

        if not plot_df.empty:
            # 5. CORE AGGREGATION
            summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                'Direct Sales': 'sum', 
                'Estimated Budget Consumed': 'sum', 
                'Impressions': 'sum',
                'CPM': 'mean', 
                'Direct RoAS': 'mean', 
                'CVR (%)': 'mean', 
                'STR (%)': 'mean'
            })
            summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

            # --- TABS: ORGANIZED FOR STRATEGY ---
            t1, t2, t3, t4, t5 = st.tabs(["📅 Trends", "🏆 Performance", "📍 Regions", "🛑 Waste", "⚖️ Bids"])

            with t1:
                # Professional Graph with Trendline
                wd = plot_df.groupby('Day of Week', observed=False).agg({'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum'}).reset_index()
                wd['ROAS'] = wd['Direct Sales'] / wd['Estimated Budget Consumed'].replace(0, 1)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Estimated Budget Consumed'], name='Spend (₹)', marker_color='#34495e'))
                fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Direct Sales'], name='Sales (₹)', marker_color='#2ecc71'))
                fig.add_trace(go.Scatter(x=wd['Day of Week'], y=wd['ROAS'], name='ROAS Trend', yaxis='y2', 
                                         line=dict(color='#e67e22', width=4, shape='spline'), marker=dict(size=8)))

                fig.update_layout(title="Daily Performance & ROAS Efficiency",
                                  yaxis=dict(title="Currency (₹)"),
                                  yaxis2=dict(title="Efficiency (ROAS)", overlaying='y', side='right', showgrid=False),
                                  barmode='group', plot_bgcolor='white')
                st.plotly_chart(fig, use_container_width=True)
                
                best_day = wd.loc[wd['ROAS'].idxmax()]['Day of Week']
                st.success(f"🌟 **Best Efficiency Day: {best_day}**")

            with t2:
                # Total Asset performance
                ss = summary_df.sort_values('Direct Sales', ascending=False)
                st.dataframe(ss.style.background_gradient(subset=['Aggregated ROAS'], cmap='RdYlGn'), use_container_width=True)

            with t3:
                # NEW REGIONAL INTELLIGENCE: Repeated Region, Unique Product
                if 'Region' in plot_df.columns:
                    reg_sum = plot_df.groupby(['Region', 'Target']).agg({
                        'Estimated Budget Consumed': 'sum', 
                        'Direct Sales': 'sum',
                        'Direct RoAS': 'mean', 
                        'CVR (%)': 'mean', 
                        'STR (%)': 'mean'
                    }).reset_index().sort_values(['Region', 'Direct Sales'], ascending=[True, False])

                    st.markdown("#### Region-Wise Product Performance")
                    st.dataframe(reg_sum.style.background_gradient(subset=['Direct Sales'], cmap='Greens')
                                             .background_gradient(subset=['Estimated Budget Consumed'], cmap='Oranges')
                                             .format({'Estimated Budget Consumed': '₹{:.2f}', 'Direct Sales': '₹{:.2f}', 
                                                      'Direct RoAS': '{:.2f}x', 'CVR (%)': '{:.2f}%', 'STR (%)': '{:.2f}%'}), 
                                 use_container_width=True, height=600)

            with t4:
                # Budget Waste Audit
                waste = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                st.warning(f"Found {len(waste)} items with zero sales and high spend.")
                st.dataframe(waste.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True)

            with t5:
                # Bidding Strategy (CPM Optimization)
                avg_cpm = summary_df['CPM'].mean()
                bids = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                st.info(f"Suggestions: These high-performing assets have an eCPM above the average (₹{avg_cpm:.2f}). Consider reducing bids.")
                st.dataframe(bids, use_container_width=True)

            # --- EXPORT ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                summary_df.to_excel(wr, index=False, sheet_name='Performance_Summary')
                if 'Region' in plot_df.columns:
                    reg_sum.to_excel(wr, index=False, sheet_name='Regional_Intelligence')
            st.download_button("📥 Download Strategic Analysis", data=buf.getvalue(), file_name="Swiggy_Full_Strategy.xlsx")

if __name__ == "__main__":
    main()
