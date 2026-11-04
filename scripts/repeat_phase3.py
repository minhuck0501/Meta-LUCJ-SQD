import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    spec=json.loads(Path('configs/phase3_repetitions.json').read_text())
    base=json.loads(Path(spec['base_config']).read_text())
    out=Path('results')/datetime.now(timezone.utc).strftime('phase3_repetitions_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    report=dict(config=spec,jobs=[],status='running')
    for job in spec['jobs']:
        config=dict(base,optimizer=dict(base['optimizer'],seed=job['optimizer_seed'],iterations=job['iterations']),
                    training_seed=job['training_seed'],evaluation_seeds=spec['evaluation_seeds'])
        if 'resume_report' in job:
            config['resume_report']=job['resume_report']
        config_path=out/(job['name']+'.json')
        config_path.write_text(json.dumps(config,indent=2))
        print('Starting',job['name'],flush=True)
        with (out/(job['name']+'.log')).open('w') as log:
            result=subprocess.run([sys.executable,'scripts/run_phase3.py','--config',str(config_path)],stdout=log,stderr=subprocess.STDOUT)
        paths=[s for s in (out/(job['name']+'.log')).read_text().splitlines() if s.startswith('results/') and s.endswith('/report.json')]
        entry=dict(name=job['name'],exit_code=result.returncode,status='failed')
        if paths:
            entry.update(report=paths[-1],status=json.loads(Path(paths[-1]).read_text())['status'])
        report['jobs'].append(entry)
        (out/'report.json').write_text(json.dumps(report,indent=2))
        print('Completed',job['name'],entry['status'],flush=True)
    report['status']='success' if all(j['status']=='success' for j in report['jobs']) else 'validation_incomplete'
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
