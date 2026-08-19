# Requirements Document

> Canonical beta policy: `.kiro/specs/farmer-ready-beta/requirements.md`
> supersedes this document where sensor aliases, simulated data, validation,
> freshness, or moisture thresholds conflict. This document remains historical
> design context for all non-conflicting requirements.

## Introduction

This feature upgrades KrishiMitra's `ChatIntelligenceService` from its current general-purpose advisory chatbot to a structured, IoT-grounded advisory system. The upgrade replaces the existing `SYSTEM_PROMPT` with a multi-section prompt template that injects live IoT sensor telemetry (soil moisture, temperature, humidity, NPK levels, last irrigation time), real-time weather alerts, and government crop advisory RAG snippets directly into the AI context before each response is generated.

The system enforces data-truthfulness rules — for example, it must never recommend irrigation when soil moisture sensors report adequate levels (≥ 60 %), and it must always acknowledge active severe weather alerts. The `ChatbotViewSet` is extended to accept an optional `sensors` payload so frontend clients and IoT gateways can pass live field readings alongside a farmer's query.

## Glossary

- **Advisory_System**: The upgraded `ChatIntelligenceService` responsible for constructing the grounded system prompt and generating responses.
- **IoT_Context_Builder**: The component inside `ChatIntelligenceService` that resolves IoT sensor data from the request payload or the `BlockchainIoTSimulator` fallback and formats it for prompt injection.
- **Grounded_Prompt**: The structured system prompt combining the operational framework, live IoT sensor section, official government/weather section, and the farmer's query section.
- **Sensor_Payload**: The optional `sensors` JSON object accepted by `ChatbotViewSet`, containing fields such as `soil_moisture_pct`, `air_temp_c`, `humidity_pct`, `nitrogen_kg_ha`, `phosphorus_kg_ha`, `potassium_kg_ha`, and `hours_since_last_water`.
- **Moisture_Status**: A categorical label (`critical`, `low`, `adequate`, `high`, `waterlogged`) derived from the `soil_moisture_pct` value.
- **Moisture_Guard**: The data-truthfulness enforcement rule that suppresses irrigation recommendations when `soil_moisture_pct` ≥ 60.
- **Alert_Acknowledger**: The enforcement rule that requires the advisory response to reference any non-empty `active_weather_warnings` before offering crop advice.
- **GovData_Block**: The formatted section of the Grounded_Prompt containing weather forecast, active weather warnings, government RAG snippets, and market prices.
- **IoTData_Block**: The formatted section of the Grounded_Prompt containing sensor telemetry values and computed `Moisture_Status`.
- **Chatbot_API**: The `ChatbotViewSet` REST endpoint at `POST /api/chatbot/`.
- **BlockchainIoTSimulator**: The existing simulator (`iot_blockchain`) used to generate synthetic IoT readings when no `Sensor_Payload` is provided.
- **WeatherService**: The existing `weather_service` singleton that provides live weather data including `active_weather_warnings`.
- **GovernmentSchemesService**: The existing `schemes_service` singleton providing RAG snippets from government crop manuals.
- **MarketPricesService**: The existing `market_service` singleton providing mandi/wholesale price data.
- **GeminiService**: The existing `gemini_service` singleton used to generate AI responses from the Grounded_Prompt.

---

## Requirements

### Requirement 1: Grounded System Prompt Construction

**User Story:** As a farmer using KrishiMitra, I want the AI advisor to reason from my actual field sensor readings and live weather data, so that every piece of advice I receive is specific to the real conditions on my farm right now.

#### Acceptance Criteria

