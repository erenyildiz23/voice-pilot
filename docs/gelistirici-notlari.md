# Geliştirici notları

Türkçe sesli asistan pilotu: çağrı merkezi için, kişisel veri sızdırmayan, belirsizlikte insana devreden bir prototip.

## Komutlar
- Test: `python -m pytest -q`
- Duman değerlendirme: `python eval/run_eval.py` (sızıntı ya da devir kaçırma varsa çıkış kodu 1)
- Sunucu: `PYTHONPATH=src uvicorn pilot.app:app --reload --env-file .env` (demo sayfası: `/`)

## Değişmezler (bozma)
1. Sınıflandırıcı, log ve TTS ham metni görmez, yalnızca `pii.redact` çıktısını görür.
2. Yanıtlar `dialogue.FAQ` / `HANDOFF_REPLIES` şablon varyantlarıdır; kullanıcı girdisini yansıtmaz. Tek dinamik veri, PIN doğrulamasından sonra `mockbank`'tan gelen demo bakiyedir.
3. Emin olunmayan durum insana devredilir. Güvenlik niyetleri (`kart_kayip`, `sikayet`) asla otomatik yanıtlanmaz.
4. API yanıtlarında ham transkript dönmez.
5. Ses ucu `ALLOW_CLOUD_AUDIO=true` olmadan çalışmaz. Bu varsayılanı değiştirme.
6. Tuşlanan PIN yanıtta, logda ve TTS metninde yer almaz; PIN beklenirken sözlü girdi loga yazılmaz. `MOCK_BANKING` varsayılanı `false`.

## Kurallar
- Türkçe metin eşleştirmede `intents.tr_fold` kullan (İ/ı ve aksan farkları için); `str.lower()` tek başına yetmez.
- Gerçek kişi verisi, anahtar ya da çağrı kaydı repoya koyma. Test verileri sentetik ve algoritmik olarak geçerli üretilmiştir.
- Yeni niyet eklerken `tests/test_intents.py` ve `eval/utterances_tr.csv` dosyalarına örnek ekle.
- FAQ metinleri demo içeriğidir; müşteri onaylı metin gelmeden "kesin bilgi" gibi sunma.

## Sıradaki işler
- Tur süresi 4,8–5,4 sn: akışlı STT/TTS ve `eleven_flash_v2_5` dene, p95 ölç
- Olumsuzlama ve ipuçlu ad-soyad maskeleme yapıldı; gölge modda `negated:*` satırlarını gerçek veriyle doğrula
- İpucusuz ad ve adres maskeleme (ör. yerel NER modeli, veri ortamdan çıkmadan)
- Telefon (SIP) entegrasyonu
