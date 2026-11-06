from meta_lucj_sqd.plotting import plot_report
import hashlib
import argparse
import importlib.metadata
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyscf import fci, lib

from meta_lucj_sqd.chemistry import build_chemistry, run_ccsd
from meta_lucj_sqd.initialization import compressed_initialization
from meta_lucj_sqd.lucj import initialize, interaction_pairs, prepare, sample
from meta_lucj_sqd.sqd import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/regularized_comparison.json')
    args = parser.parse_args()
    spec = json.loads(Path(args.config).read_text())
    cfg = json.loads(Path(spec['base_config']).read_text())
    cfg.update(spec.get('solver_overrides', {}))
    lib.num_threads(cfg['threads'])
    out = Path('results') / datetime.now(timezone.utc).strftime('initialization_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    for source in [Path(__file__), *Path('src/meta_lucj_sqd').glob('*.py'),
                   *Path('configs').glob('*.json'), Path('pyproject.toml')]:
        target = out / 'source_snapshot' / source.resolve().relative_to(Path.cwd())
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    report = dict(config=cfg, comparison=spec, status='running', rows=[], timings={},
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  versions={p: importlib.metadata.version(p) for p in
                            ['numpy','scipy','pyscf','ffsim','qiskit','qiskit-addon-sqd']},
                  python=sys.version, platform=platform.platform(),
                  git_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  git_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True)),
                  thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},
                  config_hash=hashlib.sha256(json.dumps([cfg,spec],sort_keys=True).encode()).hexdigest())
    start=time.perf_counter()

    def save():
        report['wall_seconds']=time.perf_counter()-start
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['peak_rss_mib']=rss/(1024**2 if sys.platform=='darwin' else 1024)
        temp=out/'report.tmp'
        temp.write_text(json.dumps(report,indent=2,allow_nan=False))
        temp.replace(out/'report.json')

    def stage(name, function):
        tick=time.perf_counter()
        result=function()
        report['timings'][name]=time.perf_counter()-tick
        save()
        print(name,round(report['timings'][name],3),flush=True)
        return result

    try:
        chemistry=stage('chemistry',lambda:build_chemistry(cfg))
        cc=stage('ccsd',lambda:run_ccsd(chemistry,cfg))
        report['hf_total']=float(chemistry.mf.e_tot)
        report['ccsd_total']=float(cc.e_tot)
        report['scf_converged']=bool(chemistry.mf.converged)
        report['ccsd_converged']=bool(cc.converged)
        for method in ['truncated','compressed']:
            if method=='compressed':
                op, diagnostics=stage(method+'_initialization',lambda:compressed_initialization(
                    cc,chemistry.norb,cfg,spec['compression'],spec.get('compression_stages'),spec.get('regularization',0)))
                report['compression_diagnostics']=diagnostics
                save()
            else:
                op=stage(method+'_initialization',lambda:initialize(cc,chemistry.norb,cfg))
            np.save(out/(method+'_parameters.npy'),op.to_parameters(interaction_pairs=interaction_pairs(chemistry.norb)))
            state=stage(method+'_state',lambda:prepare(op,chemistry.norb,chemistry.nelec))
            norm_error=float(abs(np.linalg.norm(state)-1))
            if norm_error>1e-10:
                raise RuntimeError('State normalization failed')
            for shots in spec['shot_budgets']:
                for seed in spec['seeds']:
                    tick=time.perf_counter()
                    samples=sample(state,chemistry.norb,chemistry.nelec,shots,seed)
                    sampling_seconds=time.perf_counter()-tick
                    np.save(out/f'{method}_{shots}_{seed}_samples.npy',samples)
                    local=dict(cfg,seed=seed,shots=shots)
                    tick=time.perf_counter()
                    result,history=evaluate(chemistry,samples,local)
                    sqd_seconds=time.perf_counter()-tick
                    residual=max(r['projected_residual_norm'] for rows in history for r in rows)
                    valid=(samples[:,:chemistry.norb].sum(axis=1)==chemistry.nelec[1]) & (samples[:,chemistry.norb:].sum(axis=1)==chemistry.nelec[0])
                    row=dict(method=method,shots=shots,seed=seed,energy_total=float(result.energy+chemistry.ecore),
                             unique_samples=len(np.unique(samples,axis=0)),valid_shots=int(valid.sum()),
                             dimension=int(result.sci_state.amplitudes.size),norm_error=norm_error,
                             projected_residual_max=residual,history=history,
                             sampling_seconds=sampling_seconds,sqd_seconds=sqd_seconds,
                             status='success' if residual<1e-6 else 'residual_too_large')
                    report['rows'].append(row)
                    save()
                    print(method,shots,seed,row['energy_total'],row['unique_samples'],row['status'],flush=True)
            del state
        if spec.get('reference_report'):
            previous=json.loads(Path(spec['reference_report']).read_text())
            for key in ['molecule','basis','distance_angstrom','frozen_core','expected_norb',
                        'expected_nelec','scf_tol','max_cycle']:
                if cfg[key] != previous['config'][key]:
                    raise ValueError('Reference physical configuration mismatch: '+key)
            if abs(previous['hf_total']-chemistry.mf.e_tot)>1e-10:
                raise ValueError('Reference HF energy mismatch')
            integrals=np.load(spec['reference_integrals'])
            for name, value in [('h1',chemistry.h1),('eri',chemistry.eri),('ecore',chemistry.ecore)]:
                np.testing.assert_allclose(integrals[name], value, atol=1e-10, rtol=0)
            reference=previous['reference']
            if not reference['converged'] or reference['residual_norm']>=spec['reference_residual_limit']:
                raise ValueError('Reference validation failed')
            report['reference']=reference
            report['reference_reused_from']=spec['reference_report']
            report['reference_integrals_verified_against']=spec['reference_integrals']
            for row in report['rows']:
                row['error_mha']=1000*(row['energy_total']-reference['energy_total'])
            report['status']='success' if report['compression_diagnostics']['all_stages_success'] and all(r['status']=='success' for r in report['rows']) else 'validation_incomplete'
            return
        solver=fci.direct_spin1.FCI(chemistry.mf.mol)
        solver.max_memory=cfg['max_memory_mb']
        solver.max_cycle=spec['reference_max_cycle']
        solver.conv_tol=spec['reference_tol']
        energy,vector=stage('fci_refined',lambda:solver.kernel(chemistry.h1,chemistry.eri,chemistry.norb,chemistry.nelec,ecore=chemistry.ecore))
        effective=fci.direct_spin1.absorb_h1e(chemistry.h1,chemistry.eri,chemistry.norb,chemistry.nelec,0.5)
        residual=stage('fci_residual',lambda:np.linalg.norm(fci.direct_spin1.contract_2e(effective,vector,chemistry.norb,chemistry.nelec)-(energy-chemistry.ecore)*vector))
        report['reference']=dict(energy_total=float(energy),converged=bool(solver.converged),residual_norm=float(residual))
        for row in report['rows']:
            row['error_mha']=1000*(row['energy_total']-energy)
        report['status']='success' if solver.converged and residual<spec['reference_residual_limit'] and report['compression_diagnostics']['success'] and all(r['status']=='success' for r in report['rows']) else 'validation_incomplete'
    except BaseException:
        report['status']='failed'
        report['exception']=traceback.format_exc()
        raise
    finally:
        save()
        plot_report(out/'report.json')
        print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
