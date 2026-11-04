import itertools

import ffsim
import numpy as np
from pyscf import fci, lib
from qiskit_addon_sqd.fermion import solve_fermion

from meta_lucj_sqd.chemistry import build_chemistry, hf_active_energy, run_ccsd
from meta_lucj_sqd.lucj import initialize, interaction_pairs, prepare, sample


def small_config():
    return dict(molecule="H", basis="sto-3g", distance_angstrom=0.74,
                frozen_core=0, expected_norb=2, expected_nelec=[1, 1],
                scf_tol=1e-12, ccsd_tol=1e-12, ccsd_amplitude_tol=1e-10,
                max_cycle=100, max_memory_mb=1000, n_reps=1,
                compressed=False, final_rotation_from_t1=True)


def test_chemistry_and_full_subspace():
    lib.num_threads(1)
    c = build_chemistry(small_config())
    assert abs(hf_active_energy(c) - c.mf.e_tot) < 1e-10
    mo = c.mf.mo_coeff
    np.testing.assert_allclose(mo.T @ c.mf.get_ovlp() @ mo, np.eye(c.norb), atol=1e-10)
    np.testing.assert_allclose(c.h1, c.h1.T, atol=1e-12)
    np.testing.assert_allclose(c.eri, c.eri.transpose(1, 0, 2, 3), atol=1e-12)
    np.testing.assert_allclose(c.eri, c.eri.transpose(2, 3, 0, 1), atol=1e-12)
    exact, _ = fci.direct_spin1.kernel(c.h1, c.eri, c.norb, c.nelec, tol=1e-12)
    strings = np.array([[b == "1" for b in beta + alpha]
                        for alpha, beta in itertools.product(["01", "10"], repeat=2)])
    energy, _, _, _ = solve_fermion(strings, c.h1, c.eri, open_shell=True,
                                   spin_sq=None, tol=1e-12)
    assert abs(energy - exact) < 1e-10
    h = ffsim.linear_operator(ffsim.MolecularHamiltonian(c.h1, c.eri), c.norb, c.nelec)
    dense = np.column_stack([h @ v.astype(complex) for v in np.eye(4)])
    np.testing.assert_allclose(dense, dense.conj().T, atol=1e-10)
    assert abs(np.linalg.eigvalsh(dense)[0] - exact) < 1e-10


def test_lucj_roundtrip_zero_and_sampling():
    lib.num_threads(1)
    cfg = small_config()
    c = build_chemistry(cfg)
    op = initialize(run_ccsd(c, cfg), c.norb, cfg)
    pairs = interaction_pairs(c.norb)
    params = op.to_parameters(interaction_pairs=pairs)
    restored = ffsim.UCJOpSpinBalanced.from_parameters(
        params, norb=c.norb, n_reps=1, interaction_pairs=pairs,
        with_final_orbital_rotation=True)
    state = prepare(op, c.norb, c.nelec)
    np.testing.assert_allclose(state, prepare(restored, c.norb, c.nelec), atol=1e-10)
    assert abs(np.linalg.norm(state) - 1) < 1e-10
    zero = ffsim.UCJOpSpinBalanced.from_parameters(
        np.zeros_like(params), norb=c.norb, n_reps=1,
        interaction_pairs=pairs, with_final_orbital_rotation=True)
    np.testing.assert_allclose(prepare(zero, c.norb, c.nelec),
                               ffsim.hartree_fock_state(c.norb, c.nelec), atol=1e-10)
    a = sample(state, c.norb, c.nelec, 100, 12345)
    np.testing.assert_array_equal(a, sample(state, c.norb, c.nelec, 100, 12345))
    assert np.all(a[:, :2].sum(axis=1) == 1)
    assert np.all(a[:, 2:].sum(axis=1) == 1)


def test_asymmetric_spin_and_endian():
    state = ffsim.hartree_fock_state(3, (2, 1))
    strings = ffsim.sample_state_vector(state, norb=3, nelec=(2, 1), shots=4, seed=1)
    assert strings == ["001011"] * 4


def test_sampled_sqd_and_residual():
    from meta_lucj_sqd.sqd import evaluate

    lib.num_threads(1)
    cfg = small_config()
    cfg.update(samples_per_batch=100, num_batches=2, sqd_iterations=2,
               solver_max_cycle=100, solver_tol=1e-12, seed=12345)
    c = build_chemistry(cfg)
    op = initialize(run_ccsd(c, cfg), c.norb, cfg)
    samples = sample(prepare(op, c.norb, c.nelec), c.norb, c.nelec, 1000, cfg["seed"])
    result, history = evaluate(c, samples, cfg)
    exact, _ = fci.direct_spin1.kernel(c.h1, c.eri, c.norb, c.nelec, tol=1e-12)
    assert exact - 1e-10 <= result.energy <= c.mf.e_tot - c.ecore + 1e-10
    assert all(r["projected_residual_norm"] < 1e-8 for rows in history for r in rows)


