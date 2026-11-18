"""Offline representation diagnostic; only coverage_audit.json is data input.

No training, tuning, inference, or cue reassignment. Python standard library only.
"""
import hashlib
import json
import math
import statistics
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'docs/experiment_results/pv_vlm_morphology_cue_audit/coverage_audit.json'
OUTPUT = INPUT.with_name('canonical_28d_diagnostic.json')
CUES = (
    'small_dark_spots', 'circular_spots', 'dark_borders', 'lighter_gray_centers',
    'surrounding_yellowing', 'concentric_ring_pattern', 'large_irregular_blotches',
    'water_soaked_appearance', 'yellowish_patches', 'olive_brown_surface_growth',
    'mosaic_mottled_green_pattern', 'leaf_curling', 'leaf_narrowing', 'leaf_deformation',
)
MAPPING = {'supported': [1, 0], 'uncertain': [0, 1], 'not_observed': [0, 0]}
REFERENCES = {
    'V2 overall_summary → SigLIP': dict(accuracy=.5666666667, macro_f1=.5546897547,
                                      balanced_accuracy=.5666666667, cosine_gap=.0194546985),
    'V4 evidence_summary → SigLIP': dict(accuracy=.4, macro_f1=.4200336700,
                                       balanced_accuracy=.4, cosine_gap=.0111476208),
    'V1 free-form → SigLIP': dict(accuracy=.3, macro_f1=.2920875421,
                                balanced_accuracy=.3, cosine_gap=.0136939838),
}


def cosine(a, b):
    denominator = math.sqrt(sum(v*v for v in a) * sum(v*v for v in b))
    assert denominator > 0, 'Cosine undefined for zero vector'
    return sum(x*y for x, y in zip(a, b)) / denominator


def mean_vector(vectors):
    assert vectors
    return [sum(column) / len(vectors) for column in zip(*vectors)]


def stats(values):
    return {'count': len(values), 'mean': statistics.mean(values),
            'std': statistics.stdev(values), 'ddof': 1, 'min': min(values), 'max': max(values)}


def top_cues(profile, offset):
    # Show every nonzero cue tied at the fifth-place frequency.
    ranked = sorted(((cue, profile[2*i+offset]) for i, cue in enumerate(CUES)), key=lambda x: -x[1])
    positive = [(cue, frequency) for cue, frequency in ranked if frequency > 0]
    cutoff = positive[min(4, len(positive)-1)][1] if positive else 0
    return [{'cue': cue, 'frequency': frequency} for cue, frequency in positive if frequency >= cutoff]


def save(report):
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def git_status():
    print('\nGit status:', flush=True)
    subprocess.run(['git', 'status', '--short'], cwd=ROOT, check=True)


