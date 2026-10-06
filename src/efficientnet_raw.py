"""Source-only EfficientNet-B0 training and external evaluation."""
import csv
import hashlib
import json
import os
import random
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torchvision
from PIL import Image
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms as T

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ['Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight', 'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot', 'Tomato___Tomato_mosaic_virus']


def csv_write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate(config):
    contract = json.loads((ROOT / config['class_set']).read_text())
    assert contract['frozen'] and contract['canonical_classes'] == EXPECTED
    with (ROOT / config['manifest']).open() as f:
        all_rows = list(csv.DictReader(f))
    rows = [r for r in all_rows if r['primary_included'] == 'True']
    assert {r['canonical_label'] for r in rows} == set(EXPECTED)
    assert len({r['image_id'] for r in all_rows}) == len(all_rows)
    splits = {s: [r for r in rows if r['split'] == s] for s in ['train', 'validation', 'test', 'external_target_test']}
    assert sum(map(len, splits.values())) == len(rows)
    assert [len(splits[s]) for s in splits] == [5692, 1221, 1219, 603]
    for s, rr in splits.items():
        assert all(r['dataset'] == ('plantdoc' if s == 'external_target_test' else 'plantvillage') for r in rr)
        assert all((ROOT / r['relative_path']).is_file() for r in rr)
        assert {r['canonical_label'] for r in rr} == set(EXPECTED)
    for key in ['image_id', 'sha256', 'duplicate_group_id']:
        memberships = defaultdict(set)
        for s, rr in splits.items():
            for r in rr:
                if r[key]:
                    memberships[r[key]].add(s)
        assert all(len(v) == 1 for v in memberships.values()), f'{key} leakage'
    assert not any(r['duplicate_group_id'] in contract['excluded_target_duplicate_groups'] for r in splits['external_target_test'])
    print('Protocol assertions passed: six classes, disjoint source splits, no duplicate leakage, 603 external targets.', flush=True)
    return splits


class Images(Dataset):
    def __init__(self, rows, config, train=False):
        self.rows = rows
        operations = [T.RandomResizedCrop(config['image_size'], scale=tuple(config['train_crop_scale']), interpolation=T.InterpolationMode.BICUBIC), T.RandomHorizontalFlip(config['horizontal_flip_probability'])] if train else [T.Resize(config['eval_resize'], interpolation=T.InterpolationMode.BICUBIC), T.CenterCrop(config['image_size'])]
        self.transform = T.Compose(operations + [T.ToTensor(), T.Normalize(config['normalization_mean'], config['normalization_std'])])

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        with Image.open(ROOT / r['relative_path']) as im:
            x = self.transform(im.convert('RGB'))
        return x, EXPECTED.index(r['canonical_label']), i


def scores(targets, predictions):
    cm = np.zeros((6, 6), dtype=np.int64)
    np.add.at(cm, (targets, predictions), 1)
    tp = cm.diagonal().astype(float)
    recall = np.divide(tp, cm.sum(1), out=np.zeros(6), where=cm.sum(1) != 0)
    f1 = np.divide(2 * tp, cm.sum(0) + cm.sum(1), out=np.zeros(6), where=(cm.sum(0) + cm.sum(1)) != 0)
    return {'macro_f1': float(f1.mean()), 'balanced_accuracy': float(recall.mean()), 'accuracy': float(tp.sum() / cm.sum()), 'per_class_recall': dict(zip(EXPECTED, recall.tolist())), 'confusion_matrix': cm.tolist()}


@torch.inference_mode()
def evaluate(model, loader, device):
    model.eval()
    loss, targets, predictions, records = 0., [], [], []
    for x, y, indices in loader:
        logits = model(x.to(device))
        loss += nn.functional.cross_entropy(logits, y.to(device), reduction='sum').item()
        confidence, prediction = logits.softmax(1).max(1)
        for idx, truth, pred, conf in zip(indices.tolist(), y.tolist(), prediction.cpu().tolist(), confidence.cpu().tolist()):
            targets.append(truth)
            predictions.append(pred)
            records.append({'image_id': loader.dataset.rows[idx]['image_id'], 'ground_truth': EXPECTED[truth], 'prediction': EXPECTED[pred], 'confidence': conf, 'correct': truth == pred})
    return scores(targets, predictions), loss / len(targets), records


