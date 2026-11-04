import ffsim
import numpy as np
from pyscf import gto
from scipy.linalg import polar


def orbital_overlap(source, target):
    cross = gto.intor_cross('int1e_ovlp', source.mf.mol, target.mf.mol)
    left = source.mf.mo_coeff[:, source.frozen_core:]
    right = target.mf.mo_coeff[:, target.frozen_core:]
    return left.conj().T @ cross @ right


def rotate_output(operator, rotation):
    final = operator.final_orbital_rotation
    if final is None:
        final = np.eye(rotation.shape[0])
    return ffsim.UCJOpSpinBalanced(operator.diag_coulomb_mats.copy(),
                                   operator.orbital_rotations.copy(), rotation @ final)


def polar_transfer(operator, source, target):
    overlap = orbital_overlap(source, target)
    rotation, _ = polar(overlap.conj().T)
    return rotate_output(operator, rotation), rotation


def block_polar_transfer(operator, source, target):
    overlap = orbital_overlap(source, target)
    occupied = source.nelec[0]
    rotation = np.zeros_like(overlap)
    for section in [slice(0, occupied), slice(occupied, source.norb)]:
        rotation[section, section], _ = polar(overlap[section, section].conj().T)
    return rotate_output(operator, rotation), rotation


def sign_transfer(operator, source, target):
    cross = gto.intor_cross('int1e_ovlp', source.mf.mol, target.mf.mol)
    left = source.mf.mo_coeff[:, source.frozen_core:]
    right = target.mf.mo_coeff[:, target.frozen_core:]
    overlap = left.T @ cross @ right
    signs = np.where(np.diag(overlap) < 0, -1., 1.)
    return transform_signs(operator, signs), dict(
        signs=signs.tolist(), diagonal_overlaps=np.diag(overlap).tolist(),
        min_abs_diagonal_overlap=float(np.min(np.abs(np.diag(overlap)))),
        max_abs_offdiagonal_overlap=float(np.max(np.abs(overlap-np.diag(np.diag(overlap))))))


def transform_signs(operator, signs):
    rotations = operator.orbital_rotations * signs[None, :, None] * signs[None, None, :]
    final = operator.final_orbital_rotation
    if final is not None:
        final = signs[:, None] * final * signs[None, :]
    return ffsim.UCJOpSpinBalanced(operator.diag_coulomb_mats.copy(), rotations, final)
