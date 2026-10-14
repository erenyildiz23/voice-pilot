import pytest

from pilot.pii import iban_valid, luhn_valid, redact, tckn_valid

# Synthetic, algorithmically valid samples (not tied to any real person).
TCKN = "12345678264"
IBAN = "TR030006100000000000012345"
IBAN_SPACED = "TR03 0006 1000 0000 0000 0123 45"
CARD = "4111111111111111"


def test_validators():
    assert tckn_valid(TCKN)
    assert not tckn_valid("12345678265")
    assert not tckn_valid("01234567890")
    assert luhn_valid(CARD)
    assert not luhn_valid("4111111111111112")
    assert iban_valid(IBAN) and iban_valid(IBAN_SPACED)
    assert not iban_valid("TR030006100000000000012346")


def test_redacts_each_kind():
    text = f"TC {TCKN} iban {IBAN_SPACED} kart {CARD} tel 0532 123 45 67 mail ali@ornek.com"
    out, found = redact(text)
    assert TCKN not in out and CARD not in out and "ali@ornek.com" not in out
    assert "0532" not in out and "0123 45" not in out
    assert dict(found) == {"iban": 1, "card": 1, "national_id": 1, "phone": 1, "email": 1}


def test_phone_formats():
    for p in ["05321234567", "+90 532 123 45 67", "532 123 45 67", "0532-123-45-67"]:
        out, found = redact(f"beni {p} numarasından arayın")
        assert "[PHONE]" in out and found["phone"] == 1, p


def test_invalid_numbers_are_not_masked():
    # An 11-digit number with a failing checksum is not a national ID; must not be a false positive.
    out, found = redact("sipariş numaram 12345678265")
    assert out == "sipariş numaram 12345678265" and not found


def test_plain_text_untouched():
    out, found = redact("Şubeniz saat kaçta açılıyor?")
    assert out == "Şubeniz saat kaçta açılıyor?" and not found


def test_spoken_digit_runs_are_masked():
    out, found = redact("kimlik numaram bir iki üç dört beş altı yedi sekiz iki altı dört")
    assert "[DIGIT_SEQUENCE]" in out and found["digit_sequence"] == 1
    assert "bir iki" not in out


def test_short_spoken_numbers_are_not_masked():
    # Everyday phrases like "iki bin yirmi altı" (2026) or "bir iki gün" (a day or two) must not be masked.
    out, found = redact("bir iki gün içinde şubeye gelirim")
    assert out == "bir iki gün içinde şubeye gelirim" and not found


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Adım Ahmet Yılmaz kartımı kaybettim", "Adım [FULL_NAME] kartımı kaybettim"),
        ("adım ahmet yılmaz ve kartım çalındı", "adım [FULL_NAME] ve kartım çalındı"),
        ("Ad soyad: Mehmet Kaya", "Ad soyad: [FULL_NAME]"),
        ("adım Ali soyadım Demir", "adım [FULL_NAME] soyadım [FULL_NAME]"),
        ("Ayşe Hanım ile görüştüm", "[FULL_NAME] Hanım ile görüştüm"),
    ],
)
def test_names_are_masked(text, expected):
    out, found = redact(text)
    assert out == expected and found["full_name"] >= 1


@pytest.mark.parametrize("text", ["bir adım daha atalım", "adım adım anlatın", "Merhaba Hanım", "Şube saatleri nedir"])
def test_name_masking_false_positives(text):
    out, found = redact(text)
    assert out == text and not found


def test_names_are_not_sensitive():
    # Saying one's name is normal on a call: it is masked but is not a reason to hand off on its own.
    from pilot.pii import SENSITIVE_KINDS
    assert "full_name" not in SENSITIVE_KINDS
