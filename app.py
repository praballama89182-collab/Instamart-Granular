with tabs[0]:
    st.subheader("Regional Performance Audit")
    # ... (existing city summary code) ...

    if df_grn is not None:
        st.divider()
        st.write("### 📦 All Products by Stock Volume (Per Region)")
        
        # REMOVED .head(10) to show everything available
        all_grn_prods = df_grn.groupby(['Mapped_City', 'SkuDescription']).agg({'ReceivedQty': 'sum'}).reset_index()
        all_grn_prods = all_grn_prods.sort_values(['Mapped_City', 'ReceivedQty'], ascending=[True, False])
        
        # Clean up descriptions for better display
        all_grn_prods['Product'] = all_grn_prods['SkuDescription'].str[:50] + "..."
        
        fig_grn_prod = px.bar(all_grn_prods, 
                              x='ReceivedQty', 
                              y='Product', 
                              color='Mapped_City',
                              orientation='h', 
                              title="Full Inventory Received per Region",
                              labels={'Mapped_City': 'Region', 'ReceivedQty': 'Qty Received'},
                              height=800, # Increased height to accommodate more products
                              template="plotly_white",
                              color_discrete_sequence=px.colors.qualitative.Pastel)
        
        fig_grn_prod.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_grn_prod, use_container_width=True)