1. THE Advisory_System SHALL replace the existing `SYSTEM_PROMPT` constant with a Grounded_Prompt template that contains three named sections in this fixed order: `[LIVE IOT SENSOR DATA]`, `[OFFICIAL GOVERNMENT & WEATHER DATA]`, and `[FARMER'S QUERY]`.
2. WHEN the Grounded_Prompt is assembled, THE Advisory_System SHALL populate all template placeholders in the `[LIVE IOT SENSOR DATA]` section — `soil_moisture_percentage`, `moisture_status`, `air_temp_c`, `humidity_percentage`, `nitrogen_lvl`, `phosphorus_lvl`, `potassium_lvl`, `hours_since_last_water` — with values from the resolved sensor data before passing the prompt to GeminiService.
3. WHEN the Grounded_Prompt is assembled, THE Advisory_System SHALL populate all template placeholders in the `[OFFICIAL GOVERNMENT & WEATHER DATA]` section — `weather_forecast_summary`, `active_weather_warnings`, `government_crop_manual_search_results`, `current_market_price` — with values from WeatherService, GovernmentSchemesService, and MarketPricesService before passing the prompt to GeminiService.
4. THE Advisory_System SHALL include the `OPERATIONAL FRAMEWORK` preamble (PERCEIVE → GROUND → DECIDE & ACT) and the `CRITICAL RULES` block in every assembled Grounded_Prompt.
5. IF any individual data source (WeatherService, GovernmentSchemesService, MarketPricesService) fails to return data, THEN THE Advisory_System SHALL substitute a clearly labelled "Data unavailable" string for that placeholder so the Grounded_Prompt remains structurally complete.

---

### Requirement 2: IoT Sensor Data Resolution

**User Story:** As a developer integrating IoT hardware with KrishiMitra, I want the chatbot to use real sensor readings when I send them in the API request, and fall back to simulated readings when I do not, so that both real deployments and demos work correctly.

#### Acceptance Criteria

1. WHEN a `POST /api/chatbot/` request includes a `sensors` object with at least one valid numeric field, THE IoT_Context_Builder SHALL use those values as the authoritative sensor data for the Grounded_Prompt and SHALL NOT call `BlockchainIoTSimulator.get_iot_sensor_data`.
2. WHEN a `POST /api/chatbot/` request does not include a `sensors` object or the `sensors` object is empty, THE IoT_Context_Builder SHALL call `BlockchainIoTSimulator.get_iot_sensor_data(location)` to obtain simulated sensor data.
3. THE IoT_Context_Builder SHALL accept `sensors` fields in both snake_case variants (`soil_moisture_pct`, `nitrogen_kg_ha`, `phosphorus_kg_ha`, `potassium_kg_ha`) and the prompt template names (`soil_moisture_percentage`, `nitrogen_lvl`, `phosphorus_lvl`, `potassium_lvl`) and SHALL normalise them to a single internal representation.
4. IF a required sensor field is absent from both the request payload and the simulator result, THEN THE IoT_Context_Builder SHALL substitute the string `"N/A"` for that field in the IoTData_Block.
5. THE IoT_Context_Builder SHALL compute `Moisture_Status` from `soil_moisture_pct` according to this mapping: below 30 → `critical`, 30–44 → `low`, 45–59 → `adequate`, 60–79 → `high`, 80 and above → `waterlogged`.

---

### Requirement 3: Chatbot API Extension for Sensor Payload

**User Story:** As a frontend developer or IoT gateway operator, I want to include field sensor readings in a chatbot API call, so that the AI response is grounded in actual measured data from the farmer's field.

#### Acceptance Criteria

1. THE Chatbot_API SHALL accept an optional `sensors` JSON object in the `POST /api/chatbot/` request body alongside the existing `query`, `language`, `latitude`, `longitude`, and `history` fields.
2. WHEN the `sensors` object is present and contains non-null numeric values, THE Chatbot_API SHALL pass the parsed sensor data to `chat_intelligence_service.answer()` without modification.
3. IF the `sensors` object contains non-numeric values for numeric sensor fields, THEN THE Chatbot_API SHALL silently discard those invalid fields and process the remaining valid fields.
4. THE Chatbot_API SHALL return the same response structure as the current implementation, with an additional `iot_sensors_used` boolean field indicating whether sensor data was applied to the response.
5. THE Chatbot_API SHALL NOT require the `sensors` field — requests without it SHALL continue to function as before, returning `"iot_sensors_used": false` in the response.

---

### Requirement 4: Data-Truthfulness Enforcement — Moisture Guard

**User Story:** As a farmer, I want the AI advisor to never tell me to irrigate when my soil is already moist, so that I do not waste water or damage my crops through overwatering.

