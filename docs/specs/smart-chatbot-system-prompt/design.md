# Design Document

## Overview

This document describes the technical design for upgrading the KrishiMitra chatbot from a generic context-block approach to a fully structured, variable-rendered system prompt that injects live IoT sensor telemetry, weather alerts, government RAG snippets, and mandi prices before every Gemini call.

The existing `ChatIntelligenceService` is extended in-place. No new Django apps or models are required. The change is contained to three files: `chat_intelligence_service.py`, `viewsets/chatbot.py`, and `frontend/public/js/app.js`.

## Architecture

```
Browser
  │  POST /api/chatbot/query/
  │  { query, language, latitude, longitude, session_id, sensor_context? }
  ▼
ChatbotViewSet._handle_query()
  │  extracts sensor_context from payload
  │  resolves LocationContext
  ▼
ChatIntelligenceService.answer(query, ctx, language, history, sensor_context)
  │
  ├─ classify_query()              ← intent + entity extraction (unchanged)
  │
  ├─ _resolve_sensor_context()     ← NEW: merge payload → DB lookup → simulator
  │    └─ returns SensorContext dataclass
  │
  ├─ _build_iot_block()            ← NEW: formats IoT section of prompt
  │
  ├─ _build_official_context()     ← EXTENDED: adds weather alerts, RAG snippets,
  │    weather_service              market price for query crop, structured alert flag
  │    market_service
  │    schemes_service
  │    crop_recommendation_engine
  │
  ├─ _derive_weather_constraints() ← NEW: returns WeatherConstraints dataclass
  │    (irrigation_blocked, spray_blocked, frost_warning, alerts_text, forecast_3day)
  │
  ├─ _fetch_gov_rag_snippets()     ← NEW: keyword search across ICAR crop DB
  │
  ├─ _render_grounded_prompt()     ← NEW: renders SYSTEM_PROMPT_TEMPLATE
  │    fills all {{ variable }} slots
  │
  └─ gemini_service.generate()     ← unchanged call, new richer prompt
       OR _smart_rule_response()   ← EXTENDED: applies sensor/weather checks
```

## Component Design

### 1. `SensorContext` Dataclass

A lightweight, typed container that normalises sensor data from all sources (payload, DB, simulator) into one shape.

```python
# advisory/services/chat_intelligence_service.py  (new, near top of file)
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SensorContext:
    soil_moisture_pct: Optional[float] = None
    soil_temp_c:       Optional[float] = None
    air_temp_c:        Optional[float] = None   # from weather, not sensor
    humidity_pct:      Optional[float] = None   # from weather
    nitrogen_kg_ha:    Optional[float] = None
    phosphorus_kg_ha:  Optional[float] = None
    potassium_kg_ha:   Optional[float] = None
    soil_ph:           Optional[float] = None
    hours_since_water: Optional[float] = None
    soil_health_score: Optional[int]   = None
    soil_health_grade: str             = "—"
    source:            str             = "simulated"   # "live", "db", "simulated", "none"

    # Derived fields (set by _resolve_sensor_context)
    moisture_status: str = "Unknown"   # "Critical", "Low", "Adequate", "High"

    def moisture_label(self) -> str:
        if self.soil_moisture_pct is None:
            return "Unknown (sensor offline)"
        if self.soil_moisture_pct < 35:
            return f"{self.soil_moisture_pct:.1f}% — ⚠️ CRITICAL: Irrigate immediately"
        if self.soil_moisture_pct < 50:
            return f"{self.soil_moisture_pct:.1f}% — Low: Monitor closely"
        if self.soil_moisture_pct <= 65:
            return f"{self.soil_moisture_pct:.1f}% — Adequate"
        return f"{self.soil_moisture_pct:.1f}% — High: Skip irrigation"
```

### 2. `WeatherConstraints` Dataclass

Derived from the weather context block. Used to gate irrigation and spray recommendations.

```python
@dataclass
class WeatherConstraints:
    alerts_text:        str   = "None"
    forecast_3day:      str   = "N/A"
    irrigation_blocked: bool  = False   # True if moisture high OR heavy rain forecast
    spray_blocked:      bool  = False   # True if rain >20mm within 48h
    frost_warning:      bool  = False   # True if min_temp <2°C in 3 days
    heavy_rain_48h:     bool  = False
```

### 3. `_resolve_sensor_context()` — Three-Tier Resolution

Priority order: (1) payload `sensor_context`, (2) latest `IoTSensorReading` from DB, (3) `BlockchainIoTSimulator`.

