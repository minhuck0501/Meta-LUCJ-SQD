from meta_lucj_sqd.plotting import plot_report
import json
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/phase4.json')
    args=parser.parse_args()
    spec=json.loads(Path(args.config).read_text())
    template=json.loads(Path(spec['base_config']).read_text())
    geometry=json.loads(Path(spec['geometry_summary']).read_text())
    baseline={point['distance_angstrom']:point['source_report'] for point in geometry['points']}
    baseline[1.2]=spec['center_report']
    out=Path('results')/datetime.now(timezone.utc).strftime('phase4_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    report=dict(config=spec,baselines=baseline,directions=[],status='running')
    started=time.perf_counter()
    for index,distances in enumerate(spec['directions']):
        chain=dict(distances=distances,endpoint_report=baseline[distances[0]],points=[],status='running')
        previous=baseline[distances[0]]
        for distance in distances[1:]:
            target=json.loads(Path(baseline[distance]).read_text())
            cfg=dict(template,distance_angstrom=distance,
                     reference_report=target['config']['reference_report'],
                     reference_integrals=target['config']['reference_integrals'],
                     warm_start_report=previous,transfer_method=spec.get('transfer_method','sign'),evaluation_seeds=spec['evaluation_seeds'],
                     training_seed=spec['training_seed'],
                     optimizer=dict(template['optimizer'],iterations=spec['iterations'],seed=spec['optimizer_seed']))
            config=out/f'direction{index}_R{distance:.2f}.json'
            config.write_text(json.dumps(cfg,indent=2))
            logpath=config.with_suffix('.log')
            print('Starting',index,distance,flush=True)
            with logpath.open('w') as log:
                result=subprocess.run([sys.executable,'scripts/run_phase3.py','--config',str(config)],stdout=log,stderr=subprocess.STDOUT)
            paths=[s for s in logpath.read_text().splitlines() if s.startswith('results/') and s.endswith('/report.json')]
            entry=dict(distance_angstrom=distance,status='failed',exit_code=result.returncode)
            if paths:
                previous=paths[-1]
                entry.update(report=previous,status=json.loads(Path(previous).read_text())['status'])
            chain['points'].append(entry)
            report['wall_seconds']=time.perf_counter()-started
            (out/'progress.json').write_text(json.dumps(dict(report,active_chain=chain),indent=2))
            print('Completed',index,distance,entry['status'],flush=True)
            if entry['status']!='success':
                break
        chain['status']='success' if len(chain['points'])==len(distances)-1 and all(p['status']=='success' for p in chain['points']) else 'validation_incomplete'
        report['directions'].append(chain)
        (out/'report.json').write_text(json.dumps(report,indent=2))
    report['status']='success' if all(d['status']=='success' for d in report['directions']) else 'validation_incomplete'
    report['wall_seconds']=time.perf_counter()-started
    (out/'report.json').write_text(json.dumps(report,indent=2))
    plot_report(out/'report.json')
    print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
