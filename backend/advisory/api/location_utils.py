"""Shared request → LocationContext resolution for all API viewsets."""

from typing import Any, Dict, Optional

from rest_framework.request import Request
from rest_framework import status
from rest_framework.response import Response

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


def resolve_request_location(
    request: Request,
    *,
    enrich_coordinates: bool = True,
) -> LocationContext:
    """
    Resolve location from API request.

    Accepts latitude/longitude (or lat/lon), accuracy/accuracy_meters, and
    location text.
    GPS coordinates always win when valid (India bounds).

    ``enrich_coordinates=False`` keeps latency-sensitive, non-advisory paths
    local when the client already supplied a confirmed label and coordinates.
    It must not be used for weather, mandi, crop, or field advice, where the
    full district/state context affects the result.
    """
    location_confirmed = _get_param(request, "location_confirmed")
    if location_confirmed is False or str(location_confirmed).strip().lower() in {
        "0", "false", "no", "off"
    }:
        return LocationContext(
            latitude=None,
            longitude=None,
            display_name="",
            country="India",
            location_type="country",
            accuracy_label="unknown",
            source="unconfirmed",
            confidence=0.0,
            is_gps=False,
        )

    lat = _float_param(_get_param(
        request, "latitude", "lat", "gps_lat", "gps_latitude"
    ))
    lon = _float_param(_get_param(
        request, "longitude", "lon", "lng", "gps_lon", "gps_longitude"
    ))
    accuracy = _float_param(_get_param(
        request, "accuracy", "accuracy_meters", "gps_accuracy"
    ))
    location_query = _get_param(
        request,
        "location",
        "location_name",
        "city",
        "village",
        "district",
        "place",
        "address",
    )
    state_hint = _get_param(request, "state")
    requested_source = str(_get_param(request, "location_source") or "unknown").strip().lower()

    # Valid GPS in India always wins over text search (delivery-app style)
    if lat is not None and lon is not None:
        from ..services.location_context import _in_india, _region_from_state

        if _in_india(lat, lon):
            if not enrich_coordinates:
                selected_name = str(location_query or state_hint or "").strip()
                selected_state = str(state_hint or "").strip()
                source = (
                    requested_source
                    if requested_source != "unknown"
                    else "request_coordinates"
                )
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    display_name=selected_name,
                    city=selected_name if selected_name else "",
                    state=selected_state,
                    region=_region_from_state(selected_state),
                    location_type="request_coordinates",
                    accuracy_meters=accuracy,
                    accuracy_label=(
                        "high" if accuracy is not None and accuracy <= 100
                        else "medium"
                    ),
                    source=source,
                    confidence=0.9 if selected_name else 0.7,
                    is_gps=requested_source == "gps",
                    full_address=(
                        f"{selected_name}, {selected_state}"
                        if selected_name and selected_state and selected_state != selected_name
                        else selected_name or selected_state
                    ),
                )
            if requested_source == "manual_search" and location_query:
                selected_name = str(location_query).strip()
                selected_state = str(state_hint or "").strip()
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    display_name=selected_name,
                    city=selected_name,
                    state=selected_state,
                    region=_region_from_state(selected_state),
                    location_type="manual_selection",
                    accuracy_meters=accuracy,
                    accuracy_label=(
                        "high" if accuracy is not None and accuracy <= 100
                        else "medium"
                    ),
                    source="manual_search",
                    confidence=0.9,
                    is_gps=False,
                    full_address=(
                        f"{selected_name}, {selected_state}"
                        if selected_state and selected_state != selected_name
                        else selected_name
                    ),
                )
            ctx = location_resolver.resolve(
                latitude=lat,
                longitude=lon,
                location_query=None,
                accuracy_meters=accuracy,
                use_ip_fallback=False,
            )
            from dataclasses import replace

            updates = {}
            if state_hint and not ctx.state:
                updates["state"] = str(state_hint).strip()
            if requested_source == "gps":
                updates.update({"source": "gps", "is_gps": True})
            elif requested_source == "profile":
                updates.update({"source": "farmer_profile", "is_gps": False})
            if updates:
                ctx = replace(ctx, **updates)
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


def require_confirmed_location(
    ctx: LocationContext,
    *,
    service: str,
) -> Optional[Response]:
    """Return a consistent 400 response when location-sensitive work is unsafe."""
    if ctx.confirmed:
        return None

    return Response(
        attach_location_metadata(
            {
                "status": "location_required",
                "error_code": "LOCATION_REQUIRED",
                "service": service,
                "is_live": False,
                "message": (
                    "Confirm GPS or choose your village/district before using "
                    "this location-based service."
                ),
                "message_hi": (
                    "इस स्थान-आधारित सेवा के लिए GPS की पुष्टि करें या अपना "
                    "गांव/जिला चुनें।"
                ),
            },
            ctx,
        ),
        status=status.HTTP_400_BAD_REQUEST,
    )


def attach_location_metadata(payload: Dict[str, Any], ctx: LocationContext) -> Dict[str, Any]:
    """Add resolved location block so clients know what was used."""
    payload = dict(payload)
    payload["location"] = ctx.display_name
    location_context = ctx.to_dict()
    location_context["confirmed"] = ctx.confirmed
    payload["location_context"] = location_context
    return payload
