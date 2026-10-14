"""Dialogue manager: redaction -> intent -> policy -> reply.

Invariants (guarded by tests):
1. The classifier, the logs and TTS never see raw text; they only see redacted text.
2. Replies are fixed templates (a few approved variants per intent) and never echo what the
   caller said. The only exception is the balance in demo banking mode, and that comes from
   the back end (mockbank) after authentication, not from the caller.
3. Anything uncertain goes to a human. Card security and complaints are never answered
   automatically, in any mode.
4. A keyed-in PIN never appears in a reply, a log line or TTS text.

The reply templates are Turkish because the assistant speaks Turkish to callers.
"""
from __future__ import annotations

import random
import re
import uuid
from dataclasses import dataclass, field

from . import mockbank
from .intents import classify
from .pii import SENSITIVE_KINDS, redact

# NOTE: The texts below are DEMO content. The pilot does not go live until the customer
# provides approved texts (see docs/01-discovery-note.md). A variant is picked at random
# for each key; all variants carry the same information.
FAQ: dict[str, list[str]] = {
    "greeting": [
        "Merhaba, Demo Finans'a hoş geldiniz. Ben sesli asistanınızım.",
        "Merhaba, Demo Finans sesli asistanına bağlandınız. Size nasıl yardımcı olabilirim?",
        "İyi günler, Demo Finans'tan ben sesli asistan. Dinliyorum.",
    ],
    "branch_hours": [
        "Şubelerimiz hafta içi dokuz ile on yedi arasında açıktır. Hafta sonu için lütfen internet sitemizi kontrol edin.",
        "Hafta içi her gün sabah dokuzdan akşam beşe kadar şubelerimizde sizi bekliyoruz. Hafta sonu açık şubeleri internet sitemizde bulabilirsiniz.",
        "Şube çalışma saatlerimiz hafta içi dokuz ile on yedi arası. Cumartesi ve pazar günleri için internet sitemize göz atabilirsiniz.",
    ],
    "loan_info": [
        "Kredi başvurusunu mobil uygulamadan, internet şubesinden ya da en yakın şubemizden yapabilirsiniz. Güncel oranlar için sizi temsilcimize aktarabilirim.",
        "Kredi başvurunuzu mobil uygulamamızdan birkaç dakikada yapabilirsiniz; dilerseniz internet şubesi ya da şubelerimiz de kullanılabilir. Faiz oranları için temsilcimiz yardımcı olur.",
        "Başvuru için mobil uygulama en hızlı yol; internet şubesi ve şubelerimizden de başvurabilirsiniz. Oranları öğrenmek isterseniz temsilcimize bağlayabilirim.",
    ],
    "goodbye": [
        "Rica ederim, iyi günler dilerim.",
        "Ben teşekkür ederim. Demo Finans'ı aradığınız için sağ olun, iyi günler.",
        "Rica ederim. Başka bir sorunuz olursa yine bekleriz, hoşça kalın.",
    ],
    "clarify": [
        "Sizi tam anlayamadım.",
        "Kusura bakmayın, bunu anlayamadım.",
        "Üzgünüm, söylediğinizi tam çıkaramadım.",
    ],
    "invalid_key": [
        "Geçersiz bir tuşlama yaptınız.",
        "Bu tuş için tanımlı bir işlem yok.",
    ],
    "pin_prompt": [
        "Bakiye bilgisi için kimliğinizi doğrulamam gerekiyor. Lütfen dört haneli telefon bankacılığı şifrenizi tuşlayın. Temsilci için yıldız tuşuna basabilirsiniz.",
        "Hesap bilgilerinizi paylaşabilmem için dört haneli telefon şifrenizi tuşlamanız gerekiyor. Temsilciye bağlanmak isterseniz yıldıza basın.",
    ],
    "pin_spoken": [
        "Güvenliğiniz için şifrenizi lütfen sesli söylemeyin; telefonunuzun tuşlarıyla girin. Temsilciye bağlanmak için yıldız tuşuna basabilirsiniz.",
    ],
    "pin_retry": [
        "Girdiğiniz şifre doğrulanamadı. Lütfen tekrar tuşlayın.",
        "Şifre hatalı görünüyor. Bir kez daha deneyebilirsiniz.",
    ],
    "balance": [
        "Teşekkürler, kimliğiniz doğrulandı. Demo hesabınızın kullanılabilir bakiyesi {amount}.",
        "Doğrulama tamamlandı. Vadesiz demo hesabınızda {amount} bulunuyor.",
    ],
}

