"""Join retained 5-second GPU telemetry to the frozen Agent trial windows.

The power integral is an estimate from sparse nvidia-smi samples, not a cloud
billing amount. Run after fetching gpu-samples.jsonl from the pinned host.
"""
import json
from pathlib import Path

study=Path(__file__).resolve().parents[1]
samples_file=study/'evidence/gpu-samples.jsonl'
manifest=json.loads((study/'frozen-manifest-v2.json').read_text())
samples=[]
for line in samples_file.read_text().splitlines():
    try:sample=json.loads(line)
    except json.JSONDecodeError:continue
    if sample.get('exit')!=0:continue
    gpus={}
    for row in sample['rows']:
        parts=[x.strip() for x in row.split(',')]
        if len(parts)!=4:continue
        try:gpus[int(parts[0])]={'memory_mib':float(parts[1]),
                                  'util_percent':float(parts[2]),'power_w':float(parts[3])}
        except ValueError:continue
    samples.append((sample['epoch'],gpus))

rows=[]
for cell in manifest['trial_cells']:
    trial_id=f"p2-{cell['stage']}-{cell['task_id']}-{cell['model']}-{cell['condition']}-r{cell['trial']}"
    result_file=study/'trials'/trial_id/'result.json'
    if not result_file.exists():continue
    result=json.loads(result_file.read_text())
    start,end=result['started_epoch'],result['finished_epoch']
    ids=manifest['models'][cell['model']]['gpu_ids']
    window=[(t,{i:g[i] for i in ids if i in g}) for t,g in samples if start<=t<=end]
    memory=max((v['memory_mib'] for _,g in window for v in g.values()),default=None)
    utilization={str(i):round(sum(g[i]['util_percent'] for _,g in window if i in g)
                              /max(1,sum(i in g for _,g in window)),2) for i in ids}
    # Each sampled power covers at most the nominal 5 s until the next sample.
    energy_wh=0.0
    for j,(t,g) in enumerate(window):
        dt=min(5.0,max(0.0,window[j+1][0]-t)) if j+1<len(window) else 0.0
        energy_wh+=sum(v['power_w'] for v in g.values())*dt/3600
    rows.append({'trial_id':trial_id,'sample_count':len(window),
                 'gpu_ids':ids,'peak_memory_mib':memory,
                 'mean_utilization_percent':utilization,
                 'sampled_energy_wh':round(energy_wh,2),
                 'energy_method':'5-second nvidia-smi sample integration; last interval omitted'})

out={'sampler':'nvidia-smi every 5 s on AutoDL host',
     'monetary_cost':'unknown: provider billing rate not recorded',
     'rows':rows}
(study/'evidence/gpu-by-trial.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'trials':len(rows),'samples':len(samples)}))
