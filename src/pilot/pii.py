"""Turkish personal data redaction.

Goal: mask national ID (TCKN), IBAN, card number, phone and email before the text
reaches the classifier, the logs or any third-party service.

Limits (also listed in the docs):
- Digits written as numbers are caught with validators (TCKN checksum, Luhn, IBAN mod 97).
  Spoken digit runs ("sıfır beş üç iki ...") cannot be validated, so 9 or more consecutive
  digit words are masked as a whole and treated as sensitive.
- Full names are caught only after cue phrases: "adım ..." (my name is), "ismim ...",
  "soyadım ..." (my surname is), "adım soyadım ..." and capitalised "Ahmet Bey / Ayşe Hanım"
  (Mr/Ms). A name without a cue ("ben Ahmet, kartım...") and addresses are not caught.
- The audio itself has already been processed by the time text reaches this module.
"""
from __future__ import annotations

import re
from collections import Counter

from .intents import tr_fold

# Kinds treated as sensitive: if any appears in the conversation, the call goes to a human.
SENSITIVE_KINDS = frozenset({"national_id", "iban", "card", "digit_sequence"})

_IBAN_RE = re.compile(
    r"(?<![A-Za-z0-9])TR\s?\d{2}(?:\s?\d{4}){5}\s?\d{2}(?![A-Za-z0-9])", re.IGNORECASE
)
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_TCKN_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+90\s?|0090\s?|0)?\(?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Turkish digit words 0-9, with and without diacritics (STT sometimes drops them).
_DIGIT_WORD = r"(?:sıfır|sifir|bir|iki|üç|uc|dört|dort|beş|bes|altı|alti|yedi|sekiz|dokuz)"
_LETTERS = "A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû"
# Name cues: "adım soyadım", "ad soyad(ım)", "adı soyadı", "adım", "ismim", "soyadım".
_NAME_CUE_RE = re.compile(
    rf"(?<![{_LETTERS}])(?:ad[ıi]m\s+soyad[ıi]m|ad\s+soyad[ıi]?m?|ad[ıi]\s+soyad[ıi]|ad[ıi]m|[iİı]sm[iı]m|soyad[ıi]m)"
    rf"\s*[:,]?\s+([{_LETTERS}]+(?:\s+[{_LETTERS}]+){{0,2}})",
    re.IGNORECASE,
)
# Words that follow a cue but are not names: masking stops here ("bir adım daha" = "one more
# step" is not masked; in "adım Ahmet kartımı kaybettim" the word "kartımı" is kept for the
# intent). Compared after tr_fold.
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
    """Turkish national ID (TC kimlik no) checksum."""
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
        # Lower-case STT output: first name + surname (2 words); up to 3 if all are capitalised.
        limit = 3 if all(w[0].isupper() for w in words) else 2
        for w in words[:limit]:
            f = tr_fold(w)
            if f in _NAME_STOP_WORDS or f.startswith(_NAME_STOP_STEMS):
                break
            name.append(w)
        if not name:
            return m.group(0)
        found["full_name"] += 1
        head = m.group(0)[: m.start(1) - m.start(0)]
        tail = " ".join(words[len(name):])
        return head + "[FULL_NAME]" + (" " + tail if tail else "")

    # "adım Ali soyadım Demir": the second cue sits in the tail of the first match, so run again.
    for _ in range(3):
        nt = _NAME_CUE_RE.sub(repl, t)
        if nt == t:
            break
        t = nt

    def hon(m: re.Match) -> str:
        if tr_fold(m.group(0).split()[0]).startswith(_NAME_STOP_STEMS + ("selam", "gunaydin", "sayin")):
            return m.group(0)  # "Merhaba Hanım" (hello madam), "Sayın Bey" (dear sir) are not names
        found["full_name"] += 1
        return "[FULL_NAME]"

    return _HONORIFIC_RE.sub(hon, t)


def redact(text: str) -> tuple[str, Counter]:
    """Replace personal data in the text with placeholders.

    Returns: (redacted text, count per kind).
    Order matters: spoken digit run > IBAN > card > national ID > phone > email > full name.
    Placeholders contain no digits, so they never collide with later patterns.
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
    out = apply(out, _SPOKEN_RE, "digit_sequence", "[DIGIT_SEQUENCE]", None)
    out = apply(out, _IBAN_RE, "iban", "[IBAN]", iban_valid)
    out = apply(out, _CARD_RE, "card", "[CARD]", lambda r: luhn_valid(_digits_only(r)))
    out = apply(out, _TCKN_RE, "national_id", "[NATIONAL_ID]", tckn_valid)
    out = apply(out, _PHONE_RE, "phone", "[PHONE]", None)
    out = apply(out, _EMAIL_RE, "email", "[EMAIL]", None)
    out = _redact_names(out, found)
    return out, found
