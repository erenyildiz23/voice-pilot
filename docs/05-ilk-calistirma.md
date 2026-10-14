# 5. ElevenLabs ile ilk çalıştırma

Gerçek servisle ilk çalıştırma 14 Ekim 2026'da yapıldı (sonuçlar en altta). Yeniden kurarken şunları kontrol et:

1. `.env.example` dosyasını `.env` olarak kopyala (sunucuyu `--env-file .env` ile başlat, aksi halde .env okunmaz), `PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` doldur. Test için `ALLOW_CLOUD_AUDIO=true` yap. Gerçek müşteri verisiyle deneme.
2. Model adlarını güncel dokümandan doğrula (`ELEVENLABS_STT_MODEL`, `ELEVENLABS_TTS_MODEL`). Varsayılanlar: `scribe_v2`, `eleven_multilingual_v2`.
3. Türkçe için `ELEVENLABS_STT_LANGUAGE` ayarının kabul ettiği kodu doğrula; boş bırakırsan dil otomatik algılanır.
4. Kendi sesinle 10 kısa kayıt gönder (`curl -F file=@kayit.wav localhost:8000/v1/turn/audio`), `transcript_redacted` alanında transkripti kontrol et.
5. Dönen `audio_b64` değerini çöz ve dinle (`base64 -d`).
6. Hata durumları: yanlış anahtarla 502 döndüğünü ve hata gövdesinin yanıta sızmadığını doğrula.

Bulduğun farkları `src/pilot/providers.py` içinde düzelt ve ilgili testi güncelle.

## İlk çalıştırma sonucu (14 Ekim 2026, ücretsiz plan)

| Kontrol | Sonuç |
| --- | --- |
| `.env` okunuyor mu | İlk denemede **hayır**: uygulama yalnızca ortam değişkeni okuyordu. `--env-file .env` + `python-dotenv` ile düzeltildi |
| Yanlış anahtar (Key ID anahtar yerine girildi) | ElevenLabs 400 `invalid_api_key`; API **502** döndü, hata gövdesi yanıta sızmadı ✓ |
| Kütüphane sesi (Şevval) | **402 `paid_plan_required`**: ücretsiz plan kütüphane seslerini API'den kullandırmıyor. Hazır (premade) ses "Sarah" ile devam edildi. Müşteri pilotunda ses seçimi plan/lisans kararıdır |
| Metin turu + TTS | 200, geçerli MP3 (~117 KB) ✓ |
| Ses turu: STT (`scribe_v2`) → maskeleme → niyet → TTS | 3/3 doğru: "kaybetmedim ama çalındı" → devir; "Adım Ayşe Demir…" → ad maskelendi, yanıt; sözlü kimlik no → maskelendi, devir ✓ |
| Ham veri sızıntısı (API yanıtı + denetim kaydı) | Yok ✓ |
| Tur süresi (STT + işleme + TTS, yerel makineden) | 4,8–5,4 sn. **Telefon için yavaş**; akışlı (streaming) STT/TTS ve daha hızlı model (`eleven_flash_v2_5`) pilotta denenmeli |
| `ELEVENLABS_STT_LANGUAGE` | Boş bırakıldı, dil otomatik algılandı ve Türkçe doğru çıktı |
