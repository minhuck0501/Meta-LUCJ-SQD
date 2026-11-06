import json
from pathlib import Path

import numpy as np


def _mean(group):
    return group.get('mean_error_mha',group.get('error_mha_mean'))


def _std(group):
    return group.get('sample_std_mha',group.get('error_mha_std',group.get('error_mha_sample_std',0.)))


def _series(name,x,y,error=None):
    return dict(name=name,x=list(x),y=list(y),error=None if error is None else list(error))


def _refined_group(report):
    rows=[r for r in report.get('evaluations',[]) if r.get('label')=='heldout_refined']
    if not rows:return None
    values=[r['error_mha'] for r in rows]
    return dict(error_mha_mean=float(np.mean(values)),error_mha_std=float(np.std(values,ddof=1)) if len(values)>1 else 0.)


def _groups(points,container):
    series={}
    for point in points:
        groups=point[container]
        if isinstance(groups,dict):
            groups=[dict(value,method=key) for key,value in groups.items()]
        for group in groups:
            name=group['method'];value=_mean(group)
            if value is None and group.get('rows') and 'error_mha' in group['rows'][0]:
                values=[r['error_mha'] for r in group['rows']]
                value=float(np.mean(values));error=float(np.std(values,ddof=1)) if len(values)>1 else 0.
            else:
                error=_std(group)
            if value is not None:
                series.setdefault(name,[]).append((point['distance_angstrom'],value,error))
    return [_series(name,*zip(*sorted(values))) for name,values in series.items()]


