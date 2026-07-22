"""Scoring & Ranking Agent -- pure deterministic implementation of the
confidence-score formula from application_design_v2 §7. No LLM involved.

    Score = 0.30 x Evidence Strength
          + 0.25 x Mechanism Relevance
          + 0.20 x Concentration / Bioavailability
          + 0.15 x Safety Profile (herb's general risk surface)
          + 0.10 x Traditional / Historical Use

    Adjusted Score = Score x Safety Factor (personalized, from the Safety Agent's verdict)
"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Scoring & Ranking Agent")

EVIDENCE_LEVEL_SCORES = {
    "clinical_trial": 1.0,
    "human_observational": 0.8,
    "animal_model": 0.6,
    "in_vitro_cellular": 0.3,
    "traditional_and_limited_clinical": 0.4,
    "anecdotal_traditional": 0.1,
}


class RankRequest(BaseModel):
    symptom_ids: list[str]
    candidates: list[dict]
    verdicts: list[dict]


class RankedCandidate(BaseModel):
    herb_id: str
    base_score: float
    adjusted_score: float
    confidence_band: str
    safety_factor: float


class RankResponse(BaseModel):
    ranked: list[RankedCandidate]


def _evidence_strength(herb: dict) -> float:
    return EVIDENCE_LEVEL_SCORES.get(herb.get("evidence_level", ""), 0.3)


def _mechanism_relevance(herb: dict, symptom_ids: list[str]) -> float:
    linked = set(herb.get("linked_symptoms", []))
    requested = set(symptom_ids)
    if not requested:
        return 0.3
    overlap = len(linked & requested)
    return min(overlap / len(requested), 1.0)


def _concentration_bioavailability(herb: dict) -> float:
    compounds = herb.get("compounds", [])
    return min(0.5 + 0.15 * len(compounds), 1.0)


def _safety_profile(herb: dict) -> float:
    rule_count = len(herb.get("contraindications", []))
    return max(1.0 - 0.15 * rule_count, 0.4)


def _traditional_use(herb: dict) -> float:
    return 0.8 if "traditional" in herb.get("evidence_level", "") else 0.5


def _confidence_band(adjusted_score: float) -> str:
    if adjusted_score >= 0.75:
        return "high"
    if adjusted_score >= 0.5:
        return "moderate"
    return "low"


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/scoring/rank", response_model=RankResponse)
async def rank(req: RankRequest):
    verdict_by_herb = {v["herb_id"]: v for v in req.verdicts}
    ranked: list[RankedCandidate] = []

    for herb in req.candidates:
        herb_id = herb["id"]
        base_score = (
            0.30 * _evidence_strength(herb)
            + 0.25 * _mechanism_relevance(herb, req.symptom_ids)
            + 0.20 * _concentration_bioavailability(herb)
            + 0.15 * _safety_profile(herb)
            + 0.10 * _traditional_use(herb)
        )
        verdict = verdict_by_herb.get(herb_id, {"safety_factor": 1.0, "allowed": True})
        safety_factor = verdict.get("safety_factor", 1.0)
        if not verdict.get("allowed", True):
            safety_factor = 0.0
        adjusted_score = round(base_score * safety_factor, 4)

        ranked.append(
            RankedCandidate(
                herb_id=herb_id,
                base_score=round(base_score, 4),
                adjusted_score=adjusted_score,
                confidence_band=_confidence_band(adjusted_score),
                safety_factor=safety_factor,
            )
        )

    ranked.sort(key=lambda c: c.adjusted_score, reverse=True)
    return RankResponse(ranked=ranked)
