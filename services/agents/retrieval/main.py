"""Knowledge Retrieval Agent -- expands symptoms/imbalances into candidate
herbs by calling the Botanical, Compound, and Toxicology/Evidence knowledge
services. No direct external API calls in this phase (design doc §2.2's
live-fallback path is a phase 2 addition) -- everything here reads from the
seed-backed Tier 1 cache via the knowledge services.
"""
import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

BOTANICAL_URL = os.environ.get("BOTANICAL_SERVICE_URL", "http://knowledge-botanical:8000")
COMPOUND_URL = os.environ.get("COMPOUND_SERVICE_URL", "http://knowledge-compound:8000")

app = FastAPI(title="Knowledge Retrieval Agent")


class CandidatesRequest(BaseModel):
    symptom_ids: list[str]
    imbalances: list[str] = []


class CandidatesResponse(BaseModel):
    candidates: list[dict]


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/retrieval/candidates", response_model=CandidatesResponse)
async def candidates(req: CandidatesRequest):
    herbs_by_id: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for symptom_id in req.symptom_ids:
            resp = await client.get(f"{BOTANICAL_URL}/herbs", params={"symptom_id": symptom_id})
            resp.raise_for_status()
            for herb in resp.json()["herbs"]:
                herbs_by_id[herb["id"]] = herb

        compound_ids = sorted({
            link["compound_id"]
            for herb in herbs_by_id.values()
            for link in herb.get("compounds", [])
        })
        compound_records: dict[str, dict] = {}
        if compound_ids:
            resp = await client.get(f"{COMPOUND_URL}/compounds", params={"ids": ",".join(compound_ids)})
            resp.raise_for_status()
            compound_records = {c["id"]: c for c in resp.json()["compounds"]}

    for herb in herbs_by_id.values():
        for link in herb.get("compounds", []):
            record = compound_records.get(link["compound_id"])
            if record:
                link["mechanism_summary"] = record.get("mechanism_summary")

    return CandidatesResponse(candidates=list(herbs_by_id.values()))
