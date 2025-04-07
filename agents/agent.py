import os
from agents.gemini import generate_response_with_gemini
from utils import generate_view_text, generate_model_text

def structure_agent(content):
    prompt = f"""{content}
    you are an expert in analysing tableau file and writing lookml i want you to convert the provided tableau file to lookml files. So just return the file names(.views,.models,.dashboard) that is needed to achive this in a json format.
    Example JSON structure:
    {{
        "view_files": [
            <file_name>.views.lkml
        ],
        "model_files": [
            <file_name>.model.lkml
        ],
        "dashboard_files": [
            <file_name>.dashboard.lookml  //dashboard file should always end with.lookml
        ]
    }}
    """
    response = generate_response_with_gemini(prompt, temperature=0.1)
    return response
    
def view_agent(content, file_name):
    prompt = f"""
You are an expert in analyzing Tableau XML files and writing LookML. From the provided Tableau XML files, identify and extract only the specified file. Convert this file into a .view file for Looker.
Maintain the column names and connection names exactly as they appear in the source.
Ensure the structure aligns with LookML best practices.

Instructions:
    - Ensure all relevant fields, dimensions, and measures are correctly defined based on the <cols> and <columns> in Tableau schema.
        - Ensure dimensions are created for all <map> using the value if cols are present. [MUST]
        - Create dimensions and measures using the <column-instance> elements.
        - Refer to the table details in <cols> if present; otherwise, assume a single table source.
    - Map columns with role='dimension' to LookML Dimensions and those with role='measure' to LookML Measures.
    - Extract `looker_datatype` if available and assign the correct LookML `type`.
            Example XML:
            <column-instance column='[DATE]' derivation='Quarter' role='dimension' looker_datatype='data_quarter' name='[qr:DATE:ok]' pivot='key' type='ordinal' />
            Example LookML:
            dimension: data_quater {{
                description: "Quarterly date derived from the DATE field"
                type: date_quarter
                sql: ${{TABLE}}.DATE ;;
            }}
    - **Aggregate Table Generation for KPIs:** If the source Tableau worksheet represents Key Performance Indicators (KPIs):
        - Identify the corresponding Looker `explore` based on the Tableau datasource.
        - Extract the actual table and explore names from the context to use as references, not placeholder values.
        - For *each distinct KPI measure* identified in that worksheet (e.g., SUM(Sales), COUNTD(Orders)):
            - Generate an `aggregate_table` definition specifically for optimizing that measure's query.
            - This definition must be placed *inside* the relevant `explore: <explore_name> {{ ... }}` block within the model file.
            - Use the following structure, replacing `<measure_name>` with the actual Looker measure name:
              ```lookml
              aggregate_table: rollup__<measure_name> {{ # e.g., rollup__sales
                query: {{
                  measures: [<measure_name>] # e.g., [sales]
                }}
                materialization: {{
                  # Recommendation: Add datagroup_trigger or sql_trigger_value for persistence
                  # datagroup_trigger: your_datagroup_name
                }}
              }}
              ```
              - Include a comment recommending the addition of a materialization strategy (datagroup or SQL trigger).
             - Ensure these aggregate table definitions are correctly added to the appropriate explore definition within the model.

    view: view_name {{
  
  # Option 1: If the SQL is a direct table reference
  sql_table_name: your_schema.your_table_name ;;  # <- Use this if it's a simple table reference

  # Option 2: If the SQL is a custom SQL with joins/aggregations
  derived_table: {{
    sql:
      SELECT column1, column2, ...
      FROM your_schema.your_table1 AS a
      JOIN your_schema.your_table2 AS b ON a.key = b.key
      WHERE ...
      GROUP BY ... ;;
  }}    
   set: set_name{{
        fields:[field_or_set, field_or_set, ...]
    }}

    drill_fields: [field_or_set, field_or_set, …]
    dimension: field_name {{
        primary_key: yes # if the field is the primary key
        description: description of this dimension
        type: number | string | time | zipcode | date | date_day_of_week | date_month_name | date_month_num | date_month | date_quarter_of_year | date_quarter | date_year
        sql: $your_table_name.column_name # example sql: $customer.name
    }}
    dimension: field_name {{
        description: description of this dimension
        type: location
        sql_latitude:  $your_table_name.latitude_column_name ;;
        sql_longitude:  $your_table_name.longitude_column_name ;;
    }}
    filter: filter_name {{
        description: description of this filter
        type: string | number | yesno | date
        suggest_dimension: user_name
        sql: sql_condition ;;
    }}
    measure: field_name {{
        description: description of this measure
        type: number | string # for non Aggregate column
        sql: $your_table_name.column_name ;; # example sql: $customer.age
    }}
    measure: field_name {{
        description: description of this measure
        type: count | sum | average | max | median | min | list | percentile  # for Aggregate column
        sql: $your_table_name.column_name / $your_table_name.column_name ;; # example sql: $sales.profit / $sales.sales [Note: do not add this if the type is count]
    }}
}}

Specified File: {file_name}    

Tableau file: {content}
    """
    
    response = generate_response_with_gemini(prompt)
    return response