def test_sqd_complete_sample_support():
    from meta_lucj_sqd.sqd import evaluate

    lib.num_threads(1)
    cfg = small_config()
    cfg.update(samples_per_batch=100, num_batches=1, sqd_iterations=2,
               solver_max_cycle=100, solver_tol=1e-12, seed=12345)
    c = build_chemistry(cfg)
    samples = np.array([[b == "1" for b in beta + alpha]
                        for alpha, beta in itertools.product(["01", "10"], repeat=2)])
    result, history = evaluate(c, samples, cfg)
    exact, _ = fci.direct_spin1.kernel(c.h1, c.eri, c.norb, c.nelec, tol=1e-12)
    assert abs(result.energy - exact) < 1e-10
    assert all(r["projected_residual_norm"] < 1e-8 for rows in history for r in rows)


def test_compression_matches_library_constructor():
    from meta_lucj_sqd.initialization import compressed_initialization

    lib.num_threads(1)
    cfg = small_config()
    c = build_chemistry(cfg)
    cc = run_ccsd(c, cfg)
    options = dict(maxiter=100, ftol=1e-12, gtol=1e-7)
    op, diagnostics = compressed_initialization(cc, c.norb, cfg, options)
    expected = ffsim.UCJOpSpinBalanced.from_t_amplitudes(
        cc.t2, t1=cc.t1, n_reps=1, interaction_pairs=interaction_pairs(c.norb),
        optimize=True, options=options)
    np.testing.assert_allclose(prepare(op, c.norb, c.nelec),
                               prepare(expected, c.norb, c.nelec), atol=1e-10)
    assert np.isfinite(diagnostics['loss'])
    assert abs(np.linalg.norm(prepare(op, c.norb, c.nelec)) - 1) < 1e-10


def test_multistage_matches_library():
    from meta_lucj_sqd.initialization import compressed_initialization

    lib.num_threads(1)
    cfg = small_config()
    c = build_chemistry(cfg)
    cc = run_ccsd(c, cfg)
    options = dict(maxiter=100, ftol=1e-12, gtol=1e-7)
    op, diagnostics = compressed_initialization(cc, c.norb, cfg, options, [2, 1])
    expected = ffsim.UCJOpSpinBalanced.from_t_amplitudes(
        cc.t2, t1=cc.t1, n_reps=1, interaction_pairs=interaction_pairs(c.norb),
        optimize=True, options=options, multi_stage_start=2, multi_stage_step=1)
    np.testing.assert_allclose(prepare(op, c.norb, c.nelec),
                               prepare(expected, c.norb, c.nelec), atol=1e-10)
    assert len(diagnostics['stages']) == 2


def test_regularized_compression_matches_library():
    from meta_lucj_sqd.initialization import compressed_initialization

    lib.num_threads(1)
    cfg = small_config()
    c = build_chemistry(cfg)
    cc = run_ccsd(c, cfg)
    options = dict(maxiter=100, ftol=1e-12, gtol=1e-7)
    op, diagnostics = compressed_initialization(cc, c.norb, cfg, options, regularization=0.001)
    expected = ffsim.UCJOpSpinBalanced.from_t_amplitudes(
        cc.t2, t1=cc.t1, n_reps=1, interaction_pairs=interaction_pairs(c.norb),
        optimize=True, options=options, regularization=0.001)
    np.testing.assert_allclose(prepare(op, c.norb, c.nelec),
                               prepare(expected, c.norb, c.nelec), atol=1e-10)
    assert diagnostics['regularization'] == 0.001


def test_spsa_step_quadratic_and_cap():
    from meta_lucj_sqd.optimization import spsa_step

    x=np.array([1.,2.]);direction=np.array([1.,-1.])
    cfg=dict(a=0.1,c=0.01,alpha=0.602,gamma=0.101,stability=1,max_step_norm=0.1)
    plus=float(np.sum((x+0.01*direction)**2));minus=float(np.sum((x-0.01*direction)**2))
    updated=spsa_step(x,plus,minus,direction,0,cfg)
    assert np.linalg.norm(updated-x)<=0.1+1e-12
    assert np.sum(updated**2)<np.sum(x**2)


