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

Newer reference docs (added for the Java migration / interview-prep pass):
- `docs/ARCHITECTURE.md` — as-built system architecture, request flow, migration status table
- `docs/DEVELOPER_GUIDE.md` — how to run it, repo layout, how to migrate the next service to Java
- `docs/TECHNICAL_GUIDE.md` — detailed stack/dependency rationale (why FastAPI, why Redis-only, why Spring Boot for the Java side, etc.) — written to double as MIT Lincoln Lab interview prep material, cross-referenced to `mit-lincoln-lab-technical-qa.md` in the user's `Desktop/resume/` prep folder
- `docs/API_REFERENCE.md` — every internal + external API call, resiliency posture (timeouts/retries/idempotency, honestly gapped where true), and a boundary-by-boundary security review. Documents one real finding, now fixed: unescaped user text interpolated into the emailed HTML report (XSS-shaped, low blast radius since it only affects the recipient's own inbox rendering their own submitted data) — was present in the original Python `services/agents/reporting/main.py`, fixed during the Java rewrite (`ReportingService.java` HTML-escapes every interpolated field)
- `docs/PRODUCTION_READINESS.md` — the production push plan (written 2026-07-23, nothing in it acted on yet). Covers the one real blocker (frontend Dockerfile still runs `next dev`), the hosting decision (settled on a single GCP `e2-small` VM at $12.23/month under a confirmed $15/month budget — see that doc for the free-tier research that got ruled out first and why), and an ordered todo list for the next session picking this up

## Why a Python→Java migration is happening (session context)

User has an MIT Lincoln Lab (Group 57, Cyber Ops) software engineer
interview likely the week of 2026-07-27 (see `Desktop/resume/` prep
materials — `mit-lincoln-lab-interview-prep.md` and
`mit-lincoln-lab-technical-qa.md`). Per that prep guide's gap map, the
user's Java/Spring/Docker/AWS skills are already strong; real gaps are
Kafka/NiFi/Istio/Terraform/Ansible, a live Python exercise, and having
concrete stories ready. Decision: keep migrating Rootwell's non-LLM
backend services from Python/FastAPI to Java/Spring Boot as hands-on
practice reps (reinforces the strong column, gives a second "built the
platform" story alongside PolicyMind), while separately drilling the
actual gap topics via mock Q&A / STAR rehearsal / Python warm-ups —
**don't let the Rootwell rewrite crowd out that gap-drilling time**, per
the user's own prioritization. See `docs/TECHNICAL_GUIDE.md` §7 for how
each Rootwell architecture choice ties back to a specific interview-guide
question.

**Migration scope** (re-derived from the code, not assumed): only
`agent-intake`, `agent-mapping`, `agent-explanation` import `shared.llm`
(the Anthropic wrapper) — those three stay Python. Everything else in
`services/` is moving to Java one service at a time, each verified
end-to-end before the next. Frontend stays Next.js. Full status table in
`docs/ARCHITECTURE.md` §7.

## Current status: Phase 1 built and verified end-to-end; Java migration complete

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
container (FastAPI for the three LLM agents + gateway, Spring Boot for the
rest — see below); the `orchestrator` sequences calls to the stateless
agents; the `gateway` is the only thing the frontend talks to directly. See
the v2 design doc for the full service map and the reasoning behind the
two-tier cache split.

The backend is now a deliberate, permanent Python/Java mix, not a rewrite
in progress: `knowledge-botanical`, `knowledge-compound`,
`knowledge-toxicology`, `knowledge-rules`, `agent-retrieval`,
`agent-safety`, `agent-scoring`, `agent-reporting`, `email`, and
`orchestrator` are Java/Spring Boot; `agent-intake`, `agent-mapping`,
`agent-explanation`, and `gateway` stay Python (full rationale and status
table in `docs/ARCHITECTURE.md` §7). Every service, regardless of
language, keeps the same external contract — port 8000 internally,
`GET /healthz`, `REDIS_URL` from env — so this is invisible to every other
service.

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
- [x] `ANTHROPIC_API_KEY` is real and live in `.env` (set 2026-07-22) — all
      three LLM agents confirmed running with `mock_mode: false`
- [ ] `RESEND_API_KEY` is still unset — email export runs in mock mode
      (logs the rendered email instead of sending it)
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
- [ ] Donations — user wants a way for visitors to voluntarily support
      ongoing Claude API / hosting / Resend costs (and some of the labor),
      with a small, low-pressure "if this is useful, consider a small
      donation" note (e.g. Footer + About page), not a paywall or anything
      gating features. Recommended: **Ko-fi** (0% platform fee on one-time
      tips, no business entity required, simple embeddable button) over
      Buy Me a Coffee (~5% fee, nicer brand recognition) as the close
      second. **Blocked on the user creating the actual Ko-fi/BMC account**
      (needs their real identity + bank details, not something to do on
      their behalf) — once a link exists, wiring up the on-site copy/
      placement is quick. Also connects directly to the business-entity
      item right above this one: accepting real money is the natural
      trigger point for that decision, worth a beat of thought (and
      possibly an accountant check on how donation income is treated)
      before this goes live, not after.
      **Compliance guardrails (Stripe/app-store Restricted Businesses
      policy for health-adjacent apps, researched 2026-07-23) — checked
      the app against these directly, not just noted them:** medical
      disclaimer must be prominent (**already true** — persistent in
      `SummaryPanel` every session + on the About page, standard
      "informational only, not a substitute for professional medical
      advice, diagnosis, or treatment" phrasing); must never claim an
      herb "cures/treats/prevents" a specific disease (**already true,
      verified by grepping the full codebase** — the seed dataset only
      uses hedged terms like "support"/"comfort," and both
      `agent-mapping`'s and `agent-explanation`'s system prompts already
      forbid diagnosing or claiming guaranteed efficacy, on purpose, from
      the original design). **The one real to-do**: when the actual
      donation button/copy gets built, frame it explicitly as
      "support the project" / "help cover server + API costs" — never
      anything implying payment grants better advice or faster/special
      treatment.

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
