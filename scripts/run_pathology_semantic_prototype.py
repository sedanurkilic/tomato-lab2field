"""PV-only projection training with fixed pathology text output geometry."""

import copy
import hashlib
import json
import random
from pathlib import Path
import time

import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "artifacts/dinov2_raw"
PROTOTYPE_PATH = ROOT / "artifacts/pathology_text/pathology_text_prototypes_siglip.pt"
BASELINE_DIR = ROOT / "docs/experiment_results/dinov2_raw"
OUT = ROOT / "docs/experiment_results/pathology_semantic_prototype"
SEEDS = [42, 0, 1]
SCALE = 10.0
SPLIT_COUNTS = {"train": 5692, "validation": 1221, "test": 1219, "external_target_test": 603}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SemanticPrototypeClassifier(nn.Module):
    def __init__(self, prototypes):
        super().__init__()
        self.projection = nn.Linear(768, 768, bias=False)
        self.register_buffer("prototypes", prototypes.detach().clone())

    def forward(self, x):
        z = nn.functional.normalize(self.projection(x), p=2, dim=-1)
        return SCALE * (z @ self.prototypes.T)


def metrics(y, pred):
    return {
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "accuracy": float(accuracy_score(y, pred)),
        "per_class_recall": recall_score(y, pred, labels=list(range(6)),
                                       average=None, zero_division=0).tolist(),
    }


def evaluate(model, x, y, device):
    model.eval()
    with torch.no_grad():
        logits = model(x.to(device))
        assert torch.isfinite(logits).all(), "Non-finite evaluation logits"
        pred = logits.argmax(dim=1).cpu().numpy()
    return metrics(y.numpy(), pred)


def mean_std(values):
    values = np.asarray(values, dtype=float)
    return {"mean": float(values.mean()), "std": float(values.std(ddof=1))}


def train_seed(seed, features, labels, indices, prototypes, config, device):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    model = SemanticPrototypeClassifier(prototypes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"],
                                 weight_decay=config["weight_decay"])
    criterion = nn.CrossEntropyLoss()
    train_rows = indices["train"]
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(features[train_rows], labels[train_rows]),
        batch_size=config["batch_size"], shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )
    best_f1, best_epoch, best_state, bad_epochs = -1.0, -1, None, 0
    history, sanity = [], None
    frozen_before = model.prototypes.detach().clone()
    for epoch in range(1, config["max_epochs"] + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            if sanity is None:
                with torch.no_grad():
                    projected = model.projection(xb)
                    normalized = nn.functional.normalize(projected, p=2, dim=-1)
                    norms = normalized.norm(dim=-1)
                    assert projected.shape == xb.shape
                    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-6, rtol=0)
                    sanity = {"input_shape": list(xb.shape),
                              "projected_shape": list(projected.shape),
                              "normalized_norm_min": norms.min().item(),
                              "normalized_norm_max": norms.max().item()}
            logits = model(xb)
            assert logits.shape == (len(xb), 6)
            assert torch.isfinite(logits).all()
            loss = criterion(logits, yb)
            assert torch.isfinite(loss)
            loss.backward()
            assert model.prototypes.grad is None and not model.prototypes.requires_grad
            assert torch.isfinite(model.projection.weight.grad).all()
            if "logits_shape" not in sanity:
                sanity["logits_shape"] = list(logits.shape)
                sanity["projection_gradient_norm"] = model.projection.weight.grad.norm().item()
                assert sanity["projection_gradient_norm"] > 0
                print(f"seed={seed} first batch: {sanity}", flush=True)
            optimizer.step()
            total_loss += loss.item() * len(xb)
        rows = indices["validation"]
        val = evaluate(model, features[rows], labels[rows], device)
        history.append({"epoch": epoch, "train_loss": total_loss / len(train_rows),
                        "val_macro_f1": val["macro_f1"]})
        if val["macro_f1"] > best_f1:
            best_f1, best_epoch, bad_epochs = val["macro_f1"], epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            bad_epochs += 1
        print(f"seed={seed} epoch={epoch} val_macro_f1={val['macro_f1']:.5f}", flush=True)
        if bad_epochs >= config["patience"]:
            break
    model.load_state_dict(best_state)
    assert torch.equal(model.prototypes, frozen_before), "Frozen prototypes changed"
    result = {"seed": seed, "best_epoch": best_epoch, "epochs_run": len(history),
              "best_val_macro_f1": best_f1, "first_batch_sanity": sanity,
              "history": history}
    # Both held-out sets are evaluated only after PV-validation selection finishes.
    for name, split in [("pv_test", "test"), ("plantdoc", "external_target_test")]:
        rows = indices[split]
        result[name] = evaluate(model, features[rows], labels[rows], device)
    result["delta_macro_f1"] = result["pv_test"]["macro_f1"] - result["plantdoc"]["macro_f1"]
    print(f"seed={seed} best_epoch={best_epoch} PV={result['pv_test']} PD={result['plantdoc']}", flush=True)
    return result


