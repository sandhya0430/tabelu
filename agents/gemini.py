import requests
import json
import os

# Import Google Cloud libraries
import google.auth
import google.auth.transport.requests

def get_access_token():
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

# api_key = os.environ["GEMINI_API_KEY"]
def generate_response_with_gemini(prompt, url="https://us-central1-aiplatform.googleapis.com/v1/projects/gke-elastic-394012/locations/us-central1/publishers/google/models/gemini-2.0-flash:generateContent",temperature=0.1):
    """Generate a response using the Gemini Flash API."""
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT"]
            ,"temperature": temperature
            ,"maxOutputTokens": 8192
            ,"topP": 0.95
        }
    }

    try:
        # response = requests.post(f"{url}?key={api_key}", headers=headers, data=json.dumps(data))
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        response_data = response.json()

        # Extract the generated response from 'candidates'
        if "candidates" in response_data and len(response_data["candidates"]) > 0:
            generated_response = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return generated_response
        else:
            return "No valid response from Gemini API."

    except requests.exceptions.RequestException as e:
        return f"Error communicating with Gemini API: {e}"
    except KeyError as ke:
        return f"Error parsing response from Gemini API: {ke}"
    
def generate_image_response_with_gemini(image_base_64, url="https://us-central1-aiplatform.googleapis.com/v1/projects/gke-elastic-394012/locations/us-central1/publishers/google/models/gemini-2.0-flash:generateContent",temperature=0.1):
    """Generate a response using the Gemini Flash API."""
    prompt = """
Examine the provided image containing a data visualization (chart).

Your task is to:
    1. Determine the common, generic name for the chart type shown (e.g., "Line Chart", "Stacked Bar Chart", "Pie Chart", "Scatter Plot").
    2. Identify the corresponding Looker chart type identifier (e.g., `looker_line`, `looker_bar`, `looker_pie`, `looker_scatter`).\
    3. determine the stacked type used in the chart:
        - 'overlay': Data series are layered without stacking values.
        - 'stacked': Data series are stacked cumulatively by value.
        - 'stacked_percent': Data series are stacked as percentages of a whole.
        - 'Grouped': Data series are grouped by category.
        - 'No': if not applicalble

Looker chart types and explanation:
    - `looker_column`: Vertical bar chart
    - `looker_bar`: Horizontal bar chart
    - `looker_scatter`: Scatter plot
    - `looker_line`: line chart
    - `looker_area`: Area chart
    - `looker_boxplot`: Box plot
    - `looker_waterfall`: Waterfall chart
    - `looker_pie`: Pie chart
    - `looker_donut_multiples`: Donut chart multiples
    - `looker_funnel`: Funnel chart
    - `looker_timeline`: Timeline chart
    - `text`: Text display
    - `button`: Interactive button
    - `single_value`: Single value display
    - `looker_single_record`: Single record display
    - `looker_grid`: Data grid
    - `looker_google_map`: Google Map visualization
    - `looker_map`: Map visualization
    - `looker_geo_coordinates`: Geographic coordinates visualization
    - `looker_geo_choropleth`: Geographic choropleth map


Output *only* a valid JSON object matching this structure::
    {{
        "name": "<Generic Chart Name>",
        "looker_type": "<looker_chart_type>",
        "stacked_type": "<stacked_type>"
    }}
"""

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    },
                    {
                        "inlineData": {
                            # "mimeType": "image/jpeg",
                            "mimeType": "image/png",
                            "data": image_base_64 # Must be base64 encoded *string*
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature
            ,"maxOutputTokens": 1024
            ,"topP": 0.95
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        response_data = response.json()

        # Extract the generated response from 'candidates'
        if "candidates" in response_data and len(response_data["candidates"]) > 0:
            generated_response = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return generated_response
        else:
            return "No valid response from Gemini API."

    except requests.exceptions.RequestException as e:
        return f"Error communicating with Gemini API: {e}"
    except KeyError as ke:
        return f"Error parsing response from Gemini API: {ke}"