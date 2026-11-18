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

- Structured morphology v2 prompt-development pilot: same 30 PV-train images as v1; strict six-string JSON schema, combined 150-word validation limit, cautious "not clearly visible" wording; {"model": "gpt-4.1-mini", "model_version": ["gpt-4.1-mini-2025-04-14"], "prompt_sha256": "4a5150a8b66d27b132a0be35816b9fcf15592531fb552538886312fbd770935c"}; frozen SigLIP google/siglip-base-patch16-224; diagnostics {"same_class": {"count": 60, "mean": 0.9684615979592005, "sample_std": 0.0145442147628839}, "different_class": {"count": 375, "mean": 0.9609444832801819, "sample_std": 0.01610043613046728}, "gap": 0.0075171146790186105, "loo": {"accuracy": 0.23333333333333334, "macro_f1": 0.20341880341880345, "balanced_accuracy": 0.2333333333333333}, "comparison": {"same_class_mean": {"v1": 0.9141676157712937, "v2": 0.9684615979592005, "absolute_difference_v2_minus_v1": 0.05429398218790682}, "different_class_mean": {"v1": 0.9004736320177714, "v2": 0.9609444832801819, "absolute_difference_v2_minus_v1": 0.060470851262410474}, "cosine_gap": {"v1": 0.013693983753522265, "v2": 0.0075171146790186105, "absolute_difference_v2_minus_v1": -0.006176869074503655}, "accuracy": {"v1": 0.3, "v2": 0.23333333333333334, "absolute_difference_v2_minus_v1": -0.06666666666666665}, "macro_f1": {"v1": 0.2920875420875421, "v2": 0.20341880341880345, "absolute_difference_v2_minus_v1": -0.08866873866873867}, "balanced_accuracy": {"v1": 0.30000000000000004, "v2": 0.2333333333333333, "absolute_difference_v2_minus_v1": -0.06666666666666674}}}; V2 differs from V1 in both structured generation and field-wise embedding aggregation; therefore this is a pipeline-level development comparison, not an isolated prompt-only ablation.; no training, threshold tuning, significance or generalization claim; no PlantDoc; independent unseen source-side PV confirmation still required.

- V3-final discriminative structured morphology development: rationale from V2 text-overlap/retention error analysis; frozen six-string strict JSON schema, combined 180-word limit, discriminative_summary 35-word limit and cautious wording; same 30-image development set, no resampling; candidate = discriminative_summary only, frozen SigLIP with lossless chunking; {"model": "gpt-4.1-mini", "versions": ["gpt-4.1-mini-2025-04-14"], "metrics": {"accuracy": 0.23333333333333334, "macro_f1": 0.2324074074074074, "balanced_accuracy": 0.23333333333333336, "cosine_gap": 0.015007034301757871}}; no PlantDoc, no significance claim; prior 60-image confirmation not used; entirely new independent unseen PV-train confirmation required.

- V4 taxonomy-aware structured morphology development: fixed six-class morphology ontology in prompt only; ground-truth labels never dynamically supplied; frozen six-string strict JSON schema, combined 200-word limit, evidence_summary 45-word limit and cautious wording; same 30-image development set, no resampling; candidate = evidence_summary only, frozen SigLIP with lossless chunking; {"model": "gpt-4.1-mini", "versions": ["gpt-4.1-mini-2025-04-14"], "metrics": {"accuracy": 0.4, "macro_f1": 0.42003367003367004, "balanced_accuracy": 0.39999999999999997, "cosine_gap": 0.011147620797157254}}; no PlantDoc, no significance claim; prior 60-image confirmation not used; entirely new independent unseen PV-train confirmation required.

## Semantic Morphology Extraction, Canonical Representation, and Information-Loss Checkpoint

Checkpoint date: 2026-10-21. This consolidates the completed semantic-morphology work since `1c3585a`, including the earlier short V2–V4 entries above. It preserves the distinction between development, independent source confirmation, blocked confirmation, exploratory sensitivity analysis, and future method development. This documentation pass used existing text/results and static script inspection only; no API requests, SigLIP inference, visual feature extraction, model training, or new PlantDoc analysis were performed.

