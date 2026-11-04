import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyscf import lib

from meta_lucj_sqd.chemistry import build_chemistry, hf_active_energy


def main():
    spec=json.loads(Path('configs/phase3_geometries.json').read_text())
    base=json.loads(Path(spec['base_config']).read_text())
    chemistry_base=json.loads(Path(base['base_config']).read_text())
    phase2=json.loads(Path(spec['phase2_summary']).read_text())
    out=Path('results')/datetime.now(timezone.utc).strftime('phase3_geometries_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    report=dict(config=spec,points=[],status='running')
    lib.num_threads(chemistry_base['threads'])
    for distance in spec['distances_angstrom']:
        point=out/f'R_{distance:.2f}'
        point.mkdir()
        previous=next(p for p in phase2['points'] if p['distance_angstrom']==distance)
        reference=json.loads(Path(previous['source_report']).read_text())
        cfg=dict(chemistry_base,distance_angstrom=distance)
        for key in ['molecule','basis','distance_angstrom','frozen_core','expected_norb','expected_nelec','scf_tol','max_cycle']:
            if cfg[key]!=reference['config'][key]:
                raise ValueError('Physical reference configuration mismatch: '+key)
        chemistry=build_chemistry(cfg)
        if abs(chemistry.mf.e_tot-reference['hf_total'])>1e-10 or abs(hf_active_energy(chemistry)-chemistry.mf.e_tot)>1e-8:
            raise ValueError('Reference HF consistency failed')
        integrals=point/'integrals.npz'
        np.savez_compressed(integrals,h1=chemistry.h1,eri=chemistry.eri,ecore=chemistry.ecore)
        config=dict(base,distance_angstrom=distance,evaluation_seeds=spec['evaluation_seeds'],training_seed=spec['training_seed'],
                    optimizer=dict(base['optimizer'],iterations=spec['iterations'],seed=spec['optimizer_seed']),
                    reference_report=previous['source_report'],reference_integrals=str(integrals))
        config_path=point/'config.json';config_path.write_text(json.dumps(config,indent=2))
        print('Starting',distance,flush=True)
        with (point/'execution.log').open('w') as log:
            completed=subprocess.run([sys.executable,'scripts/run_phase3.py','--config',str(config_path)],stdout=log,stderr=subprocess.STDOUT)
        paths=[s for s in (point/'execution.log').read_text().splitlines() if s.startswith('results/') and s.endswith('/report.json')]
        entry=dict(distance_angstrom=distance,config=str(config_path),exit_code=completed.returncode,status='failed',
                   reference_provenance=previous['source_report'],integrals_regenerated=True)
        if paths:
            entry.update(report=paths[-1],status=json.loads(Path(paths[-1]).read_text())['status'])
        report['points'].append(entry)
        (out/'report.json').write_text(json.dumps(report,indent=2))
        print('Completed',distance,entry['status'],flush=True)
    report['status']='success' if all(p['status']=='success' for p in report['points']) else 'validation_incomplete'
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
