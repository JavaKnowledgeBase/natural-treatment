# Rootwell — Project Reference

Read this first when picking this project back up. It captures decisions and
state that aren't obvious from the code alone.

## What this is

**Rootwell** (formerly called "Natural Treatment Recommendation Engine" in
the early research docs — same product, renamed). A conversational,
agentic, microservice web app that traces user-reported symptoms back to a
likely biochemical root cause and suggests herbs with some evidence backing
them. Founder: **Ravi Kafley**. Contact: `hello@rootwell.app` (placeholder —
domain not registered yet).

Design docs (still accurate for architecture/product decisions):
- `research docs/application_design.md` — v1, product vision, UX flow, scoring formula
- `research docs/application_design_v2_microservices_agentic.md` — v2, current architecture (microservices, agentic, cache-only)

## Current status: Phase 1 built and verified end-to-end

All 13 backend microservices + Next.js frontend exist, run via
`docker compose -f infra/docker-compose.yml up -d --build`, and were
verified working end-to-end (session creation → symptom collection → cause
collection → analysis pipeline → ranked recommendations → email export with
verification-code gate → session purge confirmed via `redis-cli`). Safety
rule enforcement was verified too (volunteering "I am pregnant" correctly
penalizes ashwagandha's score via the independent Safety Agent).

Runs with **zero external credentials** by design — every LLM call
(Anthropic) and every email send (Resend) falls back to a clearly-labeled
mock response when the corresponding API key is absent from `.env`.

### Architecture, in one paragraph

No database anywhere. Redis is the only stateful component, split into
Tier 1 (`ref:*`, shared herb/compound/symptom/rule data, loaded from the
hand-curated starter seed in `seed/data/*.json`) and Tier 2 (`session:*`,
one user's chat/symptoms/causes/recommendations, TTL'd and hard-deleted on
session end or email export). Every service in `services/` is a separate
FastAPI container; the `orchestrator` sequences calls to the stateless
agents; the `gateway` is the only thing the frontend talks to directly. See
the v2 design doc for the full service map and the reasoning behind the
two-tier cache split.

### Known environment quirks (this machine specifically)

- Port 8080 conflicts with an unrelated local project (`policymind`) — the
  gateway is mapped to host port **8082** instead. Frontend's
  `NEXT_PUBLIC_GATEWAY_URL` points there.
- Port 6379 also conflicts — Redis is mapped to host port **6380**.
- These are host-port mappings only; internal container-to-container URLs
  are unaffected (still `:8000` on the docker network).

### Bug fixed this session

Mock-mode intake agent originally required the *entire* catalog symptom
phrase (e.g. "chronic headaches") to appear verbatim in the user's message,
so "I have a headache" matched nothing. Fixed in
`services/agents/intake/main.py` (`_symptom_matches` /
`_word_matches_text`) to match on individual significant words with basic
singular/plural tolerance instead of the whole phrase.

## Branding (added this session)

- Logo: `frontend/src/components/Logo.tsx` — minimal botanical line-art
  (leaf + root SVG) + "Root**well**" wordmark, two-tone (stone/emerald).
- `frontend/src/components/Header.tsx` — site header, wraps every page via
  `layout.tsx`.
- `frontend/src/components/Footer.tsx` — contact/legal links.
- `frontend/src/app/about/page.tsx` — mission blurb, founder byline ("Ravi
  Kafley, Founder"), contact email.
- `frontend/src/app/privacy/page.tsx` and `.../terms/page.tsx` — **drafts**
  that accurately reflect the current cache-only architecture, explicitly
  marked as needing real legal review before any public launch.
- No phone number yet — user is getting a Google Voice number to forward;
  add it to the About page and Footer once provided. Don't add a personal
  number without checking first (flagged as a public-exposure tradeoff
  earlier in the conversation).

## Open items / where to pick up next

- [ ] Add phone number (Google Voice) once the user has it
- [ ] Register `rootwell.app` (or whatever domain) and set up real email
      forwarding for `hello@rootwell.app`, then swap `RESEND_FROM_ADDRESS`
      in `.env` to match
- [ ] Get real `ANTHROPIC_API_KEY` / `RESEND_API_KEY` into `.env` when ready
      to leave mock mode
- [ ] Replace/expand the starter seed dataset (`seed/data/*.json`, ~18
      herbs) with real curated data — every record is currently tagged
      `curation_status: starter_dataset_unreviewed` and that flag is
      threaded through to the UI and email export on purpose; don't remove
      the flag without an actual curation pass
- [ ] Phase 2 items deferred by design (see v2 doc §9 and README): Cloud
      Run/K8s deployment manifests, live fallback to IMPPAT/ChEBI/PubChem/CTD
      on cache miss, multi-symptom conflict resolution, personalized history
- [ ] Legal review of the Privacy/Terms drafts before any public launch
- [ ] Consider whether "Ravi Kafley" as sole named founder should later move
      under a business entity for liability separation once this is more
      than a dev build (flagged, not decided)

## How to verify it still works

```bash
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml ps          # all should be Up
curl -s http://localhost:8082/healthz                   # gateway
curl -s http://localhost:3000/about                      # frontend + branding
```

Full manual curl walkthrough is in `README.md`. See the "Verification"
section of the original plan (this session's plan file, if still present at
`~/.claude/plans/`) for the exact sequence used to validate the full
pipeline including the email export and purge.
