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

# UI + LLM-conversation language support only (see docs/ARCHITECTURE.md).
# Herb names are shown as "<local name> (<English name>)" per the user's
# explicit preference (e.g. "अश्वगंधा (Ashwagandha)") -- pairing rather than
# replacing the English name keeps the botanical/scientific identity
# unambiguous (still traceable to the English-keyed starter dataset) while
# giving the local name for readability. Local names below favor
# well-established traditional/pharmacopoeia names where one genuinely
# exists (e.g. तुलसी for holy basil, 甘草 for licorice root, which are the
# real native names, not inventions) and fall back to plain phonetic
# transliteration for herbs with no established local name, rather than
# guessing at one -- a wrong invented "traditional" name would be worse
# than an honest transliteration in a health-adjacent app.
HERB_NAME_TRANSLATIONS = {
    "ashwagandha": {"hi": "अश्वगंधा", "zh": "南非醉茄", "fr": "Ashwagandha", "es": "Ashwagandha"},
    "turmeric": {"hi": "हल्दी", "zh": "姜黄", "fr": "Curcuma", "es": "Cúrcuma"},
    "ginger": {"hi": "अदरक", "zh": "生姜", "fr": "Gingembre", "es": "Jengibre"},
    "chamomile": {"hi": "कैमोमाइल", "zh": "洋甘菊", "fr": "Camomille", "es": "Manzanilla"},
    "valerian": {"hi": "वेलेरियन", "zh": "缬草", "fr": "Valériane", "es": "Valeriana"},
    "peppermint": {"hi": "पुदीना", "zh": "薄荷", "fr": "Menthe poivrée", "es": "Menta piperita"},
    "milk_thistle": {"hi": "मिल्क थिस्ल", "zh": "水飞蓟", "fr": "Chardon-Marie", "es": "Cardo mariano"},
    "elderberry": {"hi": "एल्डरबेरी", "zh": "接骨木果", "fr": "Sureau", "es": "Saúco"},
    "echinacea": {"hi": "इचिनेशिया", "zh": "紫锥菊", "fr": "Échinacée", "es": "Equinácea"},
    "ginkgo": {"hi": "जिंकगो", "zh": "银杏", "fr": "Ginkgo", "es": "Ginkgo"},
    "holy_basil": {"hi": "तुलसी", "zh": "圣罗勒", "fr": "Basilic sacré", "es": "Albahaca sagrada"},
    "licorice_root": {"hi": "मुलेठी", "zh": "甘草", "fr": "Réglisse", "es": "Regaliz"},
    "nettle": {"hi": "बिच्छू बूटी", "zh": "荨麻", "fr": "Ortie", "es": "Ortiga"},
    "dandelion": {"hi": "डैंडिलियन", "zh": "蒲公英", "fr": "Pissenlit", "es": "Diente de león"},
    "hawthorn": {"hi": "हॉथॉर्न", "zh": "山楂", "fr": "Aubépine", "es": "Espino blanco"},
    "maca": {"hi": "माका", "zh": "玛卡", "fr": "Maca", "es": "Maca"},
    "rhodiola": {"hi": "रोडियोला", "zh": "红景天", "fr": "Rhodiole", "es": "Rodiola"},
    "passionflower": {"hi": "पैशनफ्लावर", "zh": "西番莲", "fr": "Passiflore", "es": "Pasiflora"},
    "feverfew": {"hi": "फीवरफ्यू", "zh": "小白菊", "fr": "Grande camomille", "es": "Matricaria"},
    "cramp_bark": {"hi": "क्रैम्प बार्क", "zh": "荚蒾", "fr": "Viorne obier", "es": "Viburno"},
    "chasteberry": {"hi": "चेस्टबेरी", "zh": "穗花牡荆", "fr": "Gattilier", "es": "Sauzgatillo"},
    "psyllium": {"hi": "ईसबगोल", "zh": "车前子", "fr": "Psyllium", "es": "Zaragatona"},
    "boswellia": {"hi": "शल्लकी", "zh": "乳香", "fr": "Oliban", "es": "Incienso"},
    "brahmi": {"hi": "ब्राह्मी", "zh": "布拉米", "fr": "Brahmi", "es": "Brahmi"},
    "guduchi": {"hi": "गिलोय", "zh": "古都基", "fr": "Guduchi", "es": "Guduchi"},
    "amla": {"hi": "आंवला", "zh": "余甘子", "fr": "Groseille indienne", "es": "Grosella india"},
    "neem": {"hi": "नीम", "zh": "印楝", "fr": "Margousier", "es": "Nim"},
    "fenugreek": {"hi": "मेथी", "zh": "胡芦巴", "fr": "Fenugrec", "es": "Fenogreco"},
    "gotu_kola": {"hi": "मंडूकपर्णी", "zh": "积雪草", "fr": "Centella", "es": "Centella asiática"},
    "shatavari": {"hi": "शतावरी", "zh": "沙塔瓦丽", "fr": "Shatavari", "es": "Shatavari"},
    "guggul": {"hi": "गुग्गुल", "zh": "印度没药", "fr": "Myrrhe indienne", "es": "Mirra india"},
    "arjuna": {"hi": "अर्जुन", "zh": "阿周那", "fr": "Arjuna", "es": "Arjuna"},
    "punarnava": {"hi": "पुनर्नवा", "zh": "普纳尔纳瓦", "fr": "Punarnava", "es": "Punarnava"},
    "astragalus": {"hi": "एस्ट्रागालस", "zh": "黄芪", "fr": "Astragale", "es": "Astrágalo"},
    "panax_ginseng": {"hi": "जिनसेंग", "zh": "人参", "fr": "Ginseng", "es": "Ginseng"},
    "schisandra": {"hi": "शिसेंड्रा", "zh": "五味子", "fr": "Schisandra", "es": "Schisandra"},
    "reishi": {"hi": "रीशी", "zh": "灵芝", "fr": "Ganoderme luisant", "es": "Reishi"},
    "he_shou_wu": {"hi": "शी शो वू", "zh": "何首乌", "fr": "He Shou Wu", "es": "He Shou Wu"},
    "dong_quai": {"hi": "डोंग क्वाई", "zh": "当归", "fr": "Angélique chinoise", "es": "Angélica china"},
    "goji_berry": {"hi": "गोजी बेरी", "zh": "枸杞", "fr": "Baie de goji", "es": "Bayas de goji"},
    "cordyceps": {"hi": "कॉर्डिसेप्स", "zh": "冬虫夏草", "fr": "Cordyceps", "es": "Cordyceps"},
    "poria": {"hi": "पोरिया", "zh": "茯苓", "fr": "Poria", "es": "Poria"},
    "bupleurum": {"hi": "बुप्लेरम", "zh": "柴胡", "fr": "Bupleurum", "es": "Bupleurum"},
}

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


