# MASTER RESEARCH PROTOCOL

## Lab-to-Field Robustness in Tomato Leaf Disease Classification
### Frozen Representations, Background Shortcuts, and Spatial Agent Attention

---

## 0. ÇALIŞMANIN TEMEL FELSEFESİ

Bu tez, kontrollü laboratuvar görüntülerinde yüksek doğruluk veren bitki hastalığı sınıflandırıcılarının gerçek saha görüntülerinde neden başarım kaybettiğini ve bu kaybın hangi ölçüde daha güçlü görsel temsiller, arka plan izolasyonu ve uzamsal dikkat mekanizmaları ile azaltılabildiğini araştırır.

Çalışmanın amacı mümkün olan en fazla modeli denemek veya tek bir “en iyi skor” üretmek değildir.

Amaç:

- açık araştırma soruları sormak,
- az sayıda fakat güçlü referans model kullanmak,
- deneyleri kaynak alan üzerinde geliştirmek,
- PlantDoc'u gerçek dış test alanı olarak korumak,
- karmaşık yöntemleri ancak basit referansları geçebildikleri ölçüde anlamlı kabul etmek,
- negatif sonuçları saklamamaktır.

Ana deney hattı:

```text
VERİYİ HAZIRLA
      ↓
LAB → FIELD AÇIĞINI ÖLÇ
      ↓
CNN vs FROZEN FOUNDATION MODEL
      ↓
RAW vs LEAF-ISOLATED
      ↓
BASİT TOKEN TOPLAMA
      ↓
MULTI-AGENT ATTENTION
      ↓
KERNEL-GUIDED AGENT ATTENTION
      ↓
UZAMSAL ODAK ANALİZİ
      ↓
HATA ANALİZİ ve TEZ SONUCU
```

Bu tez, önerilen Agent Attention yöntemi basit GAP veya tek-sorgulu attention pooling yöntemini geçmese bile bilimsel olarak başarılı sayılabilir.

---

# 1. ARAŞTIRMA SORULARI

## RQ1 — Lab-to-Field Açığı

PlantVillage domates görüntülerinde eğitilen modeller, PlantDoc domates görüntülerine doğrudan aktarıldığında ne kadar başarım kaybeder?

Ana ölçümler:

- PlantVillage validation Macro-F1
- PlantVillage test Macro-F1
- PlantDoc Macro-F1
- PlantDoc Balanced Accuracy
- PlantDoc Top-1 Accuracy

Tanımlayıcı alan kayması:

```text
ΔMacroF1 = MacroF1_source_test − MacroF1_target
```

Bu fark yalnızca başarım düşüşünü ifade eder; tek başına nedensellik iddiası değildir.

---

## RQ2 — Temsil Gücü

Aynı kaynak veri kullanıldığında:

```text
EfficientNet-B0
vs.
Frozen DINOv2 ViT-B/14
```

saha transferinde nasıl farklılaşır?

Ana hipotez:

> Geniş ölçekli ön eğitimden geçmiş ve PlantVillage üzerinde değiştirilmemiş DINOv2 temsilleri, PlantVillage'a özel olarak eğitilmiş klasik CNN temsillerinden daha güçlü alan dışı genelleme sağlayabilir.

---

## RQ3 — Arka Plan Kestirmeleri

Yaprak arka plandan izole edildiğinde saha başarımı nasıl değişir?

Karşılaştırma:

```text
RAW
vs.
LEAF-ISOLATED
```

Bu deneyin amacı “arka plan açığın yüzde X'ini açıklıyor” demek değildir.

Amaç:

> Arka plan bilgisinin kaldırılması, farklı temsil ailelerini aynı şekilde mi yoksa farklı şekilde mi etkiliyor?

---

## RQ4 — Token Aggregation ve Agent Attention

Dondurulmuş DINOv2 patch token'ları üzerinde daha karmaşık uzamsal toplama mekanizmaları gerçekten gerekli midir?

Karşılaştırma sırası:

```text
CLS Linear
↓
GAP Linear
↓
Single-Query Attention Pooling
↓
Vanilla Multi-Agent Attention
↓
Kernel-Guided Multi-Agent Attention
```

Ana soru:

> Multi-agent yapı ve uzamsal kernel rehberliği, basit token toplama yöntemlerinden tutarlı ve ölçülebilir biçimde daha iyi saha genellemesi sağlıyor mu?

---

## RQ5 — Uzamsal Odak ve Saha Başarımı

