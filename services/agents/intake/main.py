"""Intake Agent -- drives the conversational flow from application_design.md
§12.5: greeting, symptom-collection loop, cause-collection loop.

Hard product rule (set by the user this build): this agent must never
proactively ask for personal details (age, pregnancy, medications,
allergies, chronic conditions). It only ever *extracts* those fields from
free text the user volunteers unprompted -- it never prompts for them. The
only explicit ask for contact info anywhere in this system is the opt-in
"email me this" action after results are shown, which lives in the
reporting/email flow, not here.
"""
import json
import os
import re

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from shared import llm

TOXICOLOGY_URL = os.environ.get("TOXICOLOGY_SERVICE_URL", "http://knowledge-toxicology:8000")
MAX_SUGGESTIONS = 4

app = FastAPI(title="Intake Agent")

_catalog_cache: list[dict] | None = None

SYSTEM_PROMPT = """You are the conversational intake agent for a conservative, evidence-aware \
herbal recommendation app. You help the user describe how they're feeling in a natural \
conversation, not a form.

Hard rules:
- NEVER ask the user for age, pregnancy status, medications, allergies, or medical conditions.
- If the user mentions any of those unprompted, silently record them in extracted_profile -- \
do not comment on it or ask follow-up questions about it.
- Only suggest symptoms/causes from the provided catalog. Never invent new ones.
- Keep assistant_message short, warm, and conversational (1-2 sentences).

Respond with strict JSON only, matching this shape:
{"assistant_message": str, "matched": [str], "suggestions": [str], "extracted_profile": {}}
For a symptom turn: "matched" are catalog ids the user's message directly describes; "suggestions" \
are up to 4 catalog ids worth offering next (related, not already known).
For a cause turn: "matched" are short cause labels the user's message directly describes (free text, \
not a fixed catalog); "suggestions" are up to 4 related cause labels worth offering next.
"extracted_profile" may include any of: age_range, pregnancy_status, medications (list), \
allergies (list), chronic_conditions (list) -- only if volunteered, otherwise omit entirely."""


class GreetingResponse(BaseModel):
    message: str


class SymptomTurnRequest(BaseModel):
    user_message: str
    known_symptom_ids: list[str] = []


class CauseTurnRequest(BaseModel):
    user_message: str
    known_cause_labels: list[str] = []


class TurnResponse(BaseModel):
    assistant_message: str
    matched: list[dict] = []
    suggestions: list[dict]
    extracted_profile: dict = {}


CAUSE_CATEGORIES = ["stress", "diet", "sleep", "environment", "exposure", "routine"]
CAUSE_KEYWORDS = {
    "stress": ["stress", "work", "deadline", "anxious", "overwhelm"],
    "diet": ["ate", "food", "diet", "meal", "skipped meal", "sugar", "alcohol"],
    "sleep": ["sleep", "insomnia", "late night", "tired"],
    "environment": ["pollen", "weather", "travel", "allergen", "dust"],
    "exposure": ["chemical", "smoke", "toxin", "paint", "mold"],
    "routine": ["schedule", "routine", "sitting", "sedentary", "screen"],
}
PREGNANCY_MARKERS = ["pregnant", "pregnancy"]
MEDICATION_MARKERS = ["blood thinner", "warfarin", "aspirin daily", "beta blocker", "sedative", "antidepressant"]


async def _catalog() -> list[dict]:
    global _catalog_cache
    if _catalog_cache is None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{TOXICOLOGY_URL}/symptoms")
            resp.raise_for_status()
            _catalog_cache = resp.json()["symptoms"]
    return _catalog_cache


def _extract_profile_hints(text: str) -> dict:
    lower = text.lower()
    extracted: dict = {}
    if any(m in lower for m in PREGNANCY_MARKERS) and "not pregnant" not in lower:
        extracted["pregnancy_status"] = "pregnant (volunteered by user)"
    meds = [m for m in MEDICATION_MARKERS if m in lower]
    if meds:
        extracted["medications"] = meds
    return extracted


STOPWORDS = {"chronic", "occasional", "seasonal", "poor", "low", "high", "mild", "and", "or", "of", "the", "to", "a", "an"}


