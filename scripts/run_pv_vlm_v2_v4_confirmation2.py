"""Frozen paired V2 versus V4 confirmation on 120 new PV-train images.

Preflight only prepares a locked manifest and protocol. No prompt selection,
training, PlantDoc, significance testing, or research-log writes in any mode.
--run requires fresh response files; --embed-only explicitly reuses validated
responses; --analyze-only explicitly reuses provenance-matched embeddings.
"""
import argparse
import base64
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re

import run_pv_vlm_description_structured_pilot as v2
import run_pv_vlm_description_v4_taxonomy_aware as v4
from run_pv_vlm_description_pilot import encode_image
from run_pv_vlm_semantic_confirmation import diagnostics
from siglip_text_encoding import ENCODING_RULE, encode_texts_lossless

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/experiment_results/pv_vlm_v2_v4_confirmation2'
ART=ROOT/'artifacts/pv_vlm_v2_v4_confirmation2'
MODEL='gpt-4.1-mini'
ENCODER=v4.ENCODER
REVISION=v4.REVISION
EXPERIMENT='frozen_pv_train_120_v2_vs_v4_confirmation2'
CLASSES=['Tomato___Bacterial_spot','Tomato___Early_blight','Tomato___Late_blight','Tomato___Leaf_Mold','Tomato___Septoria_leaf_spot','Tomato___Tomato_mosaic_virus']
PROMPTS={'v2':ROOT/'data/pv_vlm_description_prompt_structured.txt','v4':v4.PROMPT}
EXPECTED_HASHES={'v2':'4a5150a8b66d27b132a0be35816b9fcf15592531fb552538886312fbd770935c','v4':'ecee01ce0f90e89392b4a20daaa8ecf1d1146017b5cf5117ad040e2d16528d4b'}
SCHEMAS={'v2':v2.SCHEMA,'v4':v4.SCHEMA}
NAMES={'v2':v2.SCHEMA_NAME,'v4':v4.SCHEMA_NAME}
VERSIONS={'v2':v2.SCHEMA_VERSION,'v4':v4.SCHEMA_VERSION}
CANDIDATES={'v2':'overall_summary','v4':'evidence_summary'}
HISTORY={'context_only_not_tuning_targets':True,
 'previous_60':{'v1':{'accuracy':.33333,'macro_f1':.32222,'balanced_accuracy':.33333,'cosine_gap':.009276},'v2':{'accuracy':.35000,'macro_f1':.33830,'balanced_accuracy':.35000,'cosine_gap':.012643}},
 'development':{'v2':{'accuracy':.56667,'macro_f1':.55469,'balanced_accuracy':.56667,'cosine_gap':.01945},'v4':{'accuracy':.40000,'macro_f1':.42003,'balanced_accuracy':.40000,'cosine_gap':.01115}}}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temp.replace(path)


def frozen_protocol():
    for key,path in PROMPTS.items():
        if digest(path)!=EXPECTED_HASHES[key]:raise RuntimeError(f'{key} frozen prompt provenance mismatch')
    assert v4.FROZEN_PROMPT_SHA256==EXPECTED_HASHES['v4']
    for key in SCHEMAS:
        assert SCHEMAS[key]=={'type':'object','properties':{k:{'type':'string'} for k in ['color_pattern','lesions_spots','center_border_internal_pattern','distribution','surface_deformation',CANDIDATES[key]]},'required':['color_pattern','lesions_spots','center_border_internal_pattern','distribution','surface_deformation',CANDIDATES[key]],'additionalProperties':False}
    assert VERSIONS=={'v2':'1','v4':'2'}
    return {'experiment_id':EXPERIMENT,'model':MODEL,'prompts':{key:{'path':str(path.relative_to(ROOT)),'sha256':digest(path),'schema':SCHEMAS[key],'schema_name':NAMES[key],'schema_version':VERSIONS[key],'candidate':CANDIDATES[key]} for key,path in PROMPTS.items()},
            'encoder':ENCODER,'encoder_revision':REVISION,'encoding_rule':ENCODING_RULE,
            'validator_sha256':{'v2':digest(Path(v2.__file__)),'v4':digest(Path(v4.__file__))},
            'helper_sha256':digest(ROOT/'scripts/siglip_text_encoding.py'),
            'sampling_seed':42,'class_order':CLASSES,'sample_count':120,'per_class_count':20,
            'paired_same_image_bytes':True,'prompt_tuning_permitted':False,'plantdoc_used':False,
            'decision_policy':'Review Macro-F1, balanced accuracy, recall balance, paired correctness and qualitative stability together. Mixed/similar favors simpler V2. No automatic winner or significance claim; no prompt changes on this set. Any refinement requires a new development subset.'}


