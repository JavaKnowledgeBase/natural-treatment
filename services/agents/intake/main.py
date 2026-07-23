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

# UI + LLM-conversation language support only (see docs/ARCHITECTURE.md) --
# backend catalog matching (mock-mode keyword matching below) stays
# English-only regardless of the requested language; only the live-Claude
# path actually responds in a non-English language.
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "zh": "Simplified Chinese",
    "fr": "French",
    "es": "Spanish",
}
DEFAULT_LANGUAGE = "en"

GREETINGS = {
    "en": "Hello! How are you feeling today?",
    "hi": "नमस्ते! आज आप कैसा महसूस कर रहे हैं?",
    "zh": "您好！您今天感觉怎么样？",
    "fr": "Bonjour ! Comment vous sentez-vous aujourd'hui ?",
    "es": "¡Hola! ¿Cómo te sientes hoy?",
}

# Mock mode's fixed templates, translated per language so the assistant's
# own phrasing matches the selected UI language even without a live LLM
# call. Matching itself (_symptom_matches/CAUSE_KEYWORDS below) stays
# English-keyword-only regardless -- translating *what the catalog contains*
# is a bigger, separate effort (see docs/ARCHITECTURE.md); this only fixes
# the mismatch where the assistant's own words were English no matter what
# language the user picked.
MOCK_SYMPTOM_MATCHED = {
    "en": "Thank you for sharing that. A few other things people often notice alongside it -- do any of these feel familiar too?",
    "hi": "यह बताने के लिए धन्यवाद। अक्सर इसके साथ कुछ और चीज़ें भी महसूस होती हैं -- क्या इनमें से कोई आपको भी परिचित लगती है?",
    "zh": "谢谢您告诉我这些。人们常常还会注意到一些相关的情况 —— 以下有没有哪些您也觉得眼熟？",
    "fr": "Merci de me l'avoir dit. On remarque souvent d'autres choses en parallèle -- est-ce que l'une d'elles vous semble familière ?",
    "es": "Gracias por contármelo. A menudo la gente nota otras cosas junto con esto -- ¿alguna de estas te resulta familiar?",
}
MOCK_SYMPTOM_SUGGESTIONS_ONLY = {
    "en": "Got it, thank you. Here are a few related things that sometimes go together -- feel free to pick any that fit, or just skip ahead.",
    "hi": "समझ गई, धन्यवाद। यहाँ कुछ जुड़ी हुई बातें हैं जो अक्सर साथ होती हैं -- जो आपको सही लगे उसे चुनें, या आगे बढ़ जाएँ।",
    "zh": "明白了，谢谢您。以下是一些常常相关联的情况 —— 欢迎选择符合您情况的，或者直接跳过。",
    "fr": "D'accord, merci. Voici quelques éléments liés qui vont parfois de pair -- n'hésitez pas à choisir ceux qui correspondent, ou à passer directement à la suite.",
    "es": "Entendido, gracias. Aquí tienes algunas cosas relacionadas que a veces van juntas -- elige las que apliquen, o simplemente continúa.",
}
MOCK_SYMPTOM_NO_MATCH = {
    "en": "Thank you for telling me that. I want to make sure I understand -- could you say a bit more, like where you feel it, when it started, or what makes it better or worse?",
    "hi": "यह बताने के लिए धन्यवाद। मैं ठीक से समझना चाहती हूँ -- क्या आप थोड़ा और बता सकते हैं, जैसे यह कहाँ महसूस होता है, कब शुरू हुआ, या किस चीज़ से यह बेहतर या बदतर होता है?",
    "zh": "谢谢您告诉我这些。为了更好地理解，能否再多说一些？比如具体是哪里不舒服、什么时候开始的，或者什么情况下会好一些或更严重？",
    "fr": "Merci de me l'avoir dit. Je veux être sûr(e) de bien comprendre -- pourriez-vous m'en dire un peu plus, par exemple où vous le ressentez, quand cela a commencé, ou ce qui l'améliore ou l'aggrave ?",
    "es": "Gracias por contármelo. Quiero asegurarme de entenderlo bien -- ¿podrías contarme un poco más, como dónde lo sientes, cuándo comenzó, o qué lo mejora o empeora?",
}
MOCK_CAUSE_SUGGESTIONS = {
    "en": "Thank you, that helps me understand the bigger picture. Do any of these related factors sound like they apply too?",
    "hi": "धन्यवाद, इससे मुझे पूरी तस्वीर समझने में मदद मिलती है। क्या इनमें से कोई जुड़ा हुआ कारण भी आप पर लागू होता है?",
    "zh": "谢谢您，这有助于我了解更全面的情况。以下这些相关因素中，有没有也适用于您的？",
    "fr": "Merci, cela m'aide à mieux comprendre l'ensemble de la situation. Est-ce que l'un de ces facteurs liés s'applique aussi à vous ?",
    "es": "Gracias, eso me ayuda a entender el panorama completo. ¿Alguno de estos factores relacionados también aplica en tu caso?",
}
MOCK_CAUSE_NO_SUGGESTIONS = {
    "en": "Thank you for sharing that. Whenever you're ready, feel free to add anything else that might have played a role.",
    "hi": "यह साझा करने के लिए धन्यवाद। जब भी आप तैयार हों, कोई और बात जो इसमें भूमिका निभा सकती हो, बेझिझक बताइए।",
    "zh": "谢谢您的分享。准备好之后，欢迎补充任何可能相关的其他情况。",
    "fr": "Merci de l'avoir partagé. Quand vous serez prêt(e), n'hésitez pas à ajouter tout autre élément qui aurait pu jouer un rôle.",
    "es": "Gracias por compartir eso. Cuando quieras, no dudes en añadir cualquier otra cosa que pueda haber influido.",
}


