"""Encode source-grounded observable concepts; no images or training.

Definitions live only in the concept txt. Manual source-text mapping below
is fixed before encoding; cosine diagnostics never modify it. Evidence indices
are zero-based sentence positions in the original disease-text sections.
"""

import argparse
import hashlib
from pathlib import Path
import re

from build_pathology_text_prototypes import MODEL_NAME, MODEL_REVISION, ROOT, parse_source


# Optional morphology remains possible even when another sentence states it
# without a qualifier. Unlisted concepts are not_supported, never negatives.
SOURCE_MAPPING = {
    "Tomato___Bacterial_spot": {
        "small_dark_spots": ("present", [0, 1, 2]),
        "surrounding_yellowing": ("possible", [1]),
    },
    "Tomato___Early_blight": {
        "concentric_ring_pattern": ("present", [0, 1, 2]),
        "surrounding_yellowing": ("present", [1]),
    },
    "Tomato___Late_blight": {
        "large_irregular_blotches": ("present", [0, 1]),
        "water_soaked_appearance": ("possible", [2]),
    },
    "Tomato___Leaf_Mold": {
        "yellowish_patches": ("present", [0, 1, 2]),
        "olive_brown_surface_growth": ("possible", [0, 1, 2]),
    },
    "Tomato___Septoria_leaf_spot": {
        "circular_spots": ("present", [0, 1, 2]),
        "dark_borders": ("present", [0, 1, 2]),
        "lighter_gray_centers": ("present", [0, 1, 2]),
    },
    "Tomato___Tomato_mosaic_virus": {
        "mosaic_mottled_green_pattern": ("present", [0, 1, 2]),
        "leaf_curling": ("possible", [1, 2]),
        "leaf_narrowing": ("possible", [1]),
        "leaf_deformation": ("possible", [2]),
    },
}


def parse_concepts(raw):
    names, texts = [], []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        header = re.fullmatch(r"\[([a-z][a-z0-9_]*)\]", line)
        if header:
            if header[1] in names:
                raise ValueError(f"Duplicate concept at line {number}: {header[1]}")
            names.append(header[1])
            texts.append([])
        elif not texts or line.startswith(("[", "]")):
            raise ValueError(f"Invalid concept section at line {number}")
        else:
            texts[-1].append(line)
    if not names or any(len(t) != 1 for t in texts):
        raise ValueError("Each concept must have exactly one non-empty description line.")
    expected = {name for mapping in SOURCE_MAPPING.values() for name in mapping}
    if set(names) != expected:
        raise ValueError("Concept names do not match the source-grounded mapping.")
    return names, [t[0] for t in texts]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/pathology_morphology_concepts.txt")
    parser.add_argument("--disease-source", type=Path, default=ROOT / "data/pathology_morphology_prompts.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/pathology_text/pathology_morphology_concepts_siglip.pt")
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    raw, disease_raw = args.source.read_bytes(), args.disease_source.read_bytes()
    names, texts = parse_concepts(raw)
    class_names, disease_texts = parse_source(disease_raw)
    if class_names != list(SOURCE_MAPPING):
        raise ValueError("Disease class order differs from mapping order.")
    mapping, evidence = {}, {}
    for class_name, sentences in zip(class_names, disease_texts):
        supported = SOURCE_MAPPING[class_name]
        mapping[class_name] = {name: supported[name][0] if name in supported else "not_supported" for name in names}
        evidence[class_name] = {
            name: {"sentence_indices": indices, "source_sentences": [sentences[i] for i in indices]}
            for name, (_, indices) in supported.items()
        }

    import torch
    import transformers
    from transformers import AutoTokenizer, SiglipModel

    torch.manual_seed(0)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    options = {"revision": MODEL_REVISION, "cache_dir": args.cache_dir}
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, **options)
    model = SiglipModel.from_pretrained(MODEL_NAME, **options).to(device="cpu", dtype=torch.float32)
    model.requires_grad_(False)
    model.eval()
    max_length = model.config.text_config.max_position_embeddings
    embeddings = []
    with torch.inference_mode():
        for text in texts:
            tokens = tokenizer(text, padding="max_length", max_length=max_length,
                               truncation=False, return_tensors="pt")
            if tokens["input_ids"].shape[1] > max_length:
                raise ValueError("Concept exceeds context; refusing truncation.")
            embedding = model.get_text_features(**tokens)
            norm = embedding.norm(dim=-1, keepdim=True)
            if not torch.isfinite(embedding).all() or not torch.isfinite(norm).all() or (norm <= 0).any():
                raise ValueError("Non-finite or zero-norm concept embedding.")
            embeddings.append((embedding / norm).squeeze(0))
        embeddings = torch.stack(embeddings)
        norms = embeddings.norm(dim=-1)
        if embeddings.shape != (len(names), 768):
            raise ValueError(f"Unexpected concept shape: {embeddings.shape}")
        if not torch.isfinite(embeddings).all() or not torch.allclose(norms, torch.ones_like(norms), atol=1e-6, rtol=0):
            raise ValueError("Concept finite/unit-norm check failed.")
        cosine = embeddings @ embeddings.T
    if raw != args.source.read_bytes() or disease_raw != args.disease_source.read_bytes():
        raise ValueError("Source changed during extraction.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "concept_names": names, "concept_texts": texts, "concept_embeddings": embeddings,
        "model_name": MODEL_NAME, "model_revision": MODEL_REVISION,
        "source_text_path": str(args.source.resolve()),
        "source_text_sha256": hashlib.sha256(raw).hexdigest(),
        "disease_source_text_path": str(args.disease_source.resolve()),
        "disease_source_sha256": hashlib.sha256(disease_raw).hexdigest(),
        "class_names": class_names, "class_to_concepts": mapping,
        "class_to_concept_evidence": evidence,
        "mapping_semantics": {"present": "explicit unqualified morphology in source",
                              "possible": "conditional morphology; not an unconditional positive",
                              "not_supported": "not established by source; not a negative label"},
        "torch_version": str(torch.__version__), "transformers_version": transformers.__version__,
        "device": "cpu", "dtype": "float32", "seed": 0, "max_length": max_length,
    }, args.output)
    print(f"Concept count K: {len(names)}\nConcept names: {names}")
    print(f"Embedding shape: {list(embeddings.shape)}\nL2 norms: {norms.tolist()}\nNaN/Inf: none")
    print("Class-to-concept mapping (unlisted = not_supported):")
    for name in class_names:
        print(name, {k: v for k, v in mapping[name].items() if v != "not_supported"})
    print("Cosine similarity matrix (diagnostic only; source order):")
    for row in cosine.tolist():
        print(" ".join(f"{v:.4f}" for v in row))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