Daha iyi saha başarımı gösteren modeller aynı zamanda daha fazla yaprak ön-planına ve daha az arka plan/border bölgesine mi odaklanmaktadır?

Bu çalışma piksel seviyesinde manuel lezyon anotasyonu üretmeyecektir.

Bu nedenle analiz:

```text
LESION LOCALIZATION
```

olarak değil,

```text
SPATIAL FOCUS / FOREGROUND RELIANCE ANALYSIS
```

olarak raporlanacaktır.

Ana ölçümler:

- Leaf Attention Mass
- Background Attention Mass
- Border Activation Ratio
- Attention Entropy

SAM veya başka bir segmentasyon maskesi yalnızca **leaf foreground referansı** olarak kullanılır.

Bu maskeler hastalık lezyonu ground truth'u olarak yorumlanmaz.

---

# 2. VERİ SETLERİ

## 2.1 Kaynak Alan — PlantVillage

Yalnızca domates sınıfları kullanılır.

Rolü:

- training,
- validation,
- source test,
- hyperparameter selection,
- checkpoint selection.

Önerilen bölme:

```text
70% Train
15% Validation
15% Test
```

Bölmeler sınıf bazında stratified oluşturulur.

Primary seeds:

```text
42
0
1
```

---

## 2.2 Hedef Alan — PlantDoc

Yalnızca PlantVillage ile semantik olarak güvenilir biçimde eşleşen domates sınıfları kullanılır.

PlantDoc:

```text
EXTERNAL TARGET TEST SET
```

olarak kalır.

PlantDoc şu kararların hiçbirinde kullanılamaz:

- model seçimi,
- epoch seçimi,
- learning rate seçimi,
- agent sayısı seçimi,
- kernel genişliği seçimi,
- checkpoint seçimi,
- preprocessing yöntemi seçimi,
- attention modelinin seçimi.

---

# 3. SINIF KESİŞİMİ

Aşağıdaki sınıflar başlangıçta aday sınıflardır:

```text
Tomato___Bacterial_spot
Tomato___Early_blight
Tomato___Late_blight
Tomato___Leaf_Mold
Tomato___Septoria_leaf_spot
Tomato___Spider_mites_Two-spotted_spider_mite
Tomato___Target_Spot
Tomato___Yellow_Leaf_Curl_Virus
Tomato___healthy
```

Ancak final sınıf uzayı klasör isimlerine körü körüne güvenilerek belirlenmez.

Phase 0'da:

```text
PlantVillage label
↔
PlantDoc label
↔
Canonical Tomato_Disease
```

eşlemesi oluşturulur.

Sadece semantik olarak güvenilir ortak sınıflar ana protokole alınır.

Son sınıf kümesi model sonuçlarına bakılmadan dondurulur.

---

# 4. FAZ 0 — PRATİK VERİ HAZIRLIĞI

Bu faz bilinçli olarak sade tutulur.

## 4.1 Manifest

Her görüntü için:

```text
image_id
dataset
relative_path
original_label
canonical_label
sha256
split
```

alanlarını içeren manifest oluşturulur.

---

## 4.2 Exact Duplicate Kontrolü

SHA-256 ile yalnızca tam kopyalar kontrol edilir:

```text
PlantVillage içinde
PlantDoc içinde
PlantVillage ↔ PlantDoc
```

Tam kopyalar raporlanır ve gerekiyorsa evaluation leakage yaratmayacak şekilde dışlanır.

Near-duplicate taraması ana tez kapsamına alınmaz.

---

## 4.3 Dosya Geçerlilik Kontrolü

Otomatik olarak yalnızca şu kontroller yapılır:

- dosya açılabiliyor mu?
- RGB'ye dönüştürülebiliyor mu?
- boyut sıfır mı?
- görüntü bozuk mu?

Manuel geniş veri temizliği yapılmaz.

PlantDoc'taki zor veya sıra dışı örnekler ana test kümesinde korunur.

Bu karar gerçek saha zorluğunu yapay biçimde azaltmamak içindir.

---

## 4.4 RAW ve LEAF-ISOLATED Veri

İki görüntü biçimi oluşturulur:

```text
RAW
LEAF-ISOLATED
```

Leaf isolation için önceden eğitilmiş bir segmentasyon yöntemi kullanılır.

Tercih:

```text
SAM tabanlı otomatik leaf mask
```

Maskeler otomatik üretilir.

Elle maske düzeltmesi zorunlu değildir.

