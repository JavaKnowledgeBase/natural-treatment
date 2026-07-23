# Rootwell — Production Readiness & Push Plan

Written 2026-07-23 as a planning document ahead of a production push. Every
claim below was checked directly against the current code/Dockerfiles/`.env`
as of this date (commit `5e14c0d` and earlier), not assumed — see inline
notes for what was verified how. Nothing in this document has been acted on
yet; it's the plan, not a log of completed work. Pair with `CLAUDE.md`'s
"Open items" section, which this doc's todo list (§6) folds into.

---

## 1. Honest current-state assessment

**What's already production-appropriate:**
- All 8 Java services (`knowledge-*`, `agent-scoring/-reporting/-safety/-retrieval`,
  `email`, `orchestrator`) build a real multi-stage Maven artifact and run
  it via plain `java -jar app.jar` on a slim JRE base image — no dev-mode
  Spring tooling, no `mvn spring-boot:run`. Verified by reading every
  Dockerfile directly.
- All 4 Python services (`gateway`, `agent-intake/-mapping/-explanation`)
  run plain `uvicorn main:app --host 0.0.0.0 --port 8000` — no `--reload`,
  no dev flags. Single worker process each, which is fine for today's
  traffic but is a real scaling knob to revisit later (see §3).
- The gateway's rate limiter is already Redis-backed (`INCR`/`EXPIRE` on a
  shared key), not in-process memory — so it's already correct if this
  ever runs as multiple gateway replicas, not a gap to fix.
- Mock-mode-by-default means the app never *hard*-fails on a missing
  credential; it degrades to a clearly-labeled deterministic fallback.
  This property should be preserved through any production change.

**The one unambiguous blocker: the frontend container runs `next dev`.**
`frontend/Dockerfile`'s `CMD` is `["npm", "run", "dev"]` — the Next.js
*development* server: unoptimized bundles, hot-reload overhead, dev-only
warnings, not meant to serve real internet traffic. This must become a
real multi-stage build (`next build` → `next start`, or `output: "standalone"`
for a smaller runtime image) before any production push. Every other
service is already built correctly; this one was never revisited after
the initial scaffold.

**No CI/CD, no staging/prod split, no deploy target yet.** Confirmed: no
`.github/` directory, only one `infra/docker-compose.yml` (local-only,
plain HTTP, `localhost` URLs baked into `NEXT_PUBLIC_GATEWAY_URL` and
`CORS_ALLOW_ORIGINS`'s default). Today's "production push" is starting
from zero infrastructure, not migrating an existing one — worth setting
expectations accordingly for how much can realistically land in one day.

---

## 2. Must-fix before any production push (blocking)

1. **Fix the frontend Dockerfile** (§1) — multi-stage build, real `next build`.
2. **Domain + DNS.** `hello@rootwell.app` is still a placeholder (`CLAUDE.md`
   open item, unregistered as of this writing). Needed for: the real
   gateway/frontend URLs, `RESEND_FROM_ADDRESS` (Resend requires a
   verified sending domain for anything beyond their own test address),
   and `CORS_ALLOW_ORIGINS`.
3. **`RESEND_API_KEY` + verified sending domain.** Currently unset —
   confirmed in `.env`, email export runs in mock mode (logs instead of
   sending). Needs the domain from #2 first.
4. **Update `CORS_ALLOW_ORIGINS` and `NEXT_PUBLIC_GATEWAY_URL`** away from
   their `localhost` defaults to the real production origin/URL once #2
   exists.
5. **Secrets management for whatever host is chosen.** There's currently
   one flat `.env` file read by Docker Compose locally — that pattern
   doesn't transfer to most hosting platforms as-is (see §4's per-target
   notes). Needs a decision tied to the hosting choice, not solved
   generically here.
6. **TLS/HTTPS.** Nothing in this stack terminates TLS today; everything
   local is plain HTTP. Whatever hosting target is chosen needs to own
   this (a platform-managed cert is the default expectation on every
   option considered in §4).

---

## 3. Strongly recommended, not strictly blocking

- **Retry/backoff on the Resend send call** — the one real asymmetry left
  in the mock-mode-fallback story (documented honestly in
  `docs/API_REFERENCE.md` §3): a transient Resend outage surfaces as a
  500 to the user at the exact moment they're trying to save their
  session, right before purge. Anthropic already got the equivalent
  hardening (timeout + fallback) earlier; Resend hasn't.
- **Redis auth (`requirepass`).** Fine on an isolated local Docker
  network; a real finding the moment Redis's network boundary is less
  tightly controlled than that (see `docs/ARCHITECTURE.md` §7's note on
  the reverted attempt at this, and the root cause found there).
- **Legal review of the Privacy/Terms drafts** — both pages already say
  "draft, have this reviewed by counsel before launch" directly in the
  UI; that's not satisfied yet.
- **Multi-worker Python processes** (`uvicorn --workers N` or a process
  manager in front) once real concurrent traffic shows up — today's
  single-worker-per-service is fine for low/sporadic traffic, not for
  genuine concurrency.
