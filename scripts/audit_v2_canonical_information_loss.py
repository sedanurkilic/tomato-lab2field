"""Deterministic text information-loss inventory, not a new representation.

Only the three declared original-development inputs are read. No inference,
classification, label-guided extraction, or modification of existing cue states.
"""
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'docs/experiment_results/pv_vlm_morphology_cue_audit'
INPUTS = {
    'v2': ROOT / 'docs/experiment_results/pv_vlm_description_structured_pilot/descriptions.jsonl',
    'coverage': DIRECTORY / 'coverage_audit.json',
    'diagnostic': DIRECTORY / 'canonical_28d_diagnostic.json',
}
OUTPUT = DIRECTORY / 'information_loss_audit.json'
FIELDS = ('color_pattern', 'lesions_spots', 'center_border_internal_pattern',
          'distribution', 'surface_deformation', 'overall_summary')
CUES = ('small_dark_spots', 'circular_spots', 'dark_borders', 'lighter_gray_centers',
        'surrounding_yellowing', 'concentric_ring_pattern', 'large_irregular_blotches',
        'water_soaked_appearance', 'yellowish_patches', 'olive_brown_surface_growth',
        'mosaic_mottled_green_pattern', 'leaf_curling', 'leaf_narrowing', 'leaf_deformation')
FAMILIES = {'A': 'Lesion count/density', 'B': 'Lesion size', 'C': 'Distribution geometry',
            'D': 'Spatial location', 'E': 'Lesion organization',
            'F': 'Color structure not fully represented',
            'G': 'Surface texture beyond deformation (additional family)'}
LESION_FIELDS = ('lesions_spots', 'overall_summary')
SPATIAL_FIELDS = ('color_pattern', 'lesions_spots', 'distribution', 'overall_summary')
COLOR_FIELDS = ('color_pattern', 'overall_summary')
SURFACE_FIELDS = ('surface_deformation', 'overall_summary')


def rule(family, patterns, fields, rationale, redundancy='low', ambiguity='medium', guard=None):
    return dict(family=family, patterns=patterns, fields=fields, lost_information=rationale,
                redundancy_risk=redundancy, extraction_ambiguity_risk=ambiguity, guard=guard)


