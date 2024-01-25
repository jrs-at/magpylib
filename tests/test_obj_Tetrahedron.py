import numpy as np
import pytest

import magpylib as magpy
from magpylib._src.exceptions import MagpylibBadUnitsInput
from magpylib._src.exceptions import MagpylibBadUserInput


def test_Tetrahedron_repr():
    """Tetrahedron repr test"""
    tetra = magpy.magnet.Tetrahedron()
    assert repr(tetra)[:11] == "Tetrahedron", "Tetrahedron repr failed"


def test_tetra_input():
    """test obj-oriented triangle vs cube"""
    obs = (1, 2, 3)
    pol = (111, 222, 333)
    vert_list = [
        [(1, 1, -1), (1, 1, 1), (-1, 1, 1), (1, -1, 1)],
        [(-1, -1, 1), (-1, 1, 1), (1, -1, 1), (1, -1, -1)],
        [(-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)],
        [(-1, 1, -1), (1, -1, -1), (-1, -1, 1), (-1, 1, 1)],
        [(1, -1, -1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)],
        [(-1, 1, -1), (-1, 1, 1), (1, 1, -1), (1, -1, -1)],
    ]

    coll = magpy.Collection()
    for v in vert_list:
        coll.add(magpy.magnet.Tetrahedron(polarization=pol, vertices=v))

    cube = magpy.magnet.Cuboid(polarization=pol, dimension=(2, 2, 2))

    b = coll.getB(obs)
    bb = cube.getB(obs)
    np.testing.assert_allclose(b, bb)

    h = coll.getH(obs)
    hh = cube.getH(obs)
    np.testing.assert_allclose(h, hh)


@pytest.mark.parametrize(
    "vertices",
    [
        1,
        [[(1, 1, -1), (1, 1, 1), (-1, 1, 1), (1, -1, 1)]] * 2,
        [(1, 1, -1), (1, 1, 1), (-1, 1, 1)],
        "123",
    ],
)
def test_tetra_bad_inputs(vertices):
    """test obj-oriented triangle vs cube"""

    with pytest.raises((MagpylibBadUserInput, MagpylibBadUnitsInput)):
        magpy.magnet.Tetrahedron(polarization=(0.111, 0.222, 0.333), vertices=vertices)


def test_tetra_barycenter():
    """get barycenter"""
    pol = (0.111, 0.222, 0.333)
    vert = [(1, 1, -1), (1, 1, 1), (-1, 1, 1), (1, -1, 1)]
    tetra = magpy.magnet.Tetrahedron(polarization=pol, vertices=vert)
    np.testing.assert_allclose(tetra.barycenter, (0.5, 0.5, 0.5))