Başarısız segmentasyon örnekleri ayrıca not edilebilir ancak manuel yeniden çizim ana protokolün parçası değildir.

---

# 5. ÇEKİRDEK MODEL SETİ

Deneyler aşağıdaki sınırlı model seti etrafında yürütülür.

| ID | Model | Rol |
|---|---|---|
| A | EfficientNet-B0 | Klasik CNN referansı |
| B1 | Frozen DINOv2 + CLS Linear | Foundation baseline |
| B2 | Frozen DINOv2 + GAP Linear | Güçlü basit token baseline |
| B3 | Frozen DINOv2 + Single-Query Attention | Learned pooling baseline |
| B4 | Frozen DINOv2 + Vanilla Multi-Agent Attention | Multi-agent hipotezi |
| B5 | Frozen DINOv2 + Kernel-Guided Multi-Agent Attention | Ana uzamsal hipotez |

Ana backbone:

```text
DINOv2 ViT-B/14
```

Backbone tamamen frozen kalır.

DINOv2 feature extraction yalnızca bir kez yapılır ve cache edilir.

---

# 6. FAZ 1 — ANCHOR BASELINES

İlk olarak yalnızca RAW görüntüler kullanılır.

Çalıştır:

```text
A  EfficientNet-B0
B1 DINOv2 CLS
B2 DINOv2 GAP
```

Amaç:

1. Lab-to-field gap'i doğrulamak.
2. Frozen representation avantajı olup olmadığını görmek.
3. Deney protokolünün doğru çalıştığını doğrulamak.

Bu faz tamamlanmadan Agent Attention deneylerine geçilmez.

---

# 7. FAZ 2 — BASİT TOKEN TOPLAMA

Frozen DINOv2 patch token'ları kullanılır.

Karşılaştır:

```text
B1 CLS Linear
B2 GAP Linear
B3 Single-Query Attention Pooling
```

Amaç:

> Learned attention, yalnızca global averaging'e göre gerçekten avantaj sağlıyor mu?

Bu baseline, multi-agent mekanizmasının gerekliliğini test etmek için zorunludur.

---

# 8. FAZ 3 — VANILLA MULTI-AGENT ATTENTION

Frozen patch token'ları üzerinde N adet learnable query/agent kullanılır.

Primary configuration:

```text
N = 4
```

Agent sayısının geniş taraması yapılmaz.

Yalnızca aşağıdaki durumda ek sensitivity deneyi yapılabilir:

```text
N = 8
```

Koşul:

- N=4 modeli belirgin agent collapse gösteriyorsa,
- veya N=4 umut verici sonuç verip agent sayısına duyarlılık kontrol edilmek isteniyorsa.

Ana karşılaştırma:

```text
Single-Query Attention
vs.
4-Agent Attention
```

Bu deney şu soruyu cevaplar:

> Kazanç yalnızca learned attention'dan mı geliyor, yoksa birden fazla query kullanmak gerçekten ek değer sağlıyor mu?

---

# 9. FAZ 4 — KERNEL-GUIDED AGENT ATTENTION

Kernel guidance sabit görüntü koordinatlarına bağlanmaz.

Amaç ajanları “sol üst”, “sağ alt” gibi sabit bölgelere kilitlemek değildir.

Hipotez:

> Farklı ajanlar farklı uzamsal ölçeklerde yoğunlaşmayı öğrenirse küçük ve büyük hastalık örüntülerini daha iyi temsil edebilir.

Önerilen kavramsal mekanizma:

```text
Patch Tokens
    ↓
Initial Content Attention
    ↓
Agent-Specific Soft Spatial Center
    ↓
Scale-Dependent Gaussian / Radial Bias
    ↓
Refined Attention
```

Örnek 4-agent yapı:

```text
Agent 1 → small locality
Agent 2 → medium locality
Agent 3 → large locality
Agent 4 → weak/global locality
```

Ana karşılaştırma:

```text
B4 Vanilla Multi-Agent
vs.
B5 Kernel-Guided Multi-Agent
```

İlk tez sürümünde ayrı diversity-loss deneyleri zorunlu değildir.

Agent collapse ciddi bir problem olarak gözlenirse diversity regularization yalnızca takip deneyi olarak eklenebilir.

---

# 10. FAZ 5 — RAW vs LEAF-ISOLATED

Combinatorial explosion önlemek için tüm modeller RAW ve LEAF üzerinde tekrar edilmez.

Ana background analizi yalnızca üç temsil noktasıyla yapılır:

