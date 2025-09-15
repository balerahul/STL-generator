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
    Creates 4 rectangular strips around the hole.
    """
    triangles = []

    # Outer: 0=BL, 1=BR, 2=TR, 3=TL (CCW)
    # Inner: 4=TL, 5=TR, 6=BR, 7=BL (CW - reversed)

    # Create 4 strips: bottom, right, top, left

    # Bottom strip: outer[0,1] to inner[7,6]
    triangles.append([0, 1, 7])  # outer BL -> outer BR -> inner BL
    triangles.append([1, 6, 7])  # outer BR -> inner BR -> inner BL

    # Right strip: outer[1,2] to inner[6,5]
    triangles.append([1, 2, 6])  # outer BR -> outer TR -> inner BR
    triangles.append([2, 5, 6])  # outer TR -> inner TR -> inner BR

    # Top strip: outer[2,3] to inner[5,4]
    triangles.append([2, 3, 5])  # outer TR -> outer TL -> inner TR
    triangles.append([3, 4, 5])  # outer TL -> inner TL -> inner TR

    # Left strip: outer[3,0] to inner[4,7]
    triangles.append([3, 0, 4])  # outer TL -> outer BL -> inner TL
    triangles.append([0, 7, 4])  # outer BL -> inner BL -> inner TL

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