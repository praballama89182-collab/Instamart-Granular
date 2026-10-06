import os
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Swiggy Instamart Ad Analytics",
    page_icon="🍊",
    layout="wide"
)

# Custom CSS for UI centering
st.markdown("""
<style>
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🍊 Swiggy Instamart Ad Report Merger & Analytics")
st.write("Upload up to 5 Swiggy Instamart granular ad reports (.csv, .xlsx, .xls). View campaign, product, keyword, city, and weekly performance trends.")

# Helper to convert dataframe to downloadable Excel bytes
def convert_df_to_excel(df, sheet_name="Performance"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    return buffer.getvalue()

# Helper function to read Swiggy CSV or Excel while skipping metadata header rows
def load_instamart_file(file_obj):
    filename = file_obj.name.lower()
    
    if filename.endswith('.csv'):
        file_bytes = file_obj.getvalue()
        content = file_bytes.decode('utf-8', errors='ignore')
        lines = content.splitlines()
        
        # Detect actual header row index
        skip_count = 0
        for idx, line in enumerate(lines[:20]):
            if 'METRICS_DATE' in line or 'CAMPAIGN_NAME' in line or 'CAMPAIGN_ID' in line:
                skip_count = idx
                break
                
        file_obj.seek(0)
        df = pd.read_csv(file_obj, skiprows=skip_count)
        return {"Instamart_Data": df}
    else:
        xls = pd.ExcelFile(file_obj)
        sheets_dict = {}
        for sheet_name in xls.sheet_names:
            sheets_dict[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
        return sheets_dict

# 5 Upload Boxes
col1, col2, col3, col4, col5 = st.columns(5)
uploaded_files = []

with col1:
    f1 = st.file_uploader("Upload File 1", type=["csv", "xlsx", "xls", "xlsb"], key="f1")
    if f1: uploaded_files.append(f1)
with col2:
    f2 = st.file_uploader("Upload File 2", type=["csv", "xlsx", "xls", "xlsb"], key="f2")
    if f2: uploaded_files.append(f2)
with col3:
    f3 = st.file_uploader("Upload File 3", type=["csv", "xlsx", "xls", "xlsb"], key="f3")
    if f3: uploaded_files.append(f3)
with col4:
    f4 = st.file_uploader("Upload File 4", type=["csv", "xlsx", "xls", "xlsb"], key="f4")
    if f4: uploaded_files.append(f4)
with col5:
    f5 = st.file_uploader("Upload File 5", type=["csv", "xlsx", "xls", "xlsb"], key="f5")
    if f5: uploaded_files.append(f5)

if uploaded_files:
    consolidated_dfs = []

    for uploaded_file in uploaded_files:
        try:
            sheets_dict = load_instamart_file(uploaded_file)
            for sheet_name, df in sheets_dict.items():
                if df.empty:
                    continue
                
                df_consolidated = df.copy()
                df_consolidated.insert(0, 'Source Sheet', sheet_name)
                consolidated_dfs.append(df_consolidated)
                
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")

    if consolidated_dfs:
        final_df = pd.concat(consolidated_dfs, ignore_index=True)

        # Helper numeric extractor
        def get_numeric_col(df, possible_cols):
            for col in possible_cols:
                if col in df.columns:
                    return pd.to_numeric(df[col], errors='coerce').fillna(0)
            return pd.Series(0, index=df.index)

        # Standardise Swiggy Instamart metric columns
        final_df['_impressions'] = get_numeric_col(final_df, ['TOTAL_IMPRESSIONS', 'Impressions'])
        final_df['_clicks'] = get_numeric_col(final_df, ['TOTAL_CLICKS', 'Clicks'])
        final_df['_atc'] = get_numeric_col(final_df, ['TOTAL_A2C', 'ATC', 'Add To Cart'])
        final_df['_orders'] = get_numeric_col(final_df, ['TOTAL_CONVERSIONS', 'Orders'])
        final_df['_sales'] = get_numeric_col(final_df, ['TOTAL_GMV', 'Sales', 'GMV'])
        final_df['_budget_consumed'] = get_numeric_col(final_df, ['TOTAL_BUDGET_BURNT', 'Spend', 'Budget Consumed'])

        # Unified Ad Type / Target Property
        if 'AD_PROPERTY' in final_df.columns:
            final_df['Ad Property Combined'] = final_df['AD_PROPERTY'].astype(str)
            if 'MATCH_TYPE' in final_df.columns:
                final_df['Ad Property Combined'] += " (" + final_df['MATCH_TYPE'].astype(str) + ")"
        else:
            final_df['Ad Property Combined'] = "Other"

        # --- DATE PARSING & MONTH EXTRACTION FROM METRICS_DATE ---
        date_col = None
        for col_candidate in ['METRICS_DATE', 'Date', 'Day', 'DATE']:
            if col_candidate in final_df.columns:
                date_col = col_candidate
                break

        if date_col:
            # Parse date in MM/DD/YYYY or standard format
            final_df['_date_dt'] = pd.to_datetime(final_df[date_col], errors='coerce')
            
            # Extract Month Name (e.g., 9 -> SEPTEMBER 2026)
            final_df['Month'] = final_df['_date_dt'].dt.strftime('%B %Y').str.upper()
            final_df['Month'] = final_df['Month'].fillna('UNKNOWN')

            def assign_week(row):
                dt = row['_date_dt']
                if pd.isna(dt):
                    return np.nan
                day = dt.day
                if 1 <= day <= 7:
                    return "Week 1"
                elif 8 <= day <= 14:
                    return "Week 2"
                elif 15 <= day <= 21:
                    return "Week 3"
                elif 22 <= day <= 28:
                    return "Week 4"
                else:
                    return "Week 5"

            final_df['Week'] = final_df.apply(assign_week, axis=1)
        else:
            final_df['Month'] = 'UNKNOWN'
            final_df['Week'] = np.nan

        # Available months list derived directly from data dates
        available_months = ["All Months"] + sorted([m for m in final_df['Month'].unique() if m != 'UNKNOWN'])

        # --- TOP LEVEL DASHBOARD METRICS ---
        total_impressions = final_df['_impressions'].sum()
        total_clicks = final_df['_clicks'].sum()
        total_sales = final_df['_sales'].sum()
        total_orders = final_df['_orders'].sum()
        total_atc = final_df['_atc'].sum()
        total_budget = final_df['_budget_consumed'].sum()
        
        overall_roas = round((total_sales / total_budget), 2) if total_budget > 0 else 0.0

        st.markdown("### 📈 Overall Instamart Campaign Performance Dashboard")
        
        row1_col1, row1_col2, row1_col3 = st.columns(3)
        with row1_col1:
            st.metric("Total Impressions", f"{int(total_impressions):,}")
        with row1_col2:
            st.metric("Total Sales (GMV)", f"₹{total_sales:,.2f}")
        with row1_col3:
            st.metric("Total Budget Consumed", f"₹{total_budget:,.2f}")

        row2_col1, row2_col2, row2_col3 = st.columns(3)
        with row2_col1:
            st.metric("Overall RoAS", f"{overall_roas:.2f}x")
        with row2_col2:
            st.metric("Total Conversions (Orders)", f"{int(total_orders):,}")
        with row2_col3:
            st.metric("Total Clicks / ATC", f"{int(total_clicks):,} / {int(total_atc):,}")

        st.divider()

        # Grouping helper function
        def compute_grouped_table(df_subset, group_col, selected_item="All"):
            if group_col not in df_subset.columns:
                return pd.DataFrame()
            
            df_working = df_subset.dropna(subset=[group_col]).copy()
            df_working[group_col] = df_working[group_col].astype(str)
            
            if selected_item and selected_item != "All":
                df_working = df_working[df_working[group_col] == selected_item]
            
            if df_working.empty:
                return pd.DataFrame()

            grouped = df_working.groupby(group_col).agg(
                IMPRESSIONS=('_impressions', 'sum'),
                CLICKS=('_clicks', 'sum'),
                ATC=('_atc', 'sum'),
                ORDERS=('_orders', 'sum'),
                SPENDS=('_budget_consumed', 'sum'),
                SALES=('_sales', 'sum')
            ).reset_index()

            grouped['CPM'] = grouped.apply(
                lambda r: round((r['SPENDS'] / r['IMPRESSIONS']) * 1000, 2) if r['IMPRESSIONS'] > 0 else 0.0, axis=1
            )
            grouped['ROAS'] = grouped.apply(
                lambda r: round(r['SALES'] / r['SPENDS'], 2) if r['SPENDS'] > 0 else 0.0, axis=1
            )
            grouped['ACOS'] = grouped.apply(
                lambda r: round((r['SPENDS'] / r['SALES']) * 100, 2) if r['SALES'] > 0 else 0.0, axis=1
            )

            display_name = group_col.upper()
            if group_col == 'CAMPAIGN_NAME': display_name = 'CAMPAIGN NAME'
            elif group_col == 'KEYWORD': display_name = 'SEARCH TERM / KEYWORD'
            elif group_col == 'CITY': display_name = 'CITY'
            elif group_col == 'PRODUCT_NAME': display_name = 'PRODUCT NAME'
            elif group_col == 'Ad Property Combined': display_name = 'AD PROPERTY / MATCH TYPE'

            grouped = grouped.rename(columns={group_col: display_name})
            col_order = [display_name, 'IMPRESSIONS', 'CLICKS', 'CPM', 'ATC', 'ORDERS', 'SPENDS', 'SALES', 'ROAS', 'ACOS']
            return grouped.reindex(columns=col_order)

        def style_roas(val):
            try:
                val_float = float(val)
                if val_float < 1.0:
                    return 'background-color: #ffcdd2; color: #b71c1c; font-weight: bold; text-align: center;'
                else:
                    return 'background-color: #c8e6c9; color: #1b5e20; font-weight: bold; text-align: center;'
            except:
                return ''

        def style_dataframe(df):
            styler = df.style
            if 'ROAS' in df.columns:
                if hasattr(styler, 'map'):
                    styler = styler.map(style_roas, subset=['ROAS'])
                else:
                    styler = styler.applymap(style_roas, subset=['ROAS'])
            
            styler = styler.set_properties(**{'text-align': 'center'})
            format_dict = {
                'SALES': '₹{:,.2f}', 'SPENDS': '₹{:,.2f}', 'CPM': '₹{:,.2f}',
                'IMPRESSIONS': '{:,.0f}', 'CLICKS': '{:,.0f}', 'ORDERS': '{:,.0f}', 
                'ATC': '{:,.0f}', 'ROAS': '{:.2f}x', 'ACOS': '{:.2f}%'
            }
            active_formats = {k: v for k, v in format_dict.items() if k in df.columns}
            return styler.format(active_formats)

        # Helper to apply month filter inside tabs
        def apply_month_filter(df, month_val):
            if month_val != "All Months":
                return df[df['Month'] == month_val]
            return df

        # --- NAVIGATION TABS ---
        st.markdown("### 📑 Instamart Performance Breakdown")
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📄 Raw Data Preview",
            "🎯 Campaign Performance", 
            "📦 Product Performance",
            "📢 Ad Property & Match Type",
            "🔎 Keyword / Search Term",
            "🏙 City Performance",
            "📅 Weekly Trend"
        ])

        # TAB 1: Raw Data Preview
        with tab1:
            st.caption("Preview raw consolidated dataset across all uploaded Instamart files.")
            m_tab1 = st.selectbox("Select Month (Derived from METRICS_DATE):", available_months, key="m_tab1")
            df_t1 = apply_month_filter(final_df, m_tab1)
            
            preview_df = df_t1.drop(columns=['_impressions', '_clicks', '_atc', '_orders', '_sales', '_budget_consumed', '_date_dt', 'Ad Property Combined'], errors='ignore')
            st.write(f"Total Rows Consolidated: **{len(preview_df):,}**")
            st.dataframe(preview_df.head(100), use_container_width=True)

        # TAB 2: Campaign Performance
        with tab2:
            st.caption("Aggregated performance per Swiggy Instamart campaign.")
            col_a, col_b = st.columns(2)
            with col_a:
                m_tab2 = st.selectbox("Select Month:", available_months, key="m_tab2")
            df_t2 = apply_month_filter(final_df, m_tab2)

            if 'CAMPAIGN_NAME' in df_t2.columns:
                c_opts = ["All"] + sorted([str(x) for x in df_t2['CAMPAIGN_NAME'].dropna().unique()])
                with col_b:
                    sel_c = st.selectbox("Select Campaign:", c_opts, key="c_flt")
                
                campaign_df = compute_grouped_table(df_t2, 'CAMPAIGN_NAME', sel_c)
                if not campaign_df.empty:
                    st.dataframe(style_dataframe(campaign_df), use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Campaign Performance (.xlsx)", convert_df_to_excel(campaign_df, "Campaign_Performance"), "Instamart_Campaign_Report.xlsx", key="dl_c")
            else:
                st.info("No 'CAMPAIGN_NAME' column found.")

        # TAB 3: Product Performance
        with tab3:
            st.caption("Aggregated performance by SKU / Product Name.")
            col_a, col_b = st.columns(2)
            with col_a:
                m_tab3 = st.selectbox("Select Month:", available_months, key="m_tab3")
            df_t3 = apply_month_filter(final_df, m_tab3)

            if 'PRODUCT_NAME' in df_t3.columns:
                p_opts = ["All"] + sorted([str(x) for x in df_t3['PRODUCT_NAME'].dropna().unique()])
                with col_b:
                    sel_p = st.selectbox("Select Product:", p_opts, key="p_flt")
                
                prod_df = compute_grouped_table(df_t3, 'PRODUCT_NAME', sel_p)
                if not prod_df.empty:
                    st.dataframe(style_dataframe(prod_df), use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Product Performance (.xlsx)", convert_df_to_excel(prod_df, "Product_Performance"), "Instamart_Product_Report.xlsx", key="dl_p")
            else:
                st.info("No 'PRODUCT_NAME' column found.")

        # TAB 4: Ad Property Performance
        with tab4:
            st.caption("Performance by Ad Property and Match Type.")
            col_a, col_b = st.columns(2)
            with col_a:
                m_tab4 = st.selectbox("Select Month:", available_months, key="m_tab4")
            df_t4 = apply_month_filter(final_df, m_tab4)

            if 'Ad Property Combined' in df_t4.columns:
                ad_opts = ["All"] + sorted([str(x) for x in df_t4['Ad Property Combined'].dropna().unique()])
                with col_b:
                    sel_ad = st.selectbox("Select Ad Property:", ad_opts, key="ad_flt")
                
                ad_df = compute_grouped_table(df_t4, 'Ad Property Combined', sel_ad)
                if not ad_df.empty:
                    st.dataframe(style_dataframe(ad_df), use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Ad Property Performance (.xlsx)", convert_df_to_excel(ad_df, "Ad_Property_Performance"), "Instamart_Ad_Property_Report.xlsx", key="dl_ad")

        # TAB 5: Search Term / Keyword Performance
        with tab5:
            st.caption("Performance breakdown by targeted keywords.")
            col_a, col_b = st.columns(2)
            with col_a:
                m_tab5 = st.selectbox("Select Month:", available_months, key="m_tab5")
            df_t5 = apply_month_filter(final_df, m_tab5)

            if 'KEYWORD' in df_t5.columns:
                kw_opts = ["All"] + sorted([str(x) for x in df_t5['KEYWORD'].dropna().unique()])
                with col_b:
                    sel_kw = st.selectbox("Select Keyword:", kw_opts, key="kw_flt")
                
                kw_df = compute_grouped_table(df_t5, 'KEYWORD', sel_kw)
                if not kw_df.empty:
                    st.dataframe(style_dataframe(kw_df), use_container_width=True, hide_index=True, height=500)
                    st.download_button("📥 Download Keyword Performance (.xlsx)", convert_df_to_excel(kw_df, "Keyword_Performance"), "Instamart_Keyword_Report.xlsx", key="dl_kw")

        # TAB 6: City Performance
        with tab6:
            st.caption("City-wise advertising performance breakdown & pie chart share.")
            col_a, col_b = st.columns(2)
            with col_a:
                m_tab6 = st.selectbox("Select Month:", available_months, key="m_tab6")
            df_t6 = apply_month_filter(final_df, m_tab6)

            if 'CITY' in df_t6.columns:
                city_opts = ["All"] + sorted([str(x) for x in df_t6['CITY'].dropna().unique()])
                with col_b:
                    sel_city = st.selectbox("Select City:", city_opts, key="city_flt")
                
                city_df = compute_grouped_table(df_t6, 'CITY', sel_city)
                if not city_df.empty:
                    # Pie Chart for City Spend & Sales Share
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        fig_spend_pie = px.pie(
                            city_df, 
                            values='SPENDS', 
                            names='CITY', 
                            title="🏙️ City-wise Spend Share",
                            color_discrete_sequence=px.colors.sequential.Blues_r,
                            hole=0.4
                        )
                        fig_spend_pie.update_traces(textposition='inside', textinfo='percent+label')
                        fig_spend_pie.update_layout(template='plotly_white', height=380)
                        st.plotly_chart(fig_spend_pie, use_container_width=True)

                    with col_p2:
                        fig_sales_pie = px.pie(
                            city_df, 
                            values='SALES', 
                            names='CITY', 
                            title="🏙️ City-wise Sales (GMV) Share",
                            color_discrete_sequence=px.colors.sequential.Blues_r,
                            hole=0.4
                        )
                        fig_sales_pie.update_traces(textposition='inside', textinfo='percent+label')
                        fig_sales_pie.update_layout(template='plotly_white', height=380)
                        st.plotly_chart(fig_sales_pie, use_container_width=True)

                    st.dataframe(style_dataframe(city_df), use_container_width=True, hide_index=True)
                    st.download_button("📥 Download City Performance (.xlsx)", convert_df_to_excel(city_df, "City_Performance"), "Instamart_City_Report.xlsx", key="dl_city")
            else:
                st.info("No 'CITY' column found.")

        # TAB 7: Weekly Performance Trend
        with tab7:
            st.caption("Weekly performance trend (Week 1 through Week 5).")
            m_tab7 = st.selectbox("Select Month:", available_months, key="m_tab7")
            df_t7 = apply_month_filter(final_df, m_tab7)

            if 'Week' in df_t7.columns and df_t7['Week'].notna().any():
                weekly_df = compute_grouped_table(df_t7, 'Week', "All")
                
                week_order = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5']
                weekly_df['Week_Cat'] = pd.Categorical(weekly_df['WEEK'], categories=week_order, ordered=True)
                weekly_df = weekly_df.sort_values('Week_Cat').drop(columns=['Week_Cat'])

                # Professional Plotly Chart (Shades of Blue Palette)
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Dark Navy Blue for Spends
                fig.add_trace(
                    go.Bar(
                        x=weekly_df['WEEK'], 
                        y=weekly_df['SPENDS'], 
                        name='Spends (₹)', 
                        marker_color='#1B365D', 
                        text=[f"₹{v:,.0f}" for v in weekly_df['SPENDS']], 
                        textposition='auto'
                    ), 
                    secondary_y=False
                )
                
                # Slate Blue for Sales
                fig.add_trace(
                    go.Bar(
                        x=weekly_df['WEEK'], 
                        y=weekly_df['SALES'], 
                        name='Sales (₹)', 
                        marker_color='#4A90E2', 
                        text=[f"₹{v:,.0f}" for v in weekly_df['SALES']], 
                        textposition='auto'
                    ), 
                    secondary_y=False
                )
                
                # Vivid Cyan Blue Line for ROAS
                fig.add_trace(
                    go.Scatter(
                        x=weekly_df['WEEK'], 
                        y=weekly_df['ROAS'], 
                        name='ROAS', 
                        mode='lines+markers+text', 
                        line=dict(color='#00A8E8', width=3), 
                        marker=dict(size=8, color='#00A8E8'), 
                        text=[f"{v:.2f}x" for v in weekly_df['ROAS']], 
                        textposition='top center'
                    ), 
                    secondary_y=True
                )

                fig.update_layout(
                    title="📊 Weekly Spends vs Sales & ROAS Trend", 
                    barmode='group', 
                    template='plotly_white', 
                    height=500, 
                    legend=dict(orientation="h", y=1.1, x=1, xanchor="right")
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(style_dataframe(weekly_df), use_container_width=True, hide_index=True)

        st.divider()

        # Download Consolidated Master File
        st.subheader("💾 Download Consolidated Instamart Workbook")
        master_export_df = final_df.drop(columns=['_impressions', '_clicks', '_atc', '_orders', '_sales', '_budget_consumed', '_date_dt', 'Ad Property Combined'], errors='ignore')
        st.download_button(
            label="📥 Download Consolidated Master Excel Report (.xlsx)",
            data=convert_df_to_excel(master_export_df, sheet_name="Consolidated_Master"),
            file_name="Swiggy_Instamart_Consolidated_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
