"""Frozen v1 vs structured-v2 overall_summary on 60 disjoint PV-train images.

--preflight locks design/sample without any API or encoder inference.
--run resumes validated outputs for this exact locked protocol, then diagnoses.
--embed-only performs no API calls. No candidate/field/combination search.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import sys

from siglip_text_encoding import ENCODING_RULE, encode_texts_lossless
from run_pv_vlm_description_pilot import validate as validate_v1, encode_image
from run_pv_vlm_description_structured_pilot import (
    SCHEMA, SCHEMA_NAME, parse_and_validate, load_sample as development_sample,
)

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/experiment_results/pv_vlm_semantic_confirmation'
ARTIFACT=ROOT/'artifacts/pv_vlm_semantic_confirmation/semantic_embeddings_siglip.pt'
PROMPT_V1=ROOT/'data/pv_vlm_description_prompt.txt'
PROMPT_V2=ROOT/'data/pv_vlm_description_prompt_structured.txt'
MODEL='gpt-4.1-mini'
ENCODER='google/siglip-base-patch16-224'
REVISION='7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed'
CANDIDATE_FIELD='overall_summary'
EXPERIMENT='independent_pv_train_60_v1_vs_v2_overall_summary'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(text);tmp.replace(path)


def write_summary(summary):atomic_text(OUT/'summary.json',json.dumps(summary,indent=2,allow_nan=False)+'\n')


def select_confirmation():
    development,classes=development_sample()
    excluded={r['image_id'] for r in development}
    # Cross-check both stored development generations before excluding their union.
    structured=ROOT/'docs/experiment_results/pv_vlm_description_structured_pilot/descriptions.jsonl'
    structured_ids={json.loads(line)['source_image_id'] for line in structured.read_text().splitlines() if line.strip()}
    if structured_ids!=excluded:raise RuntimeError('v1/v2 development source identities differ')
    with (ROOT/'manifests/primary_split_manifest.csv').open(newline='') as stream:
        train=[r for r in csv.DictReader(stream) if r['dataset']=='plantvillage' and r['split']=='train'
               and r['primary_included'].lower()=='true']
    rng=random.Random(42);selected=[]
    for name in classes:
        pool=sorted([r for r in train if r['canonical_label']==name and r['image_id'] not in excluded],key=lambda r:r['image_id'])
        if len(pool)<10:raise RuntimeError('Not enough disjoint PV-train images')
        selected.extend(rng.sample(pool,10))
    rng.shuffle(selected)
    sample=[dict(row,neutral_id=f'pv_confirm_{i:03d}') for i,row in enumerate(selected,1)]
    confirmation_ids={r['image_id'] for r in sample}
    assert len(confirmation_ids)==60 and not excluded.intersection(confirmation_ids)
    assert Counter(r['canonical_label'] for r in sample)==Counter({c:10 for c in classes})
    from PIL import Image
    for row in sample:
        assert row['dataset']=='plantvillage' and row['split']=='train'
        path=(ROOT/row['relative_path']).resolve()
        assert path.is_relative_to((ROOT/'data/processed/tomato_plantvillage').resolve()) and path.is_file()
        with Image.open(path) as image:assert image.size==(256,256)
    return sample,classes,sorted(excluded)


def check_label_blind(prompt,schema,sample):
    text=prompt+'\n'+json.dumps(schema or {})
    for row in sample:
        path=Path(row['relative_path'])
        for forbidden in [row['canonical_label'],row['original_label'],row['relative_path'],row['image_id'],path.name,path.parent.name]:
            assert forbidden.lower() not in text.lower(),'Label/path leakage in request'
    assert not re.search(r'\b(?:bacterial spot|early blight|late blight|leaf mold|septoria|tomato mosaic virus|xanthomonas|alternaria|phytophthora)\b',text,re.I)


def request_payload(prompt,image,model,structured,sample):
    check_label_blind(prompt,SCHEMA if structured else None,sample)
    import base64
    request={'model':model,'temperature':0,'store':False,'input':[{'role':'user','content':[
        {'type':'input_text','text':prompt},
        {'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(image).decode('ascii')}
    ]}]}
    if structured:request['text']={'format':{'type':'json_schema','name':SCHEMA_NAME,'strict':True,'schema':SCHEMA}}
    return request


def prepare(sample,classes,excluded,model):
    protocol={'experiment_id':EXPERIMENT,'sampling_seed':42,'candidate_field':CANDIDATE_FIELD,
              'v1_prompt_source':str(PROMPT_V1.relative_to(ROOT)),'v1_prompt_sha256':digest(PROMPT_V1),
              'v2_prompt_source':str(PROMPT_V2.relative_to(ROOT)),'v2_prompt_sha256':digest(PROMPT_V2),
              'structured_schema':SCHEMA,'gpt_model':model,'siglip_encoder':ENCODER,'siglip_revision':REVISION,
              'sample_count':60,'per_class_counts':{c:10 for c in classes},'class_order':classes,
              'excluded_development_image_ids':excluded,
              'excluded_development_ids_sha256':hashlib.sha256('\n'.join(excluded).encode()).hexdigest(),
              'overlap_count':0,'all_unique':True,'all_pv_train':True,'original_resolution':[256,256],
              'confirmation_sample':[{'image_id':r['neutral_id'],'source_image_id':r['image_id'],
                                      'hidden_ground_truth_class':r['canonical_label']} for r in sample]}
    if (OUT/'summary.json').exists():
        summary=json.loads((OUT/'summary.json').read_text())
        if summary['protocol']!=protocol:raise RuntimeError('Existing confirmation protocol differs; refusing changes')
        return summary
    summary={'protocol':protocol,'status':'prepared_no_inference',
             'inference_validation':{version:{'attempted_count':0,'completed_count':0,'validation_pass_count':0,
                                            'failure_count':0,'pending_count':60,'leakage_count':0,'word_limit_violation_count':0}
                                     for version in ['v1','v2_summary']},
             'interpretation':'Independent source-side confirmation relative to the 30-image development set; no PlantDoc, tuning, learned weighting, field selection, threshold selection, training or significance claim.'}
    write_summary(summary);return summary


def load_outputs(sample):
    records={'v1':{},'v2_summary':{}}
    allowed={r['neutral_id']:r for r in sample}
    for version,path in [('v1',OUT/'descriptions_v1.csv'),('v2_summary',OUT/'descriptions_v2.jsonl')]:
        if not path.exists():continue
        if version=='v1':
            with path.open(newline='') as f:rows=[json.loads(r['record_json']) for r in csv.DictReader(f)]
        else:rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        for record in rows:
            key=record['image_id']
            if key not in allowed or key in records[version]:raise RuntimeError('Unknown/duplicate confirmation ID')
            if record['source_image_id']!=allowed[key]['image_id'] or record['model']!=MODEL or record['hidden_ground_truth_class']!=allowed[key]['canonical_label']:raise RuntimeError('Output identity/model mismatch')
            records[version][key]=record
    return records


def save_outputs(records,sample,summary):
    v1=[records['v1'][r['neutral_id']] for r in sample if r['neutral_id'] in records['v1']]
    if v1:
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=['image_id','hidden_ground_truth_class','description','model','model_version','validation_pass','record_json'])
        writer.writeheader()
        for r in v1:writer.writerow({k:r[k] for k in ['image_id','hidden_ground_truth_class','description','model','model_version','validation_pass']}|{'record_json':json.dumps(r)})
        atomic_text(OUT/'descriptions_v1.csv',stream.getvalue())
    if records['v2_summary']:
        atomic_text(OUT/'descriptions_v2.jsonl',''.join(json.dumps(records['v2_summary'][r['neutral_id']])+'\n' for r in sample if r['neutral_id'] in records['v2_summary']))
    for version,group in records.items():
        rows=list(group.values())
        summary['inference_validation'][version]={'attempted_count':len(rows),'completed_count':sum(r['completed'] for r in rows),
            'validation_pass_count':sum(r['validation_pass'] for r in rows),'failure_count':sum(not r['validation_pass'] for r in rows),
            'pending_count':60-len(rows),'leakage_count':sum(r['leakage'] for r in rows),
            'word_limit_violation_count':sum(r['word_count']>(50 if version=='v1' else 150) for r in rows),
            'returned_model_versions':sorted({r['model_version'] for r in rows if r['model_version']})}
    write_summary(summary)


def validate_record(record,version):
    if version=='v1':
        result=validate_v1(record['raw_response']);record.update(result)
    else:
        result=parse_and_validate(record['raw_response']);record.update(result)
        record['word_count']=result['total_word_count'] or 0
        record['description']=result['fields'][CANDIDATE_FIELD] if result['parse_valid'] else ''
    if not record['completed']:record['validation_pass']=False
    return record


def infer(sample,summary,records):
    pending=[]
    for row in sample:
        for version in ['v1','v2_summary']:
            old=records[version].get(row['neutral_id'])
            prompt_hash=summary['protocol']['v1_prompt_sha256' if version=='v1' else 'v2_prompt_sha256']
            if old:
                if old.get('prompt_sha256')!=prompt_hash:raise RuntimeError('Stored output prompt mismatch')
                validate_record(old,version)
            if not old or not old['validation_pass']:pending.append((row,version))
    if not pending:return
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key:
        summary['status']='blocked_missing_api_key';summary['warning']='OPENAI_API_KEY not set; no request sent. Counts describe unattempted work, not model failures.'
        write_summary(summary)
        raise RuntimeError(f'OPENAI_API_KEY is not set; {len(pending)} paired-representation requests pending; no new inference performed.')
    from openai import OpenAI
    with OpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=60.0) as client:
        for row,version in pending:
            prompt_path=PROMPT_V1 if version=='v1' else PROMPT_V2
            record={'image_id':row['neutral_id'],'source_image_id':row['image_id'],'hidden_ground_truth_class':row['canonical_label'],
                    'provider':'OpenAI','model':MODEL,'model_version':None,'prompt_sha256':digest(prompt_path),
                    'completed':False,'raw_response':'','description':'','validation_pass':False,'leakage':False,'word_count':0}
            try:
                image,original,sent=encode_image(ROOT/row['relative_path']);assert original==sent==[256,256]
                response=client.responses.create(**request_payload(prompt_path.read_text(),image,MODEL,version=='v2_summary',sample))
                record.update(raw_response=response.output_text or '',model_version=response.model,response_id=response.id,completed=response.status=='completed')
            except AssertionError:raise
            except Exception as exc:
                code=getattr(exc,'status_code',None);record.update(error_type=type(exc).__name__,http_status=code if isinstance(code,int) else None)
            if version=='v1':record['description']=record['raw_response']
            records[version][row['neutral_id']]=validate_record(record,version)
            summary['status']='inference_in_progress';summary.pop('warning',None)
            save_outputs(records,sample,summary)


def diagnostics(x,labels,classes,ids):
    import torch,numpy as np
    from sklearn.metrics import accuracy_score,f1_score,balanced_accuracy_score,confusion_matrix,recall_score
    n=len(ids);assert x.shape==(n,768) and torch.isfinite(x).all()
    assert torch.allclose(x.norm(dim=-1),torch.ones(n),atol=1e-6,rtol=0)
    y=torch.tensor([classes.index(c) for c in labels]);class_count=Counter(labels)
    assert len(set(class_count.values()))==1
    cosine=x@x.T
    same=[float(cosine[i,j]) for i in range(n) for j in range(i+1,n) if y[i]==y[j]]
    different=[float(cosine[i,j]) for i in range(n) for j in range(i+1,n) if y[i]!=y[j]]
    def stats(values):return {'count':len(values),'mean':float(np.mean(values)),'sample_std':float(np.std(values,ddof=1))}
    per_image=[];pred=[]
    for i in range(n):
        prototypes=[]
        for c,name in enumerate(classes):
            indices=torch.nonzero(y==c).flatten();indices=indices[indices!=i]
            assert len(indices)==class_count[name]-(int(y[i])==c) and i not in indices.tolist()
            mean=x[indices].mean(0);assert torch.isfinite(mean).all() and mean.norm()>0
            prototypes.append(mean/mean.norm())
        scores=x[i]@torch.stack(prototypes).T;prediction=int(scores.argmax());pred.append(prediction)
        per_image.append({'image_id':ids[i],'true_class':labels[i],'predicted_class':classes[prediction],
                          'cosine_scores':scores.tolist(),'correct':prediction==int(y[i])})
    return {'same_class_cosine':stats(same),'different_class_cosine':stats(different),
            'cosine_gap':float(np.mean(same)-np.mean(different)),
            'accuracy':float(accuracy_score(y.numpy(),pred)),'macro_f1':float(f1_score(y.numpy(),pred,labels=list(range(6)),average='macro',zero_division=0)),
            'balanced_accuracy':float(balanced_accuracy_score(y.numpy(),pred)),
            'class_order':classes,'confusion_matrix_axes':'rows=true, columns=predicted',
            'confusion_matrix':confusion_matrix(y.numpy(),pred,labels=list(range(6))).tolist(),
            'per_class_recall':dict(zip(classes,recall_score(y.numpy(),pred,labels=list(range(6)),average=None,zero_division=0).tolist())),
            'per_image':per_image}


def embed_and_diagnose(sample,classes,summary,records,cache_dir):
    for version in records:
        if len(records[version])!=60 or not all(r['validation_pass'] for r in records[version].values()):
            summary['status']='blocked_incomplete_or_invalid_descriptions';write_summary(summary)
            raise RuntimeError('Need 60 valid paired descriptions per representation; no imputation')
    import torch
    import transformers
    from transformers import AutoTokenizer,SiglipTextModel
    torch.manual_seed(0);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    options={'revision':REVISION,'cache_dir':cache_dir}
    tokenizer=AutoTokenizer.from_pretrained(ENCODER,**options)
    texts={version:[records[version][r['neutral_id']]['description'] for r in sample] for version in records}
    encoder,loading=SiglipTextModel.from_pretrained(ENCODER,output_loading_info=True,**options)
    if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):raise RuntimeError('Incomplete encoder weights')
    encoder=encoder.to(device='cpu',dtype=torch.float32).eval();encoder.requires_grad_(False)
    assert encoder.config.max_position_embeddings==64
    embeddings,chunk_metadata={},{}
    for version,values in texts.items():
        embeddings[version],chunk_metadata[version]=encode_texts_lossless(values,tokenizer,encoder)
    ids=[r['neutral_id'] for r in sample];labels=[r['canonical_label'] for r in sample]
    results={version:diagnostics(x,labels,classes,ids) for version,x in embeddings.items()}
    assert results['v1']['same_class_cosine']['count']==270 and results['v1']['different_class_cosine']['count']==1500
    paired=Counter({'both_correct':0,'only_v1_correct':0,'only_v2_correct':0,'both_wrong':0})
    for first,second in zip(results['v1']['per_image'],results['v2_summary']['per_image']):
        assert first['image_id']==second['image_id']
        a,b=first['correct'],second['correct']
        paired['both_correct' if a and b else 'only_v1_correct' if a else 'only_v2_correct' if b else 'both_wrong']+=1
    differences={k:results['v2_summary'][k]-results['v1'][k] for k in ['cosine_gap','accuracy','macro_f1','balanced_accuracy']}
    ARTIFACT.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'experiment_id':EXPERIMENT,'image_ids':ids,'source_image_ids':[r['image_id'] for r in sample],
                'hidden_ground_truth_classes':labels,'class_names':classes,'v1_embeddings':embeddings['v1'],
                'v2_summary_embeddings':embeddings['v2_summary'],'v1_descriptions':texts['v1'],
                'v2_overall_summary_texts':texts['v2_summary'],'candidate_field':CANDIDATE_FIELD,
                'encoding_rule':ENCODING_RULE,'chunk_metadata':chunk_metadata,
                'protocol':summary['protocol'],'torch_version':str(torch.__version__),'transformers_version':transformers.__version__},ARTIFACT)
    summary.pop('over_context_records',None)
    summary.update(encoding_rule=ENCODING_RULE,chunk_metadata=chunk_metadata,status='completed',diagnostics=results,paired_correct_wrong_counts=dict(paired),v2_minus_v1=differences)
    summary['embedding_checks']={k:{'shape':list(x.shape),'norms':x.norm(dim=-1).tolist(),'all_finite':bool(torch.isfinite(x).all())} for k,x in embeddings.items()}
    write_summary(summary)
    with (ROOT/'research_log.md').open('a') as log:
        log.write('\n- Independent source-side semantic confirmation: v2 overall_summary selected on the prior 30-image development set; 60 PV-train images (10/class), seed 42, explicit zero overlap; frozen v1/v2-150 prompts, GPT-4.1-mini, frozen SigLIP text encoder; '+json.dumps({'inference':summary['inference_validation'],'metrics':{v:{k:r[k] for k in ['accuracy','macro_f1','balanced_accuracy','cosine_gap','per_class_recall']} for v,r in results.items()},'paired':dict(paired),'v2_minus_v1':differences})+'; no tuning on confirmation set, no PlantDoc, no significance or external-field generalization claim.\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight',action='store_true');mode.add_argument('--run',action='store_true');mode.add_argument('--embed-only',action='store_true')
    parser.add_argument('--cache-dir',type=Path);args=parser.parse_args()
    model=os.environ.get('OPENAI_MODEL',MODEL)
    if model!=MODEL:raise RuntimeError('Frozen confirmation design requires gpt-4.1-mini')
    # Existing development sources and results must remain byte-identical.
    protected=[PROMPT_V1,PROMPT_V2]+[p for name in ['pv_vlm_description_pilot','pv_vlm_description_structured_pilot']
                                for p in (ROOT/'docs/experiment_results'/name).rglob('*') if p.is_file()]
    hashes={p:digest(p) for p in protected}
    try:
        sample,classes,excluded=select_confirmation()
        for path,structured in [(PROMPT_V1,False),(PROMPT_V2,True)]:check_label_blind(path.read_text(),SCHEMA if structured else None,sample)
        summary=prepare(sample,classes,excluded,model)
        print('Preflight PASS: 60 unique PV-train images, 10/class, original 256x256; overlap=0; candidate fixed to overall_summary.')
        if args.preflight:return
        records=load_outputs(sample)
        if args.run:infer(sample,summary,records)
        else:
            for version,group in records.items():
                for record in group.values():
                    expected=summary['protocol']['v1_prompt_sha256' if version=='v1' else 'v2_prompt_sha256']
                    if record.get('prompt_sha256')!=expected:raise RuntimeError('Prompt provenance mismatch')
                    validate_record(record,version)
        save_outputs(records,sample,summary)
        embed_and_diagnose(sample,classes,summary,records,args.cache_dir)
    finally:
        if any(digest(p)!=h for p,h in hashes.items()):raise RuntimeError('Frozen development inputs/results changed')


if __name__=='__main__':
    try:main()
    except RuntimeError as exc:print('Error: '+str(exc),file=sys.stderr);sys.exit(1)
    except Exception as exc:print('Error: '+type(exc).__name__+' (sensitive details suppressed)',file=sys.stderr);sys.exit(1)