def model_agent(content, workbook_name):
    view_prompt = generate_view_text(workbook_name) 
    prompt = f"""
you are an expert in analysing tableau file and writing lookml I want you to convert the provided tableau file to lookml files. Maintain the colomn names and connection names from the provided source. Create a .model file for this provided source
your output should be only in lookml format file. don't output anything other than lookml file.
return .model file.

Instructions:
    - Analyse the provided tableau file and view file and with this you need to create a .model file
    - Do not use any other parameter that is not provided in the sample model file
    - Maintain column and connection names exactly as in the Tableau source.
    - Do not include connection and include statements.
    - Do not use join for the same view file
    - Always extract the correct view name by examining the view file precisely.
        - Example: If the view file contains: view: my_view_1
        - Then the model file must reference that exact view name: explore: my_view_1 {{ ... }} or join: my_view_1 {{ ... }}.
    - Do NOT use hardcoded placeholder names like 'orders_derived_table' or similar. Instead, extract actual table/view names from context.

    - Use joins only when necessary (only if multiple views have same field):
        - Join dimension tables (lookup/reference tables) that enrich the fact table, such as City, Category, or Country.
        - Avoid joins that do not add new dimensions or that cause redundancy.
        - Ensure a clear primary key relationship, such as `main_table.id = lookup_table.id`.
    - Key considerations:
        - If there are no dimension tables (lookup/reference tables), do not add any joins.
        - If all fields exist in a single table, create an explore without any joins.
        - Ensure all joins have a valid key match and are not redundant.

    - **Aggregate Table Generation for KPIs:** If the source Tableau worksheet represents Key Performance Indicators (KPIs) and corresponding `explore_source` derived views were generated:
        - Identify the corresponding base Looker `explore` based on the Tableau datasource used by the KPI worksheet. This explore should already exist or be defined based on the primary data source.
        - For *each distinct KPI measure* identified in that worksheet (e.g., SUM(Sales), COUNTD(Orders), mapped to Looker measure names like `sales`, `count_of_orders`):
            - Generate an `aggregate_table` definition specifically for optimizing that measure's query *within the base explore*.
            - This definition must be placed *inside* the relevant `explore: <base_explore_name> {{ ... }}` block. Do NOT place it inside explores related to the derived views themselves.
            - Use the following structure, replacing `<measure_name>` with the actual Looker measure name from the *base explore*:
            ```lookml
              # Aggregate table for KPI measure optimization
              aggregate_table: rollup__<measure_name> {{ # e.g., rollup__sales
                query: {{
                  # Reference the measure directly by its name from the joined view(s)
                  measures: [<measure_name>] # e.g., [sales]

                  # Optionally include dimensions used in KPI filters if needed for granularity
                  # Reference dimensions directly by their names from the joined view(s)
                  # dimensions: [order_year, region]
                }}
                materialization: {{
                  # Recommendation: Add datagroup_trigger or sql_trigger_value for persistence
                  # datagroup_trigger: your_datagroup_name
                }}
              }}
              ```
            - Include a comment recommending the addition of a materialization strategy.
        - Ensure these aggregate table definitions are correctly added to the appropriate base explore definition within the model.

sample model file:
    ```lookml
    # Minimal example structure for a .model.lkml file

    explore: base_explore_name {{ # The main explore derived from the Tableau source

      # Example Join (if needed based on Instructions)
      join: joined_view_name {{
        type: left_outer # Or other type
        relationship: many_to_one # Or other relationship
        sql_on: ${{base_explore_name.join_key}} = ${{joined_view_name.join_key}} ;;
      }}

      # --- KPI Aggregate Table ---
      # (Added inside the base explore if KPIs were detected)
      aggregate_table: rollup__<kpi_measure_name> {{ # e.g., rollup__sales
        query: {{
          measures: [<kpi_measure_name>] # e.g., [sales]
          # dimensions: [<filter_dimension_1>, <filter_dimension_2>] # Optional dimensions
        }}
        materialization: {{
          # datagroup_trigger: your_datagroup_name # Recommended
        }}
      }}
      # (Potentially more aggregate tables for other KPIs)

    }} # End of base_explore_name explore

    ```

Tableau File:
```
{content}
```

Views File:
{view_prompt}
"""
    response = generate_response_with_gemini(prompt)
    return response