def sample_manifest():
    development,classes=v2.load_sample();assert classes==CLASSES
    excluded_dev={r['image_id'] for r in development};assert len(excluded_dev)==30
    # Read only identity fields from the previous protocol. Never use its outputs,
    # predictions, embeddings, or metrics for selection or analysis.
    previous=json.loads((ROOT/'docs/experiment_results/pv_vlm_semantic_confirmation/summary.json').read_text())['protocol']['confirmation_sample']
    excluded_previous={r['source_image_id'] for r in previous};assert len(excluded_previous)==60
    assert not excluded_dev & excluded_previous
    with (ROOT/'manifests/primary_split_manifest.csv').open(newline='') as stream:
        train=[r for r in csv.DictReader(stream) if r['dataset']=='plantvillage' and r['split']=='train' and r['primary_included'].lower()=='true']
    rng=random.Random(42);selected=[]
    for name in CLASSES:
        pool=sorted([r for r in train if r['canonical_label']==name and r['image_id'] not in excluded_dev|excluded_previous],key=lambda r:r['image_id'])
        if len(pool)<20:raise RuntimeError('Insufficient unseen PV-train images')
        selected.extend(rng.sample(pool,20))
    rng.shuffle(selected)
    sample=[dict(r,neutral_id=f'pv_confirm2_{i:03d}') for i,r in enumerate(selected,1)]
    sources={r['image_id'] for r in sample};assert len(sources)==120
    assert Counter(r['canonical_label'] for r in sample)==Counter({c:20 for c in CLASSES})
    assert len(sources&excluded_dev)==len(sources&excluded_previous)==0
    from PIL import Image
    for r in sample:
        path=(ROOT/r['relative_path']).resolve()
        assert r['dataset']=='plantvillage' and r['split']=='train'
        assert path.is_relative_to((ROOT/'data/processed/tomato_plantvillage').resolve()) and path.is_file()
        with Image.open(path) as image:assert image.size==(256,256)
    return {'sample':sample,'excluded_development_source_ids':sorted(excluded_dev),
            'excluded_previous_confirmation_source_ids':sorted(excluded_previous),
            'development_overlap_count':0,'previous_confirmation_overlap_count':0}


def prepare():
    protocol=frozen_protocol();manifest=sample_manifest()
    protocol['sample_sha256']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    for path,expected in [(OUT/'sample_manifest.json',manifest)]:
        if path.exists():
            if json.loads(path.read_text())!=expected:raise RuntimeError('Stored sample mismatch; refusing resampling')
        else:write_json(path,expected)
    path=OUT/'summary.json'
    if path.exists():
        summary=json.loads(path.read_text())
        if summary['protocol']!=protocol:raise RuntimeError('Cached protocol mismatch')
    else:
        summary={'protocol':protocol,'status':'prepared_no_inference','historical_context':HISTORY,'overlap_checks':{k:manifest[k] for k in ['development_overlap_count','previous_confirmation_overlap_count']},'new_api_calls':0}
        write_json(path,summary)
    return manifest['sample'],summary