```text
A  EfficientNet-B0
B2 DINOv2 GAP
B5 Kernel-Guided Agent
```

Koşullar:

```text
RAW
LEAF-ISOLATED
```

Toplam:

```text
3 model × 2 input condition
```

Bu deney şu üç seviyeyi temsil eder:

```text
task-specialized CNN
simple frozen foundation representation
proposed spatial aggregation
```

Eğer B5 ana deneylerde başarısız veya teknik olarak geçersiz çıkarsa, background analizinde B4 Vanilla Agent kullanılabilir.

---

# 11. UZAMSAL ODAK ANALİZİ

Manuel lesion bounding-box veya pixel-level annotation zorunlu değildir.

LEAF-ISOLATED pipeline tarafından üretilen leaf mask foreground referansı olarak kullanılır.

Attention map bulunan modeller için:

## 11.1 Leaf Attention Mass

```text
attention mass inside leaf mask
/
total attention mass
```

## 11.2 Background Attention Mass

```text
attention mass outside leaf mask
/
total attention mass
```

## 11.3 Border Activation Ratio

Görüntünün dış %20'lik sınır bölgesinde bulunan attention oranı.

## 11.4 Attention Entropy

Attention'ın ne kadar dağınık veya yoğun olduğunu ölçer.

Bu metrikler:

```text
lesion localization
```

olarak adlandırılmaz.

Doğru terminoloji:

```text
foreground focus
background reliance
spatial concentration
```

---

# 12. HESAPLAMA STRATEJİSİ

## Lokal — Apple Silicon M2

Kullan:

- manifest üretimi,
- SHA-256 hesaplama,
- split üretimi,
- cached feature üzerinde probe eğitimi,
- Agent Attention head eğitimi,
- metrik hesaplama,
- grafik ve tablo üretimi.

## GPU — Google Colab / Kaggle

Kullan:

- DINOv2 feature extraction,
- patch-token caching,
- SAM leaf-mask inference,
- EfficientNet training gerekiyorsa GPU training.

---

# 13. FEATURE CACHING

DINOv2 frozen olduğu için feature extraction her seed için tekrar edilmez.

Önerilen dosyalar:

```text
artifacts/features/raw_cls.pt
artifacts/features/raw_patch_tokens.pt

artifacts/features/leaf_cls.pt
artifacts/features/leaf_patch_tokens.pt
```

Her kayıt `image_id` ile ilişkilendirilir.

Patch token cache spatial grid bilgisini korumalıdır.

---

# 14. SEED POLİTİKASI

Ana deneylerde:

```text
42
0
1
```

kullanılır.

Rapor:

```text
mean ± standard deviation
```

şeklinde yapılır.

En iyi seed headline sonuç olarak kullanılmaz.

---

# 15. İSTATİSTİKSEL RAPORLAMA

Ana metrikler:

```text
Macro-F1
Balanced Accuracy
Top-1 Accuracy
Per-Class Recall
```

Ana karşılaştırmalarda mümkün olduğunda:

```text
paired bootstrap 95% confidence interval
```

hesaplanır.

Özellikle:

```text
DINO GAP − EfficientNet
Single Attention − GAP
Multi-Agent − Single Attention
Kernel Agent − Vanilla Agent
LEAF − RAW
```

farkları için bootstrap CI raporlanabilir.

Karmaşık istatistik testi ailesi zorunlu değildir.

---

# 16. ANA DENEY MATRİSİ

## Bölüm A — RAW Core Benchmark

| Model | RAW | 3 Seed |
|---|---:|---:|
| EfficientNet-B0 | ✓ | ✓ |
| DINO CLS | ✓ | ✓ |
| DINO GAP | ✓ | ✓ |
| Single-Query Attention | ✓ | ✓ |
| Vanilla Multi-Agent | ✓ | ✓ |
| Kernel-Guided Agent | ✓ | ✓ |

Toplam:

```text
6 × 3 = 18 run
```

DINO backbone inference tekrar edilmez.

---

## Bölüm B — Background Study

| Model | RAW | LEAF | 3 Seed |
|---|---:|---:|---:|
| EfficientNet-B0 | ✓ | ✓ | ✓ |
| DINO GAP | ✓ | ✓ | ✓ |
| Kernel Agent* | ✓ | ✓ | ✓ |

`*` Kernel Agent teknik olarak başarısızsa Vanilla Agent kullanılır.

RAW sonuçlar Bölüm A'dan tekrar kullanılır.

