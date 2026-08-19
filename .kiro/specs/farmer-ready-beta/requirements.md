# Farmer-Ready India-Wide Beta Requirements

## Status And Precedence

This document is the canonical contract for the India-wide beta. Where an older
specification conflicts with this document, this document takes precedence. All
non-conflicting acceptance criteria in the older specifications remain active.

## 1. Farmer-Safe Data Policy

1. The application must never present synthetic, simulated, MSP-derived, or
   predicted values as live weather, mandi, sensor, or disease data.
2. Weather and mandi integrations are intent-aware. Greetings and unrelated
   questions must not call those services merely to populate a prompt.
3. A selected mandi's fresh official row is preferred. If it is unavailable,
   the API may return fresh official alternatives within 150 km, ordered by
   distance and labelled with mandi, commodity, variety, min/modal/max price,
   report date, distance, freshness, and source.
4. When no qualifying official mandi row exists, the result is `unavailable`.
   MSP may be shown only as a separately labelled government support price, not
   as a traded or estimated mandi price.
5. Disease classification remains disabled unless model metadata is
   `production_candidate`. Photo workflows return `advisory_fallback` with
   symptom questions, weather context, warning signs, and KVK escalation.

## 2. IoT-Grounded Chat Contract

1. `sensor_context` is the canonical chatbot request field. `sensors` is a
   backwards-compatible alias; sending both is rejected.
2. Sensor payloads use a strict schema. Unknown fields, non-numeric readings,
   out-of-range values, and malformed timestamps are rejected with HTTP 400.
3. Request sensor data is authoritative only when the client identifies a real
   device/source and supplies a timestamp no older than 30 minutes. Otherwise,
   the service may use the newest matching `IoTSensorReading` no older than 30
   minutes. Missing data remains unavailable.
4. Simulated readings may be used only in an explicitly enabled demo mode and
   must never influence farmer-facing production advice.
5. JSON and SSE final metadata include `iot_sensors_used`, `sensor_source`,
   `sensor_observed_at`, `sensor_age_seconds`, and `weather_constraints`.
6. Soil moisture classification is: Critical below 35%, Low from 35% to below
   50%, Adequate from 50% through 65%, and High above 65%.
7. Adequate or high moisture blocks irrigation advice. Heavy-rain, frost, and
   spray constraints are applied before model generation and in rule fallback.
8. Grounded prompt assembly is deterministic and independently testable. It
   contains no session identifiers, random values, or implicit current time.

## 3. AI And Learning Policy

1. The answer chain is: instant factual/rule response, local knowledge facts,
   Phase 1 RAG/Ollama, direct Ollama, labelled Gemini fallback, then safe rule
   fallback.
2. Knowledge-base text is grounding context. Except for direct factual lookups,
   it must be reframed for the current question rather than returned verbatim.
3. Chemical products or doses require attributable ICAR/PPQS evidence in the
   supplied context. Without it, the response directs the farmer to KVK.
4. Farmer feedback is signed, de-identified before export, reviewed by an
   agronomist, evaluated, versioned, and promoted through staging. Unreviewed
   messages never update production retrieval or model weights automatically.

## 4. Authentication And Privacy

1. Weather, mandi, crop advice, chatbot, schemes, and advisory-only diagnosis
   remain available to guests.
2. OTP verification is the primary phone-account registration path and locks
   after three failed verification attempts per phone and per IP in one hour.
3. Classic registration requires username and password; phone is optional and
   linked only after validation. Password login accepts username or email.
4. Access tokens use `localStorage`; refresh tokens use `sessionStorage` until
   an HTTP-only cookie deployment is introduced. Logout clears tokens, user
   state, OTP fields, registration fields, timers, and private cached history.
5. Guest location and conversation history are linked to the account only after
   successful authentication and must never be exposed through client-supplied
   ownership identifiers.

## 5. Launch Gates

1. Strict launch readiness returns HTTP 200 only when `DEBUG=false`, PostgreSQL,
   Redis, Sentry, valid production origins, live data.gov.in credentials, Phase
   1/RAG, and the configured Ollama model are operational.
2. `RAG_INDEX_REQUIRED=true` and shared Redis-backed throttling are mandatory in
   production.
3. An unverified disease model is not a whole-application blocker while
   classification is disabled and advisory fallback is healthy. Enabling image
   classification makes `production_candidate` model quality mandatory.
4. Hindi, Hinglish, and English are launch-grade. Other languages are labelled
   beta until their safety and language evaluations pass.
5. The CI launch gate must run against the deployed strict-readiness endpoint;
   normal development checks may continue to use explicit safe fallbacks.
