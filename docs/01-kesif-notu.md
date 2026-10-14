# 1. Keşif notu

Bu not, müşteriyle yapılacak ilk görüşmenin gündemidir. Kod yazmadan önce bu sorulara cevap alınır; cevaplar mimariyi değiştirebilir.

**Senaryo (varsayım):** Orta ölçekli bir finans kuruluşu, çağrı merkezine gelen basit soruları Türkçe sesli asistanla karşılamak istiyor. Müşteri verisinin kurumun ortamından çıkmaması isteniyor. Bu senaryo dokümandaki "Demo Finans" ile örneklenmiştir, gerçek bir kuruma ait değildir.

## Önce cevaplanması gereken beş soru

1. **Ses buluta gidebilir mi?** "Veri çıkamaz" şartı yalnızca metin için mi, ses kaydı için de mi geçerli? Cevap hayırsa bulut STT/TTS pilotta kullanılamaz; yerel (on-prem) model ya da yalnızca metin kanalı gerekir. Bu projede ses ucu varsayılan olarak kapalıdır (`ALLOW_CLOUD_AUDIO=false`).
2. **Hangi çağrılar kapsam içinde?** Önerilen ilk kapsam: şube saatleri, genel kredi başvuru bilgisi. Kimlik doğrulama gerektiren her şey (bakiye, işlem) pilot dışıdır ve insana devredilir.
3. **Son kullanıcıya aydınlatma nasıl yapılacak?** Çağrının başında kaydın ve otomatik asistanın bildirimi için onaylı metin kimde?
4. **Telefon altyapısı ne?** SIP/IVR sağlayıcısı, ses codec'i (8 kHz telefon sesi STT doğruluğunu düşürür), asistanın çağrıyı nasıl devredeceği (transfer API'si).
5. **Başarı nasıl ölçülecek?** Gerçek çağrı kayıtlarından izinli ve maskelenmiş bir örnek set verilebilir mi?

## Kapsam dışı (pilotta bilerek yok)

- Kimlik doğrulama ve hesap bilgisi sorgusu
- Serbest sohbet / üretken model yanıtı (yanıtlar onaylı sabit metinlerdir)
- Gerçek telefon entegrasyonu (SIP). Prototip HTTP üzerinden ses/metin alır.

## Müşteriden alınacaklar

- Onaylı yanıt metinleri (koddaki `FAQ` demo içeriğidir)
- Devir kuralları: hangi durumda, hangi kuyruğa
- Örnek çağrı dökümü (maskelenmiş), en az birkaç yüz tur