def request_payload(key,prompt,image,sample):
    assert prompt==PROMPTS[key].read_text() and digest(PROMPTS[key])==EXPECTED_HASHES[key]
    text=prompt+'\n'+json.dumps(SCHEMAS[key])
    for row in sample:
        path=Path(row['relative_path'])
        for forbidden in [row['canonical_label'],row['original_label'],row['image_id'],row['relative_path'],path.name,path.parent.name,row['neutral_id']]:
            assert forbidden.lower() not in text.lower(),'Dynamic source/class leakage'
    content=[{'type':'input_text','text':prompt},{'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(image).decode('ascii')}]
    return {'model':MODEL,'temperature':0,'store':False,'input':[{'role':'user','content':content}],
            'text':{'format':{'type':'json_schema','strict':True,'name':NAMES[key],'schema':SCHEMAS[key]}}}


def validate(key,raw,sample):
    # Frozen scientific validators are called unchanged. Only audit retention and
    # source-identity isolation are added around V2's existing validation result.
    result=v2.parse_and_validate(raw) if key=='v2' else v4.validate_raw(raw,sample)
    result['raw_response']=raw
    if result['fields'] is None:
        try:
            def unique(pairs):
                value={}
                for name,item in pairs:
                    if name in value:raise ValueError('Duplicate JSON key')
                    value[name]=item
                return value
            parsed=json.loads(raw,object_pairs_hook=unique)
            if isinstance(parsed,dict):result['fields']=parsed
            else:result['parsed_output']=parsed
        except (ValueError,TypeError):pass
    if result['parse_valid']:
        text='\n'.join(result['fields'].values())
        source=bool(re.search(r'pv_confirm2_\d+|plantvillage_[0-9a-f]+|data/(?:raw|processed)/|/Users/|file://|\b[\w.-]+\.(?:jpe?g|png|webp|bmp)\b',text,re.I))
        for row in sample:
            for value in [row['canonical_label'],row['original_label'],row['image_id'],row['relative_path'],Path(row['relative_path']).name,Path(row['relative_path']).parent.name,row['neutral_id']]:
                if value.lower() in text.lower():source=True
        if source:
            result.update(validation_pass=False,leakage=True)
            result['errors'].append('source_class_path_or_filename_leakage')
    return result


def save_records(key,records):
    path=OUT/f'{key}_descriptions.jsonl';temp=path.with_suffix('.jsonl.tmp')
    temp.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in records));temp.replace(path)


def record_counts(records):
    return {key:{'record_count':len(rows),'completed_count':sum(r['completed'] for r in rows),
                 'valid_count':sum(r['validation_pass'] for r in rows),
                 'failures':[{'image_id':r['image_id'],'errors':r['errors']} for r in rows if not r['validation_pass']],
                 'returned_model_versions':sorted({r['model_version'] for r in rows if r.get('model_version')})} for key,rows in records.items()}


def infer(sample,summary):
    if any((OUT/f'{key}_descriptions.jsonl').exists() or (ART/f'{key}_embeddings_siglip.pt').exists() for key in CANDIDATES):
        raise RuntimeError('Responses/artifacts already exist; no silent reuse or overwrite. Use --embed-only or --analyze-only explicitly.')
    api_key=os.environ.get('OPENAI_API_KEY','').strip()
    if not api_key:raise RuntimeError('OPENAI_API_KEY is not set; no request sent')
    from openai import OpenAI
    records={key:[] for key in CANDIDATES};attempted=0
    with OpenAI(api_key=api_key,base_url='https://api.openai.com/v1',timeout=60,max_retries=0) as client:
        for row in sample:
            # Encode once; this exact byte string is shared by the paired calls.
            try:
                image,original,sent=encode_image(ROOT/row['relative_path']);assert original==sent==[256,256]
                image_error=None
            except AssertionError:raise
            except Exception as exc:image=None;image_error=type(exc).__name__
            for key in CANDIDATES:
                record={'image_id':row['neutral_id'],'source_image_id':row['image_id'],'hidden_ground_truth_class':row['canonical_label'],
                        'model':MODEL,'model_version':None,'completed':False,'protocol':summary['protocol'],'raw_response':'',
                        'image_bytes_sha256':hashlib.sha256(image).hexdigest() if image is not None else None}
                if image_error:record['error_type']='image_read:'+image_error
                else:
                    try:
                        attempted+=1
                        response=client.responses.create(**request_payload(key,PROMPTS[key].read_text(),image,sample))
                        record.update(raw_response=response.output_text or '',model_version=response.model,response_id=response.id,completed=response.status=='completed')
                    except AssertionError:raise
                    except Exception as exc:
                        code=getattr(exc,'status_code',None);record.update(error_type=type(exc).__name__,http_status=code if isinstance(code,int) else None)
                record.update(validate(key,record['raw_response'],sample))
                if not record['completed']:record['validation_pass']=False;record['errors'].append('inference_not_completed')
                records[key].append(record);save_records(key,records[key])
                summary.update(status='inference_in_progress',inference=record_counts(records),new_api_calls=attempted)
                write_json(OUT/'summary.json',summary)
    summary.update(status='generated_not_embedded',inference=record_counts(records));write_json(OUT/'summary.json',summary)
    return records


