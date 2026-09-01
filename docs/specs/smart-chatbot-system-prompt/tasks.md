# Implementation Plan: Smart Agricultural Chatbot System Prompt with Live Data Grounding

## Overview

Ten sequential tasks that upgrade `ChatIntelligenceService` to use a structured, variable-rendered system prompt grounded in live IoT sensor telemetry, weather constraints, government RAG snippets, and real-time mandi prices. Tasks 1–8 are backend-only (Python). Task 9 updates the DRF viewset. Task 10 updates the frontend JavaScript. No new migrations are needed.

## Tasks

- [ ] 1. Add `SensorContext` and `WeatherConstraints` dataclasses to `chat_intelligence_service.py`
  - Add `SensorContext` dataclass (moisture, NPK, temp, humidity, soil health, source, moisture_status) with a `moisture_label()` method that returns a human-readable string with emoji status indicator
  - Add `WeatherConstraints` dataclass (alerts_text, forecast_3day, irrigation_blocked, spray_blocked, frost_warning, heavy_rain_48h)
  - Add static `_classify_moisture(pct) → str` helper returning `"Critical"` / `"Low"` / `"Adequate"` / `"High"`
  - Add `import dataclass, field` from dataclasses and `timedelta` from datetime at the top of the file
  - Add `iot_blockchain` import from `.unified_realtime_service` (not currently imported in this file)
  - _Requirements: 1.1, 2.1, 2.2, 3.1_

- [ ] 2. Implement `_resolve_sensor_context()` three-tier IoT data resolution method
  - Add `_resolve_sensor_context(self, ctx, payload_sensors) → SensorContext` on `ChatIntelligenceService`
  - Tier 1: if `payload_sensors` dict contains `moisture_pct` or `soil_moisture_pct`, build `SensorContext(source="live")` and return
  - Tier 2: query `IoTSensorReading` for GPS grid ±0.01° within last 24 hours ordered by `-created_at`; if found, compute `hours_since_water` from `created_at`, build `SensorContext(source="db")` and return
  - Tier 3: call `iot_blockchain.get_iot_sensor_data(ctx.query_label)`, map `readings` dict and `soil_health_score` to `SensorContext(source="simulated")`
  - All tiers: call `_classify_moisture()` to set `sc.moisture_status` before returning
  - Wrap each tier in `try/except`; on exception fall through to next tier; if all fail return default `SensorContext(source="none")`
  - Add `_parse_sensor_dict(raw, source) → SensorContext` helper that maps flat dict keys to `SensorContext` fields
  - _Requirements: 2.1, 2.6, 7.2, 7.3_

- [ ] 3. Implement `_derive_weather_constraints()` alert and gate logic method
  - Add `_derive_weather_constraints(self, weather, sc) → WeatherConstraints` on `ChatIntelligenceService`
  - Parse `weather["farming_alerts"]` → `wc.alerts_text`; join up to 3 entries with ` | `; default to string `"None"` when list is empty
  - Parse first 3 days of `forecast_7day` / `forecast_7_days` into `wc.forecast_3day` summary string (date, max temp, rainfall mm, probability)
  - Set `wc.spray_blocked = True` if any of first 2 forecast days has `rainfall_mm > 20` or `rain_probability > 70`
  - Set `wc.frost_warning = True` if any of first 3 forecast days has `min_temp < 2`
  - Set `wc.irrigation_blocked = True` if `sc.moisture_status in ("Adequate", "High")` OR `wc.heavy_rain_48h` is True
  - Default `wc.forecast_3day` to `"Forecast unavailable — check mausam.imd.gov.in"` when forecast list is empty
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.1_

