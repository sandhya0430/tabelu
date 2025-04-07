- dashboard: sales_profit_dashboard_789
  title: "Sales Profit Dashboard"
  layout: newspaper
  auto_run: true
  crossfilter_enabled: true

  filters:
    - name: Year_Filter
      title: "Year"
      type: field_filter
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      field: custom_sql_query.order_date_year
      default_value: ""
      allow_multiple_values: true
      required: false

    - name: Region_Filter
      title: "Region"
      type: field_filter
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      field: custom_sql_query.region
      default_value: ""
      allow_multiple_values: true
      required: false

    - name: Category_Filter
      title: "Category"
      type: field_filter
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      field: custom_sql_query.category
      default_value: ""
      allow_multiple_values: true
      required: false

  elements:
    - name: kpi_sales_123
      title: "Sales"
      type: single_value
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      fields: [custom_sql_query.sales]
      filters:
        custom_sql_query.order_date_year: ""
        custom_sql_query.region: ""
        custom_sql_query.category: ""
      listen:
        Year_Filter: custom_sql_query.order_date_year
        Region_Filter: custom_sql_query.region
        Category_Filter: custom_sql_query.category
      limit: 500
      value_format: "$#,##0"
      custom_color_enabled: true
      show_single_value_title: true
      show_comparison: false
      defaults_version: 1
      row: 0
      col: 0
      width: 8
      height: 3

    - name: kpi_profit_456
      title: "Profit"
      type: single_value
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      fields: [custom_sql_query.profit]
      filters:
        custom_sql_query.order_date_year: ""
        custom_sql_query.region: ""
        custom_sql_query.category: ""
      listen:
        Year_Filter: custom_sql_query.order_date_year
        Region_Filter: custom_sql_query.region
        Category_Filter: custom_sql_query.category
      limit: 500
      value_format: "$#,##0"
      custom_color_enabled: true
      show_single_value_title: true
      show_comparison: false
      defaults_version: 1
      row: 0
      col: 8
      width: 8
      height: 3

    - name: kpi_order_count_789
      title: "Order Count"
      type: single_value
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      fields: [custom_sql_query.order_id]
      filters:
        custom_sql_query.order_date_year: ""
        custom_sql_query.region: ""
        custom_sql_query.category: ""
      listen:
        Year_Filter: custom_sql_query.order_date_year
        Region_Filter: custom_sql_query.region
        Category_Filter: custom_sql_query.category
      limit: 500
      value_format: "#,##0"
      custom_color_enabled: true
      show_single_value_title: true
      show_comparison: false
      defaults_version: 1
      row: 0
      col: 16
      width: 8
      height: 3

    - name: sales_by_year_chart
      title: "Sales by Year"
      type: looker_area
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      fields: [custom_sql_query.order_date_year, custom_sql_query.sales]
      pivots: [custom_sql_query.order_date_year]
      limit: 500
      stacking: ''
      listen:
        Year_Filter: custom_sql_query.order_date_year
        Region_Filter: custom_sql_query.region
        Category_Filter: custom_sql_query.category
      row: 3
      col: 0
      width: 12
      height: 8

    - name: sales_and_profit_by_year_chart
      title: "Sales and Profit by Year"
      type: looker_line
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      fields: [custom_sql_query.order_date_year, custom_sql_query.sales, custom_sql_query.profit]
      limit: 500
      stacking: ''
      listen:
        Year_Filter: custom_sql_query.order_date_year
        Region_Filter: custom_sql_query.region
        Category_Filter: custom_sql_query.category
      row: 3
      col: 12
      width: 12
      height: 8

    - name: sales_profit_comparision_chart
      title: "Sales Profit Comparision"
      type: looker_scatter
      model: sample_complex_reports_v2_super_store_sales
      explore: custom_sql_query
      fields: [custom_sql_query.category, custom_sql_query.region, custom_sql_query.sales, custom_sql_query.profit]
      limit: 500
      listen:
        Year_Filter: custom_sql_query.order_date_year
        Region_Filter: custom_sql_query.region
        Category_Filter: custom_sql_query.category
      row: 11
      col: 0
      width: 24
      height: 8