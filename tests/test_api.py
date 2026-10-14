import base64
import json

import httpx
from fastapi.testclient import TestClient

from pilot.app import create_app
from pilot.audit import AuditLog
from pilot.providers import ElevenLabsProvider, MockProvider, ProviderError

TCKN = "12345678264"


def client(tmp_path, allow_audio=False):
    audit = AuditLog(tmp_path / "audit.jsonl")
    return TestClient(create_app(MockProvider(), audit, allow_audio)), tmp_path / "audit.jsonl"


def test_text_turn_with_audio(tmp_path):
    c, _ = client(tmp_path)
    r = c.post("/v1/turn", json={"text": "Şubeniz saat kaçta açılıyor", "with_audio": True})
    j = r.json()
    assert r.status_code == 200 and j["action"] == "answer"
    assert base64.b64decode(j["audio_b64"]).startswith(b"MOCKAUDIO:")


def test_session_continuity(tmp_path):
    c, _ = client(tmp_path)
    sid = c.post("/v1/turn", json={"text": "mavi bulut"}).json()["session_id"]
    r = c.post("/v1/turn", json={"session_id": sid, "text": "kırmızı elma"}).json()
    assert r["action"] == "handoff" and r["session_id"] == sid


def test_audit_log_has_no_raw_pii(tmp_path):
    c, path = client(tmp_path)
    c.post("/v1/turn", json={"text": f"TC kimlik {TCKN} kartım çalındı"})
    raw = path.read_text(encoding="utf-8")
    assert TCKN not in raw
    entry = json.loads(raw.splitlines()[0])
    assert entry["pii_counts"] == {"tckn": 1} and "[TCKN]" in entry["redacted_input"]


def test_audio_blocked_by_default(tmp_path):
    c, _ = client(tmp_path, allow_audio=False)
    r = c.post("/v1/turn/audio", files={"file": ("a.wav", b"merhaba")})
    assert r.status_code == 403


def test_audio_when_allowed_returns_only_redacted_transcript(tmp_path):
    c, _ = client(tmp_path, allow_audio=True)
    r = c.post("/v1/turn/audio", files={"file": ("a.wav", f"kimlik {TCKN}".encode())})
    j = r.json()
    assert r.status_code == 200 and TCKN not in json.dumps(j)
    assert j["action"] == "handoff"


def test_elevenlabs_request_shapes():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path == "/v1/speech-to-text":
            return httpx.Response(200, json={"text": "merhaba"})
        return httpx.Response(200, content=b"mp3bytes")

    p = ElevenLabsProvider("KEY", "VOICE", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert p.transcribe(b"x", "a.wav") == "merhaba"
    assert p.synthesize("selam") == b"mp3bytes"
    stt, tts = seen
    assert stt.headers["xi-api-key"] == "KEY" and b"scribe_v2" in stt.content
    assert tts.url.path == "/v1/text-to-speech/VOICE"
    assert tts.url.params["output_format"] == "mp3_44100_128"
    assert json.loads(tts.content) == {"text": "selam", "model_id": "eleven_multilingual_v2"}


def test_elevenlabs_error_does_not_leak_body():
    def handler(req):
        return httpx.Response(401, json={"detail": "secret-ish"})

    p = ElevenLabsProvider("KEY", "V", client=httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        p.synthesize("x")
    except ProviderError as e:
        assert "401" in str(e) and "secret-ish" not in str(e)
    else:
        raise AssertionError("ProviderError bekleniyordu")


def test_demo_page_and_health(tmp_path):
    c, _ = client(tmp_path)
    assert "Sesli asistan" in c.get("/").text or "sesli asistan" in c.get("/").text
    assert c.get("/health").json() == {"status": "ok", "cloud_audio": False, "provider": "MockProvider", "mock_banking": False}


def test_dtmf_pin_never_reaches_audit_or_response(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    c = TestClient(create_app(MockProvider(), audit, False, mock_banking=True))
    sid = c.post("/v1/turn", json={"dtmf": "3"}).json()["session_id"]
    r = c.post("/v1/turn", json={"session_id": sid, "dtmf": "1234", "with_audio": True})
    j = r.json()
    assert r.status_code == 200 and j["action"] == "answer" and j["awaiting"] == "post"
    assert "1234" not in json.dumps({k: v for k, v in j.items() if k != "audio_b64"})
    assert "1234" not in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")


def test_turn_requires_exactly_one_input(tmp_path):
    c, _ = client(tmp_path)
    assert c.post("/v1/turn", json={}).status_code == 422
    assert c.post("/v1/turn", json={"text": "a", "dtmf": "1"}).status_code == 422
    assert c.post("/v1/turn", json={"dtmf": "12ab"}).status_code == 422