- [ ] 4. Implement `_fetch_gov_rag_snippets()` government advisory keyword retrieval
  - Add `_fetch_gov_rag_snippets(self, query, intent, crops) → str` on `ChatIntelligenceService`
  - For `INTENT_PEST_DISEASE` intent: prepend ICAR IPM snippet (neem oil 5ml/L, Imidacloprid 17.8SL dose, Mancozeb 75WP dose, source attribution)
  - For `INTENT_FERTILIZER` intent: prepend ICAR fertiliser snippet (NCU, split-dose guidance, soil test recommendation)
  - For each of up to 2 detected crops: try `comprehensive_crop_database.get_crop_info(crop["id"])` and append `pest_management` or `fertiliser_schedule` field (max 200 chars), matched to intent
  - Join snippets with ` | ` separator and cap combined string at 500 characters
  - Return safe fallback `"No specific advisory found. Please consult your local KVK extension officer or call 1800-180-1551."` when no snippets found
  - Wrap the `comprehensive_crop_database` import in `try/except`; skip silently if module absent
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 5. Implement `_build_market_price_str()` market price slot formatter
  - Add `_build_market_price_str(self, prices, crops) → str` on `ChatIntelligenceService`
  - When `prices.get("is_live")` is falsy: build MSP values for mentioned crops from `MSP_2024_25` dict and append `"— live mandi data unavailable, check agmarknet.gov.in"`
  - When live: filter `top_crops` by `is_live=True`, sort matched crops (from detected entities) first, format up to 4 rows as `"{crop} ₹{modal}/q (MSP ₹{msp}) @ {mandi} — {profit indicator}"`
  - Never return an empty string; always include at least MSP fallback or `"N/A — market data unavailable"`
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Add `SYSTEM_PROMPT_TEMPLATE` constant and implement `_render_grounded_prompt()`
  - Replace existing `SYSTEM_PROMPT` class constant with new `SYSTEM_PROMPT_TEMPLATE` using `{variable}` Python format slots (single braces); keep old value as `_SYSTEM_PROMPT_LEGACY` for fallback
  - Template must include: `### OPERATIONAL FRAMEWORK` (PERCEIVE/GROUND/DECIDE sections), `### CRITICAL RULES` (DATA TRUTHFULNESS, SAFETY FIRST, TONALITY, LANGUAGE), `[LIVE IOT SENSOR DATA]` with all 10 sensor slots, `[OFFICIAL GOVERNMENT & WEATHER DATA]` with forecast/alerts/flags/RAG/price/season/location, `[FARMER'S CONVERSATION HISTORY]`, `[FARMER'S CURRENT QUERY]`, and `### KIRO'S RESPONSE EVALUATION STEPS` with 3 numbered checks
  - Add `_render_grounded_prompt(self, query, ctx, sc, wc, rag, market_price_str, history_block, lang, season) → str`
  - Inside `_render_grounded_prompt`: call `get_gemini_language_instruction(lang)` for `{lang_instruction}` slot; add inner `_fmt()`, `_npk_status()`, `_ph_status()` helpers for safe value formatting
  - Wrap the `SYSTEM_PROMPT_TEMPLATE.format(...)` call in `try/except KeyError`; on error log a warning and return the legacy `context_block`-based prompt string as fallback
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 8.1, 8.2_

- [ ] 7. Update `answer()` for concurrent fetch and grounded prompt routing
  - Add `sensor_context: Optional[Dict[str, Any]] = None` parameter to `answer()` signature
  - Replace sequential weather and market fetches with a `ThreadPoolExecutor(max_workers=3)` block running `_fetch_weather`, `_fetch_prices`, and `_fetch_iot` concurrently with a 5-second timeout; catch per-future exceptions without aborting sibling fetches
  - After futures resolve: merge weather `temperature` → `sc.air_temp_c` and `humidity` → `sc.humidity_pct` if not already set in `sc`
  - Call `_derive_weather_constraints(weather_data, sc)`, `_fetch_gov_rag_snippets(query, intent, crops_mentioned)`, `_build_market_price_str(prices_data, crops_mentioned)` in sequence
  - Refactor `_build_official_context()` to accept optional `_weather` and `_prices` keyword arguments and skip their internal fetches when pre-fetched dicts are provided; pass them from `answer()`
  - When Gemini is available: call `_render_grounded_prompt()` and pass `prompt=rendered_prompt, system_prompt=""` to `gemini_service.generate()`
  - When rule-based: call `_smart_rule_response(..., sc=sc, wc=wc)`
  - Add `"sensor_context"` dict and `"weather_constraints"` dict to the returned result (existing keys unchanged)
  - _Requirements: 1.1, 2.1, 7.2, Non-Functional latency_