### A. Thesis objective and experimental discipline

Source domain: PlantVillage (PV). External field domain: PlantDoc (PD). The thesis studies transfer from controlled PV images to real field conditions, and whether morphology-oriented semantic information can help reduce the lab-to-field robustness gap relative to visual-only baselines. A motivation is to encourage reliance on visible disease morphology rather than possible source/background shortcuts; these diagnostics do not establish that such shortcuts caused earlier errors.

PlantDoc was previously used for EfficientNet, DINOv2, and other visual baseline evaluations. It was also used in the PV↔PD PCA/domain-shift diagnostic. Consequently, PlantDoc is not historically a completely unseen or untouched dataset. Earlier target-domain characterization and external baseline results remain part of the research history; this checkpoint does not erase that exposure.

PlantDoc was not used for VLM prompt selection, semantic representation selection, morphology ontology design, canonicalization design, teacher/fusion architecture selection, knowledge-distillation design, or hyperparameter tuning in the current semantic-morphology development loop.

Historical target-domain characterization and baseline evaluation were performed on PlantDoc, but the subsequent semantic-morphology and distillation method-development loop is source-only with respect to model selection.

No PlantDoc data were used for prompt development, semantic representation selection, ontology design, or source-side diagnostics documented in this checkpoint. This statement concerns the present development loop, not the historical baseline/PCA work summarized as motivation.

Going forward, PlantDoc metrics will not be consulted to choose an ontology, prompt, teacher/fusion architecture, distillation loss, or hyperparameters. Those decisions must use source-side development/validation only. The completed development/confirmation diagnostics are not evidence of reduced domain gap or improved field robustness.

Frozen candidate systems will later be evaluated on PlantDoc as an external target-domain benchmark, but this must not be described as a historically unseen test set.

### B. Semantic morphology motivation and intended method direction

RAW EfficientNet and frozen DINOv2 visual baselines performed strongly on PV but exhibited substantial performance drops on PD, as documented in the earlier baseline sections. This motivated investigation of a more interpretable morphology-information branch. The aim is not to use GPT as the final disease classifier, nor to replace visual representations with a sparse canonical vector.

The intended method direction is:

```text
PV image
→ DINOv2 visual features
+
VLM/GPT-derived morphology semantic information
→ multimodal/fused teacher representation
→ knowledge distillation
→ image-only student
→ frozen external PlantDoc evaluation
```

DINOv2 visual representation will be retained and used together with semantic text/morphology information. V1–V5, the cue audit, 28D diagnostic, and information-loss audit investigate what the teacher's semantic-information branch observes and preserves. They do not yet implement or validate a fused teacher or distilled student. Canonical morphology vectors are not designed as the standalone final classifier. Subsequent knowledge distillation is planned to transfer semantic/visual teacher knowledge into an image-only student; the fusion design, distillation loss, and student design remain future work.

### C. V1 — free-form morphology description

GPT-4.1-mini (observed version `gpt-4.1-mini-2025-04-14`) produced label-blind natural morphology descriptions. Disease labels, class paths, and filenames were not supplied as model content. The original development sample comprised 30 PV-train images, five per class. The downstream candidate was the entire free-form description encoded by frozen `google/siglip-base-patch16-224` (revision `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`).

Development LOO class-prototype accuracy was 9/30 = 0.30000; Macro-F1 0.29209; balanced accuracy 0.30000. Same-class cosine mean was 0.91417, different-class mean 0.90047, and cosine gap 0.01369. The descriptions carried some class-related semantic structure, but separation was weak and cross-class similarities were generally high. Generic natural description alone was insufficient in this diagnostic. No significance claim is made.

Provenance: `docs/experiment_results/pv_vlm_description_pilot/{descriptions.csv,summary.json,embedding_summary.json}`; existing V1 scripts and prompt were already covered by `1c3585a`.

### D. V2 — structured visible morphology and overall_summary

