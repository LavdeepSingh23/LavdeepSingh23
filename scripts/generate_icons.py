#!/usr/bin/env python3
"""Builds the clickable pixel link icons: assets/icons/<name>-light.svg and <name>-dark.svg.
Each icon is a bevelled pixel tile with a white glyph and a tiny pixel label underneath.
Run from the repo root:  python scripts/generate_icons.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pxlib as px
px.U = 2

GLYPHS = {
    'bolt': ["......###..", ".....###...", "....###....", "...###.....", "..#######..", "..#######..",
             ".....###...", "....###....", "...###.....", "..##.......", "..#........"],
    'database': ["..########..", ".##########.", ".##########.", "............", ".##########.", ".##########.",
                 "............", ".##########.", ".##########.", "..########.."],
    'heart': [".###...###.", "#####.#####", "###########", "###########", ".#########.", "..#######..",
              "...#####...", "....###....", ".....#....."],
    'in': [".##.........", ".##.........", "............", ".##.######..", ".##.##..##..", ".##.##..##..",
           ".##.##..##..", ".##.##..##..", ".##.##..##..", ".##.##..##.."],
    'mail': ["############", "###......###", "#.##....##.#", "#..##..##..#", "#...####...#", "#..........#",
             "#..........#", "############"],
}
ICONS = [  # file, label, glyph, tile color
    ('enerlytics', 'ENERLYTICS', 'bolt', '#f2a33a'),
    ('acadhub', 'ACADHUB', 'database', '#7d5df0'),
    ('diabetes', 'DIABETES', 'heart', '#ff6f7d'),
    ('linkedin', 'LINKEDIN', 'in', '#0a66c2'),
    ('email', 'EMAIL', 'mail', '#1fa2d4'),
]
W, H = 72, 52           # canvas in cells (2px each) -> 144 x 104 px


def scale(cells, ox, oy):
    return {(ox + x * 2 + a, oy + y * 2 + b) for x, y in cells for a in (0, 1) for b in (0, 1)}


def make(label, glyph, base, theme):
    tile = {(x, y) for x in range(16) for y in range(16) if (x, y) not in ((0, 0), (15, 0), (0, 15), (15, 15))}
    hi = {(x, y) for x, y in tile if y == 0 or (x == 0 and y < 15)}
    lo = {(x, y) for x, y in tile if y == 15 or (x == 15 and y > 0)}
    mid = tile - hi - lo
    tx, ty = (W - 32) // 2, 3
    g = GLYPHS[glyph]; gw, gh = len(g[0]), len(g)
    gcells = {(c, r) for r, row in enumerate(g) for c, ch in enumerate(row) if ch == '#'}
    gx, gy = (16 - gw) // 2, (16 - gh) // 2
    # a little pixel highlight dither on the tile
    spark = {(x, y) for x, y in mid if (x + y) % 5 == 0 and x < 8 and y < 7}
    parts = [px.P(scale(mid, tx, ty), base), px.P(scale(hi, tx, ty), px.shade(base, 1.3)), px.P(scale(lo, tx, ty), px.shade(base, 0.68)),
             px.P(scale(spark, tx, ty), px.shade(base, 1.12)),
             px.P(scale({(x + gx + 1, y + gy + 1) for x, y in gcells}, tx, ty), px.shade(base, 0.55)),
             px.P(scale({(x + gx, y + gy) for x, y in gcells}, tx, ty), '#ffffff')]
    ink = px.THEMES[theme]['ink']
    text = px.safe(label); lx = (W - px.tw(text)) // 2
    parts.append(px.P(px.text_cells(text, lx, ty + 32 + 7, 1), ink))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * 2}" height="{H * 2}" viewBox="0 0 {W * 2} {H * 2}" '
            f'shape-rendering="crispEdges" role="img" aria-label="{label}">\n' + '\n'.join(parts) + '\n</svg>')


if __name__ == '__main__':
    out = os.path.join(ROOT, 'assets', 'icons'); os.makedirs(out, exist_ok=True)
    for name, label, glyph, base in ICONS:
        for theme in ('light', 'dark'):
            with open(os.path.join(out, f'{name}-{theme}.svg'), 'w') as f: f.write(make(label, glyph, base, theme))
    print('wrote', len(ICONS) * 2, 'icons')
