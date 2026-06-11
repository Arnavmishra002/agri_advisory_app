"""Shared request → LocationContext resolution for all API viewsets."""

from typing import Any, Dict, Optional

from rest_framework.request import Request

from ..services.location_context import LocationContext, location_resolver


def _float_param(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_param(request: Request, *keys: str) -> Any:
    for key in keys:
        if hasattr(request, "query_params") and key in request.query_params:
            val = request.query_params.get(key)
            if val not in (None, ""):
                return val
        data = getattr(request, "data", None)
        if data and key in data:
            val = data.get(key)
            if val not in (None, ""):
                return val
    return None


def resolve_request_location(request: Request) -> LocationContext:
    """
  Resolve location from API request.

  Accepts: latitude/longitude (or lat/lon), accuracy/accuracy_meters, location text.
  GPS coordinates always win when valid (India bounds).
    """
    lat = _float_param(_get_param(
        request, "latitude", "lat", "gps_lat", "gps_latitude"
    ))
    lon = _float_param(_get_param(
        request, "longitude", "lon", "lng", "gps_lon", "gps_longitude"
    ))
    accuracy = _float_param(_get_param(
        request, "accuracy", "accuracy_meters", "gps_accuracy"
    ))
    location_query = _get_param(request, "location", "city", "place", "address")
    state_hint = _get_param(request, "state")

    # Valid GPS in India always wins over text search (delivery-app style)
    if lat is not None and lon is not None:
        from ..services.location_context import _in_india

        if _in_india(lat, lon):
            ctx = location_resolver.resolve(
                latitude=lat,
                longitude=lon,
                location_query=None,
                accuracy_meters=accuracy,
                use_ip_fallback=False,
            )
            if state_hint and not ctx.state:
                from dataclasses import replace
                ctx = replace(ctx, state=str(state_hint).strip())
            return ctx

    ctx = location_resolver.resolve(
        latitude=lat,
        longitude=lon,
        location_query=location_query,
        accuracy_meters=accuracy,
    )

    if state_hint and not ctx.state:
        from dataclasses import replace
        ctx = replace(ctx, state=str(state_hint).strip())

    return ctx


def attach_location_metadata(payload: Dict[str, Any], ctx: LocationContext) -> Dict[str, Any]:
    """Add resolved location block so clients know what was used."""
    payload = dict(payload)
    payload["location"] = ctx.display_name
    payload["location_context"] = ctx.to_dict()
    return payload
