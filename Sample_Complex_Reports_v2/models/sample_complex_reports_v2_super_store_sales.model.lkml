connection: "tableau_looker_poc"
include: "/Sample_Complex_Reports_v2/views/*.view.lkml"
include: "/Sample_Complex_Reports_v2/dashboards/*.dashboard.lookml"
    
#included all views and dashboards
# Model file for Custom SQL Query

explore: custom_sql_query {
  # Aggregate table for KPI measure optimization
  aggregate_table: rollup__sales {
    query: {
      measures: [sales]
      dimensions: [region, category, order_date_year]
    }
    materialization: {
      # Recommendation: Add datagroup_trigger or sql_trigger_value for persistence
      # datagroup_trigger: your_datagroup_name
    }
  }

  # Aggregate table for KPI measure optimization
  aggregate_table: rollup__profit {
    query: {
      measures: [profit]
      dimensions: [region, category, order_date_year]
    }
    materialization: {
      # Recommendation: Add datagroup_trigger or sql_trigger_value for persistence
      # datagroup_trigger: your_datagroup_name
    }
  }

    # Aggregate table for KPI measure optimization
  aggregate_table: rollup__order_id {
    query: {
      measures: [order_id]
      dimensions: [region, category, order_date_year]
    }
    materialization: {
      # Recommendation: Add datagroup_trigger or sql_trigger_value for persistence
      # datagroup_trigger: your_datagroup_name
    }
  }
}