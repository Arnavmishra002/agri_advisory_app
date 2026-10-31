# Release Checklist

Status: **HOLD for public farmer launch**. No push or deployment authorized in
this pass. Preserve the current worktree and existing user changes.

## Local gates completed

- [x] Audited OTP acceptance and timeout behavior repaired and tested.
- [x] Borrowed district field facts removed; unknown input provenance exposed.
- [x] Date boundary regressions use explicit clocks.
- [x] Public detailed launch-readiness restricted outside DEBUG.
- [x] Bodo compatibility, beta language labels and required-key CI check.
- [x] Main/labels/focus/RTL/responsive browser regressions.
- [x] Real Django browser OTP/profile/reload/refresh/logout journey with synthetic SMS.
- [x] Full backend, frontend build, UI contract and three browser engines tested.
- [x] Historical evidence retained and matrix regenerated.

## Required before deployment approval

- [ ] Review every changed file and contract in REMEDIATION_REPORT.md.
- [ ] Finish hardcoded service/error translations and fluent review.
- [ ] Resolve ChromaDB advisory exposure and document mitigation/upgrade decision.
- [ ] Run PostgreSQL/Redis/Celery integration and failure tests in disposable staging.
- [ ] Configure provider secrets through secret stores, not Git:
  `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `DATA_GOV_IN_API_KEY`,
  `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`,
  `PHASE1_BASE_URL`, `PHASE1_SERVICE_TOKEN`, `OLLAMA_BASE_URL`, optional
  `GOOGLE_AI_API_KEY`, `SENTRY_DSN` (verify provider-specific names in settings).
- [ ] Set and validate `DEBUG=false`, `RATE_LIMIT_ENABLED=true`,
  `STRICT_PRODUCTION_CONFIG=true`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`,
  `RAG_INDEX_REQUIRED=true` in the intended environment.
- [ ] Use a valid staff JWT as `LAUNCH_READINESS_TOKEN` for protected CI probes.
  Expiration must fail the job; do not make readiness public to work around it.
- [ ] Verify live SMS acceptance AND delivery, expiry and resend on real devices.
- [ ] Verify Phase1 retrieval, Ollama generation, grounded JSON/SSE and latency.
- [ ] Verify mandi dates/units/local scope; never substitute dated or state rows
  as a live exact-mandi price. Measure coverage, not just HTTP success.
- [ ] Keep disease advisory fallback until independent model/serving validation.
- [ ] Finish remaining NOT RUN/PARTIAL matrix entries and farmer usability study.

## Approved release procedure

1. Obtain approval to push/merge/deploy. Review dirty files individually; do not
   blindly `git add -A` and do not discard audit/user work.
2. Run the reproducible local and disposable staging gates in TEST_RESULTS.md.
3. Capture intended Git SHA and build/image revision label. Run CI on that SHA.
4. Request deployment using the actual configured mechanism. A skipped hook,
   successful build or HTTP200 must not be reported as a verified release.
5. Verify Render deploy status and matching deployed SHA, collectstatic, migrations,
   protected launch-readiness, minimal public health and critical live journeys.
6. Invite a limited cohort only after release blockers are resolved; observe
   errors, source freshness, latency and support contacts before wider rollout.

## Rollback and data

No schema migration was added by this remediation. The local test database was
disposable; no shared database was migrated. Before an approved production change,
take the provider's supported backup and retain the last working deployment SHA.
Rollback means redeploying that approved SHA, not resetting this dirty worktree.
Do not restore old code that exposes readiness details or fabricated field facts
without an explicit security review. Never commit credentials, OTP captures or
private farmer records with the reports.