```python
def _resolve_sensor_context(
    self,
    ctx: LocationContext,
    payload_sensors: Optional[Dict[str, Any]],
) -> SensorContext:
    """
    Tier 1 — caller supplied sensor data (from frontend IoT panel)
    Tier 2 — most recent IoTSensorReading within last 24h for this GPS cell
    Tier 3 — BlockchainIoTSimulator (simulated, always available)
    """
    sc = SensorContext()

    # Tier 1: payload
    if payload_sensors and isinstance(payload_sensors, dict):
        sc = self._parse_sensor_dict(payload_sensors, source="live")
        if sc.soil_moisture_pct is not None:
            sc.moisture_status = self._classify_moisture(sc.soil_moisture_pct)
            return sc

    # Tier 2: DB lookup (lat/lon grid ±0.01°)
    try:
        from ...models import IoTSensorReading
        from django.utils import timezone
        cutoff = timezone.now() - timedelta(hours=24)
        reading = (
            IoTSensorReading.objects
            .filter(
                latitude__range=(ctx.latitude - 0.01, ctx.latitude + 0.01),
                longitude__range=(ctx.longitude - 0.01, ctx.longitude + 0.01),
                created_at__gte=cutoff,
            )
            .order_by("-created_at")
            .first()
        )
        if reading:
            hours_ago = (timezone.now() - reading.created_at).total_seconds() / 3600
            sc = SensorContext(
                soil_moisture_pct=reading.moisture_pct,
                soil_temp_c=reading.soil_temp_c,
                nitrogen_kg_ha=reading.nitrogen_kg_ha,
                phosphorus_kg_ha=reading.phosphorus_kg_ha,
                potassium_kg_ha=reading.potassium_kg_ha,
                soil_ph=reading.ph,
                hours_since_water=round(hours_ago, 1),
                source="db",
            )
            sc.moisture_status = self._classify_moisture(sc.soil_moisture_pct)
            return sc
    except Exception:
        pass

    # Tier 3: simulator
    try:
        sim = iot_blockchain.get_iot_sensor_data(ctx.query_label)
        readings = sim.get("readings", {})
        npk = readings.get("npk", {})
        health = sim.get("soil_health_score", {})
        sc = SensorContext(
            soil_moisture_pct=readings.get("soil_moisture_pct"),
            soil_temp_c=readings.get("soil_temperature_c"),
            nitrogen_kg_ha=npk.get("nitrogen_kg_ha"),
            phosphorus_kg_ha=npk.get("phosphorus_kg_ha"),
            potassium_kg_ha=npk.get("potassium_kg_ha"),
            soil_ph=readings.get("soil_ph"),
            hours_since_water=None,
            soil_health_score=health.get("score"),
            soil_health_grade=health.get("grade", "—"),
            source="simulated",
        )
        sc.moisture_status = self._classify_moisture(sc.soil_moisture_pct)
    except Exception:
        pass

    return sc

@staticmethod
def _classify_moisture(pct: Optional[float]) -> str:
    if pct is None:
        return "Unknown"
    if pct < 35:
        return "Critical"
    if pct < 50:
        return "Low"
    if pct <= 65:
        return "Adequate"
    return "High"
```

### 4. `SYSTEM_PROMPT_TEMPLATE` — The New Structured Prompt

Replaces the existing `SYSTEM_PROMPT` class constant. It is a template string with named `{{ variable }}` slots that are rendered by `_render_grounded_prompt()` before the Gemini call.

```python
SYSTEM_PROMPT_TEMPLATE = """\
You are KrishiMitra AI — an elite, hyper-intelligent Smart Agricultural Advisory AI \
for Indian farmers. Your mission is to provide SAFE, HIGHLY LOCALIZED, and DATA-DRIVEN \
agronomy advice by synthesising the live IoT sensor telemetry, regional weather, and \
official government agricultural guidelines provided below.

### OPERATIONAL FRAMEWORK
1. PERCEIVE: Analyse [LIVE IOT SENSOR DATA] FIRST. Look for anomalies — critical \
moisture drops, temperature spikes, NPK imbalances.
2. GROUND: Cross-reference the farmer's query with [OFFICIAL GOVERNMENT & WEATHER DATA]. \
Your advice MUST comply with official pesticide approvals, regional planting calendars, \
and immediate weather threats.
3. DECIDE & ACT: Provide a highly tailored diagnostic or step-by-step action plan.

### CRITICAL RULES (NEVER BREAK)
- DATA TRUTHFULNESS: NEVER recommend watering if soil moisture sensors show Adequate or \
High levels. NEVER ignore an active weather alert.
- SAFETY FIRST: For any chemical treatment (pesticide/fertiliser dose), rely ONLY on the \
verified government data in [OFFICIAL GOVERNMENT & WEATHER DATA]. If the snippet is missing \
or says "No specific advisory found", do NOT guess — tell the farmer to consult their \
local KVK extension officer or call 1800-180-1551.
- TONALITY: Be an empathetic expert agronomist. Use clear, practical, actionable language. \
Use bullet points for action steps. Avoid academic jargon unless defining a disease.
- LANGUAGE: {lang_instruction}

---

[LIVE IOT SENSOR DATA]
Soil Moisture  : {soil_moisture_label}
Soil Temp      : {soil_temp_c}°C
Ambient Temp   : {air_temp_c}°C
Humidity       : {humidity_pct}%
N (Nitrogen)   : {nitrogen_kg_ha} kg/ha  ({nitrogen_status})
P (Phosphorus) : {phosphorus_kg_ha} kg/ha  ({phosphorus_status})
K (Potassium)  : {potassium_kg_ha} kg/ha  ({potassium_status})
Soil pH        : {soil_ph}  ({ph_status})
Last Irrigation: {hours_since_water} hours ago
Soil Health    : Score {soil_health_score}/100 — Grade {soil_health_grade}
Data Source    : {sensor_source}

---

[OFFICIAL GOVERNMENT & WEATHER DATA]
3-Day Forecast      : {forecast_3day}
Severe Weather Alert: {active_weather_warnings}
Irrigation Blocked  : {irrigation_blocked}
Spray/Fert Blocked  : {spray_blocked}
Frost Warning       : {frost_warning}

Government/ICAR Advisory (use these facts for any treatment recommendation):
\"\"\"{government_rag_snippets}\"\"\"

Current Market Price: {current_market_price}
Season              : {season}
Location            : {location_label}

---

[FARMER'S CONVERSATION HISTORY]
{history_block}

---

[FARMER'S CURRENT QUERY]
{farmer_query}

---

### KIRO'S RESPONSE EVALUATION STEPS
Before writing your answer, silently check:
1. Does the farmer's request CONFLICT with the sensor data? \
(e.g., asking to irrigate when moisture is Adequate/High → refuse and explain why)
2. Does any active WEATHER ALERT or spray-block apply to this advice? \
If yes, mention it prominently FIRST.
3. Is your treatment/chemical recommendation backed by the government snippet above? \
If the snippet is missing or generic, do NOT prescribe a specific product — \
defer to a KVK extension officer.

Now write your response.
"""
```

