# Requirements Document

> Canonical beta policy: `.kiro/specs/farmer-ready-beta/requirements.md`
> supersedes this document where intent-aware fetching, verified sensor use,
> mandi fallback, or learning policy conflict. Non-conflicting grounding and
> safety requirements remain active.

## Introduction

Upgrade the KrishiMitra AI chatbot to use a structured, data-grounded system prompt that synthesises live IoT sensor telemetry, regional weather forecasts, official government/RAG advisory snippets, and real-time mandi prices into every farmer query response. The chatbot should operate as a truly data-aware agronomist — never ignoring a weather alert, never recommending irrigation when sensors show adequate moisture, and never citing a chemical treatment without official backing.

## Glossary

- **IoT Sensor Data** — Soil moisture, temperature, NPK readings from `BlockchainIoTSimulator` (simulated) or `IoTSensorReading` DB model (real hardware)
- **RAG Snippet** — Relevant text retrieved from ICAR/government crop manuals to ground AI responses
- **Grounded Prompt** — A prompt where `{{ variable }}` placeholders are replaced with actual live data before being sent to Gemini
- **Moisture Status** — A derived label: `Critical (<35%)`, `Low (35-50%)`, `Adequate (50-65%)`, `High (>65%)`
- **Weather Alert** — An active `farming_alerts` entry from `WeatherService.get_weather()` indicating severe conditions (storm, frost, heavy rain)
- **Rule-based Fallback** — The `_smart_rule_response()` path used when no Gemini API key is configured
- **context_block** — The existing plain-text data section assembled by `_build_official_context()` and injected into the Gemini user prompt

## Requirements

### Requirement 1: Structured System Prompt with Live Data Slots

**User Story:** As a farmer, I want the AI to speak with full awareness of my field's live sensor readings, the local weather forecast, and the current mandi price — so that advice is actually relevant to my situation right now, not generic.

#### Acceptance Criteria

