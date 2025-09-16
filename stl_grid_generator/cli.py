"""Command-line interface for STL Grid Generator."""

import argparse
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

from .core import STLGridGenerator


def create_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Generate rectangular STL grids with optional holes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Getting Started:
  # Generate an example config file
  stl-grid-gen --generate-config my_config.yaml

  # Use the config file (recommended)
  stl-grid-gen --config my_config.yaml

  # Quick CLI usage
  stl-grid-gen --nx 3 --ny 2 --W 10 --H 8 --sx 0.7 --sy 0.7

Examples:
  # Basic 3x2 grid with relative holes
  stl-grid-gen --nx 3 --ny 2 --W 15 --H 10 --sx 0.7 --sy 0.7

  # X-oriented grid with absolute hole sizes
  stl-grid-gen --nx 2 --ny 2 --W 5 --H 5 --orientation x --sx 1.0 --sy 1.0 --inner-size-mode absolute

  # Config file with CLI overrides
  stl-grid-gen --config examples/basic_grid.yaml --out-dir custom_output --stl-ascii

  # Use pre-made examples
  stl-grid-gen --config examples/laser_cutting.yaml
  stl-grid-gen --config examples/rotated_supports.yaml

For more information, see README.md and the examples/ directory.
        """
    )

    # Primary input method
    parser.add_argument('--config', '-c', type=str,
                       help='YAML configuration file path (recommended)')

    # Generate example config
    parser.add_argument('--generate-config', type=str, metavar='PATH',
                       help='Generate example YAML config file and exit')

    # Required parameters (when not using config file)
    parser.add_argument('--nx', type=int,
                       help='Number of cells along u-axis (>= 1)')
    parser.add_argument('--ny', type=int,
                       help='Number of cells along v-axis (>= 1)')
    parser.add_argument('--W', type=float,
                       help='Total width along u-axis (> 0)')
    parser.add_argument('--H', type=float,
                       help='Total height along v-axis (> 0)')

    # Orientation and rotation
    parser.add_argument('--orientation', choices=['x', 'y', 'z'], default='z',
                       help='Plane normal orientation (default: z)')
    parser.add_argument('--normal-sign', type=int, choices=[1, -1], default=1,
                       help='Normal direction sign (default: 1)')
    parser.add_argument('--rotate-deg', type=float, default=0.0,
                       help='In-plane rotation in degrees (default: 0)')

    # Inner rectangle (hole) parameters
    parser.add_argument('--sx', type=float, default=0.5,
                       help='Inner rectangle u-size parameter (default: 0.5)')
    parser.add_argument('--sy', type=float, default=0.5,
                       help='Inner rectangle v-size parameter (default: 0.5)')
    parser.add_argument('--inner-size-mode', choices=['relative', 'absolute'], default='relative',
                       help='Inner size mode: relative (fraction) or absolute (units) (default: relative)')

    # Placement
    parser.add_argument('--origin', type=float, nargs=3, default=[0.0, 0.0, 0.0],
                       metavar=('X', 'Y', 'Z'),
                       help='World origin coordinates (default: 0 0 0)')

    # Cell modification
    parser.add_argument('--border-gap', type=float, default=0.0,
                       help='Gap to shrink cell bounds (default: 0)')

    # Output options
    parser.add_argument('--out-dir', type=str, default='output',
                       help='Output directory (default: output)')
    parser.add_argument('--inner-pattern', type=str, default='cell_inner_x{i}_y{j}.stl',
                       help='Filename pattern for inner rectangles (default: cell_inner_x{i}_y{j}.stl)')
    parser.add_argument('--ring-pattern', type=str, default='cell_ring_x{i}_y{j}.stl',
                       help='Filename pattern for rings (default: cell_ring_x{i}_y{j}.stl)')
    parser.add_argument('--stl-ascii', action='store_true',
                       help='Generate ASCII STL files (default: binary)')

    # Information options
    parser.add_argument('--info-only', action='store_true',
                       help='Print configuration info without generating files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    return parser


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config or {}
    except FileNotFoundError:
        raise ValueError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")


def generate_example_config(output_path: str):
    """Generate an example YAML configuration file."""
    example_config = {
        'grid': {
            'nx': 3,
            'ny': 2,
            'W': 10.0,
            'H': 8.0,
        },
        'orientation': {
            'orientation': 'z',
            'normal_sign': 1,
            'rotate_deg': 0.0,
        },
        'inner_rectangle': {
            'sx': 0.7,
            'sy': 0.7,
            'inner_size_mode': 'relative',
        },
        'placement': {
            'origin': [0.0, 0.0, 0.0],
            'border_gap': 0.0,
        },
        'output': {
            'out_dir': 'output',
            'cell_filename_inner': 'cell_inner_x{i}_y{j}.stl',
            'cell_filename_ring': 'cell_ring_x{i}_y{j}.stl',
            'stl_ascii': False,
        },
        'options': {
            'verbose': False,
            'info_only': False,
        }
    }

    with open(output_path, 'w') as f:
        yaml.dump(example_config, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f"Example configuration written to: {output_path}")
    print("\nExample usage:")
    print(f"  stl-grid-gen --config {output_path}")


def merge_config_and_args(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """Merge YAML config with command line arguments (CLI args take precedence)."""
    # Start with flattened config values
    merged = {}

    # Extract values from nested config structure
    if 'grid' in config:
        merged.update({k: v for k, v in config['grid'].items()})
    if 'orientation' in config:
        merged.update({k: v for k, v in config['orientation'].items()})
    if 'inner_rectangle' in config:
        merged.update({k: v for k, v in config['inner_rectangle'].items()})
    if 'placement' in config:
        merged.update({k: v for k, v in config['placement'].items()})
    if 'output' in config:
        merged.update({k: v for k, v in config['output'].items()})
    if 'options' in config:
        merged.update({k: v for k, v in config['options'].items()})

    # Override with command line arguments (only non-None values)
    arg_dict = vars(args)
    for key, value in arg_dict.items():
        if value is not None:
            # Convert argument names to config names
            if key == 'inner_pattern':
                merged['cell_filename_inner'] = value
            elif key == 'ring_pattern':
                merged['cell_filename_ring'] = value
            elif key == 'stl_ascii':
                merged['stl_ascii'] = value
            else:
                merged[key] = value

    return merged


def validate_config(config: Dict[str, Any]) -> list:
    """Validate merged configuration."""
    errors = []

    # Check required parameters
    required_params = ['nx', 'ny', 'W', 'H']
    for param in required_params:
        if param not in config:
            errors.append(f"Missing required parameter: {param}")

    if errors:
        return errors

    # Validate values
    if config.get('nx', 1) < 1:
        errors.append("nx must be >= 1")
    if config.get('ny', 1) < 1:
        errors.append("ny must be >= 1")
    if config.get('W', 1) <= 0:
        errors.append("W must be > 0")
    if config.get('H', 1) <= 0:
        errors.append("H must be > 0")
    if config.get('sx', 1) <= 0:
        errors.append("sx must be > 0")
    if config.get('sy', 1) <= 0:
        errors.append("sy must be > 0")
    if config.get('border_gap', 0) < 0:
        errors.append("border_gap must be >= 0")

    inner_size_mode = config.get('inner_size_mode', 'relative')
    if inner_size_mode == 'relative':
        if config.get('sx', 0.5) > 1:
            errors.append("For relative mode, sx must be <= 1")
        if config.get('sy', 0.5) > 1:
            errors.append("For relative mode, sy must be <= 1")

    # Check filename patterns
    inner_pattern = config.get('cell_filename_inner', 'cell_inner_x{i}_y{j}.stl')
    ring_pattern = config.get('cell_filename_ring', 'cell_ring_x{i}_y{j}.stl')

    if '{i}' not in inner_pattern or '{j}' not in inner_pattern:
        errors.append("cell_filename_inner must contain {i} and {j} placeholders")
    if '{i}' not in ring_pattern or '{j}' not in ring_pattern:
        errors.append("cell_filename_ring must contain {i} and {j} placeholders")

    return errors


def validate_args(args):
    """Validate command-line arguments."""
    errors = []

    # Check required parameters are provided
    required_params = [('nx', '--nx'), ('ny', '--ny'), ('W', '--W'), ('H', '--H')]
    for param, flag in required_params:
        value = getattr(args, param, None)
        if value is None:
            errors.append(f"Missing required parameter: {flag}")

    # If we have missing required params, return early
    if errors:
        return errors

    # Validate parameter values
    if args.nx < 1:
        errors.append("--nx must be >= 1")
    if args.ny < 1:
        errors.append("--ny must be >= 1")
    if args.W <= 0:
        errors.append("--W must be > 0")
    if args.H <= 0:
        errors.append("--H must be > 0")
    if args.sx <= 0:
        errors.append("--sx must be > 0")
    if args.sy <= 0:
        errors.append("--sy must be > 0")
    if args.border_gap < 0:
        errors.append("--border-gap must be >= 0")

    if args.inner_size_mode == 'relative':
        if args.sx > 1:
            errors.append("For relative mode, --sx must be <= 1")
        if args.sy > 1:
            errors.append("For relative mode, --sy must be <= 1")

    # Check if patterns contain required placeholders
    if '{i}' not in args.inner_pattern or '{j}' not in args.inner_pattern:
        errors.append("--inner-pattern must contain {i} and {j} placeholders")
    if '{i}' not in args.ring_pattern or '{j}' not in args.ring_pattern:
        errors.append("--ring-pattern must contain {i} and {j} placeholders")

    if errors:
        return errors

    return None


def print_configuration(config: Dict[str, Any], generator):
    """Print configuration information."""
    print("STL Grid Generator Configuration:")
    print("=" * 40)
    print(f"Grid dimensions:     {config['nx']} × {config['ny']}")
    print(f"Rectangle size:      {config['W']} × {config['H']}")
    orientation = config.get('orientation', 'z')
    normal_sign = config.get('normal_sign', 1)
    print(f"Orientation:         {orientation} (normal sign: {normal_sign:+d})")
    rotate_deg = config.get('rotate_deg', 0.0)
    print(f"Rotation:           {rotate_deg}°")
    origin = config.get('origin', [0.0, 0.0, 0.0])
    print(f"Origin:             ({origin[0]}, {origin[1]}, {origin[2]})")
    sx = config.get('sx', 0.5)
    sy = config.get('sy', 0.5)
    inner_size_mode = config.get('inner_size_mode', 'relative')
    print(f"Inner size:         {sx} × {sy} ({inner_size_mode})")
    border_gap = config.get('border_gap', 0.0)
    if border_gap > 0:
        print(f"Border gap:         {border_gap}")
    out_dir = config.get('out_dir', 'output')
    print(f"Output directory:   {out_dir}")
    stl_ascii = config.get('stl_ascii', False)
    print(f"STL format:         {'ASCII' if stl_ascii else 'Binary'}")
    print(f"Files to generate:  {2 * config['nx'] * config['ny']}")
    print()

    # Show sample cell info
    verbose = config.get('verbose', False)
    if verbose:
        print("Sample cell information (0, 0):")
        print("-" * 30)
        info = generator.get_cell_info(0, 0)
        print(f"Local bounds:       {info['local_bounds']}")
        print(f"Local center:       {info['local_center']}")
        print(f"World center:       {info['world_center']}")
        print(f"Outer size:         {info['outer_size']}")
        print(f"Inner size:         {info['inner_size']}")
        print(f"Normal vector:      {info['normal']}")
        print()


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle config file generation
    if args.generate_config:
        try:
            generate_example_config(args.generate_config)
            return
        except Exception as e:
            print(f"Error generating config file: {e}", file=sys.stderr)
            sys.exit(1)

    # Load configuration
    config = {}
    if args.config:
        try:
            config = load_yaml_config(args.config)
            print(f"Loaded configuration from: {args.config}")
        except ValueError as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            sys.exit(1)

    # Merge config with command line arguments
    try:
        merged_config = merge_config_and_args(config, args)
    except Exception as e:
        print(f"Error merging configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Skip validation if we're only using config file or generating config
    if not args.config and not args.generate_config:
        # Pure CLI mode - need to validate args
        errors = validate_args(args)
        if errors:
            print("Error: Invalid arguments:", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            print("\nFor help: stl-grid-gen --help")
            print("For config file usage: stl-grid-gen --generate-config example.yaml")
            sys.exit(1)

    # Validate final configuration only if we have a config
    if args.config:
        errors = validate_config(merged_config)
        if errors:
            print("Error: Invalid configuration:", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)

    try:
        # Create generator from merged config
        if args.config:
            generator = STLGridGenerator(
                nx=merged_config['nx'],
                ny=merged_config['ny'],
                W=merged_config['W'],
                H=merged_config['H'],
                orientation=merged_config.get('orientation', 'z'),
                normal_sign=merged_config.get('normal_sign', 1),
                sx=merged_config.get('sx', 0.5),
                sy=merged_config.get('sy', 0.5),
                inner_size_mode=merged_config.get('inner_size_mode', 'relative'),
                origin=tuple(merged_config.get('origin', [0.0, 0.0, 0.0])),
                rotate_deg=merged_config.get('rotate_deg', 0.0),
                border_gap=merged_config.get('border_gap', 0.0),
                out_dir=merged_config.get('out_dir', 'output'),
                cell_filename_inner=merged_config.get('cell_filename_inner', 'cell_inner_x{i}_y{j}.stl'),
                cell_filename_ring=merged_config.get('cell_filename_ring', 'cell_ring_x{i}_y{j}.stl'),
                stl_ascii=merged_config.get('stl_ascii', False)
            )
        else:
            # Pure CLI mode (backward compatibility)
            generator = STLGridGenerator(
                nx=args.nx, ny=args.ny,
                W=args.W, H=args.H,
                orientation=args.orientation,
                normal_sign=args.normal_sign,
                sx=args.sx, sy=args.sy,
                inner_size_mode=args.inner_size_mode,
                origin=tuple(args.origin),
                rotate_deg=args.rotate_deg,
                border_gap=args.border_gap,
                out_dir=args.out_dir,
                cell_filename_inner=args.inner_pattern,
                cell_filename_ring=args.ring_pattern,
                stl_ascii=args.stl_ascii
            )

        # Print configuration
        verbose = merged_config.get('verbose', args.verbose) if args.config else args.verbose
        info_only = merged_config.get('info_only', args.info_only) if args.config else args.info_only

        if verbose or info_only:
            if args.config:
                print_configuration(merged_config, generator)
            else:
                # Convert args to dict for backward compatibility
                args_dict = vars(args)
                print_configuration(args_dict, generator)

        if info_only:
            print("Info-only mode: no files generated.")
            return

        # Generate files
        if verbose:
            print("Generating STL files...")

        files_generated = generator.generate_all()

        out_dir = merged_config.get('out_dir', 'output') if args.config else args.out_dir
        print(f"Successfully generated {files_generated} STL files in '{out_dir}'")

        if verbose:
            print("Output files:")
            output_dir = Path(out_dir)
            nx = merged_config['nx'] if args.config else args.nx
            ny = merged_config['ny'] if args.config else args.ny
            inner_pattern = merged_config.get('cell_filename_inner', 'cell_inner_x{i}_y{j}.stl') if args.config else args.inner_pattern
            ring_pattern = merged_config.get('cell_filename_ring', 'cell_ring_x{i}_y{j}.stl') if args.config else args.ring_pattern

            for i in range(nx):
                for j in range(ny):
                    inner_file = output_dir / inner_pattern.format(i=i, j=j)
                    ring_file = output_dir / ring_pattern.format(i=i, j=j)
                    print(f"  {inner_file}")
                    print(f"  {ring_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        verbose = merged_config.get('verbose', args.verbose) if args.config else args.verbose
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()