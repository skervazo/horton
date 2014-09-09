# -*- coding: utf-8 -*-
# Horton is a development platform for electronic structure methods.
# Copyright (C) 2011-2013 Toon Verstraelen <Toon.Verstraelen@UGent.be>
#
# This file is part of Horton.
#
# Horton is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# Horton is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
#--
#pylint: skip-file


import numpy as np
from nose.tools import assert_raises

from horton import *


def get_water_sto3g_hf(lf=None):
    if lf is None:
        lf = DenseLinalgFactory(7)
    fn = context.get_fn('test/water_sto3g_hf_g03.log')
    coeffs = np.array([
        9.94099882E-01, 2.67799213E-02, 3.46630004E-03, -1.54676269E-15,
        2.45105601E-03, -6.08393842E-03, -6.08393693E-03, -2.32889095E-01,
        8.31788042E-01, 1.03349385E-01, 9.97532839E-17, 7.30794097E-02,
        1.60223990E-01, 1.60223948E-01, 1.65502862E-08, -9.03020258E-08,
        -3.46565859E-01, -2.28559667E-16, 4.90116062E-01, 4.41542336E-01,
        -4.41542341E-01, 1.00235366E-01, -5.23423149E-01, 6.48259144E-01,
        -5.78009326E-16, 4.58390414E-01, 2.69085788E-01, 2.69085849E-01,
        8.92936017E-17, -1.75482465E-16, 2.47517845E-16, 1.00000000E+00,
        5.97439610E-16, -3.70474007E-17, -2.27323914E-17, -1.35631600E-01,
        9.08581133E-01, 5.83295647E-01, -4.37819173E-16, 4.12453695E-01,
        -8.07337352E-01, -8.07337875E-01, 5.67656309E-08, -4.29452066E-07,
        5.82525068E-01, -6.76605679E-17, -8.23811720E-01, 8.42614916E-01,
        -8.42614243E-01
    ]).reshape(7,7).T
    epsilons = np.array([
        -2.02333942E+01, -1.26583942E+00, -6.29365088E-01, -4.41724988E-01,
        -3.87671783E-01, 6.03082408E-01, 7.66134805E-01
    ])
    occ_model = AufbauOccModel(5)
    exp_alpha = lf.create_expansion()
    exp_alpha.coeffs[:] = coeffs
    exp_alpha.energies[:] = epsilons
    occ_model.assign(exp_alpha)
    assert (exp_alpha.occupations == np.array([1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0])).all()
    # convert the cache dictionary to a real cache object
    cache = Cache()
    data = load_operators_g09(fn, lf)
    for key, value in data.iteritems():
        cache.dump(key, value)
    return lf, cache, exp_alpha


def test_fock_matrix_eigen():
    lf, cache, exp_alpha = get_water_sto3g_hf()
    nbasis = cache['olp'].nbasis

    hartree = lf.create_one_body(nbasis)
    exchange = lf.create_one_body(nbasis)
    dm_alpha = exp_alpha.to_dm()
    cache['er'].apply_direct(dm_alpha, hartree)
    cache['er'].apply_exchange(dm_alpha, exchange)

    # Construct the Fock operator
    fock = lf.create_one_body(nbasis)
    fock.iadd(cache['kin'], 1)
    fock.iadd(cache['na'], -1)
    fock.iadd(hartree, 2)
    fock.iadd(exchange, -1)

    # Check for convergence
    error = lf.error_eigen(fock, cache['olp'], exp_alpha)
    assert error > 0
    assert error < 1e-4

    # Check self-consistency of the orbital energies
    old_energies = exp_alpha.energies.copy()
    exp_alpha.from_fock(fock, cache['olp'])
    assert abs(exp_alpha.energies - old_energies).max() < 1e-4



def test_kinetic_energy_water_sto3g():
    lf, cache, exp_alpha = get_water_sto3g_hf()
    dm = exp_alpha.to_dm()
    dm.iscale(2)
    ekin = cache['kin'].expectation_value(dm)
    assert abs(ekin - 74.60736832935) < 1e-4


def test_ortho_water_sto3g():
    lf, cache, exp_alpha = get_water_sto3g_hf()
    for i0 in xrange(7):
        orb0 = exp_alpha.coeffs[:,i0]
        for i1 in xrange(i0+1):
            orb1 = exp_alpha.coeffs[:,i1]
            check = cache['olp'].dot(orb0, orb1)
            assert abs(check - (i0==i1)) < 1e-4


