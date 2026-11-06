from meta_lucj_sqd.plotting import plot_report
import json
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
from scipy.linalg import polar

from meta_lucj_sqd.chemistry import build_chemistry
from meta_lucj_sqd.lucj import interaction_pairs,prepare,sample
from meta_lucj_sqd.meta import AffineModel
from meta_lucj_sqd.representation import decode_operator,change_block_frame
from meta_lucj_sqd.sqd import evaluate


def feature_diagnostics(features,norb):
    index=0;rotations=[];angles=[]
    def matrix():
        nonlocal index
        n=norb*norb
        m=(features[index:index+n]+1j*features[index+n:index+2*n]).reshape(norb,norb);index+=2*n
        rotations.append(dict(min_singular_value=float(np.linalg.svd(m,compute_uv=False)[-1]),unitarity_error=float(np.linalg.norm(m.conj().T@m-np.eye(norb))),polar_projection_distance=float(np.linalg.norm(polar(m)[0]-m))))
    matrix()
    for pairs in interaction_pairs(norb):
        n=len(pairs);radius=np.hypot(features[index:index+n],features[index+n:index+2*n]);index+=2*n
        angles.append(dict(min_radius=float(radius.min()),max_unit_circle_error=float(np.max(np.abs(radius-1)))))
    matrix()
    return dict(rotations=rotations,jastrow_angle_blocks=angles)


def probability_metrics(state):
    probabilities=np.abs(state)**2
    positive=probabilities[probabilities>0]
    return dict(hf_probability=float(probabilities[0]),entropy_bits=float(-np.sum(positive*np.log2(positive))),inverse_participation=float(1/np.sum(probabilities**2)))


def main():
    spec=json.loads(Path('configs/meta_diagnostic.json').read_text())
    meta_path=Path(spec['meta_report']);meta=json.loads(meta_path.read_text())
    rep_path=Path(spec['representation_report']);rep=json.loads(rep_path.read_text());archive=np.load(rep_path.parent/'features.npz')
    saved=np.load(meta_path.parent/'model.npz');model=AffineModel(float(saved['center']),float(saved['scale']),saved['coefficients'])
    out=Path('results')/datetime.now(timezone.utc).strftime('meta_diagnostic_%Y%m%dT%H%M%S');out.mkdir(parents=True)
    for source in [Path(__file__),Path('configs/meta_diagnostic.json'),*Path('src/meta_lucj_sqd').glob('*.py')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,status='running',training=[],unseen=[],versions=meta['versions']);started=time.perf_counter()
    def save():
        report['wall_seconds']=time.perf_counter()-started
        report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
        temporary=out/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(out/'report.json')
    try:
        for point in rep['points']:
            distance=point['distance_angstrom'];path=Path(point['source_report']);prior=json.loads(path.read_text());cfg=prior['effective_config'];lib.num_threads(cfg['threads']);c=build_chemistry(cfg)
            index=int(np.flatnonzero(np.isclose(archive['distances'],distance))[0]);truth=archive['features'][index];prediction=model.predict(distance)
            rotation=np.load(rep_path.parent/f'to_anchor_{distance:.1f}.npy')
            control=change_block_frame(decode_operator(truth,c.norb,1),rotation.conj().T,c.nelec[0])
            predicted=change_block_frame(decode_operator(prediction,c.norb,1),rotation.conj().T,c.nelec[0])
            original=ffsim.UCJOpSpinBalanced.from_parameters(np.load(path.parent/'best.npy'),norb=c.norb,n_reps=1,interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=True)
            label_state=prepare(original,c.norb,c.nelec);control_state=prepare(control,c.norb,c.nelec)
            reconstruction=float(np.linalg.norm(label_state-control_state));del control_state
            if reconstruction>spec['roundtrip_tolerance']:raise RuntimeError('Exact-label decode control failed')
            predicted_state=prepare(predicted,c.norb,c.nelec)
            entry=dict(distance_angstrom=distance,feature_rmse=float(np.sqrt(np.mean((truth-prediction)**2))),exact_label_roundtrip_error=reconstruction,projection=feature_diagnostics(prediction,c.norb),label_metrics=probability_metrics(label_state),prediction_metrics=probability_metrics(predicted_state),fidelity=float(abs(np.vdot(label_state,predicted_state))**2),total_variation=float(0.5*np.sum(np.abs(np.abs(label_state)**2-np.abs(predicted_state)**2))),methods=[])
            report['training'].append(entry)
            for method,state in [('optimized_label',label_state),('affine_prediction',predicted_state)]:
                item=dict(method=method,rows=[]);entry['methods'].append(item)
                for seed in spec['evaluation_seeds']:
                    samples=sample(state,c.norb,c.nelec,spec['shots'],seed);result,history=evaluate(c,samples,dict(cfg,seed=seed));residual=max(e['projected_residual_norm'] for rows in history for e in rows)
                    item['rows'].append(dict(seed=seed,error_mha=float(1000*(result.energy+c.ecore-prior['reference']['energy_total'])),residual=residual))
                    if residual>=1e-6:raise RuntimeError('Projected residual failed')
                    save()
            print('Training',distance,'fidelity',round(entry['fidelity'],4),flush=True)
            del label_state,predicted_state
        template=json.loads(Path(meta['config']['phase3_config']).read_text());base=json.loads(Path(template['base_config']).read_text());base.update(template['solver_overrides'])
        for point in meta['targets']:
            distance=point['distance_angstrom'];c=build_chemistry(dict(base,distance_angstrom=distance))
            states={}
            for method in ['independent','warm','meta']:
                operator=ffsim.UCJOpSpinBalanced.from_parameters(np.load(meta_path.parent/f'{method}_{distance:.1f}_parameters.npy'),norb=c.norb,n_reps=1,interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=True)
                states[method]=prepare(operator,c.norb,c.nelec)
            entry=dict(distance_angstrom=distance,projection=feature_diagnostics(model.predict(distance),c.norb),metrics={name:probability_metrics(v) for name,v in states.items()},comparisons=[])
            for name in ['independent','warm']:
                entry['comparisons'].append(dict(reference=name,fidelity=float(abs(np.vdot(states[name],states['meta']))**2),total_variation=float(0.5*np.sum(np.abs(np.abs(states[name])**2-np.abs(states['meta'])**2)))))
            report['unseen'].append(entry);save();print('Unseen diagnostics',distance,flush=True);del states
        report['status']='success'
    except BaseException:
        report['status']='failed';report['exception']=traceback.format_exc();raise
    finally:
        save()
        plot_report(out/'report.json')
        print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
