"""Tests for core STL generation functionality."""

import tempfile
import shutil
import numpy as np
import pytest
from pathlib import Path

from stl_grid_generator.core import STLGridGenerator


class TestSTLGridGenerator:
    """Test STL grid generator."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_basic_initialization(self):
        """Test basic generator initialization."""
        generator = STLGridGenerator(
            nx=2, ny=3, W=4.0, H=6.0,
            out_dir=str(self.temp_path)
        )

        assert generator.nx == 2
        assert generator.ny == 3
        assert generator.W == 4.0
        assert generator.H == 6.0
        assert generator.frame.orientation == 'z'

    def test_invalid_inputs(self):
        """Test validation of invalid inputs."""
        # Negative dimensions
        with pytest.raises(ValueError, match="nx and ny must be >= 1"):
            STLGridGenerator(nx=0, ny=1, W=1, H=1)

        # Zero size
        with pytest.raises(ValueError, match="W and H must be > 0"):
            STLGridGenerator(nx=1, ny=1, W=0, H=1)

        # Invalid inner size for relative mode
        with pytest.raises(ValueError, match="sx and sy must be <= 1"):
            STLGridGenerator(nx=1, ny=1, W=1, H=1, sx=1.5, inner_size_mode='relative')

    def test_file_generation(self):
        """Test STL file generation."""
        generator = STLGridGenerator(
            nx=2, ny=2, W=2.0, H=2.0,
            out_dir=str(self.temp_path),
            stl_ascii=True  # Use ASCII for easier testing
        )

        files_generated = generator.generate_all()

        # Should generate 2 files per cell (outer + ring)
        assert files_generated == 8

        # Check that files exist
        expected_files = [
            'cell_0_0_outer.stl', 'cell_0_0_ring.stl',
            'cell_0_1_outer.stl', 'cell_0_1_ring.stl',
            'cell_1_0_outer.stl', 'cell_1_0_ring.stl',
            'cell_1_1_outer.stl', 'cell_1_1_ring.stl',
        ]

        for filename in expected_files:
            filepath = self.temp_path / filename
            assert filepath.exists()
            assert filepath.stat().st_size > 0

    def test_ascii_stl_format(self):
        """Test ASCII STL file format."""
        generator = STLGridGenerator(
            nx=1, ny=1, W=1.0, H=1.0,
            out_dir=str(self.temp_path),
            stl_ascii=True
        )

        generator.generate_all()

        # Check outer file content
        outer_file = self.temp_path / 'cell_0_0_outer.stl'
        content = outer_file.read_text()

        assert content.startswith('solid')
        assert 'facet normal' in content
        assert 'vertex' in content
        assert content.endswith('endsolid cell_0_0_outer\n')

    def test_binary_stl_format(self):
        """Test binary STL file format."""
        generator = STLGridGenerator(
            nx=1, ny=1, W=1.0, H=1.0,
            out_dir=str(self.temp_path),
            stl_ascii=False
        )

        generator.generate_all()

        # Check outer file content
        outer_file = self.temp_path / 'cell_0_0_outer.stl'

        with open(outer_file, 'rb') as f:
            # Read 80-byte header
            header = f.read(80)
            assert len(header) == 80

            # Read triangle count
            triangle_count_bytes = f.read(4)
            assert len(triangle_count_bytes) == 4

            # Should have remaining data for triangles
            remaining = f.read()
            triangle_count = int.from_bytes(triangle_count_bytes, 'little')
            expected_size = triangle_count * 50  # 50 bytes per triangle
            assert len(remaining) == expected_size

    def test_different_orientations(self):
        """Test different plane orientations."""
        for orientation in ['x', 'y', 'z']:
            generator = STLGridGenerator(
                nx=1, ny=1, W=1.0, H=1.0,
                orientation=orientation,
                out_dir=str(self.temp_path / orientation)
            )

            info = generator.get_cell_info(0, 0)
            assert info['orientation'] == orientation

            # Check normal vector
            if orientation == 'x':
                assert np.allclose(info['normal'], [1, 0, 0])
            elif orientation == 'y':
                assert np.allclose(info['normal'], [0, 1, 0])
            else:  # z
                assert np.allclose(info['normal'], [0, 0, 1])

    def test_custom_filenames(self):
        """Test custom filename patterns."""
        generator = STLGridGenerator(
            nx=1, ny=2, W=1.0, H=2.0,
            out_dir=str(self.temp_path),
            cell_filename_outer='part_{i}_{j}_base.stl',
            cell_filename_ring='part_{i}_{j}_hole.stl'
        )

        generator.generate_all()

        # Check custom filenames exist
        expected_files = [
            'part_0_0_base.stl', 'part_0_0_hole.stl',
            'part_0_1_base.stl', 'part_0_1_hole.stl',
        ]

        for filename in expected_files:
            filepath = self.temp_path / filename
            assert filepath.exists()

    def test_get_cell_info(self):
        """Test cell information retrieval."""
        generator = STLGridGenerator(
            nx=2, ny=2, W=4.0, H=6.0,
            origin=(1, 2, 3),
            sx=0.6, sy=0.8
        )

        info = generator.get_cell_info(0, 0)

        assert info['cell_index'] == (0, 0)
        assert info['local_bounds'] == (-2.0, 0.0, -3.0, 0.0)
        assert info['local_center'] == (-1.0, -1.5)
        assert np.allclose(info['world_center'], [0, 0.5, 3])  # origin + local center
        assert info['outer_size'] == (2.0, 3.0)  # Cell size
        assert info['inner_size'] == (1.2, 2.4)  # 0.6 * 2.0, 0.8 * 3.0

    def test_border_gap(self):
        """Test border gap functionality."""
        generator = STLGridGenerator(
            nx=1, ny=1, W=2.0, H=2.0,
            border_gap=0.2
        )

        info = generator.get_cell_info(0, 0)

        # With border gap, effective cell size is reduced
        assert info['local_bounds'] == (-0.8, 0.8, -0.8, 0.8)  # ±1 ± 0.2
        assert info['outer_size'] == (1.6, 1.6)  # Reduced by 2*border_gap

    def test_absolute_inner_size_mode(self):
        """Test absolute inner size mode."""
        generator = STLGridGenerator(
            nx=1, ny=1, W=4.0, H=6.0,
            sx=1.0, sy=2.0,
            inner_size_mode='absolute'
        )

        info = generator.get_cell_info(0, 0)

        assert info['inner_size'] == (1.0, 2.0)  # Absolute sizes