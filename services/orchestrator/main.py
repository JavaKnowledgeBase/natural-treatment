"""Agent Orchestrator -- runs the state graph from application_design_v2 §4:

    Greeting -> SymptomCollection -> CauseCollection -> Analysis -> Results -> EmailSent/Purged

This service owns all Tier 2 (session) reads/writes; every agent it calls is
a stateless HTTP service that takes JSON in and returns JSON out. Note there
is no profile-collection state anywhere in this graph -- that's what makes
"never proactively ask for personal details" a structural property of the
orchestration, not just a prompt instruction.
"""
import os
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared import cache

INTAKE_URL = os.environ.get("INTAKE_SERVICE_URL", "http://agent-intake:8000")
MAPPING_URL = os.environ.get("MAPPING_SERVICE_URL", "http://agent-mapping:8000")
RETRIEVAL_URL = os.environ.get("RETRIEVAL_SERVICE_URL", "http://agent-retrieval:8000")
SAFETY_URL = os.environ.get("SAFETY_SERVICE_URL", "http://agent-safety:8000")
SCORING_URL = os.environ.get("SCORING_SERVICE_URL", "http://agent-scoring:8000")
EXPLANATION_URL = os.environ.get("EXPLANATION_SERVICE_URL", "http://agent-explanation:8000")
REPORTING_URL = os.environ.get("REPORTING_SERVICE_URL", "http://agent-reporting:8000")
EMAIL_URL = os.environ.get("EMAIL_SERVICE_URL", "http://email:8000")

app = FastAPI(title="Agent Orchestrator")


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class CreateSessionResponse(BaseModel):
    session_id: str
    greeting: str


class MessageRequest(BaseModel):
    text: str


class TurnResult(BaseModel):
    assistant_message: str
    current_step: str
    suggestions: list[dict]
    symptoms: list[dict]
    causes: list[dict]


class AddItemRequest(BaseModel):
    kind: str  # "symptom" | "cause"
    id: str | None = None
    label: str
    category: str | None = None


class RemoveItemRequest(BaseModel):
    kind: str
    id: str


class AnalyzeResult(BaseModel):
    current_step: str
    reasoning: str | None
    recommendations: list[dict]


class EmailRequestBody(BaseModel):
    to: str


class EmailConfirmBody(BaseModel):
    verification_token: str
    code: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_session(sid: str) -> dict:
    meta = await cache.get_meta(sid)
    if meta is None:
        raise HTTPException(status_code=404, detail="Session not found or already expired/purged")
    return meta


