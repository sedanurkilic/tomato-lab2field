"""Multi-Agent Attention baseline on cached frozen DINOv2 patch tokens.

Single-Query Attention extended only by the number of queries: 4 learnable
queries (Normal(0, 0.02) init), each with its own softmax over the 256 patch
tokens. The four pooled vectors are averaged (mean over agents, no
concatenation) and fed to one shared Linear(768 -> 6). No key/value
projection, multi-head, MLP, residual, LayerNorm, positional bias, diversity
loss, agent-specific classifier or dropout.

PlantDoc (external_target_test) is used only for the final evaluation after
the best PlantVillage-validation checkpoint has been restored.
"""

import copy
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "artifacts" / "dinov2_raw"
RESULT_DIR = ROOT / "results" / "multi_agent_attention"

SEEDS = [42, 0, 1]
NUM_AGENTS = 4
CONFIG = {
    "backbone": "Frozen DINOv2 ViT-B/14 (cached patch tokens)",
    "aggregation": "4 learnable queries (Normal(0, 0.02)), per-agent softmax over patches, mean over agents",
    "num_agents": NUM_AGENTS,
    "classifier": "Linear(768 -> 6)",
    "optimizer": "AdamW",
    "learning_rate": 1e-3,
    "weight_decay": 1e-4,
    "loss": "CrossEntropyLoss",
    "batch_size": 64,
    "eval_batch_size": 256,
    "max_epochs": 50,
    "patience": 5,
    "selection_metric": "PlantVillage validation Macro-F1",
    "seeds": SEEDS,
}

EXPECTED_SPLITS = {
    "train": 5692,
    "validation": 1221,
    "test": 1219,
    "external_target_test": 603,
}
NUM_PATCHES = 256
DIM = 768


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def pick_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class MultiAgentAttention(nn.Module):
    def __init__(self, dim=DIM, num_classes=6, num_agents=NUM_AGENTS):
        super().__init__()
        self.query = nn.Parameter(torch.randn(num_agents, dim) * 0.02)  # [A, D]
        self.classifier = nn.Linear(dim, num_classes)
        self.scale = math.sqrt(dim)

    def forward(self, tokens):
        # tokens: [B, N, D]
        scores = torch.einsum("bnd,ad->ban", tokens, self.query) / self.scale  # [B, A, N]
        weights = torch.softmax(scores, dim=2)  # softmax over patches only
        pooled = torch.einsum("ban,bnd->bad", weights, tokens)  # [B, A, D]
        fused = pooled.mean(dim=1)  # [B, D], mean over agents (no concat)
        return self.classifier(fused), weights  # weights: [B, A, N]


def fetch(patches, idx, device):
    """Index the mmap'd fp16 cache; only the batch is made float32 / moved."""
    return patches[idx].float().to(device)


def run_eval(model, patches, indices, labels, device, batch_size, collect_weights=False):
    model.eval()
    loader = DataLoader(
        TensorDataset(torch.as_tensor(indices)), batch_size=batch_size, shuffle=False
    )
    logits_all, weights_all = [], []
    with torch.no_grad():
        for (idx,) in loader:
            logits, weights = model(fetch(patches, idx, device))
            logits_all.append(logits.cpu())
            if collect_weights:
                weights_all.append(weights.cpu())
    logits = torch.cat(logits_all)
    y = labels[indices]
    loss = nn.functional.cross_entropy(logits, y).item()
    probs = torch.softmax(logits, dim=1)
    preds = probs.argmax(dim=1)
    weights = torch.cat(weights_all) if collect_weights else None
    return loss, y.numpy(), preds.numpy(), probs.numpy(), weights