def run(config, splits):
    torch.set_num_threads(config['cpu_threads'])
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
    print('FINAL CONFIG:', json.dumps(config, indent=2), '\nDEVICE:', device, flush=True)
    # Weights cache stays inside project artifacts.
    torch.hub.set_dir(str(ROOT / 'artifacts/torch_hub'))
    base = ROOT / 'results' / config['experiment']
    checkpoints = ROOT / 'artifacts/checkpoints' / config['experiment']
    # Refuse existing runs before writing any results/checkpoints.
    for seed in config['seeds']:
        if (base / f'seed_{seed}').exists() or (checkpoints / f'seed_{seed}_best.pt').exists():
            raise FileExistsError(f'Seed {seed} artifacts exist; refusing overwrite')
    base.mkdir(parents=True, exist_ok=True)
    checkpoints.mkdir(parents=True, exist_ok=True)
    results = []
    for seed in config['seeds']:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        started = datetime.now(timezone.utc).isoformat()
        model = torchvision.models.efficientnet_b0(weights=torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 6)
        model.to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
        loaders = {s: DataLoader(Images(rr, config, train=s == 'train'), batch_size=config['batch_size'], shuffle=s == 'train', num_workers=config['num_workers'], generator=torch.Generator().manual_seed(seed)) for s, rr in splits.items()}
        folder = base / f'seed_{seed}'
        folder.mkdir()
        best, best_epoch, stale, history = -1., 0, 0, []
        # Epoch-specific checkpoints are exclusive; selected best is created only once.
        candidate = folder / 'best_candidate.pt'
        for epoch in range(1, config['max_epochs'] + 1):
            model.train()
            total_loss, correct, total = 0., 0, 0
            for x, y, _ in loaders['train']:
                x, y = x.to(device), y.to(device)
                optimizer.zero_grad(set_to_none=True)
                logits = model(x)
                loss = nn.functional.cross_entropy(logits, y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(y)
                correct += (logits.argmax(1) == y).sum().item()
                total += len(y)
            val, val_loss, _ = evaluate(model, loaders['validation'], device)
            history.append({'epoch': epoch, 'train_loss': total_loss / total, 'train_accuracy': correct / total, 'val_loss': val_loss, 'val_macro_f1': val['macro_f1'], 'learning_rate': optimizer.param_groups[0]['lr']})
            csv_write(folder / 'training_history.csv', history)
            print(f"seed={seed} epoch={epoch} train_loss={total_loss/total:.5f} val_macro_f1={val['macro_f1']:.5f}", flush=True)
            if val['macro_f1'] > best:
                best, best_epoch, stale = val['macro_f1'], epoch, 0
                state = {'model_state_dict': model.state_dict(), 'optimizer_state_dict': optimizer.state_dict(), 'epoch': epoch, 'best_validation_macro_f1': best, 'seed': seed, 'class_names': EXPECTED, 'preprocessing': {k: config[k] for k in ['image_size', 'eval_resize', 'normalization_mean', 'normalization_std', 'train_crop_scale', 'horizontal_flip_probability']}, 'config': config, 'python_rng_state': random.getstate(), 'numpy_rng_state': np.random.get_state(), 'torch_rng_state': torch.get_rng_state()}
                temp = folder / 'candidate_pending.pt'
                torch.save(state, temp)
                os.replace(temp, candidate)
            else:
                stale += 1
            if stale >= config['early_stopping_patience']:
                break
        checkpoint = checkpoints / f'seed_{seed}_best.pt'
        # Hard link fails if best checkpoint already exists; never overwrites it.
        os.link(candidate, checkpoint)
        candidate.unlink()
        state = torch.load(checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(state['model_state_dict'])
        source, _, source_records = evaluate(model, loaders['test'], device)
        target, _, target_records = evaluate(model, loaders['external_target_test'], device)
        metadata = {'seed': seed, 'config': config, 'timestamp': started, 'finished_timestamp': datetime.now(timezone.utc).isoformat(), 'git_commit_hash': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'git_worktree_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True), 'device': str(device), 'pytorch_version': torch.__version__, 'torchvision_version': torchvision.__version__, 'manifest_sha256': hashlib.sha256((ROOT / config['manifest']).read_bytes()).hexdigest(), 'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'determinism': 'deterministic algorithms warn_only; backend may have unsupported operations'}
        metrics = {**metadata, 'best_epoch': best_epoch, 'validation_macro_f1': best, **{'source_test_' + k: source[k] for k in ['macro_f1', 'balanced_accuracy', 'accuracy']}, **{'target_' + k: target[k] for k in ['macro_f1', 'balanced_accuracy', 'accuracy']}, 'delta_macro_f1': source['macro_f1'] - target['macro_f1'], 'target_per_class_recall': target['per_class_recall'], 'source_per_class_recall': source['per_class_recall'], 'source_confusion_matrix': source['confusion_matrix'], 'target_confusion_matrix': target['confusion_matrix']}
        (folder / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
        csv_write(folder / 'predictions_pv_test.csv', source_records)
        csv_write(folder / 'predictions_plantdoc.csv', target_records)
        results.append(metrics)
        print('SEED RESULT:', json.dumps(metrics), flush=True)
        del state, model, optimizer, loaders
        if device.type == 'mps':
            torch.mps.empty_cache()
    keys = ['source_test_macro_f1', 'source_test_balanced_accuracy', 'source_test_accuracy', 'target_macro_f1', 'target_balanced_accuracy', 'target_accuracy', 'delta_macro_f1']
    summary = {'seed_results': results, 'std_definition': 'sample standard deviation ddof=1', 'aggregate': {k: {'mean': float(np.mean([r[k] for r in results])), 'std': float(np.std([r[k] for r in results], ddof=1))} for k in keys}, 'target_per_class_recall': {c: {'mean': float(np.mean([r['target_per_class_recall'][c] for r in results])), 'std': float(np.std([r['target_per_class_recall'][c] for r in results], ddof=1))} for c in EXPECTED}}
    (base / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    csv_write(base / 'summary.csv', [{'seed': r['seed'], **{k: r[k] for k in keys}} for r in results] + [{'seed': stat, **{k: summary['aggregate'][k][stat] for k in keys}} for stat in ['mean', 'std']])
    with (ROOT / 'research_log.md').open('a') as f:
        f.write('\n### EfficientNet-B0 RAW baseline — ' + datetime.now().strftime('%Y-%m-%d') + '\n\n')
        f.write('Aynı dondurulmuş splitlerle seed 42, 0, 1 çalıştırıldı. Config: `configs/efficientnet_b0_raw.json`; checkpoint seçimi yalnızca PV validation Macro-F1 ile yapıldı.\n\n')
        for r in results:
            f.write(f"- Seed {r['seed']}: source Macro-F1 {r['source_test_macro_f1']:.4f}, target Macro-F1 {r['target_macro_f1']:.4f}, delta {r['delta_macro_f1']:.4f}.\n")
        f.write('\nÜç seed ortalamaları (örnek std): ' + json.dumps(summary['aggregate']) + '\n\n')
        f.write('PlantDoc sınıf recall: ' + json.dumps(summary['target_per_class_recall']) + '\n\n')
        f.write('Delta tanımlayıcı alan kaymasıdır, nedensellik iddiası değildir. Sıradaki adım bu baseline sonuçlarını incelemektir; başka deney başlatılmadı.\n')
    return summary