def load_records(sample,summary):
    records={}
    for key in CANDIDATES:
        rows=[json.loads(line) for line in (OUT/f'{key}_descriptions.jsonl').read_text().splitlines() if line.strip()]
        byid={r['image_id']:r for r in rows}
        if len(rows)!=120 or len(byid)!=120 or set(byid)!={r['neutral_id'] for r in sample}:raise RuntimeError('Need exactly 120 unique manifest records per method')
        ordered=[]
        for row in sample:
            r=byid[row['neutral_id']]
            if r['protocol']!=summary['protocol'] or r['model']!=MODEL or r['source_image_id']!=row['image_id'] or r['hidden_ground_truth_class']!=row['canonical_label']:raise RuntimeError('Cached response provenance mismatch')
            checked=validate(key,r['raw_response'],sample)
            if checked['fields']!=r['fields']:raise RuntimeError('Raw/parsed fields mismatch')
            ordered.append({**r,**checked,'validation_pass':checked['validation_pass'] and r['completed']})
        records[key]=ordered
    return records


def require_complete(records,summary):
    summary['inference']=record_counts(records);write_json(OUT/'summary.json',summary)
    if any(len(rows)!=120 or not all(r['completed'] and r['validation_pass'] for r in rows) for rows in records.values()):
        summary['status']='blocked_invalid_or_missing_paired_outputs';write_json(OUT/'summary.json',summary)
        raise RuntimeError('Need 120 valid representations for BOTH methods; see failure records; no dropping/replacement')
    for a,b in zip(records['v2'],records['v4']):
        assert a['image_id']==b['image_id'] and a['source_image_id']==b['source_image_id']
        assert a['image_bytes_sha256']==b['image_bytes_sha256'] and a['image_bytes_sha256']


def embed(sample,summary,records,cache_dir):
    require_complete(records,summary)
    import torch,transformers
    from transformers import AutoTokenizer,SiglipTextModel
    torch.manual_seed(0);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    options={'revision':REVISION,'cache_dir':cache_dir}
    tokenizer=AutoTokenizer.from_pretrained(ENCODER,**options)
    encoder,loading=SiglipTextModel.from_pretrained(ENCODER,output_loading_info=True,**options)
    if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):raise RuntimeError('Incomplete encoder weights')
    encoder=encoder.to('cpu',dtype=torch.float32).eval();encoder.requires_grad_(False)
    assert encoder.config.max_position_embeddings==64 and tokenizer.num_special_tokens_to_add(pair=False)==1
    ART.mkdir(parents=True,exist_ok=True)
    for key in CANDIDATES:
        texts=[r['fields'][CANDIDATES[key]] for r in records[key]]
        x,chunks=encode_texts_lossless(texts,tokenizer,encoder);assert x.shape==(120,768)
        torch.save({'protocol':summary['protocol'],'image_ids':[r['neutral_id'] for r in sample],
                    'source_image_ids':[r['image_id'] for r in sample],'hidden_ground_truth_classes':[r['canonical_label'] for r in sample],
                    'candidate':CANDIDATES[key],'texts':texts,'embeddings':x,'chunk_metadata':chunks,
                    'torch_version':str(torch.__version__),'transformers_version':transformers.__version__},ART/f'{key}_embeddings_siglip.pt')


