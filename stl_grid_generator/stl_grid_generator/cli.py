"""Command-line interface for STL Grid Generator."""

import argparse
import sys
from pathlib import Path

from .core import STLGridGenerator


def create_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Generate rectangular STL grids with optional holes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 3x2 grid with Z-normal, relative holes
  stl-grid-gen --nx 3 --ny 2 --W 10 --H 8 --sx 0.7 --sy 0.7

  # Generate X-oriented grid with absolute hole sizes
  stl-grid-gen --nx 2 --ny 2 --W 5 --H 5 --orientation x --sx 1.0 --sy 1.0 --inner-size-mode absolute

  # Generate with rotation and custom origin
  stl-grid-gen --nx 4 --ny 3 --W 12 --H 9 --rotate-deg 45 --origin 5 3 2

  # Generate ASCII STL files with custom filenames
  stl-grid-gen --nx 2 --ny 2 --W 4 --H 4 --stl-ascii --outer-pattern "part_{i}_{j}_base.stl"
        """
    )

    # Required parameters
    parser.add_argument('--nx', type=int, required=True,
                       help='Number of cells along u-axis (>= 1)')
    parser.add_argument('--ny', type=int, required=True,
                       help='Number of cells along v-axis (>= 1)')
    parser.add_argument('--W', type=float, required=True,
                       help='Total width along u-axis (> 0)')
    parser.add_argument('--H', type=float, required=True,
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
    parser.add_argument('--outer-pattern', type=str, default='cell_{i}_{j}_outer.stl',
                       help='Filename pattern for outer rectangles (default: cell_{i}_{j}_outer.stl)')
    parser.add_argument('--ring-pattern', type=str, default='cell_{i}_{j}_ring.stl',
                       help='Filename pattern for rings (default: cell_{i}_{j}_ring.stl)')
    parser.add_argument('--stl-ascii', action='store_true',
                       help='Generate ASCII STL files (default: binary)')

    # Information options
    parser.add_argument('--info-only', action='store_true',
                       help='Print configuration info without generating files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    return parser


def validate_args(args):
    """Validate command-line arguments."""
    errors = []

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
    if '{i}' not in args.outer_pattern or '{j}' not in args.outer_pattern:
        errors.append("--outer-pattern must contain {i} and {j} placeholders")
    if '{i}' not in args.ring_pattern or '{j}' not in args.ring_pattern:
        errors.append("--ring-pattern must contain {i} and {j} placeholders")

    if errors:
        return errors

    return None


def print_configuration(args, generator):
    """Print configuration information."""
    print("STL Grid Generator Configuration:")
    print("=" * 40)
    print(f"Grid dimensions:     {args.nx} × {args.ny}")
    print(f"Rectangle size:      {args.W} × {args.H}")
    print(f"Orientation:         {args.orientation} (normal sign: {args.normal_sign:+d})")
    print(f"Rotation:           {args.rotate_deg}°")
    print(f"Origin:             ({args.origin[0]}, {args.origin[1]}, {args.origin[2]})")
    print(f"Inner size:         {args.sx} × {args.sy} ({args.inner_size_mode})")
    if args.border_gap > 0:
        print(f"Border gap:         {args.border_gap}")
    print(f"Output directory:   {args.out_dir}")
    print(f"STL format:         {'ASCII' if args.stl_ascii else 'Binary'}")
    print(f"Files to generate:  {2 * args.nx * args.ny}")
    print()

    # Show sample cell info
    if args.verbose:
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

    # Validate arguments
    errors = validate_args(args)
    if errors:
        print("Error: Invalid arguments:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        sys.exit(1)

    try:
        # Create generator
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
            cell_filename_outer=args.outer_pattern,
            cell_filename_ring=args.ring_pattern,
            stl_ascii=args.stl_ascii
        )

        # Print configuration
        if args.verbose or args.info_only:
            print_configuration(args, generator)

        if args.info_only:
            print("Info-only mode: no files generated.")
            return

        # Generate files
        if args.verbose:
            print("Generating STL files...")

        files_generated = generator.generate_all()

        print(f"Successfully generated {files_generated} STL files in '{args.out_dir}'")

        if args.verbose:
            print(f"Output files:")
            output_dir = Path(args.out_dir)
            for i in range(args.nx):
                for j in range(args.ny):
                    outer_file = output_dir / args.outer_pattern.format(i=i, j=j)
                    ring_file = output_dir / args.ring_pattern.format(i=i, j=j)
                    print(f"  {outer_file}")
                    print(f"  {ring_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()