#### Acceptance Criteria

1. WHEN `soil_moisture_pct` is greater than or equal to 60, THE Advisory_System SHALL include an explicit instruction in the Grounded_Prompt's `CRITICAL RULES` block stating that irrigation must not be recommended for the current query.
2. WHEN `soil_moisture_pct` is greater than or equal to 60 and the farmer's query contains irrigation-related intent keywords (in any supported language), THE Advisory_System SHALL ensure the Grounded_Prompt contains the moisture reading and its `Moisture_Status` in the `[LIVE IOT SENSOR DATA]` section so the AI can use that data when formulating its response.
3. WHEN `soil_moisture_pct` is below 30 (critical), THE Advisory_System SHALL include an urgent irrigation flag in the IoTData_Block so the AI is explicitly informed of the critical condition.
4. FOR ALL values of `soil_moisture_pct`, THE Advisory_System SHALL include the computed `Moisture_Status` label alongside the numeric value in the IoTData_Block.

---

### Requirement 5: Data-Truthfulness Enforcement — Weather Alert Acknowledgement

**User Story:** As a farmer, I want the AI advisor to always acknowledge active severe weather alerts before giving crop advice, so that I am not directed to take field actions that are dangerous given current weather conditions.

#### Acceptance Criteria

1. WHEN WeatherService returns one or more active weather warnings, THE Advisory_System SHALL include those warnings verbatim in the `active_weather_warnings` placeholder of the GovData_Block.
2. WHEN WeatherService returns one or more active weather warnings, THE Advisory_System SHALL add an explicit instruction in the Grounded_Prompt's `CRITICAL RULES` block requiring the AI to acknowledge the active alerts before offering any crop action plan.
3. WHEN WeatherService returns no active weather warnings, THE Advisory_System SHALL set the `active_weather_warnings` placeholder to the string `"None"`.
4. THE Advisory_System SHALL NOT modify, summarise, or truncate the weather warning text when injecting it into the GovData_Block.

---

### Requirement 6: Chemical Treatment Safety Rule

**User Story:** As a farmer, I want the AI to only recommend specific pesticides or chemical treatments that are backed by verified government data, so that I do not apply unapproved or unsafe chemicals on my crops.

#### Acceptance Criteria

1. THE Grounded_Prompt SHALL contain a `SAFETY FIRST` rule stating that chemical treatment recommendations must rely exclusively on data present in the `government_crop_manual_search_results` placeholder.
2. WHEN the `government_crop_manual_search_results` placeholder is populated with empty or "Data unavailable" content and the farmer's query relates to pest or disease treatment, THE Advisory_System SHALL include a fallback instruction in the Grounded_Prompt directing the AI to advise the farmer to consult a local extension officer.
3. THE Advisory_System SHALL populate `government_crop_manual_search_results` using GovernmentSchemesService for the farmer's detected location and any crops mentioned in the query.

---

### Requirement 7: Prompt Round-Trip Integrity

**User Story:** As a developer maintaining KrishiMitra, I want to verify that the prompt assembly process is deterministic and complete, so that I can trust every AI response is based on a fully populated context and not on missing or placeholder data.

#### Acceptance Criteria

1. THE Advisory_System SHALL expose a `build_grounded_prompt(sensor_data, gov_data, farmer_query)` method that accepts structured data dictionaries and returns a fully assembled Grounded_Prompt string.
2. FOR ALL valid combinations of `sensor_data`, `gov_data`, and `farmer_query` inputs, the string returned by `build_grounded_prompt` SHALL contain all eight sensor placeholders and all four government/weather placeholders populated with non-empty values (substituted with `"N/A"` or `"None"` only when the source data is genuinely absent).
3. FOR ALL valid inputs, calling `build_grounded_prompt` twice with the same arguments SHALL return identical strings (deterministic assembly, no timestamp or random values embedded in the prompt template itself).
4. THE Advisory_System SHALL NOT embed any value that changes between calls (such as the current timestamp, session identifiers, or random seeds) directly inside the Grounded_Prompt template — such dynamic values SHALL be passed in the `user_prompt` layer instead.
