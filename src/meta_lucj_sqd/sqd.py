from functools import partial

import numpy as np
from pyscf import fci
from qiskit_addon_sqd.fermion import diagonalize_fermionic_hamiltonian, solve_sci_batch


def residual_norm(chemistry, state, energy):
    vector = fci.selected_ci._as_SCIvector(
        state.amplitudes, (state.ci_strs_a, state.ci_strs_b))
    effective = fci.direct_spin1.absorb_h1e(
        chemistry.h1, chemistry.eri, chemistry.norb, chemistry.nelec, 0.5)
    action = fci.selected_ci.contract_2e(effective, vector, chemistry.norb, chemistry.nelec)
    return float(np.linalg.norm(action - energy * vector))


def evaluate(chemistry, samples, config):
    history = []

    def callback(results):
        history.append([{"energy_total": float(r.energy + chemistry.ecore),
                         "dimension": int(r.sci_state.amplitudes.size),
                         "projected_residual_norm": residual_norm(chemistry, r.sci_state, r.energy)}
                        for r in results])

    result = diagonalize_fermionic_hamiltonian(
        chemistry.h1, chemistry.eri, samples,
        samples_per_batch=config["samples_per_batch"], norb=chemistry.norb,
        nelec=chemistry.nelec, num_batches=config["num_batches"],
        max_iterations=config["sqd_iterations"], energy_tol=1e-8,
        occupancies_tol=1e-6, symmetrize_spin=False,
        sci_solver=partial(solve_sci_batch, spin_sq=None,
                           max_cycle=config["solver_max_cycle"], tol=config["solver_tol"]),
        callback=callback, seed=config["seed"])
    return result, history
