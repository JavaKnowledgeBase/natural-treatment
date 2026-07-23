"""Explanation Agent -- turns a ranked, safety-checked candidate list into
the final natural-language recommendations shown to the user. Language is
deliberately hedged ("associated with", "may support") per the design doc's
over-claiming mitigation (application_design.md §19).

Cost note: this agent used to make one Claude call per recommended herb
(up to 5 calls per single /analyze request -- by far the most Claude-call-
heavy agent in the system). It now makes a single batched call covering
every qualifying herb at once, cutting this agent's API cost by up to 5x
with no change in output quality -- same prompt content, same per-herb
constraints, just one request instead of five. If the batched call fails
or returns incomplete JSON, each missing herb falls back independently to
the deterministic template rather than failing the whole batch.
"""
import json
import re

from fastapi import FastAPI
from pydantic import BaseModel

from shared import llm

app = FastAPI(title="Explanation Agent")

TOP_N = 5

SYSTEM_PROMPT = (
    "You write one-sentence explanations for why each herb in a list was recommended, in a "
    "conservative, evidence-aware herbal recommendation engine. For every herb given to you, write "
    "exactly one sentence using hedged language such as 'associated with' or 'may support'. Never "
    "claim guaranteed efficacy, never diagnose, and mention the herb's evidence level in the sentence. "
    "\n\nRespond with strict JSON only, matching this shape: "
    '{"reasons": {"<herb_id>": "<one-sentence explanation>", ...}}. '
    "Include exactly one entry per herb id given to you, in any order."
)

# UI + LLM-conversation language support only (see docs/ARCHITECTURE.md) --
# the per-herb "reason" sentence is the only user-visible text this agent
# produces; herb *names* come from the (always-English) starter dataset and
# stay as-is (see main.py's module docstring / the conversation with the
# user about why -- botanical/traditional names carry real accuracy risk to
# mistranslate). Evidence level is different: it's an internal enum
# (EVIDENCE_LEVEL_SCORES in agent-scoring), not a proper noun, so it gets a
# real translated phrase below rather than being embedded raw -- a raw
# "human_observational" token showing up mid-sentence in a Hindi/Chinese/
# French/Spanish response reads as broken, not just anglicized.
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "zh": "Simplified Chinese",
    "fr": "French",
    "es": "Spanish",
}
DEFAULT_LANGUAGE = "en"

EVIDENCE_LEVEL_PHRASES = {
    "clinical_trial": {
        "en": "clinical trial evidence",
        "hi": "नैदानिक परीक्षण प्रमाण",
        "zh": "临床试验证据",
        "fr": "preuves d'essais cliniques",
        "es": "evidencia de ensayos clínicos",
    },
    "human_observational": {
        "en": "human observational evidence",
        "hi": "मानव अवलोकन आधारित प्रमाण",
        "zh": "人体观察性证据",
        "fr": "preuves observationnelles chez l'humain",
        "es": "evidencia observacional en humanos",
    },
    "animal_model": {
        "en": "animal model evidence",
        "hi": "पशु अध्ययन आधारित प्रमाण",
        "zh": "动物模型证据",
        "fr": "preuves issues de modèles animaux",
        "es": "evidencia de modelos animales",
    },
    "in_vitro_cellular": {
        "en": "in-vitro/cellular evidence",
        "hi": "इन-विट्रो/कोशिकीय प्रमाण",
        "zh": "体外/细胞实验证据",
        "fr": "preuves in vitro/cellulaires",
        "es": "evidencia in vitro/celular",
    },
    "traditional_and_limited_clinical": {
        "en": "traditional use with limited clinical evidence",
        "hi": "पारंपरिक उपयोग, सीमित नैदानिक प्रमाण के साथ",
        "zh": "传统用法及有限的临床证据",
        "fr": "usage traditionnel avec des preuves cliniques limitées",
        "es": "uso tradicional con evidencia clínica limitada",
    },
    "anecdotal_traditional": {
        "en": "anecdotal/traditional evidence",
        "hi": "पारंपरिक/किस्सागत प्रमाण",
        "zh": "传统经验性证据",
        "fr": "preuves anecdotiques/traditionnelles",
        "es": "evidencia anecdótica/tradicional",
    },
}


def _normalize_language(language: str | None) -> str:
    return language if language in LANGUAGE_NAMES else DEFAULT_LANGUAGE


def _evidence_level_phrase(level: str | None, language: str) -> str:
    return EVIDENCE_LEVEL_PHRASES.get(level or "", {}).get(language, level or "unreviewed")


def _localized_system_prompt(language: str) -> str:
    if language == DEFAULT_LANGUAGE:
        return SYSTEM_PROMPT
    return (
        SYSTEM_PROMPT
        + f"\n\nWrite every sentence entirely in {LANGUAGE_NAMES[language]}, even though the herb "
        f"name given to you is in English -- weave it into the sentence naturally rather than "
        f"leaving the rest of the sentence in English. The evidence level phrase given to you is "
        f"already translated into {LANGUAGE_NAMES[language]}; use it verbatim."
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


def _parse_llm_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None


async def _batched_reasons(qualifying: list[tuple[dict, dict]], language: str) -> dict[str, str]:
    """One Claude call covering every qualifying herb, instead of one call
    per herb. Returns whatever herb_id -> reason pairs it could parse;
    callers fall back to the template for any herb_id missing from the
    result (including all of them, if the call/parse fails outright)."""
    if llm.MOCK_MODE:
        return {}

    herb_lines = []
    for herb, entry in qualifying:
        mechanisms = [l.get("mechanism_summary") for l in herb.get("compounds", [])]
        evidence_phrase = _evidence_level_phrase(herb.get("evidence_level"), language)
        herb_lines.append(
            f"- id: {herb['id']}, name: {herb['name']}, evidence level: \"{evidence_phrase}\" "
            f"(use this exact phrase, already translated -- do not translate it yourself or leave "
            f"an English/internal token in its place), mechanism notes: {mechanisms}, "
            f"confidence band: {entry['confidence_band']}"
        )
    raw = await llm.complete_or_none(
        _localized_system_prompt(language),
        "Write one hedged, evidence-aware sentence for each of these herbs:\n" + "\n".join(herb_lines),
        max_tokens=180 * max(len(qualifying), 1),
    )
    if raw is None:
        return {}
    parsed = _parse_llm_json(raw)
    if parsed is None:
        return {}
    reasons = parsed.get("reasons", {})
    return reasons if isinstance(reasons, dict) else {}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "mock_mode": llm.MOCK_MODE}


@app.post("/explanation/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    herbs_by_id = {c["id"]: c for c in req.candidates}
    verdicts_by_id = {v["herb_id"]: v for v in req.verdicts}
    language = _normalize_language(req.language)

    qualifying: list[tuple[dict, dict]] = []
    for entry in req.ranked:
        if entry["adjusted_score"] <= 0:
            continue
        herb = herbs_by_id.get(entry["herb_id"])
        if herb is None:
            continue
        qualifying.append((herb, entry))
        if len(qualifying) >= TOP_N:
            break

    reasons_by_id = await _batched_reasons(qualifying, language)

    recommendations: list[dict] = []
    for herb, entry in qualifying:
        reason = reasons_by_id.get(herb["id"]) or _template_reason(herb)
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

    return GenerateResponse(recommendations=recommendations)