Yeni LEAF run sayısı:

```text
3 × 3 = 9
```

Yaklaşık toplam train/evaluation run:

```text
27
```

Bu tez için yönetilebilir ana deney bütçesidir.

---

# 17. SONUÇ DOSYALARI

Her run:

```text
results/<experiment>/seed_<seed>.json
```

oluşturur.

Asgari alanlar:

```text
experiment
seed
model
input_condition
trainable_parameters
source_val_macro_f1
source_test_macro_f1
target_macro_f1
target_balanced_accuracy
target_accuracy
per_class_recall
```

Ayrıca:

```text
results/<experiment>/seed_<seed>_predictions.csv
```

oluşturulur.

Bu dosya:

```text
image_id
ground_truth
prediction
confidence
correct
```

alanlarını içermelidir.

Attention modellerinde ek olarak:

```text
leaf_attention_mass
background_attention_mass
border_activation_ratio
attention_entropy
```

saklanabilir.

---

# 18. HATA ANALİZİ

Sadece en önemli modeller için yapılır:

```text
EfficientNet
DINO GAP
Vanilla Agent
Kernel Agent
```

İncelenecekler:

- en çok karışan sınıflar,
- yüksek güvenli yanlış tahminler,
- düşük güvenli yanlış tahminler,
- RAW→LEAF ile düzeltilen örnekler,
- RAW→LEAF ile bozulan örnekler,
- attention'ın background'a kaydığı örnekler.

Kapsamlı manuel veri etiketleme yapılmaz.

Ama tezde sınırlı sayıda örnek görsel nitel analiz için gösterilebilir.

---

# 19. ÇALIŞMA PLANI

| Aşama | Tahmini Süre | İş |
|---|---:|---|
| Hafta 1–2 | 2 hafta | Repo, dataset manifest, label mapping, SHA-256, split |
| Hafta 3 | 1 hafta | EfficientNet baseline |
| Hafta 4 | 1 hafta | DINOv2 RAW feature caching + CLS/GAP |
| Hafta 5 | 1 hafta | Single-Query Attention |
| Hafta 6–7 | 2 hafta | Vanilla Multi-Agent |
| Hafta 8–9 | 2 hafta | Kernel-Guided Agent |
| Hafta 10 | 1 hafta | SAM leaf masks + LEAF feature caching |
| Hafta 11 | 1 hafta | RAW vs LEAF experiments |
| Hafta 12 | 1 hafta | Spatial focus + error analysis |
| Hafta 13–16 | 3–4 hafta | Thesis writing, figures, tables, revision |

Toplam hedef:

```text
yaklaşık 3–4 ay
```

---

# 20. STOP RULES

Deneyler olumlu sonuç üretmek için sonsuza kadar genişletilmez.

Eğer:

```text
GAP ≈ Single Attention ≈ Multi-Agent
```

ise sonuç:

> Daha karmaşık patch aggregation mekanizmaları frozen DINOv2 üzerinde anlamlı ek saha genellemesi sağlamamaktadır.

Eğer:

```text
Vanilla Agent ≈ Kernel Agent
```

ise sonuç:

> Ek uzamsal kernel prior bu deney düzeninde anlamlı katkı sağlamamıştır.

Eğer:

```text
Kernel Agent < Vanilla Agent
```

ise negatif sonuç aynen raporlanır.

Yeni modüller yalnızca açık bir failure mode'u test etmek için eklenir.

---

# 21. BAŞARI KRİTERLERİ

Kernel-Guided Agent yaklaşımı ancak aşağıdaki bulguların bir kısmını tutarlı biçimde gösterirse desteklenmiş kabul edilir:

- PlantDoc Macro-F1 artışı,
- PlantDoc Balanced Accuracy artışı,
- üç seed'de tutarlı yön,
- paired bootstrap farkının anlamlı büyüklükte olması,
- vanilla agent'a göre daha güçlü leaf foreground focus,
- daha düşük background/border reliance.

Tek bir seed veya tek bir metrik yeterli değildir.

---

# 22. TEZİN OLASI SONUÇ SENARYOLARI

## Senaryo A

```text
DINO > CNN
Kernel Agent > GAP
LEAF > RAW
Kernel Agent foreground'a daha fazla odaklanıyor
```

Sonuç:

> Foundation representations, background suppression ve spatially guided aggregation birbirini tamamlayan katkılar sağlamaktadır.

---

## Senaryo B

