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
from pyscf import fci,lib

from meta_lucj_sqd.chemistry import build_chemistry,run_ccsd
from meta_lucj_sqd.initialization import compressed_initialization
from meta_lucj_sqd.jastrow_meta import correct_jastrow,parameter_count
from meta_lucj_sqd.lucj import interaction_pairs,prepare,sample
from meta_lucj_sqd.optimization import spsa_step
from meta_lucj_sqd.sqd import evaluate
from meta_lucj_sqd.transfer import block_polar_transfer


def main():
    spec=json.loads(Path('configs/jastrow_joint.json').read_text())
    template=json.loads(Path(spec['phase3_config']).read_text())
    base=json.loads(Path(template['base_config']).read_text());base.update(template['solver_overrides']);base['shots']=spec['shots']
    lib.num_threads(base['threads'])
    out=Path('results')/datetime.now(timezone.utc).strftime('jastrow_joint_%Y%m%dT%H%M%S');out.mkdir(parents=True)
    for source in [Path(__file__),Path('configs/jastrow_joint.json'),*Path('src/meta_lucj_sqd').glob('*.py')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,status='running',evaluations=[],aggregate_calls=[],trajectory=[],training_evaluation=[],targets=[],versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','pyscf','ffsim','qiskit','qiskit-addon-sqd']},reference_label='Mean training FCI (0 mHa)',reference_scope='Mean error across three fixed training Hamiltonians')
    started=time.perf_counter()
    def save():
        report['wall_seconds']=time.perf_counter()-started
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temporary=out/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(out/'report.json')
    try:
        summary=json.loads(Path(spec['training_summary']).read_text())
        paths={p['distance_angstrom']:p['source_report'] for p in summary['points']};paths[spec['geometry_center']]=spec['anchor_report']
        training={};prior_ops={};references={}
        for distance,path in paths.items():
            prior=json.loads(Path(path).read_text());training[distance]=build_chemistry(prior['effective_config']);references[distance]=prior['reference']
            prior_ops[distance]=ffsim.UCJOpSpinBalanced.from_parameters(np.load(Path(path).parent/'best.npy'),norb=base['expected_norb'],n_reps=1,interaction_pairs=interaction_pairs(base['expected_norb']),with_final_orbital_rotation=True)
        anchor=training[spec['geometry_center']];anchor_operator=prior_ops[spec['geometry_center']]
        report['anchor_archive_wall_seconds']=json.loads(Path(spec['anchor_report']).read_text())['wall_seconds']
        report['reference']=dict(energy_total=float(np.mean([references[d]['energy_total'] for d in spec['training_distances']])),kind='mean_training_fci')
        for distance in spec['training_distances']:
            if not references[distance]['converged'] or references[distance]['residual_norm']>=spec['reference_residual_limit']:raise ValueError('Training reference invalid')
        count=parameter_count(anchor.norb);zero=np.zeros((2,count));report['shared_parameter_count']=int(zero.size)
        def operator_at(coefficients,distance,c):
            corrected=correct_jastrow(anchor_operator,coefficients,distance,spec['geometry_center'],spec['geometry_scale'])
            return block_polar_transfer(corrected,anchor,c)[0]
        def energy(c,operator,seed,label,distance,reference=None):
            tick=time.perf_counter();state=prepare(operator,c.norb,c.nelec)
            if abs(np.linalg.norm(state)-1)>1e-10:raise RuntimeError('State norm invalid')
            samples=sample(state,c.norb,c.nelec,spec['shots'],seed);del state
            outcome,history=evaluate(c,samples,dict(base,seed=seed));residual=max(v['projected_residual_norm'] for rows in history for v in rows)
            row=dict(distance_angstrom=distance,seed=seed,label=label,energy_total=float(outcome.energy+c.ecore),residual=residual,history=history,seconds=time.perf_counter()-tick,diagonalizations=sum(map(len,history)))
            if reference is not None:row['error_mha']=1000*(row['energy_total']-reference)
            report['evaluations'].append(row);save()
            if residual>=1e-6:raise RuntimeError('Projected residual invalid')
            return row
        def aggregate(coefficients,seeds,label):
            tick=time.perf_counter();rows=[]
            for distance,seed in zip(spec['training_distances'],seeds):
                rows.append(energy(training[distance],operator_at(coefficients,distance,training[distance]),seed,label,distance,references[distance]['energy_total']))
            mean=float(np.mean([r['energy_total'] for r in rows]));entry=dict(label=label,value=mean,seconds=time.perf_counter()-tick,mean_error_mha=1000*(mean-report['reference']['energy_total']))
            report['aggregate_calls'].append(entry);save();print(label,round(entry['mean_error_mha'],3),flush=True)
            return mean
        for seeds in spec['probe_seed_sets']:aggregate(zero,seeds,'noise_probe')
        measured=float(np.mean([c['seconds'] for c in report['aggregate_calls']]))
        iterations=max(1,min(spec['optimizer']['iterations'],int(spec['update_wall_budget_seconds']/(3*measured))))
        report['budget']=dict(probe_mean_aggregate_seconds=measured,chosen_iterations=iterations,requested_max_iterations=spec['optimizer']['iterations'],probe_mean_error_sample_std=float(np.std([c['mean_error_mha'] for c in report['aggregate_calls']],ddof=1)))
        print('Chosen updates',iterations,flush=True)
        coefficients=zero.copy();best=zero.copy();best_value=aggregate(zero,spec['training_seeds'],'train_initial')
        rng=np.random.default_rng(spec['optimizer']['seed'])
        for k in range(iterations):
            direction=rng.choice([-1.,1.],size=zero.shape);perturb=spec['optimizer']['c']/(k+1)**spec['optimizer']['gamma']
            plus=aggregate(coefficients+perturb*direction,spec['training_seeds'],f'plus_{k}')
            minus=aggregate(coefficients-perturb*direction,spec['training_seeds'],f'minus_{k}')
            coefficients=spsa_step(coefficients.ravel(),plus,minus,direction.ravel(),k,spec['optimizer']).reshape(zero.shape)
            value=aggregate(coefficients,spec['training_seeds'],f'candidate_{k}')
            if value<best_value:best_value=value;best=coefficients.copy()
            report['trajectory'].append(dict(iteration=k+1,value=value,best_value=best_value,rng_state=rng.bit_generator.state))
            np.save(out/'current.npy',coefficients);np.save(out/'best.npy',best);save()
        np.savez_compressed(out/'model.npz',coefficients=best,center=spec['geometry_center'],scale=spec['geometry_scale'])
        report['optimizer_status']='budget_exhausted';report['model_frozen']=True;save()
        for distance in spec['training_distances']:
            c=training[distance];item=dict(distance_angstrom=distance,reference=references[distance],methods=[]);report['training_evaluation'].append(item)
            for method,coefficient in [('zero_correction',zero),('trained_jastrow',best)]:
                rows=[energy(c,operator_at(coefficient,distance,c),seed,'training_check_'+method,distance,references[distance]['energy_total']) for seed in spec['evaluation_seeds']]
                item['methods'].append(dict(method=method,rows=rows))
        for target in spec['targets']:
            distance=target['distance_angstrom']
            if distance in spec['training_distances']:raise ValueError('Target overlaps training')
            c=build_chemistry(dict(base,distance_angstrom=distance))
            item=dict(distance_angstrom=distance,methods=[],status='running');report['targets'].append(item)
            np.savez_compressed(out/f'integrals_{distance:.2f}.npz',h1=c.h1,eri=c.eri,ecore=c.ecore,mo_coeff=c.mf.mo_coeff)
            tick=time.perf_counter();cc=run_ccsd(c,base);independent,diag=compressed_initialization(cc,c.norb,base,template['compression'],regularization=template['regularization']);item['independent_initialization_seconds']=time.perf_counter()-tick;item['compression']=diag
            warm=block_polar_transfer(prior_ops[target['warm_source']],training[target['warm_source']],c)[0]
            for method,operator in [('independent',independent),('warm',warm),('zero_correction',operator_at(zero,distance,c)),('trained_jastrow',operator_at(best,distance,c))]:
                np.save(out/f'{method}_{distance:.2f}_parameters.npy',operator.to_parameters(interaction_pairs=interaction_pairs(c.norb)))
                rows=[energy(c,operator,seed,method,distance) for seed in spec['evaluation_seeds']];item['methods'].append(dict(method=method,rows=rows))
                print('Target',distance,method,[round(r['energy_total'],7) for r in rows],flush=True)
            tick=time.perf_counter();solver=fci.direct_spin1.FCI(c.mf.mol);solver.max_memory=base['max_memory_mb'];solver.conv_tol=spec['reference_tol'];solver.max_cycle=spec['reference_max_cycle']
            e,v=solver.kernel(c.h1,c.eri,c.norb,c.nelec,ecore=c.ecore);effective=fci.direct_spin1.absorb_h1e(c.h1,c.eri,c.norb,c.nelec,0.5)
            residual=float(np.linalg.norm(fci.direct_spin1.contract_2e(effective,v,c.norb,c.nelec)-(e-c.ecore)*v));del v
            item['reference']=dict(energy_total=float(e),converged=bool(solver.converged),residual_norm=residual,seconds=time.perf_counter()-tick)
            for method in item['methods']:
                for row in method['rows']:row['error_mha']=1000*(row['energy_total']-e)
            item['status']='success' if solver.converged and residual<spec['reference_residual_limit'] and diag['all_stages_success'] else 'validation_incomplete'
            save();print('Completed target',distance,item['status'],flush=True)
        report['status']='success' if all(t['status']=='success' for t in report['targets']) else 'validation_incomplete'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save();plot_report(out/'report.json')
        for name,points in [('training_evaluation',report['training_evaluation']),('target_evaluation',report['targets'])]:
            if points and all(m.get('rows') and 'error_mha' in m['rows'][0] for p in points for m in p['methods']):
                path=out/(name+'.json');path.write_text(json.dumps(dict(targets=points,status=report['status']),indent=2));plot_report(path)
        print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
