"""Tests for geometry module."""

import numpy as np
import pytest
from stl_grid_generator.geometry import (
    CoordinateFrame, create_rectangle_vertices, compute_cell_bounds,
    compute_inner_rectangle_size
)


class TestCoordinateFrame:
    """Test coordinate frame transformations."""

    def test_z_orientation_default(self):
        """Test Z orientation with default parameters."""
        frame = CoordinateFrame('z')

        assert np.allclose(frame.u_vec, [1, 0, 0])
        assert np.allclose(frame.v_vec, [0, 1, 0])
        assert np.allclose(frame.w_vec, [0, 0, 1])

    def test_x_orientation(self):
        """Test X orientation."""
        frame = CoordinateFrame('x')

        assert np.allclose(frame.u_vec, [0, 1, 0])
        assert np.allclose(frame.v_vec, [0, 0, 1])
        assert np.allclose(frame.w_vec, [1, 0, 0])

    def test_y_orientation(self):
        """Test Y orientation."""
        frame = CoordinateFrame('y')

        assert np.allclose(frame.u_vec, [1, 0, 0])
        assert np.allclose(frame.v_vec, [0, 0, 1])
        assert np.allclose(frame.w_vec, [0, 1, 0])

    def test_negative_normal(self):
        """Test negative normal sign."""
        frame = CoordinateFrame('z', normal_sign=-1)

        assert np.allclose(frame.w_vec, [0, 0, -1])

    def test_rotation(self):
        """Test in-plane rotation."""
        frame = CoordinateFrame('z', rotate_deg=90)

        # After 90° rotation: u -> -v, v -> u
        assert np.allclose(frame.u_vec, [0, 1, 0], atol=1e-10)
        assert np.allclose(frame.v_vec, [-1, 0, 0], atol=1e-10)

    def test_local_to_world(self):
        """Test local to world coordinate transformation."""
        frame = CoordinateFrame('z')
        origin = np.array([1, 2, 3])

        result = frame.local_to_world(4, 5, origin)
        expected = np.array([5, 7, 3])  # origin + 4*u + 5*v

        assert np.allclose(result, expected)

    def test_invalid_orientation(self):
        """Test invalid orientation raises error."""
        with pytest.raises(ValueError, match="Orientation must be"):
            CoordinateFrame('invalid')

    def test_invalid_normal_sign(self):
        """Test invalid normal sign raises error."""
        with pytest.raises(ValueError, match="Normal sign must be"):
            CoordinateFrame('z', normal_sign=0)


class TestCreateRectangleVertices:
    """Test rectangle vertex creation."""

    def test_basic_rectangle(self):
        """Test basic rectangle creation."""
        vertices = create_rectangle_vertices((0, 0), 1, 2)

        expected = np.array([
            [-1, -2],  # Bottom-left
            [1, -2],   # Bottom-right
            [1, 2],    # Top-right
            [-1, 2],   # Top-left
        ])

        assert np.allclose(vertices, expected)

    def test_offset_center(self):
        """Test rectangle with offset center."""
        vertices = create_rectangle_vertices((3, 4), 0.5, 1.5)

        expected = np.array([
            [2.5, 2.5],  # Bottom-left
            [3.5, 2.5],  # Bottom-right
            [3.5, 5.5],  # Top-right
            [2.5, 5.5],  # Top-left
        ])

        assert np.allclose(vertices, expected)


class TestComputeCellBounds:
    """Test cell bounds computation."""

    def test_basic_grid(self):
        """Test basic 2x2 grid."""
        # Cell (0,0) in 2x2 grid with W=4, H=6
        u0, u1, v0, v1 = compute_cell_bounds(0, 0, 2, 2, 4, 6)

        assert u0 == -2  # -W/2 + 0*du = -2 + 0*2 = -2
        assert u1 == 0   # u0 + du = -2 + 2 = 0
        assert v0 == -3  # -H/2 + 0*dv = -3 + 0*3 = -3
        assert v1 == 0   # v0 + dv = -3 + 3 = 0

    def test_with_border_gap(self):
        """Test cell bounds with border gap."""
        u0, u1, v0, v1 = compute_cell_bounds(0, 0, 1, 1, 2, 2, border_gap=0.2)

        assert u0 == -0.8  # -1 + 0.2
        assert u1 == 0.8   # 1 - 0.2
        assert v0 == -0.8  # -1 + 0.2
        assert v1 == 0.8   # 1 - 0.2

    def test_border_gap_too_large(self):
        """Test border gap too large raises error."""
        with pytest.raises(ValueError, match="Border gap.*too large"):
            compute_cell_bounds(0, 0, 1, 1, 1, 1, border_gap=0.6)


class TestComputeInnerRectangleSize:
    """Test inner rectangle size computation."""

    def test_relative_mode(self):
        """Test relative sizing mode."""
        inner_hw, inner_hh = compute_inner_rectangle_size(2, 3, 0.5, 0.8, 'relative')

        assert inner_hw == 1.0  # 2 * 0.5
        assert inner_hh == 2.4  # 3 * 0.8

    def test_absolute_mode(self):
        """Test absolute sizing mode."""
        inner_hw, inner_hh = compute_inner_rectangle_size(2, 3, 1.5, 2.0, 'absolute')

        assert inner_hw == 0.75  # 1.5 / 2
        assert inner_hh == 1.0   # 2.0 / 2

    def test_clamping(self):
        """Test size clamping to valid range."""
        # Test clamping to maximum
        inner_hw, inner_hh = compute_inner_rectangle_size(1, 1, 3.0, 3.0, 'absolute')
        assert inner_hw == 1.0  # Clamped to outer size
        assert inner_hh == 1.0

        # Test clamping to minimum
        inner_hw, inner_hh = compute_inner_rectangle_size(1, 1, 0, 0, 'absolute')
        assert inner_hw > 0  # Clamped to minimum positive value
        assert inner_hh > 0

    def test_invalid_mode(self):
        """Test invalid sizing mode raises error."""
        with pytest.raises(ValueError, match="inner_size_mode must be"):
            compute_inner_rectangle_size(1, 1, 0.5, 0.5, 'invalid')