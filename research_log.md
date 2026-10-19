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

### DINOv2 PCA diagnostik analizi — 2026-10-14

#### Bugün ne yaptık?

Cached frozen DINOv2 CLS ve GAP feature'ları (her görüntü için 768 boyut) üzerinde sade bir PCA diagnostik analizi yapıldı. CLS ve GAP için ayrı `PCA(n_components=2)` kullanıldı. PCA yalnızca PlantVillage train (n=5692) üzerinde fit edildi; PlantVillage validation fit'e dahil edilmedi. PlantVillage test (n=1219) ve PlantDoc external target test (n=603) aynı source-fitted PCA uzayına yalnızca transform edildi. Her representation için renk = sınıf, işaret = domain (PV test `o`, PlantDoc `x`) olan birer scatter figürü üretildi (`docs/figures/dinov2_pca/`, script: `scripts/analyze_dinov2_pca.py`). Yeni model eğitilmedi.

#### Ne öğrendik?

Source-fitted PCA'da açıklanan varyans:

| Representation | PC1 | PC2 | PC1+PC2 |
|---|---|---|---|
| CLS | 13.0% | 8.1% | 21.1% |
| GAP | 16.2% | 7.1% | 23.3% |

Nitel (görsel) gözlemler:
- GAP PCA'da PlantVillage ve PlantDoc örnekleri, özellikle PC1 boyunca, CLS'ye göre daha belirgin bir domain ayrımı gösteriyor.
- CLS PCA'da source ve target örnekleri daha fazla örtüşüyor.
- Sınıflar ilk iki PCA boyutunda temiz biçimde ayrışmıyor.

Bu nitel gözlem, mevcut field sonuçlarıyla uyumlu: PlantDoc Macro-F1 CLS 0.29315 ± 0.02131, GAP 0.24874 ± 0.00378. Bu bir uyum gözlemidir; nedensel açıklama veya istatistiksel test değildir.

#### Tez için olası bulgular

PCA bulgusu, Single-Query Attention deneyini motive eden diagnostik bir gözlemdir; tek başına bir sonuç değildir. Sınıfların ilk iki bileşende ayrışmaması, DINOv2'nin sınıfları ayıramadığı anlamına gelmez: iki bileşen CLS için yalnızca %21.1, GAP için %23.3 toplam varyansı gösteriyor ve linear probe 768 boyutun tamamını kullanıyor (PV test Macro-F1 ≈ 0.98). Bu analizden "background shortcut kanıtlandı" ya da "CLS domain invariant" gibi sonuçlar çıkarılmamalıdır.

#### Teknik notlar

- Fit seti: `dataset == "plantvillage"` ve `split == "train"`; transform edilen setler: `split == "test"` ve `split == "external_target_test"`. Validation hiçbir aşamada kullanılmadı.
- Çalıştırma öncesi shape (8735×768) ve split sayıları (5692/1221/1219/603, 6 sınıf) assert ile doğrulandı.
- Renk paleti matplotlib `tab10`; sınıf renkleri iki figürde aynı. Renk körlüğü doğrulaması yapılmadı.
- Gözlemler iki 2B projeksiyonun görsel incelemesine dayanır; domain ayrımı için nicel bir ölçü hesaplanmadı.
- Feature dosyaları (`artifacts/`) gitignore'da ve değiştirilmedi.

#### Sıradaki adım

PCA diagnostik gözlemini motivasyon olarak kullanarak Single-Query Attention deneyini tasarlamak. Yöntem veya checkpoint seçimi PlantDoc sonuçlarına göre değiştirilmeyecek; PlantDoc yalnızca final external target değerlendirmesinde kullanılacak.

### Single-Query Attention baseline — 2026-10-14

#### Bugün ne yaptık?

