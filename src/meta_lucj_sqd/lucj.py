import ffsim
import numpy as np


def interaction_pairs(norb):
    return ([(p, p + 1) for p in range(norb - 1)],
            [(p, p) for p in range(0, norb, 4)])


def initialize(ccsd, norb, config):
    return ffsim.UCJOpSpinBalanced.from_t_amplitudes(
        ccsd.t2, t1=ccsd.t1 if config["final_rotation_from_t1"] else None,
        n_reps=config["n_reps"], interaction_pairs=interaction_pairs(norb),
        optimize=config["compressed"])


def prepare(op, norb, nelec):
    state = ffsim.hartree_fock_state(norb, nelec)
    return ffsim.apply_unitary(state, op, norb, nelec, copy=False)


def sample(state, norb, nelec, shots, seed):
    strings = ffsim.sample_state_vector(state, norb=norb, nelec=nelec,
                                       shots=shots, seed=seed)
    return np.array([[bit == "1" for bit in s] for s in strings], dtype=bool)
