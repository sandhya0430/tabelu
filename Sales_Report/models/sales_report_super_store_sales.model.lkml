connection: "tableau_looker_poc"
include: "/Sales_Report/views/*.view.lkml"
include: "/Sales_Report/dashboards/*.dashboard.lookml"
    
#included all views and dashboards
explore: orders {
  join: returns {
    sql_on: ${orders.order_id} = ${returns.order_id} ;;
    relationship: many_to_one
  }
}