"""Tests for triangulation module."""

import numpy as np
import pytest
from stl_grid_generator.triangulation import (
    triangulate_rectangle, triangulate_ring, compute_triangle_normal,
    ensure_consistent_winding
)


class TestTriangulateRectangle:
    """Test rectangle triangulation."""

    def test_basic_triangulation(self):
        """Test basic rectangle triangulation."""
        vertices = np.array([
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1]
        ])

        triangles = triangulate_rectangle(vertices)

        expected = np.array([
            [0, 1, 2],
            [0, 2, 3]
        ])

        assert np.array_equal(triangles, expected)

    def test_invalid_input(self):
        """Test invalid input raises error."""
        with pytest.raises(ValueError, match="Expected 4x2 array"):
            triangulate_rectangle(np.array([[0, 0], [1, 1]]))


class TestTriangulateRing:
    """Test ring triangulation."""

    def test_basic_ring(self):
        """Test basic ring triangulation."""
        outer_vertices = np.array([
            [0, 0],
            [2, 0],
            [2, 2],
            [0, 2]
        ])

        inner_vertices = np.array([
            [0.5, 0.5],
            [1.5, 0.5],
            [1.5, 1.5],
            [0.5, 1.5]
        ])

        combined_vertices, triangles = triangulate_ring(outer_vertices, inner_vertices)

        # Should have 8 vertices (4 outer + 4 inner)
        assert combined_vertices.shape == (8, 2)

        # Should have some triangles (exact number depends on triangulation method)
        assert triangles.shape[1] == 3  # Each triangle has 3 vertices
        assert triangles.shape[0] > 0   # Should have at least some triangles

        # All triangle indices should be valid
        assert np.all(triangles >= 0)
        assert np.all(triangles < 8)

    def test_inner_vertices_reversed(self):
        """Test that inner vertices are reversed (made CW)."""
        outer_vertices = np.array([
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1]
        ])

        inner_vertices = np.array([
            [0.2, 0.2],
            [0.8, 0.2],
            [0.8, 0.8],
            [0.2, 0.8]
        ])

        combined_vertices, _ = triangulate_ring(outer_vertices, inner_vertices)

        # First 4 vertices should be outer (unchanged)
        assert np.array_equal(combined_vertices[:4], outer_vertices)

        # Last 4 vertices should be inner (reversed)
        expected_inner_reversed = inner_vertices[::-1]
        assert np.array_equal(combined_vertices[4:], expected_inner_reversed)

    def test_invalid_input(self):
        """Test invalid input raises error."""
        outer = np.array([[0, 0], [1, 1]])  # Too few vertices
        inner = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])

        with pytest.raises(ValueError, match="Expected 4x2 arrays"):
            triangulate_ring(outer, inner)


class TestComputeTriangleNormal:
    """Test triangle normal computation."""

    def test_ccw_triangle(self):
        """Test CCW triangle produces positive Z normal."""
        v0 = np.array([0, 0, 0])
        v1 = np.array([1, 0, 0])
        v2 = np.array([0, 1, 0])

        normal = compute_triangle_normal(v0, v1, v2)
        expected = np.array([0, 0, 1])

        assert np.allclose(normal, expected)

    def test_cw_triangle(self):
        """Test CW triangle produces negative Z normal."""
        v0 = np.array([0, 0, 0])
        v1 = np.array([0, 1, 0])
        v2 = np.array([1, 0, 0])

        normal = compute_triangle_normal(v0, v1, v2)
        expected = np.array([0, 0, -1])

        assert np.allclose(normal, expected)

    def test_degenerate_triangle(self):
        """Test degenerate triangle returns zero normal."""
        v0 = np.array([0, 0, 0])
        v1 = np.array([1, 1, 1])
        v2 = np.array([2, 2, 2])  # Collinear points

        normal = compute_triangle_normal(v0, v1, v2)

        assert np.allclose(normal, [0, 0, 0])


class TestEnsureConsistentWinding:
    """Test consistent winding order."""

    def test_correct_winding_unchanged(self):
        """Test triangles with correct winding remain unchanged."""
        triangles = np.array([
            [0, 1, 2],
            [0, 2, 3]
        ])

        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0]
        ])

        target_normal = np.array([0, 0, 1])

        result = ensure_consistent_winding(triangles, vertices, target_normal)

        assert np.array_equal(result, triangles)

    def test_incorrect_winding_flipped(self):
        """Test triangles with incorrect winding are flipped."""
        triangles = np.array([
            [0, 2, 1],  # Wrong winding order
        ])

        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0]
        ])

        target_normal = np.array([0, 0, 1])

        result = ensure_consistent_winding(triangles, vertices, target_normal)
        expected = np.array([[0, 1, 2]])  # Corrected winding

        assert np.array_equal(result, expected)