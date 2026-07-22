"""Email Delivery Service -- sends the end-of-session export via Resend, or
mock-logs it when RESEND_API_KEY is unset.

Implements the anti-abuse flow from application_design_v2 §6.3: a send
always requires a prior verification code to have been confirmed, and
verification requests are rate-limited per recipient address. This is what
stops the "email me this" feature from being usable as an open relay.
"""
import os
import secrets
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.cache import get_redis

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_ADDRESS = os.environ.get("RESEND_FROM_ADDRESS", "onboarding@resend.dev")
MOCK_MODE = not bool(RESEND_API_KEY)

VERIFY_TTL_SECONDS = 10 * 60
RATE_LIMIT_WINDOW_SECONDS = 60 * 60
RATE_LIMIT_MAX_PER_WINDOW = 3

app = FastAPI(title="Email Delivery Service")


class VerifyRequest(BaseModel):
    to: str


class VerifyResponse(BaseModel):
    verification_token: str
    mock_mode: bool


class SendRequest(BaseModel):
    verification_token: str
    code: str
    subject: str
    html: str
    text: str


class SendResponse(BaseModel):
    status: str
    message_id: Optional[str] = None


def _verify_key(token: str) -> str:
    return f"email:verify:{token}"


def _ratelimit_key(to: str) -> str:
    return f"email:ratelimit:{to.lower()}"


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "mock_mode": MOCK_MODE}


@app.post("/email/verify", response_model=VerifyResponse)
async def request_verification(req: VerifyRequest):
    r = get_redis()
    rl_key = _ratelimit_key(req.to)
    count = await r.incr(rl_key)
    if count == 1:
        await r.expire(rl_key, RATE_LIMIT_WINDOW_SECONDS)
    if count > RATE_LIMIT_MAX_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many verification requests for this address. Try again later.")

    token = secrets.token_urlsafe(16)
    code = f"{secrets.randbelow(1_000_000):06d}"
    await r.hset(_verify_key(token), mapping={"to": req.to, "code": code})
    await r.expire(_verify_key(token), VERIFY_TTL_SECONDS)

    if MOCK_MODE:
        print(f"[email:mock] verification code for {req.to}: {code} (token={token})")
    else:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={
                    "from": RESEND_FROM_ADDRESS,
                    "to": [req.to],
                    "subject": "Your verification code",
                    "text": f"Your verification code is {code}. It expires in 10 minutes.",
                },
            )

    return VerifyResponse(verification_token=token, mock_mode=MOCK_MODE)


@app.post("/email/send", response_model=SendResponse)
async def send(req: SendRequest):
    r = get_redis()
    stored = await r.hgetall(_verify_key(req.verification_token))
    if not stored:
        raise HTTPException(status_code=400, detail="Verification token expired or not found.")
    if stored.get("code") != req.code:
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    to_address = stored["to"]
    await r.delete(_verify_key(req.verification_token))

    if MOCK_MODE:
        print(f"[email:mock] --- SENDING EMAIL to {to_address} ---")
        print(f"[email:mock] subject: {req.subject}")
        print(f"[email:mock] text:\n{req.text}")
        return SendResponse(status="mock_sent", message_id=f"mock-{secrets.token_hex(8)}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": RESEND_FROM_ADDRESS,
                "to": [to_address],
                "subject": req.subject,
                "html": req.html,
                "text": req.text,
            },
        )
        resp.raise_for_status()
        message_id = resp.json().get("id")

    return SendResponse(status="sent", message_id=message_id)