Cached frozen DINOv2 patch tokenları üzerinde Single-Query Attention baseline'ı seeds 42, 0, 1 ile çalıştırıldı. Amaç, GAP'teki eşit ağırlıklı patch ortalaması yerine tek learnable query ile öğrenilmiş, düzgün olmayan (non-uniform) spatial ağırlıklandırmanın etkisini izole etmekti. Bu deney, PCA diagnostik gözleminden motive edilmiştir.

Protokol:
- Frozen DINOv2 patch tokenları kullanıldı; patch tensor shape `[8735, 256, 768]`. DINOv2 backbone yeniden eğitilmedi.
- Tek trainable query `[768]`, sıfır initialize edildi. Başlangıç aggregation'ı tam uniform 1/256, yani GAP-equivalent pooling.
- Final classifier `Linear(768 -> 6)`. Toplam trainable parametre: 5382.
- AdamW, learning rate 1e-3, weight decay 1e-4; batch size 64, max epoch 50, early stopping patience 5.
- Model seçimi yalnız PlantVillage validation Macro-F1 ile yapıldı. PlantDoc yalnız final external target evaluation'da kullanıldı.
- Patch cache `mmap=True` ile batch bazında okundu.

#### Ne öğrendik?

Seed bazlı sonuçlar:

| Seed | Best epoch | PV Macro-F1 | PlantDoc Macro-F1 | ΔMacro-F1 |
|---|---|---|---|---|
| 42 | 24 | 0.98805 | 0.31100 | 0.67705 |
| 0 | 24 | 0.98814 | 0.29533 | 0.69281 |
| 1 | 19 | 0.99133 | 0.29070 | 0.70063 |

3-seed mean ± örnek std:

| Metrik | PV test | PlantDoc |
|---|---|---|
| Macro-F1 | 0.98917 ± 0.00187 | 0.29901 ± 0.01064 |
| Balanced accuracy | 0.98698 ± 0.00205 | 0.35961 ± 0.00839 |
| Accuracy | 0.99152 ± 0.00095 | 0.41183 ± 0.00957 |

ΔMacro-F1: 0.69016 ± 0.01201.

PlantDoc Macro-F1 baseline karşılaştırması:

| Model | PlantDoc Macro-F1 |
|---|---|
| DINOv2 GAP | 0.24874 ± 0.00378 |
| DINOv2 CLS | 0.29315 ± 0.02131 |
| Single-Query Attention | 0.29901 ± 0.01064 |

PlantDoc Single-Query mean per-class recall: Bacterial spot 0.0612, Early blight 0.4242, Late blight 0.9640, Leaf Mold 0.1209, Septoria leaf spot 0.5689, Tomato mosaic virus 0.0185.

#### Tez için olası bulgular

- Single-Query, GAP'e göre yaklaşık +5.03 yüzde puan daha yüksek PlantDoc Macro-F1 verdi. Başlangıçta GAP-equivalent olan modelde tek query'nin öğrenilmesiyle bu fark oluştu.
- CLS'ye göre üç-seed ortalama fark yalnızca yaklaşık +0.59 yüzde puan. Bu nedenle Single-Query CLS'den üstün değildir; CLS ile karşılaştırılabilir field performansı verdi ve GAP'i belirgin biçimde geçti.
- Seed bazında (aynı seed numaralı CLS değerleriyle) Single-Query seed 42 ve 0'da çok az daha düşük (0.31100 vs 0.31209; 0.29533 vs 0.29729), seed 1'de daha yüksek (0.29070 vs 0.27008). CLS'ye karşı tutarlı bir seed davranışı yok.
- Single-Query'nin PV Macro-F1'i CLS'den yüksek (0.98917 vs 0.97885), ancak field kazancı aynı ölçüde artmadı. Source iyileşmesi ile field robustness birebir aynı şey değildir.
- ΔMacro-F1 0.69016 ile büyük lab-to-field kaybı sürüyor.
- PlantDoc başarısı sınıflar arasında çok dengesiz: Late blight güçlü (0.9640), Bacterial spot (0.0612) ve Tomato mosaic virus (0.0185) çok zayıf.