def test_potential_energy_water_sto3g_hf():
    lf, cache, exp_alpha = get_water_sto3g_hf()
    dm = exp_alpha.to_dm()
    dm.iscale(2)
    #epot = -nuclear_attraction.expectation_value(dm)
    epot = -cache['na'].expectation_value(dm)
    assert abs(epot - (-197.1170963957)) < 2e-3


def test_electron_electron_water_sto3g_hf():
    lf, cache, exp_alpha = get_water_sto3g_hf()
    hartree = lf.create_one_body()
    exchange = lf.create_one_body()
    dm = exp_alpha.to_dm()
    cache['er'].apply_direct(dm, hartree)
    cache['er'].apply_exchange(dm, exchange)
    eee = 2*hartree.expectation_value(dm) \
          - exchange.expectation_value(dm)
    assert abs(eee - 38.29686853319) < 1e-4


def test_hartree_fock_water():
    lf, cache, exp_alpha0 = get_water_sto3g_hf()

    # Neutral water molecule
    nalpha = 5

    # Construct the hamiltonian core guess
    hamcore = lf.create_one_body()
    hamcore.iadd(cache['kin'], 1)
    hamcore.iadd(cache['na'], -1)
    exp_alpha1 = lf.create_expansion()
    exp_alpha1.from_fock(hamcore, cache['olp'])
    exp_alpha1.occupations[:nalpha] = 1.0
    assert (exp_alpha1.energies != 0.0).all()

    # The SCF loop
    hartree = lf.create_one_body()
    exchange = lf.create_one_body()
    fock = lf.create_one_body()
    for i in xrange(1000):
        # Derive the density matrix
        dm_alpha = exp_alpha1.to_dm()
        # Construct the Fock operator
        fock.clear()
        fock.iadd(hamcore, 1)
        cache['er'].apply_direct(dm_alpha, hartree)
        cache['er'].apply_exchange(dm_alpha, exchange)
        fock.iadd(hartree, 2)
        fock.iadd(exchange, -1)
        # Check for convergence
        error = lf.error_eigen(fock, cache['olp'], exp_alpha1)
        if error < 1e-10:
            break
        # Derive the expansion and the density matrix from the fock operator
        exp_alpha1.from_fock(fock, cache['olp'])

    assert abs(exp_alpha0.energies - exp_alpha1.energies).max() < 1e-4

    # Check the hartree-fock energy
    dm_alpha = exp_alpha1.to_dm()
    hf1 = sum([
        -2*hartree.expectation_value(dm_alpha),
        +1*exchange.expectation_value(dm_alpha),
    ]) + exp_alpha1.energies[:nalpha].sum()*2
    hf2 = sum([
        2*cache['kin'].expectation_value(dm_alpha),
        -2*cache['na'].expectation_value(dm_alpha),
        +2*hartree.expectation_value(dm_alpha),
        -exchange.expectation_value(dm_alpha),
    ])
    enn = 9.2535672047 # nucleus-nucleus interaction
    assert abs(hf1 + enn - (-74.9592923284)) < 1e-4
    assert abs(hf2 + enn - (-74.9592923284)) < 1e-4


def test_dense_one_body_trace():
    lf = DenseLinalgFactory()
    op1 = lf.create_one_body(3)
    op1._array[:] = np.random.uniform(-1, 1, (3,3))
    assert op1.trace() == op1._array[0,0] + op1._array[1,1] + op1._array[2,2]


def test_dense_one_body_itranspose():
    lf = DenseLinalgFactory()
    op1 = lf.create_one_body(3)
    op2 = lf.create_one_body(3)
    op1._array[:] = np.random.uniform(-1, 1, (3,3))
    op2._array[:] = op1._array
    op2.itranspose()
    assert op1._array[0,1] == op2._array[1,0]


def test_dense_one_body_iscale():
    lf = DenseLinalgFactory()
    op = lf.create_one_body(3)
    op._array[:] = np.random.uniform(-1, 1, (3,3))
    tmp = op._array.copy()
    op.iscale(3.0)
    assert abs(op._array - 3*tmp).max() < 1e-10


def test_dense_linalg_factory_properties():
    lf = DenseLinalgFactory(5)
    assert lf.default_nbasis == 5
    lf = DenseLinalgFactory()
    assert lf.default_nbasis is None
    lf.default_nbasis = 10
    ex = lf.create_expansion()
    assert ex.nbasis == 10
    assert ex.nfn == 10
    assert ex.energies.shape == (10,)
    assert ex.occupations.shape == (10,)
    op1 = lf.create_one_body()
    assert op1.nbasis == 10
    op2 = lf.create_two_body()
    assert op2.nbasis == 10


