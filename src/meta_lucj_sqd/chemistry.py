from dataclasses import dataclass

import numpy as np
from pyscf import ao2mo, cc, gto, mcscf, scf


@dataclass
class Chemistry:
    mf: object
    h1: np.ndarray
    eri: np.ndarray
    ecore: float
    norb: int
    nelec: tuple[int, int]
    frozen_core: int


def build_chemistry(config):
    atom = config["molecule"]
    mol = gto.M(atom=f"{atom} 0 0 0; {atom} 0 0 {config['distance_angstrom']}",
                basis=config["basis"], unit="Angstrom", charge=0, spin=0, verbose=0)
    mf = scf.RHF(mol)
    mf.conv_tol = config["scf_tol"]
    mf.max_cycle = config["max_cycle"]
    mf.max_memory = config["max_memory_mb"]
    mf.kernel()
    if not mf.converged:
        raise RuntimeError("SCF did not converge")
    core = config["frozen_core"]
    norb = mol.nao_nr() - core
    nelec = ((mol.nelectron - 2 * core) // 2,) * 2
    if norb != config["expected_norb"] or list(nelec) != config["expected_nelec"]:
        raise ValueError("Unexpected active space")
    cas = mcscf.CASCI(mf, norb, nelec)
    h1, ecore = cas.get_h1cas()
    eri = ao2mo.restore(1, cas.get_h2cas(), norb)
    return Chemistry(mf, h1, eri, float(ecore), norb, nelec, core)


def run_ccsd(chemistry, config):
    solver = cc.CCSD(chemistry.mf, frozen=chemistry.frozen_core)
    solver.conv_tol = config["ccsd_tol"]
    solver.conv_tol_normt = config["ccsd_amplitude_tol"]
    solver.max_cycle = config["max_cycle"]
    solver.kernel()
    if not solver.converged:
        raise RuntimeError("CCSD did not converge")
    return solver


def hf_active_energy(chemistry):
    occupied = range(chemistry.nelec[0])
    energy = chemistry.ecore + 2 * sum(chemistry.h1[i, i] for i in occupied)
    energy += sum(2 * chemistry.eri[i, i, j, j] - chemistry.eri[i, j, j, i]
                  for i in occupied for j in occupied)
    return float(energy)