def _significant_words(phrase: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", phrase.lower()) if w not in STOPWORDS and len(w) > 2]


def _word_matches_text(word: str, text: str) -> bool:
    # Tolerates simple singular/plural mismatches, e.g. catalog "headaches" vs
    # user text "headache" -- stripping the catalog word's trailing 's' means
    # its stem is a substring of the user's text either way.
    stem = word[:-1] if word.endswith("s") and len(word) > 4 else word
    return stem in text


def _symptom_matches(symptom: dict, text: str) -> bool:
    words = _significant_words(symptom["name"]) or _significant_words(symptom["id"].replace("_", " "))
    return any(_word_matches_text(w, text) for w in words)


def _mock_symptom_turn(text: str, catalog: list[dict], known_ids: list[str]) -> TurnResponse:
    lower = text.lower()
    matched = [s for s in catalog if s["id"] not in known_ids and _symptom_matches(s, lower)]
    matched_ids = [s["id"] for s in matched] or known_ids

    related_ids: list[str] = []
    for symptom_id in matched_ids:
        record = next((s for s in catalog if s["id"] == symptom_id), None)
        if not record:
            continue
        for related_id in record.get("related_symptom_ids", []):
            if related_id not in known_ids and related_id not in related_ids:
                related_ids.append(related_id)

    suggestions = [
        {"id": s["id"], "label": s["name"]}
        for s in catalog if s["id"] in related_ids
    ][:MAX_SUGGESTIONS]

    if matched:
        message = "Thanks for sharing that. A few other things people in similar situations sometimes notice -- any of these sound familiar?"
    elif suggestions:
        message = "Got it. Here are a few related things worth checking -- feel free to pick any that apply, or skip."
    else:
        message = "Thanks for sharing. Tell me a bit more about how you're feeling whenever you're ready, or select from what's already listed."

    matched_out = [{"id": s["id"], "label": s["name"]} for s in matched]
    return TurnResponse(
        assistant_message=message,
        matched=matched_out,
        suggestions=suggestions,
        extracted_profile=_extract_profile_hints(text),
    )


def _mock_cause_turn(text: str, known_labels: list[str]) -> TurnResponse:
    lower = text.lower()
    matched_category = "routine"
    suggestions = []
    for category, keywords in CAUSE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            matched_category = category
            for k in keywords[:2]:
                label = k.capitalize()
                if label not in known_labels:
                    suggestions.append({"label": label, "category": category})
        if len(suggestions) >= MAX_SUGGESTIONS:
            break

    message = (
        "Thanks -- that helps build the picture. Any of these related factors also apply?"
        if suggestions else
        "Noted. Share anything else that might have contributed, whenever you're ready."
    )
    matched = [{"label": text.strip(), "category": matched_category}] if text.strip() else []
    return TurnResponse(
        assistant_message=message,
        matched=matched,
        suggestions=suggestions[:MAX_SUGGESTIONS],
        extracted_profile=_extract_profile_hints(text),
    )


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


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "mock_mode": llm.MOCK_MODE}


@app.get("/intake/greeting", response_model=GreetingResponse)
async def greeting():
    return GreetingResponse(message="Hello! How are you feeling today?")


@app.post("/intake/symptom-turn", response_model=TurnResponse)
async def symptom_turn(req: SymptomTurnRequest):
    catalog = await _catalog()

    if llm.MOCK_MODE:
        return _mock_symptom_turn(req.user_message, catalog, req.known_symptom_ids)

    catalog_desc = "\n".join(f"- {s['id']}: {s['name']}" for s in catalog if s["id"] not in req.known_symptom_ids)
    raw = await llm.complete_or_none(
        SYSTEM_PROMPT,
        f"Symptom catalog (id: name):\n{catalog_desc}\n\nAlready known symptoms: {req.known_symptom_ids}\n\n"
        f"User just said: \"{req.user_message}\"",
        max_tokens=400,
    )
    parsed = _parse_llm_json(raw) if raw else None
    if parsed is None:
        return _mock_symptom_turn(req.user_message, catalog, req.known_symptom_ids)

    id_to_name = {s["id"]: s["name"] for s in catalog}
    matched = [
        {"id": sid, "label": id_to_name[sid]}
        for sid in parsed.get("matched", [])
        if sid in id_to_name
    ]
    suggestions = [
        {"id": sid, "label": id_to_name[sid]}
        for sid in parsed.get("suggestions", [])
        if sid in id_to_name and sid not in req.known_symptom_ids
    ][:MAX_SUGGESTIONS]
    return TurnResponse(
        assistant_message=parsed.get("assistant_message", "Thanks for sharing."),
        matched=matched,
        suggestions=suggestions,
        extracted_profile=parsed.get("extracted_profile", {}),
    )


@app.post("/intake/cause-turn", response_model=TurnResponse)
async def cause_turn(req: CauseTurnRequest):
    if llm.MOCK_MODE:
        return _mock_cause_turn(req.user_message, req.known_cause_labels)

    raw = await llm.complete_or_none(
        SYSTEM_PROMPT,
        f"Cause categories: {CAUSE_CATEGORIES}\nAlready known causes: {req.known_cause_labels}\n\n"
        f"User just said: \"{req.user_message}\"\n\n"
        f"For this turn, 'suggestions' should be short cause/contributing-factor labels (not catalog ids).",
        max_tokens=400,
    )
    parsed = _parse_llm_json(raw) if raw else None
    if parsed is None:
        return _mock_cause_turn(req.user_message, req.known_cause_labels)

    suggestions = [
        {"label": s, "category": "routine"} if isinstance(s, str) else s
        for s in parsed.get("suggestions", [])
    ][:MAX_SUGGESTIONS]
    matched = [
        {"label": s, "category": "routine"} if isinstance(s, str) else s
        for s in parsed.get("matched", [])
    ]
    return TurnResponse(
        assistant_message=parsed.get("assistant_message", "Noted, thank you."),
        matched=matched,
        suggestions=suggestions,
        extracted_profile=parsed.get("extracted_profile", {}),
    )
