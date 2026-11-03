import ffsim
import numpy as np

from meta_lucj_sqd.lucj import interaction_pairs


def compressed_initialization(ccsd, norb, config, options):
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
    diagonals, rotations, result = ffsim.linalg.double_factorized_t2_compressed(
        ccsd.t2, initial_guess=guess, max_terms=config["n_reps"],
        diag_coulomb_indices=allowed,
        regularization=0, options=options)
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
                       regularization=0, multi_stage=False)
    return op, diagnostics
