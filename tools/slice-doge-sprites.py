#!/usr/bin/env python3
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCES_BY_KING = {
    "doge": {
        "swordsman": Path("/Users/binkyfishai/Downloads/ChatGPT Image Jun 22, 2026, 10_05_52 PM.png"),
        "villager": Path("/Users/binkyfishai/Downloads/ChatGPT Image Jun 22, 2026, 10_05_45 PM.png"),
        "archer": Path("/Users/binkyfishai/Downloads/ChatGPT Image Jun 22, 2026, 10_05_17 PM.png"),
        "lancer": Path("/Users/binkyfishai/Downloads/lancer doge.png"),
        "siege": Path("/Users/binkyfishai/Downloads/siegecrawler real.png"),
    },
    "pepe": {
        "swordsman": Path("/Users/binkyfishai/Downloads/pepe swordsman.png"),
        "villager": Path("/Users/binkyfishai/Downloads/pepevillager.png"),
        "archer": Path("/Users/binkyfishai/Downloads/ChatGPT Image Jun 23, 2026, 01_59_38 AM.png"),
        "lancer": Path("/Users/binkyfishai/Downloads/ChatGPT Image Jun 23, 2026, 02_09_13 AM.png"),
    },
}

OUT_DIR = ROOT / "assets" / "units"
CELL = 48
SHEET = CELL * 4

# Source sheets are 4 columns x 2 rows. Build a 4x4 Godot sheet where each row
# is a useful facing band and each column is a tiny walk cycle.
ROW_POSES = [
    [0, 7, 0, 7],  # facing down / camera
    [1, 2, 1, 2],  # side / forward diagonal
    [4, 5, 4, 5],  # facing up / away
    [3, 6, 3, 6],  # back diagonal / alternate side
]


def bg_candidate(pixel):
    r, g, b = pixel[:3]
    low = min(r, g, b)
    high = max(r, g, b)
    spread = high - low
    return (low >= 218 and spread <= 58) or (high >= 145 and spread <= 28)


def zero_transparent_rgb(rgba):
    pix = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pix[x, y]
            if a <= 2:
                pix[x, y] = (0, 0, 0, 0)
    return rgba


def touches_transparent(pix, x, y, w, h):
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if nx < 0 or ny < 0 or nx >= w or ny >= h:
            return True
        if pix[nx, ny][3] <= 2:
            return True
    return False


def strip_background_fringe(rgba):
    pix = rgba.load()
    w, h = rgba.size
    for _ in range(3):
        clear = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = pix[x, y]
                if a <= 2 or not touches_transparent(pix, x, y, w, h):
                    continue
                if bg_candidate((r, g, b, a)):
                    clear.append((x, y))
        if not clear:
            break
        for x, y in clear:
            pix[x, y] = (0, 0, 0, 0)
    return zero_transparent_rgb(rgba)


def resize_rgba(src, size):
    premul = src.convert("RGBA")
    pix = premul.load()
    for y in range(premul.height):
        for x in range(premul.width):
            r, g, b, a = pix[x, y]
            pix[x, y] = (r * a // 255, g * a // 255, b * a // 255, a)
    resized = premul.resize(size, Image.Resampling.LANCZOS)
    pix = resized.load()
    for y in range(resized.height):
        for x in range(resized.width):
            r, g, b, a = pix[x, y]
            if a <= 2:
                pix[x, y] = (0, 0, 0, 0)
            else:
                pix[x, y] = (
                    min(255, round(r * 255 / a)),
                    min(255, round(g * 255 / a)),
                    min(255, round(b * 255 / a)),
                    a,
                )
    return resized


def remove_small_components(rgba, min_area=8):
    pix = rgba.load()
    w, h = rgba.size
    seen = set()
    for sy in range(h):
        for sx in range(w):
            if (sx, sy) in seen or pix[sx, sy][3] <= 8:
                continue
            q = deque([(sx, sy)])
            component = []
            seen.add((sx, sy))
            while q:
                x, y = q.popleft()
                component.append((x, y))
                for ny in range(y - 1, y + 2):
                    for nx in range(x - 1, x + 2):
                        if nx < 0 or ny < 0 or nx >= w or ny >= h or (nx, ny) in seen:
                            continue
                        if pix[nx, ny][3] <= 8:
                            continue
                        seen.add((nx, ny))
                        q.append((nx, ny))
            if len(component) < min_area:
                for x, y in component:
                    pix[x, y] = (0, 0, 0, 0)
    return rgba


def transparent_cell(cell):
    rgba = cell.convert("RGBA")
    pix = rgba.load()
    w, h = rgba.size
    seen = set()
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen:
            continue
        seen.add((x, y))
        if pix[x, y][3] <= 2:
            continue
        if not bg_candidate(pix[x, y]):
            continue
        pix[x, y] = (255, 255, 255, 0)
        q.append((x + 1, y))
        q.append((x - 1, y))
        q.append((x, y + 1))
        q.append((x, y - 1))

    return strip_background_fringe(rgba)


def crop_pose(src, index):
    sw, sh = src.size
    col = index % 4
    row = index // 4
    x0 = round(col * sw / 4)
    x1 = round((col + 1) * sw / 4)
    y0 = round(row * sh / 2)
    y1 = round((row + 1) * sh / 2)
    cell = transparent_cell(src.crop((x0, y0, x1, y1)))
    bbox = cell.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"pose {index} has no visible pixels")
    return cell.crop(bbox)


def fit_pose(pose):
    max_w = 44
    max_h = 46
    scale = min(max_w / pose.width, max_h / pose.height)
    nw = max(1, round(pose.width * scale))
    nh = max(1, round(pose.height * scale))
    scaled = resize_rgba(pose, (nw, nh))
    out = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    scaled = remove_small_components(scaled)
    out.alpha_composite(scaled, ((CELL - nw) // 2, CELL - nh - 1))
    return out


def build_sheet(king, kind, path):
    src = Image.open(path).convert("RGBA")
    poses = [fit_pose(crop_pose(src, i)) for i in range(8)]
    sheet = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    for row, indices in enumerate(ROW_POSES):
        for col, pose_idx in enumerate(indices):
            sheet.alpha_composite(poses[pose_idx], (col * CELL, row * CELL))
    out = OUT_DIR / f"{king}_{kind}_walk.png"
    sheet.save(out)
    return out


def main():
    for king, sources in SOURCES_BY_KING.items():
        for kind, path in sources.items():
            if not path.exists():
                raise FileNotFoundError(path)
            out = build_sheet(king, kind, path)
            print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
