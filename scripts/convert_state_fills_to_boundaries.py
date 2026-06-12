from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image


BACKGROUND_RGB = (0, 0, 0)
BOUNDARY_RGBA = (0, 0, 0, 255)
EMPTY_RGBA = (0, 0, 0, 0)


def is_background(rgb: tuple[int, int, int]) -> bool:
    return rgb == BACKGROUND_RGB


def load_province_types(definition_path: Path) -> dict[tuple[int, int, int], str]:
    province_types: dict[tuple[int, int, int], str] = {}
    with definition_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if len(row) < 5:
                continue

            try:
                color = tuple(map(int, row[1:4]))
            except ValueError:
                continue

            province_types[color] = row[4].strip().lower()

    return province_types


def resolve_map_inputs(src_path: Path) -> tuple[Path, Path]:
    map_dir = src_path.parent
    definition_path = map_dir / "definition.csv"
    provinces_path = map_dir / "provinces.bmp"
    if not definition_path.exists():
        raise FileNotFoundError(f"Missing {definition_path}")
    if not provinces_path.exists():
        raise FileNotFoundError(f"Missing {provinces_path}")
    return definition_path, provinces_path


def build_boundary_map(src_path: Path, dst_path: Path) -> None:
    src = Image.open(src_path).convert("RGBA")
    width, height = src.size
    src_px = src.load()

    definition_path, provinces_path = resolve_map_inputs(src_path)
    province_types = load_province_types(definition_path)
    provinces = Image.open(provinces_path).convert("RGB")
    if provinces.size != src.size:
        raise ValueError(
            f"{provinces_path} size {provinces.size} does not match {src_path} size {src.size}"
        )
    prov_px = provinces.load()

    out = Image.new("RGBA", src.size, EMPTY_RGBA)
    out_px = out.load()

    for y in range(height):
        for x in range(width):
            here = src_px[x, y][:3]
            if is_background(here):
                continue

            here_type = province_types.get(prov_px[x, y], "land")
            if here_type != "land":
                continue

            # Draw coastlines from the land side only, including both sea and lake edges.
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue

                neighbor_type = province_types.get(prov_px[nx, ny], "land")
                if neighbor_type == "sea" or neighbor_type == "lake":
                    out_px[x, y] = BOUNDARY_RGBA
                    break

            if out_px[x, y] == BOUNDARY_RGBA:
                continue

            # For state-to-state borders, compare only right/down neighbors so the
            # output stays one pixel thick instead of drawing both sides.
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if nx >= width or ny >= height:
                    continue

                neighbor_type = province_types.get(prov_px[nx, ny], "land")
                if neighbor_type != "land":
                    continue

                neighbor = src_px[nx, ny][:3]
                if is_background(neighbor):
                    continue
                if neighbor != here:
                    out_px[x, y] = BOUNDARY_RGBA
                    break

    out.save(dst_path)


def default_output_path(src_path: Path) -> Path:
    return src_path.with_name(f"{src_path.stem}_boundaries{src_path.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert filled state maps into pure-black one-pixel boundaries. "
            "Includes coastlines against sea and lakes, plus internal state borders."
        )
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input filled state images")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file instead of writing a *_boundaries copy",
    )
    args = parser.parse_args()

    for src_path in args.inputs:
        dst_path = src_path if args.in_place else default_output_path(src_path)
        build_boundary_map(src_path, dst_path)
        print(f"Wrote {dst_path}")


if __name__ == "__main__":
    main()