HANDOFF_REPLIES: dict[str, list[str]] = {
    "card_security": [
        "Kartınızla ilgili acil bir durum anlıyorum. Sizi hemen bir temsilcimize aktarıyorum, lütfen hatta kalın.",
        "Kart güvenliğiniz bizim için öncelikli. Sizi şimdi kart güvenliği ekibimize bağlıyorum.",
    ],
    "complaint": [
        "Yaşadığınız sorun için üzgünüm. Sizi hemen bir temsilcimize aktarıyorum.",
        "Bunu duyduğuma üzüldüm. Sorununuzu dinlemesi için sizi bir temsilcimize bağlıyorum.",
    ],
    "agent_request": [
        "Elbette, sizi bir temsilcimize aktarıyorum.",
        "Tabii, hemen bir müşteri temsilcimize bağlıyorum, lütfen hatta kalın.",
    ],
    "balance_inquiry": [
        "Hesap bilgileri için kimlik doğrulaması gerekiyor. Sizi bir temsilcimize aktarıyorum.",
    ],
    "out_of_scope": [
        "Bu konuda size en doğru yardımı temsilcimiz verebilir. Sizi hemen aktarıyorum.",
        "Bu işlem için sizi uzman bir temsilcimize yönlendiriyorum.",
    ],
    "sensitive_data": [
        "Güvenliğiniz için kişisel bilgileri bu hatta paylaşmanızı istemiyoruz. Sizi bir temsilcimize aktarıyorum.",
    ],
    "fallback_limit": [
        "Size daha iyi yardımcı olabilmesi için sizi bir temsilcimize aktarıyorum.",
        "Sizi daha iyi anlayabilecek bir temsilcimize bağlıyorum.",
    ],
    "pin_failed": [
        "Şifreniz doğrulanamadı. Güvenliğiniz için sizi bir temsilcimize aktarıyorum.",
    ],
    "already_handed_off": [
        "Sizi temsilcimize aktarıyorum, lütfen hatta kalın.",
    ],
}

# Pilot scope: only these intents are answered automatically; everything else is handed off.
_ANSWERABLE = {"greeting", "branch_hours", "loan_info", "goodbye"}
_HANDOFF_INTENTS = {"card_security", "complaint", "agent_request", "balance_inquiry", "out_of_scope"}
_MAX_PIN_ATTEMPTS = 2


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    turns: int = 0
    fallback_streak: int = 0
    handed_off: bool = False
    awaiting: str | None = None  # None | "menu" | "pin" | "post"
    pin_attempts: int = 0


@dataclass(frozen=True)
class TurnResult:
    session_id: str
    intent: str
    confidence: float
    action: str  # answer | clarify | collect | handoff
    reply: str
    reasons: tuple[str, ...]
    redacted_input: str
    pii_found: dict[str, int]
    awaiting: str | None = None  # tells the client what the next turn expects (e.g. PIN entry)


