import ffsim
import numpy as np
from scipy.linalg import polar

from meta_lucj_sqd.lucj import interaction_pairs


def change_block_frame(operator,rotation,occupied):
    norb=operator.norb
    if np.linalg.norm(rotation.conj().T@rotation-np.eye(norb))>1e-10:
        raise ValueError('Frame change must be unitary')
    if np.linalg.norm(rotation[:occupied,occupied:])+np.linalg.norm(rotation[occupied:,:occupied])>1e-10:
        raise ValueError('Frame change must preserve reference occupations')
    rotations=np.einsum('ij,kjl->kil',rotation,operator.orbital_rotations)
    final=operator.final_orbital_rotation
    if final is None:
        final=np.eye(norb)
    return ffsim.UCJOpSpinBalanced(operator.diag_coulomb_mats.copy(),rotations,
                                   rotation@final@rotation.conj().T)


def encode_operator(operator):
    pieces=[]
    pairs=interaction_pairs(operator.norb)
    for rotation,matrices in zip(operator.orbital_rotations,operator.diag_coulomb_mats):
        rotation=rotation.copy()
        rows=np.argmax(np.abs(rotation),axis=0)
        phases=np.angle(rotation[rows,np.arange(operator.norb)])
        rotation*=np.exp(-1j*phases)[None,:]
        pieces.extend([rotation.real.ravel(),rotation.imag.ravel()])
        for matrix,indices in zip(matrices,pairs):
            angles=np.array([matrix[p,q] for p,q in indices])
            pieces.extend([np.cos(angles),np.sin(angles)])
    if operator.final_orbital_rotation is None:
        raise ValueError('Representation requires final rotation')
    pieces.extend([operator.final_orbital_rotation.real.ravel(),operator.final_orbital_rotation.imag.ravel()])
    return np.concatenate(pieces)


def decode_operator(features,norb,n_reps):
    values=np.asarray(features,dtype=float)
    pairs=interaction_pairs(norb)
    expected=n_reps*(2*norb*norb+2*sum(map(len,pairs)))+2*norb*norb
    if values.shape!=(expected,) or not np.all(np.isfinite(values)):
        raise ValueError('Invalid representation feature vector')
    index=0

    def rotation():
        nonlocal index
        size=norb*norb
        matrix=(values[index:index+size]+1j*values[index+size:index+2*size]).reshape(norb,norb)
        index+=2*size
        if np.linalg.svd(matrix,compute_uv=False)[-1]<1e-10:
            raise ValueError('Singular predicted rotation')
        return polar(matrix)[0]

    rotations=[];diagonals=[]
    for _ in range(n_reps):
        rotations.append(rotation())
        matrices=np.zeros((2,norb,norb))
        for spin,indices in enumerate(pairs):
            size=len(indices)
            cosine=values[index:index+size];sine=values[index+size:index+2*size]
            index+=2*size
            if np.any(np.hypot(cosine,sine)<1e-10):
                raise ValueError('Undefined predicted Jastrow angle')
            for (p,q),angle in zip(indices,np.arctan2(sine,cosine)):
                matrices[spin,p,q]=matrices[spin,q,p]=angle
        diagonals.append(matrices)
    final=rotation()
    return ffsim.UCJOpSpinBalanced(np.array(diagonals),np.array(rotations),final)
