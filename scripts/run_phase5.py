import json
import argparse
import resource
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import ffsim
import numpy as np
from pyscf import lib
from scipy.optimize import linear_sum_assignment

from meta_lucj_sqd.chemistry import build_chemistry
from meta_lucj_sqd.lucj import interaction_pairs,prepare,sample
from meta_lucj_sqd.sqd import evaluate
from meta_lucj_sqd.transfer import orbital_overlap,sign_transfer,polar_transfer,block_polar_transfer


def main():
    spec=json.loads(Path('configs/phase5.json').read_text())
    parser=argparse.ArgumentParser()
    parser.add_argument('--methods',nargs='+',choices=['sign','polar','block_polar'])
    args=parser.parse_args()
    if args.methods:
        spec['methods']=args.methods
    geometry=json.loads(Path(spec['geometry_summary']).read_text())
    paths={p['distance_angstrom']:p['source_report'] for p in geometry['points']}
    paths[1.2]=spec['center_report']
    out=Path('results')/datetime.now(timezone.utc).strftime('phase5_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    for source in [Path(__file__),*Path('src/meta_lucj_sqd').glob('*.py'),Path('configs/phase5.json')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd())
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,sources=paths,pairs=[],status='running')
    started=time.perf_counter()

    def save():
        report['wall_seconds']=time.perf_counter()-started
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temp=out/'report.tmp';temp.write_text(json.dumps(report,indent=2));temp.replace(out/'report.json')

    try:
        chemistry={};operators={};configs={};vectors=[];references={}
        for distance,path in sorted(paths.items()):
            previous=json.loads(Path(path).read_text());cfg=previous['effective_config']
            configs[distance]=cfg;lib.num_threads(cfg['threads'])
            chemistry[distance]=build_chemistry(cfg)
            np.save(out/f'mo_{distance:.1f}.npy',chemistry[distance].mf.mo_coeff)
            values=np.load(Path(path).parent/'best.npy');vectors.append(values)
            operators[distance]=ffsim.UCJOpSpinBalanced.from_parameters(values,norb=cfg['expected_norb'],n_reps=cfg['n_reps'],interaction_pairs=interaction_pairs(cfg['expected_norb']),with_final_orbital_rotation=True)
            references[distance]=previous['reference']
            if not previous['reference']['converged'] or previous['reference']['residual_norm']>=1e-5:
                raise ValueError('Reference invalid')
        centered=np.stack(vectors);centered-=centered.mean(axis=0)
        report['raw_parameter_centered_singular_values']=np.linalg.svd(centered,compute_uv=False).tolist()
        c=chemistry[1.2];op=operators[1.2]
        state=prepare(op,c.norb,c.nelec)
        shifted=op.diag_coulomb_mats.copy();shifted[0,1,0,0]+=2*np.pi
        equivalent=ffsim.UCJOpSpinBalanced(shifted,op.orbital_rotations,op.final_orbital_rotation)
        difference=np.linalg.norm(prepare(equivalent,c.norb,c.nelec)-state)
        report['jastrow_periodicity']=dict(parameter_shift=float(2*np.pi),state_l2_difference=float(difference))
        if difference>1e-10:
            raise RuntimeError('Periodicity invariant failed')
        del state
        for source,target in spec['pairs']:
            left=chemistry[source];right=chemistry[target]
            overlap=orbital_overlap(left,right)
            ri,ci=linear_sum_assignment(-np.abs(overlap)**2)
            point=dict(source=source,target=target,singular_values=np.linalg.svd(overlap,compute_uv=False).tolist(),
                       diagonal_overlaps=np.diag(overlap).tolist(),assignment=ci.tolist(),
                       diagonal_abs_mean=float(np.mean(np.abs(np.diag(overlap)))),
                       assigned_abs_mean=float(np.mean(np.abs(overlap[ri,ci]))),methods=[])
            report['pairs'].append(point)
            target_state=prepare(operators[target],right.norb,right.nelec)
            target_prob=np.abs(target_state)**2
            for method in spec['methods']:
                if method=='sign':
                    operator,_=sign_transfer(operators[source],left,right)
                else:
                    function=polar_transfer if method=='polar' else block_polar_transfer
                    operator,rotation=function(operators[source],left,right)
                    if np.linalg.norm(rotation.conj().T@rotation-np.eye(right.norb))>1e-10:
                        raise RuntimeError('Transport rotation not unitary')
                    np.save(out/f'{method}_{source:.1f}_{target:.1f}.npy',rotation)
                state=prepare(operator,right.norb,right.nelec)
                result=dict(method=method,fidelity_to_target_independent=float(abs(np.vdot(target_state,state))**2),
                            total_variation_to_target_independent=float(0.5*np.sum(np.abs(np.abs(state)**2-target_prob))),rows=[])
                point['methods'].append(result)
                if abs(np.linalg.norm(state)-1)>1e-10:
                    raise RuntimeError('State norm invalid')
                for seed in spec['evaluation_seeds']:
                    samples=sample(state,right.norb,right.nelec,spec['shots'],seed)
                    outcome,history=evaluate(right,samples,dict(configs[target],seed=seed))
                    residual=max(v['projected_residual_norm'] for rows in history for v in rows)
                    result['rows'].append(dict(seed=seed,energy_total=float(outcome.energy+right.ecore),error_mha=float(1000*(outcome.energy+right.ecore-references[target]['energy_total'])),history=history,residual=residual))
                    save()
                    if residual>=spec['residual_limit']:
                        raise RuntimeError('Projected residual invalid')
                print(source,target,method,[round(x['error_mha'],3) for x in result['rows']],flush=True)
                del state
            del target_state,target_prob
        report['status']='success'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save();print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
