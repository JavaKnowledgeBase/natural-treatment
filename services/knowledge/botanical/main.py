"""Botanical Service -- serves herb records from the Tier 1 reference cache.

Stands in for the IMPPAT/KNApSAcK integration described in the design doc.
In this phase the cache is populated from the local seed bundle only; a
live-fallback external API call is a phase 2 addition (design doc §2.2).
"""
from fastapi import FastAPI, HTTPException

from shared import cache
from seed.load_seed import load_seed

app = FastAPI(title="Botanical Service")


@app.on_event("startup")
async def _startup() -> None:
    await load_seed()


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "kb_version": await cache.get_kb_version()}


@app.get("/herbs")
async def list_herbs(symptom_id: str | None = None):
    herbs = await cache.list_refs("herb")
    if symptom_id:
        herbs = [h for h in herbs if symptom_id in h.get("linked_symptoms", [])]
    return {"herbs": herbs}


@app.get("/herbs/{herb_id}")
async def get_herb(herb_id: str):
    herb = await cache.get_ref("herb", herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail=f"Herb '{herb_id}' not found in reference cache")
    return herb