V2 generated six string fields: `color_pattern`, `lesions_spots`, `center_border_internal_pattern`, `distribution`, `surface_deformation`, and `overall_summary`. The ground-truth label remained hidden. The prompt requested visible morphology only, cautious wording such as “not clearly visible,” and no biological-absence inference. The combined output validation limit was 150 words. The candidate later selected on development was `overall_summary` alone.

For text exceeding SigLIP's 64-token context, `scripts/siglip_text_encoding.py` partitions all content tokens in token space, budgets special tokens per chunk, and discards no tokens. Each chunk embedding is L2-normalized; chunks receive an equal mean followed by final L2 normalization. Single-chunk results retain the equivalent existing normalized result without redundant normalization. This is lossless with respect to input tokens, not a claim that chunk pooling preserves every semantic relation.

| V2 development representation | Accuracy | Macro-F1 | Balanced accuracy | Cosine gap |
|---|---:|---:|---:|---:|
| overall_summary only | 0.56667 | 0.55469 | 0.56667 | 0.01945 |
| Equal pooling of all six fields | 0.23333 | 0.20342 | 0.23333 | 0.00752 |

Structured generation itself was not sufficient to explain the weaker all-field result. Equal pooling appears to introduce generic/repeated information and compress classes together, whereas the natural summary acted as useful semantic compression on development. This is a development-set observation and selection, not final evidence or an isolated causal ablation of prompt structure.

Provenance: `data/pv_vlm_description_prompt_structured.txt`, `scripts/run_pv_vlm_description_structured_pilot.py`, `docs/experiment_results/pv_vlm_description_structured_pilot/{descriptions.jsonl,summary.json,field_diagnostics.json}`. Summary-only development verification is also retained in `pv_vlm_semantic_confirmation/summary.json`.

### E. Field-level V2 diagnostic

Existing structured outputs were analyzed field by field without new API inference. The original 30-image set gave the following individual-field LOO results:

| Field | Accuracy | Macro-F1 |
|---|---:|---:|
| color_pattern | 0.36667 | 0.37398 |
| lesions_spots | 0.30000 | 0.28290 |
| center_border_internal_pattern | 0.23333 | 0.20723 |
| distribution | 0.23333 | 0.18571 |
| surface_deformation | 0.23333 | 0.21517 |
| overall_summary | 0.56667 | 0.55469 |

`overall_summary` was the strongest individual field; `color_pattern` also showed signal. Distribution and surface deformation were weak alone under this text embedding/prototype protocol. That does not show those information types are intrinsically unimportant: useful information may be present while its embedding or aggregation is ineffective. Indiscriminate pooling performed worse than natural summarization. These are small-sample descriptive findings, not statistical proof. Provenance: `pv_vlm_description_structured_pilot/field_diagnostics.json`.

### F. Independent 60-image V1 versus V2 source confirmation

A new PV-train sample contained 60 images, ten per class, with zero source-image overlap with the original development 30. V2's summary-only candidate had already been selected on development. No PD data were used in this confirmation.

| Representation | Accuracy | Macro-F1 | Balanced accuracy | Cosine gap |
|---|---:|---:|---:|---:|
| V1 free-form | 0.33333 | 0.32222 | 0.33333 | 0.009276 |
| V2 overall_summary | 0.35000 | 0.33830 | 0.35000 | 0.012643 |

Paired correctness: both correct 8; V1 only correct 12; V2 only correct 13; both wrong 27. The large V2 development advantage did not reproduce. V2's source-side advantage remained directionally positive but small; it was retained as an observation candidate rather than a solved representation. No significance claim is made. This set was subsequently inspected in error analysis and is no longer pristine for future prompt confirmation.

Provenance: `scripts/run_pv_vlm_semantic_confirmation.py`, `docs/experiment_results/pv_vlm_semantic_confirmation/{descriptions_v1.csv,descriptions_v2.jsonl,summary.json}`. The protocol embeds the 60-image identity manifest and original-development exclusions.

### G. V2 confirmation error analysis

