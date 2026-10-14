# 2. Mimari

```mermaid
flowchart LR
  A[Arayan] -->|ses| B[Telefon/IVR]
  B -->|HTTP ses ya da metin| C[API: /v1/turn, /v1/turn/audio]
  C -->|ALLOW_CLOUD_AUDIO=true ise| D[STT sağlayıcısı]
  D -->|transkript| E[PII maskeleme]
  C -->|metin kanalı| E
  E -->|maskelenmiş metin| F[Niyet sınıflandırıcı]
  F --> G{Politika}
  G -->|kapsam içi| H[Onaylı yanıt şablonu]
  G -->|hassas / emin değil| I[İnsana devir]
  H --> J[TTS sağlayıcısı]
  E --> K[(Denetim kaydı: yalnızca maskelenmiş metin)]
```

## Değişmezler

1. Sınıflandırıcı, log ve TTS ham metni görmez; maskelenmiş metni görür.
2. Yanıtlar sabit şablondur, kullanıcının sözünü yansıtmaz. TTS'e kişisel veri gidemez.
3. Emin olunamayan her durum insana devredilir. İki ardışık anlaşılmayan turda devir.
4. Ham transkript hiçbir API yanıtında dönmez.
5. Sağlayıcı hatası (STT/TTS) 502 döner; çağıran taraf çağrıyı insana yönlendirmelidir.

## Dağıtım modları

| Mod | Ses nereye gider | Durum |
| --- | --- | --- |
| Yalnızca metin | Hiçbir yere (IVR kendi STT'sini kullanır) | Bu repoda çalışır ve test edilmiştir |
| Bulut STT/TTS | ElevenLabs'a | Kod yazıldı, istek şekilleri testlerle doğrulandı, gerçek servisle denenmedi, müşteri onayı gerekir |
| Yerel STT/TTS | Kurum içinde | Yok. `SpeechProvider` arayüzünü uygulayan yeni bir sağlayıcı yazılır |

## Önemli sınırlama

Maskeleme, STT'den **sonra** çalışır. Bulut STT kullanılırsa ham ses, maskeleme devreye girmeden sağlayıcıya ulaşır. Bu yüzden "veri çıkamaz" şartı varsa bulut modu tek başına çözüm değildir (bkz. risk tablosu, madde 1).
