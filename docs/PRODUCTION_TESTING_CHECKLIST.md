# Production Testing Checklist — first live deploy (2026-07-23)

Manual pass over `https://naturalremedyresearch.com` now that it's real
infrastructure instead of `docker-compose` on a laptop. Check items off
as you go; anything that fails, note it here with what you saw before
fixing, so the failure mode is on record.

## Core pipeline

- [ ] Load `https://naturalremedyresearch.com` — page loads, correct
      branding ("Remedy Research" wordmark, brand/gold palette)
- [ ] Padlock/HTTPS shows valid (no browser warnings) — confirms Full
      Strict + Origin Certificate is actually trusted end-to-end
- [ ] Full session: describe 2+ symptoms → advance to causes → describe
      a cause → analyze → get ranked herb recommendations
- [ ] Recommendations show `curation_status: starter_dataset_unreviewed`
      messaging somewhere visible (not silently dropped in prod)

## Safety + correctness

- [ ] Volunteer a safety-relevant detail mid-conversation (e.g. "I am
      pregnant") and confirm it measurably changes/penalizes a
      contraindicated herb's score (ashwagandha is the known case)
- [ ] Try an ambiguous/sparse symptom description and confirm graceful
      handling (not a crash, not an empty result with no explanation)

## Email export (real sending now, not mock)

- [ ] Request the email summary with a real address you can check
- [ ] Verification code actually arrives in inbox (from
      `hello@naturalremedyresearch.com`, not the old
      `onboarding@resend.dev` test sender)
- [ ] Enter the code, confirm the full report email arrives and reads
      correctly (herb names, reasoning, disclaimer all present)
- [ ] Confirm session is purged after send (ask me to check
      `redis-cli` on the VM if you want it verified from the backend
      side, not just "the UI said so")

## Multi-language

- [ ] Switch to at least one non-English language (Hindi or Chinese are
      the best stress test — non-Latin script + the herb
      "local name (English name)" formatting)
- [ ] Confirm the language picker under the greeting and the header
      dropdown both work
- [ ] Confirm a symptom described in that language is understood
      correctly (live LLM mode, not mock keyword matching)

## Cross-cutting

- [ ] Try on a phone / narrow browser window — layout holds up
- [ ] Refresh mid-session — does it recover sensibly or just break?
- [ ] Try `https://api.naturalremedyresearch.com/healthz` directly —
      should return `{"status":"ok"}`, confirms the api subdomain is
      independently reachable
- [ ] Open dev tools Network tab once — confirm no requests are quietly
      failing (CORS errors, mixed content, etc.) even if the UI looks fine

## After testing

- [ ] Tell me what broke, if anything — I'll check VM memory/logs
      (`docker compose logs`, `free -h`) alongside whatever you saw,
      since e2-medium's headroom under real concurrent use from your
      testing hasn't been measured yet (only idle-after-startup was)
