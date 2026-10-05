"""Create the user-approved primary benchmark metadata; never writes images."""
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manifests"
SEED = 42
MAPPING = {
    "tomato_leaf_bacterial_spot": "Tomato___Bacterial_spot",
    "tomato_leaf_early_blight": "Tomato___Early_blight",
    "tomato_leaf_late_blight": "Tomato___Late_blight",
    "tomato_leaf_mold": "Tomato___Leaf_Mold",
    "tomato_septoria_leaf_spot": "Tomato___Septoria_leaf_spot",
    "tomato_leaf_mosaic_virus": "Tomato___Tomato_mosaic_virus",
}
SPLITS = ("train", "validation", "test")


def read(name):
    with (OUT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def quotas(n):
    # Largest remainder, with train/validation/test ordering for ties.
    numerators = [n * p for p in (70, 15, 15)]
    result = [v // 100 for v in numerators]
    order = sorted(range(3), key=lambda i: (-(numerators[i] % 100), i))
    for i in order[:n - sum(result)]:
        result[i] += 1
    return dict(zip(SPLITS, result))


def main():
    all_rows = {d: read(f"tomato_{d}_manifest.csv") for d in ("plantvillage", "plantdoc")}
    conflicts = {r["duplicate_group_id"] for r in read("duplicate_group_summary.csv")
                 if r["label_conflict"] == "True" and "plantdoc" in r["datasets"].split("|")}
    rows = []
    for d, records in all_rows.items():
        for original in records:
            r = dict(original)
            r["canonical_label"] = MAPPING.get(r["original_label"], "")
            r["split"] = ""
            reason = "outside_primary_class_set" if not r["canonical_label"] else ""
            if d == "plantdoc" and r["duplicate_group_id"] in conflicts:
                reason = "label_conflict_duplicate_group"
            r["primary_included"] = not bool(reason)
            r["exclusion_reason"] = reason
            if d == "plantdoc" and r["primary_included"]:
                r["split"] = "external_target_test"
            rows.append(r)
    counts = []
    for label in MAPPING.values():
        selected = [r for r in rows if r["dataset"] == "plantvillage" and r["canonical_label"] == label]
        groups = defaultdict(list)
        for r in selected:
            groups[r["duplicate_group_id"] or r["image_id"]].append(r)
        rng = random.Random(f"{SEED}:{label}")
        ordered = sorted(groups.items())
        rng.shuffle(ordered)
        ordered.sort(key=lambda item: -len(item[1]))
        remaining = quotas(len(selected))
        target = dict(remaining)
        for gid, members in ordered:
            eligible = [s for s in SPLITS if remaining[s] >= len(members)]
            if not eligible:
                raise ValueError(f"Cannot satisfy exact quotas for {label} without splitting group {gid}")
            # Weighted choice among remaining capacities; larger groups allocated first.
            draw = rng.randrange(sum(remaining[s] for s in eligible))
            for s in eligible:
                if draw < remaining[s]:
                    chosen = s
                    break
                draw -= remaining[s]
            for r in members:
                r["split"] = chosen
            remaining[chosen] -= len(members)
        assert not any(remaining.values())
        pd = [r for r in rows if r["dataset"] == "plantdoc" and r["canonical_label"] == label]
        counts.append({"canonical_class": label, "PlantVillage_count": len(selected), **target,
                       "PlantDoc_count": len(pd), "PlantDoc_evaluation_count": sum(r["primary_included"] for r in pd)})
    pv = [r for r in rows if r["dataset"] == "plantvillage" and r["primary_included"]]
    pd = [r for r in rows if r["dataset"] == "plantdoc" and r["primary_included"]]
    group_splits, hash_splits = defaultdict(set), defaultdict(set)
    for r in pv:
        group_splits[r["duplicate_group_id"] or r["image_id"]].add(r["split"])
        hash_splits[r["sha256"]].add(r["split"])
    assert all(len(s) == 1 for s in group_splits.values())
    assert all(len(s) == 1 for s in hash_splits.values())
    assert not ({r["sha256"] for r in pv} & {r["sha256"] for r in pd})
    assert all(r["split"] == "external_target_test" for r in pd)
    assert not any(r["duplicate_group_id"] in conflicts for r in pd)
    config = {"frozen": True, "approved_by": "explicit_user_instruction", "date": "2026-10-06",
              "canonical_classes": list(MAPPING.values()), "original_to_canonical": MAPPING,
              "split_seed": SEED, "ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
              "rounding": "largest remainder per class; ties train, validation, test",
              "grouping": "duplicate_group_id or image_id; largest groups first",
              "plantdoc_role": "external_target_test", "excluded_target_duplicate_groups": sorted(conflicts),
              "source_manifest_sha256": {d: hashlib.sha256((OUT / f"tomato_{d}_manifest.csv").read_bytes()).hexdigest() for d in all_rows}}
    result = {"full_inventory_counts": {d: len(r) for d, r in all_rows.items()},
              "primary_PlantVillage_count": len(pv), "primary_PlantDoc_before_exclusions": sum(r["dataset"] == "plantdoc" and bool(r["canonical_label"]) for r in rows),
              "PlantDoc_evaluation_count": len(pd), "split_counts": dict(Counter(r["split"] for r in pv)),
              "duplicate_leakage": False, "cross_dataset_exact_duplicates": False, "per_class": counts}
    # Separate full-coverage split manifest preserves the initial audit manifests unchanged.
    write("primary_split_manifest.csv", rows)
    write("primary_class_split_counts.csv", counts)
    (OUT / "primary_class_set.json").write_text(json.dumps(config, indent=2) + "\n")
    (OUT / "primary_split_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
