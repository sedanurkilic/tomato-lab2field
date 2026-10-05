"""Read-only dataset audit; writes metadata only. Requires Pillow for validation."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manifests"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
LABELS = {
    "tomato_leaf_bacterial_spot": "Tomato___Bacterial_spot",
    "tomato_leaf_early_blight": "Tomato___Early_blight",
    "tomato_leaf_late_blight": "Tomato___Late_blight",
    "tomato_leaf_mold": "Tomato___Leaf_Mold",
    "tomato_septoria_leaf_spot": "Tomato___Septoria_leaf_spot",
    "tomato_leaf_two_spotted_spider_mites": "Tomato___Spider_mites_Two-spotted_spider_mite",
    "tomato_target_spot": "Tomato___Target_Spot",
    "tomato_leaf_yellow_virus": "Tomato___Yellow_Leaf_Curl_Virus",
    "tomato_leaf_mosaic_virus": "Tomato___Tomato_mosaic_virus",
    "tomato_leaf_healthy": "Tomato___healthy",
}


def write_csv(name, fields, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    manifests, counts, ignored, invalid = [], [], [], []
    classes = {}
    for dataset in ("plantvillage", "plantdoc"):
        base = ROOT / "data" / "processed" / f"tomato_{dataset}"
        if not base.is_dir():
            raise FileNotFoundError(base)
        classes[dataset] = sorted(p.name for p in base.iterdir() if p.is_dir())
        rows = []
        class_ext = defaultdict(Counter)
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT).as_posix()
            if path.suffix.lower() not in EXTENSIONS:
                ignored.append({"dataset": dataset, "relative_path": relative, "extension": path.suffix})
                continue
            parts = path.relative_to(base).parts
            label = parts[0] if len(parts) > 1 else "__unlabeled__"
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            row = {"image_id": dataset + "_" + hashlib.sha256(relative.encode()).hexdigest(),
                   "dataset": dataset, "relative_path": relative,
                   "original_label": label, "sha256": digest.hexdigest(),
                   "canonical_label": "", "split": ""}
            rows.append(row)
            class_ext[label][path.suffix] += 1
            try:
                with Image.open(path) as im:
                    im.verify()
                with Image.open(path) as im:
                    if min(im.size) <= 0:
                        raise ValueError("zero dimension")
                    im.convert("RGB").load()
            except Exception as exc:
                invalid.append({"image_id": row["image_id"], "relative_path": relative,
                                "error": f"{type(exc).__name__}: {exc}"})
        for label in sorted(set(classes[dataset]) | set(class_ext)):
            counts.append({"dataset": dataset, "original_label": label,
                           "image_count": sum(class_ext[label].values()),
                           "extensions": json.dumps(dict(sorted(class_ext[label].items())))})
        write_csv(f"tomato_{dataset}_manifest.csv", list(rows[0]) if rows else
                  ["image_id", "dataset", "relative_path", "original_label", "sha256", "canonical_label", "split"], rows)
        manifests.extend(rows)
    mappings = []
    for label in sorted(set(classes["plantvillage"]) | set(classes["plantdoc"])):
        notes = "Klasör adlarından aday eşleşme; final sınıf onayı değildir."
        if label == "tomato_leaf_yellow_virus":
            notes = "PlantDoc yellow virus etiketi TYLCV olduğunu tek başına kanıtlamaz; kaynak etiketi doğrulanmalı."
        elif label == "tomato_leaf_healthy":
            notes = "PlantDoc statistics.txt özgün etiketi Tomato leaf; healthy anlamı doğrulanmalı."
        elif label == "tomato_leaf_mosaic_virus":
            notes = "İki sette mevcut; protokol bölüm 3 başlangıç aday listesinde yok. Dahil etme kararı bekliyor."
        elif label == "tomato_target_spot":
            notes = "PlantDoc karşılığı yok; ortak sınıf adayı değil."
        mappings.append({"plantvillage_label": label if label in classes["plantvillage"] else "",
                         "plantdoc_label": label if label in classes["plantdoc"] else "",
                         "candidate_canonical_label": LABELS.get(label, ""),
                         "status": "pending_review", "notes": notes})
    write_csv("candidate_label_mapping.csv", list(mappings[0]), mappings)
    write_csv("class_inventory.csv", ["dataset", "original_label", "image_count", "extensions"], counts)
    write_csv("non_image_files.csv", ["dataset", "relative_path", "extension"], ignored)
    write_csv("invalid_images.csv", ["image_id", "relative_path", "error"], invalid)
    hashes = defaultdict(list)
    for row in manifests:
        hashes[row["sha256"]].append(row)
    duplicates = []
    for digest, members in sorted(hashes.items()):
        if len(members) > 1:
            for row in members:
                duplicates.append({"sha256": digest, "group_size": len(members),
                                   "cross_dataset": len({m["dataset"] for m in members}) > 1,
                                   "dataset": row["dataset"], "original_label": row["original_label"],
                                   "image_id": row["image_id"], "relative_path": row["relative_path"]})
    write_csv("exact_duplicates.csv", ["sha256", "group_size", "cross_dataset", "dataset", "original_label", "image_id", "relative_path"], duplicates)
    summary = {"audit_date": "2026-10-05", "protocol_sha256": hashlib.sha256((ROOT / "MASTER_RESEARCH_PROTOCOL.md").read_bytes()).hexdigest(),
               "datasets": {d: {"class_count": len(classes[d]), "image_count": sum(r["dataset"] == d for r in manifests),
                                 "extensions": dict(sorted(Counter(Path(r["relative_path"]).suffix for r in manifests if r["dataset"] == d).items())),
                                 "within_dataset_duplicate_groups": sum(sum(m["dataset"] == d for m in members) > 1 for members in hashes.values())} for d in classes},
               "invalid_image_count": len(invalid), "non_image_file_count": len(ignored),
               "duplicate_groups": sum(len(m) > 1 for m in hashes.values()),
               "cross_dataset_duplicate_groups": sum(len({r["dataset"] for r in m}) > 1 for m in hashes.values())}
    (OUT / "audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    report = ["# Faz 0 — İlk veri denetimi", "", "Tarih: 2026-10-05. Bilimsel sözleşme: `MASTER_RESEARCH_PROTOCOL.md` (SHA-256 `" + summary["protocol_sha256"] + "`).", "",
              "PlantDoc dış hedef test kümesidir; model/preprocessing seçimi için kullanılmaz. Bu çalışma yalnızca envanter, hash, dosya geçerliliği ve aday etiket eşleşmesi üretir.", "",
              "| Veri seti | Sınıf klasörü | Görüntü | Uzantılar (büyük/küçük harf korunur) |", "|---|---:|---:|---|"]
    for d, s in summary["datasets"].items():
        report.append(f"| {d} | {s['class_count']} | {s['image_count']} | {s['extensions']} |")
    report += ["", "| Veri seti | Sınıf klasörü | Görüntü | Uzantılar |", "|---|---|---:|---|"]
    for r in counts:
        report.append(f"| {r['dataset']} | {r['original_label']} | {r['image_count']} | {r['extensions']} |")
    report += ["", "## Eşleşme durumu", "",
               "Dokuz klasör adı ortaktır; `tomato_target_spot` yalnızca PlantVillage'dadır. Tüm canonical eşleşmeler `candidate_label_mapping.csv` içinde inceleme bekleyen önerilerdir. Yellow virus → Yellow Leaf Curl Virus ve PlantDoc Tomato leaf → healthy anlamları kaynak etiketlerinden doğrulanmalıdır. Mosaic virus her iki sette bulunur fakat protokolün başlangıç aday listesinde yoktur. Spider mites PlantDoc örnek sayısı ayrıca dikkate alınmalıdır. Final sınıf kümesi dondurulmadı.", "",
               "## Bütünlük ve çıktı sözleşmesi", "",
               f"Geçersiz görüntü: {len(invalid)}. Tam kopya hash grubu: {summary['duplicate_groups']}; veri setleri arası: {summary['cross_dataset_duplicate_groups']}. Veri seti içi grup sayıları audit_summary.json içindedir. Kopyalar raporlandı, dışlanmadı. Near-duplicate taraması yapılmadı.", "",
               "Manifestler her tanınan görüntü dosyasını (geçersizler dahil) içerir. `original_label` mevcut processed sınıf klasörüdür; upstream özgün etiket iddiası değildir. `relative_path` proje köküne göredir. `image_id`, dataset öneki + relative_path UTF-8 SHA-256 ile deterministik ve yol bazlıdır; dosya içeriği SHA-256 ayrı tutulur. Protokoldeki `canonical_label` ve `split` alanları karar verilmediği için boş bırakıldı.", "",
               "Sayım uzantı bazlıdır (.jpg/.jpeg/.png/.bmp/.gif/.tif/.tiff/.webp, harf duyarsız tanıma); Pillow verify, pozitif boyut ve tam RGB decode kontrolü uygulandı. Diğer dosyalar non_image_files.csv içinde listelenir. statistics.txt sayımları doğrudan kabul edilmedi.", "",
               "Çıktılar `manifests/`: tomato_plantvillage_manifest.csv, tomato_plantdoc_manifest.csv, class_inventory.csv, candidate_label_mapping.csv, audit_summary.json, exact_duplicates.csv, invalid_images.csv, non_image_files.csv. Yeniden üretim: `python3 scripts/phase_0_initial_audit.py` (Pillow gerekir).", "",
               "Hiçbir sınıf veya görüntü silinmedi, yeniden adlandırılmadı veya birleştirilmedi. Split, training, DINOv2 feature extraction, SAM ve başka model kodu/inference üretilmedi. Bu ilk denetim, sonraki tüm Faz 0 adımlarının tamamlandığı anlamına gelmez."]
    checkpoint = ROOT / "docs" / "checkpoints"
    checkpoint.mkdir(parents=True, exist_ok=True)
    (checkpoint / "phase_0_initial_audit.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
