"""
services/facility_service.py
------------------------------
"Residual Pyrolysis Tracker" -- given a facility's coordinates, finds the
nearest operating waste-to-energy / RDF treatment plant to route
non-recyclable residuals to.

FACILITIES below are real, verified operating (or under-construction)
Sri Lankan waste-to-energy plants, not placeholders:

  - Kerawalapitiya Waste-to-Energy Plant (Western Power Company, an Aitken
    Spence subsidiary) -- Sri Lanka's first WtE plant, operational since
    Feb 2021, under a Waste Supply Agreement with Colombo Municipal
    Council. ~7.0128 N, 79.8764 E (Kerawalapitiya, Western Province).

  - Karadiyana / Colombo South Waste Processing Facility (Fairway Waste
    Management), Karadiyana landfill site, serving multiple local
    authorities under the Western Province Waste Management Authority.
    6.8158 N, 79.9031 E. Feed-in tariff 37.10 LKR/kWh per its PPA.

This list is intentionally small and easy to extend -- add a facility as
soon as your own municipal partner names one, or as further regional
plants (e.g. a future Kandy/Galle facility) come online. Distances use the
Haversine great-circle formula (straight-line, not road distance -- good
enough for "which plant is closer", not for routing/logistics).
"""

from __future__ import annotations
import math
from dataclasses import dataclass

# Default source-facility location if a request doesn't supply lat/lon:
# central Colombo. Replace with your actual facility's surveyed
# coordinates once deployed.
DEFAULT_LATITUDE = 6.9271
DEFAULT_LONGITUDE = 79.8612


@dataclass(frozen=True)
class Facility:
    name: str
    facility_type: str
    latitude: float
    longitude: float
    feed_in_tariff_lkr_per_kwh: float | None


FACILITIES: list[Facility] = [
    Facility(
        name="Kerawalapitiya Waste-to-Energy Plant (Western Power Company)",
        facility_type="Waste-to-Energy",
        latitude=7.0128,
        longitude=79.8764,
        feed_in_tariff_lkr_per_kwh=None,  # PPA rate not publicly disclosed
    ),
    Facility(
        name="Karadiyana Waste-to-Energy Plant (Colombo South Waste Processing Facility)",
        facility_type="Waste-to-Energy",
        latitude=6.8158,
        longitude=79.9031,
        feed_in_tariff_lkr_per_kwh=37.10,
    ),
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r_earth_km * math.asin(math.sqrt(a))


def nearest_facility(latitude: float | None, longitude: float | None) -> tuple[Facility, float]:
    lat = latitude if latitude is not None else DEFAULT_LATITUDE
    lon = longitude if longitude is not None else DEFAULT_LONGITUDE

    best_facility, best_distance = None, math.inf
    for facility in FACILITIES:
        d = haversine_km(lat, lon, facility.latitude, facility.longitude)
        if d < best_distance:
            best_facility, best_distance = facility, d
    return best_facility, round(best_distance, 2)