- [ ] 8. Update `_smart_rule_response()` with sensor and weather evaluation checks
  - Update signature to `_smart_rule_response(self, query, intent, crops, ctx, context_block, lang, history=None, *, sc=None, wc=None) → str`
  - At the top of the method body, before any intent dispatching: if `wc.alerts_text != "None"` build `alert_prefix` string with Hindi and English variants
  - For `INTENT_IRRIGATION` intent: if `sc.moisture_status in ("Adequate", "High")` return early with a "no irrigation needed" message citing the actual moisture percentage and status (Hindi and English variants); if `sc.moisture_status == "Critical"` return early with "irrigate immediately" message
  - For `INTENT_FERTILIZER` and `INTENT_PEST_DISEASE` intents: if `wc.spray_blocked` prepend a "postpone spray — rain forecast within 48h" warning before the normal advisory response (do not suppress the full advisory)
  - Prepend `alert_prefix` to all other intent responses when alerts are active
  - Default `sc` and `wc` to empty dataclass instances when `None` (safe for callers that do not pass them)
  - _Requirements: 2.2, 2.3, 3.1, 3.2, 6.2, 6.3_

- [ ] 9. Update `ChatbotViewSet._handle_query()` to extract and pass `sensor_context`
  - In `backend/advisory/api/viewsets/chatbot.py`, inside `_handle_query()`: extract `sensor_context = request.data.get("sensor_context") or None`
  - Validate: if `sensor_context` is not a `dict`, set it to `None`
  - Pass `sensor_context=sensor_context` as keyword argument to `chat_intelligence_service.answer(...)`
  - In the response dict, add `"sensor_context": result.get("sensor_context")` and `"weather_constraints": result.get("weather_constraints")` (nullable; does not break existing consumers)
  - _Requirements: 7.1, 7.2_

- [ ] 10. Update frontend to cache IoT data and include it in chat POST payload
  - In `frontend/public/js/app.js`, add module-level `let cachedSensorContext = null;`
  - Add `cacheSensorContext(sensorData)` function that maps `sensorData.readings` fields (`soil_moisture_pct`, `soil_temperature_c`, `npk.nitrogen_kg_ha`, `npk.phosphorus_kg_ha`, `npk.potassium_kg_ha`, `soil_ph`) into a flat `cachedSensorContext` object
  - Find the existing IoT sensor data fetch (call to `/api/iot/sensor_data/` or IoT panel refresh) and call `cacheSensorContext(data)` after a successful response
  - In `handleChatUserMessage()`, add `sensor_context: cachedSensorContext` to the `apiPostJson('/api/chatbot/query/', {...})` call body; value will be `null` if IoT panel has not been loaded yet
  - _Requirements: 7.1_

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": [1]
    },
    {
      "wave": 2,
      "tasks": [2, 3, 4, 5, 6]
    },
    {
      "wave": 3,
      "tasks": [7]
    },
    {
      "wave": 4,
      "tasks": [8, 9]
    },
    {
      "wave": 5,
      "tasks": [10]
    }
  ]
}
```

Tasks 2, 3, 4, 5, 6 are independently implementable after Task 1. Task 7 integrates all of them. Tasks 8 and 9 depend on Task 7. Task 10 depends on Task 9.

## Notes

- All new code must be wrapped in `try/except` following the existing pattern in `_build_official_context()`. The chatbot must never raise an unhandled exception to the API layer.
- `SYSTEM_PROMPT_TEMPLATE` uses single-brace `{variable}` Python format syntax. The old `SYSTEM_PROMPT` used no variables. Do NOT use `{{ }}` Jinja/Django template syntax — the template is rendered with `.format()`.
- Simulated sensor data from `BlockchainIoTSimulator` must be labelled `source="simulated"` in the prompt so Gemini can see that the readings are not from real hardware.
- Tasks 1–9 change only Python files. No Django migrations are needed (reads from `IoTSensorReading` only, no schema changes).
- Task 10 is a frontend-only change; it is safe to ship independently and the backend gracefully handles `null` for `sensor_context`.