def main():
    started = time.monotonic()
    config = json.loads((BASELINE_DIR / "probe_config.json").read_text())
    assert config["optimizer"] == "AdamW"
    assert config["selection_metric"] == "PlantVillage validation Macro-F1"
    config.update({"backbone": "Frozen cached DINOv2 CLS", "probe": "Linear(768, 768, bias=False)",
                   "output_geometry": "frozen SigLIP pathology text prototypes",
                   "scale": SCALE, "seeds": SEEDS, "loss": "CrossEntropyLoss",
                   "input_normalization": "none (same as existing CLS baseline)"})
    baseline = pd.read_csv(BASELINE_DIR / "seed_results.csv")
    baseline = baseline[baseline["representation"] == "cls"].set_index("seed")
    assert baseline.index.is_unique and set(SEEDS).issubset(baseline.index)
    features = torch.load(FEATURE_DIR / "cls_features.pt", map_location="cpu", weights_only=True).float()
    meta = pd.read_csv(FEATURE_DIR / "metadata.csv")
    artifact = torch.load(PROTOTYPE_PATH, map_location="cpu", weights_only=True)
    prototypes = artifact["text_prototypes"].detach().float()
    class_names = artifact["class_names"]
    assert features.shape == (8735, 768) and len(meta) == 8735
    assert prototypes.shape == (6, 768)
    assert torch.isfinite(features).all() and torch.isfinite(prototypes).all()
    assert torch.allclose(prototypes.norm(dim=-1), torch.ones(6), atol=1e-6, rtol=0)
    assert class_names == sorted(meta["canonical_label"].unique().tolist())
    mapping = dict(enumerate(class_names))
    assert (meta["label"].map(mapping) == meta["canonical_label"]).all()
    assert meta["image_id"].is_unique
    assert meta["split"].value_counts().to_dict() == SPLIT_COUNTS
    assert (meta.loc[meta["split"] != "external_target_test", "dataset"] == "plantvillage").all()
    assert (meta.loc[meta["split"] == "external_target_test", "dataset"] == "plantdoc").all()
    labels = torch.tensor(meta["label"].values, dtype=torch.long)
    indices = {split: np.flatnonzero(meta["split"].values == split) for split in SPLIT_COUNTS}
    assert not features.requires_grad and not prototypes.requires_grad
    # Match the notebook baseline's CUDA/CPU choice; cap CPU threads for these small matrices.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(1)
    parameter_count = 768 * 768
    assert sum(p.numel() for p in SemanticPrototypeClassifier(prototypes).parameters()) == parameter_count
    sanity = {"feature_shape": list(features.shape), "prototype_shape": list(prototypes.shape),
              "prototype_norms": prototypes.norm(dim=-1).tolist(), "finite": True,
              "class_mapping_matches": True, "split_counts": SPLIT_COUNTS}
    print(f"Preflight PASS: {sanity}\nDevice: {device}\nTrainable parameters: {parameter_count}", flush=True)
    results = [train_seed(seed, features, labels, indices, prototypes, config, device) for seed in SEEDS]
    rows = []
    for result in results:
        seed = result["seed"]
        row = {key: result[key] for key in ["seed", "best_epoch", "epochs_run", "best_val_macro_f1", "delta_macro_f1"]}
        for dataset in ["pv_test", "plantdoc"]:
            for metric in ["macro_f1", "balanced_accuracy", "accuracy"]:
                row[f"{dataset}_{metric}"] = result[dataset][metric]
        for i, name in enumerate(class_names):
            row[f"plantdoc_recall_{name}"] = result["plantdoc"]["per_class_recall"][i]
        row["cls_baseline_plantdoc_macro_f1"] = float(baseline.loc[seed, "pd_macro_f1"])
        row["semantic_minus_cls_plantdoc_macro_f1"] = row["plantdoc_macro_f1"] - row["cls_baseline_plantdoc_macro_f1"]
        rows.append(row)
    table = pd.DataFrame(rows)
    summary = {"config": config, "class_names": class_names, "trainable_parameters": parameter_count,
               "device": str(device), "torch_version": str(torch.__version__),
               "cpu_threads": torch.get_num_threads(), "sanity_checks": sanity,
               "per_seed": results, "n_seeds": len(SEEDS),
               "baseline_source": str((BASELINE_DIR / "seed_results.csv").relative_to(ROOT)),
               "baseline_config_source": str((BASELINE_DIR / "probe_config.json").relative_to(ROOT)),
               "baseline_summary": {k: mean_std(baseline.loc[SEEDS, k]) for k in
                                    ["pv_macro_f1", "pd_macro_f1", "delta_macro_f1"]},
               "input_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in
                                [FEATURE_DIR / "cls_features.pt", FEATURE_DIR / "metadata.csv", PROTOTYPE_PATH]},
               "interpretation": "Fixed pathology-derived text prototypes were used as the classifier output geometry; descriptive comparison only, no statistical significance or semantic grounding claim.",
               "elapsed_seconds": time.monotonic() - started}
    for column in table:
        if column not in ["seed", "best_epoch", "epochs_run"]:
            summary[column] = mean_std(table[column])
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "seed_results.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(table.to_string(index=False))
    print(json.dumps({k: v for k, v in summary.items() if isinstance(v, dict) and "mean" in v}, indent=2))


if __name__ == "__main__":
    main()
