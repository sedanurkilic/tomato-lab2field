"""Strict structured morphology v2 on the exact v1 sample; never overwrite v1.

--preflight: source/schema/sample checks only (no API or model inference).
--run: fresh inference on all 30 images; refuse existing generated outputs.
Then embed/diagnose if all 30 are valid.
--embed-only: process only current pure v2-150 generation records without API access.
Each field is encoded separately; equal-weight normalized pooling forms each image embedding.
Individual fields exceeding SigLIP's context are rejected, never truncated.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

from run_pv_vlm_description_pilot import LEAKAGE, DIAGNOSIS, encode_image, request_payload

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / 'docs/experiment_results/pv_vlm_description_pilot'
OUT = ROOT / 'docs/experiment_results/pv_vlm_description_structured_pilot'
PROMPT = ROOT / 'data/pv_vlm_description_prompt_structured.txt'
ARTIFACT = ROOT / 'artifacts/pv_vlm_description/pv_vlm_description_structured_embeddings_siglip.pt'
MODEL = 'gpt-4.1-mini'
ENCODER = 'google/siglip-base-patch16-224'
REVISION = '7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed'
SCHEMA_NAME = 'pv_structured_morphology_v2'
SCHEMA_VERSION = '1'
EXPERIMENT_ID = 'pv_structured_v2_150_field_mean_v1'
COMPARISON_NOTE = 'V2 differs from V1 in both structured generation and field-wise embedding aggregation; therefore this is a pipeline-level development comparison, not an isolated prompt-only ablation.'
EMBEDDING_METHOD = 'L2-normalize each of 6 field embeddings; arithmetic mean across fields; final L2 normalization'
FIELD_LABELS = [
    ('color_pattern','Color pattern'),
    ('lesions_spots','Lesions/spots'),
    ('center_border_internal_pattern','Center/border/internal pattern'),
    ('distribution','Distribution'),
    ('surface_deformation','Surface/deformation'),
    ('overall_summary','Overall summary'),
]
SCHEMA = {'type':'object','properties':{k:{'type':'string'} for k,_ in FIELD_LABELS},
          'required':[k for k,_ in FIELD_LABELS],'additionalProperties':False}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(fields):
    return '\n'.join(f'{label}: {fields[name]}' for name,label in FIELD_LABELS)


def parse_and_validate(raw):
    """Parse JSON, then validate the exact schema with Pydantic; never repair."""
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate_json_key')
            result[key]=value
        return result
    fields=None
    result={'parse_valid':False,'validation_pass':False,'total_word_count':None,
            'leakage':False,'errors':[],'fields':None,'canonical_text':None}
    try:
        parsed=json.loads(raw,object_pairs_hook=unique)
        from pydantic import ConfigDict,create_model
        schema_model=create_model(SCHEMA_NAME,__config__=ConfigDict(extra='forbid',strict=True),
                                  **{name:(str,...) for name,_ in FIELD_LABELS})
        fields=schema_model.model_validate(parsed,strict=True).model_dump()
    except Exception as exc:
        # Validation errors may include raw input; retain raw separately only.
        result['errors']=['json_or_schema_validation_failed:'+type(exc).__name__]
        return result
    total=sum(len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",fields[name])) for name,_ in FIELD_LABELS)
    joined='\n'.join(fields[name] for name,_ in FIELD_LABELS)
    errors=[]
    leakage=bool(LEAKAGE.search(joined))
    if total>150: errors.append('over_150_words')
    if any(not value.strip() for value in fields.values()): errors.append('empty_field')
    if leakage: errors.append('disease_pathogen_or_diagnostic_term')
    if DIAGNOSIS.search(joined): errors.append('explicit_diagnosis_language')
    return dict(result,parse_valid=True,validation_pass=not errors,total_word_count=total,
                leakage=leakage,errors=errors,fields=fields,canonical_text=canonical(fields))


def load_sample():
    """Join stored v1 neutral/source IDs to existing train metadata; no sampling."""
    summary=json.loads((V1/'summary.json').read_text())
    with (V1/'descriptions.csv').open(newline='') as f: descriptions=list(csv.DictReader(f))
    with (ROOT/'manifests/primary_split_manifest.csv').open(newline='') as f:
        train={r['image_id']:r for r in csv.DictReader(f)
               if r['dataset']=='plantvillage' and r['split']=='train' and r['primary_included'].lower()=='true'}
    detail={d['image_id']:d for d in summary['details']}
    if len(detail)!=30 or len(descriptions)!=30: raise ValueError('v1 requires 30 identities')
    sample=[]
    for old in descriptions:
        source_id=detail[old['image_id']]['source_image_id']
        row=dict(train[source_id],neutral_id=old['image_id'],v1_description=old['description'])
        if row['canonical_label']!=old['hidden_ground_truth_class']: raise ValueError('v1 class identity mismatch')
        path=(ROOT/row['relative_path']).resolve()
        if not path.is_relative_to((ROOT/'data/processed/tomato_plantvillage').resolve()) or not path.is_file():
            raise ValueError('Invalid PV-train image identity')
        sample.append(row)
    from collections import Counter
    classes=json.loads((ROOT/'manifests/primary_class_set.json').read_text())['canonical_classes']
    if Counter(r['canonical_label'] for r in sample)!=Counter({c:5 for c in classes}): raise ValueError('Expected 5/class')
    if len({r['neutral_id'] for r in sample})!=30 or len({r['image_id'] for r in sample})!=30: raise ValueError('Duplicate image')
    return sample,classes


def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    tmp.replace(path)


def save_records(records,sample):
    OUT.mkdir(parents=True,exist_ok=True)
    tmp=OUT/'descriptions.jsonl.tmp'
    tmp.write_text(''.join(json.dumps(records[r['neutral_id']],allow_nan=False)+'\n'
                           for r in sample if r['neutral_id'] in records))
    tmp.replace(OUT/'descriptions.jsonl')


def gpt_summary(records,sample,classes,prompt_hash,model):
    rows=list(records.values())
    return {'prompt_source_path':str(PROMPT.relative_to(ROOT)),'prompt_sha256':prompt_hash,
            'provider':'OpenAI','experiment_id':EXPERIMENT_ID,'generation_word_limit':150,'validation_word_limit':150,'schema_name':SCHEMA_NAME,'schema_version':SCHEMA_VERSION,'schema':SCHEMA,
            'model':model,'model_version':sorted({r['model_version'] for r in rows if r.get('model_version')}),
            'sample_count':30,'per_class_counts':{c:5 for c in classes},
            'completed_count':sum(r.get('completed',False) for r in rows),
            'parse_success_count':sum(r['parse_valid'] for r in rows),
            'parse_success_rate':sum(r['parse_valid'] for r in rows)/30,
            'validation_pass_count':sum(r['validation_pass'] for r in rows),
            'leakage_count':sum(r['leakage'] for r in rows),
            'word_limit_violation_count':sum((r['total_word_count'] or 0)>150 for r in rows),
            'failure_count':sum(not r['validation_pass'] for r in rows),'pending_count':30-len(rows),
            'v1_source_sha256':{p.name:digest(p) for p in [V1/'descriptions.csv',V1/'summary.json']},
            'framing':'Prompt-development on the same 30 PV-train images; no independent validation or generalization claim. Unseen source-side PV confirmation required; no PlantDoc.'}


def infer(sample,classes,prompt,prompt_hash,model):
    # Pure v2-150 runs never consume existing structured response caches.
    # Refuse stale files before constructing a client or sending any request.
    generated=[OUT/'descriptions.jsonl',OUT/'summary.json',ARTIFACT]
    if any(path.exists() for path in generated):
        raise RuntimeError('Existing v2 generated outputs detected; refusing cache reuse or overwrite. Clean outputs explicitly before a fresh 30-image run.')
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key: raise RuntimeError('OPENAI_API_KEY is not set; no inference or v2 result artifacts created.')
    from openai import OpenAI
    records={}
    with OpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=60.0) as client:
        for row in sample:
            record={'image_id':row['neutral_id'],'source_image_id':row['image_id'],
                    'hidden_ground_truth_class':row['canonical_label'],'provider':'OpenAI','model':model,'model_version':None,
                    'completed':False,'raw_response':'','prompt_sha256':prompt_hash,
                    'experiment_id':EXPERIMENT_ID,'generation_word_limit':150}
            try:
                image,original,sent=encode_image(ROOT/row['relative_path'])
                if original!=[256,256] or sent!=[256,256]: raise ValueError('Expected original 256x256')
                request=request_payload(prompt,row['neutral_id'],image,model,sample)
                # Schema carries only predefined field names/types, no labels.
                schema_text=json.dumps(SCHEMA).lower()
                for forbidden in [r['canonical_label'] for r in sample]: assert forbidden.lower() not in schema_text
                request['text']={'format':{'type':'json_schema','name':SCHEMA_NAME,'strict':True,'schema':SCHEMA}}
                response=client.responses.create(**request)
                record.update(model_version=response.model,completed=response.status=='completed',
                              response_id=response.id,raw_response=response.output_text or '')
            except AssertionError:raise
            except Exception as exc:
                code=getattr(exc,'status_code',None)
                record.update(api_error_type=type(exc).__name__,http_status=code if isinstance(code,int) else None)
            record.update(parse_and_validate(record['raw_response']))
            if not record['completed']:
                record['validation_pass']=False;record['errors'].append('inference_not_completed')
            records[row['neutral_id']]=record
            save_records(records,sample)
            atomic_json(OUT/'summary.json',gpt_summary(records,sample,classes,prompt_hash,model))
    return records


def encode_field_embeddings(field_texts,tokenizer,encoder,max_length):
    """Raw field values only, no canonical labels or metadata sent to SigLIP."""
    import torch
    image_fields=[]
    with torch.inference_mode():
        for fields in field_texts:
            if len(fields)!=6:raise RuntimeError('Expected exactly six ordered fields')
            encoded=[]
            for j,text in enumerate(fields):
                tokens=tokenizer(text,padding='max_length',max_length=max_length,
                                 truncation=False,return_tensors='pt')
                if tokens['input_ids'].shape[1]>max_length:
                    raise RuntimeError('Field '+FIELD_LABELS[j][0]+' exceeds context; refusing truncation')
                vector=encoder(**tokens).pooler_output.squeeze(0)
                if vector.shape!=(768,) or not torch.isfinite(vector).all() or vector.norm()<=0:
                    raise RuntimeError('Invalid field embedding')
                encoded.append(vector/vector.norm())
            image_fields.append(torch.stack(encoded))
        result=torch.stack(image_fields)
        if not torch.allclose(result.norm(dim=-1),torch.ones(result.shape[:2]),atol=1e-6,rtol=0):
            raise RuntimeError('Field unit-norm check failed')
    return result


def pool_field_embeddings(field_embeddings):
    """Equal-weight average of all six normalized fields, including summary."""
    import torch
    if field_embeddings.ndim!=3 or tuple(field_embeddings.shape[1:])!=(6,768):
        raise RuntimeError('Expected field embeddings [N,6,768]')
    if not torch.isfinite(field_embeddings).all() or not torch.allclose(
            field_embeddings.norm(dim=-1),torch.ones(field_embeddings.shape[:2]),atol=1e-6,rtol=0):
        raise RuntimeError('Invalid normalized field embeddings')
    mean=field_embeddings.mean(dim=1)
    norms=mean.norm(dim=-1,keepdim=True)
    if not torch.isfinite(norms).all() or (norms<=0).any():raise RuntimeError('Invalid field mean norm')
    result=mean/norms
    if not torch.isfinite(result).all() or not torch.allclose(result.norm(dim=-1),torch.ones(len(result)),atol=1e-6,rtol=0):
        raise RuntimeError('Image-level unit-norm check failed')
    return result


def embed_diagnose(records,sample,classes,summary,cache_dir):
    if len(records)!=30 or not all(r['validation_pass'] for r in records.values()):
        raise RuntimeError('Need 30 schema/semantic-valid records before embedding; no imputation')
    import torch
    import numpy as np
    import transformers
    from transformers import AutoTokenizer,SiglipTextModel
    from sklearn.metrics import accuracy_score,f1_score,balanced_accuracy_score,confusion_matrix,recall_score
    torch.manual_seed(0);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    options={'revision':REVISION,'cache_dir':cache_dir}
    tokenizer=AutoTokenizer.from_pretrained(ENCODER,**options)
    texts=[records[r['neutral_id']]['canonical_text'] for r in sample]  # audit metadata only
    field_order=[name for name,_ in FIELD_LABELS]
    field_texts=[[records[r['neutral_id']]['fields'][name] for name in field_order] for r in sample]
    max_length=64
    lengths=[[len(tokenizer(text,truncation=False)['input_ids']) for text in fields] for fields in field_texts]
    too_long=[{'image_id':r['neutral_id'],'field_name':field_order[j],'token_count':length,
               'max_tokens':max_length}
              for r,counts in zip(sample,lengths) for j,length in enumerate(counts) if length>max_length]
    if too_long:
        summary['embedding_status']='blocked_field_context_limit'
        summary['over_context_fields']=too_long
        summary['field_order']=field_order
        summary['embedding_method']=EMBEDDING_METHOD
        summary['comparison_note']=COMPARISON_NOTE
        atomic_json(OUT/'summary.json',summary)
        raise RuntimeError('Individual structured field exceeds SigLIP 64-token context; no truncation or text repair applied. See over_context_fields.')
    encoder,loading=SiglipTextModel.from_pretrained(ENCODER,output_loading_info=True,**options)
    if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):raise RuntimeError('Incomplete text encoder weights')
    encoder=encoder.to(device='cpu',dtype=torch.float32).eval();encoder.requires_grad_(False)
    assert encoder.config.max_position_embeddings==max_length
    with torch.inference_mode():
        field_embeddings=encode_field_embeddings(field_texts,tokenizer,encoder,max_length)
        assert field_embeddings.shape==(30,6,768)
        x=pool_field_embeddings(field_embeddings)
        assert x.shape==(30,768)
        y=torch.tensor([classes.index(r['canonical_label']) for r in sample])
        prototypes=[]
        for c in range(6):
            mean=x[y==c].mean(0);prototypes.append(mean/mean.norm())
        prototypes=torch.stack(prototypes)
        if not torch.isfinite(prototypes).all() or not torch.allclose(prototypes.norm(dim=-1),torch.ones(6),atol=1e-6,rtol=0):raise RuntimeError('Invalid prototype norm/finite check')
        cosine=x@x.T
        same=[float(cosine[i,j]) for i in range(30) for j in range(i+1,30) if y[i]==y[j]]
        different=[float(cosine[i,j]) for i in range(30) for j in range(i+1,30) if y[i]!=y[j]]
        assert len(same)==60 and len(different)==375
        def stats(values):return {'count':len(values),'mean':float(np.mean(values)),'sample_std':float(np.std(values,ddof=1))}
        loo=[]
        for i in range(30):
            ps=[]
            for c in range(6):
                indices=torch.nonzero(y==c).flatten();indices=indices[indices!=i]
                assert len(indices)==(4 if int(y[i])==c else 5)
                mean=x[indices].mean(0);ps.append(mean/mean.norm())
            scores=x[i]@torch.stack(ps).T;pred=int(scores.argmax())
            loo.append({'image_id':sample[i]['neutral_id'],'true_class':classes[int(y[i])],
                        'predicted_class':classes[pred],'cosine_scores':scores.tolist()})
        pred=[classes.index(r['predicted_class']) for r in loo]
        metrics={'accuracy':float(accuracy_score(y.numpy(),pred)),'macro_f1':float(f1_score(y.numpy(),pred,average='macro')),
                 'balanced_accuracy':float(balanced_accuracy_score(y.numpy(),pred)),
                 'confusion_matrix':confusion_matrix(y.numpy(),pred,labels=list(range(6))).tolist(),
                 'per_class_recall':dict(zip(classes,recall_score(y.numpy(),pred,labels=list(range(6)),average=None,zero_division=0).tolist())),
                 'per_image':loo}
    diagnostics={'field_order':field_order,'field_weights':[1/6]*6,'embedding_method':EMBEDDING_METHOD,
                 'comparison_note':COMPARISON_NOTE,'field_embedding_shape':list(field_embeddings.shape),
                 'field_l2_norms':field_embeddings.norm(dim=-1).tolist(),
                 'class_order':classes,'embedding_shape':list(x.shape),'dtype':'float32','l2_norms':x.norm(dim=-1).tolist(),
                 'all_finite':bool(torch.isfinite(x).all()),'cosine_similarity_matrix':cosine.tolist(),
                 'same_class_cosine':stats(same),'different_class_cosine':stats(different),
                 'same_class_pair_values':same,'different_class_pair_values':different,
                 'prototype_shape':list(prototypes.shape),'prototype_l2_norms':prototypes.norm(dim=-1).tolist(),
                 'prototype_cosine_similarity_matrix':(prototypes@prototypes.T).tolist(),'leave_one_out':metrics}
    diagnostics['cosine_gap']=diagnostics['same_class_cosine']['mean']-diagnostics['different_class_cosine']['mean']
    baseline=json.loads((V1/'embedding_summary.json').read_text());v1loo=baseline['leave_one_out_class_prototype_diagnostic']
    v1={'same_class_mean':baseline['same_class_cosine']['mean'],'different_class_mean':baseline['different_class_cosine']['mean'],
        'cosine_gap':baseline['same_class_cosine']['mean']-baseline['different_class_cosine']['mean'],
        **{k:v1loo[k] for k in ['accuracy','macro_f1','balanced_accuracy']}}
    v2={'same_class_mean':diagnostics['same_class_cosine']['mean'],'different_class_mean':diagnostics['different_class_cosine']['mean'],
        'cosine_gap':diagnostics['cosine_gap'],**{k:metrics[k] for k in ['accuracy','macro_f1','balanced_accuracy']}}
    diagnostics['v1_v2_comparison']={k:{'v1':v1[k],'v2':v2[k],'absolute_difference_v2_minus_v1':v2[k]-v1[k]} for k in v1}
    ARTIFACT.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'image_ids':[r['neutral_id'] for r in sample],'hidden_ground_truth_classes':[r['canonical_label'] for r in sample],
                'canonical_texts':texts,'structured_fields':[records[r['neutral_id']]['fields'] for r in sample],
                'embeddings':x,'field_embeddings':field_embeddings,'field_order':field_order,
                'field_texts':field_texts,'field_weights':[1/6]*6,'embedding_method':EMBEDDING_METHOD,
                'comparison_note':COMPARISON_NOTE,'class_names':classes,'class_prototypes':prototypes,'encoder_name':ENCODER,'encoder_revision':REVISION,
                'prompt_sha256':summary['prompt_sha256'],'experiment_id':EXPERIMENT_ID,'generation_word_limit':150,
                'validation_word_limit':150,'schema':SCHEMA,'field_token_counts':lengths,
                'torch_version':str(torch.__version__),'transformers_version':transformers.__version__},ARTIFACT)
    summary.update(embedding_status='completed',embedding_method=EMBEDDING_METHOD,comparison_note=COMPARISON_NOTE,diagnostics=diagnostics)
    atomic_json(OUT/'summary.json',summary)
    with (ROOT/'research_log.md').open('a') as log:
        log.write('\n- Structured morphology v2 prompt-development pilot: same 30 PV-train images as v1; strict six-string JSON schema, combined 150-word validation limit, cautious "not clearly visible" wording; '+json.dumps({k:summary[k] for k in ['model','model_version','prompt_sha256']})
                  +'; frozen SigLIP '+ENCODER+'; diagnostics '+json.dumps({'same_class':diagnostics['same_class_cosine'],'different_class':diagnostics['different_class_cosine'],'gap':diagnostics['cosine_gap'],'loo':{k:metrics[k] for k in ['accuracy','macro_f1','balanced_accuracy']},'comparison':diagnostics['v1_v2_comparison']})
                  +'; '+COMPARISON_NOTE+'; no training, threshold tuning, significance or generalization claim; no PlantDoc; independent unseen source-side PV confirmation still required.\n')
    print(json.dumps(diagnostics,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight',action='store_true');mode.add_argument('--run',action='store_true');mode.add_argument('--embed-only',action='store_true')
    parser.add_argument('--cache-dir',type=Path)
    args=parser.parse_args()
    # Hash all v1 outputs/artifact to enforce immutability through this run.
    protected=[p for p in V1.rglob('*') if p.is_file()]+[ROOT/'artifacts/pv_vlm_description/pv_vlm_description_embeddings_siglip.pt',ROOT/'data/pv_vlm_description_prompt.txt']
    before={p:digest(p) for p in protected}
    sample,classes=load_sample();prompt=PROMPT.read_text();prompt_hash=digest(PROMPT)
    if 'Keep the combined descriptive text within 150 words.' not in prompt:
        raise RuntimeError('Pure v2-150 requires the 150-word source prompt')
    model=os.environ.get('OPENAI_MODEL',MODEL)
    if model!=MODEL:raise RuntimeError('This experiment requires gpt-4.1-mini')
    # Privacy assertions without opening images or making a request.
    for row in sample:request_payload(prompt,row['neutral_id'],b'preflight-only',model,sample)
    if args.preflight:
        print('Preflight PASS: exact v1 identities/order, 30 PV-train images, 5/class; label-blind source prompt; six-field strict schema. No inference.')
        return
    try:
        if args.run:records=infer(sample,classes,prompt,prompt_hash,model)
        else:
            records={}
            for line in (OUT/'descriptions.jsonl').read_text().splitlines():
                record=json.loads(line);neutral=record['image_id']
                if neutral in records:raise RuntimeError('Duplicate structured ID')
                record.update(parse_and_validate(record['raw_response']));records[neutral]=record
            previous=json.loads((OUT/'summary.json').read_text())
            if previous.get('experiment_id')!=EXPERIMENT_ID or previous.get('generation_word_limit')!=150:
                raise RuntimeError('Only fresh pure v2-150 generation results can be embedded')
            if previous['prompt_sha256']!=prompt_hash or previous['schema']!=SCHEMA or previous['model']!=model:
                raise RuntimeError('v2-150 prompt/schema/model provenance mismatch')
            if any(r.get('prompt_sha256')!=prompt_hash or r.get('experiment_id')!=EXPERIMENT_ID
                   or r.get('generation_word_limit')!=150 or r.get('model')!=model for r in records.values()):
                raise RuntimeError('Record is not from the current pure v2-150 generation')
            if set(records)!={r['neutral_id'] for r in sample}:raise RuntimeError('v2 sample ID mismatch')
            for row in sample:
                record=records[row['neutral_id']]
                if record['source_image_id']!=row['image_id'] or record['hidden_ground_truth_class']!=row['canonical_label']:raise RuntimeError('v2 source identity mismatch')
                if not record['completed']:record['validation_pass']=False
        summary=gpt_summary(records,sample,classes,prompt_hash,model)
        embed_diagnose(records,sample,classes,summary,args.cache_dir)
    finally:
        if any(digest(p)!=h for p,h in before.items()):raise RuntimeError('v1 immutability check failed')
        if digest(PROMPT)!=prompt_hash:raise RuntimeError('Frozen v2 prompt changed')


if __name__=='__main__':
    try:main()
    except RuntimeError as exc:print('Error: '+str(exc),file=sys.stderr);sys.exit(1)
    except Exception as exc:print('Error: '+type(exc).__name__+' (sensitive details suppressed)',file=sys.stderr);sys.exit(1)
