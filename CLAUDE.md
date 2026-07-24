# Natural Remedy Research — Project Reference

Read this first when picking this project back up. It captures decisions and
state that aren't obvious from the code alone.

## What this is

**Natural Remedy Research** (formerly called "Natural Treatment Recommendation
Engine" in the early research docs, then **Rootwell** — same product, renamed
again 2026-07-23 when picking a production domain: `rootwell.app` and every
close variant turned out to already be registered by unrelated parties, so
the product name changed along with the domain search rather than settling
for a distant variant). A conversational, agentic, microservice web app that
traces user-reported symptoms back to a likely biochemical root cause and
suggests herbs with some evidence backing them. Founder: **Ravi Kafley**.
Contact: `hello@naturalremedyresearch.com` (domain confirmed available via
RDAP lookup 2026-07-23, not yet registered).

Frontend UI note: the full name is used in page titles/metadata and the
About page; the compact header/nav wordmark shows "Remedy Research"
(`frontend/src/components/Logo.tsx`'s `wordmark` prop, default `"short"`,
`"full"` on the About page).

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
concrete stories ready. Decision: keep migrating this app's non-LLM
backend services from Python/FastAPI to Java/Spring Boot as hands-on
practice reps (reinforces the strong column, gives a second "built the
platform" story alongside PolicyMind), while separately drilling the
actual gap topics via mock Q&A / STAR rehearsal / Python warm-ups —
**don't let the rewrite crowd out that gap-drilling time**, per
the user's own prioritization. See `docs/TECHNICAL_GUIDE.md` §7 for how
each architecture choice ties back to a specific interview-guide
question.

Note: the Java backend's package namespace (`app.rootwell.*` across all 8
Java services) still reflects the old product name. This is a deliberate,
known gap, not an oversight — see the "Open items" list below.

**Migration scope** (re-derived from the code, not assumed): only
`agent-intake`, `agent-mapping`, `agent-explanation` import `shared.llm`
(the Anthropic wrapper) — those three stay Python. Everything else in
`services/` is moving to Java one service at a time, each verified
end-to-end before the next. Frontend stays Next.js. Full status table in
`docs/ARCHITECTURE.md` §7.

## Current status: Phase 1 built and verified end-to-end; Java migration complete; design refresh + 5-language support shipped

