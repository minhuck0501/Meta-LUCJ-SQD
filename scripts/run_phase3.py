import json
import argparse
import hashlib
import importlib.metadata
import os
import platform
import resource
import shutil
import sys
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import ffsim
import numpy as np
from pyscf import lib

from meta_lucj_sqd.chemistry import build_chemistry, run_ccsd
from meta_lucj_sqd.initialization import compressed_initialization
from meta_lucj_sqd.lucj import interaction_pairs, prepare, sample
from meta_lucj_sqd.optimization import spsa_step
from meta_lucj_sqd.sqd import evaluate
from meta_lucj_sqd.transfer import sign_transfer,block_polar_transfer,orbital_overlap


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/phase3.json')
    args=parser.parse_args()
    spec=json.loads(Path(args.config).read_text())
    cfg=json.loads(Path(spec['base_config']).read_text())
    cfg.update(spec['solver_overrides'])
    cfg.update(distance_angstrom=spec['distance_angstrom'],shots=spec['shots'])
    lib.num_threads(cfg['threads'])
    out=Path('results')/datetime.now(timezone.utc).strftime('phase3_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    for source in [Path(__file__),*Path('src/meta_lucj_sqd').glob('*.py'),*Path('configs').glob('*.json')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd())
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    report=dict(config=spec,effective_config=cfg,status='running',evaluations=[],trajectory=[],
                config_sha256=hashlib.sha256(json.dumps([spec,cfg],sort_keys=True).encode()).hexdigest(),
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','pyscf','ffsim','qiskit','qiskit-addon-sqd']},
                git_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                git_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True)),
                python=sys.version,platform=platform.platform(),threads={k:os.getenv(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']})
    started=time.perf_counter()

    def save():
        report['wall_seconds']=time.perf_counter()-started
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temp=out/'report.tmp'
        temp.write_text(json.dumps(report,indent=2,allow_nan=False));temp.replace(out/'report.json')

    try:
        c=build_chemistry(cfg)
        np.save(out/'mo_coeff.npy',c.mf.mo_coeff)
        integrals=np.load(spec['reference_integrals'])
        for key,value in [('h1',c.h1),('eri',c.eri),('ecore',c.ecore)]:
            np.testing.assert_allclose(integrals[key],value,atol=1e-10,rtol=0)
        ref=json.loads(Path(spec['reference_report']).read_text())['reference']
        if not ref['converged'] or ref['residual_norm']>=1e-5:
            raise ValueError('Reference invalid')
        report['reference']=ref
        tick=time.perf_counter()
        if spec.get('warm_start_report'):
            previous_path=Path(spec['warm_start_report'])
            previous=json.loads(previous_path.read_text())
            source=build_chemistry(previous['effective_config'])
            if (previous_path.parent/'mo_coeff.npy').exists():
                source.mf.mo_coeff=np.load(previous_path.parent/'mo_coeff.npy')
            params=np.load(previous_path.parent/'best.npy')
            old_op=ffsim.UCJOpSpinBalanced.from_parameters(params,norb=c.norb,n_reps=cfg['n_reps'],interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=cfg['final_rotation_from_t1'])
            method=spec.get('transfer_method','sign')
            if method=='block_polar':
                op,rotation=block_polar_transfer(old_op,source,c)
                overlap=orbital_overlap(source,c)
                transfer=dict(method=method,overlap_singular_values=np.linalg.svd(overlap,compute_uv=False).tolist(),unitarity_error=float(np.linalg.norm(rotation.conj().T@rotation-np.eye(c.norb))))
                np.save(out/'transfer_rotation.npy',rotation)
            elif method=='sign':
                op,transfer=sign_transfer(old_op,source,c)
            else:
                raise ValueError('Unknown transfer method')
            report['transfer']=transfer
            report['warm_start_from']=str(previous_path)
            diag=dict(all_stages_success=True,kind=method+'_transferred_previous_best')
        else:
            cc=run_ccsd(c,cfg)
            op,diag=compressed_initialization(cc,c.norb,cfg,spec['compression'],regularization=spec['regularization'])
        report['initialization_seconds']=time.perf_counter()-tick
        report['initialization']=diag
        if not diag['all_stages_success']:
            raise RuntimeError('Initialization did not converge')
        initial=op.to_parameters(interaction_pairs=interaction_pairs(c.norb))
        np.save(out/'initial.npy',initial)

        def objective(params,seed,label):
            tick=time.perf_counter()
            operator=ffsim.UCJOpSpinBalanced.from_parameters(params,norb=c.norb,n_reps=cfg['n_reps'],interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=cfg['final_rotation_from_t1'])
            state=prepare(operator,c.norb,c.nelec)
            if abs(np.linalg.norm(state)-1)>1e-10:
                raise RuntimeError('State norm failed')
            samples=sample(state,c.norb,c.nelec,spec['shots'],seed)
            del state
            result,history=evaluate(c,samples,dict(cfg,seed=seed))
            residual=max(x['projected_residual_norm'] for rows in history for x in rows)
            entry=dict(label=label,seed=seed,energy_total=float(result.energy+c.ecore),
                       error_mha=float(1000*(result.energy+c.ecore-ref['energy_total'])),
                       history=history,dimension=int(result.sci_state.amplitudes.size),
                       unique_samples=len(np.unique(samples,axis=0)),residual=residual,
                       seconds=time.perf_counter()-tick,diagonalizations=sum(map(len,history)))
            report['evaluations'].append(entry);save()
            if residual>=1e-6:
                raise RuntimeError('Projected residual failed')
            print(label,round(entry['error_mha'],3),flush=True)
            return entry['energy_total']

        for seed in spec['probe_seeds']:
            objective(initial,seed,'noise_probe')
        parameters=initial.copy();best=initial.copy()
        best_value=objective(parameters,spec['training_seed'],'train_initial')
        rng=np.random.default_rng(spec['optimizer']['seed'])
        start_iteration=0
        earlier_best=None
        if spec.get('resume_report'):
            prior_path=Path(spec['resume_report'])
            prior=json.loads(prior_path.read_text())
            for key in ['training_seed','shots','regularization','distance_angstrom']:
                if spec[key]!=prior['config'][key]:
                    raise ValueError('Resume configuration mismatch: '+key)
            for key in spec['optimizer']:
                if key!='iterations' and spec['optimizer'][key]!=prior['config']['optimizer'][key]:
                    raise ValueError('Resume optimizer mismatch: '+key)
            if cfg!=prior['effective_config']:
                raise ValueError('Resume effective configuration mismatch')
            np.testing.assert_allclose(initial,np.load(prior_path.parent/'initial.npy'),atol=1e-10,rtol=0)
            parameters=np.load(prior_path.parent/'current.npy')
            best=np.load(prior_path.parent/'best.npy')
            earlier_best=best.copy()
            start_iteration=prior['trajectory'][-1]['iteration']
            best_value=prior['trajectory'][-1]['best_value']
            rng.bit_generator.state=prior['trajectory'][-1]['rng_state']
            report['resumed_from']=str(prior_path)
            report['prior_wall_seconds']=prior['wall_seconds']
            report['prior_evaluations']=len(prior['evaluations'])
        for k in range(start_iteration,spec['optimizer']['iterations']):
            direction=rng.choice([-1.,1.],size=len(parameters))
            perturb=spec['optimizer']['c']/(k+1)**spec['optimizer']['gamma']
            plus=objective(parameters+perturb*direction,spec['training_seed'],f'plus_{k}')
            minus=objective(parameters-perturb*direction,spec['training_seed'],f'minus_{k}')
            parameters=spsa_step(parameters,plus,minus,direction,k,spec['optimizer'])
            value=objective(parameters,spec['training_seed'],f'candidate_{k}')
            if value<best_value:
                best_value=value;best=parameters.copy()
            np.save(out/'best.npy',best);np.save(out/'current.npy',parameters)
            report['trajectory'].append(dict(iteration=k+1,value=value,best_value=best_value,rng_state=rng.bit_generator.state))
            save()
        for seed in spec['evaluation_seeds']:
            objective(initial,seed,'heldout_initial')
            if earlier_best is not None:
                objective(earlier_best,seed,'heldout_budget12')
            objective(best,seed,'heldout_refined')
        report['optimizer_status']='budget_exhausted'
        report['status']='success'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save();print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
