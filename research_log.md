# Research Log

## Tez İçin Biriken Ana Bulgular

- [ ] Lab-to-field gap
- [ ] Frozen DINOv2 vs EfficientNet
- [ ] RAW vs LEAF
- [ ] GAP vs Single-Query Attention
- [ ] Single-Query vs Multi-Agent
- [ ] Vanilla Agent vs Kernel-Guided Agent
- [ ] Foreground/background attention analizi

---

## Günlük Kayıtlar

Bu dosya projenin tek ilerleme günlüğüdür. Yeni fazların ilerleme kayıtları buraya eklenir; ayrı `.md` faz raporları oluşturulmaz.

## 2026-10-06

### Bugün ne yaptık?

`MASTER_RESEARCH_PROTOCOL.md` ve mevcut Phase 0 manifest/özet çıktıları incelendi. Daha önce tamamlanan veri denetiminin sonuçları bu ilk günlük kaydında bir araya getirildi; bugün yeniden denetim veya model çalıştırması yapılmadı. Projenin tek ilerleme günlüğü olarak `research_log.md` oluşturuldu. Kaldırılması istenen iki eski checkpoint raporu işlem başında zaten mevcut değildi.

### Ne öğrendik?

- PlantVillage: 10 sınıf, 16.011 görüntü.
- PlantDoc: 9 sınıf, 746 görüntü.
- Toplam 16.757 görüntü manifestlendi.
- Görüntü geçerlilik kontrollerinde teknik hata bulunmadı: dosya açma, pozitif boyut, bütünlük ve RGB dönüşümü kontrollerinde 0 geçersiz görüntü raporlandı.
- SHA-256 ile exact duplicate kontrolü yapıldı. PlantVillage içinde 14, PlantDoc içinde 3 duplicate group bulundu; toplam 17 grup, 34 görüntü içeriyor.
- Veri setleri arasında exact duplicate bulunmadı. Bu sonuç near-duplicate bulunmadığı anlamına gelmez; near-duplicate taraması yapılmadı.
- PlantDoc içinde bir duplicate grubunda `bacterial spot` ve `Septoria` arasında label conflict bulundu. Aynı içerik farklı hastalık etiketleri altında yer alıyor.
- Dokuz klasör adı iki veri setinde ortak. Target Spot yalnızca PlantVillage'da bulunuyor (1.404 görüntü). PlantDoc spider mites sınıfı yalnızca 2 görüntü içeriyor.
- Canonical class intersection henüz dondurulmadı; mevcut mapping önerileri kullanıcı onayı bekliyor.
- Henüz train/val/test split oluşturulmadı.
- Henüz hiçbir model eğitilmedi.

### Tez için olası bulgular

Şu anki sonuçlar veri denetimi bulgularıdır; lab-to-field gap, temsil üstünlüğü veya attention kazancı hakkında deneysel sonuç yoktur. Bu nedenle ana bulgu listesinde hiçbir kutu işaretlenmedi.

PlantDoc'taki düşük sınıf örnek sayıları ve çelişkili etiketli exact duplicate, ileride sınıf bazlı metriklerin yorumunu etkileyebilir. Veri setleri arasında exact duplicate bulunmaması, incelenen dosyalarda tam kopya kaynaklı alanlar arası sızıntı saptanmadığını gösterir; tüm olası sızıntıları dışlamaz. PlantDoc dış hedef test kümesi olarak korunmalı ve model/preprocessing seçiminde kullanılmamalıdır.

### Teknik notlar

- Bilgi kaynakları: `manifests/audit_summary.json`, `manifests/phase_0_finalization_summary.json`, `manifests/class_counts_summary.csv`, `manifests/candidate_label_mapping.csv` ve `manifests/duplicate_group_summary.csv`.
- Manifestlerde `image_id`, `dataset`, `relative_path`, `original_label`, `sha256`, `canonical_label`, `split` ve `duplicate_group_id` alanları bulunur. `original_label` mevcut processed klasör adıdır. `canonical_label` ve `split` henüz boştur.
- Duplicate grup kimliği `dup_sha256_<tam içerik SHA-256>` olarak deterministik üretilir; tekil görüntülerde alan boştur. Kopyalar otomatik dışlanmadı.
- Etiket çelişkisi grubu: `dup_sha256_e23a29c94b58aac28e92f57f95eb6f53e99c874323cb2b90ebd327085721574e`. PlantDoc bacterial spot klasöründeki `test_tomato_V8.jpg` ile Septoria klasöründeki `train_tomato_V8.jpg` aynı içeriğe sahiptir. Dosya adlarındaki train/test önekleri yeni bir split ataması değildir.
- Muhafazakâr kesişim önerisi 6 sınıftır: Bacterial spot, Early blight, Late blight, Leaf Mold, Septoria leaf spot ve Two-spotted spider mite. Healthy ve Yellow Leaf Curl Virus için semantik kaynak doğrulaması; mosaic virus için protokol aday listesini genişletme onayı bekleniyor. Bunlar öneridir, onaylanmış sınıf kümesi değildir.
- Veri dosyaları, manifest CSV'leri ve Phase 0 denetim scriptleri korundu. Model kodu, split veya training üretilmedi/başlatılmadı.
- Mevcut audit scriptleri eski checkpoint `.md` raporlarını yeniden üretebilir; bu kayıt sırasında çalıştırılmadı. İleride kullanılacak raporlama akışı bu tek günlük kuralına uyarlanmalıdır.

