from meta_lucj_sqd.plotting import plot_report
import argparse
import hashlib
import importlib.metadata
import json
import platform
import resource
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import ffsim
import numpy as np
from pyscf import fci, lib

from meta_lucj_sqd.chemistry import build_chemistry, hf_active_energy, run_ccsd
from meta_lucj_sqd.lucj import initialize, interaction_pairs, prepare, sample
from meta_lucj_sqd.sqd import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase1.json")
    parser.add_argument("--reference", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path("results") / datetime.now(timezone.utc).strftime("phase1_%Y%m%dT%H%M%S")
    out.mkdir(parents=True)
    for source in [Path(__file__), Path(args.config), Path("pyproject.toml"),
                   *Path("src/meta_lucj_sqd").glob("*.py")]:
        destination = out / "source_snapshot" / source.resolve().relative_to(Path.cwd())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    lib.num_threads(cfg["threads"])
    report = dict(config=cfg, config_sha256=hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, platform=platform.platform(), architecture=platform.machine(),
                  versions={p: importlib.metadata.version(p) for p in
                            ["numpy", "scipy", "pyscf", "ffsim", "qiskit", "qiskit-addon-sqd"]},
                  git_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  git_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
                  thread_environment={k: os.environ.get(k) for k in
                                      ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]},
                  pyscf_effective_threads=lib.num_threads(),
                  reference_requested=args.reference,
                  timings={}, status="running")
    start = time.perf_counter()

    def save():
        report["wall_seconds"] = time.perf_counter() - start
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report["peak_rss_mib"] = rss / (1024 ** 2 if sys.platform == "darwin" else 1024)
        target = out / "report.json"
        temp = out / "report.tmp"
        temp.write_text(json.dumps(report, indent=2, allow_nan=False))
        temp.replace(target)

    def stage(name, function):
        tick = time.perf_counter()
        value = function()
        report["timings"][name] = time.perf_counter() - tick
        save()
        print(name, round(report["timings"][name], 3), flush=True)
        return value

    try:
        c = stage("chemistry", lambda: build_chemistry(cfg))
        report["chemistry"] = dict(hf_total=float(c.mf.e_tot), ecore=c.ecore,
                                    nuclear_repulsion=float(c.mf.mol.energy_nuc()),
                                    hf_reconstruction_error=hf_active_energy(c) - c.mf.e_tot,
                                    scf_converged=bool(c.mf.converged), norb=c.norb, nelec=c.nelec,
                                    scf_gradient_norm=float(np.linalg.norm(c.mf.get_grad(c.mf.mo_coeff, c.mf.mo_occ))))
        if abs(report["chemistry"]["hf_reconstruction_error"]) > 1e-8:
            raise RuntimeError("HF reconstruction failed")
        np.savez_compressed(out / "integrals.npz", h1=c.h1, eri=c.eri, ecore=c.ecore,
                            mo_coeff=c.mf.mo_coeff, mo_energy=c.mf.mo_energy)
        cc = stage("ccsd", lambda: run_ccsd(c, cfg))
        report["chemistry"]["ccsd_total"] = float(cc.e_tot)
        report["chemistry"]["ccsd_converged"] = bool(cc.converged)
        np.savez_compressed(out / "amplitudes.npz", t1=cc.t1, t2=cc.t2)
        op = stage("lucj_initialization", lambda: initialize(cc, c.norb, cfg))
        params = op.to_parameters(interaction_pairs=interaction_pairs(c.norb))
        np.save(out / "parameters.npy", params)
        report["parameter_count"] = len(params)
        state = stage("state_preparation", lambda: prepare(op, c.norb, c.nelec))
        report["state_norm_error"] = float(abs(np.linalg.norm(state) - 1))
        if report["state_norm_error"] > 1e-10:
            raise RuntimeError("State normalization failed")
        samples = stage("sampling", lambda: sample(state, c.norb, c.nelec, cfg["shots"], cfg["seed"]))
        del state
        np.save(out / "samples.npy", samples)
        report["unique_samples"] = len(np.unique(samples, axis=0))
        report["valid_shots"] = int(np.sum((samples[:, :c.norb].sum(axis=1) == c.nelec[1]) &
                                            (samples[:, c.norb:].sum(axis=1) == c.nelec[0])))
        result, history = stage("sqd", lambda: evaluate(c, samples, cfg))
        report["sqd"] = dict(energy_total=float(result.energy + c.ecore), history=history,
                              dimension=int(result.sci_state.amplitudes.size))
        if any(row["projected_residual_norm"] > 1e-6 for iteration in history for row in iteration):
            raise RuntimeError("SQD projected eigenvector residual too large")
        np.savez_compressed(out / "sqd_state.npz", amplitudes=result.sci_state.amplitudes,
                            strings_a=result.sci_state.ci_strs_a, strings_b=result.sci_state.ci_strs_b)
        if args.reference:
            solver = fci.direct_spin1.FCI(c.mf.mol)
            solver.max_memory = cfg["max_memory_mb"]
            solver.max_cycle = cfg["reference_max_cycle"]
            solver.conv_tol = cfg["reference_tol"]
            energy, vector = stage("fci", lambda: solver.kernel(c.h1, c.eri, c.norb, c.nelec, ecore=c.ecore))
            effective = fci.direct_spin1.absorb_h1e(c.h1, c.eri, c.norb, c.nelec, 0.5)
            residual = stage("fci_residual", lambda: np.linalg.norm(
                fci.direct_spin1.contract_2e(effective, vector, c.norb, c.nelec)
                - (energy - c.ecore) * vector))
            report["reference"] = dict(energy_total=float(energy), converged=bool(solver.converged),
                                        residual_norm=float(residual))
            report["sqd"]["error_ha"] = float(result.energy + c.ecore - energy)
            del vector
            if not solver.converged or residual > 1e-4:
                report["status"] = "nonconverged"
                return
        report["status"] = "success"
    except BaseException:
        report["status"] = "interrupted" if isinstance(sys.exc_info()[1], KeyboardInterrupt) else "failed"
        report["exception"] = traceback.format_exc()
        raise
    finally:
        save()
        plot_report(out / "report.json")
        print(str(out / "report.json"), flush=True)


if __name__ == "__main__":
    main()
