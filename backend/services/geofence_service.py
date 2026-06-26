import math
import logging
from datetime import datetime
from backend.database.db import get_db

logger = logging.getLogger("faceai.geofence_service")

# Earth radius in meters
EARTH_RADIUS_METERS = 6371000.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula. Returns distance in meters.
    """
    try:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        
        distance = EARTH_RADIUS_METERS * c
        return distance
    except Exception as e:
        logger.error(f"Error computing Haversine distance: {e}")
        return float('inf')

def get_active_geo_fences() -> list[dict]:
    """Retrieve all active geo fences from the database."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, location_name, latitude, longitude, radius_meters, is_active 
                    FROM geo_fences 
                    WHERE is_active = TRUE
                    """
                )
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch active geo-fences: {e}")
        return []

def is_location_required() -> bool:
    """True when at least one active geofence is configured."""
    return len(get_active_geo_fences()) > 0

def verify_location(user_lat: float, user_lon: float) -> tuple[bool, int | None, str | None]:
    """
    Verify if the given coordinates lie within the radius of any active geo fence.
    Returns (is_verified, geo_fence_id, location_name)
    """
    # Guard: if no coordinates provided, skip DB call entirely
    if user_lat is None or user_lon is None:
        active_fences = get_active_geo_fences()
        if not active_fences:
            return True, None, "Default (No Active Geo Fences)"
        return False, None, None

    active_fences = get_active_geo_fences()
    if not active_fences:
        return True, None, "Default (No Active Geo Fences)"

    for fence in active_fences:
        dist = haversine_distance(user_lat, user_lon, fence["latitude"], fence["longitude"])
        logger.info(f"Checking location: User is {dist:.1f}m away from GeoFence '{fence['location_name']}' (radius: {fence['radius_meters']}m)")
        if dist <= fence["radius_meters"]:
            return True, fence["id"], fence["location_name"]

    return False, None, None

def get_location_details(user_lat: float, user_lon: float) -> dict:
    """Return human-readable location check details for the UI."""
    active_fences = get_active_geo_fences()
    if not active_fences:
        return {"ok": True, "location_required": False, "message": "Location check not required."}

    if user_lat is None or user_lon is None:
        return {
            "ok": False,
            "location_required": True,
            "message": "GPS location not available yet.",
        }

    nearest = None
    for fence in active_fences:
        dist = haversine_distance(user_lat, user_lon, fence["latitude"], fence["longitude"])
        if dist <= fence["radius_meters"]:
            return {
                "ok": True,
                "location_required": True,
                "message": f"Inside '{fence['location_name']}' ({dist:.0f}m from center).",
                "distance_m": round(dist, 1),
                "fence_name": fence["location_name"],
            }
        if nearest is None or dist < nearest["distance_m"]:
            nearest = {
                "distance_m": dist,
                "fence_name": fence["location_name"],
                "radius_m": fence["radius_meters"],
            }

    return {
        "ok": False,
        "location_required": True,
        "message": (
            f"Outside allowed area — {nearest['distance_m']:.0f}m from "
            f"'{nearest['fence_name']}' (allowed radius: {nearest['radius_m']:.0f}m)."
        ),
        "distance_m": round(nearest["distance_m"], 1),
        "fence_name": nearest["fence_name"],
    }

def add_geo_fence(name: str, lat: float, lon: float, radius: float, is_active: bool = True, user_id: int | None = None) -> int | None:
    """Add a new geo fence and return its row ID."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO geo_fences (location_name, latitude, longitude, radius_meters, is_active, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (name.strip(), lat, lon, radius, is_active, user_id)
                )
                return cursor.lastrowid
    except Exception as e:
        logger.error(f"Failed to add geo-fence: {e}")
        return None

def update_geo_fence(fence_id: int, name: str, lat: float, lon: float, radius: float, is_active: bool) -> bool:
    """Update an existing geo fence."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE geo_fences 
                    SET location_name = %s, latitude = %s, longitude = %s, radius_meters = %s, is_active = %s
                    WHERE id = %s
                    """,
                    (name.strip(), lat, lon, radius, is_active, fence_id)
                )
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to update geo-fence {fence_id}: {e}")
        return False

def delete_geo_fence(fence_id: int) -> bool:
    """Delete a geo fence by its ID."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM geo_fences WHERE id = %s", (fence_id,))
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to delete geo-fence {fence_id}: {e}")
        return False

def list_all_geo_fences() -> list[dict]:
    """Retrieve all geo fences from the database."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM geo_fences ORDER BY id DESC")
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to list all geo-fences: {e}")
        return []
