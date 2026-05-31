import requests
import time
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

CACHE = {}
CACHE_TTL = 60 * 60  # 1 hora

FALLBACK_LOCATIONS = [
    {"label": "Rossio, Lisboa, Portugal", "lat": 38.7149, "lon": -9.1394},
    {"label": "Aeroporto Humberto Delgado, Lisboa, Portugal", "lat": 38.7742, "lon": -9.1342},
    {"label": "Parque das Nações, Lisboa, Portugal", "lat": 38.7680, "lon": -9.0948},
    {"label": "Lisboa, Portugal", "lat": 38.7223, "lon": -9.1393},
    {"label": "Porto, Portugal", "lat": 41.1579, "lon": -8.6291},
    {"label": "Bragança, Portugal", "lat": 41.8060, "lon": -6.7567},
    {"label": "Leiria, Portugal", "lat": 39.7436, "lon": -8.8071},
    {"label": "Algarve, Portugal", "lat": 37.0179, "lon": -7.9308},
    {"label": "Belém, Lisboa, Portugal", "lat": 38.6977, "lon": -9.2068},
]


def fallback_search(query):
    q = query.lower()
    return [item for item in FALLBACK_LOCATIONS if q in item["label"].lower()][:5]


@api_view(["GET"])
def geocoding_search(request):
    query = request.GET.get("q", "").strip().lower()

    if len(query) < 3:
        return Response([], status=status.HTTP_200_OK)

    now = time.time()

    if query in CACHE:
        cached_time, cached_results = CACHE[query]
        if now - cached_time < CACHE_TTL:
            return Response(cached_results, status=status.HTTP_200_OK)

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{query}, Portugal",
                "format": "jsonv2",
                "limit": 5,
                "countrycodes": "pt",
            },
            headers={
                "User-Agent": "HermezApp/1.0",
                "Accept-Language": "pt-PT",
            },
            timeout=15,
        )

        if response.status_code == 429:
            results = fallback_search(query)
            CACHE[query] = (now, results)
            return Response(results, status=status.HTTP_200_OK)

        response.raise_for_status()
        data = response.json()

        results = [
            {
                "label": item.get("display_name", ""),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
            }
            for item in data
            if item.get("display_name") and item.get("lat") and item.get("lon")
        ]

        CACHE[query] = (now, results)
        return Response(results, status=status.HTTP_200_OK)

    except requests.RequestException:
        results = fallback_search(query)
        return Response(results, status=status.HTTP_200_OK)