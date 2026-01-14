import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

# 1. PAGE SETUP
st.set_page_config(page_title="Swiggy Granular Summary by Prabal", layout="wide")

# Custom CSS for a cleaner look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_headers=True)

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
            'METRICS_DATE': 'date_ist', 'CAMPAIGN_NAME': 'Campaign Name',
            'TOTAL_GMV': 'Direct Sales', 'TOTAL_BUDGET_BURNT': 'Estimated Budget Consumed',
            'eCPM': 'CPM', 'TOTAL_ROI': 'Direct RoAS', 'TOTAL_IMPRESSIONS': 'Impressions',
            'TOTAL_CONVERSIONS': 'Conversions', 'TOTAL_CLICKS': 'Clicks',
            'TOTAL_CTR': 'STR (%)', 'CITY': 'Region', 'PRODUCT_NAME': 'Product Name', 'KEYWORD': 'Keyword'
        }
        master_df = master_df.rename(columns=mapping)

        # Target Hierarchy
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

        # --- CAMPAIGN FILTER ---
        st.sidebar.markdown("---")
        all_camps = sorted([str(x) for x in master_df['Campaign Name'].dropna().unique()])
        search_query = st.sidebar.text_input("🔍 Filter Campaign", "").lower()
        filtered_camps = [c for c in all_camps if search_query in c.lower()] if search_query else all_camps
        selected_campaign = st.sidebar.selectbox("Select Campaign", ["All Campaigns"] + filtered_camps)
        
        plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

        if not plot_df.empty:
            # Aggregation for summaries
            summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                'Direct Sales': 'sum', 'Estimated Budget Consumed': 'sum', 'Impressions': 'sum',
                'CPM': 'mean', 'Direct RoAS': 'mean', 'CVR (%)': 'mean', 'STR (%)': 'mean'
            })
            summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

            # --- TABS ---
            t1, t2, t3, t4, t5 = st.tabs(["📅 Weekly Trends", "🏆 Performance", "📍 Regional Intelligence", "🛑 Waste Audit", "⚖️ Bids"])

            with t1:
                if 'Day of Week' in plot_df.columns:
                    wd = plot_df.groupby('Day of Week', observed=False).agg({'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum'}).reset_index()
                    wd['ROAS'] = wd['Direct Sales'] / wd['Estimated Budget Consumed'].replace(0, 1)
                    
                    # Professional Palette
                    COLOR_SPEND = '#34495e'  # Slate Grey
                    COLOR_SALES = '#2ecc71'  # Emerald Green
                    COLOR_ROAS  = '#e67e22'  # Carrot Orange

                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Estimated Budget Consumed'], name='Ad Spend', marker_color=COLOR_SPEND, opacity=0.85))
                    fig.add_trace(go.Bar(x=wd['Day of Week'], y=wd['Direct Sales'], name='Revenue', marker_color=COLOR_SALES, opacity=0.85))
                    fig.add_trace(go.Scatter(x=wd['Day of Week'], y=wd['ROAS'], name='ROAS Trend', yaxis='y2', 
                                             line=dict(color=COLOR_ROAS, width=4, shape='spline'),
                                             marker=dict(size=8, symbol='diamond')))

                    fig.update_layout(
                        title=dict(text=f"Weekly Performance: {selected_campaign}", font=dict(size=20)),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        hovermode='x unified',
                        margin=dict(t=80, b=40, l=50, r=50),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        yaxis=dict(title="Currency (₹)", gridcolor='#f0f0f0', showline=True, linecolor='#cccccc'),
                        yaxis2=dict(title="Efficiency (ROAS)", overlaying='y', side='right', showgrid=False, rangemode="tozero")
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Insights Metrics
                    c1, c2, c3 = st.columns(3)
                    best_day = wd.loc[wd['ROAS'].idxmax()]['Day of Week']
                    c1.metric("Top Efficiency Day", best_day)
                    c2.metric("Total Sales", f"₹{wd['Direct Sales'].sum():,.0f}")
                    c3.metric("Overall ROAS", f"{(wd['Direct Sales'].sum()/wd['Estimated Budget Consumed'].sum()):.2f}x")

            with t2:
                st.subheader("Asset Performance Summary")
                st.dataframe(summary_df.sort_values('Direct Sales', ascending=False).style.background_gradient(subset=['Aggregated ROAS'], cmap='RdYlGn'), use_container_width=True)

            with t3:
                st.subheader("📍 Regional Deep-Dive")
                if 'Region' in plot_df.columns:
                    reg = plot_df.groupby(['Region', 'Target']).agg({
                        'Estimated Budget Consumed': 'sum', 'Direct Sales': 'sum',
                        'Direct RoAS': 'mean', 'CVR (%)': 'mean', 'STR (%)': 'mean'
                    }).reset_index().sort_values(['Region', 'Direct Sales'], ascending=[True, False])
                    
                    # Styled Table with repeated regions and heatmaps
                    st.dataframe(reg.style.background_gradient(subset=['Direct Sales'], cmap='Greens')
                                         .background_gradient(subset=['Estimated Budget Consumed'], cmap='Reds')
                                         .format({'Estimated Budget Consumed': '₹{:.2f}', 'Direct Sales': '₹{:.2f}', 
                                                  'Direct RoAS': '{:.2f}x', 'CVR (%)': '{:.2f}%', 'STR (%)': '{:.2f}%'}), 
                                 use_container_width=True, height=600)

            with t4:
                st.subheader("🛑 Waste Audit (High Spend / Zero Sales)")
                waste = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                st.dataframe(waste.sort_values('Estimated Budget Consumed', ascending=False), use_container_width=True)

            with t5:
                st.subheader("⚖️ CPM Bidding Optimization")
                avg_cpm = summary_df['CPM'].mean()
                bids = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                st.info(f"Suggestions: These high-efficiency items have a higher than average CPM (₹{avg_cpm:.2f}). Consider a 5-10% bid reduction.")
                st.dataframe(bids, use_container_width=True)

            # --- EXPORT ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                summary_df.to_excel(wr, index=False, sheet_name='Performance')
                if 'Region' in plot_df.columns: reg.to_excel(wr, index=False, sheet_name='Regional_Intelligence')
            st.download_button("📥 Download Strategic Report", data=buf.getvalue(), file_name="Swiggy_Strategy_Report.xlsx")

if __name__ == "__main__":
    main()