def _normalize_language(language: str | None) -> str:
    return language if language in LANGUAGE_NAMES else DEFAULT_LANGUAGE


# Many users don't have a native-script keyboard and will type their
# selected language phonetically in the Latin alphabet instead (e.g. Hindi
# written as "mujhe sar dard hai" instead of Devanagari, or Chinese typed
# in Pinyin). This is normal input in that language, not English and not a
# different language -- only languages that don't already use Latin script
# need the note.
TRANSLITERATION_NOTES = {
    "hi": (
        "Many users typing Hindi won't have a Devanagari keyboard and will write phonetically in "
        "the Latin alphabet instead (e.g. \"mujhe sar dard hai\" for \"मुझे सर दर्द है\"). Treat "
        "Romanized/Hinglish text like this as ordinary Hindi input, not English and not a mix -- "
        "interpret it by sound/meaning the way a Hindi speaker texting a friend would, and still "
        "reply in proper Devanagari script yourself."
    ),
    "zh": (
        "Many users typing Chinese won't have a Chinese input method available and will write "
        "phonetically in Pinyin instead (e.g. \"tou teng\" for \"头疼\"), often without tone marks. "
        "Treat Pinyin text like this as ordinary Chinese input, not English -- interpret it by sound/"
        "meaning, and still reply in proper Chinese characters yourself."
    ),
}


def _localized_system_prompt(language: str) -> str:
    if language == DEFAULT_LANGUAGE:
        return SYSTEM_PROMPT
    name = LANGUAGE_NAMES[language]
    prompt = (
        SYSTEM_PROMPT
        + f"\n\nRespond in {name}: \"assistant_message\" must be written entirely in {name}. "
        "For a symptom turn, \"matched\" and \"suggestions\" must stay the exact English catalog ids "
        "given to you (e.g. \"chronic_headaches\") -- those are looked up against a fixed, "
        "English-keyed catalog and are never shown to the user verbatim, so translating them would "
        f"break the lookup. For a cause turn, \"matched\" and \"suggestions\" are free text with no "
        f"fixed catalog, so write those labels in {name} too, matching the conversation."
    )
    if language in TRANSLITERATION_NOTES:
        prompt += "\n\n" + TRANSLITERATION_NOTES[language]
    return prompt