def test_dense_expansion_properties():
    lf = DenseLinalgFactory()
    ex = lf.create_expansion(10, 8)
    assert ex.nbasis == 10
    assert ex.nfn == 8
    assert ex.coeffs.shape == (10,8) # orbitals stored as columns
    assert ex.energies.shape == (8,)
    assert ex.occupations.shape == (8,)


def test_dense_one_body_properties():
    lf = DenseLinalgFactory()
    op = lf.create_one_body(3)
    assert op.nbasis == 3
    op.set_element(0, 1, 1.2)
    assert op.get_element(0, 1) == 1.2


def test_dense_two_body_properties():
    lf = DenseLinalgFactory()
    op = lf.create_two_body(3)
    assert op.nbasis == 3


def test_dense_one_body_assign():
    lf = DenseLinalgFactory()
    op1 = lf.create_one_body(3)
    op2 = lf.create_one_body(3)
    op1._array[:] = np.random.uniform(0, 1, (3, 3))
    op2.assign(op1)
    assert (op1._array == op2._array).all()


def test_dense_one_body_copy():
    lf = DenseLinalgFactory()
    op1 = lf.create_one_body(3)
    op1._array[:] = np.random.uniform(0, 1, (3, 3))
    op2 = op1.copy()
    assert (op1._array == op2._array).all()


def test_dense_expansion_copy():
    lf = DenseLinalgFactory()
    exp1 = lf.create_expansion(3, 2)
    exp1._coeffs[:] = np.random.uniform(0, 1, (3, 2))
    exp1._energies[:] = np.random.uniform(0, 1, 2)
    exp1._occupations[:] = np.random.uniform(0, 1, 2)
    exp2 = exp1.copy()
    assert (exp1._coeffs == exp2._coeffs).all()
    assert (exp1._energies == exp2._energies).all()
    assert (exp1._occupations == exp2._occupations).all()


def test_homo_lumo_ch3_hf():
    fn_fchk = context.get_fn('test/ch3_hf_sto3g.fchk')
    mol = Molecule.from_file(fn_fchk)
    assert mol.exp_alpha.get_homo_index() == 4
    assert mol.exp_beta.get_homo_index() == 3
    assert mol.exp_alpha.get_lumo_index() == 5
    assert mol.exp_beta.get_lumo_index() == 4
    assert mol.exp_alpha.get_homo_index(1) == 3
    assert mol.exp_beta.get_homo_index(1) == 2
    assert mol.exp_alpha.get_lumo_index(1) == 6
    assert mol.exp_beta.get_lumo_index(1) == 5
    assert abs(mol.exp_alpha.get_homo_energy() - -3.63936540E-01) < 1e-8
    assert abs(mol.exp_alpha.get_homo_energy(1) - -5.37273275E-01) < 1e-8
    assert abs(mol.exp_alpha.get_lumo_energy() - 6.48361367E-01) < 1e-8
    assert abs(mol.exp_beta.get_homo_energy() - -5.18988806E-01) < 1e-8
    assert abs(mol.exp_beta.get_homo_energy(1) - -5.19454722E-01) < 1e-8
    assert abs(mol.exp_beta.get_lumo_energy() - 3.28562907E-01) < 1e-8
    assert abs(mol.exp_alpha.homo_energy - -3.63936540E-01) < 1e-8
    assert abs(mol.exp_alpha.lumo_energy - 6.48361367E-01) < 1e-8
    assert abs(mol.exp_beta.homo_energy - -5.18988806E-01) < 1e-8
    assert abs(mol.exp_beta.lumo_energy - 3.28562907E-01) < 1e-8


def test_naturals():
    fn_fchk = context.get_fn('test/ch3_hf_sto3g.fchk')
    mol = Molecule.from_file(fn_fchk)
    overlap = mol.obasis.compute_overlap(mol.lf)
    dm = mol.exp_alpha.to_dm()
    exp = mol.lf.create_expansion()
    exp.derive_naturals(dm, overlap)
    assert exp.occupations.min() > -1e-6
    assert exp.occupations.max() < 1+1e-6
    exp.check_normalization(overlap)


def test_linalg_objects_del():
    lf = DenseLinalgFactory()
    with assert_raises(TypeError):
        exp = lf.create_expansion()
    with assert_raises(TypeError):
        op1 = lf.create_one_body()
    with assert_raises(TypeError):
        op2 = lf.create_two_body()


