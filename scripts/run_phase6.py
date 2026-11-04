import json
import importlib.metadata
import resource
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import ffsim
import numpy as np
from pyscf import fci,lib

from meta_lucj_sqd.chemistry import build_chemistry,run_ccsd
from meta_lucj_sqd.initialization import compressed_initialization
from meta_lucj_sqd.lucj import interaction_pairs,prepare,sample
from meta_lucj_sqd.meta import fit_affine
from meta_lucj_sqd.representation import decode_operator,change_block_frame
from meta_lucj_sqd.transfer import block_polar_transfer
from meta_lucj_sqd.sqd import evaluate


def main():
    spec=json.loads(Path('configs/phase6.json').read_text())
    representation=json.loads(Path(spec['representation_report']).read_text())
    features=np.load(Path(spec['representation_report']).parent/'features.npz')
    training=features['distances'];labels=features['features']
    if any(np.any(np.isclose(training,t['distance_angstrom'])) for t in spec['targets']):
        raise ValueError('Target geometry overlaps training')
    template=json.loads(Path(spec['phase3_config']).read_text())
    base=json.loads(Path(template['base_config']).read_text());base.update(template['solver_overrides']);base['shots']=spec['shots']
    lib.num_threads(base['threads'])
    out=Path('results')/datetime.now(timezone.utc).strftime('phase6_%Y%m%dT%H%M%S');out.mkdir(parents=True)
    for source in [Path(__file__),Path('configs/phase6.json'),*Path('src/meta_lucj_sqd').glob('*.py')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,training_distances=training.tolist(),status='running',targets=[],versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','pyscf','ffsim','qiskit','qiskit-addon-sqd']})
    start=time.perf_counter()

    def save():
        report['wall_seconds']=time.perf_counter()-start
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temp=out/'report.tmp';temp.write_text(json.dumps(report,indent=2));temp.replace(out/'report.json')

    try:
        tick=time.perf_counter();model=fit_affine(training,labels,spec['ridge']);report['model_fit_seconds']=time.perf_counter()-tick
        np.savez_compressed(out/'model.npz',center=model.center,scale=model.scale,coefficients=model.coefficients)
        sources={};source_ops={};report['label_generation_wall_seconds']=0.
        for point in representation['points']:
            distance=point['distance_angstrom'];prior=json.loads(Path(point['source_report']).read_text())
            sources[distance]=build_chemistry(prior['effective_config'])
            params=np.load(Path(point['source_report']).parent/'best.npy')
            source_ops[distance]=ffsim.UCJOpSpinBalanced.from_parameters(params,norb=base['expected_norb'],n_reps=1,interaction_pairs=interaction_pairs(base['expected_norb']),with_final_orbital_rotation=True)
            report['label_generation_wall_seconds']+=prior['wall_seconds']
        anchor=sources[spec['anchor_distance_angstrom']]
        for target in spec['targets']:
            distance=target['distance_angstrom'];cfg=dict(base,distance_angstrom=distance)
            point=dict(distance_angstrom=distance,role=target['role'],methods=[],status='running');report['targets'].append(point)
            c=build_chemistry(cfg)
            np.savez_compressed(out/f'integrals_{distance:.1f}.npz',h1=c.h1,eri=c.eri,ecore=c.ecore,mo_coeff=c.mf.mo_coeff)
            tick=time.perf_counter();predicted=model.predict(distance);common=decode_operator(predicted,c.norb,1)
            _,rotation=block_polar_transfer(common,anchor,c)
            meta=change_block_frame(common,rotation,c.nelec[0]);point['meta_prediction_and_transport_seconds']=time.perf_counter()-tick
            tick=time.perf_counter();cc=run_ccsd(c,cfg);independent,diag=compressed_initialization(cc,c.norb,cfg,template['compression'],regularization=template['regularization'])
            point['independent_initialization_seconds']=time.perf_counter()-tick;point['compression']=diag
            warm_source=target['warm_source'];tick=time.perf_counter();warm,_=block_polar_transfer(source_ops[warm_source],sources[warm_source],c);point['warm_transfer_seconds']=time.perf_counter()-tick
            for method,operator in [('independent',independent),('warm',warm),('meta',meta)]:
                record=dict(method=method,rows=[]);point['methods'].append(record)
                np.save(out/f'{method}_{distance:.1f}_parameters.npy',operator.to_parameters(interaction_pairs=interaction_pairs(c.norb)))
                tick=time.perf_counter();state=prepare(operator,c.norb,c.nelec);record['state_preparation_seconds']=time.perf_counter()-tick
                if abs(np.linalg.norm(state)-1)>1e-10:
                    raise RuntimeError('State norm failed')
                for seed in spec['evaluation_seeds']:
                    tick=time.perf_counter();samples=sample(state,c.norb,c.nelec,spec['shots'],seed)
                    outcome,history=evaluate(c,samples,dict(cfg,seed=seed))
                    residual=max(e['projected_residual_norm'] for rows in history for e in rows)
                    record['rows'].append(dict(seed=seed,energy_total=float(outcome.energy+c.ecore),residual=residual,history=history,seconds=time.perf_counter()-tick))
                    save()
                    if residual>=1e-6:
                        raise RuntimeError('SQD projected residual failed')
                del state
                print(distance,method,[round(e['energy_total'],7) for e in record['rows']],flush=True)
            tick=time.perf_counter();solver=fci.direct_spin1.FCI(c.mf.mol);solver.max_memory=cfg['max_memory_mb'];solver.conv_tol=spec['reference_tol'];solver.max_cycle=spec['reference_max_cycle']
            energy,vector=solver.kernel(c.h1,c.eri,c.norb,c.nelec,ecore=c.ecore)
            effective=fci.direct_spin1.absorb_h1e(c.h1,c.eri,c.norb,c.nelec,0.5)
            residual=float(np.linalg.norm(fci.direct_spin1.contract_2e(effective,vector,c.norb,c.nelec)-(energy-c.ecore)*vector));del vector
            point['reference']=dict(energy_total=float(energy),converged=bool(solver.converged),residual_norm=residual,seconds=time.perf_counter()-tick)
            for method in point['methods']:
                for row in method['rows']:row['error_mha']=1000*(row['energy_total']-energy)
            point['status']='success' if solver.converged and residual<spec['reference_residual_limit'] and diag['all_stages_success'] else 'validation_incomplete'
            save();print('Completed',distance,point['status'],flush=True)
        report['status']='success' if all(t['status']=='success' for t in report['targets']) else 'validation_incomplete'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save();print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