def main():
    raw = INPUT.read_bytes()
    images = json.loads(raw)['per_image']
    assert len(images) == 30
    assert len({i['image_id'] for i in images}) == 30
    labels = [i['hidden_ground_truth_class'] for i in images]
    counts = Counter(labels)
    assert len(counts) == 6 and set(counts.values()) == {5}
    for image in images:
        assert len(image['cues']) == 14 and set(image['cues']) == set(CUES)
        assert all(image['cues'][cue]['state'] in MAPPING for cue in CUES)
    vectors = [[channel for cue in CUES for channel in MAPPING[i['cues'][cue]['state']]] for i in images]
    assert all(len(v) == 28 and set(v) <= {0, 1} for v in vectors)
    classes = sorted(counts)
    zero_ids = [i['image_id'] for i, v in zip(images, vectors) if not any(v)]
    assert all((sum(v) == 0) == (not any(v)) for v in vectors)
    feature_order = [f'{cue}.{channel}_channel' for cue in CUES for channel in ('supported', 'uncertain')]
    per_image = [{'image_id': i['image_id'], 'hidden_ground_truth_class': label, 'vector_28d': v,
                  'active_supported_channels': sum(v[::2]), 'active_uncertain_channels': sum(v[1::2])}
                 for i, label, v in zip(images, labels, vectors)]
    constant_zero = [cue for j, cue in enumerate(CUES) if all(v[2*j] == v[2*j+1] == 0 for v in vectors)]
    sparsity = {'supported_channels': stats([p['active_supported_channels'] for p in per_image]),
                'uncertain_channels': stats([p['active_uncertain_channels'] for p in per_image]),
                'constant_zero_cue_count': len(constant_zero), 'constant_zero_cues': constant_zero,
                'constant_zero_channel_count': sum(all(v[j] == 0 for v in vectors) for j in range(28))}
    report = {
        'input': str(INPUT.relative_to(ROOT)), 'input_sha256': hashlib.sha256(raw).hexdigest(),
        'validation': {'image_count': 30, 'class_count': 6, 'images_per_class': 5,
                       'class_counts': dict(sorted(counts.items())), 'cues_per_image': 14, 'dimensions': 28},
        'cue_order': CUES, 'feature_order': feature_order, 'state_mapping': MAPPING,
        'zero_vector_check': {'exists': bool(zero_ids), 'count': len(zero_ids), 'image_ids': zero_ids},
        'protocol': {'representation': 'Raw binary 28D vectors; arithmetic mean before prototype cosine normalization.',
                     'held_out_exclusion': 'Exclude only held-out image; own class n=4, other classes n=5.',
                     'class_order': classes, 'tie_break': 'Exact maximum tie: first class in sorted class order; ties reported.',
                     'pairwise': 'Unique unordered image pairs i<j, diagonal excluded; sample std ddof=1.',
                     'profile_top_rule': 'Top five nonzero frequencies including all ties at fifth place.'},
        'sparsity': sparsity, 'per_image': per_image,
        'cautions': ['Development sample only: 30 images, five per class; no significance claim.',
                     'Measures class-related structure of the existing cue assignments only; rule ambiguities are inherited.',
                     'No inference about field robustness or domain-gap reduction.',
                     'Rare cues are not necessarily useless; not_observed is not biological absence.',
                     'Prototype predictions are a representation diagnostic, not a trained or tuned classifier.',
                     'Cosine gaps depend on representation geometry; cross-representation differences are descriptive only.'],
    }
    print('Validation passed: 30 unique images; 6 classes x 5; exactly 14 cues/image; 28 binary dimensions.')
    print('Full zero vectors:', len(zero_ids), zero_ids)
    print('Sparsity (sample std):', json.dumps(sparsity, ensure_ascii=False))
    if zero_ids:
        report['status'] = 'stopped_before_prototype_metrics_due_to_zero_vectors'
        save(report)
        git_status()
        return
    # A mean of nonnegative nonzero vectors cannot be zero; still assert per fold.
    confusion = [[0]*6 for _ in classes]
    for held_out, (v, label, record) in enumerate(zip(vectors, labels, per_image)):
        prototypes = {c: mean_vector([x for j, (x, y) in enumerate(zip(vectors, labels))
                                     if j != held_out and y == c]) for c in classes}
        assert all(any(p) for p in prototypes.values())
        sizes = {c: sum(j != held_out and y == c for j, y in enumerate(labels)) for c in classes}
        assert sizes[label] == 4 and all(n == 5 for c, n in sizes.items() if c != label)
        scores = {c: cosine(v, prototypes[c]) for c in classes}
        tied = [c for c in classes if scores[c] == max(scores.values())]
        predicted = tied[0]
        record.update(predicted_class=predicted, cosine_scores=scores, max_score_tied_classes=tied,
                      prototype_image_counts=sizes)
        confusion[classes.index(label)][classes.index(predicted)] += 1
    recalls, f1s = {}, []
    for k, c in enumerate(classes):
        tp = confusion[k][k]
        actual, predicted = sum(confusion[k]), sum(row[k] for row in confusion)
        recalls[c] = tp/actual
        f1s.append(2*tp/(actual+predicted) if actual+predicted else 0.0)
    same, different = [], []
    for i in range(30):
        for j in range(i+1, 30):
            (same if labels[i] == labels[j] else different).append(cosine(vectors[i], vectors[j]))
    assert len(same) == 60 and len(different) == 375
    gap = statistics.mean(same) - statistics.mean(different)
    metrics = {'accuracy': sum(confusion[k][k] for k in range(6))/30,
               'macro_f1': statistics.mean(f1s), 'balanced_accuracy': statistics.mean(recalls.values())}
    profiles = {}
    for c in classes:
        profile = mean_vector([v for v, y in zip(vectors, labels) if y == c])
        profiles[c] = {'image_count': 5, 'mean_vector_28d': profile,
                       'top_supported_frequency_cues': top_cues(profile, 0),
                       'top_uncertain_frequency_cues': top_cues(profile, 1)}
    comparisons = {name: {'reference': ref, 'canonical_minus_reference':
                          {k: ({**metrics, 'cosine_gap': gap})[k]-value for k, value in ref.items()}}
                   for name, ref in REFERENCES.items()}
    report.update(status='completed', metrics=metrics,
                  confusion_matrix={'rows': 'ground_truth', 'columns': 'predicted', 'class_order': classes, 'counts': confusion},
                  per_class_recall=recalls, pairwise_cosine={'same_class': stats(same), 'different_class': stats(different), 'gap': gap},
                  exact_prediction_tie_count=sum(len(r['max_score_tied_classes']) > 1 for r in per_image),
                  per_class_mean_cue_profile=profiles,
                  development_reference_comparison={'source': 'User-supplied fixed development references; no other result files read.',
                                                    'comparisons': comparisons})
    save(report)
    print('\nMetrics:', json.dumps(metrics))
    print('Pairwise cosine:', json.dumps(report['pairwise_cosine']))
    print('\nConfusion matrix (rows=true, columns=predicted):', classes)
    for c, row in zip(classes, confusion): print(c, row)
    print('Per-class recall:', json.dumps(recalls))
    print('Exact maximum-score ties:', report['exact_prediction_tie_count'])
    print('\nDevelopment comparisons (canonical minus reference):')
    for name, comparison in comparisons.items(): print(name, json.dumps(comparison))
    print('\nClass cue profiles (descriptive, n=5 each):')
    for c, profile in profiles.items():
        print(c)
        for channel in ('supported', 'uncertain'):
            print(' ', channel, ', '.join(f'{p["cue"]}={p["frequency"]:.1f}' for p in profile[f'top_{channel}_frequency_cues']) or '(none)')
    print('\nDevelopment-only representation diagnostic; no significance or field-robustness claim.')
    print('Output:', OUTPUT.relative_to(ROOT), flush=True)
    git_status()


if __name__ == '__main__':
    main()