def test_sign_transfer_preserves_gauge_state_and_energy():
    from meta_lucj_sqd.transfer import transform_signs

    lib.num_threads(1)
    cfg=small_config();c=build_chemistry(cfg)
    pairs=interaction_pairs(c.norb)
    count=ffsim.UCJOpSpinBalanced.n_params(c.norb,1,interaction_pairs=pairs,with_final_orbital_rotation=True)
    parameters=np.random.default_rng(65432).normal(scale=0.2,size=count)
    op=ffsim.UCJOpSpinBalanced.from_parameters(parameters,norb=c.norb,n_reps=1,interaction_pairs=pairs,with_final_orbital_rotation=True)
    signs=np.array([-1.,1.])
    state=prepare(op,c.norb,c.nelec)
    assert abs(state[0])**2 < 0.99
    transformed=prepare(transform_signs(op,signs),c.norb,c.nelec)
    expected=ffsim.apply_orbital_rotation(state,np.diag(signs),c.norb,c.nelec)
    np.testing.assert_allclose(transformed,expected,atol=1e-10)
    h1=c.h1*signs[:,None]*signs[None,:]
    eri=c.eri*np.einsum('p,q,r,s->pqrs',signs,signs,signs,signs)
    h=ffsim.linear_operator(ffsim.MolecularHamiltonian(c.h1,c.eri),c.norb,c.nelec)
    hg=ffsim.linear_operator(ffsim.MolecularHamiltonian(h1,eri),c.norb,c.nelec)
    assert abs(np.vdot(state,h@state)-np.vdot(transformed,hg@transformed))<1e-10


def test_output_rotation_and_jastrow_periodicity():
    from meta_lucj_sqd.transfer import rotate_output

    lib.num_threads(1)
    norb=2;nelec=(1,1);pairs=interaction_pairs(norb)
    count=ffsim.UCJOpSpinBalanced.n_params(norb,1,interaction_pairs=pairs,with_final_orbital_rotation=True)
    parameters=np.random.default_rng(657).normal(scale=0.3,size=count)
    op=ffsim.UCJOpSpinBalanced.from_parameters(parameters,norb=norb,n_reps=1,interaction_pairs=pairs,with_final_orbital_rotation=True)
    rotation=np.array([[0.,-1.],[1.,0.]])
    state=prepare(op,norb,nelec)
    np.testing.assert_allclose(prepare(rotate_output(op,rotation),norb,nelec),
        ffsim.apply_orbital_rotation(state,rotation,norb,nelec),atol=1e-10)
    shifted=op.diag_coulomb_mats.copy();shifted[0,1,0,0]+=2*np.pi
    equivalent=ffsim.UCJOpSpinBalanced(shifted,op.orbital_rotations,op.final_orbital_rotation)
    np.testing.assert_allclose(prepare(equivalent,norb,nelec),state,atol=1e-10)


def test_block_transport_preserves_reference_occupations():
    from types import SimpleNamespace
    from unittest.mock import patch
    from meta_lucj_sqd.transfer import block_polar_transfer

    norb=4;nelec=(2,2);pairs=interaction_pairs(norb)
    count=ffsim.UCJOpSpinBalanced.n_params(norb,1,interaction_pairs=pairs,with_final_orbital_rotation=True)
    params=np.random.default_rng(887).normal(scale=0.1,size=count)
    op=ffsim.UCJOpSpinBalanced.from_parameters(params,norb=norb,n_reps=1,interaction_pairs=pairs,with_final_orbital_rotation=True)
    overlap=np.array([[0.8,0.3,0.1,0.0],[-0.3,0.8,0.0,0.1],[0.1,0.0,0.7,0.2],[0.0,0.1,-0.2,0.7]])
    c=SimpleNamespace(norb=norb,nelec=nelec)
    with patch('meta_lucj_sqd.transfer.orbital_overlap',return_value=overlap):
        transformed,rotation=block_polar_transfer(op,c,c)
    np.testing.assert_allclose(rotation.T@rotation,np.eye(norb),atol=1e-10)
    np.testing.assert_allclose(rotation[:2,2:],0,atol=1e-10)
    hf=ffsim.hartree_fock_state(norb,nelec)
    np.testing.assert_allclose(ffsim.apply_orbital_rotation(hf,rotation,norb,nelec),hf,atol=1e-10)
    np.testing.assert_allclose(prepare(transformed,norb,nelec),ffsim.apply_orbital_rotation(prepare(op,norb,nelec),rotation,norb,nelec),atol=1e-10)
