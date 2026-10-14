"""Türkçe kişisel veri maskeleme.

Amaç: metin sınıflandırıcıya, loglara ve (varsa) üçüncü taraf servislere
gitmeden önce TC kimlik no, IBAN, kart no, telefon ve e-postayı maskelemek.

Sınırlar (dokümanda da yazılı):
- Rakam olarak yazılmış veriyi doğrulayıcılarla (TCKN, Luhn, IBAN mod 97) yakalar.
  Sözlü rakam dizisini ("sıfır beş üç iki ...") ise doğrulayamaz; 9 ya da daha fazla
  ardışık rakam sözcüğünü topluca maskeler ve hassas sayar.
- Ad-soyadı yalnızca ipucu kalıplarıyla yakalar: "adım ...", "ismim ...", "soyadım ...",
  "adım soyadım ..." ve büyük harfli "Ahmet Bey / Ayşe Hanım". İpucusuz geçen ad
  ("ben Ahmet, kartım...") ve adres yakalanmaz.
- Ses kaydının kendisi bu modülden önce zaten işlenmiş olur.
"""
from __future__ import annotations

import re
from collections import Counter

from .intents import tr_fold

# Hassas sayılan türler: bunlar konuşmada geçerse insana devredilir.
SENSITIVE_KINDS = frozenset({"tckn", "iban", "kart", "sayi_dizisi"})

_IBAN_RE = re.compile(
    r"(?<![A-Za-z0-9])TR\s?\d{2}(?:\s?\d{4}){5}\s?\d{2}(?![A-Za-z0-9])", re.IGNORECASE
)
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_TCKN_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+90\s?|0090\s?|0)?\(?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DIGIT_WORD = r"(?:sıfır|sifir|bir|iki|üç|uc|dört|dort|beş|bes|altı|alti|yedi|sekiz|dokuz)"
_LETTERS = "A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû"
_NAME_CUE_RE = re.compile(
    rf"(?<![{_LETTERS}])(?:ad[ıi]m\s+soyad[ıi]m|ad\s+soyad[ıi]?m?|ad[ıi]\s+soyad[ıi]|ad[ıi]m|[iİı]sm[iı]m|soyad[ıi]m)"
    rf"\s*[:,]?\s+([{_LETTERS}]+(?:\s+[{_LETTERS}]+){{0,2}})",
    re.IGNORECASE,
)
# İpucundan sonra gelen ama ad olmayan sözcükler: burada durulur ("bir adım daha" maskelenmez,
# "adım Ahmet kartımı kaybettim" içinde "kartımı" niyet için korunur). Karşılaştırma tr_fold ile.
_NAME_STOP_WORDS = frozenset("ve ama fakat ile icin ben benim bu su o de da daha adim mi mu ne neydi".split())
_NAME_STOP_STEMS = (
    "soyad", "kart", "sube", "kredi", "hesab", "hesap", "sikayet", "temsilci", "bakiye", "numara",
    "telefon", "kimlik", "iban", "sifre", "bugun", "dun", "yarin", "merhaba", "iyi", "tesekkur",
)
_HONORIFIC_RE = re.compile(
    r"(?<![A-Za-zÇĞİÖŞÜçğıöşü])[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?(?=\s+(?:Bey|Hanım|bey|hanım)\b)"
)
_SPOKEN_RE = re.compile(rf"(?<!\w)(?:{_DIGIT_WORD}[\s,.-]+){{8,}}{_DIGIT_WORD}(?!\w)", re.IGNORECASE)


def tckn_valid(s: str) -> bool:
    """TC kimlik numarası sağlama algoritması."""
    if not (len(s) == 11 and s.isdigit() and s[0] != "0"):
        return False
    d = [int(c) for c in s]
    d10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    d11 = sum(d[:10]) % 10
    return d[9] == d10 and d[10] == d11


def luhn_valid(s: str) -> bool:
    if not s.isdigit() or not 13 <= len(s) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def iban_valid(raw: str) -> bool:
    s = re.sub(r"\s+", "", raw).upper()
    if not re.fullmatch(r"TR\d{24}", s):
        return False
    rearranged = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


def _digits_only(raw: str) -> str:
    return re.sub(r"[\s-]", "", raw)


def _redact_names(t: str, found: Counter) -> str:
    def repl(m: re.Match) -> str:
        words = m.group(1).split()
        name: list[str] = []
        # Küçük harfli STT çıktısında ad + soyad (2 sözcük); hepsi büyük harfliyse 3'e kadar.
        limit = 3 if all(w[0].isupper() for w in words) else 2
        for w in words[:limit]:
            f = tr_fold(w)
            if f in _NAME_STOP_WORDS or f.startswith(_NAME_STOP_STEMS):
                break
            name.append(w)
        if not name:
            return m.group(0)
        found["ad_soyad"] += 1
        head = m.group(0)[: m.start(1) - m.start(0)]
        tail = " ".join(words[len(name):])
        return head + "[AD_SOYAD]" + (" " + tail if tail else "")

    # "adım Ali soyadım Demir": ikinci ipucu ilk eşleşmenin kuyruğunda kalır, bir tur daha.
    for _ in range(3):
        nt = _NAME_CUE_RE.sub(repl, t)
        if nt == t:
            break
        t = nt

    def hon(m: re.Match) -> str:
        if tr_fold(m.group(0).split()[0]).startswith(_NAME_STOP_STEMS + ("selam", "gunaydin", "sayin")):
            return m.group(0)  # "Merhaba Hanım", "Sayın Bey" ad değildir
        found["ad_soyad"] += 1
        return "[AD_SOYAD]"

    return _HONORIFIC_RE.sub(hon, t)


def redact(text: str) -> tuple[str, Counter]:
    """Metindeki kişisel verileri yer tutucuyla değiştirir.

    Döner: (maskelenmiş metin, tür başına bulunan sayı).
    Sıra önemli: sözlü rakam dizisi > IBAN > kart > TCKN > telefon > e-posta > ad-soyad. Yer
    tutucular rakam içermediği için sonraki desenlerle çakışmaz.
    """
    found: Counter = Counter()

    def apply(t: str, pattern: re.Pattern, kind: str, label: str, check) -> str:
        def repl(m: re.Match) -> str:
            raw = m.group(0)
            if check is not None and not check(raw):
                return raw
            found[kind] += 1
            return label

        return pattern.sub(repl, t)

    out = text
    out = apply(out, _SPOKEN_RE, "sayi_dizisi", "[SAYI_DIZISI]", None)
    out = apply(out, _IBAN_RE, "iban", "[IBAN]", iban_valid)
    out = apply(out, _CARD_RE, "kart", "[KART]", lambda r: luhn_valid(_digits_only(r)))
    out = apply(out, _TCKN_RE, "tckn", "[TCKN]", tckn_valid)
    out = apply(out, _PHONE_RE, "telefon", "[TELEFON]", None)
    out = apply(out, _EMAIL_RE, "eposta", "[EPOSTA]", None)
    out = _redact_names(out, found)
    return out, found
