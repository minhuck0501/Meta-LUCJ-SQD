from meta_lucj_sqd.plotting import plot_report
import json
import argparse
import time
from pathlib import Path

import ffsim
import jax.numpy as jnp
import numpy as np
from scipy.optimize import minimize

from ffsim.linalg.double_factorized_decomposition import _make_t2_compressed_value_and_grad
from ffsim.linalg.util import df_tensors_to_params
from meta_lucj_sqd.lucj import interaction_pairs


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/regularized_diagnostic.json')
    args=parser.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    t2=np.load(cfg['amplitudes'])['t2']
    norb=t2.shape[0]+t2.shape[2]
    pairs=interaction_pairs(norb)
    indices=sorted(set(pairs[0]+pairs[1]))
    mats,rots=ffsim.linalg.double_factorized_t2(t2,tol=1e-8)
    x0=df_tensors_to_params(mats[:1],rots[:1],indices)
    function=_make_t2_compressed_value_and_grad(1,norb,t2.shape[0],tuple(indices))

    def fg(x):
        value,grad=function(jnp.asarray(x),jnp.asarray(t2),jnp.asarray(cfg.get('regularization',0.)),jnp.asarray(np.sum(mats**2)))
        return float(value),np.array(grad)

    rng=np.random.default_rng(cfg['seed'])
    directions=rng.normal(size=(cfg['directions'],len(x0)))
    directions/=np.linalg.norm(directions,axis=1)[:,None]

    def check(x):
        value,g=fg(x)
        records=[]
        for eps in cfg['gradient_steps']:
            for d in directions:
                numerical=(fg(x+eps*d)[0]-fg(x-eps*d)[0])/(2*eps)
                analytic=float(g@d)
                records.append(dict(step=eps,analytic=analytic,numerical=numerical,
                                    absolute_error=abs(numerical-analytic)))
        return dict(loss=value,gradient_l2=float(np.linalg.norm(g)),
                    gradient_inf=float(np.max(np.abs(g))),parameter_l2=float(np.linalg.norm(x)),
                    gradient_check=records)

    out=Path(cfg.get('output_directory','results/compression_diagnostic'))
    out.mkdir(exist_ok=True)
    report=dict(config=cfg,initial=check(x0),runs=[])
    for method in cfg['methods']:
        history=[]

        def callback(x):
            value,g=fg(x)
            history.append(dict(iteration=len(history)+1,loss=value,
                                gradient_l2=float(np.linalg.norm(g)),gradient_inf=float(np.max(np.abs(g))),
                                parameter_l2=float(np.linalg.norm(x)),max_parameter=float(np.max(np.abs(x)))))

        options=dict(maxiter=cfg['maxiter'],gtol=cfg['gtol'])
        if method=='L-BFGS-B':
            options['ftol']=cfg['ftol']
        tick=time.perf_counter()
        result=minimize(fg,x0.copy(),jac=True,method=method,options=options,callback=callback)
        seconds=time.perf_counter()-tick
        np.save(out/(method+'_parameters.npy'),result.x)
        record=dict(method=method,success=bool(result.success),message=str(result.message),
                    iterations=int(result.nit),evaluations=int(result.nfev),seconds=seconds,
                    final=check(result.x),history=history)
        report['runs'].append(record)
        (out/'report.json').write_text(json.dumps(report,indent=2))
        print(method,result.success,result.nit,result.fun,record['final']['gradient_inf'],seconds,flush=True)
    plot_report(out/'report.json')
    print(out/'report.json',flush=True)


if __name__=='__main__':
    main()
