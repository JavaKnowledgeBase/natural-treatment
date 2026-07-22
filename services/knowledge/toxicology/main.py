"""Toxicology/Evidence Service -- serves symptom -> candidate-imbalance
records from the Tier 1 reference cache.

Stands in for the Comparative Toxicogenomics Database (CTD) integration
described in the design doc: linking compounds/imbalances to phenotypes.
"""
from fastapi import FastAPI, HTTPException

from shared import cache
from seed.load_seed import load_seed

app = FastAPI(title="Toxicology / Evidence Service")


@app.on_event("startup")
async def _startup() -> None:
    await load_seed()


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "kb_version": await cache.get_kb_version()}


@app.get("/symptoms")
async def list_symptoms(query: str | None = None):
    symptoms = await cache.list_refs("symptom")
    if query:
        needle = query.lower()
        symptoms = [
            s for s in symptoms
            if needle in s["name"].lower() or needle in s["id"].lower()
        ]
    return {"symptoms": symptoms}


@app.get("/symptoms/{symptom_id}")
async def get_symptom(symptom_id: str):
    symptom = await cache.get_ref("symptom", symptom_id)
    if symptom is None:
        raise HTTPException(status_code=404, detail=f"Symptom '{symptom_id}' not found in reference cache")
    return symptom


@app.get("/symptoms/{symptom_id}/related")
async def get_related_symptoms(symptom_id: str):
    symptom = await cache.get_ref("symptom", symptom_id)
    if symptom is None:
        raise HTTPException(status_code=404, detail=f"Symptom '{symptom_id}' not found in reference cache")
    related = []
    for related_id in symptom.get("related_symptom_ids", []):
        record = await cache.get_ref("symptom", related_id)
        if record is not None:
            related.append(record)
    return {"related": related}