### 5. `_render_grounded_prompt()` — Variable Population

A pure function that takes `SensorContext`, `WeatherConstraints`, RAG snippet string, market price string, and conversation metadata, and returns the fully rendered prompt string with no remaining `{...}` placeholders.

```python
def _render_grounded_prompt(
    self,
    query: str,
    ctx: LocationContext,
    sc: SensorContext,
    wc: WeatherConstraints,
    rag: str,
    market_price_str: str,
    history_block: str,
    lang: str,
    season: str,
) -> str:
    from .language_service import get_gemini_language_instruction

    def _fmt(val, unit="", fallback="N/A — sensor offline"):
        if val is None:
            return fallback
        return f"{val}{unit}"

    def _npk_status(val, low=150, high=250):
        if val is None: return "unknown"
        if val < low:   return "⚠️ Low"
        if val > high:  return "✅ Adequate"
        return "✅ Adequate"

    def _ph_status(ph):
        if ph is None: return "unknown"
        if ph < 5.5:   return "⚠️ Very Acidic"
        if ph < 6.0:   return "🟡 Acidic"
        if ph <= 7.5:  return "✅ Optimal"
        if ph <= 8.0:  return "🟡 Alkaline"
        return "⚠️ Very Alkaline"

    loc = ctx.display_name
    if ctx.state and ctx.state not in loc:
        loc = f"{ctx.display_name}, {ctx.state}"

    return self.SYSTEM_PROMPT_TEMPLATE.format(
        lang_instruction    = get_gemini_language_instruction(lang),
        # IoT
        soil_moisture_label = sc.moisture_label(),
        soil_temp_c         = _fmt(sc.soil_temp_c),
        air_temp_c          = _fmt(sc.air_temp_c),
        humidity_pct        = _fmt(sc.humidity_pct),
        nitrogen_kg_ha      = _fmt(sc.nitrogen_kg_ha),
        nitrogen_status     = _npk_status(sc.nitrogen_kg_ha),
        phosphorus_kg_ha    = _fmt(sc.phosphorus_kg_ha),
        phosphorus_status   = _npk_status(sc.phosphorus_kg_ha, low=10, high=25),
        potassium_kg_ha     = _fmt(sc.potassium_kg_ha),
        potassium_status    = _npk_status(sc.potassium_kg_ha, low=100, high=200),
        soil_ph             = _fmt(sc.soil_ph),
        ph_status           = _ph_status(sc.soil_ph),
        hours_since_water   = _fmt(sc.hours_since_water, fallback="Unknown"),
        soil_health_score   = sc.soil_health_score if sc.soil_health_score is not None else "—",
        soil_health_grade   = sc.soil_health_grade,
        sensor_source       = sc.source,
        # Weather / constraints
        forecast_3day          = wc.forecast_3day,
        active_weather_warnings= wc.alerts_text,
        irrigation_blocked     = "YES ⚠️" if wc.irrigation_blocked else "No",
        spray_blocked          = "YES ⚠️ (rain forecast within 48h)" if wc.spray_blocked else "No",
        frost_warning          = "YES ❄️" if wc.frost_warning else "No",
        # Gov / market
        government_rag_snippets= rag,
        current_market_price   = market_price_str,
        # Meta
        season         = season,
        location_label = loc,
        history_block  = history_block or "(new conversation)",
        farmer_query   = query,
    )
```

### 6. `_derive_weather_constraints()` — Alert Gate Logic

Parses the raw weather dict (already fetched in `_build_official_context`) and returns a `WeatherConstraints` object.