def dashboard_agent(content, workbook_name):
    view_prompt = generate_view_text(workbook_name)
    model_prompt = generate_model_text(workbook_name)
    prompt = f"""
You are an expert in analyzing Tableau files and writing LookML. Your task is to convert the provided Tableau file into a .dashboard.lookml file while maintaining all relevant information from the provided sources.
Instructions:
  - Analyze the provided Tableau file, model file, and view file to extract relevant dimensions, measures, and relationships.
  - Use the model file to determine the dataset connections, explore definitions, and joins.
  - Define visualization elements (charts, tables, KPIs, etc.) based on the Tableau file structure, mapping the fields correctly using the dimensions and measures extracted from the LookML view file.
  - Maintain formatting and logical grouping of elements to ensure clarity and usability in Looker.
  - Structure the LookML dashboard file properly using the sample format provided.
  - Ensure correct indentation and syntax to produce a well-formatted LookML dashboard file that adheres to Looker's standards.
  - IMPORTANT: Extract actual table/view/explore names from the model file or view file. DO NOT use hardcoded placeholder names like 'orders_derived_table' - this causes errors!

  - **KPI Element Generation (Single Value):** If the source Tableau worksheet represents Key Performance Indicators (KPIs, often using Text marks and `Measure Names`):
      - For *each distinct KPI measure* identified in that worksheet (e.g., SUM(Sales), COUNTD(Orders)):
          - Generate a separate dashboard element with `type: single_value`.
          - **`name`**: Assign a unique, descriptive name (e.g., `kpi_total_sales_123`).
          - **`title`**: Use a meaningful title reflecting the measure (e.g., "Total Sales", "Profit", "Order Count"). Avoid generic titles.
          - **`model`**: Specify the correct Looker model name extracted from context.
          - **`explore`**: Specify the *base explore* name from which the KPI is derived, extracted from the model file.
          - **`fields`**: Include a single item list containing the corresponding measure field from the *base explore*.
          - **`filters`**: Define filters within the element based on the context dimensions identified in the Tableau KPI worksheet (e.g., `year_field`, `region_field`). Leave the values empty (`''`) to be controlled by dashboard filters.
          - **`listen`**: Add a `listen:` block mapping the *dashboard filter names* (defined separately at the dashboard level) to the corresponding fields in the *base explore* used by this element.
          - **`value_format`**: Apply appropriate number formatting (e.g., `"#,##0"`, `"$#,##0.00"`) based on the Tableau formatting or inferred type.
          - **`height`**: Set between 150 and 250, as per the general guidelines.
          - Include standard sensible defaults: `custom_color_enabled: true`, `show_single_value_title: true`, `show_comparison: false`, `defaults_version: 1`.

  - **Standard Element Generation (Charts/Tables):** For non-KPI worksheets:
      - For each worksheet:
          - Add only the dimension(s) present in the `<rows>` tag to the `fields` list.
          - Add only the primary aggregated measure (from the Tableau visualization) to the `fields` list.
          - Do not include calculated fields, filters, or multiple metrics unless explicitly required by the chart.
          - Add the field(s) in the `<cols>` tag to the `pivots` list only if there are two or more columns, or if the chart uses a visual grouping (like color).
          - Avoid repeating the same dimension in both `fields` and `pivots`.
          - Ensure the total number of fields in the `fields` list is minimal and sufficient to render the intended chart structure.
            example xml:
                <worksheet name="element_name">
                  <table>
                    <rows>([id].[column1] / [id].[column2] / [id].[column3])</rows>
                    <cols>[id].[column3] [id].[column4]</cols>
                  </table>
                </worksheet>
            example lookml:
                - name: "element_name"
                  fields: [view_name.column1, view_name.column1, view_name.column3, view_name.column4] # Note: Example seems to have duplicate column1, verify logic
                  pivots: [view_name.column4]
      - **Visualization Types:**
          - When generating each element, use the value from `looker_chart_type` in the `<worksheet>` tag to set the `type` in the LookML element.
          - Additionally, handle `stacked_type` attribute for stacking options (`normal`, `''`, `percent`) as specified. If not included, omit the `stacking:` parameter.

  - **Dashboard Filters:**
    - Define dashboard-level filters (`filters:` block at the top level of the dashboard definition) based on the filters identified across the Tableau worksheets (including those used for KPIs).
    - Ensure each filter has a unique `name`, a user-friendly `title`, specifies the `type` (e.g., `field_filter`), the `model` and `explore`, and the `field` it controls. Provide default values if appropriate (e.g., `default_value: ""`).
    - For elements (KPIs, charts, tables) to be affected by a dashboard filter, ensure they include the `listen:` block mapping the *dashboard filter name* to the *element's field*.

  - **Layout and Formatting:**
    - When defining the `height` and `width` for each element, adhere to the guidelines:
        - `looker_grid` (table): `height` 400-800.
        - `single_value`: `height` 150-250.
        - Charts (`looker_column`, etc.): `width` >= 300.
    - Maintain formatting and logical grouping of elements.

  - **General Rules:**
    - Do not use any additional parameters not mentioned in the Sample LookML Dashboard Format or these instructions.
    - Get the `limit` for elements from the count in the `groupfilter` for the appropriate worksheet if applicable.
    - After generating the dashboard LookML file, recheck whether the format is correctly matched; if not, fix it.
    - Always return the final, corrected dashboard LookML file.
 
Sample LookML Dashboard Format:
    ```lookml
    - dashboard: <dashboard_name>_<random_number> # Unique dashboard name
      title: "Dashboard Title from Tableau"
      description: "Dashboard description (optional)"
      # preferred_viewer: dashboards-next # Optional: Use Looker's newer rendering engine
      layout: newspaper # Example layout, choose based on Tableau layout or default to newspaper/grid
      # tile_size: 100 # Default for newspaper is based on columns/rows, 160 for tile
      # width: 1200 # Relevant for static layout
      refresh: # Optional: e.g., 1 hour
      auto_run: true # Typically true for initial load
      crossfilter_enabled: true # Enable cross-filtering if used in Tableau

      filters:
        # Example Filter (corresponds to filters used in KPI/elements below)
        - name: Year_Filter # Unique name for the filter
          title: "Year" # User-friendly title
          type: field_filter # Type of filter
          model: <model_name> # e.g., extracted from context
          explore: <base_explore_name> # e.g., extracted from model file
          field: <base_explore_name>.<filter_dimension_1> # e.g., actual_table_name.year_field
          default_value: "" # Default value (empty string means no default filter)
          allow_multiple_values: true
          required: false

        # Example Filter 2
        - name: Region_Filter
          title: "Region"
          type: field_filter
          model: <model_name>
          explore: <base_explore_name>
          field: <base_explore_name>.<filter_dimension_2> # e.g., actual_table_name.region_field
          default_value: ""
          allow_multiple_values: true
          required: false
        # (Add other dashboard-level filters as needed)

      elements:
        # --- Example KPI Element (Single Value) ---
        - name: kpi_<kpi_measure_name>_<unique_id> # e.g., kpi_sales_123
          title: "Total Sales" # Meaningful title based on measure
          type: single_value
          model: <model_name> # e.g., extracted from context
          explore: <base_explore_name> # e.g., extracted from model file (Use the BASE explore)
          fields: [<base_explore_name>.<kpi_measure_name>] # e.g., [actual_table_name.sales] (Single measure from BASE explore)
          # Define element-level filters based on Tableau context (values usually empty)
          filters:
             <base_explore_name>.<filter_dimension_1>: "" # e.g., actual_table_name.year_field: ""
             <base_explore_name>.<filter_dimension_2>: "" # e.g., actual_table_name.region_field: ""
          # Listen for dashboard-level filters
          listen:
             Year_Filter: <base_explore_name>.<filter_dimension_1> # Map dashboard filter name to element field
             Region_Filter: <base_explore_name>.<filter_dimension_2>
          limit: 500 # Standard limit for single value
          value_format: "$#,##0" # Example format, infer from Tableau/measure type
          custom_color_enabled: true
          show_single_value_title: true
          show_comparison: false
          defaults_version: 1
          # Layout properties (adjust based on newspaper grid)
          row: 0
          col: 0
          width: 6 # Example width in newspaper columns (out of 24)
          height: 3 # Example height in newspaper rows (each row ~50px high by default)

        # --- Example Standard Chart Element (Column Chart) ---
        - name: sales_by_category_chart # Unique name for the element
          title: "Sales by Category"
          type: looker_column # Chart type based on looker_chart_type
          model: <model_name>
          explore: <base_explore_name>
          fields: [<base_explore_name>.<dimension_name>, <base_explore_name>.<measure_name>] # e.g., [actual_table_name.category, actual_table_name.sales]
          pivots: [<base_explore_name>.<pivot_dimension_name>] # Optional: e.g., [actual_table_name.segment]
          sorts: [<base_explore_name>.<measure_name> desc] # Example sort
          limit: 500 # Standard limit
          stacking: '' # Example: '', normal, percent (based on Tableau stacked_type)
          # Listen for relevant dashboard filters
          listen:
             Year_Filter: <base_explore_name>.<filter_dimension_1> # Assuming year filter applies
             Region_Filter: <base_explore_name>.<filter_dimension_2> # Assuming region filter applies
          # Layout properties
          row: 0 # Example placement
          col: 6 # Example placement (next to KPI)
          width: 18 # Example width
          height: 8 # Example height


    ```

parameter definition:
  - enable_viz_full_screen: Allows dashboard viewers to expand tiles to full-screen.
    example: `enable_viz_full_screen: true`
  - layout: Determines dashboard element arrangement.
    example: `layout: tile`
      - Tile: Elements adjust dynamically to browser width; no conversion to user-defined dashboards.
      - Static: Elements positioned manually with top and left; no conversion support.
      - Grid: Uses row-based dynamic widths; supports conversion.
          - rows: For grid layout dashboards, Defines row height and elements per row. (Default height: 300px)
              example:
                rows:
                  - elements: [element1, element1]
                    height: 400
      - Newspaper: 24-column grid, default element size is 8 columns × 6 rows; supports conversion. (Recommended for flexibility).
  - tile_size: Defines element size in pixels for tile/static layouts. The default value is 160 pixels.
    example: `tile_size: 160`
  - width: For static layout dashboards, Specifies dashboard width in pixels for centering. The default width is 1200 pixels if not specified.
    example: `width: 1200`
  - refresh: Enables auto-refresh interval.
    example: `refresh: 60 minutes`
  - auto_run: Runs dashboard automatically on load.
    example: `auto_run: true`
  - crossfilter_enabled: Enables/disables cross-filtering between elements.
    example: `crossfilter_enabled: true`
  - filters: Defines dashboard-level filters. Elements must `listen:` to these filters to be affected.
    example: (See Sample Format section for full filter definition)
  - elements: Specifies individual dashboard components (visualizations, text, etc.).
    - Use only valid field names defined in the corresponding `.view.lkml` files joined into the element's specified `explore`.
    - Do not reference fields that are not defined or accessible in the element's explore context.
    - stacking: Determines the stacked type for applicable charts (bar, column, area, scatter, line). Values: `normal`, `''` (empty string for grouped/overlay), `percent`.
      example: `stacking: normal`
    - fields: Lists dimensions and measures used in the visualization element. Must reference fields accessible in the element's `explore`.
      example: `fields: [orders.order_date_week, orders.total_sales]`
    - pivots: Lists fields used for pivoting data in the element.
      example: `pivots: [orders.category]`
    - sorts: Defines sort order using fields from the element's `fields:` or `pivots:` list. Add `desc` for descending.
      example: `sorts: [orders.total_sales desc]`
    - limit: Optional. Sets the maximum number of rows/results for the element's query.
      example: `limit: 500`
    - listen: Maps dashboard filter names to the specific fields within the element's explore that the filter should affect. Crucial for interactivity.

Tableau File:
```
{content}
```

Model Files:
{model_prompt}

Views File:
{view_prompt}
    """

    response = generate_response_with_gemini(prompt)
    return response