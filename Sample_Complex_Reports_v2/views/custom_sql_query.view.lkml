view: custom_sql_query {
  derived_table: {
    sql: SELECT a.Order_ID, a.Order_Date, a.Region, a.Category, a.Sub_Category, sum(a.Sales) as Sales, sum(a.Profit) as Profit, count(a.Quantity) as Quantity FROM `elastic-pocs.Super_Store_Sales.Orders` as a
inner join `elastic-pocs.Super_Store_Sales.Returns` as b
on a.Order_ID = b.Order_ID
group by 1,2,3,4,5 ;;
  }

  dimension: order_id {
    description: "Count Distinct of Order ID"
    type: count_distinct
    sql: ${TABLE}.Order_ID ;;
  }

  dimension: category {
    type: string
    sql: ${TABLE}.Category ;;
  }

  dimension: region {
    type: string
    sql: ${TABLE}.Region ;;
  }

  measure: profit {
    type: sum
    sql: ${TABLE}.Profit ;;
  }

  measure: sales {
    type: sum
    sql: ${TABLE}.Sales ;;
  }

  dimension: order_date_year {
    type: date_year
    sql: ${TABLE}.Order_Date ;;
  }

  dimension: order_date_quarter_of_year {
    type: date_quarter
    sql: ${TABLE}.Order_Date ;;
  }

  measure: calculation_417216348520423424 {
    type: string
    sql: ${TABLE}.Calculation_417216348520423424 ;;
  }
}