def analyze(sample,summary,records):
    require_complete(records,summary)
    import torch
    ids=[r['neutral_id'] for r in sample];sources=[r['image_id'] for r in sample];labels=[r['canonical_label'] for r in sample]
    results={};encoding={}
    for key in CANDIDATES:
        artifact=torch.load(ART/f'{key}_embeddings_siglip.pt',map_location='cpu',weights_only=True)
        assert artifact['protocol']==summary['protocol'] and artifact['image_ids']==ids and artifact['source_image_ids']==sources and artifact['hidden_ground_truth_classes']==labels and artifact['candidate']==CANDIDATES[key]
        assert artifact['texts']==[r['fields'][CANDIDATES[key]] for r in records[key]]
        x=artifact['embeddings'];results[key]=diagnostics(x,labels,CLASSES,ids)
        chunks=artifact['chunk_metadata']
        encoding[key]={'embedding_shape':list(x.shape),'l2_norms':x.norm(dim=-1).tolist(),'all_finite':bool(torch.isfinite(x).all()),'token_chunk_diagnostics':chunks,
                       'content_token_counts':[c['content_token_count'] for c in chunks],
                       'chunk_counts':[c['chunk_count'] for c in chunks],
                       'max_content_token_length':max(c['content_token_count'] for c in chunks),
                       'max_chunk_total_token_length':max(max(c['chunk_total_token_counts']) for c in chunks),
                       'multi_chunk_case_count':sum(c['chunk_count']>1 for c in chunks)}
    paired=Counter({'both_correct':0,'v2_only_correct':0,'v4_only_correct':0,'both_wrong':0});groups={k:[] for k in paired}
    for a,b in zip(results['v2']['per_image'],results['v4']['per_image']):
        assert a['image_id']==b['image_id']
        group='both_correct' if a['correct'] and b['correct'] else 'v2_only_correct' if a['correct'] else 'v4_only_correct' if b['correct'] else 'both_wrong'
        paired[group]+=1;groups[group].append(a['image_id'])
    deltas={k:results['v4'][k]-results['v2'][k] for k in ['accuracy','macro_f1','balanced_accuracy','cosine_gap']}
    recalls={c:{'v2':results['v2']['per_class_recall'][c],'v4':results['v4']['per_class_recall'][c],'v4_minus_v2':results['v4']['per_class_recall'][c]-results['v2']['per_class_recall'][c]} for c in CLASSES}
    confusion_changes=[]
    for i,j in [(0,4),(1,2),(3,5)]:
        for source,target in [(i,j),(j,i)]:
            counts={key:results[key]['confusion_matrix'][source][target] for key in CANDIDATES}
            confusion_changes.append({'true_class':CLASSES[source],'predicted_class':CLASSES[target],**counts,'v4_minus_v2':counts['v4']-counts['v2']})
    lookup={key:{r['image_id']:r for r in records[key]} for key in records};preds={key:{r['image_id']:r for r in results[key]['per_image']} for key in results}
    audit=[]
    for group,values in groups.items():
        for image_id in sorted(values)[:2]:
            audit.append({'group':group,'image_id':image_id,'hidden_true_class':preds['v2'][image_id]['true_class'],
                          **{key:{'summary':lookup[key][image_id]['fields'][CANDIDATES[key]],'prediction':preds[key][image_id]['predicted_class']} for key in CANDIDATES}})
    decision={'status':'requires_joint_quantitative_and_qualitative_review_no_automatic_winner',
              'quantitative_evidence':{'v4_minus_v2':deltas,'paired_correctness':dict(paired),'class_recalls':recalls},
              'policy':summary['protocol']['decision_policy'],
              'qualitative_review':'Review the deterministic cases for added morphology, checklist-like/unsupported cue claims, broader V2 context, negative cue dominance and loss of specific morphology. Text alone cannot establish visual support; no automatic biological judgment.',
              'no_significance_claim':True,'no_prompt_changes_on_this_set':True}
    write_json(OUT/'paired_error_analysis.json',{'selection_rule':'first two neutral IDs in each correctness group; fewer if unavailable','cases':audit,'directional_confusion_changes':confusion_changes,'decision':decision})
    summary.update(status='completed_frozen_confirmation',diagnostics=results,encoding=encoding,paired_correctness=dict(paired),v4_minus_v2=deltas,per_class_recall_comparison=recalls,directional_confusion_changes=confusion_changes,decision=decision)
    write_json(OUT/'summary.json',summary)


