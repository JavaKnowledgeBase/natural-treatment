"""Compound Service -- serves compound records from the Tier 1 reference cache.

Stands in for the ChEBI/PubChem validation layer described in the design doc.
"""
from fastapi import FastAPI, HTTPException

from shared import cache
from seed.load_seed import load_seed

app = FastAPI(title="Compound Service")


@app.on_event("startup")
async def _startup() -> None:
    await load_seed()


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "kb_version": await cache.get_kb_version()}


@app.get("/compounds")
async def list_compounds(ids: str | None = None):
    if ids:
        wanted = [c.strip() for c in ids.split(",") if c.strip()]
        compounds = []
        for compound_id in wanted:
            record = await cache.get_ref("compound", compound_id)
            if record is not None:
                compounds.append(record)
        return {"compounds": compounds}
    return {"compounds": await cache.list_refs("compound")}


@app.get("/compounds/{compound_id}")
async def get_compound(compound_id: str):
    compound = await cache.get_ref("compound", compound_id)
    if compound is None:
        raise HTTPException(status_code=404, detail=f"Compound '{compound_id}' not found in reference cache")
    return compound
