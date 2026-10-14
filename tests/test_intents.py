import pytest

from pilot.intents import classify, tr_fold


def test_fold_handles_turkish_i():
    assert tr_fold("İyi günler, ŞUBE!") == "iyi gunler sube"
    assert tr_fold("IŞIK") == "isik"


@pytest.mark.parametrize(
    "text,intent",
    [
        ("Kartımı kaybettim", "card_security"),
        ("kartim calindi", "card_security"),
        ("Merhaba kartımı kaybettim", "card_security"),  # priority: before greeting
        ("Bu bir rezalet, şikayet edeceğim", "complaint"),
        ("Müşteri temsilcisine bağlanmak istiyorum", "agent_request"),
        ("Hesabımda ne kadar param var", "balance_inquiry"),
        ("Şubeniz saat kaçta açılıyor", "branch_hours"),
        ("sube hafta sonu acik mi", "branch_hours"),
        ("İhtiyaç kredisi başvurusu nasıl yapılıyor", "loan_info"),
        ("Teşekkür ederim", "goodbye"),
        ("Merhaba", "greeting"),
        ("bugün hava çok güzel", "unknown"),
        # Negation
        ("Kartımı kaybetmedim", "unknown"),
        ("Kartım bloke olmadı", "unknown"),
        ("Şikayetim yok", "unknown"),
        ("Şikayet etmiyorum", "unknown"),
        ("Dava açmayacağım", "unknown"),
        ("Kartımı kaybetmedim ama çalındı", "card_security"),  # one non-negated match is enough
        ("Kartım çalındı, hiçbir yerde bulamadım", "card_security"),  # a negated later verb does not count
        ("Bu rezalet değil mi", "complaint"),  # tag question, not a negation
        ("Kartımı kaybetmedim, şubeniz kaçta açılıyor", "branch_hours"),
        # Security sentences missed in the first out-of-set probe
        ("Birisi kartımla alışveriş yapmış", "card_security"),
        ("Kartımı bir yerde unuttum galiba", "card_security"),
        ("Hiç memnun değilim", "complaint"),
        # Out-of-scope banking requests
        ("Kredi kartı limitimi artırmak istiyorum", "out_of_scope"),
        ("Şifremi unuttum", "out_of_scope"),
        ("EFT yapmak istiyorum", "out_of_scope"),
    ],
)
def test_classify(text, intent):
    assert classify(text).intent == intent


def test_negation_is_reported():
    r = classify("Kartımı kaybetmedim")
    assert r.negated == ("card_security",)
