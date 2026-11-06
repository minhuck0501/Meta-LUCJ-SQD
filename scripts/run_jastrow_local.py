from meta_lucj_sqd.plotting import plot_report

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
from pyscf import lib

from meta_lucj_sqd.chemistry import build_chemistry
from meta_lucj_sqd.jastrow_meta import correct_jastrow,parameter_count
from meta_lucj_sqd.lucj import interaction_pairs,prepare,sample
from meta_lucj_sqd.optimization import spsa_step
from meta_lucj_sqd.sqd import evaluate


def main():
    spec=json.loads(Path('configs/jastrow_local.json').read_text())
    anchor_path=Path(spec['anchor_report']);prior=json.loads(anchor_path.read_text());cfg=dict(prior['effective_config'],shots=spec['shots'])
    lib.num_threads(cfg['threads'])
    out=Path('results')/datetime.now(timezone.utc).strftime('jastrow_local_%Y%m%dT%H%M%S');out.mkdir(parents=True)
    for source in [Path(__file__),Path('configs/jastrow_local.json'),*Path('src/meta_lucj_sqd').glob('*.py')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,effective_config=cfg,status='running',reference=prior['reference'],evaluations=[],sensitivity=[],trajectory=[],final_groups={},versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','pyscf','ffsim','qiskit','qiskit-addon-sqd']})
    started=time.perf_counter()
    def save():
        report['wall_seconds']=time.perf_counter()-started
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temporary=out/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(out/'report.json')
    try:
        c=build_chemistry(cfg)
        integrals=np.load(prior['config']['reference_integrals'])
        for key,value in [('h1',c.h1),('eri',c.eri),('ecore',c.ecore)]:np.testing.assert_allclose(integrals[key],value,atol=1e-10,rtol=0)
        if not prior['reference']['converged'] or prior['reference']['residual_norm']>=1e-5:raise ValueError('Reference invalid')
        op=ffsim.UCJOpSpinBalanced.from_parameters(np.load(anchor_path.parent/'best.npy'),norb=c.norb,n_reps=1,interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=True)
        count=parameter_count(c.norb);zero=np.zeros(count);direction=np.random.default_rng(spec['probe_direction_seed']).choice([-1.,1.],size=count)
        np.save(out/'probe_direction.npy',direction)
        def objective(delta,seed,label):
            tick=time.perf_counter();coefficients=np.vstack([delta,np.zeros_like(delta)])
            corrected=correct_jastrow(op,coefficients,cfg['distance_angstrom'],cfg['distance_angstrom'],1.)
            np.testing.assert_array_equal(corrected.orbital_rotations,op.orbital_rotations)
            np.testing.assert_array_equal(corrected.final_orbital_rotation,op.final_orbital_rotation)
            state=prepare(corrected,c.norb,c.nelec)
            if abs(np.linalg.norm(state)-1)>1e-10:raise RuntimeError('State norm invalid')
            samples=sample(state,c.norb,c.nelec,spec['shots'],seed);del state
            result,history=evaluate(c,samples,dict(cfg,seed=seed));residual=max(v['projected_residual_norm'] for rows in history for v in rows)
            row=dict(label=label,seed=seed,energy_total=float(result.energy+c.ecore),error_mha=float(1000*(result.energy+c.ecore-prior['reference']['energy_total'])),residual=residual,history=history,seconds=time.perf_counter()-tick,diagonalizations=sum(map(len,history)))
            report['evaluations'].append(row);save()
            if residual>=1e-6:raise RuntimeError('Projected residual invalid')
            return row['energy_total']
        probe_best=zero.copy();probe_value=None
        for amplitude in [0.]+[s*a for a in spec['probe_amplitudes'] for s in [-1,1]]:
            rows=[objective(amplitude*direction,seed,'probe_'+str(amplitude)) for seed in spec['probe_seeds']]
            mean=float(np.mean(rows));errors=1000*(np.array(rows)-prior['reference']['energy_total'])
            report['sensitivity'].append(dict(amplitude=amplitude,mean_error_mha=float(errors.mean()),sample_std_mha=float(errors.std(ddof=1)),values=errors.tolist()))
            if probe_value is None or mean<probe_value:probe_value=mean;probe_best=amplitude*direction
            print('Probe',amplitude,round(float(errors.mean()),3),flush=True);save()
        np.save(out/'probe_best.npy',probe_best)
        measured=float(np.mean([v['seconds'] for v in report['evaluations']]))
        iterations=max(1,min(spec['optimizer']['iterations'],int(spec['update_wall_budget_seconds']/(3*measured))))
        report['budget']=dict(chosen_iterations=iterations,probe_mean_evaluation_seconds=measured)
        print('Chosen updates',iterations,flush=True)
        delta=zero.copy();best=zero.copy();best_value=objective(zero,spec['training_seed'],'train_initial');rng=np.random.default_rng(spec['optimizer']['seed'])
        for k in range(iterations):
            perturb=spec['optimizer']['c']/(k+1)**spec['optimizer']['gamma'];d=rng.choice([-1.,1.],size=count)
            plus=objective(delta+perturb*d,spec['training_seed'],f'plus_{k}');minus=objective(delta-perturb*d,spec['training_seed'],f'minus_{k}')
            delta=spsa_step(delta,plus,minus,d,k,spec['optimizer'])
            value=objective(delta,spec['training_seed'],f'candidate_{k}')
            if value<best_value:best_value=value;best=delta.copy()
            report['trajectory'].append(dict(iteration=k+1,value=value,best_value=best_value,rng_state=rng.bit_generator.state))
            np.save(out/'spsa_best.npy',best);np.save(out/'current.npy',delta);save()
            print('Update',k+1,round(1000*(value-prior['reference']['energy_total']),3),flush=True)
        for label,delta in [('baseline',zero),('spsa_best',best),('probe_best',probe_best)]:
            energies=[objective(delta,seed,'heldout_'+label) for seed in spec['evaluation_seeds']];errors=1000*(np.array(energies)-prior['reference']['energy_total'])
            report['final_groups'][label]=dict(mean_error_mha=float(errors.mean()),sample_std_mha=float(errors.std(ddof=1)),values=errors.tolist(),correction_norm=float(np.linalg.norm(delta)))
            print('Final',label,round(float(errors.mean()),3),flush=True)
        report['optimizer_status']='budget_exhausted';report['status']='success'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save();plot_report(out/'report.json')
        if report['sensitivity']:
            p=out/'sensitivity.json';p.write_text(json.dumps(dict(sensitivity=report['sensitivity'],status=report['status']),indent=2));plot_report(p)
        if report['final_groups']:
            p=out/'final_evaluation.json';p.write_text(json.dumps(dict(groups=report['final_groups'],status=report['status']),indent=2));plot_report(p)
        print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
