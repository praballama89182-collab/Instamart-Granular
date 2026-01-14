import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from thefuzz import process

# 1. PAGE SETUP
st.set_page_config(page_title="Quick-Commerce Ads Intelligence", layout="wide")

def main():
    st.title("🚀 Swiggy & Blinkit Strategic Decision Engine")
    st.markdown("Analyze Performance, Weekly Trends, and Bidding Strategy across Quick-Commerce platforms.")

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
                    # FIX: Dynamic Header Detection for Granular Swiggy/Blinkit Reports
                    # Swiggy often puts filters in the first few rows. We find the real header row.
                    content = file.read().decode('utf-8')
                    file.seek(0) # Reset pointer
                    
                    header_row = 0
                    lines = content.split('\n')
                    # Look for keywords that define the start of the data table
                    for i, line in enumerate(lines):
                        if any(key in line for key in ["METRICS_DATE", "Campaign Name", "date_ist", "CAMPAIGN_NAME"]):
                            header_row = i
                            break
                    
                    df = pd.read_csv(file, skiprows=header_row)
                    all_dfs.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_dfs:
            # 3. CONSOLIDATION & MAPPING
            master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
            master_df.columns = master_df.columns.str.strip()

            # --- DYNAMIC MAPPING (Swiggy to Blinkit Standard) ---
            mapping = {
                'METRICS_DATE': 'date_ist',
                'CAMPAIGN_NAME': 'Campaign Name',
                'TOTAL_GMV': 'Direct Sales',
                'TOTAL_BUDGET_BURNT': 'Estimated Budget Consumed',
                'eCPM': 'CPM',
                'TOTAL_ROI': 'Direct RoAS',
                'TOTAL_IMPRESSIONS': 'Impressions'
            }
            master_df = master_df.rename(columns=mapping)

            # Mapping Target Identifiers (Hierarchy: Keyword > Product > L1 Category)
            if 'KEYWORD' in master_df.columns: master_df['Target'] = master_df['KEYWORD']
            elif 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
            elif 'PRODUCT_NAME' in master_df.columns: master_df['Target'] = master_df['PRODUCT_NAME']
            elif 'Category Name' in master_df.columns: master_df['Target'] = master_df['Category Name']
            else: master_df['Target'] = "Unknown"

            # Clean Target names
            master_df['Target'] = master_df['Target'].fillna("General/Unknown")

            # Date Conversion and Weekly Sorting
            if 'date_ist' in master_df.columns:
                master_df['date_ist'] = pd.to_datetime(master_df['date_ist'], errors='coerce')
                # Drop rows where date conversion failed
                master_df = master_df.dropna(subset=['date_ist'])
                master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

            # Numeric Conversion
            numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions']
            for col in numeric_cols:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

            # --- FUZZY SEARCH FOR CAMPAIGNS ---
            st.sidebar.markdown("---")
            st.sidebar.header("🔍 Search Campaign")
            # Filter out empty names
            all_campaigns = sorted([str(x) for x in master_df['Campaign Name'].dropna().unique()])
            search_query = st.sidebar.text_input("Type to find similar campaigns", "")
            
            if search_query:
                matches = process.extract(search_query, all_campaigns, limit=10)
                filtered_options = [match[0] for match in matches if match[1] > 45]
                campaign_options = ["All Campaigns"] + filtered_options
            else:
                campaign_options = ["All Campaigns"] + all_campaigns
            
            selected_campaign = st.sidebar.selectbox("Select Campaign", campaign_options)

            # Filter data for display
            plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

            # --- AGGREGATION LOGIC ---
            if not plot_df.empty:
                summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                    'Direct Sales': 'sum',
                    'Estimated Budget Consumed': 'sum',
                    'Impressions': 'sum',
                    'CPM': 'mean',
                    'Direct RoAS': 'mean'
                })
                # Re-calculate ROAS precisely
                summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

                # --- TABS ---
                tab_trend, tab_perf, tab_eff, tab_bids = st.tabs(["📅 Weekly Trends", "🏆 Performance Summary", "🛑 Waste Audit", "⚖️ Bidding Strategy"])

                with tab_trend:
                    st.header(f"Weekly Trend Analysis: {selected_campaign}")
                    if 'Day of Week' in plot_df.columns and not plot_df.empty:
                        weekly_data = plot_df.groupby('Day of Week', observed=False).agg({
                            'Estimated Budget Consumed': 'sum',
                            'Direct Sales': 'sum'
                        }).reset_index()

                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Estimated Budget Consumed'], 
                                             name='Budget Spent (₹)', marker_color='#4A90E2'))
                        fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Direct Sales'], 
                                             name='Direct Sales (₹)', marker_color='#50E3C2'))
                        
                        weekly_data['ROAS'] = weekly_data['Direct Sales'] / weekly_data['Estimated Budget Consumed'].replace(0, 1)
                        fig.add_trace(go.Scatter(x=weekly_data['Day of Week'], y=weekly_data['ROAS'], 
                                                 name='ROAS Trend', yaxis='y2', line=dict(color='#AB63FA', width=4)))

                        fig.update_layout(
                            title='Daily Spent vs Sales (Mon to Sun)',
                            xaxis_title='Day of the Week',
                            yaxis=dict(title='Amount (₹)'),
                            yaxis2=dict(title='ROAS Efficiency', overlaying='y', side='right', showgrid=False),
                            barmode='group',
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Missing date data for weekly analysis.")

                with tab_perf:
                    st.subheader("Performance Breakdown")
                    summary_sorted = summary_df.sort_values(by='Direct Sales', ascending=False)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.success(f"**Healthy Assets (ROAS >= {target_roas})**")
                        above_df = summary_sorted[summary_sorted['Aggregated ROAS'] >= target_roas]
                        st.dataframe(above_df, use_container_width=True, height=500)
                    with c2:
                        st.error(f"**Below Target (ROAS < {target_roas})**")
                        below_df = summary_sorted[(summary_sorted['Aggregated ROAS'] < target_roas) & (summary_sorted['Aggregated ROAS'] > 0)]
                        st.dataframe(below_df, use_container_width=True, height=500)

                with tab_eff:
                    st.subheader("Waste Audit")
                    pause_logic = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                    st.warning(f"Found {len(pause_logic)} unique items with high spend and zero sales.")
                    st.dataframe(pause_logic.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True, height=500)

                with tab_bids:
                    st.subheader("Bidding Logic (CPM Optimization)")
                    avg_cpm = summary_df['CPM'].mean()
                    cpm_opt = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                    st.info(f"Targeting ROAS >= {target_roas}. High-volume items suggested for bid reduction.")
                    st.dataframe(cpm_opt, use_container_width=True, height=600)

                # 5. EXPORT
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    summary_df.to_excel(writer, index=False, sheet_name='Strategic_Summary')
                st.download_button("📥 Download Final Strategy", data=buffer.getvalue(), file_name="quick_commerce_strategy.xlsx")
            else:
                st.warning("No data found for the selected campaign.")

if __name__ == "__main__":
    main()
