import ffsim
import numpy as np

from meta_lucj_sqd.lucj import interaction_pairs


def compressed_initialization(ccsd, norb, config, options, stages=None, regularization=0):
    pairs = interaction_pairs(norb)
    guess = ffsim.linalg.double_factorized_t2(ccsd.t2, tol=1e-8)
    allowed = sorted(set(pairs[0] + pairs[1]))
    mask_union = np.zeros((norb, norb))
    for p, q in allowed:
        mask_union[p, q] = mask_union[q, p] = 1
    initial_diagonals = guess[0][:config["n_reps"]] * mask_union
    initial_rotations = guess[1][:config["n_reps"]]
    nocc = ccsd.t2.shape[0]
    reconstructed = 1j * np.einsum(
        "kpq,kap,kip,kbq,kjq->ijab", initial_diagonals,
        initial_rotations[:, nocc:], initial_rotations[:, :nocc].conj(),
        initial_rotations[:, nocc:], initial_rotations[:, :nocc].conj(), optimize=True)
    initial_loss = 0.5 * np.sum(np.abs(reconstructed - ccsd.t2) ** 2)
    stage_results = []
    schedule = [config["n_reps"]] if stages is None else stages
    if schedule[-1] != config["n_reps"] or any(a <= b for a, b in zip(schedule, schedule[1:])):
        raise ValueError("Compression schedule must decrease to target repetitions")
    for terms in schedule:
        diagonals, rotations, result = ffsim.linalg.double_factorized_t2_compressed(
            ccsd.t2, initial_guess=guess, max_terms=terms,
            diag_coulomb_indices=allowed, regularization=regularization, options=options)
        stage_results.append(dict(terms=len(rotations), success=bool(result.success),
                                  message=str(result.message), iterations=int(result.nit),
                                  evaluations=int(result.nfev), loss=float(result.fun),
                                  gradient_norm=float(np.linalg.norm(result.jac))))
        guess = (diagonals, rotations)
    matrices = np.stack([diagonals, diagonals], axis=1)
    for spin, indices in enumerate(pairs):
        mask = np.zeros((norb, norb))
        for p, q in indices:
            mask[p, q] = mask[q, p] = 1
        matrices[:, spin] *= mask
    final = None
    if config["final_rotation_from_t1"]:
        final = ffsim.UCJOpSpinBalanced.from_t_amplitudes(
            ccsd.t2, t1=ccsd.t1, n_reps=config["n_reps"],
            interaction_pairs=pairs, optimize=False).final_orbital_rotation
    op = ffsim.UCJOpSpinBalanced(matrices, rotations, final)
    diagnostics = dict(success=bool(result.success), message=str(result.message),
                       iterations=int(result.nit), evaluations=int(result.nfev),
                       loss=float(result.fun), gradient_norm=float(np.linalg.norm(result.jac)),
                       initial_union_mask_loss=float(initial_loss),
                       regularization=regularization, multi_stage=stages is not None,
                       final_j_norm_squared=float(np.sum(diagonals ** 2)),
                       stages=stage_results,
                       all_stages_success=all(s["success"] for s in stage_results))
    return op, diagnostics
