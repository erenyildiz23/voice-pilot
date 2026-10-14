"""Rule-based Turkish intent classifier.

Deliberately simple: in the first week of the pilot the goal is not "the best model" but
measuring which calls can be automated safely and which must go to a human. Once real call
data is available this module can be replaced by a trained classifier; the interface
(classify) stays the same.

The patterns below match Turkish text after tr_fold (lower-cased, diacritics removed).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def tr_fold(text: str) -> str:
    """Lower-case with Turkish İ/I rules, fold Turkish letters to ASCII, drop punctuation.

    STT output sometimes drops diacritics; this makes matching robust to that.
    """
    t = text.replace("İ", "i").replace("I", "ı").lower().translate(_FOLD)
    t = re.sub(r"[^a-z0-9\[\]\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    negated: tuple[str, ...] = ()  # intents skipped because they were negated (for the audit log)


# Negation: a negative suffix in the rest of the matched word ("kaybet-medim" = I did not lose,
# "çalın-madı", "kaybet-miyorum"), or right after it "yok/değil" (none/not) or a negated
# auxiliary verb ("bloke olmadı", "şikayet etmiyorum", "dava açmayacağım").
# "Rezalet değil mi" ("isn't it a disgrace") is a tag question, not a negation.
_NEG = r"m(adi|edi|iyor|uyor|az|ez|ayaca|eyece|amis|emis)"
_NEG_SUFFIX = re.compile(_NEG)
_NEG_NEXT = re.compile(rf"^(yok|degil\w*|(ol|et|edil|yap|ac|yasa){_NEG}\w*)$")


def _negated(t: str, m: re.Match) -> bool:
    rest = re.match(r"[a-z]*", t[m.end():]).group(0)
    if _NEG_SUFFIX.search(rest):
        return True
    nxt = t[m.end() + len(rest):].split()
    if not nxt or not _NEG_NEXT.match(nxt[0]):
        return False
    return not (nxt[0] == "degil" and len(nxt) > 1 and re.fullmatch(r"m[iu]", nxt[1]))


# (intent, [regex groups that must each match at least once], index of the negatable group)
# List order is also priority order: security and handoff intents come first.
# An intent holds if the negatable group has AT LEAST ONE non-negated match:
# "kaybetmedim ama çalındı" (didn't lose it but it was stolen) is still card_security (safe side).
_RULES: list[tuple[str, list[str], int | None]] = [
    # Unauthorised transactions (fraud) count as card security: "birisi kartımla alışveriş yapmış".
    ("card_security", [r"kart", r"kayb|kaybol|calin|yutt|bloke|kayip|unut|izinsiz|habersiz|dolandir"
                       r"|alisveris yap|harcama yap|para cek|benim yapmadigim"], 1),
    ("complaint", [r"sikayet|rezalet|berbat|kabul edilemez|dava|mahkeme|skandal|magdur"
                   r"|memnun degil|ilgilenmedi|ilgilenmiyor"], 0),
    ("agent_request", [r"temsilci|musteri hizmet|yetkili|insanla|biriyle|canli destek|operator"], None),
    ("balance_inquiry", [r"bakiye|hesap ozet|hesabimda ne kadar|ne kadar param|kalan borc|kart borc"], None),
    # Banking requests outside the pilot scope (limit, password, transfers...): hand off directly
    # instead of looping on "I didn't understand".
    ("out_of_scope", [r"limit|sifre|parola|hesap ac|hesabimi kapat|giris yapamiyor|giris yapamadim"
                      r"|kredi karti basvur|kart basvur|havale|\beft\b|fatura|aidat"], None),
    ("branch_hours", [r"sube|subeniz|subeler|mesai", r"saat|acik|kapali|kacta|calisma|hafta sonu"], None),
    ("loan_info", [r"kredi", r"basvur|nasil|sart|gerek|belge|vade|faiz"], None),
    ("goodbye", [r"tesekkur|sagol|hosca kal|gorusuruz|baska bir sey yok|yeterli"], None),
    ("greeting", [r"^(merhaba|selam|iyi gunler|gunaydin|iyi aksamlar|alo)\b"], None),
]


def classify(text: str) -> IntentResult:
    t = tr_fold(text)
    negated: list[str] = []
    for name, groups, neg_idx in _RULES:
        if not all(re.search(g, t) for g in groups):
            continue
        if neg_idx is not None and all(_negated(t, m) for m in re.finditer(groups[neg_idx], t)):
            negated.append(name)
            continue
        return IntentResult(name, 0.9, tuple(negated))
    return IntentResult("unknown", 0.0, tuple(negated))
