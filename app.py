import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

# 1. PAGE SETUP
st.set_page_config(page_title="Swiggy Granular Summary by Prabal", layout="wide")

def main():
    st.title("🚀 Swiggy Granular Summary by Prabal")
    st.markdown("Comprehensive Performance Analysis, Regional Intelligence, and Strategic Bidding Engine.")

    # 2. SIDEBAR - PARAMETERS
    st.sidebar.header("🎯 Strategy Parameters")
    target_roas = st.sidebar.slider("ROAS Threshold (Global Target)", 0.5, 10.0, 1.4, step=0.1)
    min_spend_waste = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    # 3. FILE UPLOADER
    uploaded_files = st.file_uploader("Upload Swiggy Granular CSV", type=['csv'], accept_multiple_files=True)

    if not uploaded_files:
        st.info("👋 Upload the 'IM_GRANULAR' CSV file to generate the dashboard.")
        return

    all_dfs = []
    for file in uploaded_files:
        try:
            # Smart Header Detection for Instamart Granular Reports
            content = file.read().decode('utf-8', errors='ignore')
            file.seek(0)
            lines = content.split('\n')
            
            header_row = 0
            for i, line in enumerate(lines[:15]):
                if "METRICS_DATE" in line.upper() and "TOTAL_GMV" in line.upper():
                    header_row = i
                    break
            
            df = pd.read_csv(file, skiprows=header_row)
            all_dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    if all_dfs:
        master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
        master_df.columns = master_df.columns.str.strip()
        
        # --- MAPPING TO YOUR STANDARDS ---
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

        # Hierarchy for Target
        if 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
        elif 'Product Name' in master_df.columns: master_df['Target'] = master_df['Product Name']
        else: master_df['Target'] = "Unknown"

        # --- NUMERIC CLEANING ---
        num_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions', 'Conversions', 'Clicks', 'STR (%)']
        for col in num_cols:
            if col in master_df.columns:
                master_df[col] = pd.to_numeric(master_df[col].astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

        master_df['CVR (%)'] = (master_df['Conversions'] / master_df['Clicks'].replace(0, 1)) * 100

        # Date & Weekly Sorting
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
            summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                'Direct Sales': 'sum', 'Estimated Budget Consumed': 'sum', 'Impressions': 'sum',
                'CPM': 'mean', 'Direct RoAS': 'mean', 'CVR (%)': 'mean', 'STR (%)': 'mean'
            })
            summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

            # --- TABS ---
            t1, t2, t3, t4, t5 = st.tabs(["📅 Trends", "🏆 Performance", "📍 Regional Summary", "🛑 Waste Audit", "⚖️ Bidding"])

            with t1:
                # Chart with Trendline
                wd = plot_df.groupby('Day of Week', observed=False).agg({'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum'}).reset_index()
                wd['ROAS'] = wd['Direct Sales'] / wd['Estimated Budget Consumed'].replace(0, 1)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Estimated Budget Consumed'], name='Spend', marker_color='#4A90E2'))
                fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Direct Sales'], name='Sales', marker_color='#50E3C2'))
                fig.add_trace(go.Scatter(x=wd['Day of Week'], y=wd['ROAS'], name='ROAS Trend', yaxis='y2', line=dict(color='red', width=3)))
                fig.update_layout(title="Daily Performance & Efficiency", yaxis2=dict(overlaying='y', side='right', title="ROAS"))
                st.plotly_chart(fig, use_container_width=True)
                
                best_day = wd.loc[wd['ROAS'].idxmax()]['Day of Week']
                st.info(f"💡 Best Efficiency Day: **{best_day}**")

            with t2:
                # Original Performance fields
                st.dataframe(summary_df.sort_values('Direct Sales', ascending=False), use_container_width=True)

            with t3:
                # NEW Regional Summary: Region Repeated, Unique Product
                if 'Region' in plot_df.columns:
                    reg_sum = plot_df.groupby(['Region', 'Target']).agg({
                        'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum',
                        'Direct RoAS': 'mean', 'CVR (%)': 'mean', 'STR (%)': 'mean'
                    }).reset_index().sort_values(['Region', 'Direct Sales'], ascending=[True, False])
                    st.dataframe(reg_sum.style.background_gradient(subset=['Direct Sales'], cmap='Greens'), use_container_width=True)

            with t4:
                # Waste Audit
                waste = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                st.warning(f"Found {len(waste)} items wasting budget.")
                st.dataframe(waste.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True)

            with t5:
                # Bidding Strategy
                avg_cpm = summary_df['CPM'].mean()
                bids = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                st.dataframe(bids, use_container_width=True)

            # EXPORT
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                summary_df.to_excel(wr, index=False, sheet_name='Summary')
                if 'Region' in plot_df.columns: reg_sum.to_excel(wr, index=False, sheet_name='Regional')
            st.download_button("📥 Download Full Analysis", data=buf.getvalue(), file_name="swiggy_report.xlsx")

if __name__ == "__main__":
    main()
