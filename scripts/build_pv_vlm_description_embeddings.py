"""Encode unchanged validated PV descriptions with frozen SigLIP text only."""
import argparse
import csv
from collections import Counter
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCODER = 'google/siglip-base-patch16-224'
REVISION = '7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed'


def read_descriptions(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''))
    required = {'image_id', 'hidden_ground_truth_class', 'description', 'validation_pass'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Missing required description CSV columns')
    rows = []
    for row in reader:
        flag = row['validation_pass'].strip().lower()
        if flag not in {'true', 'false'}:
            raise ValueError('validation_pass must be true or false')
        if flag == 'true':
            if not row['description'].strip():
                raise ValueError('Empty validated description')
            rows.append(row)
    if len(rows) != 30 or len({r['image_id'] for r in rows}) != 30:
        raise ValueError('Expected exactly 30 validated descriptions with unique image IDs; complete the GPT stage first')
    classes = json.loads((ROOT/'manifests/primary_class_set.json').read_text())['canonical_classes']
    if Counter(r['hidden_ground_truth_class'] for r in rows) != Counter({c:5 for c in classes}):
        raise ValueError('Expected six frozen classes, five validated descriptions each')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'docs/experiment_results/pv_vlm_description_pilot/descriptions.csv')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/pv_vlm_description/pv_vlm_description_embeddings_siglip.pt')
    parser.add_argument('--summary', type=Path, default=ROOT/'docs/experiment_results/pv_vlm_description_pilot/embedding_summary.json')
    parser.add_argument('--cache-dir', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    rows = read_descriptions(raw)
    import torch
    import transformers
    from transformers import AutoTokenizer, SiglipTextModel
    torch.manual_seed(0)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    options = dict(revision=REVISION, cache_dir=args.cache_dir)
    tokenizer = AutoTokenizer.from_pretrained(ENCODER, **options)
    # pooler_output is the same text feature returned by SiglipModel.get_text_features.
    # Only the text encoder is instantiated; no vision encoder or image input.
    model, loading = SiglipTextModel.from_pretrained(ENCODER, output_loading_info=True, **options)
    if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):
        raise ValueError('Text encoder checkpoint did not load completely')
    model = model.to(device='cpu', dtype=torch.float32).eval()
    model.requires_grad_(False)
    assert not any(p.requires_grad for p in model.parameters())
    max_length = model.config.max_position_embeddings
    embeddings, token_counts = [], []
    with torch.inference_mode():
        for row in rows:
            # No prefixes, class names, stripping, rewriting or truncation.
            tokens = tokenizer(row['description'], padding='max_length', max_length=max_length,
                               truncation=False, return_tensors='pt')
            token_counts.append(len(tokenizer(row['description'], padding=False, truncation=False)['input_ids']))
            if tokens['input_ids'].shape[1] > max_length:
                raise ValueError(f"Description {row['image_id']} exceeds context; refusing truncation")
            embedding = model(**tokens).pooler_output
            norm = embedding.norm(p=2, dim=-1, keepdim=True)
            if not torch.isfinite(embedding).all() or not torch.isfinite(norm).all() or (norm <= 0).any():
                raise ValueError('Invalid/zero-norm text embedding')
            embeddings.append((embedding / norm).squeeze(0))
        embeddings = torch.stack(embeddings)
        norms = embeddings.norm(p=2, dim=-1)
        if embeddings.shape != (30, 768):
            raise ValueError(f'Unexpected embedding shape: {list(embeddings.shape)}')
        finite = bool(torch.isfinite(embeddings).all())
        if not finite or not torch.allclose(norms, torch.ones_like(norms), atol=1e-6, rtol=0):
            raise ValueError('Embedding unit-norm/finite validation failed')
        cosine = embeddings @ embeddings.T
        class_names = json.loads((ROOT/'manifests/primary_class_set.json').read_text())['canonical_classes']
        prototypes = []
        for name in class_names:
            indices = [i for i, r in enumerate(rows) if r['hidden_ground_truth_class'] == name]
            mean = embeddings[indices].mean(dim=0)
            norm = mean.norm()
            if not torch.isfinite(norm) or norm <= 0:
                raise ValueError('Invalid class prototype mean')
            prototypes.append(mean / norm)
        prototypes = torch.stack(prototypes)
        if prototypes.shape != (6,768) or not torch.isfinite(prototypes).all() or not torch.allclose(prototypes.norm(dim=-1),torch.ones(6),atol=1e-6,rtol=0):
            raise ValueError('Prototype shape/finite/norm check failed')
        prototype_cosine = prototypes @ prototypes.T
        same_pairs, different_pairs = [], []
        for i in range(30):
            for j in range(i+1,30):
                target = same_pairs if rows[i]['hidden_ground_truth_class']==rows[j]['hidden_ground_truth_class'] else different_pairs
                target.append({'image_id_a':rows[i]['image_id'],'image_id_b':rows[j]['image_id'],'cosine':float(cosine[i,j])})
        assert len(same_pairs)==60 and len(different_pairs)==375
        def stats(pairs):
            values = torch.tensor([pair['cosine'] for pair in pairs],dtype=torch.float64)
            return {'count':len(pairs),'mean':values.mean().item(),'sample_std':values.std(correction=1).item()}

    if args.source.read_bytes() != raw:
        raise ValueError('Source CSV changed during extraction')
    artifact = {'image_ids':[r['image_id'] for r in rows],
                'descriptions':[r['description'] for r in rows],
                'hidden_ground_truth_classes':[r['hidden_ground_truth_class'] for r in rows],
                'embeddings':embeddings, 'class_names':class_names, 'class_prototypes':prototypes,
                'encoder_name':ENCODER, 'encoder_revision':REVISION,
                'source_csv_path':str(args.source.resolve()), 'source_csv_sha256':hashlib.sha256(raw).hexdigest(),
                'torch_version':str(torch.__version__), 'transformers_version':transformers.__version__,
                'device':'cpu', 'dtype':'float32', 'seed':0, 'max_length':max_length,
                'token_counts':token_counts, 'feature_api':'SiglipTextModel.forward().pooler_output'}
    summary = {k:artifact[k] for k in ['encoder_name','encoder_revision','source_csv_path','source_csv_sha256','image_ids','dtype','token_counts']}
    summary.update(embedding_shape=list(embeddings.shape), l2_norms=norms.tolist(),
                   nan_count=int(torch.isnan(embeddings).sum()), inf_count=int(torch.isinf(embeddings).sum()),
                   all_finite=finite, unit_norm_check_pass=True, cosine_similarity_matrix=cosine.tolist(),
                   same_class_pairs=same_pairs, different_class_pairs=different_pairs,
                   same_class_cosine=stats(same_pairs), different_class_cosine=stats(different_pairs),
                   class_names=class_names, prototype_shape=list(prototypes.shape),
                   prototype_l2_norms=prototypes.norm(dim=-1).tolist(),
                   prototype_cosine_similarity_matrix=prototype_cosine.tolist(),
                   interpretation='Descriptive diagnostics only; no threshold tuning or statistical significance claim.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(artifact, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
