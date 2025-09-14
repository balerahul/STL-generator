"""Triangulation utilities for rectangles and rings."""

import numpy as np
from typing import List, Tuple, Optional

try:
    import mapbox_earcut
    EARCUT_AVAILABLE = True
except ImportError:
    EARCUT_AVAILABLE = False

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False


def triangulate_rectangle(vertices: np.ndarray) -> np.ndarray:
    """
    Triangulate a simple rectangle into two triangles.

    Args:
        vertices: 4x2 array of rectangle vertices in CCW order

    Returns:
        2x3 array of triangle vertex indices
    """
    if vertices.shape != (4, 2):
        raise ValueError("Expected 4x2 array of vertices")

    # Two triangles: (0,1,2) and (0,2,3)
    triangles = np.array([
        [0, 1, 2],
        [0, 2, 3]
    ])

    return triangles


def triangulate_ring(outer_vertices: np.ndarray, inner_vertices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Triangulate a ring (rectangle with rectangular hole).

    Args:
        outer_vertices: 4x2 array of outer rectangle vertices (CCW)
        inner_vertices: 4x2 array of inner rectangle vertices (CCW, will be reversed to CW)

    Returns:
        Tuple of (combined_vertices, triangles)
        - combined_vertices: Nx2 array of all vertices
        - triangles: Mx3 array of triangle vertex indices
    """
    if outer_vertices.shape != (4, 2) or inner_vertices.shape != (4, 2):
        raise ValueError("Expected 4x2 arrays for both outer and inner vertices")

    # Reverse inner vertices to make them CW (for hole)
    inner_vertices_cw = inner_vertices[::-1]

    # Combine vertices: outer first, then inner
    combined_vertices = np.vstack([outer_vertices, inner_vertices_cw])

    # Try mapbox_earcut first
    if EARCUT_AVAILABLE:
        try:
            triangles = _triangulate_with_earcut(combined_vertices, hole_indices=[4])
            return combined_vertices, triangles
        except Exception:
            pass  # Fall back to other methods

    # Try trimesh as fallback
    if TRIMESH_AVAILABLE:
        try:
            triangles = _triangulate_with_trimesh(outer_vertices, inner_vertices_cw)
            return combined_vertices, triangles
        except Exception:
            pass

    # Manual triangulation as last resort
    triangles = _triangulate_ring_manual(outer_vertices, inner_vertices_cw)
    return combined_vertices, triangles


def _triangulate_with_earcut(vertices: np.ndarray, hole_indices: List[int]) -> np.ndarray:
    """Triangulate using mapbox_earcut."""
    # Flatten vertices for earcut
    coords = vertices.flatten()

    # Run triangulation
    triangle_indices = mapbox_earcut.triangulate_float64(coords, hole_indices)

    # Reshape to triangles
    triangles = np.array(triangle_indices).reshape(-1, 3)
    return triangles


def _triangulate_with_trimesh(outer_vertices: np.ndarray, inner_vertices_cw: np.ndarray) -> np.ndarray:
    """Triangulate using trimesh/Shapely."""
    from shapely.geometry import Polygon

    # Create polygon with hole
    outer_ring = outer_vertices.tolist()
    inner_ring = inner_vertices_cw.tolist()

    polygon = Polygon(outer_ring, [inner_ring])

    # Triangulate
    mesh = trimesh.Trimesh(**trimesh.triangulate_polygon(polygon))

    return mesh.faces


def _triangulate_ring_manual(outer_vertices: np.ndarray, inner_vertices_cw: np.ndarray) -> np.ndarray:
    """
    Manual triangulation for a rectangle with rectangular hole.
    Creates triangles that form a frame between outer and inner boundaries.
    """
    triangles = []

    # For each side of the rectangle, create two triangles connecting outer to inner
    # This creates a "frame" without filling the hole

    for i in range(4):
        next_i = (i + 1) % 4

        # Outer vertices: 0,1,2,3 (CCW)
        # Inner vertices: 4,5,6,7 (CW, so reversed order)

        # For each edge, create two triangles that form the frame segment
        # Triangle 1: outer[i] -> inner[i] -> outer[next_i]
        triangles.append([i, 4 + i, next_i])

        # Triangle 2: outer[next_i] -> inner[i] -> inner[next_i]
        triangles.append([next_i, 4 + i, 4 + next_i])

    return np.array(triangles)


def compute_triangle_normal(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """
    Compute triangle normal using cross product.

    Args:
        v0, v1, v2: Triangle vertices (3D points)

    Returns:
        Normalized normal vector
    """
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)

    # Normalize
    norm = np.linalg.norm(normal)
    if norm > 1e-10:
        normal = normal / norm
    else:
        # Degenerate triangle, return zero normal
        normal = np.zeros(3)

    return normal


def ensure_consistent_winding(triangles: np.ndarray, vertices: np.ndarray,
                            target_normal: np.ndarray) -> np.ndarray:
    """
    Ensure triangles have consistent winding order for given target normal.

    Args:
        triangles: Mx3 array of triangle vertex indices
        vertices: Nx3 array of vertex positions
        target_normal: Target normal direction

    Returns:
        Triangles with corrected winding order
    """
    corrected_triangles = triangles.copy()

    for i, tri in enumerate(triangles):
        v0, v1, v2 = vertices[tri]
        tri_normal = compute_triangle_normal(v0, v1, v2)

        # Check if normal points in wrong direction
        if np.dot(tri_normal, target_normal) < 0:
            # Flip winding order
            corrected_triangles[i] = [tri[0], tri[2], tri[1]]

    return corrected_triangles