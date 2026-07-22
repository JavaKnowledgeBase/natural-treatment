"""Reporting Agent -- compiles the chat transcript + symptom/cause caches +
recommendations into the final email payload (subject, HTML, text), per
application_design_v2 §6.2. Deterministic templating only, no LLM -- the
final safety disclaimer and content shape should not be left to model
variance.
"""
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Reporting Agent")

DISCLAIMER = (
    "This message is informational only and is not a substitute for professional "
    "medical advice, diagnosis, or treatment. The herb data used to generate these "
    "suggestions is an unreviewed starter dataset. Please consult a licensed "
    "clinician before making any changes to your care."
)


class CompileRequest(BaseModel):
    chat_history: list[dict]
    symptoms: list[dict]
    causes: list[dict]
    recommendations: list[dict]


class CompileResponse(BaseModel):
    subject: str
    html: str
    text: str


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/reporting/compile", response_model=CompileResponse)
async def compile_report(req: CompileRequest):
    subject = "Your natural treatment session summary"

    text_lines = ["YOUR SESSION SUMMARY", "=" * 21, ""]
    html_parts = ["<h1>Your session summary</h1>"]

    text_lines.append("Symptoms you shared:")
    html_parts.append("<h2>Symptoms you shared</h2><ul>")
    for s in req.symptoms:
        text_lines.append(f"  - {s.get('label')}")
        html_parts.append(f"<li>{s.get('label')}</li>")
    html_parts.append("</ul>")

    text_lines.append("")
    text_lines.append("Possible contributing causes:")
    html_parts.append("<h2>Possible contributing causes</h2><ul>")
    for c in req.causes:
        text_lines.append(f"  - {c.get('label')} ({c.get('category', 'general')})")
        html_parts.append(f"<li>{c.get('label')} ({c.get('category', 'general')})</li>")
    html_parts.append("</ul>")

    text_lines.append("")
    text_lines.append("Top recommendations:")
    html_parts.append("<h2>Top recommendations</h2>")
    for r in req.recommendations:
        text_lines.append(
            f"  - {r.get('herb_name')} (score {r.get('score')}, {r.get('confidence_band')} confidence)\n"
            f"      {r.get('reason')}\n"
            f"      Evidence level: {r.get('evidence_level')}\n"
            f"      Safety note: {r.get('safety_note') or 'None noted'}"
        )
        html_parts.append(
            f"<div><strong>{r.get('herb_name')}</strong> "
            f"(score {r.get('score')}, {r.get('confidence_band')} confidence)"
            f"<p>{r.get('reason')}</p>"
            f"<p>Evidence level: {r.get('evidence_level')}</p>"
            f"<p>Safety note: {r.get('safety_note') or 'None noted'}</p></div>"
        )

    text_lines.append("")
    text_lines.append("Full conversation:")
    html_parts.append("<h2>Full conversation</h2>")
    for msg in req.chat_history:
        line = f"  [{_fmt_ts(msg['ts'])}] {msg['role']}: {msg['text']}"
        text_lines.append(line)
        html_parts.append(f"<p><em>{_fmt_ts(msg['ts'])}</em> <strong>{msg['role']}</strong>: {msg['text']}</p>")

    text_lines.append("")
    text_lines.append(DISCLAIMER)
    html_parts.append(f"<hr/><p><small>{DISCLAIMER}</small></p>")

    return CompileResponse(subject=subject, html="".join(html_parts), text="\n".join(text_lines))
