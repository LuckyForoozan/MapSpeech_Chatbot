import requests

def find_place(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 3}
    headers = {"User-Agent": "voicebot-learning-project"}
    results = requests.get(url, params=params, headers=headers, timeout=10).json()
    return [{"name": r["display_name"], "lat": r["lat"], "lon": r["lon"]} for r in results]

