# Deployment Log — Production Push (2026-07-23)

Every command actually run during the first production deployment, in
order, with the reasoning behind each choice. This is a log of what
happened, not a repeatable script — see `docs/PRODUCTION_READINESS.md` for
the plan this executed against, and `docs/DEVELOPER_GUIDE.md` for the
general "how to run this" reference.

## 1. Domain registration

Registered `naturalremedyresearch.com` via **Cloudflare Registrar**
(dashboard, not CLI — registrar purchases need a human to enter payment
info). Chosen over Squarespace (Google Domains' successor) for two
reasons: at-cost pricing (no markup) and, more importantly, putting DNS on
Cloudflare gets free TLS termination in front of the VM later via
Cloudflare's proxy — solving `PRODUCTION_READINESS.md`'s TLS/HTTPS
blocker without any extra cost or cert management on the VM itself.

## 2. Resend domain verification

Added the domain in Resend's dashboard (Domains → Add Domain →
`naturalremedyresearch.com`, region `us-east-1`), then **manual setup**
instead of Resend's "Auto configure" option — auto-configure connects
Resend to Cloudflare via OAuth with ongoing DNS write access, which is
more access than necessary for one-time record creation. Added 4 records
by hand in Cloudflare DNS instead:

| Type | Name | Purpose |
|---|---|---|
| MX | `send` | inbound handling for the SPF/bounce subdomain |
| TXT | `send` | SPF (`v=spf1 include:amazonses.com ~all`) |
| TXT | `resend._domainkey` | DKIM signing key |
| TXT | `_dmarc` | DMARC policy (`p=none`, monitoring only for now) |

None of these are proxied (Cloudflare doesn't proxy MX/TXT records
regardless). Verification is async and can take minutes to hours to
propagate.

## 3. gcloud CLI install and auth

```
winget install --id Google.CloudSDK -e --accept-source-agreements --accept-package-agreements
```

Installed via `winget` rather than the interactive GUI installer so the
whole VM-creation step could be driven by commands instead of clicking
through the GCP Console for every resource — much faster for a multi-step
job like this, and produces this log for free as a side effect.

The installed `gcloud.cmd` needs `CLOUDSDK_PYTHON` pointed at its bundled
Python explicitly in this shell (Windows doesn't have a system Python on
PATH here, and gcloud's own Python App Execution Alias shim doesn't
resolve it automatically):

```
export PATH="$PATH:/c/Users/ravi kafley/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin"
export CLOUDSDK_PYTHON="/c/Users/ravi kafley/AppData/Local/Google/Cloud SDK/google-cloud-sdk/platform/bundledpython/python.exe"
```

Then authenticated interactively (opens a browser login, cannot be done
non-interactively for a personal Google account):

```
gcloud auth login
```

## 4. Billing account setup (the messiest part of this session)

This took three attempts:

1. `gcloud billing accounts list` initially showed only a pre-existing
   **closed** account (`My Billing Account`, `OPEN: False`) — unusable.
2. User created a new billing account via the Console
   (`console.cloud.google.com/billing`), which briefly showed as a
   "Paid account" in the browser — but `gcloud billing accounts describe`
   on it returned a permission error (`billing.accounts.get` missing),
   and it didn't appear in `gcloud billing accounts list` moments later
   either. Root cause unclear (possibly an IAM/Principal Access Boundary
   policy scoping issue, possibly a transient state) — not worth
   debugging further given a clean retry was faster.
3. Created a **second** fresh billing account via Console → **+ Create
   account** (full flow: contact info, payment method — an existing
   Wells Fargo checking account already on file with the user's Google
   payments profile). This one (`0142FD-093347-83464B`, `natural remedy
   search`) showed up correctly in `gcloud billing accounts list` with
   `OPEN: True` immediately — used this one.

## 5. GCP project

```
gcloud projects list
```

Checked for an existing project to reuse first — found two unrelated
ones (`gen-lang-client-0641373435` / Default Gemini Project, and
`uploadcrj` / `new-pbs-main`, an existing PolicyMind-adjacent project).
Created a dedicated new project instead of reusing either, via Console
(`console.cloud.google.com/projectcreate`) named `natural-remedy-research`
— keeps this app's billing and IAM fully isolated from unrelated
projects, avoids any chance of cross-project quota or permission
surprises.

```
gcloud config set project natural-remedy-research
gcloud billing projects link natural-remedy-research --billing-account=0142FD-093347-83464B
```

