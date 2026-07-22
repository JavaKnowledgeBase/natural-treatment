"""Safety Rules Service -- serves contraindication/interaction rules from the
Tier 1 reference cache. This is the ground truth the Safety Agent checks
candidates against; it is a deterministic lookup, not an LLM judgment call
(design doc §3.2).
"""
from fastapi import FastAPI

from shared import cache
from seed.load_seed import load_seed

app = FastAPI(title="Safety Rules Service")


@app.on_event("startup")
async def _startup() -> None:
    await load_seed()


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "kb_version": await cache.get_kb_version()}


@app.get("/rules")
async def list_rules(herb_id: str | None = None):
    rules = await cache.list_refs("rule")
    if herb_id:
        rules = [r for r in rules if r["herb_id"] == herb_id]
    return {"rules": rules}
