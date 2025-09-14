"""Coordinate frame transformations and geometry utilities."""

import numpy as np
from typing import Tuple, Union


class CoordinateFrame:
    """Handle coordinate transformations for different plane orientations."""

    def __init__(self, orientation: str, normal_sign: int = 1, rotate_deg: float = 0.0):
        """
        Initialize coordinate frame.

        Args:
            orientation: 'x', 'y', or 'z' for plane normal direction
            normal_sign: +1 or -1 for normal direction
            rotate_deg: In-plane rotation in degrees
        """
        self.orientation = orientation.lower()
        self.normal_sign = normal_sign
        self.rotate_deg = rotate_deg

        if self.orientation not in ['x', 'y', 'z']:
            raise ValueError("Orientation must be 'x', 'y', or 'z'")
        if normal_sign not in [1, -1]:
            raise ValueError("Normal sign must be +1 or -1")

        self._compute_basis()

    def _compute_basis(self):
        """Compute orthonormal basis vectors (u, v, w)."""
        # Define base vectors for each orientation
        if self.orientation == 'z':
            u_base = np.array([1.0, 0.0, 0.0])  # X direction
            v_base = np.array([0.0, 1.0, 0.0])  # Y direction
            w = np.array([0.0, 0.0, self.normal_sign])  # Z direction
        elif self.orientation == 'x':
            u_base = np.array([0.0, 1.0, 0.0])  # Y direction
            v_base = np.array([0.0, 0.0, 1.0])  # Z direction
            w = np.array([self.normal_sign, 0.0, 0.0])  # X direction
        elif self.orientation == 'y':
            u_base = np.array([1.0, 0.0, 0.0])  # X direction
            v_base = np.array([0.0, 0.0, 1.0])  # Z direction
            w = np.array([0.0, self.normal_sign, 0.0])  # Y direction

        # Apply in-plane rotation
        if abs(self.rotate_deg) > 1e-10:
            rot_rad = np.deg2rad(self.rotate_deg)
            cos_rot = np.cos(rot_rad)
            sin_rot = np.sin(rot_rad)

            # Rotate u and v vectors in the plane
            u_rotated = cos_rot * u_base + sin_rot * v_base
            v_rotated = -sin_rot * u_base + cos_rot * v_base

            self.u_vec = u_rotated
            self.v_vec = v_rotated
        else:
            self.u_vec = u_base
            self.v_vec = v_base

        self.w_vec = w

        # Store as matrix for efficient transformation
        self.basis_matrix = np.column_stack([self.u_vec, self.v_vec, self.w_vec])

    def local_to_world(self, u: float, v: float, origin: np.ndarray = None) -> np.ndarray:
        """
        Transform local (u, v) coordinates to world coordinates.

        Args:
            u, v: Local coordinates
            origin: World origin point (default: [0,0,0])

        Returns:
            3D world coordinates
        """
        if origin is None:
            origin = np.zeros(3)

        return origin + u * self.u_vec + v * self.v_vec

    def get_normal(self) -> np.ndarray:
        """Get the surface normal vector."""
        return self.w_vec.copy()


def create_rectangle_vertices(center: Tuple[float, float],
                            half_width: float,
                            half_height: float) -> np.ndarray:
    """
    Create rectangle vertices in local (u, v) coordinates.

    Args:
        center: Rectangle center (u, v)
        half_width: Half-width along u axis
        half_height: Half-height along v axis

    Returns:
        4x2 array of vertices in CCW order
    """
    uc, vc = center

    vertices = np.array([
        [uc - half_width, vc - half_height],  # Bottom-left
        [uc + half_width, vc - half_height],  # Bottom-right
        [uc + half_width, vc + half_height],  # Top-right
        [uc - half_width, vc + half_height],  # Top-left
    ])

    return vertices


def compute_cell_bounds(i: int, j: int, nx: int, ny: int,
                       W: float, H: float, border_gap: float = 0.0) -> Tuple[float, float, float, float]:
    """
    Compute cell bounds in local coordinates.

    Args:
        i, j: Cell indices
        nx, ny: Grid dimensions
        W, H: Total rectangle dimensions
        border_gap: Gap to shrink cell bounds

    Returns:
        (u0, u1, v0, v1) cell bounds
    """
    du = W / nx
    dv = H / ny

    u0 = -W/2 + i * du
    u1 = u0 + du
    v0 = -H/2 + j * dv
    v1 = v0 + dv

    # Apply border gap
    if border_gap > 0:
        u0 += border_gap
        u1 -= border_gap
        v0 += border_gap
        v1 -= border_gap

        # Ensure valid bounds
        if u1 <= u0 or v1 <= v0:
            raise ValueError(f"Border gap {border_gap} too large for cell size")

    return u0, u1, v0, v1


def compute_inner_rectangle_size(outer_half_width: float, outer_half_height: float,
                               sx: float, sy: float, inner_size_mode: str) -> Tuple[float, float]:
    """
    Compute inner rectangle half-dimensions.

    Args:
        outer_half_width, outer_half_height: Outer rectangle half-dimensions
        sx, sy: Size parameters
        inner_size_mode: 'relative' or 'absolute'

    Returns:
        (inner_half_width, inner_half_height)
    """
    if inner_size_mode == 'relative':
        inner_half_width = outer_half_width * sx
        inner_half_height = outer_half_height * sy
    elif inner_size_mode == 'absolute':
        inner_half_width = sx / 2
        inner_half_height = sy / 2
    else:
        raise ValueError("inner_size_mode must be 'relative' or 'absolute'")

    # Clamp to valid range
    inner_half_width = max(1e-10, min(inner_half_width, outer_half_width))
    inner_half_height = max(1e-10, min(inner_half_height, outer_half_height))

    return inner_half_width, inner_half_height