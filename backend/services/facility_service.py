"""
services/facility_service.py
------------------------------
Facility register and routing for strategic disposition.

WHAT CHANGED, AND WHY IT MATTERS
The register used to be two hardcoded Python lists in this file. It is now
backend/data/facilities.json, so a facility can be corrected, sourced or
given real coordinates without a code edit. Every entry carries its own
source_url, coordinates_source, status and last_verified, because a
municipal council reading a dispatch note is entitled to ask where the
claim came from.

THREE RULES THIS MODULE ENFORCES, NOT SUGGESTS

  1. A facility with null coordinates is EXCLUDED from distance routing.
     It cannot be nearest-anything, because nothing here knows where it
     is. It is returned in `excluded` so the caller can say "the register
     holds this plant but has no coordinate for it yet" instead of
     quietly behaving as though the plant did not exist.

  2. An `unconfirmed` facility is NEVER the recommendation. It may be
     offered as an alternative, flagged, so an operator can see the
     option exists while knowing it is not vouched for.

  3. Distances are straight-line (Haversine) great-circle kilometres.
     Good enough to answer "which plant is nearer"; NOT road distance,
     and not a basis for logistics costing.

A consequence worth stating plainly rather than discovering in
production: when every facility of the recommended technology is either
uncoordinated or unconfirmed, `recommended` is None. That is the correct
answer -- the register genuinely does not support a recommendation -- and
`recommendation_blocked_reason` says which of the two rules bit.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Literal, Optional

Technology = Literal["pyrolysis", "incineration_wte", "mechanical_recycling"]
Status = Literal["operational", "unconfirmed"]

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
FACILITIES_PATH = os.path.join(DATA_DIR, "facilities.json")
LOCAL_AUTHORITIES_PATH = os.path.join(DATA_DIR, "local_authorities.json")

# Origin used when the caller names no local authority and gives no
# coordinates. Overridable with DEFAULT_LOCAL_AUTHORITY in .env.
FALLBACK_LOCAL_AUTHORITY = "Colombo"

# Kept at their previous values so an existing caller that still passes
# bare lat/lon keeps working unchanged.
DEFAULT_LATITUDE = 6.9271
DEFAULT_LONGITUDE = 79.8612

EARTH_RADIUS_KM = 6371.0


# --------------------------------------------------------------------- models

@dataclass(frozen=True)
class Facility:
    id: str
    name: str
    operator: str
    town: str
    district: str
    latitude: Optional[float]
    longitude: Optional[float]
    technology: Technology
    accepts: tuple[str, ...]
    exports_electricity: bool
    tariff_lkr_per_kwh: Optional[float]
    status: Status
    source_url: Optional[str]
    coordinates_source: str
    last_verified: str

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def is_operational(self) -> bool:
        return self.status == "operational"

    @property
    def pays_for_electricity(self) -> bool:
        """
        Whether an indicative electricity value may be reported for this
        plant. Both conditions are required: a plant that exports nothing
        has no electricity to value, and a plant whose tariff we cannot
        source would have its value invented rather than calculated.
        """
        return self.exports_electricity and self.tariff_lkr_per_kwh is not None


@dataclass(frozen=True)
class LocalAuthority:
    name: str
    district: str
    province: str
    latitude: float
    longitude: float
    coordinates_source: str


@dataclass(frozen=True)
class Origin:
    """Where a batch is dispatched FROM."""
    name: str
    latitude: float
    longitude: float
    source: str          # "local_authority" | "request_override" | "default"
    district: Optional[str] = None


@dataclass(frozen=True)
class FacilityDistance:
    facility: Facility
    distance_km: float


@dataclass(frozen=True)
class ExcludedFacility:
    facility: Facility
    reason: str


@dataclass(frozen=True)
class RouteResult:
    origin: Origin
    recommended: Optional[FacilityDistance]
    alternative: Optional[FacilityDistance]
    excluded: tuple[ExcludedFacility, ...]
    recommendation_blocked_reason: Optional[str] = None


# --------------------------------------------------------------------- loading

def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_facilities() -> tuple[Facility, ...]:
    """Every facility on the register, in file order."""
    doc = _load_json(FACILITIES_PATH)
    out = []
    for row in doc["facilities"]:
        out.append(Facility(
            id=row["id"],
            name=row["name"],
            operator=row["operator"],
            town=row["town"],
            district=row["district"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            technology=row["technology"],
            accepts=tuple(row.get("accepts", ())),
            exports_electricity=bool(row["exports_electricity"]),
            tariff_lkr_per_kwh=row["tariff_lkr_per_kwh"],
            status=row["status"],
            source_url=row.get("source_url"),
            coordinates_source=row["coordinates_source"],
            last_verified=row["last_verified"],
        ))
    return tuple(out)


@lru_cache(maxsize=1)
def load_local_authorities() -> tuple[LocalAuthority, ...]:
    doc = _load_json(LOCAL_AUTHORITIES_PATH)
    return tuple(
        LocalAuthority(
            name=row["name"],
            district=row["district"],
            province=row.get("province", ""),
            latitude=row["latitude"],
            longitude=row["longitude"],
            coordinates_source=row["coordinates_source"],
        )
        for row in doc["local_authorities"]
    )


def clear_cache() -> None:
    """Drop the parsed registers. For tests, and after editing the JSON."""
    load_facilities.cache_clear()
    load_local_authorities.cache_clear()


def find_local_authority(name: str | None) -> Optional[LocalAuthority]:
    if not name:
        return None
    key = name.strip().lower()
    for la in load_local_authorities():
        if la.name.lower() == key:
            return la
    return None


def default_local_authority_name() -> str:
    """
    Read per call rather than frozen at import, so a test (or a restart
    with a different .env) picks up the change without reloading this
    module -- the same reason data_loader.data_version() is a function.
    """
    return (os.environ.get("DEFAULT_LOCAL_AUTHORITY") or FALLBACK_LOCAL_AUTHORITY).strip()


# --------------------------------------------------------------------- geometry

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km. Straight line, not road distance."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# --------------------------------------------------------------------- origin

def resolve_origin(
    local_authority: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Origin:
    """
    Where to measure from, in precedence order:

      1. An explicit lat/lon on the request (an operator with a real GPS
         reading should not be forced onto a town centroid).
      2. The named local authority.
      3. DEFAULT_LOCAL_AUTHORITY from the environment.
      4. Central Colombo, as a last resort, so routing never hard-fails.
    """
    if latitude is not None and longitude is not None:
        return Origin(
            name=f"{latitude:.4f}, {longitude:.4f}",
            latitude=float(latitude), longitude=float(longitude),
            source="request_override",
        )

    la = find_local_authority(local_authority)
    if la is not None:
        return Origin(name=la.name, latitude=la.latitude, longitude=la.longitude,
                      source="local_authority", district=la.district)

    la = find_local_authority(default_local_authority_name())
    if la is not None:
        return Origin(name=la.name, latitude=la.latitude, longitude=la.longitude,
                      source="default", district=la.district)

    return Origin(name="Colombo (fallback)", latitude=DEFAULT_LATITUDE,
                  longitude=DEFAULT_LONGITUDE, source="default")


# --------------------------------------------------------------------- routing

def _by_technology(technology: Technology) -> list[Facility]:
    return [f for f in load_facilities() if f.technology == technology]


def _ranked(origin: Origin, candidates: list[Facility]) -> list[FacilityDistance]:
    """
    Routable candidates nearest-first. Operational sorts ahead of
    unconfirmed at equal distance, so a tie never silently prefers the
    entry nobody has verified.
    """
    routable = [
        FacilityDistance(f, round(haversine_km(origin.latitude, origin.longitude,
                                               f.latitude, f.longitude), 2))
        for f in candidates if f.has_coordinates
    ]
    routable.sort(key=lambda fd: (fd.distance_km, not fd.facility.is_operational))
    return routable


def _excluded_for(candidates: list[Facility]) -> list[ExcludedFacility]:
    out = []
    for f in candidates:
        if not f.has_coordinates:
            out.append(ExcludedFacility(
                f,
                "No coordinates on the register (coordinates_source "
                f"\"{f.coordinates_source}\"), so it cannot be distance-routed. "
                "Add latitude/longitude to backend/data/facilities.json to include it.",
            ))
    return out


def route_for_technology(
    origin: Origin,
    recommended_technology: Technology,
    alternative_technology: Technology | None = None,
) -> RouteResult:
    """
    Pick a recommendation and an alternative for one origin.

    The recommendation must be operational AND coordinated. The
    alternative may be unconfirmed (it is flagged in the response), and
    is drawn from `alternative_technology` when one is given -- otherwise
    it is the next-nearest facility of the same technology.
    """
    primary = _by_technology(recommended_technology)
    ranked_primary = _ranked(origin, primary)
    excluded = _excluded_for(primary)

    recommended = next((fd for fd in ranked_primary if fd.facility.is_operational), None)

    blocked: Optional[str] = None
    if recommended is None:
        uncoordinated = [f for f in primary if not f.has_coordinates]
        unconfirmed = [f for f in primary if f.has_coordinates and not f.is_operational]
        if not primary:
            blocked = (f"The register holds no {recommended_technology} facility at all.")
        elif uncoordinated and not unconfirmed:
            blocked = (
                f"Every {recommended_technology} facility on the register is missing "
                f"coordinates ({', '.join(f.name for f in uncoordinated)}), so none can "
                f"be distance-routed. Add latitude/longitude to "
                f"backend/data/facilities.json."
            )
        elif unconfirmed and not uncoordinated:
            blocked = (
                f"Every {recommended_technology} facility on the register is marked "
                f"unconfirmed ({', '.join(f.name for f in unconfirmed)}), and an "
                f"unconfirmed facility is never recommended. Supply a source_url and "
                f"set status to \"operational\" to enable it."
            )
        else:
            blocked = (
                f"No {recommended_technology} facility is both coordinated and "
                f"operational: {', '.join(f.name for f in uncoordinated)} lack "
                f"coordinates and {', '.join(f.name for f in unconfirmed)} "
                f"{'is' if len(unconfirmed) == 1 else 'are'} unconfirmed."
            )

    # The alternative: another technology when one is named, else the
    # next-nearest of the same one. Unconfirmed is allowed here.
    if alternative_technology is not None:
        secondary = _by_technology(alternative_technology)
        ranked_secondary = _ranked(origin, secondary)
        excluded += _excluded_for(secondary)
        alternative = next(
            (fd for fd in ranked_secondary if fd.facility.is_operational),
            ranked_secondary[0] if ranked_secondary else None,
        )
    else:
        alternative = next(
            (fd for fd in ranked_primary
             if recommended is None or fd.facility.id != recommended.facility.id),
            None,
        )

    return RouteResult(
        origin=origin,
        recommended=recommended,
        alternative=alternative,
        excluded=tuple(excluded),
        recommendation_blocked_reason=blocked,
    )


# Which technology each disposition route prefers, and what it falls back
# to. Keyed by materials_db.Route.
ROUTE_TECHNOLOGY: dict[str, tuple[Technology, Optional[Technology]]] = {
    # Polystyrene and polypropylene: pyrolysis first, waste-to-energy
    # incineration as the alternative.
    "pyrolysis": ("pyrolysis", "incineration_wte"),
    # PVC: mechanical recycling only. The alternative is the
    # next-nearest recycler, not a thermal plant -- PVC is deliberately
    # kept out of combustion.
    "mechanical_recycling": ("mechanical_recycling", None),
}


def route_for_route_name(origin: Origin, route: str) -> RouteResult:
    try:
        recommended_tech, alternative_tech = ROUTE_TECHNOLOGY[route]
    except KeyError:
        raise KeyError(f"No facility routing defined for disposition route '{route}'")
    return route_for_technology(origin, recommended_tech, alternative_tech)


# --------------------------------------------------------------- compatibility

def nearest_facility(
    latitude: float | None = None,
    longitude: float | None = None,
    kind: str = "thermal",
) -> tuple[Optional[Facility], Optional[float]]:
    """
    DEPRECATED, kept so nothing that still calls the old signature breaks.

    The old register had two buckets, "thermal" and "mechanical". Thermal
    now resolves to pyrolysis first and falls back to incineration, which
    is what the old waste-to-energy list actually meant.

    Prefer route_for_route_name(), which returns a recommendation AND an
    alternative AND tells you what it had to exclude -- all of which this
    two-value signature cannot express.
    """
    origin = resolve_origin(latitude=latitude, longitude=longitude)
    if kind == "mechanical":
        result = route_for_technology(origin, "mechanical_recycling", None)
    else:
        result = route_for_technology(origin, "pyrolysis", "incineration_wte")
    pick = result.recommended or result.alternative
    if pick is None:
        return None, None
    return pick.facility, pick.distance_km
