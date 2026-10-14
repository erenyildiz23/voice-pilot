import random

from pilot.dialogue import FAQ, HANDOFF_REPLIES, DialogueManager, Session
from pilot.mockbank import DEMO_PIN, balance, format_tl
from pilot.pii import redact

TCKN = "12345678264"
dm = DialogueManager()


def test_in_scope_answer():
    r = dm.handle(Session(), "Şubeniz saat kaçta açılıyor?")
    assert r.action == "answer" and r.intent == "branch_hours"
    assert any(r.reply.startswith(v) for v in FAQ["branch_hours"])


def test_sensitive_data_triggers_handoff_and_is_masked():
    s = Session()
    r = dm.handle(s, f"Kimlik numaram {TCKN} bakiyemi öğrenmek istiyorum")
    assert r.action == "handoff" and "sensitive_data_shared" in r.reasons
    assert TCKN not in r.redacted_input and "[NATIONAL_ID]" in r.redacted_input
    assert s.handed_off


def test_security_intents_hand_off_immediately():
    for text in ["Kartım çalındı", "Bu rezalet", "Temsilciye bağla", "Bakiyem ne kadar"]:
        assert dm.handle(Session(), text).action == "handoff", text


def test_two_consecutive_fallbacks_hand_off():
    s = Session()
    assert dm.handle(s, "mavi bulut").action == "clarify"
    assert dm.handle(s, "kırmızı elma").action == "handoff"


def test_fallback_streak_resets_after_valid_turn():
    s = Session()
    assert dm.handle(s, "mavi bulut").action == "clarify"
    assert dm.handle(s, "Merhaba").action == "answer"
    assert dm.handle(s, "kırmızı elma").action == "clarify"


def test_once_handed_off_stays_handed_off():
    s = Session()
    dm.handle(s, "Kartım çalındı")
    r = dm.handle(s, "Şube saatleri nedir")
    assert r.action == "handoff" and "already_handed_off" in r.reasons


def test_replies_never_contain_pii():
    # Text sent to TTS is only a template; it never echoes caller input.
    r = dm.handle(Session(), f"TC {TCKN} telefon 05321234567 şube saatleri")
    _, found = redact(r.reply)
    assert not found


def test_negated_security_intent_is_not_handed_off_but_is_logged():
    r = dm.handle(Session(), "Kartımı kaybetmedim")
    assert r.action == "clarify" and "negated:card_security" in r.reasons


def test_out_of_scope_banking_request_hands_off_without_clarify_loop():
    r = dm.handle(Session(), "Kredi kartı limitimi artırmak istiyorum")
    assert r.action == "handoff" and "policy_handoff:out_of_scope" in r.reasons


def test_name_is_masked_and_intent_still_found():
    r = dm.handle(Session(), "Adım Ahmet Yılmaz, kartımı kaybettim")
    assert r.intent == "card_security" and r.action == "handoff"
    assert "Ahmet" not in r.redacted_input and r.pii_found == {"full_name": 1}


def test_replies_vary_but_stay_within_templates():
    d = DialogueManager(rng=random.Random(1))
    seen = {d.handle(Session(), "Şubeniz kaçta açılıyor").reply for _ in range(30)}
    assert len(seen) > 1
    assert all(any(x.startswith(v) for v in FAQ["branch_hours"]) for x in seen)


def test_greeting_offers_dtmf_menu_and_keys_work():
    s = Session()
    r = dm.handle(s, "Merhaba")
    assert "1'i" in r.reply and r.awaiting == "menu"
    assert dm.handle_dtmf(s, "1").intent == "branch_hours"
    assert dm.handle_dtmf(s, "1").intent == "menu"  # in the post-answer menu, 1 = main menu
    assert dm.handle_dtmf(s, "2").intent == "loan_info"
    assert dm.handle_dtmf(s, "9").intent == "goodbye"


def test_dtmf_zero_hands_off_and_invalid_counts_as_fallback():
    s = Session()
    assert dm.handle_dtmf(s, "7").action == "clarify"
    assert dm.handle_dtmf(s, "8").action == "handoff"
    assert dm.handle_dtmf(Session(), "0").intent == "agent_request"


def test_balance_without_mock_banking_hands_off():
    assert dm.handle(Session(), "Bakiyem ne kadar").action == "handoff"
    assert dm.handle_dtmf(Session(), "3").action == "handoff"


bank = DialogueManager(mock_banking=True)


def test_balance_flow_with_pin():
    s = Session()
    r = bank.handle(s, "Bakiyemi öğrenmek istiyorum")
    assert r.action == "collect" and r.awaiting == "pin"
    r = bank.handle_dtmf(s, DEMO_PIN)
    assert r.action == "answer" and format_tl(*balance(s.id)) in r.reply
    assert DEMO_PIN not in r.reply and r.redacted_input == "[PIN]"


def test_wrong_pin_twice_hands_off():
    s = Session()
    bank.handle_dtmf(s, "3")
    assert bank.handle_dtmf(s, "0000").action == "collect"
    r = bank.handle_dtmf(s, "1111")
    assert r.action == "handoff" and "auth_failed" in r.reasons


def test_spoken_pin_is_refused_and_not_logged():
    s = Session()
    bank.handle(s, "Bakiye")
    r = bank.handle(s, "bir iki üç dört")
    assert r.action == "collect" and r.redacted_input == "[SPOKEN_INPUT_DURING_PIN]"
    assert "dört" not in r.redacted_input


def test_star_during_pin_reaches_agent():
    s = Session()
    bank.handle(s, "Bakiye")
    assert bank.handle_dtmf(s, "*").intent == "agent_request"


def test_pin_may_start_with_zero():
    # Found in an end-to-end Chrome test: 0 used to exit PIN entry, so PINs starting with 0 could not be entered.
    s = Session()
    bank.handle(s, "Bakiye")
    r = bank.handle_dtmf(s, "0123")
    assert r.action == "collect" and "auth_retry" in r.reasons


def test_security_intents_never_answered_even_with_mock_banking():
    for text in ["Kartım çalındı", "Bu rezalet"]:
        assert bank.handle(Session(), text).action == "handoff", text
