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
                    # IMPROVED: Smart Header Detection
                    # We look for the row that has the most 'Metric' keywords to avoid metadata rows
                    content = file.read().decode('utf-8')
                    file.seek(0)
                    lines = content.split('\n')
                    
                    header_row = 0
                    for i, line in enumerate(lines):
                        check_line = line.upper()
                        # Count matches for actual data columns
                        matches = sum(1 for k in ["METRICS_DATE", "CAMPAIGN_NAME", "TOTAL_GMV", "TOTAL_BUDGET", "PRODUCT_NAME", "KEYWORD"] if k in check_line)
                        if matches >= 2: # Real headers usually have at least 2-3 of these
                            header_row = i
                            break
                    
                    df = pd.read_csv(file, skiprows=header_row)
                    all_dfs.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_dfs:
            master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
            master_df.columns = master_df.columns.str.strip()
            
            # --- EXPANDED DYNAMIC MAPPING ---
            mapping = {
                'METRICS_DATE': 'date_ist',
                'Date': 'date_ist',
                'CAMPAIGN_NAME': 'Campaign Name',
                'campaign_name': 'Campaign Name',
                'Campaign': 'Campaign Name',
                'TOTAL_GMV': 'Direct Sales',
                'Sales': 'Direct Sales',
                'TOTAL_BUDGET_BURNT': 'Estimated Budget Consumed',
                'Spend': 'Estimated Budget Consumed',
                'eCPM': 'CPM',
                'TOTAL_ROI': 'Direct RoAS',
                'RoAS': 'Direct RoAS',
                'TOTAL_IMPRESSIONS': 'Impressions'
            }
            master_df = master_df.rename(columns=mapping)

            # --- TARGET MAPPING ---
            if 'KEYWORD' in master_df.columns: master_df['Target'] = master_df['KEYWORD']
            elif 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
            elif 'PRODUCT_NAME' in master_df.columns: master_df['Target'] = master_df['PRODUCT_NAME']
            elif 'Category Name' in master_df.columns: master_df['Target'] = master_df['Category Name']
            else: master_df['Target'] = "General/Unknown"

            # --- SAFETY CHECK ---
            if 'Campaign Name' not in master_df.columns:
                st.error("🚨 'Campaign Name' column not found.")
                st.write("Columns found after processing:", list(master_df.columns))
                return

            # Data Cleaning
            if 'date_ist' in master_df.columns:
                master_df['date_ist'] = pd.to_datetime(master_df['date_ist'], errors='coerce')
                master_df = master_df.dropna(subset=['date_ist'])
                master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

            for col in ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions']:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

            # --- UI: FUZZY SEARCH ---
            st.sidebar.markdown("---")
            st.sidebar.header("🔍 Search Campaign")
            all_campaigns = sorted([str(x) for x in master_df['Campaign Name'].dropna().unique()])
            search_query = st.sidebar.text_input("Find campaign...", "")
            
            if search_query:
                matches = process.extract(search_query, all_campaigns, limit=10)
                filtered_options = [match[0] for match in matches if match[1] > 45]
                campaign_options = ["All Campaigns"] + filtered_options
            else:
                campaign_options = ["All Campaigns"] + all_campaigns
            
            selected_campaign = st.sidebar.selectbox("Select Campaign", campaign_options)
            plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

            if not plot_df.empty:
                # Aggregation
                summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                    'Direct Sales': 'sum',
                    'Estimated Budget Consumed': 'sum',
                    'Impressions': 'sum',
                    'CPM': 'mean',
                    'Direct RoAS': 'mean'
                })
                summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

                tab_trend, tab_perf, tab_eff, tab_bids = st.tabs(["📅 Weekly Trends", "🏆 Performance Summary", "🛑 Waste Audit", "⚖️ Bidding Strategy"])

                with tab_trend:
                    if 'Day of Week' in plot_df.columns:
                        weekly_data = plot_df.groupby('Day of Week', observed=False).agg({'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum'}).reset_index()
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Estimated Budget Consumed'], name='Spend'))
                        fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Direct Sales'], name='Sales'))
                        st.plotly_chart(fig, use_container_width=True)

                with tab_perf:
                    summary_sorted = summary_df.sort_values(by='Direct Sales', ascending=False)
                    c1, c2 = st.columns(2)
                    c1.success(f"**Healthy (ROAS >= {target_roas})**")
                    c1.dataframe(summary_sorted[summary_sorted['Aggregated ROAS'] >= target_roas], use_container_width=True)
                    c2.error(f"**Below Target**")
                    c2.dataframe(summary_sorted[summary_sorted['Aggregated ROAS'] < target_roas], use_container_width=True)

                with tab_eff:
                    pause_logic = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                    st.dataframe(pause_logic.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True)

                with tab_bids:
                    avg_cpm = summary_df['CPM'].mean()
                    cpm_opt = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                    st.dataframe(cpm_opt, use_container_width=True)

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    summary_df.to_excel(writer, index=False, sheet_name='Strategy')
                st.download_button("📥 Download Strategy", data=buffer.getvalue(), file_name="ad_strategy.xlsx")

if __name__ == "__main__":
    main()
