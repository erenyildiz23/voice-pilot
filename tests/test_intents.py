import pytest

from pilot.intents import classify, tr_fold


def test_fold_handles_turkish_i():
    assert tr_fold("İyi günler, ŞUBE!") == "iyi gunler sube"
    assert tr_fold("IŞIK") == "isik"


@pytest.mark.parametrize(
    "text,intent",
    [
        ("Kartımı kaybettim", "kart_kayip"),
        ("kartim calindi", "kart_kayip"),
        ("Merhaba kartımı kaybettim", "kart_kayip"),  # öncelik: selamlamadan önce
        ("Bu bir rezalet, şikayet edeceğim", "sikayet"),
        ("Müşteri temsilcisine bağlanmak istiyorum", "temsilci_talebi"),
        ("Hesabımda ne kadar param var", "bakiye_sorgu"),
        ("Şubeniz saat kaçta açılıyor", "sube_saatleri"),
        ("sube hafta sonu acik mi", "sube_saatleri"),
        ("İhtiyaç kredisi başvurusu nasıl yapılıyor", "kredi_bilgi"),
        ("Teşekkür ederim", "tesekkur_kapanis"),
        ("Merhaba", "selamlama"),
        ("bugün hava çok güzel", "bilinmiyor"),
        # Olumsuzlama
        ("Kartımı kaybetmedim", "bilinmiyor"),
        ("Kartım bloke olmadı", "bilinmiyor"),
        ("Şikayetim yok", "bilinmiyor"),
        ("Şikayet etmiyorum", "bilinmiyor"),
        ("Dava açmayacağım", "bilinmiyor"),
        ("Kartımı kaybetmedim ama çalındı", "kart_kayip"),  # bir olumlu eşleşme yeter
        ("Kartım çalındı, hiçbir yerde bulamadım", "kart_kayip"),  # sonraki fiilin olumsuzu sayılmaz
        ("Bu rezalet değil mi", "sikayet"),  # soru eki olumsuzlama değil
        ("Kartımı kaybetmedim, şubeniz kaçta açılıyor", "sube_saatleri"),
        # Hazır set dışındaki ilk denemede kaçan güvenlik cümleleri
        ("Birisi kartımla alışveriş yapmış", "kart_kayip"),
        ("Kartımı bir yerde unuttum galiba", "kart_kayip"),
        ("Hiç memnun değilim", "sikayet"),
        # Kapsam dışı bankacılık talepleri
        ("Kredi kartı limitimi artırmak istiyorum", "kapsam_disi"),
        ("Şifremi unuttum", "kapsam_disi"),
        ("EFT yapmak istiyorum", "kapsam_disi"),
    ],
)
def test_classify(text, intent):
    assert classify(text).intent == intent


def test_negation_is_reported():
    r = classify("Kartımı kaybetmedim")
    assert r.negated == ("kart_kayip",)
