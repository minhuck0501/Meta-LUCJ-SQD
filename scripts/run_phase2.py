from meta_lucj_sqd.plotting import plot_report
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    spec=json.loads(Path('configs/phase2.json').read_text())
    template=json.loads(Path(spec['base_comparison']).read_text())
    base=json.loads(Path(template['base_config']).read_text())
    out=Path('results')/datetime.now(timezone.utc).strftime('phase2_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    report=dict(config=spec,points=[],status='running')
    started=time.perf_counter()
    for distance in spec['distances_angstrom']:
        point=out/f'R_{distance:.2f}'
        point.mkdir()
        cfg=dict(base,distance_angstrom=distance)
        base_path=point/'base.json'
        base_path.write_text(json.dumps(cfg,indent=2))
        comparison=dict(template,base_config=str(base_path),shot_budgets=spec['shot_budgets'])
        if distance!=base['distance_angstrom']:
            comparison.pop('reference_report',None)
            comparison.pop('reference_integrals',None)
            comparison.update(reference_tol=spec['reference_tol'],reference_max_cycle=spec['reference_max_cycle'])
        config_path=point/'comparison.json'
        config_path.write_text(json.dumps(comparison,indent=2))
        print('Starting R=',distance,flush=True)
        tick=time.perf_counter()
        entry=dict(distance_angstrom=distance,config=str(config_path))
        try:
            with (point/'execution.log').open('w') as log:
                completed=subprocess.run([sys.executable,'scripts/compare_initialization.py','--config',str(config_path)],
                                         stdout=log,stderr=subprocess.STDOUT,timeout=spec['point_timeout_seconds'],env=os.environ.copy())
            lines=(point/'execution.log').read_text().splitlines()
            paths=[s for s in lines if s.startswith('results/') and s.endswith('/report.json')]
            if paths:
                entry['report']=paths[-1]
                entry['status']=json.loads(Path(paths[-1]).read_text())['status']
            else:
                entry['status']='failed'
            entry['exit_code']=completed.returncode
        except subprocess.TimeoutExpired:
            entry['status']='timeout'
        entry['wall_seconds']=time.perf_counter()-tick
        report['points'].append(entry)
        report['wall_seconds']=time.perf_counter()-started
        (out/'report.json').write_text(json.dumps(report,indent=2))
        print('Completed',distance,entry['status'],flush=True)
    report['status']='success' if all(p['status']=='success' for p in report['points']) else 'validation_incomplete'
    (out/'report.json').write_text(json.dumps(report,indent=2))
    plot_report(out/'report.json')
    print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