# All definitions are fixed text rules, never fitted to class labels. Patterns
# include their object where necessary: 'small areas' is not a small lesion.
RULES = {
    'single_lesion': rule('A', [r'\b(?:single|one)\b[^.;]{0,35}\blesion\b'], LESION_FIELDS,
                          'Explicit singleton count is not encoded by lesion morphology cues.', ambiguity='low'),
    'two_lesions': rule('A', [r'\btwo\b[^.;]{0,50}\b(?:lesions|necrotic areas)\b'], LESION_FIELDS,
                        'Explicit count of two is lost.', ambiguity='low'),
    'few_lesions': rule('A', [r'\bfew\b[^.;]{0,45}\b(?:spots|lesions)\b'], LESION_FIELDS,
                        'Small cardinality is not a cue dimension.'),
    'multiple_lesions': rule('A', [r'\b(?:multiple|several)\b[^.;]{0,60}\b(?:spots|lesions)\b'], LESION_FIELDS,
                             'Multiplicity is not represented by lesion shape/color states.'),
    'numerous_lesions': rule('A', [r'\bnumerous\b[^.;]{0,70}\b(?:spots|lesions)\b'], LESION_FIELDS,
                             'High qualitative count is lost.', ambiguity='low'),
    'dense_lesion_distribution': rule('A', [r'\bdens(?:e|ely)\b[^.;]{0,20}\b(?:lesions|spots|packed)\b'],
                                     ('lesions_spots', 'distribution', 'overall_summary'),
                                     'Density is distinct from lesion type; count and density can overlap.', redundancy='medium'),
    'small_lesion_size': rule('B', [r'\bsmall(?:er)?\b[^.;]{0,65}\b(?:spots?|lesions?)\b'], LESION_FIELDS,
                              'Size independent of dark color is not preserved; small_dark_spots only preserves a conjunction.', redundancy='high'),
    'medium_lesion_size': rule('B', [r'\bmedium(?:-sized)?\b[^.;]{0,55}\b(?:spots?|lesions?)\b',
                                   r'\b(?:spots|lesions)\b[^.;]{0,45}\bsmall to medium\b'], LESION_FIELDS,
                               'Medium size/range is absent from the ontology.', ambiguity='low'),
    'large_lesion_size': rule('B', [r'\blarge\b[^.;]{0,50}\b(?:lesions?|necrotic areas)\b',
                                  r'\blesions\b[^.;]{0,35}\bmostly large\b'], LESION_FIELDS,
                              'Size independent of irregular shape is lost; partly overlaps large_irregular_blotches.', redundancy='high'),
    'mixed_lesion_sizes': rule('B', [r'\b(?:small to medium(?:-sized)?|varying in size|vary in size|vary in shape and size|vary in size and shape|spots of varying size)\b'],
                              LESION_FIELDS, 'Within-image size range is not represented.', redundancy='medium'),
    'scattered_distribution': rule('C', [r'\bscattered\b'], SPATIAL_FIELDS,
                                   'Dispersion is not a cue dimension.', ambiguity='low'),
    'clustered_distribution': rule('C', [r'\bcluster(?:ed|ing|s)\b'], SPATIAL_FIELDS,
                                   'Lesion clustering is not a cue dimension.'),
    'localized_distribution': rule('C', [r'\blocalized\b'], SPATIAL_FIELDS,
                                   'Restricted spatial extent is not represented.', ambiguity='low'),
    'widespread_distribution': rule('C', [r'\bwidespread\b', r'\bcover(?:ing)?\s+(?:most|much)\s+of\b',
                                        r'\bacross\s+the\s+entire\s+leaf\b'], SPATIAL_FIELDS,
                                    'Global coverage/extent is lost.'),
    'diffuse_discoloration': rule('C', [r'\bdiscoloration\b[^.;]{0,25}\bdiffuse\b'], SPATIAL_FIELDS,
                                 'Diffuse discoloration differs from lesion-border diffuseness.'),
    'uneven_distribution': rule('C', [r'\buneven(?:ly)?\b', r'\birregularly distributed\b'],
                                ('distribution', 'overall_summary'),
                                'Uneven spatial distribution is not preserved.', ambiguity='low'),
    'asymmetric_distribution': rule('C', [r'\b(?:right|left)\s+(?:half|side)\b',
                                        r'\bupper right\b', r'\b(?:one-sided|asymmetric)\b'], SPATIAL_FIELDS,
                                    'Image-relative side asymmetry is lost; orientation may be incidental.', ambiguity='high'),
    'margin_associated': rule('D', [r'\b(?:near|along|on|towards?|at|including)\s+(?:the\s+)?(?:leaf\s+)?(?:edges?|margins?)\b',
                                   r'\b(?:leaf )?(?:edges?|margins?)\s+and\s+tips?\b',
                                   r'\b(?:center|central areas|upper half)\s+and\s+(?:the\s+)?(?:leaf\s+)?edges\b'], SPATIAL_FIELDS,
                               'Location of color/lesion changes at margins is not encoded by leaf curling.', ambiguity='medium', guard='spatial'),
    'tip_associated': rule('D', [r'\b(?:near|towards?|along|on)\s+(?:the\s+)?(?:leaf\s+)?tips?\b',
                                r'\b(?:edges?|margins?)\s+and\s+tips?\b'], SPATIAL_FIELDS,
                            'Tip location is distinct from lesion morphology.', guard='spatial'),
    'central_associated': rule('D', [r'\b(?:near|towards?|along|on)\s+(?:the\s+)?(?:leaf\s+)?cent(?:er|re)\b',
                                    r'\bcentral\s+(?:area|part|portion|lesion|discoloration)',
                                    r'\bcentral(?:ly|\s+(?:and\s+upper\s+)?parts)\b',
                                    r'\b(?:upper|lower)\s+(?:and\s+)?central\b',
                                    r'\b(?:center|middle)\b'], SPATIAL_FIELDS,
                                'Leaf-central location is lost; lesion centers must be excluded.', guard='spatial'),
    'upper_leaf_associated': rule('D', [r'\bupper\s+(?:half|parts?|surface|areas?|right)\b',
                                      r'\bupper and central\b'], SPATIAL_FIELDS,
                                 'Upper-leaf location is lost; image orientation can affect wording.', ambiguity='medium', guard='spatial'),
    'lower_leaf_associated': rule('D', [r'\blower\s+(?:half|parts?|sections?|central)\b',
                                      r'\blower\s+and\s+middle\b', r'\bat\s+the\s+bottom\b'], SPATIAL_FIELDS,
                                 'Lower-leaf location is lost.', guard='spatial'),
    'vein_associated': rule('D', [r'\b(?:along|near)\s+(?:the\s+)?veins?\b',
                                 r'\bcentral vein areas\b'], SPATIAL_FIELDS,
                             'Vein-associated location is distinct from mottling itself.', guard='spatial'),
    'interveinal_associated': rule('D', [r'\binterveinal\b', r'\bbetween veins\b'], SPATIAL_FIELDS,
                                  'Interveinal location is not represented.', ambiguity='low', guard='spatial'),
    'single_large_contiguous_lesion': rule('E', [r'\b(?:single|one)\s+large\b[^.;]{0,35}\blesion\b',
                                                r'\bcontiguous\b[^.;]{0,30}\b(?:lesion|necrotic)\b'], LESION_FIELDS,
                                          'Contiguity and singleton organization are not explicitly encoded.', ambiguity='high'),
    'many_discrete_lesions': rule('E', [r'\b(?:many|numerous|multiple)\b[^.;]{0,30}\b(?:discrete|separate|individual)\b[^.;]{0,30}\b(?:spots|lesions)\b'], LESION_FIELDS,
                                'Discreteness requires explicit wording; not inferred from spots or scattered.', redundancy='medium', ambiguity='low'),
    'merging_coalescing_lesions': rule('E', [r'\b(?:merging|coalescing)\b'], LESION_FIELDS,
                                      'Coalescence is not preserved by the resulting blotch cue alone.', redundancy='medium', ambiguity='low'),
    'diffuse_discoloration_without_discrete_lesions': rule('E', [r'\bdiscoloration\b[^.;]{0,25}\bdiffuse\b',
                                                                 r'\bdiscoloration patches\b'],
                                                        ('color_pattern', 'lesions_spots', 'overall_summary'),
                                                        'Diffuse/patch organization plus explicit absence of discrete lesions; text-only relation.',
                                                        redundancy='medium', ambiguity='high', guard='no_discrete'),
    'green_to_yellow_gradient': rule('F', [r'\bgradient from green\b[^.;]{0,55}\bto yellow\b',
                                         r'\bgreen to yellow color gradient\b'], COLOR_FIELDS,
                                     'Directional color transition is lost even when yellow/mosaic cues are present.', ambiguity='low'),
    'green_to_dark_gradient': rule('F', [r'\bgradient from green\b[^.;]{0,45}\bto dark brown\b'], COLOR_FIELDS,
                                   'Directional green-to-dark transition is not encoded.', ambiguity='low'),
    'dark_brown_black_discoloration': rule('F', [r'\b(?:dark brown to black|dark brown and black|dark necrotic|dark)\s+discoloration\b',
                                                r'\bdiscoloration\b[^.;]{0,25}\bdark brown\b'], COLOR_FIELDS,
                                          'Broad discoloration color is not identical to small dark spots or dark borders.', redundancy='medium'),
    'pale_gray_discoloration': rule('F', [r'\b(?:pale|gray(?:ish)?|grey(?:ish)?)\s+discoloration\b',
                                         r'\bareas appearing pale or grayish\b',
                                         r'\bareas\s+appearing\s+pale\s+or\s+grayish\b',
                                         r'\bsome areas appearing pale or grayish\b'], COLOR_FIELDS,
                                     'Non-center pale/gray discoloration is not a pale lesion center.', redundancy='medium'),
    'unpatterned_light_dark_green_contrast': rule('F', [r'\blight(?:er)? green\b', r'\bpale green\b'], COLOR_FIELDS,
                                                'Green tonal contrast without positive mottling wording; existing mosaic cue overlaps.',
                                                redundancy='high', ambiguity='high', guard='no_mottling'),
    'dark_lesion_centers': rule('F', [r'\bdark(?:er)?(?:, almost black)?\s+centers?\b', r'\bcenters appear dark\b'],
                              ('center_border_internal_pattern', 'overall_summary'),
                              'Dark centers are distinct from dark borders and pale centers.', redundancy='medium', ambiguity='low'),
    'light_brown_lesion_margins': rule('F', [r'\blight(?:er)?\s+brown\s+margins?\b', r'\blighter\s+margins?\b'],
                                     ('center_border_internal_pattern', 'overall_summary'),
                                     'Lighter lesion margins are not dark lesion borders.', redundancy='medium'),
    'diffuse_lesion_borders': rule('E', [r'\bdiffuse\s+(?:borders?|edges?)\b'],
                                 ('center_border_internal_pattern', 'overall_summary'),
                                 'Border sharpness is not preserved by dark-border color.', redundancy='medium'),
    'rough_surface_texture': rule('G', [r'\brough(?:ness|ened)?\b'], SURFACE_FIELDS,
                                 'Surface texture is distinct from shape deformation and colored surface growth.', ambiguity='low'),
    'raised_surface_texture': rule('G', [r'\braised\s+(?:areas?|texture|lesion areas)\b', r'\bslightly raised\b'], SURFACE_FIELDS,
                                  'Surface relief is not encoded by leaf deformation alone.', redundancy='medium'),
    'dry_surface_texture': rule('G', [r'\bdry\s+(?:texture|surface)\b'], SURFACE_FIELDS,
                               'Explicit dryness is not a deformation state.', ambiguity='low'),
    'smooth_flat_surface': rule('G', [r'\bsmooth\b', r'\bmostly flat\b'], SURFACE_FIELDS,
                               'Positive smooth/flat texture is distinct from a lack of deformation mention.', ambiguity='low'),
}
NEG = r'\b(?:no|without|lack(?:s|ing)?|not|neither)\b'
WEAK = r'\b(?:faint|slight(?:ly)?|possib(?:le|ly)|unclear|indistinct|subtle|mild|minor|somewhat)\b'
STATES = ('present', 'uncertain', 'not_mentioned')