Confirmed with:

```
gcloud billing projects describe natural-remedy-research
# billingEnabled: true
```

## 6. Enable Compute Engine API

```
gcloud services enable compute.googleapis.com --project=natural-remedy-research
```

Required before any `gcloud compute` command works on a fresh project —
APIs are off by default on new GCP projects.

## 7. Firewall rules

```
gcloud compute firewall-rules create allow-http --project=natural-remedy-research --network=default --allow=tcp:80 --target-tags=http-server --direction=INGRESS
gcloud compute firewall-rules create allow-https --project=natural-remedy-research --network=default --allow=tcp:443 --target-tags=https-server --direction=INGRESS
```

GCP does NOT auto-create these the way the Console's "Allow HTTP/HTTPS
traffic" checkboxes imply — those checkboxes just apply the
`http-server`/`https-server` network tags, and the underlying firewall
rules still need to exist for the tags to mean anything. Created
explicitly rather than relying on Console defaults, and scoped to only
80/443 — no reason to open anything wider than what the reverse proxy
(§9) will actually listen on.

## 8. VM instance

```
gcloud compute instances create app-vm \
  --project=natural-remedy-research \
  --zone=us-east1-b \
  --machine-type=e2-small \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-balanced \
  --tags=http-server,https-server \
  --metadata-from-file=startup-script=vm-startup.sh
```

Choices, each deliberate:
- **`e2-small` / `us-east1-b`**: matches `PRODUCTION_READINESS.md`'s
  settled recommendation exactly (2GB RAM, $12.23/month, confirmed under
  the $15/month budget). Region `us-east1` specifically chosen (over
  `us-central1`/`us-west1`, the other two options that doc left open) to
  sit physically close to Resend's `us-east-1` sending region, set up
  earlier this session — minor latency win on the email path, no cost
  difference between the three.
- **Ubuntu 22.04 LTS**, not Container-Optimized OS: COS has no package
  manager, which makes installing `docker-compose-plugin` (needed, since
  this app is a `docker-compose.yml` stack, not a single container)
  awkward. Ubuntu + Docker's own apt repo is the standard, well-documented
  path and matches the tooling already used locally.
- **30GB disk**: the 13-service polyglot image set (8 JVMs + 4 Python +
  Next.js) plus their build layers needs more than the 10GB image
  default; sized with headroom rather than tuning tightly on day one.
- **Startup script** (`vm-startup.sh`) installs Docker via the official
  `download.docker.com` apt repo (not the Ubuntu-bundled `docker.io`
  package, which lags upstream) and the `docker-compose-plugin` package
  (the modern `docker compose` v2 CLI plugin, not the legacy standalone
  `docker-compose` binary) — matches what's already in use on this dev
  machine, so the same compose files work unmodified.

Result: `app-vm` running at external IP `35.231.127.22`.

## 9. Getting code onto the VM (git push blocked)

Plan was `git push origin master` then `git clone` on the VM. Blocked:
Windows Credential Manager had a cached GitHub credential for an
unrelated account (`steadfast-services`) with no write access to this
repo. Deleted the stale entry (`cmdkey /delete`) and retried — GCM's
browser re-auth flow still resolved to the same account, and the user
then had trouble logging into GitHub at all (cause undetermined this
session). Rather than block deployment on unwinding a GitHub account
issue, fell back to a direct transfer:

```
git archive --format=tar HEAD | gzip > app.tar.gz
gcloud compute scp app.tar.gz app-vm:/home/kafleyravi/app.tar.gz --project=natural-remedy-research --zone=us-east1-b
gcloud compute ssh app-vm --project=natural-remedy-research --zone=us-east1-b \
  --command="mkdir -p ~/app && tar xzf ~/app.tar.gz -C ~/app"
```

`git archive` (not a raw directory copy) so only the committed tree
ships — no `.git` internals, no local build artifacts. This means the
VM's code is a point-in-time snapshot, not a git checkout: future
deploys need either a repeat of this same archive+scp step, or the
GitHub auth issue fixed so `git pull` works normally. Flagged as a
follow-up, not solved here.

## 10. JVM heap caps -- and an honest capacity check

Set explicit heap caps on all 10 Java services (the actual count, found
via `grep -rl 'ENTRYPOINT \["java", "-jar", "app.jar"\]' services/` --
`CLAUDE.md`'s "8 Java services" undercounts by 2; worth fixing there
separately):

