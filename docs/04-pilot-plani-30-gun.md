# 4. Pilot planı (30 gün)

Başarı ölçütleri **öneridir**; sayısal eşikler müşteriyle ve pilot başında ölçülen taban değerle birlikte belirlenir.

| Hafta | Amaç | Çıktı |
| --- | --- | --- |
| 1 | Keşif ve veri kararı | Ses buluta gidebilir mi sorusunun yazılı cevabı, onaylı yanıt metinleri, örnek çağrı seti |
| 2 | Gölge mod | Asistan çağrıyı dinler ama yanıt vermez; niyet tahminleri insan kararıyla karşılaştırılır |
| 3 | Sınırlı canlı | Yalnızca kapsam içi iki niyet, düşük hacimli bir kuyrukta; her çağrıda devir seçeneği |
| 4 | Değerlendirme | Ölçüm raporu ve go/no-go kararı |

## Ölçülecekler

- Kapsam içi çağrılarda asistanın tek başına çözme oranı
- Güvenlik niyetlerinde (kart kaybı, şikayet) devir kaçırma sayısı. Hedef: sıfır
- Loglarda ve yanıtlarda kişisel veri sızıntısı. Hedef: sıfır
- STT kelime hata oranı (gerçek çağrı örneğinde)
- Tur başına p95 gecikme (STT + işleme + TTS)
- Devir sonrası temsilcinin yeniden sorması gereken bilgi sayısı

## Durdurma koşulları

Sızıntı tespiti, güvenlik niyetinde devir kaçırma ya da müşterinin hukuk biriminin itirazı pilotu hemen durdurur.
