"""STT/TTS providers. Mock is for offline tests, ElevenLabs is the real service."""
from __future__ import annotations

from typing import Protocol

import httpx


class ProviderError(RuntimeError):
    pass


class SpeechProvider(Protocol):
    def transcribe(self, audio: bytes, filename: str) -> str: ...
    def synthesize(self, text: str) -> bytes: ...


class MockProvider:
    """Carries UTF-8 text instead of audio; for tests and the offline demo."""

    def transcribe(self, audio: bytes, filename: str) -> str:
        return audio.decode("utf-8")

    def synthesize(self, text: str) -> bytes:
        return b"MOCKAUDIO:" + text.encode("utf-8")


class ElevenLabsProvider:
    """ElevenLabs REST client.

    Request shapes:
      STT: POST /v1/speech-to-text  (multipart: file, model_id) -> {"text": ...}
      TTS: POST /v1/text-to-speech/{voice_id}?output_format=...  (json: text, model_id) -> audio bytes
    Verified against the live service on 2026-10-14 (see docs/05-first-run.md).
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        stt_model: str = "scribe_v2",
        tts_model: str = "eleven_multilingual_v2",
        base_url: str = "https://api.elevenlabs.io",
        stt_language: str | None = None,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ):
        if not api_key or not voice_id:
            raise ProviderError("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID are required")
        self._key = api_key
        self._voice = voice_id
        self._stt_model = stt_model
        self._tts_model = tts_model
        self._base = base_url.rstrip("/")
        self._lang = stt_language
        self._client = client or httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {"xi-api-key": self._key}

    def transcribe(self, audio: bytes, filename: str) -> str:
        data = {"model_id": self._stt_model}
        if self._lang:
            data["language_code"] = self._lang
        resp = self._client.post(
            f"{self._base}/v1/speech-to-text",
            headers=self._headers(),
            files={"file": (filename, audio)},
            data=data,
        )
        if resp.status_code >= 300:
            raise ProviderError(f"STT error status {resp.status_code}")
        return resp.json().get("text", "")

    def synthesize(self, text: str) -> bytes:
        resp = self._client.post(
            f"{self._base}/v1/text-to-speech/{self._voice}",
            params={"output_format": "mp3_44100_128"},
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"text": text, "model_id": self._tts_model},
        )
        if resp.status_code >= 300:
            raise ProviderError(f"TTS error status {resp.status_code}")
        return resp.content