def test_trace_product():
    lf = DenseLinalgFactory()
    op1 = lf.create_one_body(3)
    op2 = lf.create_one_body(3)
    op1._array[:] = np.random.uniform(0, 1, (3, 3))
    op2._array[:] = np.random.uniform(0, 1, (3, 3))

    value = op1.trace_product(op2)
    op1.idot(op2)
    assert abs(op1.trace() - value) < 1e-10


def get_four_cho_dens(nbasis=10, nvec=8):
    '''Create random cholesky vectors and matching dense four-index object'''
    vecs = []
    for ivec in xrange(nvec):
        vec = np.random.normal(0, 1, (nbasis, nbasis))
        vec = (vec+vec.T)/2
        vecs.append(vec)
    chob = CholeskyTwoBody(nbasis)
    chob._array = np.array(vecs)
    chob._array2 = chob._array
    chob._nvec = nvec
    erb = DenseTwoBody(nbasis)
    erb._array[:] = np.einsum('kac,kbd->abcd', chob._array, chob._array2)
    return chob, erb


def test_cholesky_get_slice():
    chob, erb = get_four_cho_dens()

    indices = "abab->ab"
    indices2 = "aabb-> ba"
    indices3 = "abba->ab"

    indices4 = 'abcc->bac'
    indices5 = 'abcc->abc'
    indices6 = 'abcb->abc'
    indices7 = 'abbc->abc'

    list_indices = [indices, indices2, indices3, indices4, indices5, indices6,
            indices7]

    for i in list_indices:
        assert np.allclose(erb.get_slice(i),chob.get_slice(i))

def test_cholesky_esum():
    chob, erb = get_four_cho_dens()

    assert np.allclose(erb.esum(), chob.esum())

def test_cholesky_apply_direct():
    chob, erb = get_four_cho_dens()

    A = np.random.random((erb.nbasis, erb.nbasis))
    dm = DenseOneBody(A.shape[0])
    dm._array = A

    out = DenseOneBody(A.shape[0])
    out2 = DenseOneBody(A.shape[0])

    erb.apply_direct(dm, out)
    chob.apply_direct(dm, out2)

    assert np.allclose(out._array, out2._array)

def test_cholesky_apply_exchange():
    chob, erb = get_four_cho_dens()

    A = np.random.random((erb.nbasis,erb.nbasis))
    dm = DenseOneBody(A.shape[0])
    dm._array = A

    out = DenseOneBody(A.shape[0])
    out2 = DenseOneBody(A.shape[0])

    erb.apply_exchange(dm, out)
    chob.apply_exchange(dm, out2)

    assert np.allclose(out._array, out2._array)

def test_cholesky_get_dense():
    chob, erb = get_four_cho_dens()

    assert np.allclose(erb._array, chob._get_dense())

def test_cholesky_four_index_transform_tensordot():
    chob, erb = get_four_cho_dens()

    A = np.random.random((erb.nbasis, erb.nbasis))
    de = DenseExpansion(A.shape[0])
    de._coeffs = A

    A2 = np.random.random((erb.nbasis, erb.nbasis))
    de2 = DenseExpansion(A2.shape[0])
    de2._coeffs = A2

    mo1 = DenseTwoBody(erb.nbasis)
    mo2 = CholeskyTwoBody(erb.nbasis)
    mo2._array = np.zeros_like(chob._array)
    mo2.reset_array2()
    mo2._nvec = chob._array.shape[2]

    mo1.apply_four_index_transform_tensordot(erb, de, de2, de, de2)
    mo2.apply_four_index_transform_tensordot(chob, de, de2, de, de2)

    assert np.allclose(mo1._array, mo2._get_dense())

def test_cholesky_four_index_transform_einsum():
    chob, erb = get_four_cho_dens()

    A = np.random.random((erb.nbasis,erb.nbasis))
    de = DenseExpansion(A.shape[0])
    de._coeffs = A

    A2 = np.random.random((erb.nbasis,erb.nbasis))
    de2 = DenseExpansion(A2.shape[0])
    de2._coeffs = A2

    mo1 = DenseTwoBody(erb.nbasis)
    mo2 = CholeskyTwoBody(erb.nbasis)
    mo2._array = np.zeros_like(chob._array)
    mo2.reset_array2()
    mo2._nvec = chob._array.shape[2]

    mo1.apply_four_index_transform_einsum(erb, de, de2, de, de2)
    mo2.apply_four_index_transform_einsum(chob, de, de2, de, de2)

    assert np.allclose(mo1._array, mo2._get_dense())