```
ENTRYPOINT ["java", "-Xmx192m", "-XX:MaxMetaspaceSize=96m", "-XX:+UseSerialGC", "-jar", "app.jar"]
```

(`orchestrator` gets `-Xmx256m` since it coordinates every other call;
the 4 `knowledge-*` services get `-Xmx160m` since they're thin
Redis-read wrappers with the least logic. `-XX:+UseSerialGC` specifically
because it has the smallest memory overhead of any HotSpot collector --
the right trade for small, low-throughput containers where GC pause time
matters far less than baseline footprint.)

**Did the math before deploying, not after an OOM kill:** heap + capped
metaspace + thread/JIT overhead puts each JVM's worst-case RSS around
300-400MB. Across 10 services that's 3-3.5GB *before* the 4 Python
services, Next.js, Redis, and nginx -- on a 2GB `e2-small`. This is
exactly the risk `PRODUCTION_READINESS.md` §4 flagged and explicitly
left unverified ("needs to be measured on the VM directly... not assumed
correct from the plan alone").

Checked `e2-medium` (4GB) as the fallback size: no live pricing API
response came back, but GCP's e2 tier prices scale ~2x per size step,
and `e2-small` is confirmed at $12.23/mo -- so `e2-medium` should land
around $24-25/mo (matches `PRODUCTION_READINESS.md`'s own guess when it
flagged the $80.64 figure as unreliable). That's over the confirmed
$15/mo ceiling.

**Decision: deploy on `e2-small` first and measure real usage before
resizing.** The worst-case math assumes every JVM is under load
simultaneously with a full heap, which won't be true for a low-traffic
personal project most of the time. This is the actual test the
production-readiness doc called for -- resize with real numbers if it
OOMs, not by guessing upfront.

## 11. Two real build bugs found on first deploy attempt

Both only surfaced building fresh on the VM, never locally -- exactly
the value of testing a real deploy instead of assuming local-works
means prod-works.

**a) Dead `COPY` of an always-empty directory in 4 Python Dockerfiles.**
`gateway`, `agent-intake`, `agent-mapping`, `agent-explanation` each had
`COPY services/x/app ./app`, but every one of them runs `main:app`
directly via uvicorn -- nothing ever used a package under `app/`, and
the directories were empty on disk locally. Git doesn't track empty
directories, so `git archive` correctly omitted them, and the build
failed with "not found" on the VM even though it built fine locally
(where the empty directories still physically existed from old
scaffolding). Fixed by deleting the dead `COPY` lines -- this would have
broken any fresh `git clone` of the repo too, not just this deploy
method.

**b) Parallel Java builds get rate-limited/reset by Maven Central.**
`docker compose ... --build` builds all services BuildKit can
parallelize at once. Running 8 Maven builds concurrently against
`repo.maven.apache.org` (fronted by Cloudflare) caused most of them to
fail with `SSL peer shut down incorrectly` / `Remote host terminated
the handshake`. Ruled out several wrong hypotheses first by testing
directly rather than guessing:
  - Not the Docker/GCP MTU mismatch (host `ens4` is MTU 1460, Docker's
    default bridge assumes 1500) -- set `{"mtu": 1460}` in
    `/etc/docker/daemon.json` and restarted Docker; identical failure
    persisted, so this wasn't it (left the fix in place anyway, it's
    correct regardless).
  - Not a general TLS/network problem -- `curl` to the exact failing
    Maven Central URL from inside the same build image succeeded fine.
  - Not IPv6 -- this VM has no IPv6 route at all (`Network is
    unreachable`), so it wasn't a happy-eyeballs issue either.
  - A single, isolated `mvn dependency:go-offline` run (no other builds
    running concurrently) succeeded in ~28s with zero errors --
    confirming the failures only happen when many Maven processes hit
    Maven Central from this VM's IP at once.
  - `COMPOSE_PARALLEL_LIMIT=1` did **not** fix it -- current Compose's
    BuildKit-based `build` submits one combined solve graph and
    parallelizes internally regardless of that legacy env var.

**Fix**: build each service individually in a shell loop instead of one
combined `docker compose build` call, forcing genuinely sequential
builds:

```
for svc in knowledge-botanical knowledge-compound knowledge-toxicology knowledge-rules \
           agent-retrieval agent-safety agent-scoring agent-reporting email orchestrator; do
  sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build "$svc"
done
```

