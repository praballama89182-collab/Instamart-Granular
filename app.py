import os
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Swiggy Ad Report Merger & Analytics",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for center-aligning dataframe headers & cells
st.markdown("""
<style>
    /* Center align headers and cells in Streamlit dataframes */
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Swiggy Ad Report Merger & Analytics")
st.write("Upload up to 5 monthly Excel ad campaign spreadsheets (.xlsx, .xls, .xlsb, .xlsm). Preview raw & consolidated sheets, inspect campaign performance, and view weekly trend lines.")

# Helper function to convert dataframe to downloadable Excel bytes
def convert_df_to_excel(df, sheet_name="Performance"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    return buffer.getvalue()

# 5 Dedicated Upload Boxes
col1, col2, col3, col4, col5 = st.columns(5)

uploaded_files = []

with col1:
    f1 = st.file_uploader("Upload File 1", type=["xlsx", "xls", "xlsb", "xlsm"], key="file1")
    if f1: uploaded_files.append(f1)

with col2:
    f2 = st.file_uploader("Upload File 2", type=["xlsx", "xls", "xlsb", "xlsm"], key="file2")
    if f2: uploaded_files.append(f2)

with col3:
    f3 = st.file_uploader("Upload File 3", type=["xlsx", "xls", "xlsb", "xlsm"], key="file3")
    if f3: uploaded_files.append(f3)

with col4:
    f4 = st.file_uploader("Upload File 4", type=["xlsx", "xls", "xlsb", "xlsm"], key="file4")
    if f4: uploaded_files.append(f4)

with col5:
    f5 = st.file_uploader("Upload File 5", type=["xlsx", "xls", "xlsb", "xlsm"], key="file5")
    if f5: uploaded_files.append(f5)

if uploaded_files:
    consolidated_dfs = []
    raw_files_dict = {}  # {filename: {sheet_name: df}}
    consolidated_raw_tabs = {}  # {sheet_name: [df1, df2, ...]}

    for uploaded_file in uploaded_files:
        month_name = os.path.splitext(uploaded_file.name)[0].upper()
        raw_files_dict[uploaded_file.name] = {}
        
        try:
            xls = pd.ExcelFile(uploaded_file)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                
                # Store raw sheet preview
                raw_files_dict[uploaded_file.name][sheet_name] = df.copy()
                
                # Raw tab copy for consolidated output workbook
                df_raw = df.copy()
                if 'Month' not in df_raw.columns:
                    df_raw.insert(0, 'Month', month_name)
                else:
                    df_raw['Month'] = month_name
                
                if sheet_name not in consolidated_raw_tabs:
                    consolidated_raw_tabs[sheet_name] = []
                consolidated_raw_tabs[sheet_name].append(df_raw)
                
                # Consolidated Master copy
                df_consolidated = df.copy()
                if sheet_name.strip().upper() in ['PRODUCT_RECOMMENDATION', 'KEYWORD_PERFORMANCE', 'PRODUCT_PERFORMANCE']:
                    if 'Targeting Type' in df_consolidated.columns:
                        df_consolidated['Match Type'] = df_consolidated['Targeting Type']
                
                df_consolidated.insert(0, 'Month', month_name)
                df_consolidated.insert(1, 'Tab Name', sheet_name)
                consolidated_dfs.append(df_consolidated)
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")

    if consolidated_dfs:
        final_df = pd.concat(consolidated_dfs, ignore_index=True)
        
        base_cols = ['Month', 'Tab Name']
        remaining_cols = [c for c in final_df.columns if c not in base_cols]
        final_df = final_df.reindex(columns=base_cols + remaining_cols)

        # Helper numeric extractor with expanded Swiggy column aliases
        def get_numeric_col(df, possible_cols):
            for col in possible_cols:
                # Case-insensitive column search
                matched_cols = [c for c in df.columns if c.strip().lower() == col.lower()]
                if matched_cols:
                    return pd.to_numeric(df[matched_cols[0]], errors='coerce').fillna(0)
            return pd.Series(0, index=df.index)

        # Metrics Extraction (Supports Swiggy Instamart naming)
        final_df['_impressions'] = get_numeric_col(final_df, ['Impressions', 'Views'])
        final_df['_direct_atc'] = get_numeric_col(final_df, ['Direct ATC', 'Direct Add to Cart', 'ATC'])
        final_df['_indirect_atc'] = get_numeric_col(final_df, ['Indirect ATC', 'Indirect Add to Cart'])
        final_df['_atc'] = final_df['_direct_atc'] + final_df['_indirect_atc']
        if final_df['_atc'].sum() == 0:
            final_df['_atc'] = get_numeric_col(final_df, ['Add To Cart', 'ATC', 'Clicks'])

        final_df['_direct_orders'] = get_numeric_col(final_df, ['Direct Quantities Sold', 'Direct Orders', 'Direct Units'])
        final_df['_indirect_orders'] = get_numeric_col(final_df, ['Indirect Quantities Sold', 'Indirect Orders', 'Indirect Units'])
        final_df['_orders'] = final_df['_direct_orders'] + final_df['_indirect_orders']
        if final_df['_orders'].sum() == 0:
            final_df['_orders'] = get_numeric_col(final_df, ['Total Orders', 'Orders', 'Units Sold', 'Quantity Sold'])

        final_df['_direct_sales'] = get_numeric_col(final_df, ['Direct Sales', 'Direct Revenue', 'Direct GMV'])
        final_df['_indirect_sales'] = get_numeric_col(final_df, ['Indirect Sales', 'Indirect Revenue', 'Indirect GMV'])
        final_df['_sales'] = final_df['_direct_sales'] + final_df['_indirect_sales']
        if final_df['_sales'].sum() == 0:
            final_df['_sales'] = get_numeric_col(final_df, ['Total Sales', 'Total Revenue', 'GMV', 'Revenue', 'Sales'])

        final_df['_budget_consumed'] = get_numeric_col(final_df, ['Estimated Budget Consumed', 'Budget Consumed', 'Spend', 'Spends', 'Ad Spend', 'Total Spend', 'Cost'])

        # Campaign Name fallback check
        campaign_col = None
        for col_candidate in ['Campaign Name', 'Campaign', 'Campaign_Name', 'Ad Group Name']:
            if col_candidate in final_df.columns:
                campaign_col = col_candidate
                break
        if campaign_col:
            final_df['Campaign Name'] = final_df[campaign_col]

        # Unified Ad Type / Targeting Category column
        ad_type_series = pd.Series(index=final_df.index, dtype=object)
        for target_col in ['Match Type', 'Targeting Type', 'Ad Type', 'Campaign Type']:
            if target_col in final_df.columns:
                ad_type_series = ad_type_series.fillna(final_df[target_col])
        
        if 'Tab Name' in final_df.columns:
            ad_type_series = ad_type_series.fillna(final_df['Tab Name'])
            
        final_df['Ad Type Combined'] = ad_type_series.fillna("Other")

        # --- WEEK BUCKET LOGIC (Parse DD-MM-YYYY format) ---
        date_col = None
        for col_candidate in ['Date', 'date', 'Day', 'DATE', 'Created Date']:
            if col_candidate in final_df.columns:
                date_col = col_candidate
                break

        if date_col:
            final_df['_date_dt'] = pd.to_datetime(final_df[date_col], dayfirst=True, errors='coerce')
            
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
                elif day >= 29:
                    return "Week 5"
                return np.nan

            final_df['Week'] = final_df.apply(assign_week, axis=1)
        else:
            final_df['Week'] = np.nan

        # --- GLOBAL MONTH FILTER ---
        st.markdown("### 🔍 Global Dashboard Filters")
        available_months = ["All Months"] + sorted(list(final_df['Month'].dropna().unique()))
        selected_month = st.selectbox("Select Month Across Dashboard", available_months)

        # Apply Global Month Filter
        filtered_df = final_df.copy()
        if selected_month != "All Months":
            filtered_df = filtered_df[filtered_df['Month'] == selected_month]

        # --- TOP LEVEL DASHBOARD METRICS ---
        total_impressions = filtered_df['_impressions'].sum()
        total_sales = filtered_df['_sales'].sum()
        total_orders = filtered_df['_orders'].sum()
        total_atc = filtered_df['_atc'].sum()
        total_budget = filtered_df['_budget_consumed'].sum()
        
        overall_roas = round((total_sales / total_budget), 2) if total_budget > 0 else 0.0

        st.markdown("### 📈 Overall Campaign Performance Dashboard")
        
        row1_col1, row1_col2, row1_col3 = st.columns(3)
        with row1_col1:
            st.metric("Total Impressions", f"{int(total_impressions):,}")
        with row1_col2:
            st.metric("Total Sales", f"₹{total_sales:,.2f}")
        with row1_col3:
            st.metric("Total Budget Consumed", f"₹{total_budget:,.2f}")

        row2_col1, row2_col2, row2_col3 = st.columns(3)
        with row2_col1:
            st.metric("Overall RoAS", f"{overall_roas:.2f}x")
        with row2_col2:
            st.metric("Total Orders", f"{int(total_orders):,}")
        with row2_col3:
            st.metric("Total Add To Cart / Clicks", f"{int(total_atc):,}")

        st.divider()

        # Helper function for grouping metrics with specific column structure
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
                ATC=('_atc', 'sum'),
                ORDERS=('_orders', 'sum'),
                SPENDS=('_budget_consumed', 'sum'),
                SALES=('_sales', 'sum')
            ).reset_index()

            # CPM = (Spends / Impressions) * 1000
            grouped['CPM'] = grouped.apply(
                lambda r: round((r['SPENDS'] / r['IMPRESSIONS']) * 1000, 2) if r['IMPRESSIONS'] > 0 else 0.0, axis=1
            )
            
            # ROAS = Sales / Spends
            grouped['ROAS'] = grouped.apply(
                lambda r: round(r['SALES'] / r['SPENDS'], 2) if r['SPENDS'] > 0 else 0.0, axis=1
            )

            # ACOS = (Spends / Sales) * 100
            grouped['ACOS'] = grouped.apply(
                lambda r: round((r['SPENDS'] / r['SALES']) * 100, 2) if r['SALES'] > 0 else 0.0, axis=1
            )

            display_name = group_col.upper()
            if group_col == 'Campaign Name':
                display_name = 'CAMPAIGN NAME'
            elif group_col == 'Ad Type Combined':
                display_name = 'MATCH / AD TYPE'

            grouped = grouped.rename(columns={group_col: display_name})

            # Reorder columns explicitly: [Entity, IMPRESSIONS, CPM, ATC, ORDERS, SPENDS, SALES, ROAS, ACOS]
            col_order = [display_name, 'IMPRESSIONS', 'CPM', 'ATC', 'ORDERS', 'SPENDS', 'SALES', 'ROAS', 'ACOS']
            grouped = grouped.reindex(columns=col_order)

            return grouped

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
                'SALES': '₹{:,.2f}', 
                'SPENDS': '₹{:,.2f}', 
                'CPM': '₹{:,.2f}',
                'IMPRESSIONS': '{:,.0f}', 
                'ORDERS': '{:,.0f}', 
                'ATC': '{:,.0f}',
                'ROAS': '{:.2f}x',
                'ACOS': '{:.2f}%'
            }
            active_formats = {k: v for k, v in format_dict.items() if k in df.columns}
            
            return styler.format(active_formats)

        # --- MAIN NAVIGATION TABS ---
        st.markdown("### 📑 Navigation & Performance Breakdown")
        main_tab1, main_tab2, main_tab3, main_tab4, main_tab5, main_tab6 = st.tabs([
            "📄 Raw Files Preview",
            "📌 Consolidated Master Preview",
            "🎯 Campaign Performance", 
            "📢 Ad Type Performance",
            "🔎 Search Term / Keyword Performance",
            "📅 Weekly Performance Trend"
        ])

        # TAB 1: Raw Files Preview
        with main_tab1:
            st.caption("Inspect individual sheets tab-by-tab for each uploaded file.")
            selected_file_name = st.selectbox("Select Uploaded File to Preview:", list(raw_files_dict.keys()))
            if selected_file_name:
                sheets = raw_files_dict[selected_file_name]
                selected_sheet = st.selectbox("Select Sheet Tab:", list(sheets.keys()))
                if selected_sheet:
                    st.write(f"Showing raw data preview for **{selected_file_name}** ➔ **{selected_sheet}** ({len(sheets[selected_sheet])} rows):")
                    st.dataframe(sheets[selected_sheet].head(100), use_container_width=True)

        # TAB 2: Consolidated Master Dataset Preview
        with main_tab2:
            st.caption("Preview the combined dataset across all uploaded files before export.")
            preview_clean_df = final_df.drop(columns=['_impressions', '_direct_atc', '_indirect_atc', '_atc', '_direct_orders', '_indirect_orders', '_orders', '_direct_sales', '_indirect_sales', '_sales', '_budget_consumed', '_date_dt', 'Ad Type Combined'], errors='ignore')
            st.write(f"Total Rows Consolidated: **{len(preview_clean_df):,}**")
            st.dataframe(preview_clean_df.head(100), use_container_width=True)

        # TAB 3: Campaign Performance
        with main_tab3:
            st.caption("Aggregated performance metrics per campaign.")
            if 'Campaign Name' in filtered_df.columns:
                campaign_options = ["All"] + sorted([str(x) for x in filtered_df['Campaign Name'].dropna().unique()])
                selected_campaign = st.selectbox("Select or Search Campaign:", campaign_options, key="campaign_filter")
                
                campaign_df = compute_grouped_table(filtered_df, 'Campaign Name', selected_campaign)
                if not campaign_df.empty:
                    st.dataframe(style_dataframe(campaign_df), use_container_width=True, hide_index=True)
                    
                    excel_campaign = convert_df_to_excel(campaign_df, sheet_name="Campaign_Performance")
                    st.download_button(
                        label="📥 Download Campaign Performance Excel (.xlsx)",
                        data=excel_campaign,
                        file_name="Swiggy_Campaign_Performance_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_dl_campaign"
                    )
                else:
                    st.info("No campaign data matching the selected criteria.")
            else:
                st.info("No 'Campaign Name' column found in dataset.")

        # TAB 4: Ad Type Performance
        with main_tab4:
            st.caption("Aggregated performance across Ad Types & Match Types.")
            if 'Ad Type Combined' in filtered_df.columns:
                adtype_options = ["All"] + sorted([str(x) for x in filtered_df['Ad Type Combined'].dropna().unique()])
                selected_adtype = st.selectbox("Select or Search Ad Type / Targeting Type:", adtype_options, key="adtype_filter")
                
                adtype_df = compute_grouped_table(filtered_df, 'Ad Type Combined', selected_adtype)
                if not adtype_df.empty:
                    st.dataframe(style_dataframe(adtype_df), use_container_width=True, hide_index=True)
                    
                    excel_adtype = convert_df_to_excel(adtype_df, sheet_name="Ad_Type_Performance")
                    st.download_button(
                        label="📥 Download Ad Type Performance Excel (.xlsx)",
                        data=excel_adtype,
                        file_name="Swiggy_Ad_Type_Performance_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_dl_adtype"
                    )
                else:
                    st.info("No Ad Type data matching the selected criteria.")
            else:
                st.info("No Ad Type data found.")

        # TAB 5: Keyword / Search Term Performance
        with main_tab5:
            st.caption("Performance across search terms / target keywords.")
            kw_col = None
            for col_candidate in ['Search Term', 'Keyword', 'Targeting Value', 'Keyword Name']:
                if col_candidate in filtered_df.columns:
                    kw_col = col_candidate
                    break
            
            if kw_col:
                kw_options = ["All"] + sorted([str(x) for x in filtered_df[kw_col].dropna().unique()])
                selected_kw = st.selectbox(f"Select or Search {kw_col}:", kw_options, key="kw_filter")
                
                search_df = compute_grouped_table(filtered_df, kw_col, selected_kw)
                if not search_df.empty:
                    st.dataframe(style_dataframe(search_df), use_container_width=True, hide_index=True, height=500)
                    
                    excel_search = convert_df_to_excel(search_df, sheet_name="Search_Term_Performance")
                    st.download_button(
                        label="📥 Download Search Term Performance Excel (.xlsx)",
                        data=excel_search,
                        file_name="Swiggy_Search_Term_Performance_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_dl_search"
                    )
                else:
                    st.info("No search term data matching the selected criteria.")
            else:
                st.info("No Search Term or Keyword column found in the dataset.")

        # TAB 6: Weekly Performance Trend
        with main_tab6:
            st.caption("Weekly aggregated performance trend (Week 1 through Week 5).")
            
            if 'Week' in filtered_df.columns and filtered_df['Week'].notna().any():
                weekly_df = compute_grouped_table(filtered_df, 'Week', "All")
                
                week_order = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5']
                weekly_df['Week_Cat'] = pd.Categorical(weekly_df['WEEK'], categories=week_order, ordered=True)
                weekly_df = weekly_df.sort_values('Week_Cat').drop(columns=['Week_Cat'])

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # SPENDS Bar
                fig.add_trace(
                    go.Bar(
                        x=weekly_df['WEEK'],
                        y=weekly_df['SPENDS'],
                        name='Spends (₹)',
                        marker=dict(color='#FC8019', line=dict(color='#E26B08', width=1.5)), # Swiggy Orange
                        text=[f"₹{v:,.0f}" for v in weekly_df['SPENDS']],
                        textposition='auto'
                    ),
                    secondary_y=False
                )

                # SALES Bar
                fig.add_trace(
                    go.Bar(
                        x=weekly_df['WEEK'],
                        y=weekly_df['SALES'],
                        name='Sales (₹)',
                        marker=dict(color='#34A853', line=dict(color='#1E8E3E', width=1.5)),
                        text=[f"₹{v:,.0f}" for v in weekly_df['SALES']],
                        textposition='auto'
                    ),
                    secondary_y=False
                )

                # ROAS Trend Line
                fig.add_trace(
                    go.Scatter(
                        x=weekly_df['WEEK'],
                        y=weekly_df['ROAS'],
                        name='ROAS',
                        mode='lines+markers+text',
                        line=dict(color='#282C3F', width=3),
                        marker=dict(size=8, color='#282C3F'),
                        text=[f"{v:.2f}x" for v in weekly_df['ROAS']],
                        textposition='top center'
                    ),
                    secondary_y=True
                )

                fig.update_layout(
                    title=dict(text="📊 Weekly Budget Spent vs Sales & ROAS Trend", font=dict(size=18, color="#202124")),
                    barmode='group',
                    template='plotly_white',
                    height=520,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis=dict(title="Week Bucket"),
                    yaxis=dict(title="Amount (₹)", showgrid=True),
                    yaxis2=dict(title="ROAS", overlaying="y", side="right", showgrid=False)
                )

                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(style_dataframe(weekly_df), use_container_width=True, hide_index=True)
            else:
                st.info("No valid Date column found or dates could not be parsed to assign week buckets.")

        st.divider()

        # Output Excel Generation
        st.subheader("💾 Download Consolidated Excel Workbook")
        
        buffer_multi = io.BytesIO()
        with pd.ExcelWriter(buffer_multi, engine='openpyxl') as writer:
            for raw_tab_name, df_list in consolidated_raw_tabs.items():
                combined_raw_tab_df = pd.concat(df_list, ignore_index=True)
                clean_sheet_name = raw_tab_name[:31]
                combined_raw_tab_df.to_excel(writer, sheet_name=clean_sheet_name, index=False)
            
            master_export_df = final_df.drop(columns=['_impressions', '_direct_atc', '_indirect_atc', '_atc', '_direct_orders', '_indirect_orders', '_orders', '_direct_sales', '_indirect_sales', '_sales', '_budget_consumed', '_date_dt', 'Ad Type Combined'], errors='ignore')
            master_export_df.to_excel(writer, sheet_name='Consolidated_Master', index=False)
            
        buffer_multi.seek(0)

        st.download_button(
            label="📥 Download Complete Excel Workbook (Consolidated Raw Tabs + Final Master Tab)",
            data=buffer_multi,
            file_name="Swiggy_Consolidated_Master_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
