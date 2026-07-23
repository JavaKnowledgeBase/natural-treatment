"""API Gateway / BFF -- the only service the frontend talks to directly.

Session tokens are just the orchestrator's opaque session_id (128 bits of
randomness from uuid4) -- there's no account system to authenticate against,
so possession of the id is the capability. This service's job is rate
limiting and proxying, not identity.
"""
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.cache import get_redis

ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_SERVICE_URL", "http://orchestrator:8000")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("GATEWAY_RATE_LIMIT_PER_MINUTE", "60"))

app = FastAPI(title="API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path != "/healthz":
        client_ip = request.client.host if request.client else "unknown"
        r = get_redis()
        key = f"gateway:ratelimit:{client_ip}:{int(time.time() // 60)}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 60)
        if count > RATE_LIMIT_PER_MINUTE:
            return _too_many_requests()
    return await call_next(request)


def _too_many_requests():
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded, please slow down."})


async def _forward(method: str, path: str, json_body: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, f"{ORCHESTRATOR_URL}{path}", json=json_body)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


class CreateSessionBody(BaseModel):
    language: str | None = None


class MessageBody(BaseModel):
    text: str


class AddItemBody(BaseModel):
    kind: str
    id: str | None = None
    label: str
    category: str | None = None


class RemoveItemBody(BaseModel):
    kind: str
    id: str


class EmailRequestBody(BaseModel):
    to: str


class EmailConfirmBody(BaseModel):
    verification_token: str
    code: str


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/session")
async def create_session(body: CreateSessionBody = CreateSessionBody()):
    return await _forward("POST", "/sessions", body.model_dump())


@app.get("/session/{sid}")
async def get_session_state(sid: str):
    return await _forward("GET", f"/sessions/{sid}/state")


@app.post("/session/{sid}/message")
async def send_message(sid: str, body: MessageBody):
    return await _forward("POST", f"/sessions/{sid}/message", body.model_dump())


@app.post("/session/{sid}/add-item")
async def add_item(sid: str, body: AddItemBody):
    return await _forward("POST", f"/sessions/{sid}/add-item", body.model_dump())


@app.post("/session/{sid}/remove-item")
async def remove_item(sid: str, body: RemoveItemBody):
    return await _forward("POST", f"/sessions/{sid}/remove-item", body.model_dump())


@app.post("/session/{sid}/advance-to-causes")
async def advance_to_causes(sid: str):
    return await _forward("POST", f"/sessions/{sid}/advance-to-causes")


@app.post("/session/{sid}/analyze")
async def analyze(sid: str):
    return await _forward("POST", f"/sessions/{sid}/analyze")


@app.post("/session/{sid}/email/request")
async def email_request(sid: str, body: EmailRequestBody):
    return await _forward("POST", f"/sessions/{sid}/email/request", body.model_dump())


@app.post("/session/{sid}/email/confirm")
async def email_confirm(sid: str, body: EmailConfirmBody):
    return await _forward("POST", f"/sessions/{sid}/email/confirm", body.model_dump())


@app.post("/session/{sid}/end")
async def end_session(sid: str):
    return await _forward("POST", f"/sessions/{sid}/end")
