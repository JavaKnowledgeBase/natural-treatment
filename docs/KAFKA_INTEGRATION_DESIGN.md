# Kafka Integration Design — not implemented, deferred by design

**Status: planning only, nothing in this document has been built.** Written
2026-07-23 to give a concrete answer to "if this app used Kafka, where and
how would it actually fit" — both so a real future need has a starting
point instead of a blank page, and because working through a genuine,
codebase-grounded design is itself the more honest way to build Kafka
fluency than a generic tutorial. Pairs with the interview-prep reference
document this design informed (see the user's `Desktop/resume/` prep
folder).

This extends, rather than replaces, the one sentence already in
`research docs/application_design_v2_microservices_agentic.md` (§Async
messaging, phase 2): *"if agent fan-out volume grows, replace direct
service-to-service calls with a lightweight queue (Redis Streams for MVP;
Kafka/SQS if cross-region or very high throughput is needed later)."* That
sentence named Kafka as an option; this document is the actual design work
behind deciding *where* it would go and *why*, not just that it's an
option.

## 1. Honest scope check first

This app runs as a single VM, single region, low/sporadic traffic, funded
by a future donation mechanism, not a funded product with real throughput.
Nothing about its current or realistically near-future traffic shape
needs Kafka. Introducing a Kafka cluster today would mean real, ongoing
operational cost — brokers to run and monitor, partition/replication
planning, a schema registry if done properly — with no traffic-driven
justification behind it. That's the actual reason this stays a design
document and not a merge: **the trigger condition from the v2 doc has
never fired.** This section exists so that judgment is explicit and
revisitable, not implicit and forgotten.

## 2. Where Kafka would *not* go — the synchronous `/analyze` chain

`OrchestratorService.analyze()`'s five-stage pipeline (mapping →
retrieval → safety → scoring → explanation, `docs/ARCHITECTURE.md` /
the technical walkthrough §4) is a **genuine sequential data dependency**:
each stage's output is the next stage's input, within one user's one
HTTP request, and the user is waiting synchronously for a response.
Putting Kafka between these stages would not add real decoupling value —
there is exactly one producer and exactly one consumer per hop, no fan-out
to multiple independent consumers, no need for replay, and no traffic
spike this app has ever seen that synchronous HTTP calls with existing
timeouts (`docs/API_REFERENCE.md` §Resiliency) can't already handle. Kafka
would add latency (at least one broker round-trip per hop) and a much
harder-to-reason-about failure mode (a stuck consumer group instead of a
timed-out HTTP call) for zero benefit here. Naming this explicitly matters
for an interview answer too: **recognizing where a message broker does
*not* belong is as much the skill as knowing where it does.**

## 3. Where Kafka genuinely *would* fit — aggregate analytics events

The one place in this app's own design docs that already describes a
Kafka-shaped problem is `application_design_v2_microservices_agentic.md`
§Observability: *"metrics should be aggregate-only (e.g. 'sessions
completed,' 'safety rule X fired N times')."* That's:

- **Fire-and-forget** from the producer's perspective — the orchestrator
  doesn't need to wait for or care whether an analytics consumer received
  the event, unlike every hop in the `/analyze` chain above.
- **Genuinely fan-out shaped** — today it's "feed a metrics dashboard,"
  but a real production version of this app would plausibly also want a
  separate consumer for, say, alerting when a specific safety rule fires
  unusually often (a signal the seed data might have a real accuracy
  problem), without the analytics-dashboard consumer and the alerting
  consumer needing to know about each other.
- **Naturally decoupled from the ephemeral-data promise** — Tier 2
  session data is hard-purged (`docs/ARCHITECTURE.md` §Data model); an
  event stream of pre-aggregated, PII-free counters (`safety_rule_fired`,
  `session_completed`, `recommendation_shown`) is a completely separate,
  intentionally retained data path that never touches the ephemeral
  session data it's derived from.

### Concrete design

**Producer**: `orchestrator` (Java), publishing at exactly four points
already present in its existing code paths — no new business logic, just
a publish call added where these transitions already happen:

