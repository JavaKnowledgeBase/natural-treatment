"""Biochemical Mapping Agent -- symptom set -> candidate biochemical
imbalance patterns. Always grounded in the seed bundle's symptom records
(via the Toxicology/Evidence Service) so it can never invent an imbalance
outside the curated dataset; the LLM (when configured) only adds a short
plain-language reasoning summary on top of that grounded list.
"""
import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from shared import llm

TOXICOLOGY_URL = os.environ.get("TOXICOLOGY_SERVICE_URL", "http://knowledge-toxicology:8000")

app = FastAPI(title="Biochemical Mapping Agent")

SYSTEM_PROMPT = (
    "You are the biochemical mapping step of a conservative, evidence-aware herbal "
    "recommendation engine. You are given a user's reported symptoms and the candidate "
    "biochemical imbalance patterns already associated with them in a curated dataset. "
    "Write 1-3 short sentences summarizing the plausible pattern in plain language. "
    "Never claim certainty, never diagnose a disease, and never introduce an imbalance "
    "that isn't in the provided list."
)

# UI + LLM-conversation language support only (see docs/ARCHITECTURE.md) --
# the reasoning summary is the only user-visible text this agent produces.
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "zh": "Simplified Chinese",
    "fr": "French",
    "es": "Spanish",
}
DEFAULT_LANGUAGE = "en"


def _normalize_language(language: str | None) -> str:
    return language if language in LANGUAGE_NAMES else DEFAULT_LANGUAGE


def _localized_system_prompt(language: str) -> str:
    if language == DEFAULT_LANGUAGE:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + f"\n\nWrite your summary entirely in {LANGUAGE_NAMES[language]}."


class AnalyzeRequest(BaseModel):
    symptom_ids: list[str]
    language: str | None = None


class AnalyzeResponse(BaseModel):
    imbalances: list[str]
    reasoning: str | None = None


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "mock_mode": llm.MOCK_MODE}


@app.post("/mapping/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    imbalances: set[str] = set()
    symptom_names: list[str] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for symptom_id in req.symptom_ids:
            resp = await client.get(f"{TOXICOLOGY_URL}/symptoms/{symptom_id}")
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            record = resp.json()
            imbalances.update(record.get("candidate_imbalances", []))
            symptom_names.append(record["name"])

    imbalance_list = sorted(imbalances)
    language = _normalize_language(req.language)
    reasoning = await llm.complete_or_none(
        _localized_system_prompt(language),
        f"Reported symptoms: {', '.join(symptom_names) or 'none'}. "
        f"Candidate imbalance patterns from the curated dataset: {', '.join(imbalance_list) or 'none'}.",
        max_tokens=200,
    )
    if reasoning is None:
        if imbalance_list:
            reasoning = (
                f"Based on {', '.join(symptom_names)}, patterns worth exploring include "
                f"{', '.join(imbalance_list)}. This is a starter-dataset pattern match, not a diagnosis."
            )
        else:
            reasoning = "No matching patterns found yet in the starter dataset for these symptoms."

    return AnalyzeResponse(imbalances=imbalance_list, reasoning=reasoning)
