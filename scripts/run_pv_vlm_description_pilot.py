"""Thirty-image PV-train description pilot; fixed file prompt, no embeddings/training."""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / 'data/pv_vlm_description_prompt.txt'
OUT = ROOT / 'docs/experiment_results/pv_vlm_description_pilot'
DEFAULT_MODEL = 'gpt-4.1-mini'
# Output screening only: none of these labels or terms is sent to the model.
LEAKAGE = re.compile(
    r'\b(?:bacterial\s+spot|early\s+blight|late\s+blight|leaf\s+mou?ld|septoria|'
    r'tomato\s+mosaic|mosaic\s+virus|target\s+spot|leaf\s+curl\s+virus|'
    r'xanthomonas|alternaria|phytophthora|cladosporium|passalora|fulvia|'
    r'lycopersici|infestans|solani|tobamovirus|pathogen|virus|viral|bacterial|fungal|'
    r'fungus|fungi|blight|disease|infection|infected)\b', re.I)
DIAGNOSIS = re.compile(r'\b(?:diagnos\w*|suffers?\s+from|caused\s+by|indicative\s+of|'
                       r'consistent\s+with|symptom\w*\s+of|suggestive\s+of)\b', re.I)


def validate(text):
    words = len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b", text))
    leakage = bool(LEAKAGE.search(text))
    errors = []
    if not text.strip(): errors.append('empty_output')
    if words > 50: errors.append('over_50_words')
    if leakage: errors.append('disease_pathogen_or_diagnostic_term')
    if DIAGNOSIS.search(text): errors.append('explicit_diagnosis_language')
    # Conservative structural check; language correctness remains manual review.
    if '\n' in text.strip() or len(re.split(r'[.!?]+\s+(?=[A-Z])', text.strip())) != 1:
        errors.append('not_one_sentence')
    if not re.search(r'[A-Za-z]', text): errors.append('no_english_text')
    return {'validation_pass': not errors, 'word_count': words,
            'leakage': leakage, 'errors': errors}


def sample_train():
    classes = json.loads((ROOT / 'manifests/primary_class_set.json').read_text())['canonical_classes']
    if len(classes) != 6: raise ValueError('Expected six frozen classes')
    with (ROOT / 'manifests/primary_split_manifest.csv').open(newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['dataset'] == 'plantvillage'
                and r['split'] == 'train' and r['primary_included'].lower() == 'true']
    rng = random.Random(42)
    sample = []
    for i, name in enumerate(classes, 1):
        pool = sorted([r for r in rows if r['canonical_label'] == name], key=lambda r:r['image_id'])
        if not pool: raise ValueError('No PV-train candidate for a frozen class')
        row = dict(rng.choice(pool), neutral_id=f'pv_desc_{i:03d}')
        path = (ROOT / row['relative_path']).resolve()
        assert path.is_relative_to((ROOT / 'data/processed/tomato_plantvillage').resolve())
        assert path.is_file()
        sample.append(row)
    # Preserve the original six choices and neutral IDs exactly, then add four
    # distinct images per class using the same seeded generator state.
    first_six = list(sample)
    for first in first_six:
        pool = sorted([r for r in rows if r['canonical_label'] == first['canonical_label']
                       and r['image_id'] != first['image_id']], key=lambda r:r['image_id'])
        for selected in rng.sample(pool, 4):
            sample.append(dict(selected, neutral_id=f'pv_desc_{len(sample)+1:03d}'))
    assert len({r['image_id'] for r in sample}) == 30
    for row in sample:
        path = (ROOT / row['relative_path']).resolve()
        assert path.is_relative_to((ROOT / 'data/processed/tomato_plantvillage').resolve()) and path.is_file()
    return sample


def encode_image(path):
    from PIL import Image, ImageOps
    with Image.open(path) as original:
        original_size = list(original.size)
        image = ImageOps.exif_transpose(original).convert('RGB')
        clean = Image.frombytes('RGB', image.size, image.tobytes())
        memory = io.BytesIO()
        clean.save(memory, format='PNG')
    return memory.getvalue(), original_size, list(clean.size)


def request_payload(prompt, neutral_id, image, model, sample):
    assert re.fullmatch(r'pv_desc_0(?:0[1-9]|[12][0-9]|30)', neutral_id)
    # Prompt bytes are decoded unchanged; neutral ID is a separate text part.
    for row in sample:
        path = Path(row['relative_path'])
        for forbidden in [row['canonical_label'], row['original_label'], row['relative_path'],
                          row['image_id'], path.name, path.parent.name]:
            assert forbidden.lower() not in prompt.lower(), 'Label/path leakage in prompt'
    names = r'\b(?:bacterial spot|early blight|late blight|leaf mold|septoria|tomato mosaic virus|xanthomonas|alternaria|phytophthora|cladosporium|passalora|fulvia)\b'
    assert not re.search(names, prompt, re.I), 'Disease/pathogen name in source prompt; refusing request'
    return {'model':model, 'temperature':0, 'store':False,
            'input':[{'role':'user','content':[
                {'type':'input_text','text':prompt},
                {'type':'input_text','text':neutral_id},
                {'type':'input_image','image_url':'data:image/png;base64,' + base64.b64encode(image).decode('ascii')}
            ]}]}