SYSTEM_PROMPT = """You are the conversational intake agent for a conservative, evidence-aware \
herbal recommendation app. You help the user describe how they're feeling in a natural \
conversation, not a form.

Hard rules:
- NEVER ask the user for age, pregnancy status, medications, allergies, or medical conditions.
- If the user mentions any of those unprompted, silently record them in extracted_profile -- \
do not comment on it or ask follow-up questions about it.
- Only suggest symptoms/causes from the provided catalog. Never invent new ones.
- Keep assistant_message short, warm, and conversational (1-2 sentences), using natural contractions \
("that's", "you're") rather than stiff or clinical phrasing.
- Always acknowledge what the user just shared before asking anything else -- a brief "thank you for \
sharing that" or similar goes a long way.
- Never expose internal implementation details to the user -- no mentioning a "catalog," "dataset," \
or "list" of symptoms. If nothing in the catalog matches, just ask a warm, curious follow-up question \
about what they described instead (e.g. where it's felt, when it started, what makes it better or worse).

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
    language: str | None = None


class CauseTurnRequest(BaseModel):
    user_message: str
    known_cause_labels: list[str] = []
    language: str | None = None


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


def _mock_symptom_turn(text: str, catalog: list[dict], known_ids: list[str], language: str) -> TurnResponse:
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
        message = MOCK_SYMPTOM_MATCHED[language]
    elif suggestions:
        message = MOCK_SYMPTOM_SUGGESTIONS_ONLY[language]
    else:
        message = MOCK_SYMPTOM_NO_MATCH[language]

    matched_out = [{"id": s["id"], "label": s["name"]} for s in matched]
    return TurnResponse(
        assistant_message=message,
        matched=matched_out,
        suggestions=suggestions,
        extracted_profile=_extract_profile_hints(text),
    )


def _mock_cause_turn(text: str, known_labels: list[str], language: str) -> TurnResponse:
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

    message = MOCK_CAUSE_SUGGESTIONS[language] if suggestions else MOCK_CAUSE_NO_SUGGESTIONS[language]
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
async def greeting(language: str | None = None):
    return GreetingResponse(message=GREETINGS[_normalize_language(language)])


@app.post("/intake/symptom-turn", response_model=TurnResponse)
async def symptom_turn(req: SymptomTurnRequest):
    catalog = await _catalog()
    language = _normalize_language(req.language)

    if llm.MOCK_MODE:
        return _mock_symptom_turn(req.user_message, catalog, req.known_symptom_ids, language)

    catalog_desc = "\n".join(f"- {s['id']}: {s['name']}" for s in catalog if s["id"] not in req.known_symptom_ids)
    raw = await llm.complete_or_none(
        _localized_system_prompt(language),
        f"Symptom catalog (id: name):\n{catalog_desc}\n\nAlready known symptoms: {req.known_symptom_ids}\n\n"
        f"User just said: \"{req.user_message}\"",
        max_tokens=400,
    )
    parsed = _parse_llm_json(raw) if raw else None
    if parsed is None:
        return _mock_symptom_turn(req.user_message, catalog, req.known_symptom_ids, language)

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
    language = _normalize_language(req.language)

    if llm.MOCK_MODE:
        return _mock_cause_turn(req.user_message, req.known_cause_labels, language)

    raw = await llm.complete_or_none(
        _localized_system_prompt(language),
        f"Cause categories: {CAUSE_CATEGORIES}\nAlready known causes: {req.known_cause_labels}\n\n"
        f"User just said: \"{req.user_message}\"\n\n"
        f"For this turn, 'suggestions' should be short cause/contributing-factor labels (not catalog ids).",
        max_tokens=400,
    )
    parsed = _parse_llm_json(raw) if raw else None
    if parsed is None:
        return _mock_cause_turn(req.user_message, req.known_cause_labels, language)

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