def split_clauses(text):
    # Separate independent negative/positive predicates; keep coordinated negative
    # lists intact. "fewer" is handled as comparative/uncertain, not biological absence.
    return [s.strip() for s in re.split(r'[.;]|\bbut\b|,\s*(?=(?:no|without|fewer|less)\b)', text) if s.strip()]


def extract(fields):
    """No labels or cue assignments enter extraction."""
    features = {}
    positive_mottling = any(re.search(r'\bmottl\w*|\bmosaic\b', s.lower()) and
                            not re.search(NEG, re.split(r'\bmottl\w*|\bmosaic\b', s.lower())[0])
                            for f in FIELDS for s in split_clauses(fields[f]))
    for name, spec in RULES.items():
        evidence = []
        for field in spec['fields']:
            for snippet in split_clauses(fields[field]):
                lower = snippet.lower()
                for pattern in spec['patterns']:
                    for match in re.finditer(pattern, lower):
                        prefix, suffix = lower[:match.start()], lower[match.end():]
                        neg = bool(re.search(NEG, prefix)) or bool(re.search(r'^\s*(?:is|are)\s+not\s+visible\b', suffix))
                        local_prefix = re.split(r',|\band\b|\bwith\b', prefix)[-1][-35:]
                        weak = bool(re.search(WEAK, local_prefix + ' ' + match.group()))
                        weak |= bool(re.search(r'\bnot (?:clearly|distinctly) visible\b', suffix))
                        weak |= bool(re.match(r'(?:fewer|less)\b', lower))
                        if spec['family'] == 'D':
                            weak |= bool(re.search(r'\b(?:fewer|less)\b[^.;]{0,35}$', prefix))
                        rejected = None
                        if spec['guard'] == 'spatial':
                            # Avoid treating curling/deformation location as lesion/color distribution.
                            if not re.search(r'\b(?:lesions?|spots?|discoloration|yellow(?:ing)?|color|mottl\w*|necrosis|necrotic|patches|damage)\b', lower):
                                rejected = 'location_without_lesion_or_color_subject'
                            if name == 'central_associated' and re.search(r'\b(?:pale|dark|lighter)\s+center\b', lower):
                                rejected = 'lesion_center_not_leaf_center'
                            if name == 'vein_associated' and re.match(r'fewer|less', lower):
                                rejected = 'reduced_presence_near_vein_not_positive_association'
                        if spec['guard'] == 'no_mottling' and positive_mottling:
                            rejected = 'already_described_as_mottling_existing_cue_overlap'
                        corroboration = []
                        if spec['guard'] == 'no_discrete':
                            for f in FIELDS:
                                for s in split_clauses(fields[f]):
                                    if re.search(r'\b(?:no|lacking)\s+(?:distinct\s+)?(?:spots|lesions)', s.lower()):
                                        corroboration.append({'field': f, 'snippet': s})
                            if not corroboration:
                                rejected = 'requires_explicit_no_discrete_lesion_description'
                        state = 'not_mentioned' if neg or rejected else ('uncertain' if weak else 'present')
                        evidence.append({'field': field, 'snippet': snippet, 'matched_text': match.group(),
                                         'pattern': pattern, 'state': state,
                                         'reason': rejected or ('explicit_negative' if neg else 'weak_expression' if weak else 'explicit_positive'),
                                         'corroborating_evidence': corroboration})
        state = next((s for s in STATES[:2] if any(e['state'] == s for e in evidence)), 'not_mentioned')
        features[name] = {'information_family': spec['family'], 'state': state,
                          'canonical_information_loss': state != 'not_mentioned', 'evidence': evidence,
                          'reason': 'matched_evidence' if evidence else 'no_pattern_match_in_applicable_fields'}
    return features