```python
def _derive_weather_constraints(
    self,
    weather: Dict[str, Any],
    sc: SensorContext,
) -> WeatherConstraints:
    wc = WeatherConstraints()

    alerts = weather.get("farming_alerts") or []
    if alerts:
        wc.alerts_text = " | ".join(str(a) for a in alerts[:3])
    else:
        wc.alerts_text = "None"

    forecast = (
        weather.get("forecast_7day")
        or weather.get("forecast_7_days")
        or []
    )

    # Build 3-day summary text
    if forecast:
        lines = []
        for day in forecast[:3]:
            lines.append(
                f"{day.get('date')}: max {day.get('max_temp')}°C, "
                f"rain {day.get('rainfall_mm', 0)}mm "
                f"({day.get('rain_probability', 0)}% prob)"
            )
        wc.forecast_3day = "; ".join(lines)
    else:
        wc.forecast_3day = "Forecast unavailable — check mausam.imd.gov.in"

    # Spray block: rain >20mm or >70% probability in next 2 days
    for day in forecast[:2]:
        if (day.get("rainfall_mm") or 0) > 20 or (day.get("rain_probability") or 0) > 70:
            wc.spray_blocked = True
            wc.heavy_rain_48h = True
            break

    # Frost warning: min_temp <2 in next 3 days
    for day in forecast[:3]:
        if (day.get("min_temp") is not None) and day["min_temp"] < 2:
            wc.frost_warning = True
            break

    # Irrigation block: moisture adequate/high OR heavy rain coming
    if sc.moisture_status in ("Adequate", "High") or wc.heavy_rain_48h:
        wc.irrigation_blocked = True

    return wc
```

### 7. `_fetch_gov_rag_snippets()` — Keyword Search

Searches the existing `comprehensive_crop_database`, ICAR IPM guidance, and scheme data for snippets relevant to the query intent and detected crops.

```python
def _fetch_gov_rag_snippets(
    self,
    query: str,
    intent: str,
    crops: List[Dict[str, Any]],
) -> str:
    """
    Returns a ≤500-char string of government-sourced advisory text
    relevant to the query. Falls back to a safe "consult KVK" message.
    """
    snippets = []

    # IPM / pest guidance from built-in ICAR data
    if intent == INTENT_PEST_DISEASE:
        snippets.append(
            "ICAR IPM Package of Practices: Prefer neem oil (5ml/L) as first-line "
            "treatment. For chemical control, use only label-approved doses: "
            "Imidacloprid 17.8SL @ 0.25ml/L for sucking pests; Mancozeb 75WP @ 2.5g/L "
            "for fungal diseases. Source: ICAR, PPQS India."
        )

    # Fertiliser guidance
    if intent == INTENT_FERTILIZER:
        snippets.append(
            "ICAR recommends soil testing before fertiliser application. "
            "General NPK dose: 120:60:40 kg/ha for wheat; 100:50:50 for rice. "
            "Use neem-coated urea (NCU) to reduce volatilisation loss by 10-15%. "
            "Source: ICAR, Fertiliser Association of India."
        )

    # Crop-specific guidance from crop catalog / comprehensive DB
    for crop in crops[:2]:
        try:
            from .comprehensive_crop_database import comprehensive_crop_database
            info = comprehensive_crop_database.get_crop_info(crop["id"])
            if info:
                pest_note = (info.get("pest_management") or "")[:200]
                fert_note = (info.get("fertiliser_schedule") or "")[:200]
                if pest_note and intent == INTENT_PEST_DISEASE:
                    snippets.append(f"{crop['name'].title()} — {pest_note}")
                if fert_note and intent == INTENT_FERTILIZER:
                    snippets.append(f"{crop['name'].title()} — {fert_note}")
        except Exception:
            pass

    if not snippets:
        return (
            "No specific advisory found for this query. "
            "Please consult your local KVK extension officer or call 1800-180-1551."
        )

    combined = " | ".join(snippets)
    return combined[:500]
```

### 8. `_build_market_price_str()` — Market Price Slot

Formats the `current_market_price` slot value from the market service response.

```python
def _build_market_price_str(
    self,
    prices: Dict[str, Any],
    crops: List[Dict[str, Any]],
) -> str:
    if not prices.get("is_live"):
        # Show MSP for mentioned crops only
        parts = []
        for crop in crops[:3]:
            msp = MSP_2024_25.get(crop["id"])
            if msp:
                parts.append(f"{crop['name'].title()}: ₹{msp}/q (MSP 2024-25)")
        base = "; ".join(parts) if parts else "N/A"
        return f"{base} — live mandi data unavailable, check agmarknet.gov.in"

    top = [c for c in (prices.get("top_crops") or []) if c.get("is_live")]
    if crops:
        crop_ids = {c["id"] for c in crops}
        matched = [
            c for c in top
            if crop_catalog.normalize(str(c.get("crop_name", ""))) and
               crop_catalog.normalize(str(c.get("crop_name", "")))["id"] in crop_ids
        ]
        top = matched + [c for c in top if c not in matched]

    lines = []
    for c in top[:4]:
        modal = c.get("modal_price")
        msp   = c.get("msp")
        mandi = c.get("mandi_name", "N/A")
        profit = f"+{c['profit_vs_msp']}% above MSP" if c.get("profit_vs_msp", 0) > 0 else "below MSP"
        lines.append(
            f"{c.get('crop_name')} ₹{modal}/q (MSP ₹{msp}) @ {mandi} — {profit}"
        )
    return "; ".join(lines) if lines else "No live price rows today"
```

### 9. Updated `answer()` Method Flow

The `answer()` method is updated to orchestrate all new helpers while preserving the existing API contract.

