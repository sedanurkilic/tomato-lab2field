"""PCA diagnostic for frozen DINOv2 CLS and GAP features.

PCA is fit only on PlantVillage train features. PlantVillage test and
PlantDoc external target are projected into the same space. Validation
is never used.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch
from matplotlib.lines import Line2D
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "artifacts" / "dinov2_raw"
FIG_DIR = ROOT / "docs" / "figures" / "dinov2_pca"

EXPECTED_SPLITS = {
    "train": 5692,
    "validation": 1221,
    "test": 1219,
    "external_target_test": 603,
}


def load_data():
    cls = torch.load(FEATURE_DIR / "cls_features.pt", map_location="cpu").float().numpy()
    gap = torch.load(FEATURE_DIR / "gap_features.pt", map_location="cpu").float().numpy()
    meta = pd.read_csv(FEATURE_DIR / "metadata.csv")

    assert cls.shape == (8735, 768), cls.shape
    assert gap.shape == (8735, 768), gap.shape
    assert len(meta) == 8735
    for split, n in EXPECTED_SPLITS.items():
        assert (meta["split"] == split).sum() == n, split
    assert meta["canonical_label"].nunique() == 6
    return cls, gap, meta


def run_pca(features, meta, name, class_names, colors):
    is_pv = meta["dataset"].values == "plantvillage"
    split = meta["split"].values
    train_idx = (is_pv & (split == "train")).nonzero()[0]
    pv_test_idx = (is_pv & (split == "test")).nonzero()[0]
    pd_idx = (split == "external_target_test").nonzero()[0]

    pca = PCA(n_components=2).fit(features[train_idx])
    ev = pca.explained_variance_ratio_

    fig, ax = plt.subplots(figsize=(7.5, 6))
    for idx, marker, size, lw in [(pv_test_idx, "o", 14, 0), (pd_idx, "x", 22, 0.9)]:
        z = pca.transform(features[idx])
        labels = meta["canonical_label"].values[idx]
        for cls_name in class_names:
            m = labels == cls_name
            ax.scatter(
                z[m, 0], z[m, 1], s=size, marker=marker, color=colors[cls_name],
                alpha=0.4 if marker == "o" else 0.8, linewidths=lw,
            )

    ax.set_xlabel(f"PC1 ({ev[0] * 100:.1f}%)")
    ax.set_ylabel(f"PC2 ({ev[1] * 100:.1f}%)")
    ax.set_title(f"DINOv2 {name}: PlantVillage vs PlantDoc")
    ax.spines[["top", "right"]].set_visible(False)

    class_handles = [
        Line2D([], [], marker="s", linestyle="", color=colors[c],
               label=c.replace("Tomato___", "").replace("_", " "))
        for c in class_names
    ]
    domain_handles = [
        Line2D([], [], marker="o", linestyle="", color="0.3", label="PlantVillage test"),
        Line2D([], [], marker="x", linestyle="", color="0.3", label="PlantDoc"),
    ]
    ax.legend(handles=class_handles + domain_handles, fontsize=8, frameon=False,
              loc="center left", bbox_to_anchor=(1.01, 0.5))

    fig.tight_layout()
    path = FIG_DIR / f"dinov2_{name.lower()}_pca.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return ev, len(pv_test_idx), len(pd_idx), path


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    cls, gap, meta = load_data()

    class_names = sorted(meta["canonical_label"].unique())
    palette = plt.get_cmap("tab10").colors
    colors = {c: palette[i] for i, c in enumerate(class_names)}

    for name, feats in [("CLS", cls), ("GAP", gap)]:
        ev, n_pv, n_pd, path = run_pca(feats, meta, name, class_names, colors)
        print(f"{name}: PC1 {ev[0] * 100:.1f}% | PC2 {ev[1] * 100:.1f}% | "
              f"PC1+PC2 {ev.sum() * 100:.1f}%")
        print(f"  saved: {path.relative_to(ROOT)}")
    print(f"PV test n={n_pv}, PlantDoc n={n_pd}")


if __name__ == "__main__":
    main()
