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
    spec=json.loads(Path('configs/jastrow_seed_average.json').read_text())
    single_path=Path(spec['single_seed_report']);single=json.loads(single_path.read_text());cfg=single['effective_config']
    anchor_path=Path(single['config']['anchor_report']);anchor=json.loads(anchor_path.read_text());optimizer=single['config']['optimizer']
    if single['config']['training_seed']!=spec['training_seeds'][0]:raise ValueError('Training seed mismatch')
    if set(spec['evaluation_seeds'])&set(spec['training_seeds']):raise ValueError('Evaluation seed leakage')
    lib.num_threads(cfg['threads'])
    out=Path('results')/datetime.now(timezone.utc).strftime('jastrow_seed_average_%Y%m%dT%H%M%S');out.mkdir(parents=True)
    for source in [Path(__file__),Path('configs/jastrow_seed_average.json'),*Path('src/meta_lucj_sqd').glob('*.py')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,effective_config=cfg,status='running',reference=single['reference'],evaluations=[],trajectory=[],final_groups={},versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','pyscf','ffsim','qiskit','qiskit-addon-sqd']})
    started=time.perf_counter()
    def save():
        report['wall_seconds']=time.perf_counter()-started
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temporary=out/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(out/'report.json')
    try:
        c=build_chemistry(cfg);ints=np.load(anchor['config']['reference_integrals'])
        for key,value in [('h1',c.h1),('eri',c.eri),('ecore',c.ecore)]:np.testing.assert_allclose(ints[key],value,atol=1e-10,rtol=0)
        op=ffsim.UCJOpSpinBalanced.from_parameters(np.load(anchor_path.parent/'best.npy'),norb=c.norb,n_reps=1,interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=True)
        zero=np.zeros(parameter_count(c.norb))
        def energy(delta,seed,label):
            tick=time.perf_counter();operator=correct_jastrow(op,np.vstack([delta,np.zeros_like(delta)]),cfg['distance_angstrom'],cfg['distance_angstrom'],1.)
            state=prepare(operator,c.norb,c.nelec)
            if abs(np.linalg.norm(state)-1)>1e-10:raise RuntimeError('State norm invalid')
            samples=sample(state,c.norb,c.nelec,cfg['shots'],seed);del state
            result,history=evaluate(c,samples,dict(cfg,seed=seed));residual=max(v['projected_residual_norm'] for rows in history for v in rows)
            row=dict(label=label,seed=seed,energy_total=float(result.energy+c.ecore),error_mha=float(1000*(result.energy+c.ecore-single['reference']['energy_total'])),residual=residual,history=history,seconds=time.perf_counter()-tick,diagonalizations=sum(map(len,history)))
            report['evaluations'].append(row);save()
            if residual>=1e-6:raise RuntimeError('Projected residual invalid')
            return row
        def objective(delta,label):
            values=[energy(delta,seed,label)['energy_total'] for seed in spec['training_seeds']]
            value=float(np.mean(values));print(label,round(1000*(value-single['reference']['energy_total']),3),flush=True);return value
        count=len(spec['training_seeds']);iterations=(spec['training_call_budget']-count)//(3*count)
        old_calls=[v for v in single['evaluations'] if v['label']=='train_initial' or v['label'].startswith(('plus_','minus_','candidate_'))]
        report['budget']=dict(max_calls=spec['training_call_budget'],single_training_calls=len(old_calls),single_updates=len(single['trajectory']),averaged_training_calls=count*(1+3*iterations),averaged_updates=iterations,single_training_seconds=sum(v['seconds'] for v in old_calls))
        if len(old_calls)>spec['training_call_budget'] or iterations<1:raise ValueError('Invalid matched-budget setup')
        delta=zero.copy();best=zero.copy();best_value=objective(zero,'train_initial');rng=np.random.default_rng(optimizer['seed'])
        for k in range(iterations):
            perturb=optimizer['c']/(k+1)**optimizer['gamma'];direction=rng.choice([-1.,1.],size=len(zero))
            plus=objective(delta+perturb*direction,f'plus_{k}');minus=objective(delta-perturb*direction,f'minus_{k}')
            delta=spsa_step(delta,plus,minus,direction,k,optimizer);value=objective(delta,f'candidate_{k}')
            if value<best_value:best_value=value;best=delta.copy()
            report['trajectory'].append(dict(iteration=k+1,value=value,best_value=best_value,rng_state=rng.bit_generator.state))
            np.save(out/'best.npy',best);np.save(out/'current.npy',delta);save()
        single_best=np.load(single_path.parent/'spsa_best.npy')
        for name,coefficients in [('baseline',zero),('single_seed',single_best),('three_seed_average',best)]:
            rows=[energy(coefficients,seed,'heldout_'+name) for seed in spec['evaluation_seeds']];values=np.array([v['error_mha'] for v in rows])
            report['final_groups'][name]=dict(mean_error_mha=float(values.mean()),sample_std_mha=float(values.std(ddof=1)),values=values.tolist(),correction_norm=float(np.linalg.norm(coefficients)))
            print('Final',name,round(float(values.mean()),3),flush=True)
        baseline=np.array(report['final_groups']['baseline']['values'])
        report['paired_improvements']={name:dict(mean_mha=float(np.mean(baseline-np.array(group['values']))),sample_std_mha=float(np.std(baseline-np.array(group['values']),ddof=1))) for name,group in report['final_groups'].items() if name!='baseline'}
        report['optimizer_status']='budget_exhausted';report['status']='success'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save();plot_report(out/'report.json')
        if report['final_groups']:
            p=out/'final_evaluation.json';p.write_text(json.dumps(dict(groups=report['final_groups'],status=report['status']),indent=2));plot_report(p)
        print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
