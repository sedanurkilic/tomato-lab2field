"""Offline, text-only coverage audit of the original 30 structured V2 descriptions.

No model inference. Labels are attached only AFTER all text states are assigned.
not_observed means no positive textual support, never biological absence.
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/experiment_results/pv_vlm_description_structured_pilot/descriptions.jsonl'
OUTPUT = ROOT / 'docs/experiment_results/pv_vlm_morphology_cue_audit/coverage_audit.json'
FIELDS = ('color_pattern', 'lesions_spots', 'center_border_internal_pattern',
          'distribution', 'surface_deformation', 'overall_summary')
# Full patterns require explicit attributes; partial patterns retain incomplete
# mentions for inspection, but cannot yield supported. Bounded gaps stay local.
RULES = {
    'small_dark_spots': {
        'full': [r'\bsmall\b[^.;]{0,65}\b(?:dark|black)\b[^.;]{0,25}\b(?:spots?|lesions?)\b'],
        'partial': [r'\b(?:dark|black)\b[^.;]{0,25}\b(?:spots?|lesions?)\b']},
    'circular_spots': {
        'full': [r'\b(?:circular|round|rounded)\b[^.;]{0,30}\b(?:spots?|lesions?)\b'], 'partial': []},
    'dark_borders': {
        'full': [r'\bdark(?:er)?(?:[- ]bordered\b|[^.;]{0,30}\b(?:borders?|margins?)\b)'], 'partial': []},
    'lighter_gray_centers': {
        'full': [r'\b(?:pale|gray(?:ish)?|grey(?:ish)?|light(?:er)?)\b(?: or (?:gray(?:ish)?|grey(?:ish)?))?\s+cent(?:er|re)s?\b'],
        'partial': [r'\b(?:paler|pale brown|pale, yellowish)\s+centers?\b']},
    'surrounding_yellowing': {
        'full': [r'\byellow(?:ish)?\s+halos?\b', r'\byellow\s+discoloration\s+around\s+lesions\b'],
        'partial': [r'\byellow(?:ing|ish)?\b']},
    'concentric_ring_pattern': {
        'full': [r'\bconcentric\s+(?:lesion\s+)?(?:rings?|patterns?)\b', r'\btarget[- ]like\b', r'\btarget\s+patterns?\b'], 'partial': []},
    'large_irregular_blotches': {
        'full': [r'\blarge\s+irregular[^.;]{0,45}\b(?:lesions?|areas?|blotches)\b',
                 r'\birregular[^.;]{0,45}\blarge\b[^.;]{0,25}\bcoalescing\b',
                 r'\birregular[^.;]{0,65}\blarger\s+blotches\b'],
        'partial': [r'\b(?:larger\s+blotches|irregular[^.;]{0,25}\bblotches)\b']},
    'water_soaked_appearance': {'full': [r'\bwater[- ]soaked\b', r'\bwatery\b'], 'partial': []},
    'yellowish_patches': {
        'full': [r'\b(?:yellow(?:ish)?|yellowish-brown|yellow-brown)\b[^.;]{0,45}\b(?:patches|areas|blotches)\b',
                 r'\bpatches\b[^.;]{0,20}\byellow(?:ish)?\b'],
        'partial': [r'\byellow(?:ing|ish)?\b']},
    'olive_brown_surface_growth': {
        'full': [r'\b(?:olive|brown)\b[^.;]{0,35}\b(?:growth|mold|mould|coating)\b'],
        'partial': [r'\bvelvety\s+(?:growth|areas?)\b']},
    'mosaic_mottled_green_pattern': {
        'full': [r'\bmosaic(?:-like)?\b', r'\bmottled\b[^.;]{0,70}\bgreen\b',
                 r'\bgreen\b[^.;]{0,45}\bmottl(?:ing|ed)\b'],
        'partial': [r'\bmottl(?:ed|ing)\b']},
    'leaf_curling': {'full': [r'\bcurl(?:ed|ing)?\b', r'\b(?:edges?|margins?)\s+(?:are\s+)?rolled\s+inward\b'], 'partial': []},
    'leaf_narrowing': {'full': [r'\bnarrow(?:ed|ing)\b'], 'partial': []},
    'leaf_deformation': {
        'full': [r'\bdeform(?:ation|ed)\b', r'\b(?:wrinkl(?:ed|ing)|puckering|shriveled)\b'],
        'partial': [r'\b(?:edges?|margins?)\b[^.;]{0,25}\birregular\b']},
}
STATES = ('supported', 'uncertain', 'not_observed')
NEG_PREFIX = r'\b(?:no|without|lack(?:s|ing)?|do not|does not|not)\b'
WEAK = r'\b(?:faint|slight(?:ly)?|possib(?:le|ly|ility)|unclear|indistinct|subtle|mild|minor|somewhat)\b'


def audit_fields(fields):
    """Accept only the six fields: class and disease knowledge are inaccessible."""
    result = {}
    for cue, rule in RULES.items():
        evidence = []
        for field in FIELDS:
            # Keep coordinated lists together so 'no X, Y, or Z' negates Z too.
            for clause in re.split(r'[.;]|\bbut\b', fields[field]):
                text = clause.strip()
                lower = text.lower()
                if not text:
                    continue
                for kind in ('full', 'partial'):
                    for pattern in rule[kind]:
                        for match in re.finditer(pattern, lower):
                            prefix, suffix = lower[:match.start()], lower[match.end():]
                            # A negative governing the coordinated clause wins
                            # over hedges ('no clear', 'not clearly visible').
                            neg = bool(re.search(NEG_PREFIX, prefix))
                            neg |= bool(re.search(r'\b(?:are|is) not visible\b', suffix))
                            local_prefix = re.split(r',|\band\b|\bwith\b', prefix)[-1][-30:]
                            weak = bool(re.search(WEAK, local_prefix + ' ' + match.group()))
                            weak |= bool(re.search(r'\b(?:unclear|indistinct|not (?:clearly|distinctly) visible)\b', suffix))
                            state = 'not_observed' if neg else ('uncertain' if weak or kind == 'partial' else 'supported')
                            item = {'field': field, 'snippet': text, 'matched_text': match.group(),
                                    'pattern': pattern, 'match_kind': kind, 'state': state,
                                    'reason': 'explicit_negative' if neg else ('weak_or_partial' if state == 'uncertain' else 'explicit_positive')}
                            if item not in evidence:
                                evidence.append(item)
        state = next((s for s in STATES[:2] if any(e['state'] == s for e in evidence)), 'not_observed')
        result[cue] = {'state': state, 'evidence': evidence,
                       'reason': 'matched_evidence' if evidence else 'no_vocabulary_match_in_six_fields'}
    return result


def main():
    raw = SOURCE.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    assert len(rows) == 30, f'Expected 30 records, got {len(rows)}'
    assert {r['image_id'] for r in rows} == {f'pv_desc_{i:03d}' for i in range(1, 31)}
    for row in rows:
        assert row['experiment_id'] == 'pv_structured_v2_150_field_mean_v1'
        assert row['completed'] is True and row['parse_valid'] is True and row['validation_pass'] is True
        assert set(row['fields']) == set(FIELDS)
        assert all(isinstance(row['fields'][f], str) and row['fields'][f].strip() for f in FIELDS)
    # Complete every assignment before accessing labels, including preflight counts.
    assignments = [audit_fields({f: r['fields'][f] for f in FIELDS}) for r in rows]
    classes = Counter(r['hidden_ground_truth_class'] for r in rows)
    assert len(classes) == 6 and set(classes.values()) == {5}, classes
    images = [{'image_id': r['image_id'], 'hidden_ground_truth_class': r['hidden_ground_truth_class'], 'cues': cues}
              for r, cues in zip(rows, assignments)]
    overall, per_class = {}, {}
    for cue in RULES:
        counts = Counter(i['cues'][cue]['state'] for i in images)
        seen = counts['supported'] + counts['uncertain']
        flags = []
        if seen / 30 >= .30: flags.append('frequent')
        if 0 < seen / 30 < .10: flags.append('rare')
        if seen <= 1: flags.append('almost_never_observed')
        if counts['uncertain'] > counts['supported']: flags.append('mostly_uncertain')
        overall[cue] = {**{s + '_count': counts[s] for s in STATES},
                        'supported_rate': counts['supported'] / 30,
                        'supported_or_uncertain_rate': seen / 30, 'coverage_flags': flags}
        per_class[cue] = {label: {s: sum(i['cues'][cue]['state'] == s for i in images
                                              if i['hidden_ground_truth_class'] == label) for s in STATES}
                          for label in sorted(classes)}
    ranked = sorted(RULES, key=lambda c: -overall[c]['supported_or_uncertain_rate'])
    least = sorted(RULES, key=lambda c: overall[c]['supported_or_uncertain_rate'])[:5]
    mostly = [c for c in RULES if 'mostly_uncertain' in overall[c]['coverage_flags']]
    report = {
        'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'validation': {'record_count': 30, 'class_count': 6, 'images_per_class': 5,
                       'class_counts': dict(sorted(classes.items())), 'expected_v2_schema_pass': True,
                       'original_development_ids_pass': True},
        'method': {'fields': FIELDS, 'rules': RULES, 'negative_prefix_pattern': NEG_PREFIX,
                   'weak_pattern': WEAK, 'aggregation_precedence': list(STATES),
                   'no_match_evidence': 'Empty evidence means all six fields were scanned without a vocabulary match.',
                   'flags': {'frequent': 'supported+uncertain >= 30%', 'rare': '0 < supported+uncertain < 10%',
                             'almost_never_observed': 'supported+uncertain <= 1/30', 'mostly_uncertain': 'uncertain > supported'},
                   'ranking': 'supported+uncertain rate; ties retain requested cue order'},
        'cautions': [
            'Coverage measures representation in existing V2 text only, not biological absence, pathology importance, or classification utility.',
            'Partial composite cues are uncertain: e.g. dark lesions without explicit small size, yellowing without explicit halo/patch geometry.',
            'Pale/light centers are accepted as lighter centers; pale brown or yellowish centers alone are partial, not gray-center support.',
            'Leaf deformation includes explicit wrinkling, puckering and shriveling; irregular margins alone are partial.',
            'Clause negation is conservative and can over-scope coordinated statements; local hedges can miss long-distance modifiers.',
            'Positive evidence takes precedence over uncertain and negative mentions across fields; inspect evidence for contradictions.',
            'Bounded keyword gaps may associate attributes with different objects; this first-pass audit does not resolve syntax or inspect images.'
        ],
        'per_image': images, 'overall_cue_coverage': overall, 'per_class_coverage': per_class,
        'summary': {'most_observed_5': ranked[:5], 'least_observed_5': least, 'mostly_uncertain': mostly},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print('Validated: 30 original V2 records; 6 classes x 5 images; six-field schema passed.')
    print(f'{"cue":36} {"supported":>9} {"uncertain":>9} {"not_obs":>8} {"S+U %":>7}')
    for cue, c in overall.items():
        print(f'{cue:36} {c["supported_count"]:9} {c["uncertain_count"]:9} {c["not_observed_count"]:8} {100*c["supported_or_uncertain_rate"]:7.1f}')
    print('Most observed:', ', '.join(ranked[:5]))
    print('Least observed:', ', '.join(least))
    print('Mostly uncertain:', ', '.join(mostly) or 'none')
    print('Text representation only; not_observed does not mean biological absence.')
    print('Output:', OUTPUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
