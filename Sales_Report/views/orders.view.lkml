view: orders {
  sql_table_name: `elastic-pocs.Super_Store_Sales.Orders` ;;

  dimension: category {
    type: string
    sql: ${TABLE}.Category ;;
  }

  dimension: city {
    type: string
    sql: ${TABLE}.City ;;
  }

  dimension: country {
    type: string
    sql: ${TABLE}.Country ;;
  }

  dimension: customer_id {
    type: string
    sql: ${TABLE}.Customer_ID ;;
  }

  dimension: customer_name {
    type: string
    sql: ${TABLE}.Customer_Name ;;
  }

  dimension: discount {
    type: number
    sql: ${TABLE}.Discount ;;
  }

  dimension: order_date {
    type: date
    sql: CAST(${TABLE}.Order_Date AS TIMESTAMP) ;;
  }

  dimension: order_id {
    type: string
    sql: ${TABLE}.Order_ID ;;
  }

  dimension: postal_code {
    type: string
    sql: ${TABLE}.Postal_Code ;;
  }

  dimension: product_id {
    type: string
    sql: ${TABLE}.Product_ID ;;
  }

  dimension: product_name {
    type: string
    sql: ${TABLE}.Product_Name ;;
  }

  dimension: profit {
    type: number
    sql: ${TABLE}.Profit ;;
  }

  dimension: quantity {
    type: number
    sql: ${TABLE}.Quantity ;;
  }

  dimension: region {
    type: string
    sql: ${TABLE}.Region ;;
  }

  dimension: sales {
    type: number
    sql: ${TABLE}.Sales ;;
  }

  dimension: segment {
    type: string
    sql: ${TABLE}.Segment ;;
  }

  dimension: ship_date {
    type: date
    sql: CAST(${TABLE}.Ship_Date AS TIMESTAMP) ;;
  }

  dimension: ship_mode {
    type: string
    sql: ${TABLE}.Ship_Mode ;;
  }

  dimension: state {
    type: string
    sql: ${TABLE}.State ;;
  }

  dimension: sub_category {
    type: string
    sql: ${TABLE}.Sub_Category ;;
  }

  dimension: order_date_year {
    type: date_year
    sql: CAST(${TABLE}.Order_Date AS TIMESTAMP) ;;
  }

  measure: sales_sum {
    type: sum
    sql: ${sales} ;;
  }

  measure: quantity_count {
    type: count
    sql: ${quantity} ;;
  }

  measure: profit_sum {
    type: sum
    sql: ${profit} ;;
  }

  measure: calculation_179862574092779520_user {
    type: number
    sql: ${TABLE}.Calculation_179862574092779520 ;;
  }

  dimension: is_returns_present {
    type: yesno
    sql: ${order_id} IS NOT NULL ;;
  }
}

view: returns {
  sql_table_name: `elastic-pocs.Super_Store_Sales.Returns` ;;

  dimension: order_id {
    type: string
    sql: ${TABLE}.Order_ID ;;
  }

  dimension: returned {
    type: string
    sql: ${TABLE}.Returned ;;
  }
}