def _display_herb_name(herb_id: str, english_name: str, language: str) -> str:
    if language == DEFAULT_LANGUAGE:
        return english_name
    local_name = HERB_NAME_TRANSLATIONS.get(herb_id, {}).get(language)
    return f"{local_name} ({english_name})" if local_name else english_name


def _localized_system_prompt(language: str) -> str:
    if language == DEFAULT_LANGUAGE:
        return SYSTEM_PROMPT
    return (
        SYSTEM_PROMPT
        + f"\n\nWrite every sentence entirely in {LANGUAGE_NAMES[language]}. Both the herb name and "
        f"the evidence level phrase given to you are already in the format to use verbatim -- the "
        f"herb name is formatted as \"<local name> (<English name>)\" and the evidence level is "
        f"already translated into {LANGUAGE_NAMES[language]}. Use both exactly as given; do not "
        f"re-translate or alter either one."
    )


class GenerateRequest(BaseModel):
    candidates: list[dict]
    ranked: list[dict]
    verdicts: list[dict]
    language: str | None = None


class GenerateResponse(BaseModel):
    recommendations: list[dict]


def _template_reason(herb: dict, language: str) -> str:
    mechanisms = [
        link.get("mechanism_summary")
        for link in herb.get("compounds", [])
        if link.get("mechanism_summary")
    ]
    mechanism_text = " ".join(mechanisms[:1]) or "supportive traditional use"
    display_name = _display_herb_name(herb["id"], herb["name"], language)
    return f"{display_name} contains compounds associated with {mechanism_text.rstrip('.').lower()}."


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
        display_name = _display_herb_name(herb["id"], herb["name"], language)
        herb_lines.append(
            f"- id: {herb['id']}, name: \"{display_name}\" (use this exact name verbatim), "
            f"evidence level: \"{evidence_phrase}\" (use this exact phrase verbatim), "
            f"mechanism notes: {mechanisms}, confidence band: {entry['confidence_band']}"
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
        reason = reasons_by_id.get(herb["id"]) or _template_reason(herb, language)
        verdict = verdicts_by_id.get(herb["id"], {})
        safety_note = "; ".join(verdict.get("notes", [])) or None

        recommendations.append(
            {
                "herb_id": herb["id"],
                "herb_name": _display_herb_name(herb["id"], herb["name"], language),
                "score": entry["adjusted_score"],
                "confidence_band": entry["confidence_band"],
                "reason": reason,
                "evidence_level": herb.get("evidence_level"),
                "safety_note": safety_note,
                "curation_status": herb.get("curation_status", "starter_dataset_unreviewed"),
            }
        )

    return GenerateResponse(recommendations=recommendations)