| Event | Publish point | Key |
|---|---|---|
| `session.created` | `OrchestratorService.createSession()` | session language (not session ID — see §4) |
| `analysis.completed` | end of `analyze()`, after `cache.setStep(sid, "results")` | symptom category (not session ID) |
| `safety.rule_fired` | inside `analyze()`, once per fired verdict from `agents.safety` | `rule_id` |
| `session.purged` | `SessionCacheService.purgeSession()`, after purge confirmed | none (aggregate counter only) |

**Topic**: one topic, `nrr.analytics.v1`, not four — these are all
low-volume, schema-related events sharing one evolving event-type
envelope (`{event_type, timestamp, ...fields}`), and four separate topics
for a stream this size would be needless operational overhead for no
real isolation benefit. **Partitions: 3** — enough to allow horizontal
consumer scaling later without needing to guess a bigger number now
(partition count is one of the few things genuinely expensive to change
after the fact; 3 is a deliberate, modest starting point, not an
arbitrary one). **Partition key: event type** (`rule_id` for
`safety.rule_fired`, a fixed constant per event type otherwise) — this
groups same-type events for in-order processing per type, which is the
only ordering guarantee this use case actually needs; there is no
requirement to keep two *different* event types in relative order.
**Replication factor: 3** (matches this app's own stated default
preference, see the ISR discussion in the paired interview reference
doc) if this ever runs as a real multi-broker cluster; a realistic
single-VM deployment of this scale would more likely run Kafka in
KRaft combined mode with 3 controller/broker nodes total, not the
classic 5+ node production topology, given the traffic volume this
specific topic would ever see.

**Consumer(s)**: a new, genuinely optional service, `analytics-consumer`
(Java, Spring Kafka), materializing running counters into... Redis, kept
consistent with the "Redis is the only stateful component" architectural
commitment (`docs/ARCHITECTURE.md`) rather than introducing a second
storage technology just for this. Consumer group `nrr-analytics`, single
instance to start (3 partitions is headroom for later, not a requirement
to run 3 consumers now).

**Retention**: 7 days, time-based (not compacted — these are point-in-time
counters to aggregate, not current-state-per-key records; log compaction,
covered in the interview reference doc, is the wrong retention model
here). Short retention is a deliberate choice matching the app's existing
data-minimization posture, not an oversight.

**Delivery semantics**: at-least-once producer (`acks=all`), idempotent
consumer via a Redis `INCR` (naturally idempotent for the counter
aggregation this is being used for — a duplicate `safety_rule_fired`
event just needs deduplication if double-counting genuinely matters,
which for approximate operational metrics it likely doesn't, a call
worth stating as a deliberate scope decision rather than an oversight if
asked in an interview context).

## 4. Privacy discipline this design must preserve

**No session ID, no symptom text, no herb names, no user-identifying
value of any kind goes into this topic or any event on it.** This is not
a nice-to-have; it is the same non-negotiable line the rest of this
app's design already draws (`docs/ARCHITECTURE.md`, `CLAUDE.md`'s privacy
section). A Kafka topic with 7-day retention *is* a new, non-ephemeral
data store the moment anything sensitive lands in it — the entire value
of the ephemeral-session-data design elsewhere in this app would be
undermined by a badly-scoped analytics event. Every event schema in §3
above was chosen specifically to contain only pre-aggregated categories
(a symptom *category*, a rule *ID*, a language code) never raw
user-submitted content.

## 5. What would actually trigger building this

Not "nice to have," a real, specific, checkable condition:

- Real, sustained traffic where a synchronous dashboard query against
  Redis Tier 2 (today's only option, if anyone wanted this data at all
  right now) becomes a measurable load concern, **or**
- A genuine second, independent consumer need materializes (e.g., real
  alerting on anomalous safety-rule firing rates) that a simple polling
  query can't serve as well as an event stream can, **or**
- Multi-region deployment, which is the exact condition the original v2
  design doc named for Kafka specifically over the Redis Streams MVP
  option.

None of these are true today. This document exists so that the next time
one of them is, the design work doesn't start from zero.