```text
DINO > CNN
GAP ≈ Agent ≈ Kernel Agent
```

Sonuç:

> Ana kazanç aggregation complexity'den değil pretrained representation kalitesinden gelmektedir.

Bu güçlü bir negatif sonuçtur.

---

## Senaryo C

```text
EfficientNet LEAF >> EfficientNet RAW
DINO LEAF ≈ DINO RAW
```

Sonuç:

> Background shortcut etkisi conventional CNN'de daha güçlü, frozen foundation representation'da daha sınırlıdır.

---

## Senaryo D

```text
LEAF < RAW
```

Sonuç:

> Context removal yararlı saha bilgisini de ortadan kaldırıyor olabilir; background her zaman yalnızca zararlı bir shortcut değildir.

---

## Senaryo E

```text
Kernel Agent classification ↑
foreground focus ≈
```

Sonuç:

> Performans kazancı daha iyi foreground localization ile açıklanamamaktadır.

---

# 23. TEZİN ANA KATKILARI

Çalışma sonunda hedeflenen katkılar:

### Contribution 1 — Tomato-only Lab-to-Field Benchmark

PlantVillage → PlantDoc üzerinde aynı ürün içindeki hastalık genellemesine odaklanan temiz ve reproducible bir protokol.

### Contribution 2 — Representation Comparison

EfficientNet-B0 ile frozen DINOv2'nin strict source-only saha genellemesinin kontrollü karşılaştırması.

### Contribution 3 — Background Shortcut Study

RAW ve otomatik LEAF-ISOLATED görüntüler altında representation × background davranışının incelenmesi.

### Contribution 4 — Spatial Aggregation Ladder

CLS → GAP → Single Attention → Multi-Agent → Kernel-Guided Agent sıralamasında artan mimari karmaşıklığın gerçekten gerekli olup olmadığının test edilmesi.

### Contribution 5 — Spatial Focus Analysis

Manuel lesion annotation gerektirmeden, leaf foreground mask üzerinden attention'ın background reliance davranışının kantitatif olarak incelenmesi.

---

# 24. BİLİMSEL KURALLAR

1. PlantDoc ana source-only protokolde model seçiminde kullanılmaz.
2. Negatif sonuç gizlenmez.
3. En iyi seed seçilerek headline sonuç üretilmez.
4. RAW→LEAF farkı nedensel “domain gap yüzdesi” olarak yorumlanmaz.
5. SAM maskeleri lesion ground truth değildir.
6. Attention heatmap'leri otomatik olarak açıklama kabul edilmez.
7. Karmaşık yöntemler basit ve güçlü baseline'larla karşılaştırılır.
8. Agent sayısı ve kernel ayarları PlantDoc'a bakılarak optimize edilmez.
9. Sonuç tabloları result dosyalarından programatik üretilir.
10. Bilimsel açıklık, tek bir yüksek accuracy skorundan daha önemlidir.

---

# 25. FINAL THESIS STORY

Tezin sonunda ideal anlatı şu yapıda olmalıdır:

```text
1. Tomato disease classification controlled data üzerinde güçlüdür fakat field transferinde ciddi ölçüde bozulur.

2. Frozen DINOv2 bu gap altında conventional CNN'den daha güçlü veya farklı bir davranış gösterir.

3. Background removal bu iki representation ailesini aynı şekilde etkilemez.

4. Patch-token aggregation için güçlü basit baseline GAP'tir.

5. Single-query attention, multi-agent attention'ın gerçekten gerekli olup olmadığını ayırır.

6. Kernel-guided attention spatial prior'ın gerçekten ek katkı sağlayıp sağlamadığını test eder.

7. Foreground-focus analizi sınıflandırma kazançlarının background reliance değişimi ile ilişkili olup olmadığını gösterir.

8. Sonuç ister pozitif ister negatif olsun, tez lab-to-field robustness hakkında kontrollü ve tekrarlanabilir bir açıklama üretir.
```

---

# 26. SON KURAL

Bir deneyin eklenmesi için şu soruya net cevap verilmelidir:

> “Bu deney mevcut araştırma sorularından hangisini cevaplıyor?”

Net bir cevap yoksa deney yapılmaz.

Bir yöntem yalnızca “belki skoru artırır” diye eklenmez.

Tezin gücü deney sayısından değil:

```text
net hipotez
+
adil baseline
+
strict source-only değerlendirme
+
kontrollü karşılaştırma
+
dürüst negatif sonuç
```

kombinasyonundan gelecektir.