def validator_tests():
    for key in CANDIDATES:
        fields={k:'Green leaf.' for k in SCHEMAS[key]['required']}
        assert validate(key,json.dumps(fields),[])['validation_pass']
        for bad in [{},dict(fields,extra='x'),dict(fields,color_pattern={'nested':'x'}),dict(fields,color_pattern=1)]:
            raw=json.dumps(bad);r=validate(key,raw,[]);assert not r['validation_pass'] and r['raw_response']==raw and r['fields']==bad
        assert not validate(key,'malformed',[])['validation_pass']
    # V2 remains exactly its original validator, including its broad lexical rules.
    for n,valid in [(150,True),(151,False)]:
        fields={k:'leaf' for k in SCHEMAS['v2']['required']};fields['color_pattern']=' '.join(['leaf']*(n-5))
        assert validate('v2',json.dumps(fields),[])['validation_pass']==valid
    for n,valid in [(200,True),(201,False)]:
        fields={k:'leaf' for k in SCHEMAS['v4']['required']};fields['color_pattern']=' '.join(['leaf']*(n-5))
        assert validate('v4',json.dumps(fields),[])['validation_pass']==valid
    for n,valid in [(45,True),(46,False)]:
        fields={k:'leaf' for k in SCHEMAS['v4']['required']};fields['evidence_summary']=' '.join(['leaf']*n)
        assert validate('v4',json.dumps(fields),[])['validation_pass']==valid
    for text,valid,error in [('mosaic-like green mottling',True,None),('multiple dark spots',True,None),('Bacterial spot',False,'disease_or_pathogen_name_leakage'),('useful for disease differentiation',False,'meta_commentary')]:
        fields={k:'leaf' for k in SCHEMAS['v4']['required']};fields['evidence_summary']=text
        r=validate('v4',json.dumps(fields),[]);assert r['validation_pass']==valid
        if error:assert error in r['errors']
    return 'passed: frozen schemas, V2 150/151, V4 200/201 and 45/46, named/morphology/meta distinction, malformed/schema audit retention'


