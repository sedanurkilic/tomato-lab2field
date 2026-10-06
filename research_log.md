# Research Log

## Tez İçin Biriken Ana Bulgular

- [x] Lab-to-field gap
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

### EfficientNet-B0 RAW baseline — deney başlangıcı, 2026-10-06

Kullanıcı talimatıyla ilk gerçek deney başlatıldı. Sabit config: 224 input, deterministic eval resize 256 + center crop, ImageNet normalization; train RandomResizedCrop(scale 0.8–1.0) ve horizontal flip 0.5. AdamW lr=0.0001, weight_decay=0.0001, batch=32, max_epochs=30, patience=5; scheduler yok. Seed 42/0/1 aynı splitleri kullanır. Altı sınıf, split ayrıklığı, duplicate leakage ve 603 target kontrolü geçti. Sandbox dışında MPS erişimi doğrulandı ve torchvision ImageNet ağırlıkları indirildi. Checkpoint yalnızca PV validation Macro-F1 ile seçilecek; PlantDoc final değerlendirme dışında kullanılmayacak. Henüz sonuç yoktur; tez bulgusu ileri sürülmedi.

### EfficientNet-B0 RAW baseline — 2026-10-06

Aynı dondurulmuş splitlerle seed 42, 0, 1 çalıştırıldı. Config: `configs/efficientnet_b0_raw.json`; checkpoint seçimi yalnızca PV validation Macro-F1 ile yapıldı.

- Seed 42: source Macro-F1 0.9962, target Macro-F1 0.1790, delta 0.8172.
- Seed 0: source Macro-F1 0.9956, target Macro-F1 0.2407, delta 0.7550.
- Seed 1: source Macro-F1 0.9957, target Macro-F1 0.2772, delta 0.7185.

Üç seed Macro-F1 ortalaması ± örnek std: PV test **0.99586 ± 0.00032**, PlantDoc **0.23231 ± 0.04961**; delta **0.76355 ± 0.04990**. Bu RAW baseline, mevcut benchmarkta belirgin lab-to-field performans düşüşü gösterdi; nedenine ilişkin nedensellik iddiası yoktur. Tüm metriklerin mean/std değerleri `results/efficientnet_b0_raw/summary.json` ve `summary.csv` içindedir.

PlantDoc ortalama recall: Bacterial spot **%1.83**, Early blight **%55.30**, Late blight **%82.58**, Leaf Mold **%2.20**, Septoria **%36.89**, mosaic virus **%4.94**. En zayıf sınıf Bacterial spot, en güçlü sınıf Late blight. Confusion matrixler düşük recall sınıflarının çoğunlukla Early/Late blight olarak tahmin edildiğini gösteriyor. En iyi epochlar seed 42/0/1 için 11/19/12; eğitimler 16/24/17 epochta erken durdu.

Delta tanımlayıcı alan kaymasıdır, nedensellik iddiası değildir. Sıradaki adım bu baseline sonuçlarını incelemektir; başka deney başlatılmadı.

Üç checkpoint, validation seçim kriteri, her seed için 1219 source test ve 603 target tahmin satırı, tahminlerden yeniden hesaplanan metrikler ve split manifest hashinin değişmediği doğrulandı. Çalıştırma hatası veya gözlenen runtime uyarısı yok; MPS için determinism mümkün olduğu ölçüde, warn_only modunda uygulandı. Config, kod ve sürüm bilgileri sonuç metadata’sında kayıtlıdır.

### DINOv2 RAW baseline — 2026-10-06

#### Bugün ne yaptık?

Frozen DINOv2 ViT-B/14 backbone ile 6 sınıflık primary benchmark üzerinde RAW baseline çalışması tamamlandı. Backbone tamamen frozen kaldı; CLS ve GAP temsilleri üzerinde ayrı `Linear(768 -> 6)` probe'lar seeds 42, 0, 1 ile eğitildi. Bu kayıt kullanıcı tarafından sağlanan gerçek deney sonuçlarını belgelemek için eklendi; bu günlük güncellemesinde yeni eğitim çalıştırılmadı.

#### Ne öğrendik?

Üç seed için bildirilen mean ± std sonuçları:

| RAW baseline | PV test Macro-F1 | PlantDoc Macro-F1 | ΔMacro-F1 |
|---|---|---|---|
| EfficientNet-B0 | 0.99586 ± 0.00032 | 0.23231 ± 0.04961 | 0.76355 ± 0.04990 |
| DINOv2 CLS | 0.97885 ± 0.00187 | 0.29315 ± 0.02131 | 0.68570 ± 0.01944 |
| DINOv2 GAP | 0.97825 ± 0.00727 | 0.24874 ± 0.00378 | 0.72951 ± 0.01096 |

CLS, PlantDoc Macro-F1 ortalamasında EfficientNet'e göre yaklaşık **+6.1 yüzde puan** (6.084), GAP'e göre yaklaşık **+4.4 yüzde puan** (4.441) daha yüksek. DINOv2'nin iki probe'u da EfficientNet'ten daha düşük source-domain Macro-F1'e rağmen daha yüksek target-domain Macro-F1 gösterdi; GAP'in EfficientNet'e göre target farkı yaklaşık +1.6 yüzde puandır.

#### Tez için olası bulgular

Bu benchmarkta yüksek source-domain performansı daha yüksek target-domain performansıyla birlikte gitmedi. Frozen DINOv2 CLS, karşılaştırılan üç RAW baseline arasında en yüksek ortalama PlantDoc Macro-F1 ve en küçük ortalama lab-to-field gap gösterdi; ancak CLS'de bile ΔMacro-F1 0.68570 olduğundan ciddi transfer kaybı devam ediyor. Bu sonuçlar deneysel gözlemdir; nedensel açıklama veya istatistiksel anlamlılık iddiası değildir.

#### Teknik notlar

Checkpoint seçimi yalnız PlantVillage validation Macro-F1'e göre yapıldı. PlantDoc yalnız external target evaluation için kullanıldı. ΔMacro-F1, PV source test Macro-F1 eksi PlantDoc Macro-F1 olarak raporlandı. Backbone güncellenmedi; öğrenilen bileşen yalnızca linear probe'dur. Verilen aggregate sonuçlar kaydedildi; bu güncellemede seed bazlı dosyalar yeniden doğrulanmadı.

#### Sıradaki adım

Mevcut CLS/GAP tahminleri üzerinden sınıf bazlı recall ve hata örüntülerini inceleyerek farkın hangi sınıflarda oluştuğunu belgelemek; yöntem veya checkpoint seçimini PlantDoc sonuçlarına göre değiştirmemek. Bu kayıt sırasında başka deney başlatılmadı.
