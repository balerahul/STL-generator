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

### YAML Configuration (Recommended)

The easiest way to use the STL Grid Generator is with YAML configuration files:

```bash
# Generate example config file
stl-grid-gen --generate-config my_config.yaml

# Use the config file
stl-grid-gen --config my_config.yaml

# Override specific settings from command line
stl-grid-gen --config my_config.yaml --out-dir custom_output --stl-ascii
```

### Command Line Usage

For simple cases, you can still use command-line arguments:

```bash
# Generate a 3×2 grid with Z-normal orientation
stl-grid-gen --nx 3 --ny 2 --W 10 --H 8 --sx 0.7 --sy 0.7

# Generate X-oriented grid with absolute hole sizes
stl-grid-gen --nx 2 --ny 2 --W 5 --H 5 --orientation x \
             --sx 1.0 --sy 1.0 --inner-size-mode absolute
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

## Configuration

### YAML Configuration Structure

YAML files provide a clean, organized way to specify all parameters:

```yaml
grid:
  nx: 3              # Grid dimensions
  ny: 2
  W: 15.0           # Total rectangle size
  H: 10.0

orientation:
  orientation: z     # Plane normal: x, y, or z
  normal_sign: 1     # Direction: 1 or -1
  rotate_deg: 0.0    # In-plane rotation (degrees)

inner_rectangle:
  sx: 0.7           # Inner size parameters
  sy: 0.7
  inner_size_mode: relative  # 'relative' or 'absolute'

placement:
  origin: [0.0, 0.0, 0.0]   # World coordinates of rectangle center
  border_gap: 0.0           # Cell shrinkage amount

output:
  out_dir: output
  cell_filename_outer: cell_{i}_{j}_outer.stl
  cell_filename_ring: cell_{i}_{j}_ring.stl
  stl_ascii: false          # true for ASCII, false for binary

options:
  verbose: false
  info_only: false
```

### Command Line Parameters

When using CLI arguments (all parameters have YAML equivalents):

#### Required Parameters
- `--nx`, `--ny`: Grid dimensions (integers ≥ 1)
- `--W`, `--H`: Total rectangle size in local units (floats > 0)

#### Configuration Options
- `--config`, `-c`: YAML configuration file path
- `--generate-config PATH`: Generate example YAML config and exit

#### Orientation & Rotation
- `--orientation {x,y,z}`: Plane normal direction (default: `z`)
- `--normal-sign {1,-1}`: Normal vector sign (default: `1`)
- `--rotate-deg FLOAT`: In-plane rotation in degrees (default: `0`)

#### Inner Rectangle (Hole) Parameters
- `--sx`, `--sy`: Inner rectangle size parameters (default: `0.5`)
- `--inner-size-mode {relative,absolute}`: Size interpretation mode (default: `relative`)
  - `relative`: `sx`, `sy` are fractions of cell size (0 < value ≤ 1)
  - `absolute`: `sx`, `sy` are lengths in same units as `W`, `H`

#### Placement & Modification
- `--origin X Y Z`: World coordinates of the entire rectangle's center point (default: `0 0 0`)
- `--border-gap FLOAT`: Shrink each cell by this amount (default: `0`)

#### Output Options
- `--out-dir PATH`: Output directory (default: `output`)
- `--outer-pattern STR`: Filename pattern for outer rectangles
- `--ring-pattern STR`: Filename pattern for rings
- `--stl-ascii`: Generate ASCII STL files instead of binary

## Coordinate System

### Local Coordinate System

The generator uses a local `(u, v)` coordinate system within the plane:

- **Z-orientation** (`orientation='z'`): `u` = X-axis, `v` = Y-axis, normal = ±Z
- **X-orientation** (`orientation='x'`): `u` = Y-axis, `v` = Z-axis, normal = ±X
- **Y-orientation** (`orientation='y'`): `u` = X-axis, `v` = Z-axis, normal = ±Y

### Origin and Placement

The `origin` parameter specifies where the **center of the entire rectangle** is placed in world coordinates.

**Example**: For a 3×2 grid with `W=6, H=4`:
```
Local coordinates (u, v):
   u = -3    0    +3
v=+2  ┌─────┼─────┐
      │     │     │
v= 0  ├─────●─────┤  ← CENTER (0,0) in local coords
      │     │     │
v=-2  └─────┼─────┘

World transformation: P = origin + u*û + v*ṽ
```

- Rectangle spans `u ∈ [-3, +3]` and `v ∈ [-2, +2]` in local coordinates
- Center point `(u=0, v=0)` maps to `origin` in world coordinates
- If `origin = [5, 10, 2]`, the center is placed at world coordinates `(5, 10, 2)`
- Individual cells are positioned relative to this center point

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

The `examples/` directory contains ready-to-use YAML configuration files:

### Example 1: Basic Grid

```bash
# Generate example config
stl-grid-gen --generate-config basic.yaml

# Or use the provided example
stl-grid-gen --config examples/basic_grid.yaml
```

**Configuration** (`examples/basic_grid.yaml`):
```yaml
grid:
  nx: 3
  ny: 2
  W: 15.0
  H: 10.0

inner_rectangle:
  sx: 0.7
  sy: 0.7
  inner_size_mode: relative
```

### Example 2: Laser Cutting Template

```bash
stl-grid-gen --config examples/laser_cutting.yaml
```

Creates a 4×3 grid of 20×15mm rectangles with 14×10mm centered holes in ASCII format.

### Example 3: 3D Printing Supports

```bash
stl-grid-gen --config examples/rotated_supports.yaml
```

Generates a rotated 6×4 support grid with large holes for material savings.

### Example 4: Multi-Orientation

```bash
stl-grid-gen --config examples/multi_orientation.yaml
```

Demonstrates X-orientation (YZ plane) with negative normal and rotation.

### Command Line Examples

For quick tasks, you can still use CLI arguments:

```bash
# Generate a 4×3 grid of 20×15mm rectangles with 14×10mm centered holes
stl-grid-gen --nx 4 --ny 3 --W 80 --H 45 \
             --sx 14 --sy 10 --inner-size-mode absolute \
             --stl-ascii --out-dir laser_templates

# Create rotated support grid with relative hole sizes
stl-grid-gen --nx 6 --ny 4 --W 60 --H 40 \
             --rotate-deg 30 --sx 0.8 --sy 0.8 \
             --border-gap 0.5 --out-dir supports

# Mixed usage: config with CLI overrides
stl-grid-gen --config examples/basic_grid.yaml \
             --out-dir custom_output --stl-ascii
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