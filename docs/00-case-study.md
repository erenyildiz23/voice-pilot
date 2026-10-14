# Case study 1: Müşteri ortamında Türkçe sesli asistan pilotu

*Hedef rol: Forward Deployed Engineer. Tek sayfa özet; ayrıntılar 01–05 numaralı dokümanlarda.*

## Bağlam

Türkiye'de orta ölçekli bir finans kuruluşu ("Demo Finans", kurgusal) çağrı merkezine gelen basit soruları Türkçe sesli asistanla karşılamak istiyor. Şart: müşteri verisi kurumun ortamından çıkmayacak (KVKK).

## Problem

Asıl soru "asistan ne kadar akıllı" değil, **"neyi güvenle tek başına yapar, neyi insana bırakır"**. Bulut STT/TTS kullanmak teknik olarak en kolay yol ama "veri çıkamaz" şartıyla doğrudan çelişiyor: ses, maskeleme devreye girmeden sağlayıcıya ulaşıyor. Bu yüzden ilk iş kod değil, keşif sorularıydı (bkz. [01-kesif-notu.md](01-kesif-notu.md)).

## Alınan kararlar ve gerekçeleri

| Karar | Gerekçe |
| --- | --- |
| Ses ucu varsayılan **kapalı** (`ALLOW_CLOUD_AUDIO=false`) | Ses buluta gidebilir mi sorusu müşterinin ve hukukun kararı. Kod bunu yanlışlıkla açık bırakamaz. Metin kanalı (IVR'ın kendi STT'si) onaysız da çalışır |
| Üretken model yok, yalnızca onaylı şablon yanıt | Yanıt kullanıcının sözünü yansıtmadığı için TTS'e ve loga kişisel veri gidemez. Yanlış bilgi riski sıfıra iner |
| Maskeleme her şeyden önce | Sınıflandırıcı, denetim kaydı ve API yanıtı yalnızca maskelenmiş metni görür. TCKN/IBAN/kart için sağlama algoritmaları (yanlış pozitifi azaltır), sözlü rakam dizileri, ipuçlu ad-soyad |
| Güvenlik niyetleri ilk turda devir | Kart kaybı, izinsiz işlem, şikayet, bakiye ve kişisel veri paylaşımı otomatik yanıtlanmaz. Kapsam dışı bankacılık talepleri de "anlamadım" döngüsüne girmeden devredilir |
| Olumsuzlama tasarımı güvenli yöne eğik | "Kartımı kaybetmedim" devredilmez, ama "kaybetmedim ama çalındı" devredilir: tek olumlu eşleşme yeter. Atlanan niyet denetim kaydına `negated:*` olarak yazılır, gölge modda insan kontrol eder |
| Kural tabanlı sınıflandırıcı | Pilotun ilk haftasında amaç, gerçek çağrı verisinde hangi niyetlerin otomatikleşebileceğini ölçmek. `classify()` arayüzü sabit; veri gelince model ile değiştirilir |
| `SpeechProvider` arayüzü | ElevenLabs bulut, mock çevrimdışı. Müşteri "ses çıkamaz" derse yerel STT/TTS aynı arayüzle eklenir, kodun geri kalanı değişmez |

## Ölçülen sonuç

- **64 otomatik test** geçti: maskeleme, niyet, olumsuzlama, diyalog politikası, API, denetim kaydında ham veri olmaması.
- **Smoke eval: 50/50, devir kaçırma 0, sızıntı 0.** Bu bir performans iddiası *değil*: kuralları ve cümleleri aynı kişi yazdı.
- Daha dürüst sayı: kurallar yazıldıktan sonra denediğim **11 yeni cümlede 4 güvenlik kaçağı** çıktı (örn. "birisi kartımla alışveriş yapmış" ilk turda devredilmiyordu). Düzelttim ve sete ekledim. Ders: kural tabanlı sistemin kör noktaları ancak gerçek çağrı verisiyle bulunur; 30 günlük plandaki gölge mod haftası tam bunun için var.
- **Sentetik ses ölçümü:** ElevenLabs TTS ile seslendirilen 8 riskli cümle Scribe STT'den geçti: WER %0, 8/8 doğru karar. Olumsuz ek ("kaybet-me-dim") korundu; sözlü kimlik numarası rakama çevrilmeden geldi ve sözlü dizi maskesiyle yakalandı ([ayrıntı](../eval/stt_ses_olcumu.md)). Temiz stüdyo sesi olduğu için en iyimser durum.
- **Gerçek servisle uçtan uca:** Prototip ElevenLabs'e bağlıyken ses→STT→maskeleme→niyet→TTS turları çalıştı; tur süresi 4,8–5,4 sn. Bu telefon için yavaş, bir sonraki iş akışlı STT/TTS. İlk kurulumda iki gerçek sorun çıktı: uygulama `.env` dosyasını okumuyordu ve ücretsiz plan kütüphane sesini API'de reddetti (402). İkisi de belgelendi.
- **Ölçemediklerim:** Telefon sesinde (8 kHz) doğruluk. İzinli gerçek çağrı kaydı gerekiyor.

## Farklı yapsaydım

- Müşteriyle ilk görüşmede **"ses buluta gidebilir mi"** sorusunun cevabını almadan mimari çizmezdim. Cevap "hayır" ise bulut entegrasyonuna harcanan süre boşa gider; yerel Whisper benzeri bir STT ile başlardım.
- Eval setini kendim yazmak yerine, en baştan müşteriden **maskelenmiş birkaç yüz gerçek tur** isterdim. Kendi yazdığım cümlelerde %100, ilk yabancı cümlelerde %36 kaçak (4/11) farkı bunu gösteriyor.
- Olumsuzlama ve ad maskelemeyi regex yerine kurum içinde çalışan küçük bir Türkçe NER/sınıflandırıcı modeliyle yapardım; ama bunu ancak gölge mod verisiyle karşılaştırıp kararlaştırırdım.

## Nasıl denenir

```bash
pip install -r requirements.txt
python -m pytest -q && python eval/run_eval.py
PYTHONPATH=src uvicorn pilot.app:app --port 8000   # http://localhost:8000
```
