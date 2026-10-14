# STT ölçümü: sentetik Türkçe ses (14 Ekim 2026)

**Yöntem:** Prototipin en riskli bulduğu cümleler ElevenLabs TTS ile seslendirildi (`eleven_multilingual_v2`, "Şevval - Call Center" sesi), ardından ElevenLabs STT ile yazıya çevrildi (`eleven_scribe_v1`). Çıkan metin `DialogueManager`'dan geçirildi. Ham veriler: [stt_ses_olcumu.csv](stt_ses_olcumu.csv).

**Bu ölçüm neyi göstermez:** Ses temiz, stüdyo kalitesinde ve aynı firmanın TTS'inden geliyor. Gerçek telefon sesi (8 kHz, gürültü, şive, yarıda kesilen cümle) değil. Sonuç **en iyimser durumdur**, üretim performansı iddiası değildir.

## Sonuç

| Ölçüt | Sonuç |
| --- | --- |
| Cümle | 8 (planlanan 10; 2'si bütçe nedeniyle çalıştırılmadı, aşağıya bak) |
| Kelime hata oranı (tr_fold sonrası) | 0/48 = %0 |
| Doğru niyet + eylem | 8/8 |
| Güvenlik devri kaçırma | 0 |

## Asıl öğrenilenler

1. **Olumsuz ek korunuyor.** "kaybet**me**dim" STT'de düşmedi; olumsuzlama mantığının dayandığı varsayım temiz seste tutuyor. Telefon sesinde ayrıca ölçülmeli (risk 4).
2. **Sözlü rakamlar rakama çevrilmedi.** Scribe "bir iki üç ..." dizisini sözcük olarak bıraktı; bu yüzden TCKN sağlama algoritması değil, `sayi_dizisi` maskesi devreye girdi. STT ayarı ya da model değişip rakam üretirse, `tckn` maskesi devreye girer; iki yol da test altında.
3. **Ad-soyad noktalama ile geldi** ("Adım Ayşe Demir,") ve maskelendi; niyet (kredi_bilgi) korundu.
4. **Ses buluttaydı.** Bu ölçümde ses, maskeleme öncesi ElevenLabs'a gitti. Bu yüzden gerçek müşteri sesiyle değil, yalnızca sentetik test cümleleriyle yapıldı (risk 1).

## Maliyet ve aksaklık notu

- Seslendirme cümle başına 20–65 kredi, çeviri tahmini cümle başına ~33 kredi.
- Bağlayıcı üzerinden paralel istekler 429 (hız sınırı) verdi; tek tek gönderim çalıştı.
- 8. cümlenin çevirisi sırasında platform sesi yeniden üretti ve çeviri için 416 kredilik bir tutar gösterdi. Beklenen bütçeyi aşma ihtimali yüzünden kalan 2 cümle ("Hiç memnun değilim, temsilciyle görüşmek istiyorum", "Hesabımda ne kadar param var?") çalıştırılmadı.
- **Ders (FDE açısından):** Müşteri ortamında da sağlayıcı faturalandırması ve hız sınırları pilotun ilk gününde ölçülmeli; tahmin ile gerçekleşen tutar farklı olabiliyor.

## Sıradaki ölçüm

Gölge mod haftasında, izinli ve maskelenmiş **gerçek telefon kayıtlarıyla** aynı tablo: WER, olumsuz ek kaybı, rakam/sözcük biçimi ve tur başına gecikme.