All 13 backend microservices + Next.js frontend exist, run via
`docker compose -f infra/docker-compose.yml up -d --build`, and were
verified working end-to-end (session creation → symptom collection → cause
collection → analysis pipeline → ranked recommendations → email export with
verification-code gate → session purge confirmed via `redis-cli`). Safety
rule enforcement was verified too (volunteering "I am pregnant" correctly
penalizes ashwagandha's score via the independent Safety Agent).

As of 2026-07-23, also shipped and verified live (see "2026-07-23 session"
below for the full rundown, and `docs/ARCHITECTURE.md` §8 for the technical
detail): a premium design refresh (brand palette, typography, guided
2-symptom intake flow), full UI + LLM-conversation support for English/
Hindi/Chinese/French/Spanish, and a ~3x reduction in `agent-explanation`'s
Claude API calls via batching.

**`ANTHROPIC_API_KEY` is real and live** (set 2026-07-22) — all three LLM
agents run in live mode on this machine, not mock mode, unless the key is
later removed from `.env`. `RESEND_API_KEY` is still unset (email export
mock mode). Every external dependency still falls back to a clearly-labeled
mock response when its key is absent, by design — that property was
preserved through both the migration and this session's changes.

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

### Bug fixed in an earlier session

Mock-mode intake agent originally required the *entire* catalog symptom
phrase (e.g. "chronic headaches") to appear verbatim in the user's message,
so "I have a headache" matched nothing. Fixed in
`services/agents/intake/main.py` (`_symptom_matches` /
`_word_matches_text`) to match on individual significant words with basic
singular/plural tolerance instead of the whole phrase. (Superseded in
spirit by the 2026-07-23 language work below — live mode now understands
symptom descriptions by meaning, not just keyword matching, in any of the
5 supported languages; this fix is what mock mode still relies on.)

## Branding (established in an earlier session, some details updated 2026-07-23)

- Logo: `frontend/src/components/Logo.tsx` — minimal botanical line-art
  (leaf + root SVG) + wordmark. **Updated 2026-07-23 (design refresh)**:
  brand/gold palette + serif wordmark, not the original stone/emerald
  two-tone. **Updated again 2026-07-23 (product rename)**: wordmark text
  changed from "Root**well**" to a `wordmark` prop — `"short"` (default,
  renders "Remedy Research", used in the compact header) or `"full"`
  (renders "Natural Remedy Research", used on the About page). No more
  two-tone color split on the wordmark text itself — that treatment was
  specific to the "Root"/"well" compound word and didn't map onto the new
  three-word name.
- `frontend/src/components/Header.tsx` — site header, wraps every page via
  `[locale]/layout.tsx`. Now also hosts the language dropdown
  (`LanguageSwitcher`).
- `frontend/src/components/Footer.tsx` — contact/legal links.
- `frontend/src/app/[locale]/about/page.tsx` — mission blurb, founder
  byline ("Ravi Kafley, Founder"), contact email. **Path changed
  2026-07-23**: moved under `[locale]/` for i18n routing — was
  `frontend/src/app/about/page.tsx` before.
- `frontend/src/app/[locale]/privacy/page.tsx` and `.../terms/page.tsx`
  (same path change as above) — **drafts** that accurately reflect the
  current cache-only architecture, explicitly marked as needing real legal
  review before any public launch.
- No phone number yet — user is getting a Google Voice number to forward;
  add it to the About page and Footer once provided. Don't add a personal
  number without checking first (flagged as a public-exposure tradeoff
  earlier in the conversation).

## 2026-07-23 session: design refresh, guided intake, 5-language support, cost optimization

Full technical detail lives in `docs/ARCHITECTURE.md` §8 (multi-language)
and inline in the code; this is the "what shipped and where to look"
summary for picking the thread back up.

**Design refresh** — deep sage/forest-green `brand` palette + muted
antique-gold `gold` accent (`frontend/tailwind.config.js`), replacing the
original generic Tailwind emerald; serif display type (Fraunces, via
`next/font/google`) for headings/wordmark paired with Inter for body/UI;
warm ivory `paper` background; soft card shadows and rounder corners
throughout Header/Footer/ChatPanel/SummaryPanel/EmailExport and the
About/Privacy/Terms pages.

**Guided intake flow** — the "I've said everything about my symptoms"
advance link and the analyze button now require at least 2 matched
symptoms before appearing (a quiet progress hint shows below that
threshold), and both actions open an inline confirmation ("anything else
you'd like to add?") before proceeding rather than committing immediately.
Conversational copy across `agent-intake` and the frontend was rewritten
(researched via web search — Woebot-style empathetic UX writing
principles) to acknowledge what the user shared and avoid clinical
phrasing.

**Multi-language support** (English default, Hindi, Chinese, French,
Spanish) — full detail in `docs/ARCHITECTURE.md` §8. Scoped to UI chrome
and LLM-generated conversation only; backend catalog matching stays
English-keyed. Frontend: `next-intl`, locale-prefixed routing, a header
dropdown plus a first-visit picker under the greeting. Backend: session
language chosen once at `POST /session`, threaded through the orchestrator
to every LLM-backed agent. Live mode also explicitly handles
Romanized/transliterated input (Hinglish, Pinyin) for users without a
native-script keyboard — verified live matching symptoms correctly from
pure Latin-script Hindi input. Herb names shown as
`"<local name> (<English name>)"` per explicit preference (e.g.
"अश्वगंधा (Ashwagandha)"), favoring genuine traditional names where one
exists and phonetic transliteration otherwise, never an invented name.

**Cost optimization** — `agent-explanation` batched from up to 5 Claude
calls (one per recommended herb) into 1 per `/analyze`, cutting that
endpoint's total Claude calls from 6 to 2. Verified live producing 5
distinct, correctly hedged explanations from the single batched call.

**`docs/PRODUCTION_READINESS.md`** — the production push plan, not yet
acted on. Settled on a single GCP `e2-small` VM ($12.23/month, confirmed
under a $15/month budget) after ruling out GCP's free tier as genuinely
too small for this app's 16 containers — see that doc for the sourced
free-tier research and the reasoning trail, not just the conclusion.

**Donation compliance** — researched Stripe/app-store Restricted
Businesses policy requirements for health-adjacent apps ahead of building
the donation feature (still a `CLAUDE.md` todo, not built). Audited the
app directly (grepped every herb record, every LLM system prompt, and the
UI copy) rather than just noting the requirements — the medical disclaimer
and no-disease-claims requirements were already satisfied by the original
design (hedged language and no-diagnosis rules were already in the system
prompts from the start). The one real remaining action: frame the
eventual donation copy as "support the project," never as payment for
advice.

### A significant bug found and fixed: the Java migration silently dropped Tier 1 seeding

Reported by the user as "no suggestions" after several turns that should
have matched easily ("I have a headache" not matching `chronic_headaches`
at all). Root cause, found by testing the exact failing conversation live
and then checking the actual data, not by guessing at the prompt: **the
entire Tier 1 reference cache (`ref:*` — every herb, compound, symptom,
and rule) was empty in Redis.** `seed/load_seed.py`'s own docstring says
it's "safe to call from every knowledge service's startup hook" — true
when those services were Python. After the Java migration, the
replacement `knowledge-*` services' `RefCacheService`s are read-only by
design (`docs/TECHNICAL_GUIDE.md` §0/§5's deliberate choice) — nothing in
the running stack ever called `load_seed()` again. Tier 1 has a 6-hour
TTL (`REF_TTL_SECONDS` in `shared/shared/cache.py`) with no recurring
refresh; it looked fine for hours on data seeded before the migration,
then silently emptied out partway through this long session the moment
that TTL finally expired — which is exactly why this wasn't caught
earlier: everything "worked" until it very quietly didn't.

**Fixed structurally, not patched around**: added a `seed-loader` service
(`seed/Dockerfile`, new) to `infra/docker-compose.yml` that runs
`load_seed()` once on every `docker compose up` and exits; the 4
`knowledge-*` services now `depends_on: seed-loader:
condition: service_completed_successfully`, guaranteeing Tier 1 is fresh
every time the stack starts, regardless of language. This restores the
"self-healing on restart" property `docs/ARCHITECTURE.md` §3 already
claimed but which had actually been silently broken. Along the way, also
tried (and reverted, keeping the improvement since it's real UX value
independent of the actual bug) tightening `agent-intake`'s live-mode
system prompt to match more generously — Claude was being appropriately
literal about matching only what's clearly in the catalog, which read as
overly conservative once real data was flowing again.

**Verified live, full pipeline**: "I have a headache" → `chronic_headaches`;
"i am feeling sad and depressed" → `low_mood`; a full session through
`/analyze` produced 5 correctly ranked herb recommendations. This is a
strong story on its own — a real bug that only manifests hours after a
migration, traced to a responsibility (background data refresh) that
existed implicitly in a service lifecycle that no longer exists post-migration,
found via live symptoms rather than assumed from a prompt review, and
fixed at the architecture level instead of papering over the symptom.

## Open items / where to pick up next

- [ ] **Scope idea, not decided (raised 2026-07-23):** recommendations
      might not always be herbal — could span combinations of
      conventional medicine, diet, and exercise, not just herbs.
      Diet/exercise additions are a comparatively small lift (same
      hedged-language pattern, same "informational not prescriptive"
      posture already in place). **Actual medication recommendations are
      a much bigger jump, flagged explicitly rather than scoped
      casually**: real drug-drug interaction complexity beyond the
      current herb-contraindication rules, and it pushes the app
      meaningfully closer to practicing-medicine territory than
      "informational herbal support" — directly changes the calculus on
      the Stripe/app-store donation compliance research above (that
      research assumed the current herb-only, hedged-language posture).
      Needs real product/legal thought before any implementation, not
      just a dataset expansion.
- [ ] **Hybrid deterministic-first symptom matching** (explicit follow-up
      to the 2026-07-23 `agent-explanation` batching work, agreed but not
      started): try the deterministic mock-mode matcher first even in
      live mode, fall back to Claude only when nothing matches, to cut
      `agent-intake`'s Claude call volume further. Needs a bigger, richer
      symptom dataset (more synonyms per catalog entry) to actually pay
      off — the current mock matcher is too literal to be a good first
      pass as-is; this is real, separate work, not a quick toggle.
- [ ] **Tier 1 has no recurring refresh, only on-startup** (surfaced by
      the 2026-07-23 seed-loader fix): the new `seed-loader` service
      correctly reseeds on every `docker compose up`, but if the stack
      runs continuously without a restart for longer than the 6h
      `REF_TTL_SECONDS`, Tier 1 will go empty again exactly the same way
      it just did — the fix restored "self-heals on restart," not "never
      goes stale while running." Fine for local dev (restarts often);
      worth a real answer (periodic background refresh, or a much longer
      TTL now that seeding is reliable again) before this runs unattended
      on the production VM planned in `docs/PRODUCTION_READINESS.md`.
- [ ] Add phone number (Google Voice) once the user has it
- [ ] **Domain decided but not yet registered (2026-07-23): `naturalremedyresearch.com`.**
      Checked live via RDAP — available. This replaced the original
      `rootwell.app` plan after checking it and finding it (and every close
      variant: `rootwell.com`, `rootwellhealth.com`, `tryrootwell.com`,
      `rootcause.app`, `taproot.app`, `wildroot.app`, `sagewell.com`,
      `herbroot.com`, `rootlore.com`, `verdantroot.com`) already registered
      by unrelated parties — no evidence found of an actual competing
      "Rootwell" product, this reads as generic brandable-name squatting.
      Recommended registrar: **Cloudflare Registrar** (at-cost pricing, and
      routing DNS through Cloudflare gets free TLS termination for the
      `e2-small` VM, which also solves `docs/PRODUCTION_READINESS.md`'s
      TLS/HTTPS blocker for free). Once registered: set up real email
      forwarding for `hello@naturalremedyresearch.com`, then swap
      `RESEND_FROM_ADDRESS` in `.env` to match
- [x] `ANTHROPIC_API_KEY` is real and live in `.env` (set 2026-07-22) — all
      three LLM agents confirmed running with `mock_mode: false`
- [ ] `RESEND_API_KEY` is still unset — email export runs in mock mode
      (logs the rendered email instead of sending it)
- [ ] Replace/expand the starter seed dataset with real curated data —
      every record, including everything added below, is still tagged
      `curation_status: starter_dataset_unreviewed` and that flag is
      threaded through to the UI and email export on purpose; don't
      remove the flag without an actual expert (clinical herbalist/
      pharmacist) review pass. **State as of 2026-07-23: 43 herbs (up
      from 18), 32 symptoms (up from 20).** Two expansion rounds:
      - Round 1 (+5 herbs): feverfew, cramp bark, chasteberry, psyllium,
        boswellia — filled the 4 symptom categories that had only one
        herb each (`chronic_headaches`, `muscle_tension`,
        `menstrual_discomfort`, `occasional_constipation`).
      - Round 2 (+12 symptoms, +20 herbs): user asked to make the app
        genuinely resourceful/familiar to Indian and Chinese users, not
        just pad numbers. Expanded the symptom taxonomy first (acid_reflux,
        loss_of_appetite, diarrhea, acne, hair_loss, nasal_congestion,
        low_libido, menopausal_symptoms, blood_sugar_imbalance,
        memory_lapses, water_retention, frequent_urination — confirmed via
        a research pass that both LLM agents fetch the catalog dynamically
        per-request, so this needed no prompt/code changes), then added 10
        Ayurvedic + 10 TCM herbs targeting the new + existing categories:
        brahmi, guduchi, amla, neem, fenugreek, gotu_kola, shatavari,
        guggul, arjuna, punarnava, astragalus, panax_ginseng, schisandra,
        reishi, he_shou_wu, dong_quai, goji_berry, cordyceps, poria,
        bupleurum. All 30 new herbs across both rounds researched via
        PubMed/NCBI/clinical-trial-tier sources, not general blogs —
        deliberately turned down a "hundreds from web blogs" ask in favor
        of this slower, verifiable standard.
      - **Added a `liver_disease` condition to `SafetyService.java`'s
        fixed `CONDITION_KEYWORDS` vocabulary** (`services/agents/safety/
        .../SafetyService.java`) — 3 of the new TCM/Ayurvedic herbs
        (guduchi, he_shou_wu, bupleurum) have real, documented
        hepatotoxicity case reports found during research, and the
        existing vocabulary had no matching category; without this the
        rules would have been silently non-functional (see below on why
        that matters). He Shou Wu's liver rule is `disallowed` (factor
        0.0, not just penalized) given documented fatal case reports.
      - **Real gotcha found verifying this, worth remembering**:
        `agent-intake` caches the symptom catalog in a module-level
        Python variable (`_catalog_cache` in `services/agents/intake/
        main.py`) fetched once per process lifetime, no TTL. Reseeding
        Redis alone is not enough after adding symptoms/herbs —
        `agent-intake` (and `agent-mapping`, same pattern) must be
        *restarted* too, locally and in production, or it keeps
        matching against the stale catalog it fetched at startup. Cost
        one confusing "0 symptoms matched" debugging round before being
        traced to this.
      - **`SafetyService.CONDITION_KEYWORDS` is a hard-coded enum, not
        free-text/semantic matching** — worth remembering before adding
        any herb's contraindications: a condition tag only actually
        does anything if it's in that fixed map (or is `pregnancy`/
        `pediatric`, which are special-cased). An invented tag not in
        that list creates a rule that looks real in `rules.json` but
        silently never fires. Checked this for every new rule this
        session rather than assuming.
      - **Not yet done, explicitly deferred**: the user's original ask
        was "hundreds" of herbs; this delivered 30 at real rigor instead.
        Getting to genuine hundreds needs primary-literature access this
        session doesn't have (WHO monographs, national pharmacopoeias,
        Natural Medicines Database), likely a richer taxonomy than 32
        Western-biochemical-styled categories to actually represent
        Ayurvedic/TCM diagnostic logic, and eventually real expert
        review — flagged to the user directly as a multi-session effort,
        not something to compress into one sitting.
