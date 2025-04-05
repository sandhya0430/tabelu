import os
from agents.gemini import generate_response_with_gemini
from utils import generate_view_text, generate_model_text

def structure_agent(content):
    prompt = f"""{content}
    you are an expert in analysing tableau file and writing lookml i want you to convert the provided tableau file to lookml files. So just  return the file names(.views,.models,.dashboard) that is needed to achive this in a json format.
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
        - Ensure dimensions are create for all <map> using the value if cols are present. [MUST]
        - create dimension and measure using the <column-instance>
        - refer the table details in <cols> if present otherwise there is only one table there
    - Map columns with role='dimension' to Dimension and those with role='measure' to Measure in LookML.
    - Extract looker_datatype and assign correct LookML type.
            Example xml:
            <column-instance column='[DATE]' derivation='Quarter' role='dimension' looker_datatype='data_quarter' name='[qr:DATE:ok]' pivot='key' type='ordinal' />
        example lkml: 
            dimension: data_quater {{
                description: "Quarterly date derived from the DATE field"
                type: date_quarter
                sql: table.DATE ;;
            }}

    Output Requirements:

      For the specified Tableau XML, you MUST return LookML code in the following format:

      1.  Primary View File (`{{file_name}}.view`):
          - Generate a .view file named `{{file_name}}.view` (e.g., `orders.view` if `file_name` is "Orders").
          - This file will contain dimensions and measures derived from the primary table (and potentially joined table, as specified in the prompt).
          - Include the `is_{{joined_table_name}}_present` helper dimension if applicable (inner join and no other fields from joined table used in this view).

      2.  Minimal Joined Table View File (`{{joined_table_name}}.view`):
          - IF an inner join is detected between two tables, and the `file_name` corresponds to the primary table, THEN generate a separate .view file for the joined table.
          - This file should be named `{{joined_table_name}}.view` (e.g., `returns.view`).
          - It MUST contain at least:
              ```lookml
              view: {{joined_table_name}} {{
                sql_table_name: `your_project.your_dataset.{{joined_table_name}}` ;;

                dimension: {{join_key}} {{
                  type: string
                  sql: ${{TABLE}}.{{original_column_name}} ;;
                }}
              }}
              ```
              - Replace `{{joined_table_name}}`, `{{join_key}}`, and `{{original_column_name}}` dynamically.
              - Add additional dimensions from the joined table ONLY IF they are present in `<column>` or `<column-instance>` elements for that table.
              - If no column metadata for the joined table is found, only include the `join_key` dimension.

    - Ensure correct indentation and syntax to produce a well-formatted view lkml file that adheres to Looker's standards.
    - do not use additional parameter that are not mensioned in the sample view format.
    - Only create view file for the specified file name and also do not generate two view in the same file.
    - view_name must be in lowercase
    - always use meaningful unique name for the field name

    - For any dimension where the LookML type is `date` or starts with `date_` (such as `date_year`, `date_month`):
    - Always cast the SQL expression to `TIMESTAMP` using `CAST(${'TABLE'}.column_name AS TIMESTAMP)` to prevent type mismatches in filters or comparisons.
    - This is critical when filters, dashboard conditions, or chart logic compare a `DATE` field to a `TIMESTAMP`.
    - Skip casting only if the source field is already a TIMESTAMP or DATETIME in the database schema.
    - This rule must be applied dynamically across all relevant fields, not hardcoded to specific column names.
    
sample view format:
```
view: view_name {{
    sql_table_name: your_schema.your_table_name ;; # *Required*: Replace with your actual table name
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
        sql: $your_table_name.column_name ;; # example sql: $sales.profit
    }}
}}
```

Specified File: {file_name}    

Tableau file: {content}
    """
    
    response = generate_response_with_gemini(prompt)
    return response

def model_agent(content,workbook_name):
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
    Always extract the correct view name by examining the view file precisely.
        - Example: If the view file contains: view: my_view_1
        - Then the model file must reference that exact view name: my_view_1.

    - Use joins only when necessary(only if multiple views has same field):
        - Join dimension tables (lookup/reference tables) that enrich the fact table, such as City, Category, or Country.
        - Avoid joins that do not add new dimensions or that cause redundancy.
        - Ensure a clear primary key relationship, such as `main_table.id = lookup_table.id`.
    - Key considerations:
        - If there are no dimension tables (lookup/reference tables), do not add any joins.
        - If all fields exist in a single table, create an explore without any joins.
        - Ensure all joins have a valid key match and are not redundant.

