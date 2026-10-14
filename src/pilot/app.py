"""FastAPI application.

Endpoints:
  GET  /               -> demo page
  GET  /health
  POST /v1/turn        {session_id?, text | dtmf, with_audio?} -> text or keypad turn
  POST /v1/turn/audio  multipart: file, session_id?           -> audio turn (needs ALLOW_CLOUD_AUDIO=true)

The raw transcript is never returned; only the redacted version is.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, model_validator

from .audit import AuditLog
from .dialogue import DialogueManager, Session, TurnResult
from .providers import ElevenLabsProvider, MockProvider, ProviderError, SpeechProvider


class TurnRequest(BaseModel):
    session_id: str | None = None
    text: str | None = Field(default=None, min_length=1, max_length=1000)
    dtmf: str | None = Field(default=None, pattern=r"^[0-9*#]{1,8}$")  # phone keypad input
    with_audio: bool = False

    @model_validator(mode="after")
    def one_input(self):
        if (self.text is None) == (self.dtmf is None):
            raise ValueError("exactly one of text or dtmf is required")
        return self


def provider_from_env() -> SpeechProvider:
    if os.environ.get("PROVIDER", "mock") == "elevenlabs":
        return ElevenLabsProvider(
            api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", ""),
            stt_model=os.environ.get("ELEVENLABS_STT_MODEL", "scribe_v2"),
            tts_model=os.environ.get("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2"),
            stt_language=os.environ.get("ELEVENLABS_STT_LANGUAGE") or None,
        )
    return MockProvider()


def create_app(
    provider: SpeechProvider | None = None,
    audit: AuditLog | None = None,
    allow_cloud_audio: bool | None = None,
    mock_banking: bool | None = None,
) -> FastAPI:
    app = FastAPI(title="Sesli asistan pilotu")
    provider = provider or provider_from_env()
    audit = audit or AuditLog(os.environ.get("AUDIT_LOG_PATH"))
    if allow_cloud_audio is None:
        allow_cloud_audio = os.environ.get("ALLOW_CLOUD_AUDIO", "false").lower() == "true"
    # Demo banking: PIN entry for balance + mock account service. Off by default.
    if mock_banking is None:
        mock_banking = os.environ.get("MOCK_BANKING", "false").lower() == "true"
    dm = DialogueManager(mock_banking=mock_banking)
    sessions: dict[str, Session] = {}  # In memory for the pilot; Redis or similar in production

    def get_session(sid: str | None) -> Session:
        if sid and sid in sessions:
            return sessions[sid]
        s = Session()
        sessions[s.id] = s
        return s

    def body(r: TurnResult, with_audio: bool) -> dict:
        out = {
            "session_id": r.session_id,
            "intent": r.intent,
            "confidence": r.confidence,
            "action": r.action,
            "reply": r.reply,
            "reasons": list(r.reasons),
            "transcript_redacted": r.redacted_input,
            "pii_found": r.pii_found,
            "awaiting": r.awaiting,
        }
        if with_audio:
            try:
                out["audio_b64"] = base64.b64encode(provider.synthesize(r.reply)).decode()
            except ProviderError as e:
                raise HTTPException(502, f"TTS failed: {e}")
        return out

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")

    @app.get("/health")
    def health():
        return {"status": "ok", "cloud_audio": allow_cloud_audio, "provider": type(provider).__name__,
                "mock_banking": mock_banking}

    @app.post("/v1/turn")
    def turn(req: TurnRequest):
        s = get_session(req.session_id)
        if req.dtmf is not None:
            r = dm.handle_dtmf(s, req.dtmf)
            audit.write(r, "dtmf")
        else:
            r = dm.handle(s, req.text)
            audit.write(r, "text")
        return body(r, req.with_audio)

    @app.post("/v1/turn/audio")
    async def turn_audio(file: UploadFile = File(...), session_id: str | None = Form(None)):
        if not allow_cloud_audio:
            raise HTTPException(
                403,
                "Audio processing is disabled (ALLOW_CLOUD_AUDIO=false). Audio would be sent to a cloud "
                "STT, so do not enable it without customer approval and a legal review.",
            )
        audio = await file.read()
        try:
            text = provider.transcribe(audio, file.filename or "audio")
        except ProviderError as e:
            raise HTTPException(502, f"STT failed: {e}")
        if not text.strip():
            raise HTTPException(422, "Audio could not be understood")
        r = dm.handle(get_session(session_id), text)
        audit.write(r, "audio")
        return body(r, with_audio=True)

    return app


app = create_app()