def chart_data(report):
    reference=report.get('reference',{}).get('energy_total')
    if report.get('pairs'):
        points=[]
        for pair in report['pairs']:
            methods=[]
            for method in pair['methods']:
                values=[r['error_mha'] for r in method['rows']]
                if values:methods.append(dict(method=method['method'],error_mha_mean=float(np.mean(values)),error_mha_std=float(np.std(values,ddof=1)) if len(values)>1 else 0.))
            points.append(dict(source=pair['source'],target=pair['target'],methods=methods))
        if points and all(p['methods'] for p in points):return chart_data(dict(points=points))
    if report.get('directions') and not report.get('independent'):
        series=[]
        for chain in report['directions']:
            values=[]
            endpoint=json.loads(Path(chain['endpoint_report']).read_text())
            group=_refined_group(endpoint)
            if group:values.append((chain['distances'][0],_mean(group),_std(group)))
            for point in chain['points']:
                if 'report' not in point:continue
                group=_refined_group(json.loads(Path(point['report']).read_text()))
                if group:values.append((point['distance_angstrom'],_mean(group),_std(group)))
            values.sort()
            if values:series.append(_series('Increasing' if chain['distances'][0]<chain['distances'][-1] else 'Decreasing',*zip(*values)))
        return dict(title='Sequential evaluation (includes reused endpoint)',xlabel='Bond length (angstrom)',ylabel='SQD energy error (mHa)',series=series)
    if report.get('points') and 'report' in report['points'][0]:
        points=[]
        for point in report['points']:
            if 'report' not in point:continue
            child=json.loads(Path(point['report']).read_text());methods=[]
            group=_refined_group(child)
            if group:methods.append(dict(group,method='Refined'))
            elif child.get('reference'):
                for name in sorted({r['method'] for r in child.get('rows',[])}):
                    vals=[1000*(r['energy_total']-child['reference']['energy_total']) for r in child['rows'] if r['method']==name]
                    methods.append(dict(method=name,error_mha_mean=float(np.mean(vals)),error_mha_std=float(np.std(vals,ddof=1)) if len(vals)>1 else 0.))
            if methods:points.append(dict(distance_angstrom=point['distance_angstrom'],methods=methods))
        if points:return chart_data(dict(points=points))
    if report.get('jobs') and 'groups' not in report['jobs'][0]:
        jobs=[]
        for job in report['jobs']:
            if 'report' not in job:continue
            group=_refined_group(json.loads(Path(job['report']).read_text()))
            if group:jobs.append(dict(name=job['name'],groups={'heldout_refined':group}))
        if jobs:return chart_data(dict(jobs=jobs))
    if report.get('trajectory'):
        ref=reference or 0.;factor=1000 if reference is not None else 1
        rows=report['trajectory']
        if report.get('resumed_from'):
            prior=json.loads(Path(report['resumed_from']).read_text())
            rows=prior['trajectory']+rows
        return dict(title='SQD optimization trajectory (training objective)',xlabel='Update iteration',ylabel='Energy error (mHa)' if reference is not None else 'Total energy (Ha)',series=[_series('Candidate',[r['iteration'] for r in rows],[(r['value']-ref)*factor for r in rows]),_series('Best training candidate',[r['iteration'] for r in rows],[(r['best_value']-ref)*factor for r in rows])])
    if report.get('targets'):
        return dict(title='Unseen-geometry initialization evaluation',xlabel='Bond length (angstrom)',ylabel='SQD energy error (mHa)',series=_groups(report['targets'],'methods'))
    if report.get('training') and 'methods' in report['training'][0]:
        return dict(title='Training-geometry reconstruction diagnostic',xlabel='Bond length (angstrom)',ylabel='SQD energy error (mHa)',series=_groups(report['training'],'methods'))
    if report.get('runs') and 'history' in report['runs'][0]:
        return dict(title='Compression objective diagnostic',xlabel='Optimizer iteration',ylabel='Amplitude fitting loss',series=[_series(r['method'],[v['iteration'] for v in r['history']],[v['loss'] for v in r['history']]) for r in report['runs']])
    if report.get('directions') and report.get('independent'):
        series=[]
        values=sorted((float(k),v) for k,v in report['independent'].items())
        series.append(_series('Independent',[d for d,v in values],[_mean(v) for d,v in values],[_std(v) for d,v in values]))
        for chain in report['directions']:
            values=[]
            first=chain['distances'][0];group=report['independent'][str(first)]
            values.append((first,_mean(group),_std(group)))
            for point in chain['points']:
                group=point.get('groups',{}).get('heldout_refined',point)
                values.append((point['distance_angstrom'],_mean(group),_std(group)))
            values.sort();series.append(_series('Increasing' if chain['distances'][0]<chain['distances'][-1] else 'Decreasing',*zip(*values)))
        return dict(title='Fixed-budget independent and sequential evaluation',xlabel='Bond length (angstrom)',ylabel='SQD energy error (mHa)',series=series)
    if report.get('jobs') and 'groups' in report['jobs'][0]:
        series=[]
        for label in ['heldout_initial','heldout_refined']:
            x=[];y=[];e=[]
            for i,job in enumerate(report['jobs']):
                group=job['groups'].get(label)
                if group:x.append(i);y.append(_mean(group));e.append(_std(group))
            series.append(_series(label,x,y,e))
        return dict(title='Independent optimizer repetitions',xlabel='Optimizer trial (categorical)',ylabel='SQD energy error (mHa)',series=series,tick_labels=[r['name'] for r in report['jobs']])
    if report.get('points'):
        points=report['points']
        if 'methods' in points[0] and 'distance_angstrom' in points[0]:
            return dict(title='Geometry sweep',xlabel='Bond length (angstrom)',ylabel='SQD energy error (mHa)',series=_groups(points,'methods'))
        if 'groups' in points[0]:
            return dict(title='Independent refinement at additional geometries',xlabel='Bond length (angstrom)',ylabel='SQD energy error (mHa)',series=_groups(points,'groups'))
        if 'source' in points[0] and 'methods' in points[0]:
            methods=sorted({m['method'] for p in points for m in p['methods']});series=[]
            for name in methods:
                groups=[next(m for m in p['methods'] if m['method']==name) for p in points]
                series.append(_series(name,range(len(points)),[_mean(g) for g in groups],[_std(g) for g in groups]))
            return dict(title='Orbital transport diagnostic (no refinement)',xlabel='Transfer direction (categorical)',ylabel='SQD energy error (mHa)',series=series,tick_labels=[f"{p['source']:.1f} to {p['target']:.1f}" for p in points])
        if 'roundtrip_state_l2_error' in points[0]:
            return dict(title='Common-frame representation roundtrip',xlabel='Bond length (angstrom)',ylabel='State L2 difference',series=[_series('Roundtrip',[p['distance_angstrom'] for p in points],[p['roundtrip_state_l2_error'] for p in points])],log_y=True)
    if report.get('groups') and isinstance(report['groups'],list):
        groups=report['groups'];methods=sorted({g.get('method','compressed') for g in groups});series=[]
        for name in methods:
            rows=sorted((g for g in groups if g.get('method','compressed')==name),key=lambda g:g['shots'])
            series.append(_series(name,[g['shots'] for g in rows],[_mean(g) for g in rows],[_std(g) for g in rows]))
        return dict(title='Initialization sampling-budget evaluation',xlabel='Shots',ylabel='SQD energy error (mHa)',series=series)
    if report.get('groups') and isinstance(report['groups'],dict):
        groups=report['groups'];names=[n for n in ['noise_probe','heldout_initial','heldout_refined'] if n in groups]
        return dict(title='Initial and refined independent-seed evaluation',xlabel='Evaluation group (categorical)',ylabel='SQD energy error (mHa)',series=[_series('Evaluation',range(len(names)),[_mean(groups[n]) for n in names],[_std(groups[n]) for n in names])],tick_labels=names)
    if report.get('rows') and 'method' in report['rows'][0] and reference is not None:
        groups=[]
        for method,shots in sorted({(r['method'],r['shots']) for r in report['rows']}):
            vals=[1000*(r['energy_total']-reference) for r in report['rows'] if r['method']==method and r['shots']==shots]
            groups.append(dict(method=method,shots=shots,error_mha_mean=float(np.mean(vals)),error_mha_std=float(np.std(vals,ddof=1)) if len(vals)>1 else 0.))
        return chart_data(dict(groups=groups))
    if report.get('sqd'):
        chemistry=report['chemistry'];factor=1000 if reference is not None else 1.;offset=reference if reference is not None else 0.
        values=[factor*(v-offset) for v in [chemistry['hf_total'],chemistry['ccsd_total'],report['sqd']['energy_total']]]
        return dict(title='Single-geometry energy comparison',xlabel='Method (categorical)',ylabel='Energy error (mHa)' if reference is not None else 'Total energy (Ha)',series=[_series('Energy comparison',range(3),values)],tick_labels=['RHF','CCSD','SQD'])
    return None