1. GIVEN a farmer sends a chat query, WHEN the backend assembles the Gemini prompt, THEN the system prompt MUST include clearly labelled sections for `[LIVE IOT SENSOR DATA]` (soil moisture %, moisture status, ambient temperature, humidity, NPK levels, hours since last irrigation), `[OFFICIAL GOVERNMENT & WEATHER DATA]` (3-day forecast summary, active severe weather alerts, government/RAG advisory snippets, current market price), and `[FARMER'S QUERY]` (the farmer's actual question).

2. GIVEN all data is available, WHEN the prompt is rendered, THEN every `{{ variable }}` placeholder in the template MUST be replaced with a real value — no raw placeholder strings should reach Gemini.

3. GIVEN a variable cannot be fetched (API timeout, sensor offline), WHEN the prompt is built, THEN a safe, clearly labelled fallback value MUST be used (e.g. `"N/A — sensor offline"`, `"Unavailable — check mausam.imd.gov.in"`).

4. GIVEN the system prompt includes an OPERATIONAL FRAMEWORK and CRITICAL RULES section, WHEN Gemini generates a response, THEN the rules (`DATA TRUTHFULNESS`, `SAFETY FIRST`, `TONALITY`) MUST be enforced by the prompt structure — not by post-processing.

### Requirement 2: IoT Sensor Data Integration into Chat Pipeline

**User Story:** As a farmer with IoT soil sensors, I want the chatbot to read my sensor data before giving irrigation or fertiliser advice — so I don't waste water or nutrients.

#### Acceptance Criteria

1. GIVEN a farmer's GPS coordinates are known, WHEN the chat service builds context, THEN it MUST call `BlockchainIoTSimulator.get_iot_sensor_data(location)` (or query the real `IoTSensorReading` model if live data exists) and include the result in the prompt's IoT section.

2. GIVEN the sensor shows `soil_moisture_pct >= 60`, WHEN the AI is asked about irrigation, THEN the response MUST NOT recommend watering and MUST explicitly state that soil moisture is adequate.

3. GIVEN the sensor shows `soil_moisture_pct < 35`, WHEN the AI is asked about irrigation or crop health, THEN the response MUST flag a low-moisture alert and recommend immediate irrigation.

4. GIVEN NPK values are available from the sensor, WHEN the AI gives fertiliser advice, THEN it MUST reference the actual N, P, K readings rather than generic ICAR defaults.

5. GIVEN the sensor data includes a `soil_health_score`, WHEN generating a general advisory, THEN the score and grade (A/B/C) MUST be mentioned in the response.

6. GIVEN `hours_since_last_water` is derivable from the most recent `IoTSensorReading.created_at` timestamp, WHEN the context is built, THEN this value MUST be calculated and injected into the prompt.

### Requirement 3: Weather Alert Override Logic

**User Story:** As a farmer, I want the AI to warn me about any pending severe weather before I take a costly field action — so I don't spray pesticides before heavy rain washes them off.

#### Acceptance Criteria

1. GIVEN an active severe weather alert exists in the weather service response (`farming_alerts` list is non-empty), WHEN the chatbot responds to any query, THEN the alert MUST be prominently mentioned at the top of the response, before any advisory content.

2. GIVEN heavy rain is forecast within the next 48 hours (`rain_probability > 70` or `rainfall_mm > 20` in the 2-day forecast), WHEN the farmer asks about spraying pesticides or applying fertilisers, THEN the response MUST advise postponing the operation.

3. GIVEN a frost warning is active (`min_temp < 2` in the next 3 days), WHEN the farmer asks about irrigation or crop operations, THEN the response MUST warn about frost risk and recommend protective measures.

4. GIVEN the 3-day forecast shows no significant weather threats, WHEN building the context block, THEN `active_weather_warnings` MUST be set to the string `"None"` (not an empty string or null).

### Requirement 4: Government Advisory RAG Snippets in Prompt

**User Story:** As a farmer, I want the AI's chemical or crop treatment recommendations to come from official government sources, not invented — so I can trust what it tells me.

#### Acceptance Criteria

1. GIVEN a farmer asks about a specific crop, pest, or disease, WHEN the chat service builds context, THEN it MUST search the available government/ICAR data sources and inject relevant snippets (up to 500 characters) into the `government_crop_manual_search_results` slot.

2. GIVEN no matching government snippet is found for a specific query, WHEN building the prompt, THEN the slot MUST be populated with `"No specific advisory found. Please consult your local KVK extension officer."` — never left blank.

3. GIVEN a government snippet is found and Gemini cites a pesticide or treatment, THEN the response MUST reference the source (e.g., `"As per ICAR Package of Practices"` or `"As per IMD/Agmarknet data"`).

4. GIVEN the chatbot is asked about a chemical treatment and `government_crop_manual_search_results` is empty or unavailable, THEN the SAFETY FIRST rule MUST apply — the chatbot MUST decline to recommend a specific chemical and direct the farmer to a local extension officer.

### Requirement 5: Market Price Data Grounding

**User Story:** As a farmer deciding whether to sell or hold a crop, I want the chatbot to cite the actual mandi price for my nearest market — not an outdated or guessed number.

#### Acceptance Criteria

1. GIVEN a farmer sends any query, WHEN the context is built, THEN `current_market_price` MUST be populated from `market_service.get_prices()` for the farmer's location and any crops mentioned in the query.

2. GIVEN live mandi data is available (`is_live == True`), WHEN the price is shown in the response, THEN it MUST display modal price, MSP, mandi name, and the profit-vs-MSP indicator.

3. GIVEN live data is unavailable, WHEN the price slot is rendered, THEN it MUST show `"MSP 2024-25: ₹X/q (live data unavailable — check agmarknet.gov.in)"` and MUST NOT present an MSP estimate as a live traded price.

4. GIVEN the farmer explicitly asks about a specific crop's price, WHEN the context is built, THEN `market_service.get_prices()` MUST be called with that crop as a filter to surface the most relevant price row.

### Requirement 6: Response Evaluation Steps Enforced in Prompt Flow

**User Story:** As a product owner, I want every chatbot response to pass a defined checklist before reaching the farmer — so the AI never gives contradictory or dangerous advice.

#### Acceptance Criteria

1. GIVEN the system prompt includes a `KIRO'S RESPONSE EVALUATION STEPS` section, WHEN the prompt is sent to Gemini, THEN the evaluation steps MUST appear in the user prompt — instructing the model to check for weather conflicts, sensor data conflicts, and to ground every answer in the provided official snippets.

2. GIVEN the rule-based fallback (`_smart_rule_response`) is used instead of Gemini, WHEN generating a response, THEN the same three checks MUST be applied programmatically: check soil moisture before any irrigation recommendation; check weather alerts before any spray/fertiliser recommendation; verify government snippet availability before citing any chemical treatment.

3. GIVEN a query conflicts with live sensor or weather data (e.g., farmer asks to irrigate but moisture is high), WHEN the response is generated, THEN the conflict MUST be explicitly called out at the start of the response.

### Requirement 7: Frontend Sensor Context Passthrough

**User Story:** As a farmer using the web app, I want the chat interface to automatically include my location and IoT context in every message — so I don't have to repeat it manually.

#### Acceptance Criteria

1. GIVEN the frontend already sends `latitude`, `longitude`, and `session_id` with each chat message, WHEN IoT sensor data has been fetched and displayed in the UI (from `/api/iot/sensor_data/`), THEN the most recent sensor readings MUST also be included in the chat POST payload as a `sensor_context` object.

2. GIVEN `sensor_context` is included in the POST payload, WHEN the `ChatbotViewSet._handle_query()` method processes the request, THEN it MUST extract and pass `sensor_context` to `chat_intelligence_service.answer()`.

3. GIVEN a session already has a prior IoT reading stored in `ChatSession.conversation_context`, WHEN a new message arrives without `sensor_context` in the payload, THEN the service MUST fall back to the session-stored sensor context rather than making a fresh API call each time.

### Requirement 8: Multilingual Prompt Localisation

**User Story:** As a Hindi or regional language farmer, I want the structured prompt labels and advisory tone to match my language — so the response feels natural, not like a translated manual.

#### Acceptance Criteria

1. GIVEN the farmer's language is `"hi"` (Hindi), WHEN building the system prompt, THEN the language instruction MUST include Hindi-specific tone guidance (warm, empathetic, address farmer as `किसान भाई`).

2. GIVEN the farmer's language is any supported regional language (Tamil, Telugu, Marathi, Bengali, Gujarati, Kannada, Malayalam, Punjabi), WHEN building the system prompt, THEN `get_gemini_language_instruction()` MUST inject the correct language instruction so Gemini responds entirely in that language and script.

3. GIVEN the rule-based fallback is active, WHEN responses are generated, THEN all hardcoded response strings MUST include language variants for at least `"hi"` (Hindi) and `"en"` (English), with English as the default for any unlisted language code.
