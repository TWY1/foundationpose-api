#!/usr/bin/env python3
"""
Generate book-shaped CAD models for FoundationPose.
Each book is a rectangular box with slightly different dimensions
to simulate different book titles.
"""
import argparse
import os
import sys

try:
    import trimesh
    import numpy as np
except ImportError:
    print("trimesh not installed. Run: pip install trimesh numpy")
    sys.exit(1)


BOOKS = [
    {"name": "book_a5_thin", "width": 0.148, "height": 0.210, "depth": 0.008},
    {"name": "book_a5_medium", "width": 0.148, "height": 0.210, "depth": 0.015},
    {"name": "book_a5_thick", "width": 0.148, "height": 0.210, "depth": 0.025},
    {"name": "book_a4_thin", "width": 0.210, "height": 0.297, "depth": 0.008},
    {"name": "book_a4_medium", "width": 0.210, "height": 0.297, "depth": 0.018},
    {"name": "book_a4_thick", "width": 0.210, "height": 0.297, "depth": 0.030},
    {"name": "book_pocket", "width": 0.110, "height": 0.178, "depth": 0.010},
    {"name": "book_novel", "width": 0.130, "height": 0.198, "depth": 0.020},
    {"name": "book_textbook", "width": 0.180, "height": 0.240, "depth": 0.035},
    {"name": "book_magazine", "width": 0.210, "height": 0.280, "depth": 0.005},
]


def generate(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for b in BOOKS:
        mesh = trimesh.creation.box(
            extents=[b["width"], b["height"], b["depth"]],
        )
        path = os.path.join(output_dir, f"{b['name']}.obj")
        mesh.export(path)
        print(f"  ✓ {b['name']}.obj  ({b['width']}×{b['height']}×{b['depth']} m)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate book CAD models")
    parser.add_argument("--output", "-o", default="./data/objects",
                        help="Output directory for OBJ files")
    args = parser.parse_args()
    generate(args.output)
    print(f"\nGenerated {len(BOOKS)} book models in {args.output}")
