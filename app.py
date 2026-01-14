import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from thefuzz import process

# 1. PAGE SETUP
st.set_page_config(page_title="Swiggy Granular Summary by Prabal", layout="wide")

def main():
    st.title("🚀 Swiggy Granular Summary by Prabal")
    st.markdown("Comprehensive Performance Analysis, Regional Intelligence, and Strategic Bidding Engine.")

    # 2. SIDEBAR - ALL FILTERS
    st.sidebar.header("🎯 Strategy Parameters")
    target_roas = st.sidebar.slider("ROAS Threshold (Global Target)", 0.5, 10.0, 1.4, step=0.1)
    min_spend_waste = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    uploaded_files = st.file_uploader("Upload Blinkit or Swiggy Reports", type=['csv', 'xlsx'], accept_multiple_files=True)

    if uploaded_files:
        all_dfs = []
        for file in uploaded_files:
            try:
                if file.name.endswith('.xlsx'):
                    xl = pd.ExcelFile(file)
                    for sheet in xl.sheet_names:
                        df = pd.read_excel(file, sheet_name=sheet)
                        all_dfs.append(df)
                else:
                    # Smart Header Detection (Robust for Instamart Granular)
                    content = file.read().decode('utf-8')
                    file.seek(0)
                    lines = content.split('\n')
                    header_row = 0
                    for i, line in enumerate(lines):
                        check_line = line.upper()
                        # Real headers usually have at least 2 of these keywords
                        matches = sum(1 for k in ["METRICS_DATE", "CAMPAIGN_NAME", "TOTAL_GMV", "TOTAL_BUDGET", "PRODUCT_NAME", "KEYWORD"] if k in check_line)
                        if matches >= 2:
                            header_row = i
                            break
                    df = pd.read_csv(file, skiprows=header_row)
                    all_dfs.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_dfs:
            master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
            master_df.columns = master_df.columns.str.strip()
            
            # --- COMPREHENSIVE MAPPING (Preserving all fields) ---
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

            # Define Target (Keyword/Product Hierarchy)
            if 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
            elif 'Product Name' in master_df.columns: master_df['Target'] = master_df['Product Name']
            else: master_df['Target'] = "General/Unknown"

            # --- DATA CLEANING ---
            numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions', 'Conversions', 'Clicks', 'STR (%)']
            for col in numeric_cols:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col].astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

            # Derive CVR (%)
            master_df['CVR (%)'] = (master_df['Conversions'] / master_df['Clicks'].replace(0, 1)) * 100

            # Date & Day
            if 'date_ist' in master_df.columns:
                master_df['date_ist'] = pd.to_datetime(master_df['date_ist'], errors='coerce')
                master_df = master_df.dropna(subset=['date_ist'])
                master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

            # --- SEARCH & FILTER ---
            st.sidebar.markdown("---")
            all_campaigns = sorted([str(x) for x in master_df['Campaign Name'].dropna().unique()])
            search_query = st.sidebar.text_input("🔍 Search Campaign", "")
            if search_query:
                matches = process.extract(search_query, all_campaigns, limit=10)
                filtered_options = ["All Campaigns"] + [match[0] for match in matches if match[1] > 45]
            else:
                filtered_options = ["All Campaigns"] + all_campaigns
            
            selected_campaign = st.sidebar.selectbox("Select Campaign", filtered_options)
            plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

            if not plot_df.empty:
                # --- AGGREGATION ---
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

                # --- TABS ---
                tab_trend, tab_perf, tab_reg, tab_eff, tab_bids = st.tabs([
                    "📅 Weekly Trends", "🏆 Performance Summary", "📍 Regional Intelligence", "🛑 Waste Audit", "⚖️ Bidding Strategy"
                ])

                with tab_trend:
                    st.subheader("Weekly Trend Analysis")
                    if 'Day of Week' in plot_df.columns:
                        weekly_data = plot_df.groupby('Day of Week', observed=False).agg({'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum'}).reset_index()
                        weekly_data['ROAS'] = weekly_data['Direct Sales'] / weekly_data['Estimated Budget Consumed'].replace(0, 1)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Estimated Budget Consumed'], name='Spend (₹)', marker_color='#4A90E2'))
                        fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Direct Sales'], name='Sales (₹)', marker_color='#50E3C2'))
                        fig.add_trace(go.Scatter(x=weekly_data['Day of Week'], y=weekly_data['ROAS'], name='ROAS Trend', yaxis='y2', line=dict(color='#D42D2D', width=4)))
                        
                        fig.update_layout(yaxis2=dict(title='ROAS', overlaying='y', side='right', showgrid=False), barmode='group')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Summary Text
                        best_day = weekly_data.loc[weekly_data['ROAS'].idxmax()]['Day of Week']
                        st.info(f"💡 **Insight:** Your highest efficiency (ROAS) occurs on **{best_day}**. Consider increasing budgets for this day.")

                with tab_perf:
                    st.subheader("Product & Keyword Efficiency")
                    summary_sorted = summary_df.sort_values(by='Direct Sales', ascending=False)
                    c1, c2 = st.columns(2)
                    c1.success(f"**Healthy (ROAS >= {target_roas})**")
                    c1.dataframe(summary_sorted[summary_sorted['Aggregated ROAS'] >= target_roas], use_container_width=True)
                    c2.error(f"**Below Target**")
                    c2.dataframe(summary_sorted[summary_sorted['Aggregated ROAS'] < target_roas], use_container_width=True)

                with tab_reg:
                    st.subheader("Regional Deep-Dive (City-wise)")
                    if 'Region' in plot_df.columns:
                        # REGION SUMMARY (Region Repeated, Product Unique)
                        reg_summary = plot_df.groupby(['Region', 'Target']).agg({
                            'Estimated Budget Consumed': 'sum',
                            'Direct Sales': 'sum',
                            'Direct RoAS': 'mean',
                            'CVR (%)': 'mean',
                            'STR (%)': 'mean'
                        }).reset_index().sort_values(['Region', 'Direct Sales'], ascending=[True, False])

                        st.dataframe(reg_summary.style.background_gradient(subset=['Direct Sales'], cmap='Greens')
                                                 .background_gradient(subset=['Estimated Budget Consumed'], cmap='Oranges')
                                                 .format({'Estimated Budget Consumed': '₹{:.2f}', 'Direct Sales': '₹{:.2f}', 'Direct RoAS': '{:.2f}x', 'CVR (%)': '{:.2f}%', 'STR (%)': '{:.2f}%'}), 
                                     use_container_width=True, height=600)

                with tab_eff:
                    st.subheader("Waste Audit")
                    pause_logic = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                    st.warning(f"Found {len(pause_logic)} unique items with zero sales and spend > ₹{min_spend_waste}")
                    st.dataframe(pause_logic.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True)

                with tab_bids:
                    st.subheader("Bidding Logic")
                    avg_cpm = summary_df['CPM'].mean()
                    cpm_opt = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                    st.info(f"Targeting ROAS >= {target_roas}. Reduce bids for these high-cost items.")
                    st.dataframe(cpm_opt, use_container_width=True)

                # Export
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    summary_df.to_excel(writer, index=False, sheet_name='Main_Strategy')
                    if 'Region' in plot_df.columns:
                        reg_summary.to_excel(writer, index=False, sheet_name='Regional_Summary')
                st.download_button("📥 Download Full Strategy", data=buffer.getvalue(), file_name="swiggy_granular_summary.xlsx")