```python
def answer(
    self,
    query: str,
    ctx: LocationContext,
    language: str = "hi",
    history: Optional[List[Dict[str, Any]]] = None,
    sensor_context: Optional[Dict[str, Any]] = None,   # NEW parameter
) -> Dict[str, Any]:
    query = (query or "").strip()
    lang  = normalise_language_code(language)
    if language == "auto" and ctx.state:
        lang = get_language_for_state(ctx.state)

    if not query:
        return { "response": self._empty_response(lang), "intent": INTENT_GENERAL,
                 "sources": [], "crop_suggestions": [], "language": lang }

    intent, crops_mentioned = self.classify_query(query)
    # ... (existing history crop-carryover logic unchanged) ...

    # ── Concurrent data fetch ─────────────────────────────────────
    from concurrent.futures import ThreadPoolExecutor, as_completed

    weather_data = {}
    prices_data  = {}
    sc           = SensorContext()

    def _fetch_weather():
        return weather_service.get_weather(
            ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
        )
    def _fetch_prices():
        crop_filter = crops_mentioned[0]["name"] if crops_mentioned else None
        return market_service.get_prices(
            ctx.query_label, lat=ctx.latitude, lon=ctx.longitude,
            state=ctx.state or None, crop=crop_filter,
        )
    def _fetch_iot():
        return self._resolve_sensor_context(ctx, sensor_context)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_fetch_weather): "weather",
            pool.submit(_fetch_prices):  "prices",
            pool.submit(_fetch_iot):     "iot",
        }
        for fut in as_completed(futures, timeout=5):
            key = futures[fut]
            try:
                result = fut.result()
                if key == "weather": weather_data = result
                elif key == "prices": prices_data = result
                elif key == "iot":    sc = result
            except Exception as e:
                logger.warning("Concurrent fetch failed for %s: %s", key, e)

    # Merge air temp / humidity from weather into sensor context
    cur = weather_data.get("current") or {}
    if sc.air_temp_c is None:
        sc.air_temp_c = cur.get("temperature")
    if sc.humidity_pct is None:
        sc.humidity_pct = cur.get("humidity")

    # ── Derive constraints ────────────────────────────────────────
    wc  = self._derive_weather_constraints(weather_data, sc)
    rag = self._fetch_gov_rag_snippets(query, intent, crops_mentioned)
    market_str = self._build_market_price_str(prices_data, crops_mentioned)

    # ── Build legacy context_block for rule-based fallback ────────
    context_block, sources = self._build_official_context(
        ctx, query, intent, crops_mentioned, lang=lang,
        _weather=weather_data, _prices=prices_data,
    )

    # ── History block ─────────────────────────────────────────────
    history_block = ""
    if history:
        lines = []
        for msg in (history or [])[-8:]:
            role    = "Farmer" if msg.get("role") == "user" else "KrishiMitra"
            content = (msg.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")
        if lines:
            history_block = "\n".join(lines)

    season = _current_season(datetime.now().month)

    # ── Generate response ─────────────────────────────────────────
    has_gemini = bool(
        gemini_service.api_key
        and len(gemini_service.api_key) > 10
        and not gemini_service.api_key.upper().startswith("YOUR")
    )

    if has_gemini:
        rendered_prompt = self._render_grounded_prompt(
            query=query, ctx=ctx, sc=sc, wc=wc, rag=rag,
            market_price_str=market_str, history_block=history_block,
            lang=lang, season=season,
        )
        # For the grounded template the full prompt IS the system prompt;
        # pass empty string as user_prompt to avoid duplication
        response_text = gemini_service.generate(
            prompt=rendered_prompt,
            system_prompt="",          # all context is in rendered_prompt
            max_tokens=1600,
            user_query=query,
            temperature=0.3,
        )
        data_source = "Gemini AI + IoT + Official gov APIs"
    else:
        response_text = self._smart_rule_response(
            query, intent, crops_mentioned, ctx, context_block, lang, history,
            sc=sc, wc=wc,              # NEW: pass sensor/weather constraints
        )
        data_source = "KrishiMitra NLP Engine + IoT + Official gov APIs"

    crop_suggestions = self._crop_suggestions_for_intent(
        ctx, intent, crops_mentioned, lang=lang
    )

    return {
        "response":        response_text,
        "intent":          intent,
        "sources":         list(dict.fromkeys(sources)),
        "crops_detected":  [c["name"] for c in crops_mentioned],
        "crop_suggestions": crop_suggestions,
        "language":        lang,
        "data_source":     data_source,
        "timestamp":       datetime.now().isoformat(),
        # NEW: included for transparency; does not break existing consumers
        "sensor_context":  {
            "moisture_pct":   sc.soil_moisture_pct,
            "moisture_status": sc.moisture_status,
            "source":          sc.source,
        },
        "weather_constraints": {
            "irrigation_blocked": wc.irrigation_blocked,
            "spray_blocked":      wc.spray_blocked,
            "active_alerts":      wc.alerts_text,
        },
    }
```

### 10. Rule-Based Fallback — Sensor/Weather Checks

`_smart_rule_response()` signature gains `sc: SensorContext` and `wc: WeatherConstraints` keyword arguments. Evaluation checks are prepended to each relevant intent response:

```python
def _smart_rule_response(self, query, intent, crops, ctx, context_block, lang,
                          history=None, *, sc=None, wc=None) -> str:
    sc  = sc  or SensorContext()
    wc  = wc  or WeatherConstraints()

    # ── Evaluation Check 1: active weather alerts ─────────────────
    alert_prefix = ""
    if wc.alerts_text and wc.alerts_text != "None":
        alert_prefix = (
            f"⚠️ **कृषि चेतावनी (Weather Alert):** {wc.alerts_text}\n\n"
            if lang == "hi" else
            f"⚠️ **Farming Alert:** {wc.alerts_text}\n\n"
        )

    # ── Evaluation Check 2: irrigation conflict ────────────────────
    if intent == INTENT_IRRIGATION:
        if sc.moisture_status in ("Adequate", "High"):
            return (
                alert_prefix +
                (
                    f"💧 **सिंचाई की जरूरत नहीं।**\n\n"
                    f"आपके खेत की मिट्टी में नमी **{sc.soil_moisture_pct:.1f}%** है "
                    f"(स्तर: {sc.moisture_status}) — अभी सिंचाई न करें, इससे जलभराव होगा।\n\n"
                    f"अगली सिंचाई तब करें जब नमी 45% से नीचे आए।"
                    if lang == "hi" else
                    f"Soil moisture is **{sc.soil_moisture_pct:.1f}%** "
                    f"({sc.moisture_status}) — irrigation is NOT needed right now. "
                    f"Irrigate when moisture drops below 45%."
                )
            )
        elif sc.moisture_status == "Critical":
            return (
                alert_prefix +
                (
                    f"🚨 **तुरंत सिंचाई करें!**\n\n"
                    f"मिट्टी की नमी **{sc.soil_moisture_pct:.1f}%** है (Critical)। "
                    f"फसल पर सूखे का खतरा है। तुरंत 40-50mm सिंचाई करें।"
                    if lang == "hi" else
                    f"🚨 **Irrigate immediately!** Soil moisture is "
                    f"**{sc.soil_moisture_pct:.1f}%** (Critical). "
                    f"Apply 40-50mm water now to prevent crop stress."
                )
            )

    # ── Evaluation Check 3: spray/fertiliser conflict ──────────────
    if intent in (INTENT_FERTILIZER, INTENT_PEST_DISEASE) and wc.spray_blocked:
        spray_warning = (
            f"⚠️ **स्प्रे/खाद अभी न डालें** — अगले 48 घंटों में भारी बारिश की संभावना है। "
            f"बारिश के बाद करें।\n\n"
            if lang == "hi" else
            f"⚠️ **Postpone spray/fertiliser** — heavy rain forecast within 48 hours. "
            f"Apply after the rain.\n\n"
        )
        # Prepend to the existing intent response (does not block it entirely)
        return spray_warning + self._existing_intent_response(
            intent, crops, ctx, context_block, lang, sc, wc
        )

    # ... remaining intents call existing logic with alert_prefix prepended ...
```

### 11. `ChatbotViewSet` — `sensor_context` Extraction

```python
def _handle_query(self, request):
    query          = (request.data.get("query") or "").strip()
    language       = request.data.get("language", "hi")
    sensor_context = request.data.get("sensor_context") or None   # NEW
    ctx            = resolve_request_location(request)

    # ... existing validation unchanged ...

    history = [...]  # unchanged

    result = chat_intelligence_service.answer(
        query, ctx,
        language=language,
        history=history,
        sensor_context=sensor_context,   # NEW
    )
    # response shape unchanged
```

### 12. Frontend — `sensor_context` in Chat Payload

In `app.js`, the existing `sendChatMessage` function is extended to cache the last IoT sensor reading and attach it to each chat POST:

```javascript
// Module-level cache (set when IoT panel loads)
let cachedSensorContext = null;

// Called when IoT sensor data is loaded (already fetched via /api/iot/sensor_data/)
function cacheSensorContext(sensorData) {
    if (!sensorData || !sensorData.readings) return;
    const r = sensorData.readings;
    cachedSensorContext = {
        moisture_pct:     r.soil_moisture_pct,
        soil_temp_c:      r.soil_temperature_c,
        nitrogen_kg_ha:   r.npk?.nitrogen_kg_ha,
        phosphorus_kg_ha: r.npk?.phosphorus_kg_ha,
        potassium_kg_ha:  r.npk?.potassium_kg_ha,
        soil_ph:          r.soil_ph,
    };
}

// In handleChatUserMessage(), add to the POST body:
const data = await apiPostJson('/api/chatbot/query/', {
    query:          message,
    latitude:       currentLatitude,
    longitude:      currentLongitude,
    language:       getCurrentLang(),
    session_id:     sessionId,
    sensor_context: cachedSensorContext,   // NEW — null if IoT panel not loaded
});
```

## Data Flow Diagram

```
Request arrives at ChatbotViewSet
         │
         ▼
  Extract sensor_context (optional)
  Resolve LocationContext
         │
         ▼
  ChatIntelligenceService.answer()
         │
  ┌──────┴──────────────────────────────┐
  │     ThreadPoolExecutor (3 workers)  │
  │  ┌──────────┐ ┌────────┐ ┌───────┐ │
  │  │ weather  │ │ prices │ │  iot  │ │
  │  │ _service │ │_service│ │_bloc  │ │
  │  └────┬─────┘ └───┬────┘ └──┬────┘ │
  └───────┴───────────┴─────────┴──────┘
         │            │          │
      weather_data  prices_data  SensorContext
         │
  ┌──────┴──────────────────┐
  │ _derive_weather_constraints() │
  │ _fetch_gov_rag_snippets()     │
  │ _build_market_price_str()     │
  └──────────────────────────────┘
         │
  ┌──────┴──────────────┐
  │  has_gemini?        │
  │  YES → _render_     │
  │    grounded_prompt()│
  │    gemini.generate()│
  │                     │
  │  NO  → _smart_rule_ │
  │    response(sc, wc) │
  └─────────────────────┘
         │
  Return response dict
  (unchanged external shape)
```