Text-only analysis of the existing 60-image outputs found overlapping language in difficult class pairs. Bacterial spot (BS) and Septoria (SP) often shared dark-spot, yellowing, and pale-center wording; Septoria summaries did not explicitly express circular/round spots. Early blight (EB) and Late blight (LB) shared irregular brown/necrotic lesion language; concentric-ring evidence for EB and water-soaked wording for LB were frequently missing. Leaf Mold (LM) and mosaic virus (MV) shared yellow-green discoloration/curling language, while explicit visible surface-growth evidence for LM was frequently missing.

Detailed-field-to-summary affirmative retention was 23/25 for pale/gray centers, 21/21 for dark borders/margins, 1/6 for yellow-halo color specificity, and 6/7 for vein association. No affirmative detailed-field ring or surface-growth evidence was detected under that analysis's lexical rules, so affirmative retention rates for those concepts were undefined. Some discriminators were missing from the detailed observations themselves; summary compression alone cannot explain all confusion. Making summaries longer was therefore unlikely, by itself, to address the limitations. Observation quality, cue specificity, and qualifier retention remained relevant hypotheses.

The lexical analysis assesses text, not visual truth. Its own uncertainty/affirmative conventions differ from the later 14-cue audit and must not be silently treated as the same measurement. Provenance: `pv_vlm_semantic_confirmation/error_analysis.json`, including evidence, rules, representative cases, and limitations.

### H. V3 — discriminative structured summary

V3 attempted to retain only visibly distinctive morphology while avoiding generic observations. The candidate was `discriminative_summary`; the same original 30 development images were reused. Accuracy was 0.23333, Macro-F1 0.23241, balanced accuracy 0.23333, and cosine gap 0.01501.

Forcing discriminative selection did not improve the diagnostic. Descriptions also varied across prompt versions: for example, faint concentric-ring wording appeared in V3 for development images where V2 said no clear rings. This is textual instability, not image-verified evidence that either version is correct. Visually distinctive is not necessarily diagnostically discriminative. V3 was label-blind and lacked the six-class task ontology, so it had no explicit task-specific guide to which cues distinguish the classes.

Provenance: `data/pv_vlm_description_prompt_v3_discriminative.txt`, `scripts/run_pv_vlm_description_v3_discriminative.py`, `pv_vlm_description_v3_discriminative/{descriptions.jsonl,summary.json}`.

### I. V4 — taxonomy-aware morphology-only observation

V4 supplied the same six candidate disease categories and visible-morphology guide to every image. The image's true label remained hidden; the model was instructed not to diagnose or name diseases in its output. This was a fixed shared inspection ontology, not image-specific label conditioning. The candidate representation was `evidence_summary`.

Validation rejected disease/pathogen names while allowing generic morphology such as spots, mosaic-like patterns, and blotches. Meta-commentary such as “useful for disease differentiation” was rejected separately from name leakage. Raw responses were retained even when validation failed. Development accuracy was 0.40000, Macro-F1 0.42003, balanced accuracy 0.40000, and cosine gap 0.01115.

Taxonomy-aware guidance performed above V1/V3 but below V2 on development. It appeared potentially useful as observation guidance, while also risking checklist-like descriptions. No confirmed superiority follows from this development comparison.

Provenance: `data/pv_vlm_description_prompt_v4_taxonomy_aware.txt`, `scripts/run_pv_vlm_description_v4_taxonomy_aware.py`, `pv_vlm_description_v4_taxonomy_aware/{descriptions.jsonl,summary.json}`.

### J. V5 — hybrid V2 summary and taxonomy guidance

V5 aimed to preserve V2's broader natural `overall_summary` while using V4's taxonomy only for inspection. On the original development sample, accuracy was 0.30000, Macro-F1 0.30736, balanced accuracy 0.30000, and cosine gap 0.01531.

The combination did not produce additive benefit in this test. Checklist/negative-cue language may have diluted useful information, but this mechanism was not isolated experimentally. Taxonomy guidance should not simply be injected into every description stage on the assumption that it improves representation.