async def _post(url: str, path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{url}{path}", json=body)
        resp.raise_for_status()
        return resp.json()


async def _get(url: str, path: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{url}{path}")
        resp.raise_for_status()
        return resp.json()


def _cache_item_to_dict(item_id: str, label: str, source: str, category: str | None) -> dict:
    return {"id": item_id, "label": label, "source": source, "category": category, "ts": time.time()}


async def _apply_extracted_profile(sid: str, extracted: dict) -> None:
    if extracted:
        await cache.update_profile(sid, extracted)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session():
    sid = uuid.uuid4().hex
    await cache.create_session(sid)
    greeting = (await _get(INTAKE_URL, "/intake/greeting"))["message"]
    await cache.append_chat_message(sid, "assistant", greeting)
    return CreateSessionResponse(session_id=sid, greeting=greeting)


@app.get("/sessions/{sid}/state")
async def get_state(sid: str):
    meta = await _require_session(sid)
    return {
        "meta": meta,
        "chat": await cache.get_chat_history(sid),
        "symptoms": await cache.list_cached_items(sid, "symptoms"),
        "causes": await cache.list_cached_items(sid, "causes"),
        "recommendations": await cache.get_list(sid, "recommendations"),
    }


@app.post("/sessions/{sid}/message", response_model=TurnResult)
async def post_message(sid: str, req: MessageRequest):
    meta = await _require_session(sid)
    step = meta["current_step"]
    await cache.append_chat_message(sid, "user", req.text)

    if step in ("greeting", "symptom_collection"):
        if step == "greeting":
            await cache.set_step(sid, "symptom_collection")
            step = "symptom_collection"

        known_symptoms = await cache.list_cached_items(sid, "symptoms")
        known_ids = [s["id"] for s in known_symptoms]
        result = await _post(INTAKE_URL, "/intake/symptom-turn", {
            "user_message": req.text,
            "known_symptom_ids": known_ids,
        })
        for m in result.get("matched", []):
            await cache.add_cached_item(sid, "symptoms", m["id"], _cache_item_to_dict(m["id"], m["label"], "user_stated", None))
        # Suggestions are offered, not auto-added -- the user picks via /add-item.
        suggestions = result.get("suggestions", [])
        await _apply_extracted_profile(sid, result.get("extracted_profile", {}))
        assistant_message = result["assistant_message"]

    elif step == "cause_collection":
        known_causes = await cache.list_cached_items(sid, "causes")
        known_labels = [c["label"] for c in known_causes]
        result = await _post(INTAKE_URL, "/intake/cause-turn", {
            "user_message": req.text,
            "known_cause_labels": known_labels,
        })
        for m in result.get("matched", []):
            item_id = uuid.uuid4().hex[:8]
            await cache.add_cached_item(sid, "causes", item_id, _cache_item_to_dict(item_id, m["label"], "user_stated", m.get("category")))
        suggestions = result.get("suggestions", [])
        await _apply_extracted_profile(sid, result.get("extracted_profile", {}))
        assistant_message = result["assistant_message"]

    else:
        raise HTTPException(status_code=400, detail=f"Chat input isn't accepted in step '{step}'")

    await cache.append_chat_message(sid, "assistant", assistant_message)
    return TurnResult(
        assistant_message=assistant_message,
        current_step=step,
        suggestions=suggestions,
        symptoms=await cache.list_cached_items(sid, "symptoms"),
        causes=await cache.list_cached_items(sid, "causes"),
    )


@app.post("/sessions/{sid}/add-item")
async def add_item(sid: str, req: AddItemRequest):
    await _require_session(sid)
    cache_name = "symptoms" if req.kind == "symptom" else "causes"
    item_id = req.id or uuid.uuid4().hex[:8]
    await cache.add_cached_item(sid, cache_name, item_id, _cache_item_to_dict(item_id, req.label, "suggested_accepted", req.category))
    return {"status": "added", "id": item_id}


@app.post("/sessions/{sid}/remove-item")
async def remove_item(sid: str, req: RemoveItemRequest):
    await _require_session(sid)
    cache_name = "symptoms" if req.kind == "symptom" else "causes"
    await cache.remove_cached_item(sid, cache_name, req.id)
    return {"status": "removed"}


@app.post("/sessions/{sid}/advance-to-causes")
async def advance_to_causes(sid: str):
    meta = await _require_session(sid)
    if meta["current_step"] != "symptom_collection":
        raise HTTPException(status_code=400, detail="Can only advance to cause collection from symptom collection")
    await cache.set_step(sid, "cause_collection")
    message = "What events, stressors, or daily activities do you think may have contributed?"
    await cache.append_chat_message(sid, "assistant", message)
    return {"current_step": "cause_collection", "assistant_message": message}


# ---------------------------------------------------------------------------
# Analysis (the sticky-button action)
# ---------------------------------------------------------------------------

@app.post("/sessions/{sid}/analyze", response_model=AnalyzeResult)
async def analyze(sid: str):
    meta = await _require_session(sid)
    if meta["current_step"] not in ("symptom_collection", "cause_collection"):
        raise HTTPException(status_code=400, detail="Analysis is only available during symptom or cause collection")

    symptoms = await cache.list_cached_items(sid, "symptoms")
    causes = await cache.list_cached_items(sid, "causes")
    if not symptoms and not causes:
        raise HTTPException(status_code=400, detail="Add at least one symptom or cause before analyzing")

    symptom_ids = [s["id"] for s in symptoms]
    profile = await cache.get_profile(sid)

    mapping_result = await _post(MAPPING_URL, "/mapping/analyze", {"symptom_ids": symptom_ids})
    retrieval_result = await _post(RETRIEVAL_URL, "/retrieval/candidates", {
        "symptom_ids": symptom_ids,
        "imbalances": mapping_result["imbalances"],
    })
    candidates = retrieval_result["candidates"]

    safety_result = await _post(SAFETY_URL, "/safety/evaluate", {"candidates": candidates, "profile": profile})
    scoring_result = await _post(SCORING_URL, "/scoring/rank", {
        "symptom_ids": symptom_ids,
        "candidates": candidates,
        "verdicts": safety_result["verdicts"],
    })
    explanation_result = await _post(EXPLANATION_URL, "/explanation/generate", {
        "candidates": candidates,
        "ranked": scoring_result["ranked"],
        "verdicts": safety_result["verdicts"],
    })

    recommendations = explanation_result["recommendations"]
    await cache.clear_list(sid, "recommendations")
    for rec in recommendations:
        await cache.push_list_item(sid, "recommendations", rec)

    await cache.set_step(sid, "results")
    summary = mapping_result.get("reasoning") or "Here's what the starter dataset suggests based on what you shared."
    await cache.append_chat_message(sid, "assistant", summary)

    return AnalyzeResult(current_step="results", reasoning=mapping_result.get("reasoning"), recommendations=recommendations)


# ---------------------------------------------------------------------------
# Email export + purge
# ---------------------------------------------------------------------------

@app.post("/sessions/{sid}/email/request")
async def email_request(sid: str, req: EmailRequestBody):
    await _require_session(sid)
    result = await _post(EMAIL_URL, "/email/verify", {"to": req.to})
    return result


@app.post("/sessions/{sid}/email/confirm")
async def email_confirm(sid: str, req: EmailConfirmBody):
    await _require_session(sid)
    state = await get_state(sid)
    compiled = await _post(REPORTING_URL, "/reporting/compile", {
        "chat_history": state["chat"],
        "symptoms": state["symptoms"],
        "causes": state["causes"],
        "recommendations": state["recommendations"],
    })
    send_result = await _post(EMAIL_URL, "/email/send", {
        "verification_token": req.verification_token,
        "code": req.code,
        "subject": compiled["subject"],
        "html": compiled["html"],
        "text": compiled["text"],
    })
    await cache.set_step(sid, "email_sent")
    deleted = await cache.purge_session(sid)
    return {"email": send_result, "purged_keys": deleted}


@app.post("/sessions/{sid}/end")
async def end_session(sid: str):
    await _require_session(sid)
    deleted = await cache.purge_session(sid)
    return {"status": "purged", "purged_keys": deleted}
