"""Finalize audit metadata from existing manifests, without modifying images."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manifests"


def read(name):
    with (OUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write(name, rows, fields=None):
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    summary = json.loads((OUT / "audit_summary.json").read_text())
    assert summary["protocol_sha256"] == hashlib.sha256((ROOT / "MASTER_RESEARCH_PROTOCOL.md").read_bytes()).hexdigest(), "Protocol changed; re-audit first"
    datasets = {d: read(f"tomato_{d}_manifest.csv") for d in ("plantvillage", "plantdoc")}
    counts = {d: Counter(r["original_label"] for r in rows) for d, rows in datasets.items()}
    inventory = {(r["dataset"], r["original_label"]): int(r["image_count"]) for r in read("class_inventory.csv")}
    assert inventory == {(d, label): n for d, c in counts.items() for label, n in c.items()}
    hashes = defaultdict(list)
    for rows in datasets.values():
        for row in rows:
            hashes[row["sha256"]].append(row)
    groups = {h: rows for h, rows in hashes.items() if len(rows) > 1}
    assert set(groups) == {r["sha256"] for r in read("exact_duplicates.csv")}
    assert len(groups) == summary["duplicate_groups"]
    group_summary, duplicate_rows = [], []
    for h, members in sorted(groups.items()):
        gid = "dup_sha256_" + h
        ds = sorted({r["dataset"] for r in members})
        labels = sorted({r["original_label"] for r in members})
        group_summary.append({"duplicate_group_id": gid, "sha256": h, "group_size": len(members),
                              "datasets": "|".join(ds), "original_labels": "|".join(labels),
                              "cross_dataset": len(ds) > 1, "label_conflict": len(labels) > 1})
        for r in members:
            duplicate_rows.append({"duplicate_group_id": gid, "sha256": h, "group_size": len(members),
                                   "cross_dataset": len(ds) > 1, "dataset": r["dataset"],
                                   "original_label": r["original_label"], "image_id": r["image_id"],
                                   "relative_path": r["relative_path"]})
    for d, rows in datasets.items():
        for r in rows:
            r["duplicate_group_id"] = "dup_sha256_" + r["sha256"] if r["sha256"] in groups else ""
        write(f"tomato_{d}_manifest.csv", rows)
    write("exact_duplicates.csv", duplicate_rows)
    write("duplicate_group_summary.csv", group_summary)
    mappings = read("candidate_label_mapping.csv")
    core, conditional = [], []
    for m in mappings:
        m["plantvillage_image_count"] = counts["plantvillage"].get(m["plantvillage_label"], 0)
        m["plantdoc_image_count"] = counts["plantdoc"].get(m["plantdoc_label"], 0)
        label = m["plantvillage_label"]
        if not m["plantdoc_label"]:
            recommendation = "not_shared"
        elif label in ("tomato_leaf_yellow_virus", "tomato_leaf_healthy"):
            recommendation = "conditional_semantic_verification"
            conditional.append(m["candidate_canonical_label"])
        elif label == "tomato_leaf_mosaic_virus":
            recommendation = "conditional_protocol_extension"
            conditional.append(m["candidate_canonical_label"])
        else:
            recommendation = "proposed_core"
            core.append(m["candidate_canonical_label"])
        m["recommendation"] = recommendation
        m["status"] = "pending_user_approval"
    write("candidate_label_mapping.csv", mappings)
    class_summary = [{"original_label": label, "plantvillage_image_count": counts["plantvillage"].get(label, 0),
                      "plantdoc_image_count": counts["plantdoc"].get(label, 0)}
                     for label in sorted(set(counts["plantvillage"]) | set(counts["plantdoc"]))]
    write("class_counts_summary.csv", class_summary)
    final = {"date": "2026-10-05", "status": "audit_finalized_pending_class_approval",
             "canonical_class_set_frozen": False, "splits_created": False,
             "duplicate_group_id_rule": "dup_sha256_<full content sha256>; blank for singleton",
             "duplicate_groups": len(groups),
             "within_dataset_duplicate_groups": {d: sum(sum(r["dataset"] == d for r in members) > 1 for members in groups.values()) for d in datasets},
             "cross_dataset_duplicate_groups": sum(len({r["dataset"] for r in members}) > 1 for members in groups.values()),
             "label_conflict_groups": sum(g["label_conflict"] for g in group_summary),
             "proposed_core_intersection": core, "conditional_additions": conditional}
    (OUT / "phase_0_finalization_summary.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = ["# Phase 0 finalization", "", "Tarih: 2026-10-05. Bilimsel sözleşme: `MASTER_RESEARCH_PROTOCOL.md`.", "",
              "İstenen veri denetimi ve metadata finalizasyonu tamamlandı. Canonical sınıf kümesi kullanıcı onayı bekliyor ve dondurulmadı. Bu rapor, protokoldeki ileride yapılacak split ve leaf-isolation adımlarının tamamlandığını ifade etmez. PlantDoc dış hedef test kümesi olarak korunur.", "",
              "## Birleştirilmiş sınıf sayımları", "",
              "Sayım kaynağı mevcut görüntü manifestleridir; kopyalar dahil tüm dosyalar korunur. Sıfır, ilgili sınıfın diğer veri setinde bulunmadığını gösterir.", "",
              "| Mevcut sınıf klasörü | PlantVillage | PlantDoc |", "|---|---:|---:|"]
    for r in class_summary:
        report.append(f"| {r['original_label']} | {r['plantvillage_image_count']} | {r['plantdoc_image_count']} |")
    report += [f"| **Toplam görüntü** | **{sum(counts['plantvillage'].values())}** | **{sum(counts['plantdoc'].values())}** |",
               f"| **Sınıf klasörü sayısı** | **{len(counts['plantvillage'])}** | **{len(counts['plantdoc'])}** |", "",
               "## Canonical mapping önerileri", "",
               "Processed klasör adları etiket kaynağıdır; görüntü bazında hastalık doğrulaması yapılmadı. Tüm öneriler kullanıcı onayı bekler.", "",
               "| PlantVillage label | PlantDoc label | Canonical öneri | PV görüntü | PD görüntü | Öneri durumu |",
               "|---|---|---|---:|---:|---|"]
    for m in mappings:
        report.append(f"| {m['plantvillage_label']} | {m['plantdoc_label'] or '—'} | {m['candidate_canonical_label']} | {m['plantvillage_image_count']} | {m['plantdoc_image_count']} | {m['recommendation']} |")
    report += ["", "`proposed_core`: protokolde aday olan ve mevcut adları tutarlı görünen ortak sınıf önerisi. `conditional_semantic_verification`: healthy ve yellow virus kaynak anlamı doğrulanmalı. PlantDoc statistics.txt içinde healthy için özgün ad `Tomato leaf`; yellow virus için `Tomato leaf yellow virus` yazıyor. Bu adlar tek başına healthy/TYLCV anlamını kesinleştirmez. `conditional_protocol_extension`: mosaic virus iki sette de var, ancak protokol bölüm 3 aday listesinde yok; ekleme kararı ayrıca onaylanmalı.", "",
               "## Ortak olmayan sınıflar ve belirsizlikler", "",
               "`Tomato___Target_Spot`: PlantVillage 1404, PlantDoc 0; hedef karşılığı yoktur ve önerilen kesişime alınmaz. PlantDoc'a özgü ek sınıf yoktur. Healthy ve yellow virus kesin olarak ortak olmayan sınıflar diye ilan edilmez; semantik eşleşmeleri henüz doğrulanmamıştır. Mosaic virus ortak adaydır; yokluk değil protokol kapsam kararı bekler. Hiçbir dosya/sınıf silinmedi, birleştirilmedi veya yeniden adlandırılmadı.", "",
               "PlantDoc spider mites sınıfı yalnızca 2 görüntü içerir. Düşük sayı raporlandı; sınıf otomatik dışlanmadı ve bu sayı model sonuçlarına dayalı bir seçim gerekçesi olarak kullanılmadı.", "",
               "## Exact duplicate grupları", "",
               "| Kapsam | Grup | Gruba dahil görüntü |", "|---|---:|---:|"]
    for d in datasets:
        report.append(f"| {d} içi | {final['within_dataset_duplicate_groups'][d]} | {sum(r['sha256'] in groups for r in datasets[d])} |")
    report += [f"| Veri setleri arası | {final['cross_dataset_duplicate_groups']} | 0 |",
               f"| Toplam | {len(groups)} | {sum(len(m) for m in groups.values())} |", "",
               "`duplicate_group_id = dup_sha256_<tam 64 karakter içerik SHA-256>`; aynı hash aynı kimliği alır, sıra/yol/veri seti değişikliklerinden etkilenmez. Yalnızca en az iki görüntülü hash gruplarına atanır; tekil görüntülerde alan boştur. Her iki manifest ve exact_duplicates.csv güncellendi. duplicate_group_summary.csv grup başına tek satır içerir.", "",
               "**Etiket çelişkisi:** PlantDoc `test_tomato_V8.jpg` bacterial spot ve `train_tomato_V8.jpg` Septoria aynı SHA-256 içeriktir (`dup_sha256_e23a29c94b58aac28e92f57f95eb6f53e99c874323cb2b90ebd327085721574e`). Etiket düzeltmesi veya dışlama yapılmadı; değerlendirme öncesi ayrı karar gerekir. Dosya adındaki train/test önekleri mevcut dosya adlarıdır, bu çalışmada split ataması değildir. Gelecekte source split oluşturulurken aynı duplicate grubu farklı splitlere dağıtılmamalıdır.", "",
               "## Doğrulama ve yeniden üretim", "",
               "Manifest sayımları class_inventory.csv ve audit_summary.json ile karşılaştırıldı; grup kimlikleri mevcut SHA-256 gruplarından üretildi. İlk audit'in dosya geçerlilik sonucu 0 hatadır; bu aşamada görüntüler yeniden decode edilmedi. canonical_label ve split alanları boş bırakıldı; mevcut image_id, dataset, relative_path, original_label, sha256 alanları korundu. Training, feature extraction, segmentasyon veya başka model kodu yazılmadı.", "",
               "Yeni çıktılar: manifests/class_counts_summary.csv, manifests/duplicate_group_summary.csv, manifests/phase_0_finalization_summary.json. Güncellenenler: iki görüntü manifesti, exact_duplicates.csv, candidate_label_mapping.csv. Yeniden üretim: `python3 scripts/phase_0_finalize.py`. İlk audit yeniden çalıştırılırsa ardından finalizer çalıştırılmalıdır.", "",
               "## Önerilen final canonical class intersection — kullanıcı onayı bekliyor", "",
               "Mevcut yerel kanıtla muhafazakâr ana öneri aşağıdaki 6 sınıftır; bu bir freeze değildir:", "", "```text", *core, "```", "",
               "Healthy ve Yellow Leaf Curl Virus semantik kaynak doğrulamasından sonra; Tomato mosaic virus ise protokol aday listesini genişletme onayından sonra eklenebilir. Böylece genişletilmiş öneri 9 sınıfa ulaşır. Bu üç sınıf veriden çıkarılmadı. Kullanıcı onayı alınmadan hiçbir canonical sınıf manifestlere uygulanmayacak veya dondurulmayacaktır."]
    (ROOT / "docs/checkpoints/phase_0_finalization.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