Provenance: `data/pv_vlm_description_prompt_v5_hybrid.txt`, `scripts/run_pv_vlm_description_v5_hybrid.py`, `pv_vlm_description_v5_hybrid/{descriptions.jsonl,summary.json}`.

### K. Frozen V2 versus V4 — new 120-image confirmation attempt

The frozen comparison selected 120 new PV-train images, 20 per class, seed 42, with neutral IDs `pv_confirm2_001`–`pv_confirm2_120`. Source identities had zero overlap with both the development 30 and previous confirmation 60. V2/V4 used paired identical image bytes. Prompts were frozen and prompt tuning on this set was prohibited. No PD data were used.

Primary status: `blocked_invalid_or_missing_paired_outputs`. V4 had 120/120 valid outputs; V2 had 115/120. The five V2 failures were solely the frozen combined 150-word validation rule: word counts 160, 151, 152, 168, and 157. Operational failure rate: 5/120 = 4.1667%. These were structurally parsed descriptions without other recorded validation errors; exceeding the word limit is an operational compliance limitation, not evidence that the descriptions contained no usable morphology. Their morphological correctness was not independently established.

The primary protocol required 120 valid paired outputs. Consequently, the primary confirmatory comparison was not completed; no successful confirmation or winner is recorded.

Provenance: `scripts/run_pv_vlm_v2_v4_confirmation2.py`, `pv_vlm_v2_v4_confirmation2/{sample_manifest.json,v2_descriptions.jsonl,v4_descriptions.jsonl,summary.json}`. Frozen prompt, validator, helper, and sample hashes remain in the saved protocol.

### L. Exploratory common-valid 115 sensitivity analysis

**EXPLORATORY_COMMON_VALID_115_NOT_CONFIRMATORY**

Only images valid under both frozen protocols were included. V2-induced exclusions may be non-random; the original confirmation decision rule was not applied. These are exploratory/sensitivity metrics only, with no winner or significance claim.

| Representation | Accuracy | Macro-F1 | Balanced accuracy | Cosine gap |
|---|---:|---:|---:|---:|
| V2 | 0.373913 | 0.361192 | 0.369444 | 0.013762 |
| V4 | 0.452174 | 0.447038 | 0.449366 | 0.010946 |

V2 same-class cosine: 0.869517 ± 0.064121; different-class: 0.855755 ± 0.064236. V4 same-class: 0.891983 ± 0.053843; different-class: 0.881037 ± 0.054232. Standard deviations are sample standard deviations. Pair summaries are descriptive and contain dependent pairs.

Paired correctness: both correct 26; V2 only 17; V4 only 26; both wrong 46.

| Class | Support | V2 recall | V4 recall |
|---|---:|---:|---:|
| BS | 19 | 0.2105 | 0.3158 |
| EB | 18 | 0.1667 | 0.2778 |
| LB | 19 | 0.3158 | 0.4737 |
| LM | 20 | 0.6000 | 0.5000 |
| SP | 20 | 0.4500 | 0.5500 |
| MV | 19 | 0.4737 | 0.5789 |

Confusion counts V2→V4: BS→SP 7→5; EB→LB 9→6; LB→EB 7→3; MV→LM 6→4; LM→MV worsened 2→5. V4 recall was higher in five of six classes, an encouraging exploratory pattern across several difficult pairs. Non-random compliance exclusions prevent confirmatory interpretation. Global cosine gap did not consistently track prototype classification quality and remains a descriptive diagnostic rather than the primary selection criterion.

Provenance: `pv_vlm_v2_v4_confirmation2/summary.json`, subtree `exploratory_common_valid_sensitivity`. The enclosing primary status remains blocked.

### M. Canonical morphology motivation

Natural text is rich but variable: similar observations can be phrased as “small dark lesions” or “tiny blackish spots.” Canonicalization maps observations into a standard visual vocabulary to improve interpretability and investigate whether generic text embedding discards relevant information. It must not invent observations absent from the text. This is investigation of the future teacher's semantic branch, not a standalone final-classifier proposal.

### N. Existing 14-cue ontology and states

The frozen cue order is:

1. small_dark_spots
2. circular_spots
3. dark_borders
4. lighter_gray_centers
5. surrounding_yellowing
6. concentric_ring_pattern
7. large_irregular_blotches
8. water_soaked_appearance
9. yellowish_patches
10. olive_brown_surface_growth
11. mosaic_mottled_green_pattern
12. leaf_curling
13. leaf_narrowing
14. leaf_deformation

`supported` means explicit positive visible evidence in existing V2 text; `uncertain` captures weak or partial textual support; `not_observed` means no positive textual support under the rules. **not_observed does not mean biological absence.** Hidden labels were used only after state extraction for aggregation. Existing assignments were not changed by the subsequent diagnostics.

### O. Original-development 14-cue coverage audit

Only existing original 30 V2 outputs were used, without new API inference. Deterministic, inspectable vocabulary/regex rules and evidence snippets produced 420 image×cue assignments.

| Cue | Supported | Uncertain | Not observed | S+U coverage |
|---|---:|---:|---:|---:|
| small_dark_spots | 6 | 6 | 18 | 40.0% |
| circular_spots | 0 | 0 | 30 | 0.0% |
| dark_borders | 10 | 0 | 20 | 33.3% |
| lighter_gray_centers | 8 | 2 | 20 | 33.3% |
| surrounding_yellowing | 2 | 16 | 12 | 60.0% |
| concentric_ring_pattern | 0 | 3 | 27 | 10.0% |
| large_irregular_blotches | 4 | 4 | 22 | 26.7% |
| water_soaked_appearance | 0 | 0 | 30 | 0.0% |
| yellowish_patches | 5 | 13 | 12 | 60.0% |
| olive_brown_surface_growth | 0 | 0 | 30 | 0.0% |
| mosaic_mottled_green_pattern | 7 | 1 | 22 | 26.7% |
| leaf_curling | 8 | 18 | 4 | 86.7% |
| leaf_narrowing | 8 | 1 | 21 | 30.0% |
| leaf_deformation | 9 | 8 | 13 | 56.7% |

Most frequently represented: curling, surrounding yellowing, yellowish patches, deformation, and small dark spots. No positive/uncertain text matches occurred for circular spots, water-soaked appearance, or olive-brown growth. Mostly-uncertain flags applied to surrounding yellowing, concentric rings, yellowish patches, and curling. Several pathology-oriented cues were rarely or never expressed in these descriptions; this does not establish pathology irrelevance or image-level absence. Canonicalization cannot recover missing source observations.

Rules are a first pass: general yellowing without explicit halo/patch geometry can be partial support, pale/light centers are accepted as lighter centers, and negation scope or bounded attribute matching can be ambiguous. Provenance: `scripts/audit_v2_morphology_cue_coverage.py`, `pv_vlm_morphology_cue_audit/coverage_audit.json`.

### P. Canonical 28D representation diagnostic

Each cue uses two unweighted binary channels in the fixed cue order: supported→[1,0], uncertain→[0,1], not_observed→[0,0]. There are 28 dimensions, no learned weights, training, or tuning. Cosine LOO class-prototype diagnostics use the arithmetic mean of four remaining own-class vectors and five vectors for each other class. Complete zero vectors were checked before cosine/prototype metrics; none existed.

Active supported channels per image: 2.23 ± 1.59; uncertain channels: 2.40 ± 1.61; min–max for both: 0–6. Three cues were constant zero across both channels: circular spots, water-soaked appearance, and olive-brown growth. Standard deviations use ddof=1.

Development accuracy was 0.4000 (12/30), Macro-F1 0.3771, and balanced accuracy 0.4000. Same-class cosine was 0.392626 ± 0.245173, different-class 0.270002 ± 0.225445, gap 0.122624. Class recalls in BS/EB/LB/LM/SP/MV order were [0.60, 0.80, 0.40, 0.00, 0.60, 0.00]. One exact maximum-score tie (`pv_desc_027`, LM/SP) was resolved by the documented sorted-class-order rule.

