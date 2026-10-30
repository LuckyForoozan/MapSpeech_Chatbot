import os
import requests
from dotenv import load_dotenv

load_dotenv()


def find_places(category, city="Napoli"):
    """
    Search Google Maps Places API (New) for up to 5 verified places matching `category` in `city`.
    Returns a list of dicts with real 'name' and 'address'.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [
            {
                "name": "Google Maps API Key Missing",
                "address": "Please set GOOGLE_MAPS_API_KEY in your .env file.",
            }
        ]

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress",
    }
    body = {
        "textQuery": f"{category} in {city}".strip(),
        "pageSize": 5,
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        data = response.json()
        places_data = data.get("places", [])
    except Exception as e:
        print(f"[Google Maps Places API Error] {e}")
        places_data = []

    places = []
    for item in places_data[:5]:
        display_name = item.get("displayName", {})
        name = display_name.get("text", "")
        address = item.get("formattedAddress", "")
        if name:
            places.append({
                "name": name,
                "address": address,
            })

    return places


# Backwards compatibility alias
find_place = find_places
