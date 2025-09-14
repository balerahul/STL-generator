"""Core STL grid generation functionality."""

import os
import struct
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union

from .geometry import (
    CoordinateFrame, create_rectangle_vertices, compute_cell_bounds,
    compute_inner_rectangle_size
)
from .triangulation import triangulate_rectangle, triangulate_ring, ensure_consistent_winding


class STLGridGenerator:
    """Generate rectangular STL grids with optional holes."""

    def __init__(self,
                 nx: int, ny: int,
                 W: float, H: float,
                 orientation: str = 'z',
                 normal_sign: int = 1,
                 sx: float = 0.5, sy: float = 0.5,
                 inner_size_mode: str = 'relative',
                 origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 rotate_deg: float = 0.0,
                 border_gap: float = 0.0,
                 out_dir: str = 'output',
                 cell_filename_outer: str = 'cell_{i}_{j}_inner.stl',
                 cell_filename_ring: str = 'cell_{i}_{j}_ring.stl',
                 stl_ascii: bool = False):
        """
        Initialize STL grid generator.

        Args:
            nx, ny: Grid dimensions
            W, H: Total rectangle size
            orientation: 'x', 'y', or 'z' for plane normal
            normal_sign: +1 or -1 for normal direction
            sx, sy: Inner rectangle size parameters
            inner_size_mode: 'relative' or 'absolute'
            origin: World origin (cx, cy, cz)
            rotate_deg: In-plane rotation in degrees
            border_gap: Gap to shrink cell bounds
            out_dir: Output directory
            cell_filename_outer: Filename pattern for inner rectangles
            cell_filename_ring: Filename pattern for rings
            stl_ascii: True for ASCII STL, False for binary
        """
        self.nx = nx
        self.ny = ny
        self.W = W
        self.H = H
        self.sx = sx
        self.sy = sy
        self.inner_size_mode = inner_size_mode
        self.border_gap = border_gap
        self.out_dir = Path(out_dir)
        self.cell_filename_outer = cell_filename_outer
        self.cell_filename_ring = cell_filename_ring
        self.stl_ascii = stl_ascii

        # Validate inputs
        self._validate_inputs()

        # Create coordinate frame
        self.frame = CoordinateFrame(orientation, normal_sign, rotate_deg)
        self.origin = np.array(origin)

        # Create output directory
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _validate_inputs(self):
        """Validate input parameters."""
        if self.nx < 1 or self.ny < 1:
            raise ValueError("nx and ny must be >= 1")
        if self.W <= 0 or self.H <= 0:
            raise ValueError("W and H must be > 0")
        if self.sx <= 0 or self.sy <= 0:
            raise ValueError("sx and sy must be > 0")
        if self.inner_size_mode not in ['relative', 'absolute']:
            raise ValueError("inner_size_mode must be 'relative' or 'absolute'")
        if self.inner_size_mode == 'relative' and (self.sx > 1 or self.sy > 1):
            raise ValueError("For relative mode, sx and sy must be <= 1")
        if self.border_gap < 0:
            raise ValueError("border_gap must be >= 0")

    def generate_all(self) -> int:
        """
        Generate all STL files for the grid.

        Returns:
            Number of files generated
        """
        files_generated = 0

        for i in range(self.nx):
            for j in range(self.ny):
                # Generate inner rectangle
                self._generate_cell_outer(i, j)
                files_generated += 1

                # Generate ring
                self._generate_cell_ring(i, j)
                files_generated += 1

        return files_generated

    def _generate_cell_outer(self, i: int, j: int):
        """Generate inner rectangle STL for cell (i, j)."""
        # Compute cell bounds
        u0, u1, v0, v1 = compute_cell_bounds(i, j, self.nx, self.ny, self.W, self.H, self.border_gap)

        # Outer rectangle parameters
        outer_center = ((u0 + u1) / 2, (v0 + v1) / 2)
        outer_half_width = (u1 - u0) / 2
        outer_half_height = (v1 - v0) / 2

        # Inner rectangle (the hole)
        inner_half_width, inner_half_height = compute_inner_rectangle_size(
            outer_half_width, outer_half_height, self.sx, self.sy, self.inner_size_mode
        )

        # Create inner rectangle vertices
        vertices_2d = create_rectangle_vertices(outer_center, inner_half_width, inner_half_height)

        # Convert to 3D world coordinates
        vertices_3d = np.array([
            self.frame.local_to_world(u, v, self.origin)
            for u, v in vertices_2d
        ])

        # Triangulate
        triangles = triangulate_rectangle(vertices_2d)

        # Ensure consistent winding
        target_normal = self.frame.get_normal()
        triangles = ensure_consistent_winding(triangles, vertices_3d, target_normal)

        # Write STL file
        filename = self.cell_filename_outer.format(i=i, j=j)
        filepath = self.out_dir / filename
        self._write_stl(vertices_3d, triangles, filepath, target_normal)

    def _generate_cell_ring(self, i: int, j: int):
        """Generate ring STL for cell (i, j)."""
        # Compute cell bounds
        u0, u1, v0, v1 = compute_cell_bounds(i, j, self.nx, self.ny, self.W, self.H, self.border_gap)

        # Outer rectangle
        outer_center = ((u0 + u1) / 2, (v0 + v1) / 2)
        outer_half_width = (u1 - u0) / 2
        outer_half_height = (v1 - v0) / 2

        # Inner rectangle
        inner_half_width, inner_half_height = compute_inner_rectangle_size(
            outer_half_width, outer_half_height, self.sx, self.sy, self.inner_size_mode
        )

        # Create vertices
        outer_vertices_2d = create_rectangle_vertices(outer_center, outer_half_width, outer_half_height)
        inner_vertices_2d = create_rectangle_vertices(outer_center, inner_half_width, inner_half_height)

        # Triangulate ring
        combined_vertices_2d, triangles = triangulate_ring(outer_vertices_2d, inner_vertices_2d)

        # Convert to 3D world coordinates
        vertices_3d = np.array([
            self.frame.local_to_world(u, v, self.origin)
            for u, v in combined_vertices_2d
        ])

        # Ensure consistent winding
        target_normal = self.frame.get_normal()
        triangles = ensure_consistent_winding(triangles, vertices_3d, target_normal)

        # Write STL file
        filename = self.cell_filename_ring.format(i=i, j=j)
        filepath = self.out_dir / filename
        self._write_stl(vertices_3d, triangles, filepath, target_normal)

    def _write_stl(self, vertices: np.ndarray, triangles: np.ndarray,
                   filepath: Path, normal: np.ndarray):
        """Write STL file (ASCII or binary)."""
        if self.stl_ascii:
            self._write_stl_ascii(vertices, triangles, filepath, normal)
        else:
            self._write_stl_binary(vertices, triangles, filepath, normal)

    def _write_stl_ascii(self, vertices: np.ndarray, triangles: np.ndarray,
                        filepath: Path, normal: np.ndarray):
        """Write ASCII STL file."""
        with open(filepath, 'w') as f:
            f.write(f"solid {filepath.stem}\n")

            for tri in triangles:
                v0, v1, v2 = vertices[tri]

                # Compute triangle normal
                edge1 = v1 - v0
                edge2 = v2 - v0
                tri_normal = np.cross(edge1, edge2)
                norm = np.linalg.norm(tri_normal)
                if norm > 1e-10:
                    tri_normal = tri_normal / norm
                else:
                    tri_normal = normal

                f.write(f"  facet normal {tri_normal[0]:.6e} {tri_normal[1]:.6e} {tri_normal[2]:.6e}\n")
                f.write("    outer loop\n")
                f.write(f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}\n")
                f.write(f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}\n")
                f.write(f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}\n")
                f.write("    endloop\n")
                f.write("  endfacet\n")

            f.write(f"endsolid {filepath.stem}\n")

    def _write_stl_binary(self, vertices: np.ndarray, triangles: np.ndarray,
                         filepath: Path, normal: np.ndarray):
        """Write binary STL file."""
        with open(filepath, 'wb') as f:
            # 80-byte header
            header = f"STL generated by STLGridGenerator {filepath.stem}".ljust(80)[:80]
            f.write(header.encode('ascii'))

            # Number of triangles (4 bytes, little-endian)
            num_triangles = len(triangles)
            f.write(struct.pack('<I', num_triangles))

            # Triangle data
            for tri in triangles:
                v0, v1, v2 = vertices[tri]

                # Compute triangle normal
                edge1 = v1 - v0
                edge2 = v2 - v0
                tri_normal = np.cross(edge1, edge2)
                norm = np.linalg.norm(tri_normal)
                if norm > 1e-10:
                    tri_normal = tri_normal / norm
                else:
                    tri_normal = normal

                # Write normal (3 floats)
                f.write(struct.pack('<fff', tri_normal[0], tri_normal[1], tri_normal[2]))

                # Write vertices (9 floats)
                f.write(struct.pack('<fff', v0[0], v0[1], v0[2]))
                f.write(struct.pack('<fff', v1[0], v1[1], v1[2]))
                f.write(struct.pack('<fff', v2[0], v2[1], v2[2]))

                # Attribute byte count (2 bytes, unused)
                f.write(struct.pack('<H', 0))

    def get_cell_info(self, i: int, j: int) -> dict:
        """
        Get information about a specific cell.

        Args:
            i, j: Cell indices

        Returns:
            Dictionary with cell information
        """
        u0, u1, v0, v1 = compute_cell_bounds(i, j, self.nx, self.ny, self.W, self.H, self.border_gap)

        outer_center = ((u0 + u1) / 2, (v0 + v1) / 2)
        outer_half_width = (u1 - u0) / 2
        outer_half_height = (v1 - v0) / 2

        inner_half_width, inner_half_height = compute_inner_rectangle_size(
            outer_half_width, outer_half_height, self.sx, self.sy, self.inner_size_mode
        )

        # Convert to world coordinates
        world_center = self.frame.local_to_world(outer_center[0], outer_center[1], self.origin)

        return {
            'cell_index': (i, j),
            'local_bounds': (u0, u1, v0, v1),
            'local_center': outer_center,
            'world_center': world_center.tolist(),
            'outer_size': (2 * outer_half_width, 2 * outer_half_height),
            'inner_size': (2 * inner_half_width, 2 * inner_half_height),
            'orientation': self.frame.orientation,
            'normal': self.frame.get_normal().tolist(),
        }