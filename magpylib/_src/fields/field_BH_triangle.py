"""
Implementations of analytical expressions for the magnetic field of a triangular surface.
Computation details in function docstrings.
"""
# pylance: disable=Code is unreachable
import numpy as np

from magpylib._src.input_checks import check_field_input
from magpylib._src.utility import MU0


def vcross3(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    vectorized cross product for 3d vectors. Is ~4x faster than np.cross when
    arrays are smallish. Only slightly faster for large arrays.
    input shape a,b: (n,3)
    returns: (n, 3)
    """
    # receives nan values at corners
    with np.errstate(invalid="ignore"):
        result = np.array(
            [
                a[:, 1] * b[:, 2] - a[:, 2] * b[:, 1],
                a[:, 2] * b[:, 0] - a[:, 0] * b[:, 2],
                a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0],
            ]
        )
    return result.T


def norm_vector(v) -> np.ndarray:
    """
    Calculates normalized orthogonal vector on a plane defined by three vertices.
    """
    a = v[:, 1] - v[:, 0]
    b = v[:, 2] - v[:, 0]
    n = vcross3(a, b)
    n_norm = np.linalg.norm(n, axis=-1)
    return n / np.expand_dims(n_norm, axis=-1)


def solid_angle(R: np.ndarray, r: np.ndarray) -> np.ndarray:
    """
    Vectorized computation of the solid angle of triangles.

    Triangle point indices are 1,2,3, different triangles are denoted by a,b,c,...
    The first triangle is defined as R1a, R2a, R3a.

    Input:
    R = [(R1a, R1b, R1c, ...), (R2a, R2b, R2c, ...), (R3a, R3b, R3c, ...)]
    r = [(|R1a|, |R1b|, |R1c|, ...), (|R2a|, |R2b|, |R2c|, ...), (|R3a|, |R3b|, |R3c|, ...)]

    Returns:
    [sangle_a, sangle_b, sangle_c, ...]
    """

    # Calculates (oriented) volume of the parallelepiped in vectorized form.
    N = np.einsum("ij, ij->i", R[2], vcross3(R[1], R[0]))

    D = (
        r[0] * r[1] * r[2]
        + np.einsum("ij, ij->i", R[2], R[1]) * r[0]
        + np.einsum("ij, ij->i", R[2], R[0]) * r[1]
        + np.einsum("ij, ij->i", R[1], R[0]) * r[2]
    )
    result = 2.0 * np.arctan2(N, D)

    # modulus 2pi to avoid jumps on edges in line
    # "B = sigma * ((n.T * solid_angle(R, r)) - vcross3(n, PQR).T)"
    # <-- bad fix :(

    return np.where(abs(result) > 6.2831853, 0, result)


# CORE
def triangle_field(
    *,
    field: str,
    observers: np.ndarray,
    vertices: np.ndarray,
    polarizations: np.ndarray,
) -> np.ndarray:
    """Magnetic field generated by homogeneously magnetically charged triangular surfaces.

    SI units are used for all inputs and outputs.

    Can be used to compute the field of a homogeneously magnetized bodies
    with triangular surface mesh. In this case each Triangle must be defined so that the
    normal vector points outwards.

    Parameters
    ----------
    field: str, default=`'B'`
        If `field='B'` return B-field in units of T, if `field='H'` return H-field
        in units of A/m.

    observers: ndarray, shape (n,3)
        Observer positions (x,y,z) in Cartesian coordinates in units of m.

    dimensions: ndarray, shape (n,3)
        Length of Cuboid sides in units of m.

    polarizations: ndarray, shape (n,3)
        Magnetic polarization vectors in units of T. The triangle surface charge is the
        projection of the polarization vector onto the surface normal vector. The order
        of the vertices defines the sign of the normal vector (right-hand-rule).

    Returns
    -------
    B-field or H-field: ndarray, shape (n,3)
        B- or H-field of magnet in Cartesian coordinates in units of T or A/m.

    Examples
    --------
    Compute the B-field of two different triangle-observer instances.

    >>> import numpy as np
    >>> import magpylib as magpy
    >>> B = magpy.core.triangle_field(
    >>>     field='B',
    >>>     observers=np.array([(-.1,.2,.1), (.1,.2,.1)]),
    >>>     vertices=np.array([((-1,0,0), (1,-1,0), (1,1,0))]*2),
    >>>     polarizations=np.array([(.22,.33,.44), (.33,.44,.55)]),
    >>> )
    >>> print(B)
    [[-0.0548087   0.05350955  0.17683832]
     [-0.04252323  0.05292106  0.23092368]]

    Notes
    -----
    Advanced unit use: The input unit of magnetization and polarization
    gives the output unit of H and B. All results are independent of the
    length input units. One must be careful, however, to use consistently
    the same length unit throughout a script.

    Field computations implemented from Guptasarma, Geophysics, 1999, 64:1, 70-74.
    Corners give (nan, nan, nan). Edges and in-plane perp components are set to 0.
    Loss of precision when approaching a triangle as (x-edge)**2 :(
    Loss of precision with distance from the triangle as distance**3 :(
    """
    # pylint: disable=too-many-statements
    bh = check_field_input(field, "triangle_field()")

    n = norm_vector(vertices)
    sigma = np.einsum("ij, ij->i", n, polarizations)  # vectorized inner product

    # vertex <-> observer
    R = np.swapaxes(vertices, 0, 1) - observers
    r2 = np.sum(R * R, axis=-1)
    r = np.sqrt(r2)

    # vertex <-> vertex
    L = vertices[:, (1, 2, 0)] - vertices[:, (0, 1, 2)]
    L = np.swapaxes(L, 0, 1)
    l2 = np.sum(L * L, axis=-1)
    l = np.sqrt(l2)

    # vert-vert -- vert-obs
    b = np.einsum("ijk, ijk->ij", R, L)
    bl = b / l
    ind = np.fabs(r + bl)  # closeness measure to corner and edge

    # The computation of ind is the origin of a major numerical instability
    #    when approaching the triangle because r ~ -bl. This number
    #    becomes small at the same rate as it looses precision.
    #    This is a major problem, because at distances 1e-8 and 1e8 all precision
    #    is already lost !!!
    # The second problem is at corner and edge extensions where ind also computes
    #    as 0. Here one approaches a special case where another evaluation should
    #    be used. This problem is solved in the following lines.
    # np.seterr must be used because of a numpy bug. It does not interpret where
    #   correctly. The following code will raise a numpy warning - but obviously shouldn't
    #
    # x = np.array([(0,1,2), (0,0,1)])
    # np.where(
    #     x>0,
    #     1/x,
    #     0
    # )

    with np.errstate(divide="ignore", invalid="ignore"):
        I = np.where(
            ind > 1.0e-12,
            1.0 / l * np.log((np.sqrt(l2 + 2 * b + r2) + l + bl) / ind),
            -(1.0 / l) * np.log(np.fabs(l - r) / r),
        )
    PQR = np.einsum("ij, ijk -> jk", I, L)
    B = sigma * (n.T * solid_angle(R, r) - vcross3(n, PQR).T)

    # return B or compute and return H -------------
    if bh:
        return B.T / np.pi / 4.0

    H = B.T / 4 / np.pi / MU0
    return H
