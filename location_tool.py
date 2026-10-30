import math
import requests


def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points in meters."""
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_place(query, user_lat=None, user_lon=None):
    """
    Search OpenStreetMap for places matching `query`.
    If user_lat and user_lon are provided, biases search around the user's coordinates
    and sorts results by physical distance (closest first).
    """
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "MapSpeech-Chatbot/1.0"}

    params = {
        "q": query,
        "format": "json",
        "limit": 10,
        "addressdetails": 1,
    }

    if user_lat is not None and user_lon is not None:
        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
            # ~8-10 km viewbox window around user
            delta = 0.08
            params["viewbox"] = f"{user_lon - delta},{user_lat + delta},{user_lon + delta},{user_lat - delta}"
            params["bounded"] = 0
        except (ValueError, TypeError):
            user_lat, user_lon = None, None

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        results = response.json()
    except Exception:
        results = []

    # If nothing found with the viewbox bias, fallback to general search
    if not results and "viewbox" in params:
        params.pop("viewbox", None)
        params.pop("bounded", None)
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            results = response.json()
        except Exception:
            results = []

    places = []
    for r in results:
        try:
            p_lat = float(r["lat"])
            p_lon = float(r["lon"])
        except (KeyError, ValueError, TypeError):
            continue

        addr = r.get("address", {})
        road = addr.get("road") or addr.get("pedestrian") or ""
        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
        short_addr = f"{road}, {city}".strip(" ,") if road or city else r.get("display_name", "")

        item = {
            "name": r.get("name") or (r.get("display_name", "").split(",")[0]),
            "address": short_addr,
            "full_name": r.get("display_name", ""),
            "lat": p_lat,
            "lon": p_lon,
        }

        if user_lat is not None and user_lon is not None:
            dist = haversine(user_lat, user_lon, p_lat, p_lon)
            item["distance_meters"] = round(dist)
            if dist < 1000:
                item["distance"] = f"{int(round(dist))} meters away"
            else:
                item["distance"] = f"{round(dist / 1000, 1)} km away"

        places.append(item)

    # Sort ascending by distance if user location is known
    if user_lat is not None and user_lon is not None and places:
        places.sort(key=lambda p: p.get("distance_meters", float("inf")))

    return places[:5]