## Files Changed

| File | Change Type | Summary |
|------|-------------|---------|
| `backend/advisory/services/chat_intelligence_service.py` | Extend | Add `SensorContext`, `WeatherConstraints`, `SYSTEM_PROMPT_TEMPLATE`, `_resolve_sensor_context()`, `_derive_weather_constraints()`, `_fetch_gov_rag_snippets()`, `_render_grounded_prompt()`, `_build_market_price_str()`. Update `answer()` and `_smart_rule_response()` signatures. |
| `backend/advisory/api/viewsets/chatbot.py` | Extend | Extract `sensor_context` from request payload and pass to `chat_intelligence_service.answer()`. |
| `frontend/public/js/app.js` | Extend | Add `cachedSensorContext`, `cacheSensorContext()`, include `sensor_context` in chat POST body. |

## No Changes To

- `unified_realtime_service.py` — `BlockchainIoTSimulator`, `WeatherService`, `MarketPricesService` used as-is
- `models.py` — `IoTSensorReading` read-only, no new migrations
- All other viewsets — zero impact
- API response contract — all existing fields preserved; two new optional fields added (`sensor_context`, `weather_constraints`)

## Components and Interfaces

### `SensorContext` (dataclass — `chat_intelligence_service.py`)

| Field | Type | Source |
|-------|------|--------|
| `soil_moisture_pct` | `Optional[float]` | IoT sensor |
| `soil_temp_c` | `Optional[float]` | IoT sensor |
| `air_temp_c` | `Optional[float]` | Weather service |
| `humidity_pct` | `Optional[float]` | Weather service |
| `nitrogen_kg_ha` | `Optional[float]` | IoT sensor |
| `phosphorus_kg_ha` | `Optional[float]` | IoT sensor |
| `potassium_kg_ha` | `Optional[float]` | IoT sensor |
| `soil_ph` | `Optional[float]` | IoT sensor |
| `hours_since_water` | `Optional[float]` | Derived from `IoTSensorReading.created_at` |
| `soil_health_score` | `Optional[int]` | Simulator `_calculate_soil_health()` |
| `soil_health_grade` | `str` | `"A"` / `"B"` / `"C"` |
| `moisture_status` | `str` | Derived: `"Critical"` / `"Low"` / `"Adequate"` / `"High"` |
| `source` | `str` | `"live"` / `"db"` / `"simulated"` / `"none"` |

Public methods: `moisture_label() → str`

### `WeatherConstraints` (dataclass — `chat_intelligence_service.py`)

| Field | Type | Derived from |
|-------|------|-------------|
| `alerts_text` | `str` | `weather["farming_alerts"]` |
| `forecast_3day` | `str` | First 3 entries of `forecast_7day` |
| `irrigation_blocked` | `bool` | `sc.moisture_status in ("Adequate","High")` OR `heavy_rain_48h` |
| `spray_blocked` | `bool` | `rainfall_mm > 20` OR `rain_probability > 70` in next 2 days |
| `frost_warning` | `bool` | `min_temp < 2` in next 3 days |
| `heavy_rain_48h` | `bool` | Used internally to set `irrigation_blocked` |

### `ChatIntelligenceService` — new/changed public interface

| Method | Signature change | Purpose |
|--------|-----------------|---------|
| `answer()` | `+ sensor_context: Optional[Dict]` | Main entry point — now accepts optional IoT payload |
| `_resolve_sensor_context()` | new | Three-tier IoT data resolution |
| `_derive_weather_constraints()` | new | Parses weather dict into gate flags |
| `_fetch_gov_rag_snippets()` | new | Keyword-based ICAR/gov text retrieval |
| `_render_grounded_prompt()` | new | Fills all `{variable}` slots in `SYSTEM_PROMPT_TEMPLATE` |
| `_build_market_price_str()` | new | Formats market price slot string |
| `_smart_rule_response()` | `+ sc, wc kwargs` | Applies sensor/weather gate checks |
| `_build_official_context()` | `+ _weather, _prices kwargs` | Accepts pre-fetched data to avoid duplicate calls |

### `ChatbotViewSet` (`viewsets/chatbot.py`) — interface change

```
POST /api/chatbot/query/
{
  "query": "string",
  "language": "hi|en|...",
  "latitude": float,
  "longitude": float,
  "history": [...],
  "sensor_context": {           ← NEW (optional)
    "moisture_pct": float,
    "soil_temp_c": float,
    "nitrogen_kg_ha": float,
    "phosphorus_kg_ha": float,
    "potassium_kg_ha": float,
    "soil_ph": float
  }
}
```

Response gains two optional fields (existing fields unchanged):
```json
{
  "sensor_context": { "moisture_pct": 58.3, "moisture_status": "Adequate", "source": "simulated" },
  "weather_constraints": { "irrigation_blocked": true, "spray_blocked": false, "active_alerts": "None" }
}
```

## Data Models

No new Django models or migrations. The feature reads from existing models only:

