"""Kural tabanlı Türkçe niyet sınıflandırıcı.

Bilerek basit tutuldu: pilotun ilk haftasında amaç "en iyi model" değil,
hangi çağrıların güvenle otomatikleşebileceğini ve hangilerinin insana
gitmesi gerektiğini ölçmek. Gerçek çağrı verisi gelince bu modül bir
sınıflandırıcıyla değiştirilebilir; arayüz (classify) aynı kalır.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def tr_fold(text: str) -> str:
    """Küçük harfe çevirir, Türkçe karakterleri ASCII'ye indirger, noktalamayı atar.

    STT çıktısı bazen aksanlı harfleri düşürür; eşleştirmeyi buna dayanıklı yapar.
    """
    t = text.replace("İ", "i").replace("I", "ı").lower().translate(_FOLD)
    t = re.sub(r"[^a-z0-9\[\]\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    negated: tuple[str, ...] = ()  # olumsuzlandığı için atlanan niyetler (denetim için)


# Olumsuzlama: eşleşen sözcüğün kalanında olumsuz ek ("kaybet-medim", "çalın-madı",
# "kaybet-miyorum") ya da hemen ardından "yok/değil" veya olumsuz yardımcı fiil
# ("bloke olmadı", "şikayet etmiyorum", "dava açmayacağım"). "Rezalet değil mi"
# soru ekiyle olumsuzlama sayılmaz.
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


# (niyet adı, [her biri en az bir kez eşleşmesi gereken regex grupları], olumsuzlanabilir grup)
# Liste sırası aynı zamanda öncelik sırasıdır: güvenlik ve devir niyetleri önce.
# Olumsuzlanabilir grubun EN AZ BİR olumsuzlanmamış eşleşmesi varsa niyet geçerlidir:
# "kaybetmedim ama çalındı" yine kart_kayip olur (güvenli yön).
_RULES: list[tuple[str, list[str], int | None]] = [
    # İzinsiz işlem (dolandırıcılık) de kart güvenliği sayılır: "birisi kartımla alışveriş yapmış".
    ("kart_kayip", [r"kart", r"kayb|kaybol|calin|yutt|bloke|kayip|unut|izinsiz|habersiz|dolandir"
                    r"|alisveris yap|harcama yap|para cek|benim yapmadigim"], 1),
    ("sikayet", [r"sikayet|rezalet|berbat|kabul edilemez|dava|mahkeme|skandal|magdur"
                 r"|memnun degil|ilgilenmedi|ilgilenmiyor"], 0),
    ("temsilci_talebi", [r"temsilci|musteri hizmet|yetkili|insanla|biriyle|canli destek|operator"], None),
    ("bakiye_sorgu", [r"bakiye|hesap ozet|hesabimda ne kadar|ne kadar param|kalan borc|kart borc"], None),
    # Bankacılık talebi ama pilot kapsamı dışında: "anlamadım" döngüsü yerine doğrudan devir.
    ("kapsam_disi", [r"limit|sifre|parola|hesap ac|hesabimi kapat|giris yapamiyor|giris yapamadim"
                     r"|kredi karti basvur|kart basvur|havale|\beft\b|fatura|aidat"], None),
    ("sube_saatleri", [r"sube|subeniz|subeler|mesai", r"saat|acik|kapali|kacta|calisma|hafta sonu"], None),
    ("kredi_bilgi", [r"kredi", r"basvur|nasil|sart|gerek|belge|vade|faiz"], None),
    ("tesekkur_kapanis", [r"tesekkur|sagol|hosca kal|gorusuruz|baska bir sey yok|yeterli"], None),
    ("selamlama", [r"^(merhaba|selam|iyi gunler|gunaydin|iyi aksamlar|alo)\b"], None),
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
    return IntentResult("bilinmiyor", 0.0, tuple(negated))
