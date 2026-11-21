"""Freshness and provenance checks for official mandi price rows."""

from __future__ import annotations

import os
import math
from datetime import datetime, time, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo


INDIA_TZ = ZoneInfo("Asia/Kolkata")


def max_market_age_hours() -> float:
    """Maximum accepted age for the latest government-published daily price."""
    try:
        # Agmarknet is a daily feed.  A row older than one calendar day is a
        # dated reference, not a current price, even when it is official.
        # NOTE: the source itself often lags 1-2 days, so on many days there is
        # legitimately no "live" row.  That is surfaced as a dated official
        # reference carrying its published date, never relabelled as current.
        return max(1.0, float(os.getenv("MANDI_MAX_DATA_AGE_HOURS", "24")))
    except (TypeError, ValueError):
        return 24.0


def parse_market_datetime(value: Any) -> Optional[datetime]:
    """Parse Agmarknet/data.gov.in date formats at the usual 09:00 IST release."""
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("/", "-")
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d-%m-%y"):
        try:
            day = datetime.strptime(raw, fmt).date()
            return datetime.combine(day, time(hour=9), tzinfo=INDIA_TZ).astimezone(timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=INDIA_TZ)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def filter_fresh_live_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    response_date: Any = None,
    now: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], Optional[int], str]:
    """Keep only official, positive-price rows inside the configured freshness window.

    A missing publication date is not evidence that a row is current.  It is
    rejected so an upstream API cannot accidentally turn an undated response
    into a fabricated "today" price.
    """
    now_utc = now or datetime.now(tz=timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    max_age = max_market_age_hours()
    accepted: List[Dict[str, Any]] = []
    ages: List[int] = []
    newest_label = ""

    for item in rows:
        row = dict(item)
        if row.get("is_live") is not True:
            continue
        try:
            price = float(row.get("modal_price") or 0)
            if not math.isfinite(price) or price <= 0:
                continue
        except (TypeError, ValueError):
            continue
        reported = row.get("reported_date") or row.get("date") or response_date
        reported_at = parse_market_datetime(reported)
        if reported_at is None:
            continue
        age_hours = max(0.0, (now_utc - reported_at).total_seconds() / 3600)
        # A future publication date usually means the provider returned a
        # malformed value or the server clock is wrong. Do not present it as
        # fresher-than-live market data.
        if reported_at > now_utc:
            continue
        if age_hours > max_age:
            continue
        row["reported_date"] = str(reported)
        row["data_age_minutes"] = int(age_hours * 60)
        row["freshness"] = "latest_official"
        accepted.append(row)
        ages.append(row["data_age_minutes"])
        if not newest_label or reported_at > (parse_market_datetime(newest_label) or reported_at):
            newest_label = str(reported)

    return accepted, (min(ages) if ages else None), newest_label


def build_dated_official_reference(
    rows: Iterable[Dict[str, Any]],
    *,
    response_date: Any = None,
    now: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], Optional[int], str]:
    """Return recent official rows that are too old to call live.

    Agmarknet can publish its newest trading-day summary after a weekend or
    reporting gap. These rows remain useful as a dated benchmark, but must not
    be presented as today's price or as a selected mandi's exact quote.
    """
    now_utc = now or datetime.now(tz=timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    try:
        max_reference_days = max(
            1.0, float(os.getenv("MANDI_MAX_REFERENCE_AGE_DAYS", "7"))
        )
    except (TypeError, ValueError):
        max_reference_days = 7.0

    newest_at: Optional[datetime] = None
    dated_rows: List[Dict[str, Any]] = []
    ages: List[int] = []
    newest_label = ""

    for item in rows:
        row = dict(item)
        try:
            price = float(row.get("modal_price") or 0)
            if not math.isfinite(price) or price <= 0:
                continue
        except (TypeError, ValueError):
            continue
        reported = row.get("reported_date") or row.get("date") or response_date
        reported_at = parse_market_datetime(reported)
        if reported_at is None or reported_at > now_utc:
            continue
        age_hours = (now_utc - reported_at).total_seconds() / 3600
        if age_hours <= max_market_age_hours():
            continue
        if age_hours > max_reference_days * 24:
            continue

        row["reported_date"] = str(reported)
        row["data_age_minutes"] = int(age_hours * 60)
        row["freshness"] = "dated_official"
        row["is_live"] = False
        dated_rows.append(row)
        ages.append(row["data_age_minutes"])
        if newest_at is None or reported_at > newest_at:
            newest_at = reported_at
            newest_label = str(reported)

    if newest_at is not None:
        dated_rows = [
            row
            for row in dated_rows
            if parse_market_datetime(row.get("reported_date")) == newest_at
        ]
        ages = [int(row["data_age_minutes"]) for row in dated_rows]

    return dated_rows, (min(ages) if ages else None), newest_label