- **Basic uptime monitoring** — nothing currently polls `/healthz`
  externally; a container silently dying would only be noticed when a
  user hits it.
- **A backup/export path for the seed dataset and any future real
  curated data** — currently just JSON files in the repo, which is fine,
  but worth naming explicitly as "the backup story" rather than leaving
  it implicit.

---

## 4. Hosting target — settled on a direction, final sizing pending verification

**Constraint from this session, refined twice: started as "no-cost Google
Cloud specifically," relaxed to a $10/month ceiling, then confirmed at
$15/month** — ahead of the donation mechanism (`CLAUDE.md` open item)
actually being live to offset it. Researched Google Cloud's current
*Always Free* tier and small-VM pricing directly rather than relying on
memory, since both change over time and getting this wrong risks a real
bill:

| Resource | Always Free allotment (verified via web search, 2026) |
|---|---|
| Compute Engine | **1** `e2-micro` instance/month, `us-west1`/`us-central1`/`us-east1` only, + 30GB standard persistent disk |
| Cloud Run | 2,000,000 requests/month; 180,000 vCPU-seconds/month (~50 hrs); 360,000 GiB-seconds/month (~100 hrs at 1GiB / ~200 hrs at 512MiB) |
| Cloud Run network egress | 1 GiB/month free, North America only |
| Artifact Registry | Some free storage; heavy image storage can incur small charges |

**What this means concretely for a 16-container polyglot app like this
one, worked through rather than left abstract:**

- **A single free `e2-micro` cannot run the full `docker-compose.yml` stack
  as-is.** That instance has ~1GB RAM total. Eight JVMs (Spring Boot
  services realistically want 256–512MB heap each to avoid OOM) alone
  would exceed that before counting the four Python services, Next.js,
  and Redis. This would need to be radically re-architected (fewer,
  consolidated services; aggressively capped JVM heaps) to have a shot at
  fitting, and would likely still be fragile. **Not recommending this
  path** — flagging it because it's the first thing "just run
  docker-compose on the free VM" suggests, and it's a trap worth naming
  explicitly rather than discovering via OOM kills in production.
- **Cloud Run fits the actual traffic shape better** (scale-to-zero means
  an idle service costs nothing, which matches a donation-funded,
  low/sporadic-traffic side project) — but the free vCPU-second/GiB-second
  budget is **shared across every service in the project**, not per-service.
  Splitting into 13+ separate Cloud Run services (one per backend
  service) means cold-start overhead — and Spring Boot cold starts are
  not fast, often multiple seconds — eats into that shared budget faster
  and adds real, user-visible latency spikes on the first request after
  any idle period, especially painful across a multi-hop chain like
  `/analyze` (mapping → retrieval → safety → scoring → explanation, each
  a separate service that could all be cold at once).