The vector preserved class-related source-side structure but did not outperform V2 summary→SigLIP (0.56667 accuracy, 0.55469 Macro-F1). LM and MV had zero recall in this particular diagnostic, suggesting the present ontology/encoding did not separate them adequately. This is not proof that their relevant morphology is intrinsically unrepresentable.

A larger cosine gap across different representation spaces is not evidence of superior representation quality. The sparse-vector and SigLIP geometries differ, so their gap magnitudes cannot establish relative superiority.

Provenance: `scripts/analyze_canonical_morphology_representation.py`, `pv_vlm_morphology_cue_audit/canonical_28d_diagnostic.json`, which retains feature order, per-image vectors/scores, confusion matrix, class profiles, and fixed development references.

### Q. V2→canonical information-loss audit

The audit used only V2 structured development descriptions, the cue coverage audit, and the canonical 28D diagnostic, all matched to the same original 30 images (six classes × five). Input hash chains, identities, labels, and state/vector consistency were checked. No new API/SigLIP inference, confirmation samples, or PD data were used, and no existing cue assignments changed.

Question: which visibly descriptive information in the six V2 fields is not adequately preserved by the current 14-cue representation? Transparent keyword/regex rules extract candidate features as `present`, `uncertain`, or `not_mentioned`. Extraction is label-blind; labels describe aggregates only. Generic prose is excluded. Surface texture beyond deformation was included as an additional family G alongside focus families A–F.

| Information family | Images with loss | Image×feature loss records |
|---|---:|---:|
| C — Distribution geometry | 27/30 | 53 |
| D — Spatial/location information | 25/30 | 50 |
| A — Lesion count/density | 24/30 | 26 |
| B — Lesion size | 17/30 | 33 |
| G — Additional surface texture | 17/30 | 24 |
| F — Color structure | 16/30 | 27 |
| E — Lesion organization | 8/30 | 8 |

Families overlap. Counts are image×feature records, not raw repeated phrase counts or independent information bits; related features can overlap within and across families.

| Lost feature | Present | Uncertain | Coverage |
|---|---:|---:|---:|
| scattered_distribution | 19 | 0 | 63.3% |
| uneven_distribution | 19 | 0 | 63.3% |
| central_associated | 14 | 1 | 50.0% |
| small_lesion_size | 14 | 0 | 46.7% |
| numerous_lesions | 13 | 0 | 43.3% |
| rough_surface_texture | 10 | 2 | 40.0% |
| upper_leaf_associated | 11 | 0 | 36.7% |
| dark_lesion_centers | 11 | 0 | 36.7% |
| margin_associated | 10 | 0 | 33.3% |
| multiple_lesions | 9 | 0 | 30.0% |
| mixed_lesion_sizes | 9 | 0 | 30.0% |
| medium_lesion_size | 7 | 0 | 23.3% |
| widespread_distribution | 7 | 0 | 23.3% |
| dark_brown_black_discoloration | 6 | 0 | 20.0% |
| raised_surface_texture | 2 | 4 | 20.0% |

The audit's `strong_candidate` review flags were: scattered_distribution, uneven_distribution, central_associated, upper_leaf_associated, margin_associated, numerous_lesions, multiple_lesions, medium_lesion_size, widespread_distribution, and rough_surface_texture. These are candidate ontology extensions only. They have not been added or evaluated as a new representation. Ranking is descriptive by coverage, redundancy/ambiguity risk, and class-distribution variation as a tie breaker; recommendations use fixed coverage/risk rules, never classification accuracy or label-optimized performance.

Descriptive example only (n=5 per class): dark_brown_black_discoloration occurred in 5/5 Early-blight texts, 1/5 Late-blight texts, and 0/5 in each other class. Frequency is not predictive validation; class variation is not causality or image-verified pathology truth.

Risks include partial redundancy between standalone size features and existing combined cues, regex negation scope, object scope, and association versus dominant location. Existing mottling content is excluded from the unpatterned-green-contrast proposal where detected. Presence/uncertainty in text is not a biological ground-truth annotation, and not_mentioned is not biological absence.

