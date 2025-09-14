# STL Grid Generator

A Python package for generating rectangular STL grids with optional centered rectangular holes. Creates zero-thickness surface meshes suitable for CAD/CAM workflows, laser cutting templates, and 3D modeling applications.

## Features

- **Flexible Grid Generation**: Create `nx × ny` grids of rectangular cells
- **Multiple Orientations**: Generate grids aligned to X, Y, or Z planes with configurable normal directions
- **Dual Output**: Each cell produces two STL files:
  - **Outer**: Complete rectangular boundary (2 triangles)
  - **Ring**: Rectangular boundary with centered rectangular hole (triangulated polygon)
- **Size Modes**:
  - **Relative**: Inner hole size as fraction of cell size (0 < size ≤ 1)
  - **Absolute**: Inner hole size in absolute units
- **Customizable**:
  - In-plane rotation around normal axis
  - Arbitrary world origin placement
  - Optional border gaps for cell shrinking
  - Custom filename patterns
  - ASCII or binary STL output

## Installation

```bash
# Basic installation
pip install -e .

# With optional triangulation backends for better performance
pip install -e ".[full]"

# Development installation
pip install -e ".[dev]"
```

## Dependencies

- **Required**: `numpy >= 1.18.0`
- **Optional**:
  - `mapbox_earcut >= 1.0.0` (recommended for faster triangulation)
  - `trimesh >= 3.0.0` + `shapely >= 1.7.0` (alternative triangulation backend)

## Quick Start

### Command Line Usage

```bash
# Generate a 3×2 grid with Z-normal orientation
stl-grid-gen --nx 3 --ny 2 --W 10 --H 8 --sx 0.7 --sy 0.7

# Generate X-oriented grid with absolute hole sizes
stl-grid-gen --nx 2 --ny 2 --W 5 --H 5 --orientation x \
             --sx 1.0 --sy 1.0 --inner-size-mode absolute

# Generate with 45° rotation and custom origin
stl-grid-gen --nx 4 --ny 3 --W 12 --H 9 --rotate-deg 45 --origin 5 3 2

# Generate ASCII STL files with custom output directory
stl-grid-gen --nx 2 --ny 2 --W 4 --H 4 --stl-ascii --out-dir my_parts
```

### Python API Usage

```python
from stl_grid_generator import STLGridGenerator

# Create generator
generator = STLGridGenerator(
    nx=3, ny=2,           # 3×2 grid
    W=10.0, H=8.0,        # Total size: 10×8 units
    orientation='z',       # Z-normal plane
    sx=0.7, sy=0.7,       # Inner holes are 70% of cell size
    inner_size_mode='relative',
    origin=(0, 0, 0),     # Centered at origin
    out_dir='output'
)

# Generate all STL files
num_files = generator.generate_all()
print(f"Generated {num_files} STL files")

# Get information about specific cell
info = generator.get_cell_info(0, 0)
print(f"Cell (0,0) center: {info['world_center']}")
print(f"Outer size: {info['outer_size']}")
print(f"Inner size: {info['inner_size']}")
```

## Parameters

### Required Parameters

- `--nx`, `--ny`: Grid dimensions (integers ≥ 1)
- `--W`, `--H`: Total rectangle size in local units (floats > 0)

### Orientation & Rotation

- `--orientation {x,y,z}`: Plane normal direction (default: `z`)
- `--normal-sign {1,-1}`: Normal vector sign (default: `1`)
- `--rotate-deg FLOAT`: In-plane rotation in degrees (default: `0`)

### Inner Rectangle (Hole) Parameters

- `--sx`, `--sy`: Inner rectangle size parameters (default: `0.5`)
- `--inner-size-mode {relative,absolute}`: Size interpretation mode (default: `relative`)
  - `relative`: `sx`, `sy` are fractions of cell size (0 < value ≤ 1)
  - `absolute`: `sx`, `sy` are lengths in same units as `W`, `H`

### Placement & Modification

- `--origin X Y Z`: World coordinates of rectangle center (default: `0 0 0`)
- `--border-gap FLOAT`: Shrink each cell by this amount (default: `0`)

### Output Options

- `--out-dir PATH`: Output directory (default: `output`)
- `--outer-pattern STR`: Filename pattern for outer rectangles (default: `cell_{i}_{j}_outer.stl`)
- `--ring-pattern STR`: Filename pattern for rings (default: `cell_{i}_{j}_ring.stl`)
- `--stl-ascii`: Generate ASCII STL files instead of binary

## Coordinate System

The generator uses a local `(u, v)` coordinate system within the plane:

- **Z-orientation** (`orientation='z'`): `u` = X-axis, `v` = Y-axis, normal = ±Z
- **X-orientation** (`orientation='x'`): `u` = Y-axis, `v` = Z-axis, normal = ±X
- **Y-orientation** (`orientation='y'`): `u` = X-axis, `v` = Z-axis, normal = ±Y

World coordinates are computed as: `P = origin + u*û + v*ṽ`

## Output Files

For an `nx × ny` grid, the generator creates exactly `2 × nx × ny` STL files:

```
output/
├── cell_0_0_outer.stl    # Full rectangle for cell (0,0)
├── cell_0_0_ring.stl     # Rectangle with hole for cell (0,0)
├── cell_0_1_outer.stl
├── cell_0_1_ring.stl
├── ...
└── cell_{nx-1}_{ny-1}_ring.stl
```

### File Naming

Cell indices `(i, j)` range from:
- `i`: 0 to `nx-1` (along u-axis)
- `j`: 0 to `ny-1` (along v-axis)

Custom filename patterns support `{i}` and `{j}` placeholders.

## Examples

### Example 1: Laser Cutting Template

Generate a 4×3 grid of 20×15mm rectangles with 14×10mm centered holes:

```bash
stl-grid-gen --nx 4 --ny 3 --W 80 --H 45 \
             --sx 14 --sy 10 --inner-size-mode absolute \
             --stl-ascii --out-dir laser_templates
```

### Example 2: 3D Printing Supports

Create rotated support grid with relative hole sizes:

```bash
stl-grid-gen --nx 6 --ny 4 --W 60 --H 40 \
             --rotate-deg 30 --sx 0.8 --sy 0.8 \
             --border-gap 0.5 --out-dir supports
```

### Example 3: Multiple Orientations

Generate grids for all three orientations:

```bash
for orient in x y z; do
  stl-grid-gen --nx 3 --ny 3 --W 30 --H 30 \
               --orientation $orient \
               --out-dir "output_${orient}"
done
```

## Testing

Run the test suite:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=stl_grid_generator --cov-report=html
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Technical Notes

- **Zero-thickness meshes**: Generated STL files contain surface meshes without volume (non-manifold). This is intentional for template and outline applications.
- **Triangulation**: Uses `mapbox_earcut` for robust polygon-with-hole triangulation, with `trimesh` as fallback.
- **Winding order**: Ensures consistent triangle winding for proper normal orientation.
- **Precision**: Uses double-precision floating-point throughout for geometric accuracy.