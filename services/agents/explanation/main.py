"""Explanation Agent -- turns a ranked, safety-checked candidate list into
the final natural-language recommendations shown to the user. Language is
deliberately hedged ("associated with", "may support") per the design doc's
over-claiming mitigation (application_design.md §19).
"""
from fastapi import FastAPI
from pydantic import BaseModel

from shared import llm

app = FastAPI(title="Explanation Agent")

TOP_N = 5

SYSTEM_PROMPT = (
    "You write one-sentence explanations for why an herb was recommended in a "
    "conservative, evidence-aware herbal recommendation engine. Use hedged language "
    "such as 'associated with' or 'may support'. Never claim guaranteed efficacy, "
    "never diagnose, and mention the evidence level. Keep it to one sentence."
)

# UI + LLM-conversation language support only (see docs/ARCHITECTURE.md) --
# the per-herb "reason" sentence is the only user-visible text this agent
# produces; herb names/evidence levels come from the (always-English)
# starter dataset and stay as-is.
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
    return (
        SYSTEM_PROMPT
        + f"\n\nWrite the sentence entirely in {LANGUAGE_NAMES[language]}, even though the herb name "
        "and evidence level given to you are in English -- weave them into the sentence naturally."
    )


class GenerateRequest(BaseModel):
    candidates: list[dict]
    ranked: list[dict]
    verdicts: list[dict]
    language: str | None = None


class GenerateResponse(BaseModel):
    recommendations: list[dict]


def _template_reason(herb: dict) -> str:
    mechanisms = [
        link.get("mechanism_summary")
        for link in herb.get("compounds", [])
        if link.get("mechanism_summary")
    ]
    mechanism_text = " ".join(mechanisms[:1]) or "supportive traditional use"
    return f"{herb['name']} contains compounds associated with {mechanism_text.rstrip('.').lower()}."


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "mock_mode": llm.MOCK_MODE}


@app.post("/explanation/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    herbs_by_id = {c["id"]: c for c in req.candidates}
    verdicts_by_id = {v["herb_id"]: v for v in req.verdicts}
    language = _normalize_language(req.language)

    recommendations: list[dict] = []
    for entry in req.ranked:
        if entry["adjusted_score"] <= 0:
            continue
        herb = herbs_by_id.get(entry["herb_id"])
        if herb is None:
            continue

        reason = await llm.complete_or_none(
            _localized_system_prompt(language),
            f"Herb: {herb['name']}. Evidence level: {herb.get('evidence_level')}. "
            f"Mechanism notes: {[l.get('mechanism_summary') for l in herb.get('compounds', [])]}. "
            f"Confidence band: {entry['confidence_band']}.",
            max_tokens=120,
        )
        if reason is None:
            reason = _template_reason(herb)

        verdict = verdicts_by_id.get(herb["id"], {})
        safety_note = "; ".join(verdict.get("notes", [])) or None

        recommendations.append(
            {
                "herb_id": herb["id"],
                "herb_name": herb["name"],
                "score": entry["adjusted_score"],
                "confidence_band": entry["confidence_band"],
                "reason": reason,
                "evidence_level": herb.get("evidence_level"),
                "safety_note": safety_note,
                "curation_status": herb.get("curation_status", "starter_dataset_unreviewed"),
            }
        )
        if len(recommendations) >= TOP_N:
            break

    return GenerateResponse(recommendations=recommendations)
