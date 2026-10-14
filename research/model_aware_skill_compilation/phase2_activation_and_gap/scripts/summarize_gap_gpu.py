"""Join private five-second GPU samples to scored gap trial windows."""
import json
from pathlib import Path

study = Path(__file__).resolve().parents[1]
manifest = json.loads((study / 'gap-manifest.json').read_text())
samples = []
for line in (study / 'evidence/gpu-samples.jsonl').read_text().splitlines():
    try:
        sample = json.loads(line)
    except json.JSONDecodeError:
        continue
    if sample.get('exit') != 0:
        continue
    gpus = {}
    for raw in sample['rows']:
        parts = [part.strip() for part in raw.split(',')]
        if len(parts) != 4:
            continue
        try:
            gpus[int(parts[0])] = {'memory_mib': float(parts[1]),
                                    'util_percent': float(parts[2]),
                                    'power_w': float(parts[3])}
        except ValueError:
            pass
    samples.append((sample['epoch'], gpus))
rows = []
for cell in manifest['trial_cells']:
    name = f"p2-gap-{cell['task_id']}-{cell['model']}-S2-r1"
    path = study / 'trials' / name / 'result.json'
    if not path.exists():
        continue
    result = json.loads(path.read_text())
    ids = manifest['models'][cell['model']]['gpu_ids']
    window = [(t, {i: g[i] for i in ids if i in g}) for t, g in samples
              if result['started_epoch'] <= t <= result['finished_epoch']]
    energy = 0.0
    for index, (time, gpus) in enumerate(window[:-1]):
        dt = min(5.0, max(0.0, window[index + 1][0] - time))
        energy += sum(row['power_w'] for row in gpus.values()) * dt / 3600
    rows.append({'trial_id': name, 'gpu_ids': ids, 'sample_count': len(window),
                 'peak_memory_mib': max((row['memory_mib'] for _, gpu in window
                                         for row in gpu.values()), default=None),
                 'sampled_energy_wh': round(energy, 2),
                 'energy_method': '5-second nvidia-smi integration; last interval omitted'})
out = {'sampler': 'nvidia-smi every 5 seconds on AutoDL host',
       'monetary_cost': 'unknown: provider billing rate not recorded',
       'rows': rows}
(study / 'evidence/gap-gpu-by-trial.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'trial_count': len(rows), 'samples': len(samples)}))
