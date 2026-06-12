from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image


OCEAN = (5, 20, 18)
LAKES_LAND = (0, 255, 0)
LAND_FILL = (128, 128, 128)

TERRAIN_COLORS = {
    "forest": (89, 199, 85),
    "hills": (248, 255, 153),
    "mountain": (157, 192, 208),
    "plains": (255, 129, 66),
    "urban": (120, 120, 120),
    "jungle": (127, 191, 0),
    "marsh": (76, 96, 35),
    "desert": (255, 127, 0),
    "deep_ocean": (2, 38, 150),
    "shallow_sea": (56, 118, 217),
    "fjords": (75, 162, 198),
    "lakes": (58, 91, 255),
}

# Approximate mapping from the current HOI4 terrain palette subset in this mod
# to the OpenGS terrain categories.
HOI4_TO_OPENGS = {
    (86, 124, 27): "plains",
    (255, 0, 24): "plains",
    (6, 200, 11): "forest",
    (58, 131, 82): "forest",
    (0, 86, 6): "jungle",
    (132, 255, 0): "hills",
    (252, 255, 0): "hills",
    (92, 83, 76): "mountain",
    (114, 137, 105): "mountain",
    (255, 0, 127): "mountain",
    (255, 0, 240): "desert",
    (206, 169, 99): "desert",
    (112, 74, 31): "desert",
    (73, 59, 15): "desert",
    (174, 0, 255): "marsh",
    (240, 255, 0): "urban",
}


def load_definition_types(definition_path: Path) -> dict[tuple[int, int, int], str]:
    result: dict[tuple[int, int, int], str] = {}
    with definition_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if len(row) < 5:
                continue
            try:
                color = tuple(map(int, row[1:4]))
            except ValueError:
                continue
            result[color] = row[4].strip().lower()
    return result


def sea_variant(type_map, x: int, y: int, width: int, height: int) -> str:
    land_neighbors = 0
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if 0 <= nx < width and 0 <= ny < height:
            ntype = type_map[ny][nx]
            if ntype == "land" or ntype == "lake":
                land_neighbors += 1
    if land_neighbors >= 2:
        return "fjords"
    if land_neighbors >= 1:
        return "shallow_sea"
    return "deep_ocean"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    map_dir = root / "map"

    definition_types = load_definition_types(map_dir / "definition.csv")
    provinces = Image.open(map_dir / "provinces.bmp").convert("RGB")
    terrain = Image.open(map_dir / "terrain.bmp").convert("RGB")
    width, height = provinces.size

    prov_px = provinces.load()
    terr_px = terrain.load()

    type_rows: list[list[str]] = []
    for y in range(height):
        row: list[str] = []
        for x in range(width):
            row.append(definition_types.get(prov_px[x, y], "land"))
        type_rows.append(row)

    land_img = Image.new("RGB", provinces.size, LAND_FILL)
    terrain_img = Image.new("RGB", provinces.size, TERRAIN_COLORS["plains"])
    land_out = land_img.load()
    terrain_out = terrain_img.load()

    for y in range(height):
        for x in range(width):
            province_type = type_rows[y][x]
            if province_type == "lake":
                land_out[x, y] = LAKES_LAND
                terrain_out[x, y] = TERRAIN_COLORS["lakes"]
                continue

            if province_type == "sea":
                land_out[x, y] = OCEAN
                terrain_out[x, y] = TERRAIN_COLORS[sea_variant(type_rows, x, y, width, height)]
                continue

            land_out[x, y] = LAND_FILL
            terrain_name = HOI4_TO_OPENGS.get(terr_px[x, y], "plains")
            terrain_out[x, y] = TERRAIN_COLORS[terrain_name]

    land_path = map_dir / "opengs_land.png"
    terrain_path = map_dir / "opengs_terrain.png"
    land_img.save(land_path)
    terrain_img.save(terrain_path)

    print(f"Wrote {land_path}")
    print(f"Wrote {terrain_path}")


if __name__ == "__main__":
    main()