def exploratory_common_valid(cache_dir):
    """Selection-biased sensitivity analysis; never changes primary confirmation."""
    import numpy as np
    import torch
    from sklearn.metrics import accuracy_score,balanced_accuracy_score,confusion_matrix,f1_score,recall_score
    from transformers import AutoTokenizer,SiglipTextModel
    label='EXPLORATORY_COMMON_VALID_115_NOT_CONFIRMATORY'
    summary_path=OUT/'summary.json';summary=json.loads(summary_path.read_text())
    assert summary['status']=='blocked_invalid_or_missing_paired_outputs'
    primary={k:v for k,v in summary.items() if k!='exploratory_common_valid_sensitivity'}
    manifest=json.loads((OUT/'sample_manifest.json').read_text());sample=manifest['sample']
    expected=frozen_protocol()
    expected['sample_sha256']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    assert summary['protocol']==expected,'Frozen protocol mismatch'
    protected=[OUT/'sample_manifest.json',OUT/'v2_descriptions.jsonl',OUT/'v4_descriptions.jsonl',ROOT/'research_log.md',ROOT/'scripts/siglip_text_encoding.py',*PROMPTS.values()]
    before={p:digest(p) for p in protected}
    records=load_records(sample,summary)
    valid={k:{r['image_id'] for r in rows if r['validation_pass']} for k,rows in records.items()}
    assert len(valid['v2'])==115 and len(valid['v4'])==120
    common=valid['v2']&valid['v4'];assert len(common)==115
    excluded=sorted({r['neutral_id'] for r in sample}-common)
    assert excluded==['pv_confirm2_018','pv_confirm2_045','pv_confirm2_087','pv_confirm2_094','pv_confirm2_117']
    failures=[r for r in records['v2'] if not r['validation_pass']]
    assert [r['image_id'] for r in failures]==excluded
    assert [r['total_word_count'] for r in failures]==[160,151,152,168,157]
    assert all(r['errors']==['over_150_words'] for r in failures)
    selected=[r for r in sample if r['neutral_id'] in common]
    ids=[r['neutral_id'] for r in selected];labels=[r['canonical_label'] for r in selected]
    support=dict(Counter(labels));y=np.array([CLASSES.index(c) for c in labels])
    lookup={k:{r['image_id']:r for r in rows} for k,rows in records.items()}
    for image_id in ids:
        assert lookup['v2'][image_id]['image_bytes_sha256']==lookup['v4'][image_id]['image_bytes_sha256']
    torch.manual_seed(0);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    options={'revision':REVISION,'cache_dir':cache_dir,'local_files_only':True}
    tokenizer=AutoTokenizer.from_pretrained(ENCODER,**options)
    encoder,loading=SiglipTextModel.from_pretrained(ENCODER,output_loading_info=True,**options)
    if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):raise RuntimeError('Incomplete encoder checkpoint')
    encoder=encoder.to('cpu',dtype=torch.float32).eval();encoder.requires_grad_(False)
    assert encoder.config.max_position_embeddings==64 and tokenizer.num_special_tokens_to_add(pair=False)==1
    results={}
    for key in CANDIDATES:
        texts=[lookup[key][image_id]['fields'][CANDIDATES[key]] for image_id in ids]
        x,chunks=encode_texts_lossless(texts,tokenizer,encoder)
        assert x.shape==(115,768) and torch.isfinite(x).all()
        assert torch.allclose(x.norm(dim=-1),torch.ones(115),atol=1e-6,rtol=0)
        cosine=x@x.T;same=[];different=[];per_image=[];pred=[]
        for i in range(115):
            for j in range(i+1,115):
                (same if y[i]==y[j] else different).append(float(cosine[i,j]))
            prototypes=[]
            for c,name in enumerate(CLASSES):
                indices=[j for j in range(115) if y[j]==c and j!=i]
                assert len(indices)==support[name]-(int(y[i])==c)
                mean=x[indices].mean(0);assert mean.norm()>0
                prototypes.append(mean/mean.norm())
            scores=x[i]@torch.stack(prototypes).T;prediction=int(scores.argmax());pred.append(prediction)
            per_image.append({'metric_label':label,'image_id':ids[i],'true_class':labels[i],'predicted_class':CLASSES[prediction],'cosine_scores':scores.tolist(),'correct':prediction==int(y[i])})
        def stats(values):return {'metric_label':label,'count':len(values),'mean':float(np.mean(values)),'sample_std':float(np.std(values,ddof=1))}
        results[key]={'metric_label':label,'accuracy':float(accuracy_score(y,pred)),
            'macro_f1':float(f1_score(y,pred,labels=list(range(6)),average='macro',zero_division=0)),
            'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
            'same_class_cosine':stats(same),'different_class_cosine':stats(different),
            'cosine_gap':float(np.mean(same)-np.mean(different)),
            'per_class_support':support,'per_class_recall':dict(zip(CLASSES,recall_score(y,pred,labels=list(range(6)),average=None,zero_division=0).tolist())),
            'confusion_matrix':confusion_matrix(y,pred,labels=list(range(6))).tolist(),
            'confusion_matrix_axes':'rows=true, columns=predicted','class_order':CLASSES,
            'per_image':per_image,'embedding_shape':list(x.shape),'l2_norms':x.norm(dim=-1).tolist(),'all_finite':bool(torch.isfinite(x).all()),'token_chunk_diagnostics':chunks}
    paired=Counter({'both_correct':0,'v2_only_correct':0,'v4_only_correct':0,'both_wrong':0})
    for a,b in zip(results['v2']['per_image'],results['v4']['per_image']):
        assert a['image_id']==b['image_id']
        paired['both_correct' if a['correct'] and b['correct'] else 'v2_only_correct' if a['correct'] else 'v4_only_correct' if b['correct'] else 'both_wrong']+=1
    pairs=[]
    for i,j in [(0,4),(1,2),(3,5)]:
        pairs.append({'metric_label':label,'classes':[CLASSES[i],CLASSES[j]],
            'directions':[{'true_class':CLASSES[a],'predicted_class':CLASSES[b],**{k:results[k]['confusion_matrix'][a][b] for k in CANDIDATES}} for a,b in [(i,j),(j,i)]]})
    report={'metric_label':label,'scope':'All metrics in this subtree are EXPLORATORY_COMMON_VALID_115_NOT_CONFIRMATORY',
        'selection_warning':'Exclusion is induced by V2 total word-limit compliance and may be non-random. This complete-case subset is not a successful confirmation.',
        'original_confirmation_decision_rule_applied':False,'winner_declared':False,'new_api_calls':0,
        'sample_count':115,'image_ids':ids,'excluded_ids':excluded,'per_class_support':support,
        'encoder':ENCODER,'encoder_revision':REVISION,'encoding_rule':ENCODING_RULE,'embeddings_persisted':False,
        'v2_operational_compliance':{'metric_label':label,'valid':115,'total':120,'failures':5,'failure_fraction':5/120,'failure_percent':100*5/120,
            'failure_word_counts':[r['total_word_count'] for r in failures],'failures':[{'image_id':r['image_id'],'total_word_count':r['total_word_count']} for r in failures]},
        'representations':results,'paired_correctness':{'metric_label':label,**dict(paired)},'confusion_pair_summaries':pairs,
        'cached_raw_output_sha256':{k:digest(OUT/f'{k}_descriptions.jsonl') for k in CANDIDATES}}
    assert all(digest(p)==value for p,value in before.items()),'Protected input changed'
    assert json.loads(summary_path.read_text())==summary,'Summary changed during analysis'
    summary['exploratory_common_valid_sensitivity']=report
    assert {k:v for k,v in summary.items() if k!='exploratory_common_valid_sensitivity'}==primary
    write_json(summary_path,summary)
    print(json.dumps({'primary_status':summary['status'],'metric_label':label,'per_class_support':support,
        'results':{k:{name:r[name] for name in ['accuracy','macro_f1','balanced_accuracy','same_class_cosine','different_class_cosine','cosine_gap','per_class_recall','confusion_matrix']} for k,r in results.items()},
        'paired_correctness':dict(paired),'confusion_pairs':pairs},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);modes=parser.add_mutually_exclusive_group(required=True)
    for mode in ['preflight','run','embed-only','analyze-only','exploratory-common-valid']:modes.add_argument('--'+mode,action='store_true')
    parser.add_argument('--cache-dir',type=Path);args=parser.parse_args()
    if os.environ.get('OPENAI_MODEL',MODEL)!=MODEL:raise RuntimeError('Frozen confirmation requires gpt-4.1-mini')
    if args.exploratory_common_valid:
        exploratory_common_valid(args.cache_dir);return
    sample,summary=prepare()
    for row in sample:
        payloads=[request_payload(key,PROMPTS[key].read_text(),b'preflight-image-bytes',sample) for key in CANDIDATES]
        assert payloads[0]['input'][0]['content'][1]==payloads[1]['input'][0]['content'][1]
    if args.preflight:
        print(json.dumps({'status':'preflight_pass','prompt_hashes':EXPECTED_HASHES,'sample_count':len(sample),'per_class_counts':dict(Counter(r['canonical_label'] for r in sample)),
                          'overlap_checks':summary['overlap_checks'],'all_pv_train':True,'paired_same_bytes':True,'label_blind_assertions':True,'validator_tests':validator_tests(),
                          'previous_60_used_only_for_source_id_exclusion':True,'api_calls':0,'siglip_inference':False},indent=2));return
    records=infer(sample,summary) if args.run else load_records(sample,summary)
    if not args.analyze_only:embed(sample,summary,records,args.cache_dir)
    analyze(sample,summary,records)


if __name__=='__main__':main()