The initial ontology discards substantial geometry/distribution/count information. This is a plausible, untested explanation for its lower prototype performance than V2 summary→SigLIP; the audit is not a causal ablation. V2 contains spatial, organizational, and texture information beyond the initial pathology-focused cue bank.

Provenance: `scripts/audit_v2_canonical_information_loss.py`, `pv_vlm_morphology_cue_audit/information_loss_audit.json`, including per-image evidence/rejected matches, overall/per-class counts, family summaries, rules, and candidate recommendations.

### R. Current scientific interpretation and working hypothesis

The completed source-side diagnostics support the following limited synthesis:

1. VLM descriptions contain class-related morphology signal in PV text-based diagnostics; visual grounding accuracy is not established by these metrics alone.
2. Structured V2 natural summaries retained more useful prototype structure on development than the initial 14-cue vector, while their large development gain over V1 did not reproduce on independent confirmation.
3. The initial canonical ontology was pathology-cue-centric and discarded geometry, distribution, count, organization, and texture information that remained in V2 text.
4. Taxonomy-aware prompting showed encouraging exploratory behavior, but V4 superiority was not confirmed.
5. Forcing more discriminative or taxonomy-heavy text did not reliably improve representation.
6. Semantic-branch quality depends both on what the VLM observes and how observations are represented downstream. A stronger standalone semantic diagnostic does not establish a stronger fused teacher or distilled student.

Working hypothesis: a useful morphology semantic branch may need both pathology-specific lesion cues and image-grounded count, size, spatial concentration, organization, and texture. These should complement retained DINOv2 visual information in a multimodal teacher. This remains a source-side hypothesis; no PV→PD gap reduction has been demonstrated for this method.

The main thesis question is:

> Whether adding morphology-oriented semantic information to DINOv2 visual representations, and subsequently distilling that multimodal knowledge into an image-only student, improves lab-to-field robustness relative to visual-only baselines.

There is no positive answer yet. No statistical significance, causal morphology, confirmed V4 superiority, field robustness improvement, or domain-gap reduction is claimed here.

### S. Next planned research step and checkpoint provenance

Design an expanded morphology+geometry ontology for the semantic branch using the coverage and information-loss audits. Do not append every frequent feature: assess redundancy and extraction ambiguity, preserve interpretability, distinguish presence from uncertainty, and retain spatial/count/size information where justified. The next source-side diagnostic should test whether an expanded canonical representation retains more of V2's class-related structure. No expanded ontology has yet been implemented or evaluated.

Retain DINOv2 visual features, then investigate how semantic text/morphology information can form a fused/multimodal teacher. Teacher architecture, fusion, distillation loss, and hyperparameters must be selected using PV-side evidence only. Distillation into an image-only student and frozen external PD benchmarking are later steps. PD scores must not guide any of these method-development decisions, and the eventual benchmark must acknowledge prior historical PD exposure.

Provenance verification before this edit: 144 numeric/identity/hash checks passed. Supplied values agree with repository outputs at their stated rounded precision; no numerical discrepancy was found. Checks covered V1–V5 and individual V2 fields, previous-60 metrics/paired counts and retention, blocked-120 validity/failure word counts, exploratory-115 metrics/recalls/confusion trends, 14-cue counts, 28D metrics/sparsity, information-loss families/features, pairwise source-sample disjointness, frozen prompt/validator/helper hashes, and chained audit input hashes. Actual result files and static scripts were inspected; no experiment was rerun to obtain these results. Historical error-analysis source hashes are snapshots at the time of that analysis, including its earlier research-log version; they do not assert that this subsequently appended log is unchanged.

Existing result directories retain the detailed manifests, summaries, descriptions, error analysis, and audits referenced above. Future checkpoint inclusion should be limited to the four V2–V5 prompts, seven completed generation/encoding scripts, three morphology-analysis scripts, relevant source-side JSON/JSONL/CSV results in the seven semantic-morphology result directories, and this log. Generated `.pt` embeddings/model artifacts and any PD data/results must remain outside that checkpoint. This pass performs no staging, commit, or push.
