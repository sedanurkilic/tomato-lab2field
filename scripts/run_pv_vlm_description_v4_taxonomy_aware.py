"""V4 taxonomy-aware evidence-summary candidate on the frozen 30-image development set.

--preflight never sends API requests, encodes texts, or writes result files.
--run requires a fresh V4 namespace; no silent reuse/overwrite of cached outputs.
--embed-only validates prompt/schema/sample/model provenance before encoding.
The previous 60-image confirmation set is never loaded by this script.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

from run_pv_vlm_description_pilot import DIAGNOSIS, encode_image
from run_pv_vlm_description_structured_pilot import load_sample
from run_pv_vlm_semantic_confirmation import diagnostics
from siglip_text_encoding import ENCODING_RULE, encode_texts_lossless

ROOT=Path(__file__).resolve().parents[1]
PROMPT=ROOT/'data/pv_vlm_description_prompt_v4_taxonomy_aware.txt'
OUT=ROOT/'docs/experiment_results/pv_vlm_description_v4_taxonomy_aware'
ARTIFACT=ROOT/'artifacts/pv_vlm_description_v4_taxonomy_aware/semantic_embeddings_siglip.pt'
V1=ROOT/'docs/experiment_results/pv_vlm_description_pilot'
V2=ROOT/'docs/experiment_results/pv_vlm_description_structured_pilot'
MODEL='gpt-4.1-mini'
ENCODER='google/siglip-base-patch16-224'
REVISION='7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed'
CANDIDATE='evidence_summary'
EXPERIMENT='pv_v4_taxonomy_aware_morphology_only_development'
PROMPT_VERSION='V4-taxonomy-aware-morphology-only'
FROZEN_PROMPT_SHA256='ecee01ce0f90e89392b4a20daaa8ecf1d1146017b5cf5117ad040e2d16528d4b'
SCHEMA_NAME='pv_v4_taxonomy_aware_morphology'
SCHEMA_VERSION='2'
FIELDS=['color_pattern','lesions_spots','center_border_internal_pattern','distribution','surface_deformation',CANDIDATE]
SCHEMA={'type':'object','properties':{k:{'type':'string'} for k in FIELDS},'required':FIELDS,'additionalProperties':False}


def digest(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Named diseases/pathogens only: generic spots, blotches, mosaic-like, mold-like,
# disease, viral/bacterial/fungal adjectives are NOT class-name leakage.
DISEASE_NAME = re.compile(
    r'\b(?:bacterial[ -]+spot|early[ -]+blight|late[ -]+blight|leaf[ -]+mou?ld|'
    r'septoria(?:[ -]+leaf[ -]+spot)?|(?:tomato[ -]+)?mosaic[ -]+virus|'
    r'xanthomonas|alternaria|phytophthora|cladosporium|passalora|fulvia|'
    r'lycopersici|infestans|solani|tobamovirus)\b', re.I)
META_COMMENTARY = re.compile(
    r'\b(?:classif\w*|diagnos\w*|differenti\w*|distinguish\w*|'
    r'downstream(?:\s+task)?|useful\w*|usefulness|disease\s+categor(?:y|ies))\b', re.I)


def validate_raw(raw,sample=None):
    """JSON/schema validation first; preserve safely parsed failed data for audit."""
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    result={'raw_response':raw,'fields':None,'parse_valid':False,'validation_pass':False,
            'total_word_count':None,'evidence_summary_word_count':None,
            'disease_name_leakage':False,'source_leakage':False,'leakage':False,
            'meta_commentary':False,'explicit_diagnosis':False,'errors':[]}
    try:
        value=json.loads(raw,object_pairs_hook=unique)
    except (ValueError,TypeError) as exc:
        return dict(result,errors=['json_validation_failed:'+type(exc).__name__])
    # Valid JSON dictionaries can safely be retained even if the schema fails.
    # Raw response remains authoritative for malformed JSON/duplicate keys.
    if isinstance(value,dict):result['fields']=value
    else:result['parsed_output']=value
    try:
        from pydantic import ConfigDict,create_model
        schema_model=create_model(SCHEMA_NAME,__config__=ConfigDict(extra='forbid',strict=True),**{k:(str,...) for k in FIELDS})
        fields=schema_model.model_validate(value,strict=True).model_dump()
    except Exception as exc:
        return dict(result,errors=['schema_validation_failed:'+type(exc).__name__])
    text='\n'.join(fields[k] for k in FIELDS)
    count=sum(len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",fields[k])) for k in FIELDS)
    summary_count=len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",fields[CANDIDATE]))
    disease_leakage=bool(DISEASE_NAME.search(text))
    source_leakage=bool(re.search(r'plantvillage_[0-9a-f]+|pv_desc_\d+|data/(?:raw|processed)/|/Users/|file://|\b[\w.-]+\.(?:jpe?g|png|webp|bmp)\b',text,re.I))
    for row in sample or []:
        for forbidden in [row['canonical_label'],row['original_label'],row['relative_path'],row['image_id'],Path(row['relative_path']).name,Path(row['relative_path']).parent.name]:
            if forbidden.lower() in text.lower():source_leakage=True
    meta=bool(META_COMMENTARY.search(fields[CANDIDATE]))
    diagnosis=bool(DIAGNOSIS.search(text))
    leakage=disease_leakage or source_leakage;errors=[]
    if count>200:errors.append('over_200_words')
    if summary_count>45:errors.append('evidence_summary_over_45_words')
    if any(not fields[k].strip() for k in FIELDS):errors.append('empty_field')
    if disease_leakage:errors.append('disease_or_pathogen_name_leakage')
    if source_leakage:errors.append('source_class_path_or_filename_leakage')
    if diagnosis:errors.append('explicit_diagnosis_language')
    if meta:errors.append('meta_commentary')
    return dict(result,fields=fields,parse_valid=True,validation_pass=not errors,total_word_count=count,
                evidence_summary_word_count=summary_count,disease_name_leakage=disease_leakage,
                source_leakage=source_leakage,leakage=leakage,meta_commentary=meta,
                explicit_diagnosis=diagnosis,errors=errors)


def protocol(sample,classes):
    if digest(PROMPT)!=FROZEN_PROMPT_SHA256:
        raise RuntimeError('Frozen V4 prompt hash mismatch; prompt revision is not permitted')
    return {'experiment_id':EXPERIMENT,'prompt_source_path':str(PROMPT.relative_to(ROOT)),
            'prompt_sha256':digest(PROMPT),'schema_name':SCHEMA_NAME,'schema_version':SCHEMA_VERSION,'schema':SCHEMA,
            'model':MODEL,'word_limit':200,'evidence_summary_word_limit':45,'prompt_version':PROMPT_VERSION,'prompt_frozen':True,'candidate_representation':CANDIDATE,'encoder':ENCODER,
            'encoder_revision':REVISION,'encoding_rule':ENCODING_RULE,'class_order':classes,
            'sample_count':30,'per_class_counts':{c:5 for c in classes},'sample_design_seed':42,'resampling':False,
            'development_sample':[{'image_id':r['neutral_id'],'source_image_id':r['image_id'],'hidden_ground_truth_class':r['canonical_label']} for r in sample],
            'discipline':'Development candidate only; do not tune on the previous 60-image confirmation set. Entirely new unseen PV-train confirmation required if pursued; no PlantDoc or significance claim.'}


def build_request(prompt,image,row,sample):
    """Only the exact fixed ontology and image bytes enter dynamic content."""
    import base64
    assert prompt==PROMPT.read_text() and digest(PROMPT)==FROZEN_PROMPT_SHA256, 'Frozen ontology prompt altered'
    schema_text=json.dumps(SCHEMA)
    outgoing_text=prompt+'\n'+schema_text
    for item in sample:
        for forbidden in [item['canonical_label'],item['original_label'],item['relative_path'],item['image_id'],Path(item['relative_path']).name,Path(item['relative_path']).parent.name]:
            assert forbidden.lower() not in outgoing_text.lower(),'Dynamic ground-truth/source leakage'
    # Fixed disease names in the ontology are allowed, never added per image.
    content=[{'type':'input_text','text':prompt},
             {'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(image).decode('ascii')}]
    assert len(content)==2 and [p['type'] for p in content]==['input_text','input_image']
    return {'model':MODEL,'temperature':0,'store':False,'input':[{'role':'user','content':content}],
            'text':{'format':{'type':'json_schema','name':SCHEMA_NAME,'strict':True,'schema':SCHEMA}}}


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def save_records(records):
    OUT.mkdir(parents=True,exist_ok=True)
    temporary=OUT/'descriptions.jsonl.tmp';temporary.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in records));temporary.replace(OUT/'descriptions.jsonl')


def summary_for(records,design):
    return {'protocol':design,'status':'generated_not_embedded',
            'returned_model_versions':sorted({r['model_version'] for r in records if r['model_version']}),
            'completed_count':sum(r['completed'] for r in records),'pending_count':30-len(records),
            'parse_success_count':sum(r['parse_valid'] for r in records),'parse_success_rate':sum(r['parse_valid'] for r in records)/30,
            'validation_pass_count':sum(r['validation_pass'] for r in records),'leakage_count':sum(r['leakage'] for r in records),
            'disease_name_leakage_count':sum(r.get('disease_name_leakage',False) for r in records),
            'source_leakage_count':sum(r.get('source_leakage',False) for r in records),
            'meta_commentary_count':sum(r.get('meta_commentary',False) for r in records),
            'explicit_diagnosis_count':sum(r.get('explicit_diagnosis',False) for r in records),
            'total_word_limit_violation_count':sum((r['total_word_count'] or 0)>200 for r in records),
            'evidence_summary_word_limit_violation_count':sum((r.get('evidence_summary_word_count') or 0)>45 for r in records),
            'word_limit_violation_count':sum((r['total_word_count'] or 0)>200 or (r.get('evidence_summary_word_count') or 0)>45 for r in records),
            'failure_count':sum(not r['validation_pass'] for r in records)}


def infer(sample,design,prompt):
    if any(p.exists() for p in [OUT/'descriptions.jsonl',OUT/'summary.json',ARTIFACT]):
        raise RuntimeError('Existing V4 output detected; refusing silent reuse/overwrite. Use --embed-only for matching successful outputs.')
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key:raise RuntimeError('OPENAI_API_KEY is not set; no request sent')
    from openai import OpenAI
    records=[]
    with OpenAI(api_key=key,base_url='https://api.openai.com/v1',timeout=60.0,max_retries=0) as client:
        for row in sample:
            record={'image_id':row['neutral_id'],'source_image_id':row['image_id'],'hidden_ground_truth_class':row['canonical_label'],
                    'model':MODEL,'model_version':None,'experiment_id':EXPERIMENT,'prompt_sha256':design['prompt_sha256'],
                    'schema_version':SCHEMA_VERSION,'completed':False,'raw_response':''}
            try:
                image,original,sent=encode_image(ROOT/row['relative_path']);assert original==sent==[256,256]
                response=client.responses.create(**build_request(prompt,image,row,sample))
                record.update(raw_response=response.output_text or '',model_version=response.model,response_id=response.id,completed=response.status=='completed')
            except AssertionError:raise
            except Exception as exc:
                code=getattr(exc,'status_code',None);record.update(error_type=type(exc).__name__,http_status=code if isinstance(code,int) else None)
            record.update(validate_raw(record['raw_response'],sample))
            if not record['completed']:record['validation_pass']=False;record['errors'].append('inference_not_completed')
            records.append(record);save_records(records);write_json(OUT/'summary.json',summary_for(records,design))
    return records


def load_valid_records(sample,design):
    previous=json.loads((OUT/'summary.json').read_text())
    if previous['protocol']!=design:raise RuntimeError('V4 prompt/schema/sample/model provenance mismatch')
    records=[json.loads(line) for line in (OUT/'descriptions.jsonl').read_text().splitlines() if line.strip()]
    if len(records)!=30 or len({r['image_id'] for r in records})!=30:raise RuntimeError('Need 30 unique records')
    byid={r['image_id']:r for r in records};ordered=[]
    for row in sample:
        record=byid[row['neutral_id']]
        if record['source_image_id']!=row['image_id'] or record['hidden_ground_truth_class']!=row['canonical_label'] or record['prompt_sha256']!=design['prompt_sha256'] or record['model']!=MODEL or record['experiment_id']!=EXPERIMENT or record['schema_version']!=SCHEMA_VERSION:
            raise RuntimeError('V4 record identity/provenance mismatch')
        checked=validate_raw(record['raw_response'],sample)
        if checked['fields']!=record['fields'] or not checked['validation_pass'] or not record['completed']:
            raise RuntimeError('Invalid V4 record; no repair or imputation')
        ordered.append(dict(record,**checked))
    return ordered


def embed_and_diagnose(records,sample,classes,design,cache_dir):
    if len(records)!=30 or not all(r['completed'] and r['validation_pass'] for r in records):
        raise RuntimeError('Need 30 completed valid V4 descriptions')
    import torch,transformers
    from transformers import AutoTokenizer,SiglipTextModel
    torch.manual_seed(0);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    options={'revision':REVISION,'cache_dir':cache_dir}
    tokenizer=AutoTokenizer.from_pretrained(ENCODER,**options)
    encoder,loading=SiglipTextModel.from_pretrained(ENCODER,output_loading_info=True,**options)
    if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):raise RuntimeError('Incomplete encoder checkpoint')
    encoder=encoder.to('cpu',dtype=torch.float32).eval();encoder.requires_grad_(False)
    assert encoder.config.max_position_embeddings==64 and tokenizer.num_special_tokens_to_add(pair=False)==1
    texts=[r['fields'][CANDIDATE] for r in records]  # ONLY this preselected field
    embeddings,chunks=encode_texts_lossless(texts,tokenizer,encoder)
    assert embeddings.shape==(30,768)
    ids=[r['neutral_id'] for r in sample];labels=[r['canonical_label'] for r in sample]
    result=diagnostics(embeddings,labels,classes,ids)
    for record,info in zip(records,chunks):
        record['evidence_summary_token_chunk_diagnostics']=info
    save_records(records)
    v1=json.loads((V1/'embedding_summary.json').read_text())
    v2=json.loads((V2/'summary.json').read_text())['diagnostics']
    fields=json.loads((V2/'field_diagnostics.json').read_text())
    v2_summary=next(r for r in fields['single_field_results'] if r['name']=='overall_summary')
    old_v1=v1['leave_one_out_class_prototype_diagnostic']
    v3=json.loads((ROOT/'docs/experiment_results/pv_vlm_description_v3_discriminative/summary.json').read_text())['diagnostics']
    baseline={'v3_discriminative_summary':{k:v3[k] for k in ['cosine_gap','accuracy','macro_f1','balanced_accuracy']},'v1_free_form':{'cosine_gap':v1['same_class_cosine']['mean']-v1['different_class_cosine']['mean'],**{k:old_v1[k] for k in ['accuracy','macro_f1','balanced_accuracy']}},
              'v2_overall_summary':{k:v2_summary[k] for k in ['cosine_gap','accuracy','macro_f1','balanced_accuracy']},
              'v2_all_fields':{'cosine_gap':v2['cosine_gap'],**{k:v2['leave_one_out'][k] for k in ['accuracy','macro_f1','balanced_accuracy']}}}
    comparisons={name:{k:{'baseline':value,'v4':result[k],'v4_minus_baseline':result[k]-value} for k,value in metrics.items()} for name,metrics in baseline.items()}
    v3_records={r['image_id']:r for r in map(json.loads,(ROOT/'docs/experiment_results/pv_vlm_description_v3_discriminative/descriptions.jsonl').read_text().splitlines())}
    v2_records={r['image_id']:r for r in map(json.loads,(V2/'descriptions.jsonl').read_text().splitlines())}
    audit=[]
    for name in classes:
        first=next(i for i,row in enumerate(sample) if row['canonical_label']==name)
        neutral=ids[first]
        audit.append({'image_id':neutral,'hidden_ground_truth_class':name,
                      'v2_overall_summary':v2_records[neutral]['fields']['overall_summary'],
                      'v3_discriminative_summary':v3_records[neutral]['fields']['discriminative_summary'],
                      'v4_evidence_summary':texts[first]})
    ARTIFACT.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'protocol':design,'image_ids':ids,'source_image_ids':[r['image_id'] for r in sample],
                'hidden_ground_truth_classes':labels,'evidence_summary_texts':texts,
                'embeddings':embeddings,'candidate_field':CANDIDATE,'chunk_metadata':chunks,
                'torch_version':str(torch.__version__),'transformers_version':transformers.__version__},ARTIFACT)
    summary=summary_for(records,design)
    summary.update(status='completed_development_only',embedding_shape=list(embeddings.shape),l2_norms=embeddings.norm(dim=-1).tolist(),
                   all_finite=bool(torch.isfinite(embeddings).all()),chunk_metadata=chunks,diagnostics=result,
                   baseline_comparisons=comparisons,qualitative_audit=audit,
                   qualitative_audit_scope='Text comparison only: review cue retention, summary-only claims, generic wording and vocabulary consistency. Unsupported visual claims cannot be established without independent image review; outputs must not be edited after audit.',
                   warning='Development performance is not final evidence; new unseen PV-train confirmation required. No significance or generalization claim.')
    write_json(OUT/'summary.json',summary)
    with (ROOT/'research_log.md').open('a') as log:
        log.write('\n- V4 taxonomy-aware structured morphology development: fixed six-class morphology ontology in prompt only; ground-truth labels never dynamically supplied; frozen six-string strict JSON schema, combined 200-word limit, evidence_summary 45-word limit and cautious wording; same 30-image development set, no resampling; candidate = evidence_summary only, frozen SigLIP with lossless chunking; '+json.dumps({'model':MODEL,'versions':summary['returned_model_versions'],'metrics':{k:result[k] for k in ['accuracy','macro_f1','balanced_accuracy','cosine_gap']}})+'; no PlantDoc, no significance claim; prior 60-image confirmation not used; entirely new independent unseen PV-train confirmation required.\n')
    print(json.dumps(summary,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--preflight',action='store_true');modes.add_argument('--run',action='store_true');modes.add_argument('--embed-only',action='store_true')
    parser.add_argument('--cache-dir',type=Path);args=parser.parse_args()
    if os.environ.get('OPENAI_MODEL',MODEL)!=MODEL:raise RuntimeError('V4 development requires gpt-4.1-mini')
    protected=[ROOT/'data/pv_vlm_description_prompt.txt',ROOT/'data/pv_vlm_description_prompt_structured.txt',ROOT/'data/pv_vlm_description_prompt_v3_discriminative.txt',ROOT/'scripts/siglip_text_encoding.py']
    protected += [p for folder in [V1,V2,ROOT/'docs/experiment_results/pv_vlm_description_v3_discriminative',ROOT/'artifacts/pv_vlm_description',ROOT/'artifacts/pv_vlm_description_v3_discriminative'] for p in folder.rglob('*') if p.is_file()]
    before={p:digest(p) for p in protected};prompt_hash=digest(PROMPT)
    try:
        sample,classes=load_sample();design=protocol(sample,classes);prompt=PROMPT.read_text()
        for row in sample:build_request(prompt,b'preflight-only',row,sample)
        if args.preflight:
            print(json.dumps({'status':'preflight_pass','prompt_sha256':prompt_hash,'schema':SCHEMA,'sample_count':len(sample),
                              'per_class_counts':design['per_class_counts'],'candidate':CANDIDATE,'encoding_rule':ENCODING_RULE,
                              'api_calls':0,'encoder_inference':False},indent=2));return
        records=infer(sample,design,prompt) if args.run else load_valid_records(sample,design)
        embed_and_diagnose(records,sample,classes,design,args.cache_dir)
    finally:
        if any(digest(p)!=value for p,value in before.items()) or digest(PROMPT)!=prompt_hash:
            raise RuntimeError('Frozen prompt/development experiment modified')


if __name__=='__main__':
    try:main()
    except RuntimeError as exc:print('Error: '+str(exc),file=sys.stderr);sys.exit(1)
    except Exception as exc:print('Error: '+type(exc).__name__+' (sensitive details suppressed)',file=sys.stderr);sys.exit(1)
