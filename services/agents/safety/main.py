"""Safety / Guardrail Agent -- deterministic contraindication checking.

Deliberately independent from the Scoring Agent (design doc §3.2): this
service never uses an LLM to decide whether something is safe. It matches
the user's *volunteered* profile fields against the ground-truth rules from
the Safety Rules Service. If the user hasn't volunteered anything (the
common case, since nothing in this system asks), every rule simply fails to
match and the herb passes through unpenalized.
"""
import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

RULES_SERVICE_URL = os.environ.get("RULES_SERVICE_URL", "http://knowledge-rules:8000")

app = FastAPI(title="Safety / Guardrail Agent")

SEVERITY_TO_FACTOR = {"moderate": 0.6, "high": 0.2, "disallowed": 0.0}

CONDITION_KEYWORDS = {
    "thyroid_disorder": ["thyroid"],
    "hormone_sensitive_condition": ["hormone", "estrogen", "breast cancer", "endometriosis", "pcos"],
    "autoimmune_condition": ["autoimmune", "lupus", "rheumatoid", "hashimoto", "crohn", "multiple sclerosis"],
    "kidney_disease": ["kidney", "renal"],
    "hypertension": ["hypertension", "high blood pressure"],
    "gerd": ["gerd", "acid reflux", "heartburn"],
    "gallstones": ["gallstone", "gallbladder"],
    "bipolar_disorder": ["bipolar"],
    "cardiac_medication": ["heart medication", "cardiac", "beta blocker", "heart failure"],
    "anticoagulant_medication": ["blood thinner", "anticoagulant", "warfarin", "aspirin", "heparin", "clopidogrel"],
    "sedative_medication": ["sedative", "benzodiazepine", "sleep aid", "ambien", "xanax", "valium"],
}
PEDIATRIC_MARKERS = ["child", "kid", "infant", "toddler", "teen", "minor"]


class EvaluateRequest(BaseModel):
    candidates: list[dict]
    profile: dict = {}


class Verdict(BaseModel):
    herb_id: str
    allowed: bool
    safety_factor: float
    rules_fired: list[str] = []
    notes: list[str] = []


class EvaluateResponse(BaseModel):
    verdicts: list[Verdict]


def _profile_haystack(profile: dict) -> str:
    parts = list(profile.get("medications", []) or [])
    parts += list(profile.get("chronic_conditions", []) or [])
    return " | ".join(parts).lower()


def _condition_matches(condition: str, profile: dict, haystack: str) -> bool:
    if condition == "pregnancy":
        status = (profile.get("pregnancy_status") or "").lower()
        return bool(status) and "not" not in status and "pregnant" in status
    if condition == "pediatric":
        age_range = (profile.get("age_range") or "").lower()
        return any(marker in age_range for marker in PEDIATRIC_MARKERS)
    keywords = CONDITION_KEYWORDS.get(condition, [])
    return any(keyword in haystack for keyword in keywords)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/safety/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{RULES_SERVICE_URL}/rules")
        resp.raise_for_status()
        all_rules = resp.json()["rules"]

    rules_by_herb: dict[str, list[dict]] = {}
    for rule in all_rules:
        rules_by_herb.setdefault(rule["herb_id"], []).append(rule)

    haystack = _profile_haystack(req.profile)
    verdicts: list[Verdict] = []

    for herb in req.candidates:
        herb_id = herb["id"]
        fired: list[dict] = [
            rule for rule in rules_by_herb.get(herb_id, [])
            if _condition_matches(rule["condition"], req.profile, haystack)
        ]

        if not fired:
            verdicts.append(Verdict(herb_id=herb_id, allowed=True, safety_factor=1.0))
            continue

        worst = max(fired, key=lambda r: SEVERITY_TO_FACTOR.get(r["severity"], 1.0) * -1)
        safety_factor = SEVERITY_TO_FACTOR.get(worst["severity"], 1.0)
        verdicts.append(
            Verdict(
                herb_id=herb_id,
                allowed=worst["severity"] != "disallowed",
                safety_factor=safety_factor,
                rules_fired=[r["id"] for r in fired],
                notes=[r["note"] for r in fired],
            )
        )

    return EvaluateResponse(verdicts=verdicts)