| Model | Access | Fields used |
|-------|--------|-------------|
| `IoTSensorReading` | Read-only SELECT | `moisture_pct`, `soil_temp_c`, `nitrogen_kg_ha`, `phosphorus_kg_ha`, `potassium_kg_ha`, `ph`, `created_at`, `latitude`, `longitude` |
| `ChatSession` | Read (future) | `conversation_context` — reserved for session-persisted sensor state (Req 7.3) |

`BlockchainIoTSimulator.get_iot_sensor_data()` (no DB — in-memory simulation) is called as the Tier-3 fallback and returns:
```python
{
  "readings": {
    "soil_moisture_pct": float,
    "soil_temperature_c": float,
    "soil_ph": float,
    "npk": { "nitrogen_kg_ha": float, "phosphorus_kg_ha": float, "potassium_kg_ha": float },
    "conductivity_ms_cm": float,
  },
  "soil_health_score": { "score": int, "grade": str, "status": str },
  "recommendations": [str, ...],
  "blockchain": { "transaction_hash": str, ... }
}
```

## Correctness Properties

These are the invariants that must hold for every chat response:

### Property 1: No irrigation recommended when soil moisture is adequate or high
**Validates: Requirements 2.2, 6.2**
When `sc.moisture_status` is `"Adequate"` or `"High"` and the detected intent is `INTENT_IRRIGATION`, the generated response must not contain the words `"irrigate"`, `"सिंचाई करें"`, or `"पानी दें"` without an immediately adjacent negation word (`"not"`, `"नहीं"`, `"no need"`).

### Property 2: Active weather alerts must be acknowledged
**Validates: Requirements 3.1, 6.1**
When `wc.alerts_text` is not `"None"`, the first 120 characters of the response must contain at least one of: the alert text substring, `"alert"`, `"चेतावनी"`, or `"warning"`.

### Property 3: No spray or fertiliser application advised before forecasted rain
**Validates: Requirements 3.2, 6.2**
When `wc.spray_blocked` is `True` and intent is `INTENT_FERTILIZER` or `INTENT_PEST_DISEASE`, the response must contain at least one of: `"postpone"`, `"after rain"`, `"बारिश के बाद"`, or `"delay"`.

### Property 4: No raw placeholder strings in rendered prompt
**Validates: Requirements 1.2, 1.3**
After `_render_grounded_prompt()` executes, the returned string must not contain the substring `"{{"` or `"}}"`.

### Property 5: No live price label when data is not live
**Validates: Requirements 5.3**
When `prices_data.get("is_live")` is `False` or `prices_data` is empty, `_build_market_price_str()` must return a string containing `"unavailable"` and must NOT contain the word `"modal"`. 

## Error Handling

| Failure | Behaviour |
|---------|-----------|
| `WeatherService` timeout | `weather_data = {}` → `WeatherConstraints` defaults → `alerts_text = "None"`, no irrigation/spray block; prompt shows `"Unavailable — check mausam.imd.gov.in"` |
| `MarketPricesService` exception | `prices_data = {}` → `_build_market_price_str()` returns MSP fallback strings |
| `BlockchainIoTSimulator` exception | `SensorContext()` with all fields `None`, `source = "none"` → prompt shows `"N/A — sensor offline"` for all IoT slots |
| `IoTSensorReading` DB unavailable | Exception caught silently, falls through to Tier-3 simulator |
| `gemini_service.generate()` returns empty | `_smart_rule_response()` called as fallback — never raises to caller |
| `_render_grounded_prompt()` raises `KeyError` | Caught, logs warning, returns the legacy `user_prompt` string as fallback |
| Any unhandled exception in `answer()` | `ChatbotViewSet` wraps in `try/except` and returns `HTTP 500` with `safe_error_message()` |

All IoT, weather, and market fetches run inside `ThreadPoolExecutor` with a 5-second `timeout`. Individual future failures are caught per-future and do not abort the others.

## Testing Strategy

### Unit Tests

- `test_classify_moisture()` — verify all four status thresholds
- `test_resolve_sensor_context_tier1()` — payload data takes priority over DB
- `test_resolve_sensor_context_tier2()` — DB reading used when no payload
- `test_resolve_sensor_context_tier3()` — simulator used when no payload and no DB row
- `test_derive_weather_constraints_spray_block()` — rain_probability > 70 sets `spray_blocked`
- `test_derive_weather_constraints_frost()` — min_temp < 2 sets `frost_warning`
- `test_render_grounded_prompt_no_placeholders()` — assert `"{{" not in rendered`
- `test_build_market_price_str_no_live()` — assert `"unavailable"` in string, no `"modal"`

### Property-Based Tests (Correctness Properties)

- For any `SensorContext` with `moisture_status in ("Adequate", "High")`, calling `_smart_rule_response()` with `intent=INTENT_IRRIGATION` must never return a string containing the token `"irrigate"` (case-insensitive) without a negation word within 10 characters.
- For any `WeatherConstraints` with `alerts_text != "None"`, the first 100 characters of the rule-based response must contain the alert text.

### Integration Test

- `POST /api/chatbot/query/` with `sensor_context={"moisture_pct": 72}` and `query="pani kab dun"` → response body must contain `"adequate"` or `"नहीं"` and must NOT contain `"irrigate now"` or `"तुरंत सिंचाई"`.
