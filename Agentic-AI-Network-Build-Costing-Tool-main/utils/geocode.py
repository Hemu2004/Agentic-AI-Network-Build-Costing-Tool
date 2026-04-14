"""Geocoding and distance calculation for Maps Planner."""
import math
from typing import Optional, Tuple

# Default Central Office / Data Center (e.g. Hyderabad, India)
DEFAULT_CO_LAT = 17.3850
DEFAULT_CO_LNG = 78.4867

# Nominatim requires an identifiable User-Agent (see https://operations.osmfoundation.org/policies/nominatim/)
_NOMINATIM_UA = "VirtusFTTPEstimator/1.0 (internal network planning; local dev)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points (Haversine formula)."""
    R = 6371  # Earth radius km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def destination_point_km(lat: float, lon: float, distance_km: float, bearing_degrees: float = 45.0) -> Tuple[float, float]:
    """
    Compute destination point from (lat, lon) given distance (km) and bearing (degrees).
    Uses spherical Earth model.
    """
    R = 6371.0
    brng = math.radians(bearing_degrees)
    d = float(distance_km) / R
    lat1 = math.radians(float(lat))
    lon1 = math.radians(float(lon))

    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(lat2))

    return (math.degrees(lat2), ((math.degrees(lon2) + 540) % 360) - 180)


def _geocode_nominatim_httpx(location: str) -> Optional[Tuple[float, float]]:
    try:
        import httpx

        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            r = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": location.strip(), "format": "json", "limit": "1"},
                headers={"User-Agent": _NOMINATIM_UA},
            )
            r.raise_for_status()
            data = r.json()
            if data and isinstance(data, list):
                item = data[0]
                return (float(item["lat"]), float(item["lon"]))
    except Exception:
        pass
    return None


def _geocode_photon_httpx(location: str) -> Optional[Tuple[float, float]]:
    """Photon (Komoot) — tolerant CORS on their API; good fallback when Nominatim blocks."""
    try:
        import httpx

        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            r = client.get(
                "https://photon.komoot.io/api/",
                params={"q": location.strip(), "limit": 1},
                headers={"User-Agent": _NOMINATIM_UA},
            )
            r.raise_for_status()
            payload = r.json()
            feats = payload.get("features") or []
            if not feats:
                return None
            coords = feats[0].get("geometry", {}).get("coordinates")
            if not coords or len(coords) < 2:
                return None
            lon, lat = float(coords[0]), float(coords[1])
            return (lat, lon)
    except Exception:
        pass
    return None


def _geocode_geopy(location: str) -> Optional[Tuple[float, float]]:
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError

        geolocator = Nominatim(user_agent=_NOMINATIM_UA)
        loc = geolocator.geocode(location.strip(), timeout=10)
        if loc:
            return (float(loc.latitude), float(loc.longitude))
    except (GeocoderTimedOut, GeocoderServiceError, Exception):
        pass
    return None


def geocode_location(location: str) -> Optional[Tuple[float, float]]:
    """Resolve address to (lat, lng). Tries Nominatim (httpx), Photon, then geopy."""
    if not (location or "").strip() or (location or "").strip().lower() == "area":
        return None

    cleaned = location.strip()

    coords = _geocode_nominatim_httpx(cleaned)
    if coords:
        return coords

    coords = _geocode_photon_httpx(cleaned)
    if coords:
        return coords

    return _geocode_geopy(cleaned)
