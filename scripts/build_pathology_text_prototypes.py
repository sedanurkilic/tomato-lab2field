#!/usr/bin/env python3
"""Build frozen text prototypes solely from sectioned morphology source text.

Each non-empty, non-header line is one sentence. No sentence rewriting,
splitting, truncation, image access, or training is performed.
"""

import argparse
import hashlib
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "google/siglip-base-patch16-224"
MODEL_REVISION = "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed"
EXPECTED_CLASSES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Tomato_mosaic_virus",
]


def parse_source(source_bytes):
    """Preserve source order and sentence contents, excluding line terminators."""
    class_names, texts = [], []
    for line_number, line in enumerate(source_bytes.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        header = re.fullmatch(r"\[([^\[\]]+)\]", line.strip())
        if header:
            class_names.append(header.group(1))
            texts.append([])
        elif line.strip().startswith(("[", "]")):
            raise ValueError(f"Malformed section header at line {line_number}: {line!r}")
        elif not texts:
            raise ValueError(f"Sentence before first class header at line {line_number}.")
        else:
            texts[-1].append(line)
    if len(class_names) != 6:
        raise ValueError(f"Expected exactly 6 classes; found {len(class_names)}.")
    for name, sentences in zip(class_names, texts):
        if len(sentences) != 3:
            raise ValueError(f"Class {name!r}: expected exactly 3 sentences; found {len(sentences)}.")
    if class_names != EXPECTED_CLASSES:
        raise ValueError(f"Class names/order mismatch. Expected {EXPECTED_CLASSES}; found {class_names}.")
    return class_names, texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/pathology_morphology_prompts.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/pathology_text/pathology_text_prototypes_siglip.pt")
    parser.add_argument("--cache-dir", type=Path, default=None, help="Optional Hugging Face download cache.")
    args = parser.parse_args()
    source = args.source.resolve()
    source_bytes = source.read_bytes()
    class_names, texts = parse_source(source_bytes)
    print(f"Input txt path: {source}", flush=True)
    print(f"Model name: {MODEL_NAME}\nModel revision: {MODEL_REVISION}")
    print(f"Class count: {len(class_names)}\nSentences per class: {[len(t) for t in texts]}", flush=True)

    import torch
    import transformers
    from transformers import AutoTokenizer, SiglipModel

    torch.manual_seed(0)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    load_options = {"revision": MODEL_REVISION, "cache_dir": args.cache_dir}
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, **load_options)
    model = SiglipModel.from_pretrained(MODEL_NAME, **load_options).to(device="cpu", dtype=torch.float32)
    model.requires_grad_(False)
    model.eval()
    max_length = model.config.text_config.max_position_embeddings

    def normalize(tensor):
        norms = tensor.norm(p=2, dim=-1, keepdim=True)
        if not torch.isfinite(tensor).all() or not torch.isfinite(norms).all() or (norms <= 0).any():
            raise ValueError("Cannot normalize: zero norm or NaN/Inf in embeddings.")
        return tensor / norms

    embeddings = []
    with torch.inference_mode():
        for sentences in texts:
            class_embeddings = []
            for sentence in sentences:
                tokens = tokenizer(sentence, padding="max_length", max_length=max_length,
                                   truncation=False, return_tensors="pt")
                if tokens["input_ids"].shape[1] > max_length:
                    raise ValueError("Source sentence exceeds model context; refusing to truncate source text.")
                class_embeddings.append(normalize(model.get_text_features(**tokens)).squeeze(0))
            embeddings.append(torch.stack(class_embeddings))
        sentence_embeddings = torch.stack(embeddings)
        text_prototypes = normalize(sentence_embeddings.mean(dim=1))
        norms = text_prototypes.norm(p=2, dim=-1)
        dimension = text_prototypes.shape[-1]
        if sentence_embeddings.shape != (6, 3, dimension) or text_prototypes.shape != (6, dimension):
            raise ValueError("Unexpected embedding shapes.")
        if not torch.isfinite(sentence_embeddings).all() or not torch.isfinite(text_prototypes).all():
            raise ValueError("NaN/Inf detected.")
        if not torch.allclose(norms, torch.ones_like(norms), atol=1e-6, rtol=0):
            raise ValueError(f"Final prototype norms are not approximately 1: {norms}")
        cosine = text_prototypes @ text_prototypes.T

    if source.read_bytes() != source_bytes:
        raise ValueError("Source file changed during extraction; artifact not saved.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "class_names": class_names,
        "texts": texts,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "text_prototypes": text_prototypes,
        "sentence_embeddings": sentence_embeddings,
        "source_text_path": str(source),
        "source_text_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "torch_version": str(torch.__version__),
        "transformers_version": transformers.__version__,
        "device": "cpu",
        "dtype": "float32",
        "seed": 0,
        "max_length": max_length,
    }, args.output)
    print(f"Class order: {class_names}\nEmbedding dimension D: {dimension}")
    print(f"Sentence embedding shape: {list(sentence_embeddings.shape)}")
    print(f"Final prototype shape: {list(text_prototypes.shape)}")
    print(f"Final prototype L2 norms: {[round(v, 8) for v in norms.tolist()]}")
    print("NaN / Inf check: PASS (sentence embeddings and prototypes)")
    print("6x6 cosine similarity matrix (diagnostic only):")
    for row in cosine.tolist():
        print(" ".join(f"{value:.6f}" for value in row))
    print(f"Artifact saved: {args.output.resolve()}")


if __name__ == "__main__":
    main()