- **Redis needs somewhere stateful to live — not Cloud Run** (scale-to-zero
  would wipe session data on every cold start) **and not Memorystore**
  (Google's managed Redis has no free tier at all). The free `e2-micro` is
  actually a good fit for *just* Redis alone, though — it's lightweight,
  and that leaves the VM's spare capacity unused by anything else.
- **Realistic "no-cost" path, if Google Cloud specifically is the
  constraint:** Redis on the free `e2-micro`; the backend services and
  frontend on Cloud Run, consolidated where reasonable to reduce the
  cold-start-chain problem (e.g., could the four `knowledge-*` services
  become one service with four routes, cutting cold-start hops from 4 to
  1? Worth evaluating, not yet decided). Accept that the 1 GiB free
  egress will likely be exceeded the moment there's real (non-testing)
  traffic — "no cost" realistically means "no cost during testing/low
  traffic," not "free forever at any scale," and that's worth being
  explicit about rather than implying a permanent guarantee.
- **Budget relaxed mid-session, first to $10/month, then confirmed at
  $15/month — not strictly $0.** This changes the recommendation.
  Checked GCP's own small-VM pricing directly rather than estimate it:

  | Machine type | RAM | On-demand price (us-central1, verified) |
  |---|---|---|
  | `e2-small` | 2 GB | **$12.23/month** |
  | `e2-medium` | 4 GB | $80.64/month — **flagged as unreliable**, wildly inconsistent with GCP's usual ~2x-per-tier scaling (would expect ~$24-25/month); came from a third-party pricing aggregator, not Google's own calculator. Don't trust this number without re-checking directly against `cloud.google.com/products/calculator` before acting on it.

**Recommendation, given the confirmed $15/month ceiling: a single
`e2-small` VM (2GB RAM, $12.23/month) running the existing
`docker-compose.yml` via a prod override** — the same
EC2-on-a-VM-with-docker-compose pattern already used for the PolicyMind
project. This sidesteps every free-tier resource-fit and Cloud-Run-cold-start
problem discussed above entirely, is operationally the simplest option
(same tooling already known, one deploy target instead of juggling a
shared budget across 13+ Cloud Run services), and leaves ~$2.77/month of
headroom under the cap for disk or snapshot backups.

**One thing not to skip: 2GB RAM is a starting point, not a guaranteed
fit, and needs to be verified, not assumed.** Eight Spring Boot JVMs at
default settings can each want 256–512MB; even with explicit `-Xmx` heap
caps (a real, cheap fix — a few JVM flags per Dockerfile) plus four Python
processes, Next.js, and Redis, actual memory usage under real load should
be measured on the VM directly before calling this settled, not assumed
correct from the plan alone. Cloud Run (free-tier, scale-to-zero, cold-start
tradeoff described above) remains documented as the fallback path if
`e2-small` turns out too tight even after tuning.

Sources checked for the free-tier numbers above:
- [Google Cloud Free Tier Services And Limits – Notes](https://aatayyab.wordpress.com/2026/06/26/google-cloud-free-tier-services-and-limits/)
- [Google Cloud Free Tier Limits for Startups: 2026 Guide](https://www.amyntas.in/google-cloud-free-tier-limits-for-startups/)
- [Cloud Run pricing | Google Cloud](https://cloud.google.com/run/pricing)
- [compute getting started | Google Cloud](https://cloud.google.com/free/docs/compute-getting-started)
- [Google Cloud Run Pricing in 2025: A Comprehensive Guide](https://cloudchipr.com/blog/cloud-run-pricing)

---

## 5. Documentation completion — what's actually stale right now

A lot of real work landed this session that **isn't reflected in any
architecture doc yet**. Concretely missing from `docs/ARCHITECTURE.md`
and `docs/TECHNICAL_GUIDE.md` as of this writing:

- **Multi-language support** (English/Hindi/Chinese/French/Spanish) —
  the `next-intl` locale routing, the orchestrator's session-language
  plumbing, the localized LLM system prompts, the herb-name/evidence-level
  translation tables — none of this exists in the architecture docs at
  all. This is a genuinely large addition (touches frontend routing,
  every LLM agent, and the orchestrator) and deserves its own section.
- **The `agent-explanation` batching change** (5 Claude calls → 1 per
  `/analyze`) — a real, measurable cost optimization with no doc trace.
- **The design refresh** (brand palette, typography, the 2-symptom
  guided-intake gating, confirmation-before-advancing UX) — cosmetic/UX
  work, lower priority to document formally than the two above, but
  worth at least a mention so `docs/DEVELOPER_GUIDE.md`'s screenshots (if
  any get added later) aren't visually stale on day one.
- `.env.example` was missing `ANTHROPIC_TIMEOUT_SECONDS`,
  `CORS_ALLOW_ORIGINS`, and `GATEWAY_RATE_LIMIT_PER_MINUTE` — **fixed
  directly as part of writing this plan**, not deferred to the todo list.

---

## 6. Todo list for tomorrow

Ordered roughly by dependency, not necessarily by time-of-day. Items with
**(decision needed)** aren't things to just start on — they need a quick
alignment conversation first.

**Documentation:**
- [ ] Add a "Multi-language support" section to `docs/ARCHITECTURE.md`
      (or a new `docs/I18N.md`) covering the locale routing, the
      session-language plumbing through the orchestrator, and the
      scope boundary (UI + LLM conversation only, backend catalog
      matching stays English)
- [ ] Add the `agent-explanation` batching change to
      `docs/API_REFERENCE.md`'s resiliency/cost notes
- [ ] Update `CLAUDE.md`'s "Current status" summary to mention the
      design refresh + i18n + cost optimization as shipped, not just
      buried in commit messages
- [ ] Spot-check `README.md` for anything now stale (branding/status
      section specifically)

**Production build fixes:**
- [ ] Rewrite `frontend/Dockerfile` for a real production build
      (multi-stage, `next build` + `next start` or standalone output)
- [ ] Provision a GCP `e2-small` VM (us-central1/us-west1/us-east1,
      2GB RAM, $12.23/month — confirmed under the $15/month cap) as the
      settled hosting target (§4); set explicit `-Xmx` heap caps on the
      8 Java services and measure actual combined memory usage under
      real load on the VM before treating the fit as confirmed
- [ ] Register the domain, point DNS, get `RESEND_API_KEY` +
      verified sending domain
- [ ] Update `CORS_ALLOW_ORIGINS` / `NEXT_PUBLIC_GATEWAY_URL` for the
      real domain once it exists
- [ ] Secrets on the VM: same `.env`-file pattern already used locally,
      just placed on the server rather than committed — no Secret
      Manager integration needed for a single-VM deploy (that
      complexity was specific to the Cloud Run path, now not the
      chosen one)
- [ ] Deploy, then re-run the same verification pattern already
      established locally this session (full pipeline: session →
      symptoms → causes → analyze → safety-suppression check → email
      export → purge-confirmed-via-redis-cli) against the real
      production URL, not just a local rebuild

**Lower priority, same session if time allows:**
- [ ] Retry/backoff on the Resend send call (§3)
- [ ] Redis `requirepass` (§3) — only urgent once Redis is reachable
      from somewhere less isolated than a local Docker network, which a
      real hosting target makes true
