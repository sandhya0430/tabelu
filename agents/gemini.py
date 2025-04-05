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