class DialogueManager:
    def __init__(self, max_fallbacks: int = 2, mock_banking: bool = False, rng: random.Random | None = None):
        self.max_fallbacks = max_fallbacks
        self.mock_banking = mock_banking
        self.rng = rng or random.Random()

    # --- helpers -------------------------------------------------------------
    def _pick(self, table: dict[str, list[str]], key: str) -> str:
        return self.rng.choice(table[key])

    def _menu(self) -> str:
        bakiye = "bakiye öğrenmek için 3'ü, " if self.mock_banking else ""
        return ("Şube saatleri için 1'i, kredi başvurusu için 2'yi, " + bakiye
                + "temsilciye bağlanmak için 0'ı tuşlayabilir ya da sorunuzu söyleyebilirsiniz.")

    _POST_MENU = "Başka bir işlem için 1'i, temsilciye bağlanmak için 0'ı, görüşmeyi bitirmek için 9'u tuşlayın."

    def _result(self, session, intent, conf, action, reply, reasons, redacted, pii) -> TurnResult:
        return TurnResult(session.id, intent, conf, action, reply, tuple(reasons), redacted, pii, session.awaiting)

    def _handoff(self, session, intent, key, reasons, redacted, pii, conf=1.0) -> TurnResult:
        session.handed_off = True
        session.awaiting = None
        return self._result(session, intent, conf, "handoff", self._pick(HANDOFF_REPLIES, key), reasons, redacted, pii)

    def _answer(self, session, intent, reasons, redacted, pii, conf=0.9) -> TurnResult:
        session.fallback_streak = 0
        reply = self._pick(FAQ, intent)
        if intent == "greeting":
            session.awaiting = "menu"
            reply += " " + self._menu()
        elif intent == "goodbye":
            session.awaiting = None
        else:
            session.awaiting = "post"
            reply += " " + self._POST_MENU
        return self._result(session, intent, conf, "answer", reply, reasons, redacted, pii)

    def _fallback(self, session, reasons, redacted, pii, key="clarify") -> TurnResult:
        session.fallback_streak += 1
        if session.fallback_streak >= self.max_fallbacks:
            return self._handoff(session, "unknown", "fallback_limit", ["fallback_limit", *reasons], redacted, pii, 0.0)
        session.awaiting = "menu"
        reply = self._pick(FAQ, key) + " " + self._menu()
        return self._result(session, "unknown", 0.0, "clarify", reply, reasons, redacted, pii)

    def _start_balance(self, session, reasons, redacted, pii) -> TurnResult:
        if not self.mock_banking:
            return self._handoff(session, "balance_inquiry", "balance_inquiry", ["policy_handoff:balance_inquiry", *reasons], redacted, pii)
        session.awaiting = "pin"
        session.fallback_streak = 0
        return self._result(session, "balance_inquiry", 0.9, "collect", self._pick(FAQ, "pin_prompt"),
                            ["auth_required", *reasons], redacted, pii)

    # --- spoken / text turn ----------------------------------------------------
    def handle(self, session: Session, raw_text: str) -> TurnResult:
        session.turns += 1
        if session.awaiting == "pin":
            # Nothing said while a PIN is expected is logged (it may be a spoken PIN).
            redacted, pii = "[SPOKEN_INPUT_DURING_PIN]", {}
            if session.handed_off:
                return self._handoff(session, "handed_off", "already_handed_off", ["already_handed_off"], redacted, pii)
            return self._result(session, "balance_inquiry", 1.0, "collect", self._pick(FAQ, "pin_spoken"),
                                ["pin_spoken_refused"], redacted, pii)

        redacted, found = redact(raw_text)
        pii = dict(found)

        if session.handed_off:
            return self._handoff(session, "handed_off", "already_handed_off", ["already_handed_off"], redacted, pii)

        if SENSITIVE_KINDS & found.keys():
            return self._handoff(session, "sensitive_data", "sensitive_data", ["sensitive_data_shared"], redacted, pii)

        r = classify(redacted)
        # A negated security intent ("kartımı kaybetmedim" = I didn't lose my card) stays visible in the audit log.
        neg = [f"negated:{n}" for n in r.negated]

        if r.intent == "balance_inquiry":
            return self._start_balance(session, neg, redacted, pii)

        if r.intent in _HANDOFF_INTENTS:
            return self._handoff(session, r.intent, r.intent, [f"policy_handoff:{r.intent}", *neg], redacted, pii, r.confidence)

        if r.intent in _ANSWERABLE:
            return self._answer(session, r.intent, ["in_scope", *neg], redacted, pii, r.confidence)

        return self._fallback(session, ["low_confidence", *neg], redacted, pii)

    # --- keypad (DTMF) turn ----------------------------------------------------
    def handle_dtmf(self, session: Session, digits: str) -> TurnResult:
        session.turns += 1
        pii: dict[str, int] = {}
        if not re.fullmatch(r"[0-9*#]{1,8}", digits):
            raise ValueError("invalid DTMF")

        if session.awaiting == "pin":
            redacted = "[PIN]"
            if session.handed_off:
                return self._handoff(session, "handed_off", "already_handed_off", ["already_handed_off"], redacted, pii)
            if digits == "*":  # leave PIN entry to reach an agent (0 can be the first PIN digit)
                return self._handoff(session, "agent_request", "agent_request", ["dtmf", "policy_handoff:agent_request"], redacted, pii)
            if mockbank.verify_pin(digits.rstrip("#")):
                session.pin_attempts = 0
                session.awaiting = "post"
                amount = mockbank.format_tl(*mockbank.balance(session.id))
                reply = self._pick(FAQ, "balance").format(amount=amount) + " " + self._POST_MENU
                return self._result(session, "balance_inquiry", 1.0, "answer", reply,
                                    ["auth_ok", "mock_banking"], redacted, pii)
            session.pin_attempts += 1
            if session.pin_attempts >= _MAX_PIN_ATTEMPTS:
                return self._handoff(session, "balance_inquiry", "pin_failed", ["auth_failed"], redacted, pii)
            return self._result(session, "balance_inquiry", 1.0, "collect", self._pick(FAQ, "pin_retry"),
                                ["auth_retry"], redacted, pii)

        redacted = f"[DTMF:{digits}]"
        if session.handed_off:
            return self._handoff(session, "handed_off", "already_handed_off", ["already_handed_off"], redacted, pii)

        key = digits[0]
        if session.awaiting == "post":
            if key == "1":
                session.awaiting = "menu"
                session.fallback_streak = 0
                return self._result(session, "menu", 1.0, "answer", self._menu(), ["dtmf_menu"], redacted, pii)
            if key == "9":
                return self._answer(session, "goodbye", ["dtmf"], redacted, pii, 1.0)
        else:
            if key == "1":
                return self._answer(session, "branch_hours", ["dtmf"], redacted, pii, 1.0)
            if key == "2":
                return self._answer(session, "loan_info", ["dtmf"], redacted, pii, 1.0)
            if key == "3":
                return self._start_balance(session, ["dtmf"], redacted, pii)
        if key == "0":
            return self._handoff(session, "agent_request", "agent_request", ["dtmf", "policy_handoff:agent_request"], redacted, pii)
        return self._fallback(session, ["dtmf_invalid"], redacted, pii, key="invalid_key")
