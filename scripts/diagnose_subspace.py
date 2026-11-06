import json
import time
from pathlib import Path
from datetime import datetime,timezone
from functools import partial

import ffsim
import numpy as np
from pyscf import lib
from qiskit_addon_sqd.fermion import diagonalize_fermionic_hamiltonian,solve_sci_batch

from meta_lucj_sqd.chemistry import build_chemistry
from meta_lucj_sqd.lucj import interaction_pairs,prepare,sample
from meta_lucj_sqd.sqd import residual_norm
from meta_lucj_sqd.plotting import plot_report


def main():
    spec=json.loads(Path('configs/subspace_diagnostic.json').read_text());prior_path=Path(spec['anchor_report']);prior=json.loads(prior_path.read_text());cfg=prior['effective_config'];lib.num_threads(1)
    out=Path('results')/datetime.now(timezone.utc).strftime('subspace_diagnostic_%Y%m%dT%H%M%S');out.mkdir(parents=True)
    report=dict(config=spec,reference=prior['reference'],rows=[],status='running');start=time.perf_counter()
    c=build_chemistry(cfg)
    op=ffsim.UCJOpSpinBalanced.from_parameters(np.load(prior_path.parent/'best.npy'),norb=c.norb,n_reps=1,interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=True)
    state=prepare(op,c.norb,c.nelec)
    for seed in spec['seeds']:
        samples=sample(state,c.norb,c.nelec,spec['shots'],seed);np.save(out/f'samples_{seed}.npy',samples)
        report.setdefault('sample_support',[]).append(dict(seed=seed,unique_bitstrings=len(np.unique(samples,axis=0)),unique_left=len(np.unique(samples[:,:c.norb],axis=0)),unique_right=len(np.unique(samples[:,c.norb:],axis=0))))
        for batch in spec['samples_per_batch']:
            tick=time.perf_counter()
            result=diagonalize_fermionic_hamiltonian(c.h1,c.eri,samples,samples_per_batch=batch,norb=c.norb,nelec=c.nelec,num_batches=3,max_iterations=2,energy_tol=1e-8,occupancies_tol=1e-6,symmetrize_spin=False,max_dim=spec['max_dim'],sci_solver=partial(solve_sci_batch,spin_sq=None,max_cycle=200,tol=1e-13),seed=seed)
            residual=residual_norm(c,result.sci_state,result.energy)
            if residual>=1e-6:raise RuntimeError('Residual failed')
            row=dict(seed=seed,samples_per_batch=batch,error_mha=float(1000*(result.energy+c.ecore-prior['reference']['energy_total'])),dimension=int(result.sci_state.amplitudes.size),seconds=time.perf_counter()-tick,residual=residual)
            report['rows'].append(row);report['wall_seconds']=time.perf_counter()-start;(out/'report.json').write_text(json.dumps(report,indent=2));print(row,flush=True)
    report['subspace_budget']=[dict(samples_per_batch=b,mean_error_mha=float(np.mean([r['error_mha'] for r in report['rows'] if r['samples_per_batch']==b])),std_error_mha=float(np.std([r['error_mha'] for r in report['rows'] if r['samples_per_batch']==b],ddof=1))) for b in spec['samples_per_batch']]
    report['status']='success';(out/'report.json').write_text(json.dumps(report,indent=2));plot_report(out/'report.json');print(out/'report.json',flush=True)


if __name__=='__main__':main()
