# Müşteri ortamında Türkçe sesli asistan pilotu

Case study 1'in çalışan prototipi: çağrı merkezi için Türkçe sesli asistan. Odak **ne kadar akıllı olduğu** değil, **neyi güvenle yapıp neyi insana bıraktığı**.

- Kişisel veri (TCKN, IBAN, kart, telefon, e-posta, sözlü rakam dizisi, ipuçlu ad-soyad) sınıflandırmadan, logdan ve TTS'ten önce maskelenir.
- Güvenlik ve kimlik doğrulama gerektiren niyetler (kart kaybı/izinsiz işlem, şikayet, bakiye) hemen insana devredilir. Kapsam dışı bankacılık talepleri (limit, şifre, havale) "anlamadım" döngüsüne girmeden devredilir.
- Olumsuzlama anlaşılır: "kartımı kaybetmedim" devredilmez ama denetim kaydına `negated:kart_kayip` olarak düşer; "kaybetmedim ama çalındı" yine devredilir.
- İki ardışık anlaşılmayan turda devir. Yanıtlar onaylı sabit şablonlardır, üretken model yok.
- Yanıtlar her niyet için birkaç onaylı varyant arasından seçilir (aynı bilgi, farklı söyleyiş). Karşılama ve "anlamadım" yanıtları tuşlama menüsü sunar: 1 şube saatleri, 2 kredi, 3 bakiye (demo modda), 0 temsilci, 9 kapanış.
- **Demo bankacılık modu** (`MOCK_BANKING=true`, varsayılan kapalı): bakiye talebinde önce 4 haneli PIN tuşlatılır (demo PIN `1234`), sonra sahte hesap servisinden (`mockbank.py`) **uydurma** bir bakiye okunur. PIN hiçbir yanıtta ve logda yer almaz; sesli söylenen PIN reddedilir ve loga yazılmaz; iki hatalı denemede devir. Kart kaybı ve şikayet bu modda da asla otomatik yanıtlanmaz.
- Ses ucu varsayılan **kapalı**: ses buluttaki STT'ye gideceği için müşteri onayı gerektirir.

## Hızlı başlangıç (çevrimdışı, mock sağlayıcı)

```bash
pip install -r requirements.txt
python -m pytest -q
python eval/run_eval.py
PYTHONPATH=src uvicorn pilot.app:app --port 8000 --env-file .env   # .env yoksa bayrağı çıkar; tarayıcıda http://localhost:8000 demo sayfası
curl -s localhost:8000/v1/turn -H 'content-type: application/json' \
  -d '{"text":"Şubeniz saat kaçta açılıyor","with_audio":true}'
```

## Ne test edildi, ne edilmedi

| Konu | Durum |
| --- | --- |
| Maskeleme, niyet, olumsuzlama, diyalog, tuşlama menüsü, PIN akışı, API, demo sayfası, denetim kaydı | 75 birim/uç nokta testi geçti |
| ElevenLabs ile uçtan uca | Gerçek servisle çalıştırıldı: metin+TTS ve ses→STT→maskeleme→TTS turları başarılı, yanlış anahtarda 502 ve sızıntı yok. Tur süresi 4,8–5,4 sn ([ayrıntı](docs/05-ilk-calistirma.md#ilk-çalıştırma-sonucu-14-ekim-2026-ücretsiz-plan)) |
| Türkçe STT/TTS kalitesi | Sentetik temiz seste ölçüldü: 8 cümlede WER %0, 8/8 doğru karar ([eval/stt_ses_olcumu.md](eval/stt_ses_olcumu.md)). **Telefon sesinde ölçülmedi**; bu sayı en iyimser durumdur |
| Smoke eval | 50 cümlede 50 doğru. **Bu bir performans iddiası değil**: kuralları ve cümleleri aynı kişi yazdı. Gerçek çağrı verisi gelince yeniden ölçülmeli |
| Set dışı deneme | Kurallar yazıldıktan sonra denenen 11 yeni cümlede 4 güvenlik kaçağı çıktı ("birisi kartımla alışveriş yapmış", "kartımı unuttum", "memnun değilim", "kimse ilgilenmedi"). Düzeltildi ve sete eklendi; bu, kural tabanlı yaklaşımın kör noktalarının gerçek veriyle bulunacağını gösteriyor |

## Bilinen sınırlamalar

- Olumsuzlama ek ve yardımcı fiil kalıplarıyla yakalanır; STT olumsuz eki ("-me-") düşürürse cümle olumlu sayılır ve devredilir (güvenli yön). Ters yön riski: STT olumlu cümleye yanlışlıkla "-me-" eklerse devir kaçar. Gerçek ses verisiyle ölçülmeli (risk 4).
- Ad-soyad yalnızca ipucuyla ("adım", "ismim", "Ahmet Bey") yakalanır. "Ben Ahmet" ve adres maskelenmez.
- "limit" gibi geniş anahtar sözcükler "limitsiz internet paketi" gibi alakasız cümleleri de devreder (güvenli yön).
- Oturumlar bellek içidir.

## Dokümanlar

0. [Tek sayfa case study](docs/00-case-study.md)
1. [Keşif notu](docs/01-kesif-notu.md)
2. [Mimari](docs/02-mimari.md)
3. [Risk tablosu](docs/03-risk-tablosu.md)
4. [30 günlük pilot planı](docs/04-pilot-plani-30-gun.md)
5. [ElevenLabs ile ilk çalıştırma](docs/05-ilk-calistirma.md)