sample model file:
```
explore: main_view_name {{
  join: view_name1 {{
    sql_on: ${{main_view_name.field}} = ${{view_name.field}} ;;
  }}

  join: view_name2 {{
    sql_on: ${{main_view_name.field}} = ${{view_name.field}} ;;
  }}
}}
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

def dashboard_agent(content,workbook_name):
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

  - filters: Defines dashboard filters to modify displayed data. 
    - Ensure the dashboard includes appropriate filters, referencing the correct model, explore, and view fields.
    - For a filter to affect an element, the element must be set to "listen" for it using the listen parameter. This applies to all element types except text and button.
    - The `listen:` block must map each filter name to the field used in the element:
      listen:
        <filter_name>: <view_name.field_name>
    - Only include filter-to-field mappings in `listen:` if the field is actually used by the element.
    - This enables filters to dynamically update the visualizations, just like in Tableau.
  
  - When defining the 'height' and 'width' for each element, adhere to the following guidelines:
      - For `looker_grid` (table) types: set `height` between 400 and 800 based on the number of rows. A grid with >20 rows should have a height >= 600.
      - For `single_value` types: set `height` between 150 and 250.
      - For chart types (`looker_column`, `looker_bar`, `looker_line`, `looker_area`): set `width` >= 300, increasing with the number of fields displayed to avoid overlapping labels.
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
            fields: [view_name.column1, view_name.column1, view_name.column3, view_name.column4]
            pivots: [view_name.column4]
  - visualization Types:
      - When generating each element in the dashboard, use the value from looker_chart_type in the <worksheet> tag to set the type in the LookML element.
          - Additionally, if the worksheet also contains a stacked_type attribute, follow the below logic:
              - If stacked_type="stacked", then add:
                stacking: normal
              - If stacked_type="grouped" or stacked_type="overlay", then add:
                stacking: ''
              - If stacked_type="stacked_percent", then add:
                stacking: percent
          - if not included, leave it.
  - Do not use any addtional parameter that is not mentioned in the Sample LookML Dashboard Format
  - Get limit of the element from the count in the groupfilter for the appropiate worksheet
  - After generated the dashboard lookml file, recheck wheather the format is correctly matched or not, if not fix it by changing the file again
      Alwasy return the final dashboard lookml file
 
Sample LookML Dashboard Format:
```
- dashboard: dashboard_name # this must be unique so add some random number at end
  preferred_viewer: dashboards | dashboards-next
  title: "desired dashboard title"
  description: "desired dashboard description"
  enable_viz_full_screen: true | false
  layout: tile | static | grid | newspaper
  rows:
    - elements: [element_name, element_name, ...]
      height: N   # height in pixels(integer)
  tile_size: N  # tile size in pixels(integer)
  width: N  width in pixels(integer)
  refresh: N (seconds | minutes | hours | days)
  auto_run: true | false
  crossfilter_enabled: true | false
  filters:
    - name: filter_name
      title: "desired filter title"
      type: field_filter | number_filter | date_filter | string_filter
      model: model_name
      explore: explore_name
      field: view_name.field_name
      default_value: Looker filter expression
      allow_multiple_values: true | false
      required: true | false
  elements:
    - name: "element_name"
      type: looker_column | looker_bar | looker_scatter | looker_line | looker_area | looker_boxplot | looker_waterfall | looker_pie | looker_donut_multiples | looker_funnel | looker_timeline | text | button | single_value | looker_single_record | looker_grid | looker_google_map | looker_map | looker_geo_coordinates | looker_geo_choropleth
      title: "desired title"
      stacking: normal | '' | percent 
      model: model_name
      explore: explore_name
      fields: [view_name.field_name, view_name.field_name]
      pivots: [view_name.field_name, view_name.field_name]
      sorts: [view_name.field_name desc]
      limit: N # limit in integer
      listen:
        filter_name1: view_name.field_name 
        filter_name2: view_name.field_name 
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
      - Newspaper: 24-column grid, default element size is 8 columns × 6 rows; supports conversion.
  - tile_size: Defines element size in pixels for tile/static layouts. The default value is 160 pixels.
    tile_size: 160
  - width: For static layout dashboards, Specifies dashboard width in pixels for centering. The default width is 1200 pixels if not specified.
    width: 1200
  - refresh: Enables auto-refresh.
    refresh: 60 minutes
  - auto_run: Runs dashboard automatically on load.
    auto_run: true
  - crossfilter_enabled: Enables/disables cross-filtering.
    crossfilter_enabled: true
  - filters:  Defines dashboard filters to modify displayed data. For a filter to affect an element, the element must be set to "listen" for it using the listen parameter. This applies to all element types except text and button.
  - elements: Specifies dashboard elements, grouped into rows of equal width.
    - Use only valid field names defined in the corresponding `.view.lkml` files.
    - Do not reference fields that are not defined in the views.
    - stacking: determine the stacked type used in the chart (only for looker_bar, looker_column, looker_area, looker_scatter, looker_line)
    - fields: Lists dimensions and measures used in the visualization.
    - pivot: Lists fields used for pivoting if there are two or more columns or color-grouped dimensions.
    - sorts: Defines sort order using fields from the element's `fields:` list.
    - limit: Optional. Set a sensible limit for visible records.
    - listen: Always map dashboard filters to the actual fields used in the element if applicable.

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