- [ ] **Scoring quirk noticed 2026-07-23 — root cause now confirmed, fix
      deferred by user request ("check on this later").** Every single
      recommendation across the entire session (dozens of live tests)
      came back `confidence_band: "moderate"` — never `high`, never
      `low`. Traced to `agent-scoring`'s formula
      (`services/agents/scoring/.../ScoringService.java:54-59`):
      `0.30×evidence + 0.25×symptomMatch + 0.20×compoundCount +
      0.15×safety + 0.10×traditionalUse`, banded low(<0.5)/
      moderate(0.5-0.75)/high(≥0.75). Hand-computed Shatavari's exact
      live score (0.7325) from this formula to confirm the model is
      right, not guessed. Three compounding causes:
      1. `concentrationBioavailability` (20% weight) is based on
         `compounds.size()`, but **every herb in the dataset has exactly
         one compound entry** by design pattern — so this component is a
         near-constant ~0.65 for literally every herb, contributing zero
         differentiation despite its weight.
      2. Symptom-match relevance divides by the *requested* symptom
         count, not the herb's own linked-symptom count — a herb with
         one exact match out of two reported symptoms gets half credit
         even though the match itself is perfect. The app's own UX
         (`ChatPanel`) encourages reporting 2+ symptoms, so this
         structurally caps scores exactly when users share more, the
         opposite of the intended incentive.
      3. `traditionalUse` (10% weight) gives 0.8 to any evidence_level
         containing "traditional" and only 0.5 to `clinical_trial` — a
         backwards incentive where better-evidenced herbs score *lower*
         on this component than weakly-evidenced ones.
      This also explains the earlier "same top-5 across different
      symptoms" observation from earlier the same session — not a
      separate issue, same root cause. **Deliberately not fixed this
      session** — real design questions here (is `traditionalUse`
      supposed to invert like this? should compound-count even be a
      scoring input while every herb has exactly 1?), not a quick patch.
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
      **App Store / Play Store IAP rule (researched 2026-07-23, only
      relevant if this ever becomes a native app):** Apple/Google
      generally require donations to go through their official In-App
      Purchase system (15-30% cut) rather than a third-party processor
      like Stripe/Ko-fi for anything they classify as a native app, on
      risk of rejection. **This does not currently apply** — this app is
      a website (Next.js), not distributed through either app store, so
      the Ko-fi/Stripe external-link recommendation above stands as-is.
      Only becomes relevant if the app is later wrapped for native
      distribution (e.g. a WebView/Capacitor shell) — worth remembering
      *then*, not something to design around now. Two open questions
      surfaced by this research, not yet answered by the user: (1) is a
      native App Store/Play Store release even planned, or web-only for
      the foreseeable future? (2) does the user want help drafting a
      more formal/standard medical disclaimer beyond the current one
      (which is already solid, per the audit above, but a dedicated
      pass was offered and not yet taken up)?

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