def plot_report(report_path,output_stem=None,metric='error'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    path=Path(report_path);report=json.loads(path.read_text());data=chart_data(report)
    if data is None:return None
    if not data['series']:return None
    energy_error=data['ylabel'] in ['Energy error (mHa)','SQD energy error (mHa)']
    if energy_error:
        data['reference']=dict(method='FCI',value=0.,unit='mHa',scope=report.get('reference_scope','Same basis, frozen core and active-space Hamiltonian; numerically converged reference, not experimental truth'))
    if report.get('status') in ['failed','interrupted','running','validation_incomplete']:
        data['title']+=' ['+report['status']+']'
    if metric=='total_energy':
        points=report.get('targets',report.get('points',[]))
        references={}
        for point in points:
            reference=point.get('reference')
            if reference is None and point.get('report'):
                reference=json.loads(Path(point['report']).read_text()).get('reference')
            if reference is None:raise ValueError('Total-energy plot requires reference energies')
            references[point['distance_angstrom']]=reference['energy_total']
        for series in data['series']:
            series['y']=[references[x]+y/1000 for x,y in zip(series['x'],series['y'])]
            if series['error'] is not None:series['error']=[e/1000 for e in series['error']]
        data['series'].append(_series('FCI reference',sorted(references),[references[x] for x in sorted(references)]))
        data['title']='Total energies at calculated geometries'
        data['ylabel']='Total energy (Ha)'
        energy_error=False
        data['reference']=dict(method='FCI',unit='Ha',energies=references,scope='Same basis and active-space Hamiltonian')
    stem=Path(output_stem) if output_stem else path.parent/('figure' if path.name=='report.json' else path.stem+'_figure')
    stem.parent.mkdir(parents=True,exist_ok=True)
    with plt.rc_context({'font.size':10,'axes.spines.top':False,'axes.spines.right':False}):
        fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
        for series in data['series']:
            is_reference=series['name']=='FCI reference'
            sparse_geometry=data['xlabel']=='Bond length (angstrom)' and len(series['x'])<3
            ax.errorbar(series['x'],series['y'],yerr=series['error'],marker='D' if is_reference else 'o',linestyle='none' if sparse_geometry else (':' if is_reference else '--'),color='black' if is_reference else None,linewidth=2 if is_reference else 1.6,capsize=4,label=series['name'])
        if energy_error:
            ax.axhline(0.,color='black',linewidth=1.5,label=report.get('reference_label','FCI reference (0 mHa)'))
            lower,upper=ax.get_ylim()
            ax.set_ylim(min(lower,-0.03*max(abs(upper),1.)),upper)
        ax.set(title=data['title'],xlabel=data['xlabel'],ylabel=data['ylabel'])
        if data.get('tick_labels'):
            ax.set_xticks(range(len(data['tick_labels'])),data['tick_labels'],rotation=12)
        if data.get('log_y'):ax.set_yscale('log')
        ax.grid(alpha=0.2);ax.legend(fontsize=8)
        fig.get_layout_engine().set(rect=(0,0.13,1,0.87))
        fig.text(0.5,0.055,'Dashed lines guide the eye; no fitted PEC. Error bars: sample SD where available.',ha='center',fontsize=8)
        note='Diagnostic only: no FCI energy target on this axis.'
        if energy_error or metric=='total_energy':
            note='Reference: converged FCI in the same basis and active space; not experimental truth.'
        elif data.get('log_y'):
            note='Ideal roundtrip difference = 0 (not drawable on this logarithmic axis).'
        fig.text(0.5,0.015,note,ha='center',fontsize=8)
        fig.savefig(stem.with_suffix('.png'),dpi=180,bbox_inches='tight',pad_inches=0.15)
        fig.savefig(stem.with_suffix('.svg'),bbox_inches='tight',pad_inches=0.15)
        plt.close(fig)
    svg=stem.with_suffix('.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    stem.with_suffix('.json').write_text(json.dumps(dict(source_report=str(path),**data),indent=2))
    points=report.get('targets',report.get('points',[]))
    if metric=='error' and data['xlabel']=='Bond length (angstrom)' and len(points)>1 and all('reference' in p or ('report' in p and json.loads(Path(p['report']).read_text()).get('reference')) for p in points):
        plot_report(path,str(stem)+'_total_energy',metric='total_energy')
    return str(stem.with_suffix('.png'))
