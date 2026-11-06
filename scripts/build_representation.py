from meta_lucj_sqd.plotting import plot_report
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import ffsim
import numpy as np
from pyscf import lib

from meta_lucj_sqd.chemistry import build_chemistry
from meta_lucj_sqd.lucj import interaction_pairs,prepare
from meta_lucj_sqd.representation import encode_operator,decode_operator,change_block_frame
from meta_lucj_sqd.transfer import block_polar_transfer,rotate_output


def main():
    spec=json.loads(Path('configs/representation.json').read_text())
    summary=json.loads(Path(spec['source_summary']).read_text())
    paths={p['distance_angstrom']:p['source_report'] for p in summary['points']}
    paths[spec['anchor_distance_angstrom']]=spec['anchor_report']
    anchor_report=json.loads(Path(spec['anchor_report']).read_text())
    lib.num_threads(anchor_report['effective_config']['threads'])
    anchor=build_chemistry(anchor_report['effective_config'])
    out=Path('results')/datetime.now(timezone.utc).strftime('representation_%Y%m%dT%H%M%S')
    out.mkdir(parents=True)
    for source in [Path(__file__),Path('configs/representation.json'),*Path('src/meta_lucj_sqd').glob('*.py')]:
        target=out/'source_snapshot'/source.resolve().relative_to(Path.cwd());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    report=dict(config=spec,status='running',points=[])
    started=time.perf_counter();vectors=[];distances=[]
    for distance,path in sorted(paths.items()):
        prior=json.loads(Path(path).read_text());c=build_chemistry(prior['effective_config'])
        values=np.load(Path(path).parent/'best.npy')
        op=ffsim.UCJOpSpinBalanced.from_parameters(values,norb=c.norb,n_reps=1,interaction_pairs=interaction_pairs(c.norb),with_final_orbital_rotation=True)
        aligned,rotation=block_polar_transfer(op,c,anchor)
        aligned=change_block_frame(op,rotation,c.nelec[0])
        encoded=encode_operator(aligned);decoded=decode_operator(encoded,c.norb,1)
        restored=change_block_frame(decoded,rotation.conj().T,c.nelec[0])
        state=prepare(op,c.norb,c.nelec)
        restored_state=prepare(restored,c.norb,c.nelec)
        error=float(np.linalg.norm(restored_state-state))
        np.save(out/f'to_anchor_{distance:.1f}.npy',rotation)
        report['points'].append(dict(distance_angstrom=distance,source_report=path,roundtrip_state_l2_error=error,feature_count=len(encoded)))
        vectors.append(encoded);distances.append(distance)
        report['wall_seconds']=time.perf_counter()-started
        if error>spec['roundtrip_tolerance']:
            report['status']='failed';(out/'report.json').write_text(json.dumps(report,indent=2));raise RuntimeError('Representation roundtrip failed')
        print(distance,len(encoded),error,flush=True)
        del state,restored_state
    np.savez_compressed(out/'features.npz',distances=distances,features=np.stack(vectors))
    report['status']='success';report['wall_seconds']=time.perf_counter()-started
    (out/'report.json').write_text(json.dumps(report,indent=2))
    plot_report(out/'report.json')
    print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
