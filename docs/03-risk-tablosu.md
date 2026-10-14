# 3. Risk tablosu

| # | Risk | Etki | Önlem | Durum |
| --- | --- | --- | --- | --- |
| 1 | Ses buluta gider, maskeleme sesi koruyamaz | KVKK ve müşteri şartı ihlali | `ALLOW_CLOUD_AUDIO=false` varsayılan; müşteri onayı, hukuk değerlendirmesi, sağlayıcı sözleşme ve veri saklama koşullarının doğrulanması; ya da yerel model | Açık, müşteri kararı |
| 2 | Arayan kimlik/kart bilgisini söyler | Kişisel veri loga ve sağlayıcıya sızar | Rakam ve sözlü rakam maskeleme, hassas veri görülünce devir | Kısmen kapalı (aşağıdaki sınırlar) |
| 3 | STT Türkçe'yi telefon sesinde yanlış çevirir | Yanlış niyet, kötü deneyim | Düşük güvende netleştirme, ardından devir; pilotta gerçek çağrıyla WER ölçümü | Ölçülecek |
| 4 | Olumsuzlama yanlış anlaşılır | "kaybetmedim" sanılan gerçek kayıp devredilmez | Yalnızca güvenlik eylem sözcüğünün tüm geçişleri olumsuzsa niyet atlanır; "değil mi" olumsuzlama sayılmaz; atlanan niyet denetim kaydına yazılır. Gölge modda `negated:*` satırları insan kararıyla tek tek karşılaştırılır | Kısmen kapalı, gerçek sesle ölçülecek |
| 5 | Üretken model yanlış bilgi verir | İtibar, hukuki risk | Pilotta üretken yanıt yok, yalnızca onaylı şablon | Kapalı |
| 6 | Sağlayıcı kesintisi/gecikme | Çağrı kopar, arayan sessizlikte bekler | Hata anında insana devir (502 doğrulandı); ilk ölçümde tur 4,8–5,4 sn, telefon için yavaş. Akışlı STT/TTS ve hızlı model denenecek | Ölçüldü, iyileştirme gerekli |
| 9 | Ses lisansı/plan kısıtı | Seçilen ses API'de 402 verir | Ses seçimini plan ve lisansla birlikte müşteriyle kararlaştır; yedek olarak hazır ses | İlk çalıştırmada yaşandı |
| 10 | Hesap verisi (bakiye) bulut TTS'e gider | Kimlik doğrulaması sonrası bile kişisel finansal veri KVKK kapsamında üçüncü tarafa çıkar | Demo modda yalnızca uydurma bakiye; gerçek entegrasyonda ya yerel TTS ya da bakiye için önceden kaydedilmiş rakam sesleri (TTS'e sayı gitmez) | Tasarım kararı, müşteriyle |
| 7 | Aydınlatma/rıza eksikliği | KVKK | Çağrı başında onaylı bildirim | Müşteri metni bekleniyor |
| 8 | Bellek içi oturumlar yeniden başlatmada kaybolur | Devir bağlamı kaybı | Pilot için kabul; üretimde dış oturum deposu | Biliniyor |

## Maskelemenin bilinen sınırları

- TCKN, IBAN, kart (Luhn), telefon, e-posta, 9+ sözlü rakam dizisi ve ipuçlu ad-soyadı ("adım ...", "ismim ...", "Ayşe Hanım") yakalar. İpucusuz ad, adres, doğum tarihi yakalanmaz.
- Rakamlar sözcük içine gömülüyse ("sifirbes...") ya da 8 sözlü rakamdan kısa parçalara bölünmüşse kaçabilir.