def main():
    raw = {k: p.read_bytes() for k, p in INPUTS.items()}
    rows = [json.loads(s) for s in raw['v2'].decode().splitlines() if s.strip()]
    audit, diag = json.loads(raw['coverage']), json.loads(raw['diagnostic'])
    expected = {f'pv_desc_{i:03d}' for i in range(1, 31)}
    indexed = {}
    for key, records in [('v2', rows), ('coverage', audit['per_image']), ('diagnostic', diag['per_image'])]:
        assert len(records) == 30 and {r['image_id'] for r in records} == expected, key
        indexed[key] = {r['image_id']: r for r in records}
        counts = Counter(r['hidden_ground_truth_class'] for r in records)
        assert len(counts) == 6 and set(counts.values()) == {5}, key
    assert audit['source_sha256'] == hashlib.sha256(raw['v2']).hexdigest()
    assert diag['input_sha256'] == hashlib.sha256(raw['coverage']).hexdigest()
    assert tuple(diag['cue_order']) == CUES
    assert diag['state_mapping'] == {'supported': [1, 0], 'uncertain': [0, 1], 'not_observed': [0, 0]}
    for image_id in sorted(expected):
        v, a, d = (indexed[k][image_id] for k in ('v2', 'coverage', 'diagnostic'))
        assert v['hidden_ground_truth_class'] == a['hidden_ground_truth_class'] == d['hidden_ground_truth_class']
        assert v['experiment_id'] == 'pv_structured_v2_150_field_mean_v1'
        assert set(v['fields']) == set(FIELDS) and all(isinstance(v['fields'][f], str) for f in FIELDS)
        assert set(a['cues']) == set(CUES)
        assert d['vector_28d'] == [x for c in CUES for x in diag['state_mapping'][a['cues'][c]['state']]]
    # Extract every state before using labels for aggregation.
    extracted = [extract({f: row['fields'][f] for f in FIELDS}) for row in rows]
    images = [{'image_id': row['image_id'], 'hidden_ground_truth_class': row['hidden_ground_truth_class'],
               'extracted_non_14d_features': features} for row, features in zip(rows, extracted)]
    classes = sorted(counts)
    overall, per_class, candidates = {}, {}, []
    for name, spec in RULES.items():
        c = Counter(i['extracted_non_14d_features'][name]['state'] for i in images)
        mentioned = c['present'] + c['uncertain']
        overall[name] = {**{s+'_count': c[s] for s in STATES}, 'mentioned_count': mentioned,
                         'mentioned_rate': mentioned/30, 'information_family': spec['family']}
        per_class[name] = {label: {s: sum(i['hidden_ground_truth_class'] == label and
                                        i['extracted_non_14d_features'][name]['state'] == s for i in images)
                                  for s in STATES} for label in classes}
        rates = {label: (v['present']+v['uncertain'])/5 for label, v in per_class[name].items()}
        variation = max(rates.values()) - min(rates.values())
        # Fixed review triage only, not ontology adoption or performance tuning.
        if mentioned >= 6 and spec['redundancy_risk'] == 'low' and spec['extraction_ambiguity_risk'] != 'high':
            recommendation = 'strong_candidate'
        elif mentioned >= 2 and spec['redundancy_risk'] != 'high' and spec['extraction_ambiguity_risk'] != 'high':
            recommendation = 'possible_candidate'
        else:
            recommendation = 'do_not_add_yet'
        candidates.append({'name': name, 'information_family': spec['family'], 'overall_coverage': overall[name],
                           'per_class_pattern': per_class[name], 'per_class_mentioned_rates': rates,
                           'class_rate_range': variation, 'redundancy_risk': spec['redundancy_risk'],
                           'extraction_ambiguity_risk': spec['extraction_ambiguity_risk'],
                           'lost_information_rationale': spec['lost_information'], 'recommendation': recommendation})
    # Coverage first; labels only supply a descriptive tie breaker, never tuning.
    risk = {'low': 0, 'medium': 1, 'high': 2}
    candidates.sort(key=lambda c: (-c['overall_coverage']['mentioned_count'], risk[c['redundancy_risk']],
                                    risk[c['extraction_ambiguity_risk']], -c['class_rate_range'], c['name']))
    for rank, c in enumerate(candidates, 1): c['rank'] = rank
    families = {}
    for family, title in FAMILIES.items():
        names = [n for n, r in RULES.items() if r['family'] == family]
        families[family] = {'name': title, 'images_containing_lost_information': sum(
            any(i['extracted_non_14d_features'][n]['canonical_information_loss'] for n in names) for i in images),
            'total_lost_feature_mentions': sum(overall[n]['mentioned_count'] for n in names),
            'proposed_feature_count': len(names)}
    notable = []
    for c in sorted(candidates, key=lambda c: (-c['class_rate_range'], -c['overall_coverage']['mentioned_count'], c['name']))[:10]:
        rates = c['per_class_mentioned_rates']
        notable.append({'feature': c['name'], 'mentioned_rate_range': c['class_rate_range'],
                        'per_class_mentioned_counts': {k: per_class[c['name']][k]['present']+per_class[c['name']][k]['uncertain'] for k in classes}})
    report = {
        'inputs': {k: {'path': str(INPUTS[k].relative_to(ROOT)), 'sha256': hashlib.sha256(b).hexdigest()} for k, b in raw.items()},
        'validation': {'same_original_30_image_ids': True, 'class_labels_agree': True,
                       'class_counts': dict(sorted(counts.items())), 'images_per_class': 5,
                       'cue_count': 14, 'source_hash_chain_and_28d_states_match': True},
        'existing_cue_order_unchanged': CUES,
        'method': {'rules': RULES, 'fields_inspected': FIELDS, 'states': STATES,
                   'negation_pattern': NEG, 'uncertainty_pattern': WEAK,
                   'aggregation': 'present > uncertain > not_mentioned across fields; negative matches retained as rejected evidence.',
                   'loss_unit': 'One image x feature with present/uncertain state; repeated field mentions counted once.',
                   'loss_scope': 'Information content not independently recoverable from existing 14 cue states; partial overlaps documented, not declared disjoint.',
                   'ranking': 'Descending coverage, then lower redundancy risk, lower ambiguity risk, descending descriptive class-rate range, name.',
                   'recommendation_rule': 'strong: >=6/30, low redundancy, non-high ambiguity; possible: >=2/30, non-high redundancy and ambiguity; otherwise do_not_add_yet. No labels or performance metrics used.',
                   'family_counts': 'Nonexclusive; related features and cross-family overlaps can double-count information units.',
                   'excluded_existing_content': ['Curling, narrowing, deformation and mottling themselves are already represented.',
                                                 'Pale centers, dark borders, halos and rings themselves are already represented.'],
                   'extra_family': 'G records visible surface texture beyond the requested focus families A–F.'},
        'per_image': images, 'overall_coverage': overall, 'per_class_coverage': per_class,
        'information_family_summary': families, 'ranked_candidate_new_dimensions': candidates,
        'notable_descriptive_class_differences': notable,
        'cautions': ['This is a text information-loss inventory and candidate review, not a newly implemented representation.',
                     'Frequent does not mean predictive; class-varying does not mean causal; no field robustness claim.',
                     'not_mentioned includes rejected negatives and unmatched text; it never means biological absence.',
                     'Counts depend on explicit vocabulary, bounded regex scope, and inherited V2 wording, not independent image verification.',
                     'Spatial association does not necessarily mean spatial predominance; reduced-location mentions are weak or rejected.',
                     'No discreteness or contiguity is inferred from the words scattered, lesions, or necrotic areas alone.',
                     'Sizes partially overlap compound existing cues; tonal contrast overlaps mottling and is a high-risk proposal.',
                     'Class profiles use five examples each. Ranking and recommendation are transparent descriptive triage, not validation.',
                     'Negative lists and long-distance hedges can be over-scoped or missed; evidence and rejected matches are retained.'],
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    print('Validation PASS: same 30 original IDs, 6 classes x 5, matching labels, source hashes and unchanged 14-cue/28D states.')
    print('\nLost-information families (nonexclusive image x feature mentions):')
    for f, s in sorted(families.items(), key=lambda pair: -pair[1]['images_containing_lost_information']):
        print(f, s['name'], 'images=', s['images_containing_lost_information'], 'mentions=', s['total_lost_feature_mentions'])
    print('\nTop 15 lost features by coverage:')
    print(f'{"feature":44} {"P":>3} {"U":>3} {"coverage":>8} {"redundancy":>10} {"ambiguity":>10}')
    for c in candidates[:15]:
        o = c['overall_coverage']
        print(f'{c["name"]:44} {o["present_count"]:3} {o["uncertain_count"]:3} {o["mentioned_rate"]:8.1%} {c["redundancy_risk"]:>10} {c["extraction_ambiguity_risk"]:>10}')
    print('\nClass descriptive differences (counts /5; no significance claim):')
    print('Class order:', ', '.join(classes))
    for item in notable: print(item['feature'], list(item['per_class_mentioned_counts'].values()))
    print('\nStrong candidates for review:', ', '.join(c['name'] for c in candidates if c['recommendation'] == 'strong_candidate') or '(none)')
    print('Risks: size/compound-cue and green-contrast/mottling overlap; nonexclusive families; syntax/negation scope; spatial association versus predominance.')
    print('No new representation or accuracy tuning. not_mentioned is not biological absence.')
    print('Output:', OUTPUT.relative_to(ROOT), flush=True)
    print('\nGit status:', flush=True)
    subprocess.run(['git', 'status', '--short'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