Bu bulgular deneysel gözlemlerdir; istatistiksel anlamlılık veya nedensel açıklama iddiası yoktur.

#### Teknik notlar

- Preflight (tek batch): query forward öncesi tam sıfır, ilk forward'da attention min/max 1/256, attention toplamları 1, query gradient normu > 0, trainable parametre sayısı 5382, tüm patch tensörün RAM/GPU kopyası oluşmadı.
- Her seed için attention weight dosyaları başarıyla kaydedildi: PV test `[1219, 256]`, PlantDoc `[603, 256]` (image_id ve metadata satır indeksleriyle). İleride spatial-focus analizinde kullanılacak; bu aşamada modelin neye baktığına dair yorum yapılmadı.
- Çalışma MPS üzerinde yaklaşık 870 s sürdü (3 seed). Çalıştırma hatası yok.
- Karşılaştırılan CLS/GAP değerleri `docs/experiment_results/dinov2_raw/seed_results.csv` ile uyumludur.
- Checkpoint, prediction ve attention dosyaları `results/single_query_attention/` altında kalır (gitignore'da); yalnızca `seed_results.csv` ve `summary.json` `docs/experiment_results/single_query_attention/` altına değiştirilmeden arşivlendi.
- Script: `scripts/run_single_query_attention.py` (değiştirilmedi).

#### Sıradaki adım

Single-Query bulgusunu temel alarak Multi-Agent Attention deney tasarımının belirlenmesi.


### Multi-Agent Attention baseline ve agent-collapse diagnostiği — 2026-10-14

#### Bugün ne yaptık?

Single-Query Attention baseline'ı yalnızca query sayısı artırılarak genişletildi: cached frozen DINOv2 patch tokenları üzerinde 4 learnable query ile Multi-Agent Attention (N=4) seeds 42, 0, 1 ile çalıştırıldı. Ardından üç seed'in PlantVillage test attention weights'i üzerinde post-hoc agent-collapse diagnostiği yapıldı. Diagnostik yalnız PlantVillage test üzerinde yapıldı; PlantDoc attention kullanılmadı. Bu kayıt sırasında yeni deney çalıştırılmadı.

Deney protokolü:
- Frozen DINOv2 patch tokenları `[8735, 256, 768]`; backbone eğitilmedi.
- 4 learnable query `[4, 768]`, init Normal(0, 0.02).
- Attention scores `[B, 4, 256]`, softmax yalnız patch boyutunda.
- Her agent için pooled representation `[B, 4, 768]`.
- Agent çıktıları concatenate edilmedi; `mean(dim=1)` ile `[B, 768]` representation üretildi.
- Classifier `Linear(768 -> 6)`; toplam trainable parametre 7686.
- Seeds [42, 0, 1]; AdamW, lr 1e-3, weight decay 1e-4; batch size 64; max epoch 50; patience 5.
- Model seçimi yalnız PlantVillage validation Macro-F1 ile yapıldı. PlantDoc yalnız final external evaluation'da kullanıldı.
- Patch cache `mmap=True` ile okundu.

#### Ne öğrendik?

Seed bazlı sonuçlar:

| Seed | Best epoch | PV Macro-F1 | PlantDoc Macro-F1 | ΔMacro-F1 |
|---|---|---|---|---|
| 42 | 19 | 0.99007 | 0.33623 | 0.65384 |
| 0 | 21 | 0.99007 | 0.30200 | 0.68807 |
| 1 | 35 | 0.99180 | 0.29821 | 0.69359 |

3-seed mean ± örnek std:

| Metrik | PV test | PlantDoc |
|---|---|---|
| Macro-F1 | 0.99065 ± 0.00100 | 0.31215 ± 0.02095 |
| Balanced accuracy | 0.98854 ± 0.00128 | 0.36409 ± 0.01959 |
| Accuracy | 0.99316 ± 0.00095 | 0.40962 ± 0.02231 |

ΔMacro-F1: 0.67850 ± 0.02154.

PlantDoc Macro-F1 baseline karşılaştırması:

| Model | PlantDoc Macro-F1 |
|---|---|
| DINOv2 GAP | 0.24874 ± 0.00378 |
| DINOv2 CLS | 0.29315 ± 0.02131 |
| Single-Query Attention | 0.29901 ± 0.01064 |
| Multi-Agent Attention (N=4) | 0.31215 ± 0.02095 |

PlantDoc mean per-class recall: Bacterial spot 0.1223, Early blight 0.4621, Late blight 0.9550, Leaf Mold 0.1355, Septoria leaf spot 0.4911, Tomato mosaic virus 0.0185.

Agent-collapse diagnostiği (PlantVillage test, attention shape her seed için `[1219, 4, 256]`; 1219 görüntü × 6 agent çifti; üç seed birleşik):
- Pairwise Total Variation: 0.35612 ± 0.22081.
- Pairwise centered cosine (uniform 1/256 çıkarıldıktan sonra): 0.61815 ± 0.37656.
- Normalized attention entropy: 0.85749 ± 0.08302.
- Agent (0,3) çifti üç seed'de de neredeyse aynı attention pattern'ını öğrendi: TV yaklaşık 0.013–0.016, centered cosine yaklaşık 0.999.
- Diğer bazı agent çiftleri belirgin biçimde farklı spatial weighting pattern'leri öğrendi (ör. (0,2) ve (2,3) çiftlerinde TV yaklaşık 0.48–0.70).
- Sanity check'ler: attention toplamları patch boyutunda yaklaşık 1, NaN/Inf yok, hiçbir agent çifti test setinde birebir (`torch.equal`) aynı değil.

#### Tez için olası bulgular

- Multi-Agent, şimdiye kadar karşılaştırılan modeller arasında en yüksek ortalama PlantDoc Macro-F1'i verdi: GAP'e göre yaklaşık +6.34, CLS'ye göre yaklaşık +1.90, Single-Query'ye göre yaklaşık +1.31 yüzde puan.
- Aynı seed'lerde Multi-Agent, Single-Query'den daha yüksek PlantDoc Macro-F1 verdi: seed 42 +0.02523, seed 0 +0.00667, seed 1 +0.00751.
- Yalnız üç seed olduğu ve std değerleri görece yüksek olduğu için (CLS ve Single-Query farkları std aralığında) istatistiksel üstünlük iddiası yoktur.
- Single-Query ile Multi-Agent arasında query sayısının yanında initialization da değişti (sıfır init vs Normal(0, 0.02)); Single-Query başlangıçta tam uniform (GAP-equivalent), Multi-Agent hafifçe non-uniform başladı. Bu nedenle performans farkı yalnızca "dört query etkisi" olarak yorumlanamaz.
- ΔMacro-F1 0.67850 ile büyük lab-to-field kaybı sürüyor.
- PlantDoc başarısı sınıflar arasında hâlâ ciddi biçimde dengesiz: Late blight güçlü (0.9550), Tomato mosaic virus (0.0185), Bacterial spot (0.1223) ve Leaf Mold (0.1355) çok zayıf.
- Diagnostik, (0,3) çiftinde partial agent redundancy / partial collapse gösteriyor; dört agent'ın tamamı collapse etmedi. Diğer çiftler farklı spatial weighting pattern'leri öğrendi. Kesin bir bağımsız pattern sayısı iddia edilmez.
- Normalized entropy genel olarak yüksek kaldığından attention hâlâ görece diffuse. Bu diagnostik agent'ların lesion bölgelerini bulduğunu göstermez; spatial içerik (foreground/background) analizi yapılmadı.

Bu bulgular deneysel gözlemlerdir; istatistiksel anlamlılık veya nedensel açıklama iddiası yoktur.

#### Teknik notlar

- Script: `scripts/run_multi_agent_attention.py` (preflight ve eğitim sırasında değiştirilmedi). Tek batch preflight'ta query'ler birbirinden farklı, gradient'ler sıfırdan büyük ve birbirine çok yakın, trainable parametre 7686 olarak doğrulandı.
- Çalışma MPS üzerinde yaklaşık 14 dk 20 sn sürdü (3 seed). Çalıştırma hatası yok.
- Seed 42 ve 0'ın PV test metrikleri 5 hane aynı (farklı epoch'larda seçilmiş checkpoint'ler, validation Macro-F1 değerleri farklı).
- Attention dosyaları her seed için PV test `[1219, 4, 256]` ve PlantDoc `[603, 4, 256]` olarak kaydedildi (`image_id` ve metadata satır indeksleriyle). Agent-collapse diagnostiği yalnız PV test dosyaları üzerinde, scratchpad'de tek seferlik kodla çalıştırıldı; diagnostik için ayrı dosya oluşturulmadı, sonuçlar yalnızca bu günlükte tutulur.
- Checkpoint, prediction ve attention dosyaları `results/multi_agent_attention/` altında kalır (gitignore'da); yalnızca `seed_results.csv` ve `summary.json` `docs/experiment_results/multi_agent_attention/` altına içerikleri değiştirilmeden kopyalandı.

#### Sıradaki adım

Spatial-attention branch is considered sufficiently characterized at this stage. Kernel-Guided Attention will not be pursued in the current scope. The next methodological direction is semantic disease-morphology guidance using externally grounded pathology descriptions and frozen visual representations.

### 2026-10-19 — Frozen pathology text prototypes

- `data/pathology_morphology_prompts.txt` frozen as the sole source of morphology text; contents unchanged, exactly 3 sentences per class for 6 classes in the expected source order. Source SHA-256 is stored in the artifact.
- Encoder: Hugging Face `google/siglip-base-patch16-224`, pinned revision `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`; fully frozen, `eval()`, `torch.inference_mode()`, official `get_text_features` API. Each sentence encoded separately on CPU in float32 with deterministic algorithms and one thread; no truncation.
- Construction: sentence-level L2 normalization → class-wise mean over 3 sentences → final L2 normalization.
- Result: normalized sentence embeddings `[6, 3, 768]`; final prototypes `[6, 768]`, saved to `artifacts/pathology_text/pathology_text_prototypes_siglip.pt`. Final norms approximately 1 (maximum absolute deviation < 1e-6); NaN/Inf checks passed. Cosine similarities were diagnostic only and did not change source text or prototypes.
- Artifact/source matching and mean/normalization reconstruction passed; repeated offline extraction produced bitwise identical sentence embeddings and prototypes. Parser rejection checks passed for wrong order, missing/extra classes or sentences, and text before a header.
- No image data, PlantDoc metrics, DINO features/caches, or classification training used.
- Environment: torch 2.9.0, transformers 4.57.1; missing sentencepiece 0.2.2 installed only in `/private/tmp/pathology_siglip_deps`; downloaded model cache in `/private/tmp/pathology_siglip_hf_cache`. For this environment, rerun with `PYTHONPATH=/private/tmp/pathology_siglip_deps python3 scripts/build_pathology_text_prototypes.py --cache-dir /private/tmp/pathology_siglip_hf_cache`.

### 2026-10-19 — DINOv2 CLS → frozen pathology prototype classifier
- Frozen cached DINOv2 CLS input `[8735, 768]`; frozen SigLIP pathology prototypes `[6, 768]`. Trainable `Linear(768 → 768, bias=False)` (589824 parameters), L2-normalized projection, cosine logits with fixed scale 10.0 and CrossEntropyLoss. Fixed pathology-derived text prototypes were used as the classifier output geometry; no morphology-learning or semantic-grounding claim.
- Reused existing metadata row order, labels and splits (PV train 5692 / validation 1221 / test 1219; PlantDoc external test 603); no new splits, feature extraction, image reads or cache changes. PV-only training and validation Macro-F1 selection; PlantDoc evaluation only after restoring each seed’s selected checkpoint. No tuning against PlantDoc.
- Optimization reused from `docs/experiment_results/dinov2_raw/probe_config.json` and `notebooks/dinov2_raw_baseline.ipynb`: AdamW, lr=1e-3, weight_decay=1e-4, batch_size=256, max_epochs=50, patience=5, seeds [42,0,1], strict improvement for selection; original CLS input used without added normalization. CPU execution (one thread), rather than the earlier Colab runtime; hardware is a comparability limitation. Best states held in memory; no checkpoint files.
- Sanity checks passed: feature/prototype dimensions, prototype norms ≈1, exact prototype/metadata label mapping, NaN/Inf absence, split/dataset separation; first batch `[256,768]` → `[256,768]`, normalized norms ≈1, logits `[256,6]`, finite nonzero projection gradients; prototype buffer unchanged after training.

| Seed | Best epoch | PV F1 / BA / accuracy | PlantDoc F1 / BA / accuracy | ΔF1 | Semantic − CLS PD F1 |
|---|---|---|---|---|---|
| 42 | 8 | 0.97648 / 0.97313 / 0.97703 | 0.27390 / 0.33337 / 0.36484 | 0.70258 | -0.03819 |
| 0 | 20 | 0.98821 / 0.98840 / 0.98852 | 0.22646 / 0.29827 / 0.32670 | 0.76175 | -0.07084 |
| 1 | 19 | 0.98124 / 0.97891 / 0.98277 | 0.23120 / 0.29798 / 0.32504 | 0.75004 | -0.03888 |

Mean ± sample std (ddof=1):
- pv_test_macro_f1: 0.98198 ± 0.00590.
- pv_test_balanced_accuracy: 0.98015 ± 0.00771.
- pv_test_accuracy: 0.98277 ± 0.00574.
- plantdoc_macro_f1: 0.24385 ± 0.02613.
- plantdoc_balanced_accuracy: 0.30987 ± 0.02035.
- plantdoc_accuracy: 0.33886 ± 0.02252.
- delta_macro_f1: 0.73812 ± 0.03133.
- semantic_minus_cls_plantdoc_macro_f1: -0.04930 ± 0.01865.

PlantDoc per-class recall (mean ± sample std):
- Tomato___Bacterial_spot: 0.01835 ± 0.00917.
- Tomato___Early_blight: 0.45455 ± 0.02273.
- Tomato___Late_blight: 0.92192 ± 0.01040.
- Tomato___Leaf_Mold: 0.11355 ± 0.06345.
- Tomato___Septoria_leaf_spot: 0.32000 ± 0.05207.
- Tomato___Tomato_mosaic_virus: 0.03086 ± 0.01069.

- Ordinary CLS comparison source: `docs/experiment_results/dinov2_raw/seed_results.csv` (`representation=cls`), read rather than hard-coded. CLS PV Macro-F1 0.97885 ± 0.00187; PlantDoc Macro-F1 0.29315 ± 0.02131. The semantic classifier had lower PlantDoc Macro-F1 in all three seeds; this is descriptive, with no statistical significance or causal claim.
- Results: `docs/experiment_results/pathology_semantic_prototype/seed_results.csv` and `summary.json`; the latter includes per-seed validation histories, input SHA-256 identities and configuration. No runtime errors; no commit or push.

#### Final scientific interpretation (2026-10-19)

The semantic prototype classifier retained high PV source performance (Macro-F1 0.98198 ± 0.00590), but PlantDoc Macro-F1 (0.24385 ± 0.02613) remained below the ordinary CLS baseline (0.29315 ± 0.02131). All three paired seeds gave worse PlantDoc F1 for the semantic model (differences −0.03819, −0.07084, −0.03888). In this tested configuration, class-level fixed pathology prototypes with an unrestricted learned projection did not provide improved field robustness. This does not imply that pathology knowledge is useless, and does not establish that other ways of using pathology concepts will succeed. Fixed pathology-derived text prototypes were used as the classifier output geometry; no semantic grounding or learned morphology is established. This is a descriptive result, without statistical significance or causal claims. Original results, prompts, scale=10.0, architecture and PV-only selection remain unchanged; finalization involved consistency checks only, without rerunning or optimizing the classifier.

### 2026-10-19 — Source-grounded concept-level morphology bank

- Following the lack of improved field robustness in the class-level experiment, the next stage shifts to reusable concept-level morphology representations. No new classifier or distillation training has been performed; improvement is not presumed.
- `data/pathology_morphology_concepts.txt` is the sole source of concept descriptions: 14 short English descriptions of image-observable morphology derived only from `data/pathology_morphology_prompts.txt`. No disease names, diagnostic claims, new pathology information, web research, microscopic details or image data were used. Original disease texts were preserved.
- `scripts/build_pathology_morphology_concepts.py` contains the fixed, manually source-grounded 3-state class mapping. `present` means explicitly supported morphology; `possible` preserves conditional wording; `not_supported` means not established by the text, not visual absence. Surface growth, water-soaked appearance, bacterial surrounding yellowing, curling, narrowing and deformation remain conditional. Exact supporting source sentences and their zero-based indices are saved for each mapped pair. Mapping is source annotation, not an image-level label or training target.
- Frozen `google/siglip-base-patch16-224`, revision `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`; `eval()`, inference mode, official `get_text_features`, one description per embedding and L2 normalization. CPU float32, deterministic algorithms, one thread, seed 0, fixed-length padding, no truncation. Existing local model cache used offline.
- Artifact: `artifacts/pathology_text/pathology_morphology_concepts_siglip.pt`; concept embeddings `[14, 768]`. Unit-norm checks passed (maximum deviation about 2.98e-7); no NaN/Inf. The 14×14 cosine matrix is diagnostic only; concept definitions and mapping were fixed before encoding and were not changed based on cosine values. Source SHA-256 hashes, class order, source evidence and model revision are included in the artifact.
- No PlantDoc images, metrics or tuning informed the concept bank. Existing semantic result summaries were read only to finalize that previous experiment. No DINO cache access or change was needed for concept construction.
- Reproduce in this environment: `HF_HUB_OFFLINE=1 PYTHONPATH=/private/tmp/pathology_siglip_deps python3 -B scripts/build_pathology_morphology_concepts.py --cache-dir /private/tmp/pathology_siglip_hf_cache`. `sentencepiece` and the model cache remain in temporary directories as previously recorded. Tensor artifacts remain excluded by the existing gitignore; source txt files, scripts and lightweight result summaries are reviewable for a future commit. No staging, commit or push performed.

- PV description pilot: {"model": "gpt-4.1-mini", "model_version": ["gpt-4.1-mini-2025-04-14"], "prompt_sha256": "df089ab118865ef94828717b6c4fda34bb258437ffa1a69f09ba39adc81366b7", "completed_count": 6, "validation_pass_count": 6, "leakage_count": 0, "failure_count": 0}; fixed label-blind file prompt; 6 PV-train images (1/class), seed 42; original-resolution input, no disease labels in requests, no embedding, no training, no PlantDoc. Descriptions require manual review.

- PV description pilot: {"model": "gpt-4.1-mini", "model_version": ["gpt-4.1-mini-2025-04-14"], "prompt_sha256": "df089ab118865ef94828717b6c4fda34bb258437ffa1a69f09ba39adc81366b7", "completed_count": 30, "validation_pass_count": 30, "leakage_count": 0, "failure_count": 0}; fixed label-blind file prompt; 30 PV-train images (5/class), seed 42; original-resolution input, no disease labels in requests, no embedding, no training, no PlantDoc. Descriptions require manual review.

### 2026-10-19 — PV → GPT description → frozen SigLIP semantic pilot (finalized)

- Motivation: inspect whether label-blind visual descriptions contain class-related semantic structure before scaling annotation. Pipeline: PV-train image → GPT description → frozen SigLIP text embedding → descriptive diagnostics.
- Frozen prompt: `data/pv_vlm_description_prompt.txt`, SHA-256 `df089ab118865ef94828717b6c4fda34bb258437ffa1a69f09ba39adc81366b7`. Only the unchanged prompt, neutral ID and memory-encoded original-resolution image were supplied as model content; no disease label/name, class path or filename was included. API configuration/metadata remained separate. Maximum output validation: 50 words; descriptions were not rewritten. Lexical validation is a screening check, not proof of description correctness.
- Sample: existing PlantVillage train split only, seed 42, 6 classes × 5 images = 30, all original inputs 256×256. The initial six image identities/descriptions were retained; 6 descriptions reused and 24 newly inferred. GPT model `gpt-4.1-mini`, observed version `gpt-4.1-mini-2025-04-14`; 30/30 completed and passed validation, 0 detected disease-name leakage, 0 word-limit violations, 0 failures. No PlantDoc data or results were used in this experiment.
- Encoder: frozen text-only `google/siglip-base-patch16-224`, revision `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`; eval/inference mode, deterministic CPU float32, each description separately encoded without added class text or truncation and L2-normalized. Embeddings `[30,768]`, no NaN/Inf. Pairwise cosine over unique unordered pairs: same-class (60 pairs) 0.9141676158 ± 0.0355630136; different-class (375 pairs) 0.9004736320 ± 0.0351854822 (sample std, ddof=1). These dependent pairs are descriptive summaries, not independent statistical replicates.
- Class prototypes: arithmetic mean of five normalized embeddings per class, followed by L2 normalization; shape `[6,768]`. Prototype cosine similarities were high: Bacterial spot–Septoria 0.98752, Leaf Mold–Tomato mosaic virus 0.98807, Late blight–Tomato mosaic virus 0.94091, indicating limited class separation in this natural-description representation.
- Leave-one-out diagnostic: each query was excluded from its own class prototype (other 4 embeddings); other class prototypes used 5 embeddings each. Prediction was maximum cosine. Accuracy 0.30000 (9/30), Macro-F1 0.29209, balanced accuracy 0.30000. Per-class recall in frozen class order (Bacterial spot, Early blight, Late blight, Leaf Mold, Septoria, Tomato mosaic virus): [0.40, 0.40, 0.40, 0.20, 0.00, 0.40]. Confusion matrix (rows=true, columns=predicted, same order): [[2,0,0,1,2,0], [1,2,1,0,0,1], [0,2,2,1,0,0], [1,0,0,1,0,3], [3,0,1,1,0,0], [0,0,0,3,0,2]]. Query support counts and all cosine scores are retained in `embedding_summary.json`.
- Interpretation: this balanced pilot shows weak but observable class-related structure: same-class cosine is slightly higher on average, while class separation remains limited and overlapping. LOO accuracy exceeds the nominal six-class chance accuracy (1/6 ≈ 0.1667) descriptively; no statistical significance claim is made. These results do not establish a strong disease classifier, validated morphology grounding, or external-field robustness. The pilot is insufficient evidence to justify full 5,692-image GPT annotation solely for nearest-prototype classification. The representation may instead be considered as a candidate auxiliary semantic signal for future distillation/alignment experiments; its utility is not established. Full 5,692-image annotation has not been performed.
- Provenance: `scripts/run_pv_vlm_description_pilot.py`, `scripts/build_pv_vlm_description_embeddings.py`, `docs/experiment_results/pv_vlm_description_pilot/{descriptions.csv,summary.json,embedding_summary.json}` and `artifacts/pv_vlm_description/pv_vlm_description_embeddings_siglip.pt`. Generated tensor artifacts remain gitignored. `sentencepiece==0.2.2` is now declared for the SigLIP tokenizer; unrelated dependencies unchanged. Finalization used local consistency checks only: no new API calls, inference, embedding generation, training, tuning or PlantDoc access. No commit or push.