### Sıradaki adım

Healthy ve yellow virus kaynak etiketlerinin anlamını doğrulamak, mosaic virus kapsam kararını netleştirmek ve PlantDoc'taki bacterial spot/Septoria etiket çelişkisi için belgelenmiş bir karar hazırlamak. Ardından önerilen canonical class intersection kullanıcı onayına sunulmalı; onay gelmeden sınıf kümesi dondurulmamalıdır. Split oluşturma ve model eğitimi bu aşamada yapılmayacaktır. Sonraki ilerleme kayıtları yalnızca bu dosyaya eklenecektir.

### Ek ilerleme notu — canonical eşleşme kontrolü

2026-10-06: Protokolün sınıf kesişimi kuralları, iki görüntü manifestindeki gerçek sınıf sayımları ve yerel statistics.txt özgün etiketleri karşılaştırıldı. Mapping düzeyinde güvenilir ortak sınıflar `approved` olarak önerildi: Bacterial spot (2127/110), Early blight (1000/88), Late blight (1909/111), Leaf Mold (952/91), Septoria leaf spot (1771/151), Two-spotted spider mite (1676/2) ve Tomato mosaic virus (373/54); sayılar PlantVillage/PlantDoc sırasındadır. Mosaic virus özgün etiketlerde iki tarafta da açıkça vardır; protokolün başlangıç aday listesi nihai liste olmadığı için semantik olarak ortak sınıf önerisine eklendi. Bu öneri önceki 6 sınıflık muhafazakâr öneriyi 7 sınıfa genişletir.

Healthy (1591/63) ve Yellow Leaf Curl Virus (3208/76) `needs_review`: PlantDoc özgün etiketleri sırasıyla `Tomato leaf` ve `Tomato leaf yellow virus` olduğundan anlamları kesinleşmedi. Target Spot (1404/0) ortak değildir ve önerilen kesişimde yer almaz. `approved` burada sınıf eşleşmesinin değerlendirmesidir; kullanıcı onayıyla canonical kümenin dondurulduğu veya tüm görüntü etiketlerinin doğrulandığı anlamına gelmez. Bacterial spot/Septoria duplicate label conflict için ayrıca karar gerekir. Canonical küme dondurulmadı; manifestler ve veriler değiştirilmedi; split veya training yapılmadı. Yeni `.md` raporu oluşturulmadı. Sıradaki adım iki belirsiz eşleşmeyi doğrulamak ve 7 sınıflık öneriyi kullanıcı onayına sunmaktır.

### Ek günlük kayıt — primary sınıf kümesi ve source split

2026-10-06: Kullanıcının açık onayıyla primary canonical küme şu 6 sınıf olarak donduruldu: `Tomato___Bacterial_spot`, `Tomato___Early_blight`, `Tomato___Late_blight`, `Tomato___Leaf_Mold`, `Tomato___Septoria_leaf_spot`, `Tomato___Tomato_mosaic_virus`. Bu karar önceki kesişim önerilerinin yerini alır. Güncel sözleşme `manifests/primary_class_set.json` içindedir; eski Phase 0 özetleri tarihsel audit kayıtları olarak korunur.

Tam envanter PV 16.011 / PD 746; primary kapsam PV 8.132 / PD 605 görüntüdür. PV için seed 42 ile sınıf bazında 70/15/15 split üretildi: train 5.692, validation 1.221, test 1.219. Tam sayı kotaları sınıf başına largest remainder ile hesaplandı; eşit kalanlarda train/validation/test sırası kullanıldı. Duplicate grupları bölünmeden atandı. Bu aşamada tek split seed'i 42 kullanıldı; protokoldeki 0 ve 1 seed'leri için ek split üretilmedi.

PlantDoc bölünmedi; primary görüntüler `external_target_test` olarak işaretlendi. Bacterial spot/Septoria label-conflict duplicate grubunun iki görüntüsü yalnızca primary target evaluation'dan dışlandı, etiket düzeltilmedi ve dosya silinmedi. Final target evaluation 603 görüntüdür (bacterial spot 109, early blight 88, late blight 111, leaf mold 91, Septoria 150, mosaic virus 54).

Yeni `manifests/primary_split_manifest.csv` tam 16.757 satırı korur; kapsam dışı ve dışlanan görüntüler `primary_included=False` ve `exclusion_reason` ile belirtilir, split alanları boştur. İlk audit görüntü manifestleri değiştirilmedi. Sınıf bazlı sayımlar `manifests/primary_class_split_counts.csv`, doğrulama özeti `manifests/primary_split_summary.json` içindedir. Yeniden üretim scripti `scripts/create_primary_splits.py` yalnızca metadata yazar. PV duplicate_group_id ve SHA-256 düzeyinde split leakage olmadığı, PV/PD arasında exact duplicate olmadığı, iki conflict görüntüsünün evaluation'a alınmadığı ve yeniden çalıştırmanın aynı dosya içeriklerini ürettiği doğrulandı. Model eğitilmedi; yeni `.md` raporu oluşturulmadı.