def metrics_for(y, p, num_classes):
    return {
        "macro_f1": float(f1_score(y, p, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(y, p)),
        "accuracy": float(accuracy_score(y, p)),
        "per_class_recall": recall_score(
            y, p, labels=list(range(num_classes)), average=None, zero_division=0
        ).tolist(),
    }


def save_predictions(path, subset_meta, y, p, probs, class_names):
    out = subset_meta[["image_id", "canonical_label"]].reset_index(drop=True).copy()
    out["prediction"] = [class_names[i] for i in p]
    out["confidence"] = probs.max(axis=1)
    out["correct"] = p == y
    out.to_csv(path, index=False)


def save_attention(path, weights, subset_meta, meta_rows, split_name):
    torch.save(
        {
            "split": split_name,
            "weights": weights,  # [N, 4, 256], row i <-> metadata row meta_rows[i]
            "metadata_row_index": torch.as_tensor(meta_rows),
            "image_id": subset_meta["image_id"].tolist(),
        },
        path,
    )


def train_one_seed(seed, patches, meta, labels, split_idx, class_names, device):
    set_seed(seed)
    num_classes = len(class_names)
    out_dir = RESULT_DIR / f"seed_{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    model = MultiAgentAttention(DIM, num_classes, NUM_AGENTS).to(device)
    assert tuple(model.query.shape) == (NUM_AGENTS, DIM)
    assert model.query.std().item() > 0 and not torch.equal(model.query[0], model.query[1])
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert n_trainable == NUM_AGENTS * DIM + DIM * num_classes + num_classes == 7686, n_trainable
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=CONFIG["learning_rate"],
        weight_decay=CONFIG["weight_decay"],
    )
    criterion = nn.CrossEntropyLoss()

    generator = torch.Generator().manual_seed(seed)
    train_idx = split_idx["train"]
    train_loader = DataLoader(
        TensorDataset(torch.as_tensor(train_idx)),
        batch_size=CONFIG["batch_size"],
        shuffle=True,
        generator=generator,
    )

    best_f1, best_epoch, best_state, bad_epochs = -1.0, -1, None, 0
    history = []

    for epoch in range(1, CONFIG["max_epochs"] + 1):
        model.train()
        total_loss = 0.0
        for (idx,) in train_loader:
            x = fetch(patches, idx, device)
            y = labels[idx].to(device)
            optimizer.zero_grad()
            logits, _ = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)
        train_loss = total_loss / len(train_idx)

        # Model selection uses PlantVillage validation only.
        val_loss, yv, pv, _, _ = run_eval(
            model, patches, split_idx["validation"], labels, device,
            CONFIG["eval_batch_size"],
        )
        val_f1 = float(f1_score(yv, pv, average="macro"))
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_macro_f1": val_f1,
            "val_accuracy": float(accuracy_score(yv, pv)),
        })

        if val_f1 > best_f1:
            best_f1, best_epoch, bad_epochs = val_f1, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            bad_epochs += 1
            if bad_epochs >= CONFIG["patience"]:
                break

    pd.DataFrame(history).to_csv(out_dir / "training_history.csv", index=False)

    # Final evaluation with the best-validation checkpoint.
    model.load_state_dict(best_state)
    torch.save(
        {
            "state_dict": best_state,
            "seed": seed,
            "best_epoch": best_epoch,
            "best_val_macro_f1": best_f1,
            "class_names": class_names,
            "config": CONFIG,
        },
        out_dir / "best_model.pt",
    )

    results = {}
    for name, key, pred_file, att_file in [
        ("pv_test", "test", "predictions_pv_test.csv", "attention_pv_test.pt"),
        ("plantdoc", "target", "predictions_plantdoc.csv", "attention_plantdoc.pt"),
    ]:
        rows = split_idx[key]
        _, y, p, probs, weights = run_eval(
            model, patches, rows, labels, device, CONFIG["eval_batch_size"],
            collect_weights=True,
        )
        assert tuple(weights.shape) == (len(rows), NUM_AGENTS, NUM_PATCHES), weights.shape
        results[name] = metrics_for(y, p, num_classes)
        subset_meta = meta.iloc[rows]
        save_predictions(out_dir / pred_file, subset_meta, y, p, probs, class_names)
        save_attention(out_dir / att_file, weights, subset_meta, rows, key)

    delta = results["pv_test"]["macro_f1"] - results["plantdoc"]["macro_f1"]
    metrics = {
        "seed": seed,
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "best_val_macro_f1": best_f1,
        "pv_test": results["pv_test"],
        "plantdoc": results["plantdoc"],
        "delta_macro_f1": delta,
        "class_names": class_names,
    }
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(
        f"seed={seed} | PV F1={results['pv_test']['macro_f1']:.5f} | "
        f"PD F1={results['plantdoc']['macro_f1']:.5f} | Δ={delta:.5f}"
    )
    return metrics, n_trainable


