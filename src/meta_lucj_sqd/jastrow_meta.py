import ffsim
import numpy as np

from meta_lucj_sqd.lucj import interaction_pairs


def parameter_count(norb):
    return sum(map(len,interaction_pairs(norb)))


def correct_jastrow(operator,coefficients,distance,center,scale):
    if operator.n_reps!=1 or scale<=0:
        raise ValueError('Jastrow pilot requires one repetition and positive geometry scale')
    coefficients=np.asarray(coefficients,dtype=float)
    if coefficients.shape!=(2,parameter_count(operator.norb)) or not np.all(np.isfinite(coefficients)):
        raise ValueError('Invalid Jastrow meta coefficients')
    correction=coefficients[0]+((distance-center)/scale)*coefficients[1]
    matrices=operator.diag_coulomb_mats.copy();index=0
    for spin,pairs in enumerate(interaction_pairs(operator.norb)):
        for p,q in pairs:
            matrices[0,spin,p,q]+=correction[index]
            if p!=q:matrices[0,spin,q,p]+=correction[index]
            index+=1
    return ffsim.UCJOpSpinBalanced(matrices,operator.orbital_rotations.copy(),None if operator.final_orbital_rotation is None else operator.final_orbital_rotation.copy())