All 10 built clean. Slower (sequential instead of parallel) but correct
-- this is a one-time-per-deploy cost, not a runtime cost.

## 12. e2-small confirmed too small -- resized to e2-medium

Deployed clean on `e2-small` (all 17 containers "Up", Redis healthy),
but measuring immediately after showed only ~93MB available out of
1.9GB, and a follow-up `uptime` over a brand-new SSH connection timed
out after 90s -- not just the app under pressure, the whole VM was
critically overloaded, even at idle with zero real user traffic yet.
This is exactly the answer the "deploy and measure" plan was designed
to produce.

Got a real (not estimated) `e2-medium` price before resizing, since the
budget tradeoff matters: pulled the actual Compute Engine SKU catalog
via `cloudbilling.googleapis.com` (`E2 Instance Core running in
Americas` = $0.0218116/vCPU-hr, `E2 Instance Ram running in Americas` =
$0.0029235/GiB-hr -- `us-east1` isn't priced as its own city SKU, it
falls under this broader "Americas" tier). GCP's shared-core E2 types
(`micro`/`small`/`medium`) bill a *fraction* of a vCPU despite the API
reporting `guestCpus: 2` for all of them -- reverse-engineered the
exact fraction from the already-confirmed `e2-small` price ($12.23/mo
implies exactly 0.5 vCPU-equivalent billed), then applied the same
formula to `e2-medium` (1.0 vCPU-equivalent + 4GiB): **$24.46/month**,
matching to the penny what `PRODUCTION_READINESS.md` guessed when it
flagged the $80.64 figure as unreliable.

Resized in place (no data loss, same disk):

```
gcloud compute instances stop app-vm --project=natural-remedy-research --zone=us-east1-b
gcloud compute instances set-machine-type app-vm --project=natural-remedy-research --zone=us-east1-b --machine-type=e2-medium
gcloud compute instances start app-vm --project=natural-remedy-research --zone=us-east1-b
```

**External IP changed** (`35.231.127.22` -> `34.148.15.113`) since no
static IP was reserved -- worth reserving one before final DNS setup so
this doesn't happen again on a future stop/start.

## 13. Restarted on e2-medium, re-measured, DNS + TLS finalized

Stack restarted on the resized VM (images already built, no rebuild
needed). Memory this time: **1.3GB used, 2.3GB available** out of
3.8GB -- a real, comfortable margin, versus ~93MB available (and SSH
itself timing out) on `e2-small`. All 17 containers up, `nginx` and
`gateway` health-checked directly and confirmed routing correctly by
Host header for both hostnames.

**Reserved the ephemeral IP as static** before final DNS setup --
stopping/starting the VM had already changed the external IP once
(`35.231.127.22` -> `34.148.15.113`), and DNS should never have to chase
that again:

```
gcloud compute addresses create app-vm-ip --project=natural-remedy-research --region=us-east1 --addresses=34.148.15.113
```

**Cloudflare DNS**: two proxied A records, both -> `34.148.15.113`:
`naturalremedyresearch.com` (root) and `api.naturalremedyresearch.com`.
**SSL/TLS mode**: set to **Full (Strict)** (validates the origin
certificate against Cloudflare's own CA -- works because §9's cert is a
real Cloudflare Origin Certificate, not self-signed).

**Verified fully live, from outside the VM entirely** (public DNS
resolution -> real HTTPS -> real backend, not a localhost/internal
check):
- `https://naturalremedyresearch.com/` -> 200, correct page
- `https://naturalremedyresearch.com/about` -> 200
- `https://api.naturalremedyresearch.com/healthz` -> `{"status":"ok"}`
- Frontend's shipped JS bundle confirmed to contain
  `api.naturalremedyresearch.com` (the build-arg wiring from earlier
  actually took effect in what's served)
- **Full session pipeline end-to-end against the live domain**: create
  session -> send symptom message -> advance to causes -> analyze ->
  5 correctly-scored herb recommendations returned, all over real
  HTTPS through Cloudflare -> nginx -> the Java/Python backend

This is the first time this app has run as real infrastructure instead
of `docker-compose` on a laptop. Remaining open items (not blocking,
tracked in `CLAUDE.md`/`PRODUCTION_READINESS.md`): legal review of
Privacy/Terms drafts, uptime monitoring, and fixing the GitHub push
credential issue (§9) so future deploys can go back to `git pull`
instead of the archive+scp workaround.