def mean_std(values):
    arr = np.asarray(values, dtype=float)
    return float(arr.mean()), float(arr.std(ddof=1)) if len(arr) > 1 else 0.0


def main():
    device = pick_device()
    patches = torch.load(
        FEATURE_DIR / "patch_tokens_fp16.pt", mmap=True, map_location="cpu"
    )
    meta = pd.read_csv(FEATURE_DIR / "metadata.csv")

    assert tuple(patches.shape) == (8735, NUM_PATCHES, DIM), patches.shape
    assert patches.dtype == torch.float16, patches.dtype
    assert len(meta) == 8735
    for split, n in EXPECTED_SPLITS.items():
        assert (meta["split"] == split).sum() == n, split
    assert meta["canonical_label"].nunique() == 6

    class_names = sorted(meta["canonical_label"].unique())
    name_to_label = meta.groupby("canonical_label")["label"].first()
    assert [int(name_to_label[c]) for c in class_names] == list(range(len(class_names)))
    assert (meta["canonical_label"].map(name_to_label) == meta["label"]).all()
    labels = torch.tensor(meta["label"].values, dtype=torch.long)

    split_vals = meta["split"].values
    split_idx = {
        "train": np.where(split_vals == "train")[0],
        "validation": np.where(split_vals == "validation")[0],
        "test": np.where(split_vals == "test")[0],
        "target": np.where(split_vals == "external_target_test")[0],
    }

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics, n_params = [], None
    for seed in SEEDS:
        metrics, n_params = train_one_seed(
            seed, patches, meta, labels, split_idx, class_names, device
        )
        all_metrics.append(metrics)

    rows = []
    for m in all_metrics:
        row = {
            "seed": m["seed"],
            "best_epoch": m["best_epoch"],
            "epochs_run": m["epochs_run"],
            "best_val_macro_f1": m["best_val_macro_f1"],
            "delta_macro_f1": m["delta_macro_f1"],
        }
        for ds in ("pv_test", "plantdoc"):
            for k in ("macro_f1", "balanced_accuracy", "accuracy"):
                row[f"{ds}_{k}"] = m[ds][k]
        for i, c in enumerate(class_names):
            row[f"plantdoc_recall_{c}"] = m["plantdoc"]["per_class_recall"][i]
        rows.append(row)
    pd.DataFrame(rows).to_csv(RESULT_DIR / "seed_results.csv", index=False)

    summary = {"config": CONFIG, "n_seeds": len(SEEDS), "trainable_parameters": n_params}
    for ds in ("pv_test", "plantdoc"):
        for k in ("macro_f1", "balanced_accuracy", "accuracy"):
            mu, sd = mean_std([m[ds][k] for m in all_metrics])
            summary[f"{ds}_{k}"] = {"mean": mu, "std": sd}
    mu, sd = mean_std([m["delta_macro_f1"] for m in all_metrics])
    summary["delta_macro_f1"] = {"mean": mu, "std": sd}
    recalls = np.array([m["plantdoc"]["per_class_recall"] for m in all_metrics])
    summary["plantdoc_per_class_recall_mean"] = {
        c: float(recalls[:, i].mean()) for i, c in enumerate(class_names)
    }
    with open(RESULT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print()
    for label, key in [
        ("PV Macro-F1", "pv_test_macro_f1"),
        ("PV balanced accuracy", "pv_test_balanced_accuracy"),
        ("PV accuracy", "pv_test_accuracy"),
        ("PD Macro-F1", "plantdoc_macro_f1"),
        ("PD balanced accuracy", "plantdoc_balanced_accuracy"),
        ("PD accuracy", "plantdoc_accuracy"),
        ("delta Macro-F1", "delta_macro_f1"),
    ]:
        print(f"{label}: {summary[key]['mean']:.5f} ± {summary[key]['std']:.5f}")
    print()
    print(f"Trainable parameters: {n_params}")
    print(f"Patch tensor shape: {tuple(patches.shape)}")
    print(f"Patch dtype: {patches.dtype}")
    print(f"Device: {device}")


if __name__ == "__main__":
    main()
