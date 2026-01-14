import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

# 1. PAGE SETUP
st.set_page_config(page_title="Swiggy Granular Summary by Prabal", layout="wide")

def main():
    # Title is outside any 'if' block to ensure the app renders something immediately
    st.title("🚀 Swiggy Granular Summary by Prabal")
    st.markdown("Comprehensive Performance Analysis, Regional Intelligence, and Strategic Bidding Engine.")

    # 2. SIDEBAR - PARAMETERS
    st.sidebar.header("🎯 Strategy Parameters")
    target_roas = st.sidebar.slider("ROAS Threshold (Global Target)", 0.5, 10.0, 1.4, step=0.1)
    min_spend_waste = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    # 3. FILE UPLOADER
    uploaded_files = st.file_uploader("Upload Blinkit or Swiggy Reports (CSV/XLSX)", type=['csv', 'xlsx'], accept_multiple_files=True)

    if not uploaded_files:
        st.info("👋 Welcome! Please upload your granular reports to begin analysis.")
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
                # Robust Header Detection
                content = file.read().decode('utf-8', errors='ignore')
                file.seek(0)
                lines = content.split('\n')
                header_row = 0
                for i, line in enumerate(lines[:20]): # Check first 20 rows
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
        
        # --- MAPPING ---
        mapping = {
            'METRICS_DATE': 'date_ist', 'CAMPAIGN_NAME': 'Campaign Name',
            'TOTAL_GMV': 'Direct Sales', 'TOTAL_BUDGET_BURNT': 'Estimated Budget Consumed',
            'eCPM': 'CPM', 'TOTAL_ROI': 'Direct RoAS', 'TOTAL_IMPRESSIONS': 'Impressions',
            'TOTAL_CONVERSIONS': 'Conversions', 'TOTAL_CLICKS': 'Clicks',
            'TOTAL_CTR': 'STR (%)', 'CITY': 'Region', 'PRODUCT_NAME': 'Product Name', 'KEYWORD': 'Keyword'
        }
        master_df = master_df.rename(columns=mapping)

        # Hierarchy for 'Target'
        if 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
        elif 'Product Name' in master_df.columns: master_df['Target'] = master_df['Product Name']
        else: master_df['Target'] = "Unknown"

        # --- CLEANING ---
        num_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions', 'Conversions', 'Clicks', 'STR (%)']
        for col in num_cols:
            if col in master_df.columns:
                master_df[col] = pd.to_numeric(master_df[col].astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

        master_df['CVR (%)'] = (master_df['Conversions'] / master_df['Clicks'].replace(0, 1)) * 100

        if 'date_ist' in master_df.columns:
            master_df['date_ist'] = pd.to_datetime(master_df['date_ist'], errors='coerce')
            master_df = master_df.dropna(subset=['date_ist'])
            master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

        # --- SEARCH FILTER (Simple search instead of fuzzy to prevent crashes) ---
        st.sidebar.markdown("---")
        all_camps = sorted([str(x) for x in master_df['Campaign Name'].dropna().unique()])
        search_query = st.sidebar.text_input("🔍 Filter Campaign Name", "").lower()
        
        filtered_camps = [c for c in all_camps if search_query in c.lower()] if search_query else all_camps
        selected_campaign = st.sidebar.selectbox("Select Campaign", ["All Campaigns"] + filtered_camps)
        
        plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

        if not plot_df.empty:
            # AGGREGATION
            summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                'Direct Sales': 'sum', 'Estimated Budget Consumed': 'sum', 'Impressions': 'sum',
                'CPM': 'mean', 'Direct RoAS': 'mean', 'CVR (%)': 'mean', 'STR (%)': 'mean'
            })
            summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

            # --- TABS ---
            t1, t2, t3, t4, t5 = st.tabs(["📅 Trends", "🏆 Performance", "📍 Regions", "🛑 Waste", "⚖️ Bids"])

            with t1:
                if 'Day of Week' in plot_df.columns:
                    wd = plot_df.groupby('Day of Week', observed=False).agg({'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum'}).reset_index()
                    wd['ROAS'] = wd['Direct Sales'] / wd['Estimated Budget Consumed'].replace(0, 1)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Estimated Budget Consumed'], name='Spend', marker_color='#4A90E2'))
                    fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Direct Sales'], name='Sales', marker_color='#50E3C2'))
                    fig.add_trace(go.Scatter(x=wd['Day of Week'], y=wd['ROAS'], name='ROAS', yaxis='y2', line=dict(color='red', width=3)))
                    fig.update_layout(yaxis2=dict(overlaying='y', side='right'))
                    st.plotly_chart(fig, use_container_width=True)

            with t2:
                ss = summary_df.sort_values('Direct Sales', ascending=False)
                c1, c2 = st.columns(2)
                c1.success("Healthy Assets")
                c1.dataframe(ss[ss['Aggregated ROAS'] >= target_roas], use_container_width=True)
                c2.error("Action Needed")
                c2.dataframe(ss[ss['Aggregated ROAS'] < target_roas], use_container_width=True)

            with t3:
                if 'Region' in plot_df.columns:
                    reg = plot_df.groupby(['Region', 'Target']).agg({
                        'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum',
                        'Direct RoAS': 'mean', 'CVR (%)': 'mean', 'STR (%)': 'mean'
                    }).reset_index().sort_values(['Region', 'Direct Sales'], ascending=[True, False])
                    st.dataframe(reg.style.background_gradient(subset=['Direct Sales'], cmap='Greens'), use_container_width=True)

            with t4:
                waste = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                st.dataframe(waste.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True)

            with t5:
                avg_cpm = summary_df['CPM'].mean()
                bids = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                st.dataframe(bids, use_container_width=True)

            # EXPORT
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                summary_df.to_excel(wr, index=False, sheet_name='Summary')
                if 'Region' in plot_df.columns: reg.to_excel(wr, index=False, sheet_name='Regional')
            st.download_button("📥 Download Full Report", data=buf.getvalue(), file_name="analysis.xlsx")
        else:
            st.warning("No data found for this selection.")

if __name__ == "__main__":
    main()
