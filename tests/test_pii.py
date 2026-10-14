import pytest

from pilot.pii import iban_valid, luhn_valid, redact, tckn_valid

# Sentetik, algoritmik olarak geçerli örnekler (gerçek kişiye ait değil).
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
    assert dict(found) == {"iban": 1, "kart": 1, "tckn": 1, "telefon": 1, "eposta": 1}


def test_phone_formats():
    for p in ["05321234567", "+90 532 123 45 67", "532 123 45 67", "0532-123-45-67"]:
        out, found = redact(f"beni {p} numarasından arayın")
        assert "[TELEFON]" in out and found["telefon"] == 1, p


def test_invalid_numbers_are_not_masked():
    # Sağlama toplamı tutmayan 11 haneli sayı TCKN değildir; yanlış pozitif üretmemeli.
    out, found = redact("sipariş numaram 12345678265")
    assert out == "sipariş numaram 12345678265" and not found


def test_plain_text_untouched():
    out, found = redact("Şubeniz saat kaçta açılıyor?")
    assert out == "Şubeniz saat kaçta açılıyor?" and not found


def test_spoken_digit_runs_are_masked():
    out, found = redact("kimlik numaram bir iki üç dört beş altı yedi sekiz iki altı dört")
    assert "[SAYI_DIZISI]" in out and found["sayi_dizisi"] == 1
    assert "bir iki" not in out


def test_short_spoken_numbers_are_not_masked():
    # "iki bin yirmi altı", "bir iki gün" gibi sıradan kullanımlar maskelenmemeli.
    out, found = redact("bir iki gün içinde şubeye gelirim")
    assert out == "bir iki gün içinde şubeye gelirim" and not found


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Adım Ahmet Yılmaz kartımı kaybettim", "Adım [AD_SOYAD] kartımı kaybettim"),
        ("adım ahmet yılmaz ve kartım çalındı", "adım [AD_SOYAD] ve kartım çalındı"),
        ("Ad soyad: Mehmet Kaya", "Ad soyad: [AD_SOYAD]"),
        ("adım Ali soyadım Demir", "adım [AD_SOYAD] soyadım [AD_SOYAD]"),
        ("Ayşe Hanım ile görüştüm", "[AD_SOYAD] Hanım ile görüştüm"),
    ],
)
def test_names_are_masked(text, expected):
    out, found = redact(text)
    assert out == expected and found["ad_soyad"] >= 1


@pytest.mark.parametrize("text", ["bir adım daha atalım", "adım adım anlatın", "Merhaba Hanım", "Şube saatleri nedir"])
def test_name_masking_false_positives(text):
    out, found = redact(text)
    assert out == text and not found


def test_names_are_not_sensitive():
    # Ad söylemek çağrı merkezinde olağandır: maskelenir ama tek başına devir sebebi değildir.
    from pilot.pii import SENSITIVE_KINDS
    assert "ad_soyad" not in SENSITIVE_KINDS