def main():
    model = os.environ.get('OPENAI_MODEL',DEFAULT_MODEL).strip()
    if model != DEFAULT_MODEL: raise ValueError('This experiment requires gpt-4.1-mini')
    raw_prompt = PROMPT.read_bytes()
    prompt = raw_prompt.decode('utf-8')
    sample = sample_train()
    previous, previous_details = {}, {}
    if (OUT/'descriptions.csv').exists():
        old_summary = json.loads((OUT/'summary.json').read_text())
        if old_summary['prompt_sha256'] != hashlib.sha256(raw_prompt).hexdigest():
            raise ValueError('Frozen prompt hash differs from existing experiment')
        previous_details = {d['image_id']:d for d in old_summary['details']}
        with (OUT/'descriptions.csv').open(newline='') as f:
            for row in csv.DictReader(f):
                if row['image_id'] in previous: raise ValueError('Duplicate existing ID')
                previous[row['image_id']] = row
    reusable = {}
    for row in sample:
        old = previous.get(row['neutral_id'])
        detail = previous_details.get(row['neutral_id'], {})
        if old:
            if detail.get('source_image_id') != row['image_id'] or old['hidden_ground_truth_class'] != row['canonical_label']:
                raise ValueError('Existing neutral/source/class identity mismatch')
            if old['model'] != model: raise ValueError('Existing model mismatch')
            if old['validation_pass'].lower()=='true' and detail.get('completed') and validate(old['description'])['validation_pass']:
                reusable[row['neutral_id']] = old
    key = os.environ.get('OPENAI_API_KEY','').strip()
    pending = len(sample)-len(reusable)
    if pending and not key:
        print(f'Error: OPENAI_API_KEY is not set; {len(reusable)} descriptions reusable, {pending} pending. Existing outputs unchanged.',file=sys.stderr)
        return 2
    from openai import OpenAI
    results, details = [], []
    client = OpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=60.0) if pending else None
    try:
        for row in sample:
            if row['neutral_id'] in reusable:
                results.append(reusable[row['neutral_id']])
                details.append(dict(previous_details[row['neutral_id']], reused=True))
                continue
            description, version, completed = '', None, False
            detail = {'image_id':row['neutral_id'], 'source_image_id':row['image_id']}
            try:
                image, original_size, sent_size = encode_image(ROOT / row['relative_path'])
                detail.update(original_resolution=original_size,sent_resolution=sent_size)
                assert original_size == [256,256] and sent_size == [256,256], "Expected original 256x256 PV input"
                response = client.responses.create(**request_payload(prompt,row['neutral_id'],image,model,sample))
                version = response.model
                description = response.output_text or ''  # raw output, never rewritten
                completed = response.status == 'completed'
                detail.update(raw_response=description,response_id=response.id,response_status=response.status)
            except AssertionError:
                raise  # Privacy assertion failure aborts rather than dispatching further requests.
            except Exception as exc:
                status = getattr(exc,'status_code',None)
                detail.update(error_type=type(exc).__name__,http_status=status if isinstance(status,int) else None,
                              error='Request or local image preparation failed; sensitive error details suppressed')
            checks = validate(description)
            if not completed:
                checks['errors'].append('inference_not_completed')
                checks['validation_pass'] = False
            detail.update(completed=completed,model_version=version,**checks)
            details.append(detail)
            results.append({'image_id':row['neutral_id'],'hidden_ground_truth_class':row['canonical_label'],
                            'description':description,'model':model,'model_version':version,
                            'validation_pass':checks['validation_pass']})
    finally:
        if client is not None: client.close()
    if PROMPT.read_bytes() != raw_prompt: raise ValueError('Prompt changed during inference')
    summary = {'prompt_source_path':str(PROMPT.relative_to(ROOT)),
               'prompt_sha256':hashlib.sha256(raw_prompt).hexdigest(),'provider':'OpenAI','model':model,
               'model_version':sorted({d['model_version'] for d in details if d['model_version']}),
               'sample_count':30,'seed':42,'per_class_count':{r['canonical_label']:5 for r in sample},
               'reused_count':len(reusable), 'new_inference_completed_count':sum(d['completed'] and not d.get('reused') for d in details),
               'completed_count':sum(d['completed'] for d in details),
               'validation_pass_count':sum(d['validation_pass'] for d in details),
               'leakage_count':sum(d['leakage'] for d in details),
               'word_limit_violation_count':sum(d['word_count']>50 for d in details),
               'failure_count':sum(not d['validation_pass'] for d in details),
               'warnings':['Lexical leakage and sentence/language screening are conservative; manual review remains necessary.'],
               'details':details}
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'descriptions.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    if summary['completed_count']==30:
        with (ROOT/'research_log.md').open('a') as log:
            log.write('\n- PV description pilot: '+json.dumps({k:summary[k] for k in ['model','model_version','prompt_sha256','completed_count','validation_pass_count','leakage_count','failure_count']})
                      +'; fixed label-blind file prompt; 30 PV-train images (5/class), seed 42; original-resolution input, no disease labels in requests, no embedding, no training, no PlantDoc. Descriptions require manual review.\n')
    print(json.dumps(summary,indent=2))
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'Error: {type(exc).__name__}; no sensitive exception details displayed.',file=sys.stderr)
        sys.exit(1)
