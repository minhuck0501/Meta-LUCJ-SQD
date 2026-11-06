import argparse
import json
from pathlib import Path

from meta_lucj_sqd.plotting import plot_report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('reports',nargs='*')
    args=parser.parse_args()
    if args.reports:
        for report in args.reports:
            print(plot_report(report))
    else:
        for report in sorted(Path('docs/experiments').glob('*summary.json')):
            output=plot_report(report,Path('docs/experiments/figures')/report.stem)
            if output:print(output)
        output=plot_report('results/phase1_20261103T064449/report.json','docs/experiments/figures/phase1')
        if output:print(output)
        summary=json.loads(Path('docs/experiments/phase3_summary.json').read_text())
        plot_report(summary['source_report'],'docs/experiments/figures/phase3_training_curve')
        repetitions=json.loads(Path('docs/experiments/phase3_repetitions_summary.json').read_text())
        for trial in repetitions['jobs']:
            plot_report(trial['source_report'],'docs/experiments/figures/phase3_'+trial['name']+'_training_curve')
        for report in sorted(Path('results').glob('*/report.json')):
            plot_report(report)


if __name__=='__main__':
    main()
