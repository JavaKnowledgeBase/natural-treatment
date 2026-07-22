# Rootwell

A conversational, agentic, microservice application that traces user-reported
symptoms back to their likely biochemical root cause and suggests
evidence-aware herbal support. See `research docs/` for the full product and
architecture design (written under the working title "Natural Treatment
Recommendation Engine" — same product, current name is Rootwell):

- `research docs/application_design.md` -- product vision, UX flow, scoring model (v1)
- `research docs/application_design_v2_microservices_agentic.md` -- microservice/agentic/cache-only architecture (v2, current)

This repo implements Phase 1 of that design: every service in the v2
architecture diagram is its own deployable app, communicating over HTTP,
backed entirely by Redis (no persistent database anywhere). It runs fully
locally with **zero external credentials** — every LLM call and every email
send falls back to a clearly-labeled mock response when the corresponding
API key is absent.

## Running it locally

Requires Docker and Docker Compose.

```bash
docker compose -f infra/docker-compose.yml up --build
```

This starts Redis, all 13 backend services, and the frontend. First boot
builds every image, so it takes a few minutes; subsequent starts are fast.

Open **http://localhost:3000** for the chat UI.

The gateway is reachable directly at **http://localhost:8082** if you want
to drive the flow with `curl` instead — see "Manual walkthrough" below.

### Using real credentials instead of mock mode

Copy `.env.example` to `.env` (already done for you with blank values) and
fill in what you have:

- `ANTHROPIC_API_KEY` — enables real Claude calls in the intake, mapping,
  and explanation agents. Without it, those agents use deterministic
  fallbacks grounded in the seed dataset.
- `RESEND_API_KEY` / `RESEND_FROM_ADDRESS` — enables real email delivery.
  Without it, the email service logs the fully rendered email to its
  container's stdout instead of sending it (`docker compose logs email`).

No code changes are needed either way — every service reads these at
startup and switches mode automatically.

## Branding

App name: **Rootwell**. Logo, About/Contact, Privacy, and Terms pages live in
`frontend/src/app/{about,privacy,terms}` and `frontend/src/components/{Logo,Header,Footer}.tsx`.
Contact email is `hello@rootwell.app` (placeholder pending domain registration).
The Privacy and Terms pages are drafts reflecting the current architecture —
have them reviewed by counsel before any real launch.

## What's in here

```
frontend/                 Next.js chat UI (the conversational intake flow)
services/
  gateway/                Session issuance, proxying, per-IP rate limiting
  orchestrator/            State graph coordinating every agent call
  agents/                  intake, mapping, retrieval, safety, scoring, explanation, reporting
  knowledge/                botanical, compound, toxicology, rules -- Tier 1 reference lookups
  email/                    Verification-gated email export (Resend or mock)
shared/                    Redis cache helpers + Pydantic models used by every service
seed/                      Starter herb/compound/symptom/rule dataset + loader
infra/docker-compose.yml   Local multi-service run
```

Every backend service exposes `GET /healthz`.

## The seed dataset

`seed/data/*.json` is a hand-written starter set (~18 herbs, 20 symptoms,
18 compounds, 25 safety rules) used to exercise the full pipeline locally.
Every herb record is tagged `"curation_status": "starter_dataset_unreviewed"`
and that flag is carried through into every recommendation shown to the
user -- this is dev/demo data, not a reviewed clinical dataset. See
`application_design_v2_microservices_agentic.md` §2.1 for how this is meant
to be replaced by a real offline-curated bundle later.

## Privacy model

There is no database. Everything lives in Redis:

- **Tier 1** (`ref:*`) -- the shared herb/compound/symptom/rule knowledge,
  no personal data, rebuilt from the seed bundle at service startup.
- **Tier 2** (`session:*`) -- one user's chat, symptom/cause cache, and
  recommendations. TTL'd, and hard-deleted the moment a session ends —
  either because the user emails themselves the results, or explicitly
  ends the session.

Nothing in the conversation flow ever asks for personal details (age,
pregnancy, medications, allergies, conditions) — those are only recorded if
the user volunteers them unprompted in free text. The only explicit ask for
contact info anywhere in the app is the opt-in "email me this" action after
results are shown, and even that requires confirming a one-time code before
anything is sent.

## Manual walkthrough (curl)

```bash
# 1. Create a session
SID=$(curl -s -X POST http://localhost:8082/session | jq -r .session_id)

# 2. Describe a symptom
curl -s -X POST http://localhost:8082/session/$SID/message \
  -H "Content-Type: application/json" -d '{"text": "I have been feeling really fatigued and stressed lately"}'

# 3. Move to causes
curl -s -X POST http://localhost:8082/session/$SID/advance-to-causes

curl -s -X POST http://localhost:8082/session/$SID/message \
  -H "Content-Type: application/json" -d '{"text": "Work has been really demanding and I have not been sleeping well"}'

# 4. Analyze
curl -s -X POST http://localhost:8082/session/$SID/analyze | jq

# 5. Request the email export (check `docker compose logs email` for the mock code)
curl -s -X POST http://localhost:8082/session/$SID/email/request \
  -H "Content-Type: application/json" -d '{"to": "you@example.com"}'

# 6. Confirm with the code from the logs -- this also purges the session
curl -s -X POST http://localhost:8082/session/$SID/email/confirm \
  -H "Content-Type: application/json" -d '{"verification_token": "<token from step 5>", "code": "<code from logs>"}'

# Confirm the purge
docker compose -f infra/docker-compose.yml exec redis redis-cli KEYS "session:$SID:*"
# should return nothing
```

## Deferred to Phase 2

- Cloud Run / Kubernetes deployment manifests (see the earlier conversation
  for the recommended free-tier Cloud Run + Upstash Redis setup)
- Live fallback to IMPPAT/ChEBI/PubChem/CTD on a seed-bundle cache miss
- Multi-symptom conflict resolution, personalized history, clinician review workflow
