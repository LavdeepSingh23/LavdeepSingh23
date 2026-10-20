"""Tiny 8-bit pixel SVG engine: 3px cells, 5x7 bitmap font, dark (space) and light (daylight sky) themes."""
import math, random, textwrap

U = 3
OVERFLOW = []

G = {
'A':[".###.","#...#","#...#","#####","#...#","#...#","#...#"],
'B':["####.","#...#","#...#","####.","#...#","#...#","####."],
'C':[".###.","#...#","#....","#....","#....","#...#",".###."],
'D':["####.","#...#","#...#","#...#","#...#","#...#","####."],
'E':["#####","#....","#....","####.","#....","#....","#####"],
'F':["#####","#....","#....","####.","#....","#....","#...."],
'G':[".###.","#...#","#....","#.###","#...#","#...#",".###."],
'H':["#...#","#...#","#...#","#####","#...#","#...#","#...#"],
'I':[".###.","..#..","..#..","..#..","..#..","..#..",".###."],
'J':["..###","...#.","...#.","...#.","...#.","#..#.",".##.."],
'K':["#...#","#..#.","#.#..","##...","#.#..","#..#.","#...#"],
'L':["#....","#....","#....","#....","#....","#....","#####"],
'M':["#...#","##.##","#.#.#","#.#.#","#...#","#...#","#...#"],
'N':["#...#","##..#","#.#.#","#..##","#...#","#...#","#...#"],
'O':[".###.","#...#","#...#","#...#","#...#","#...#",".###."],
'P':["####.","#...#","#...#","####.","#....","#....","#...."],
'Q':[".###.","#...#","#...#","#...#","#.#.#","#..#.",".##.#"],
'R':["####.","#...#","#...#","####.","#.#..","#..#.","#...#"],
'S':[".####","#....","#....",".###.","....#","....#","####."],
'T':["#####","..#..","..#..","..#..","..#..","..#..","..#.."],
'U':["#...#","#...#","#...#","#...#","#...#","#...#",".###."],
'V':["#...#","#...#","#...#","#...#","#...#",".#.#.","..#.."],
'W':["#...#","#...#","#...#","#.#.#","#.#.#","##.##","#...#"],
'X':["#...#","#...#",".#.#.","..#..",".#.#.","#...#","#...#"],
'Y':["#...#","#...#",".#.#.","..#..","..#..","..#..","..#.."],
'Z':["#####","....#","...#.","..#..",".#...","#....","#####"],
'0':[".###.","#...#","#..##","#.#.#","##..#","#...#",".###."],
'1':["..#..",".##..","..#..","..#..","..#..","..#..",".###."],
'2':[".###.","#...#","....#","...#.","..#..",".#...","#####"],
'3':[".###.","#...#","....#","..##.","....#","#...#",".###."],
'4':["...#.","..##.",".#.#.","#..#.","#####","...#.","...#."],
'5':["#####","#....","####.","....#","....#","#...#",".###."],
'6':[".###.","#....","#....","####.","#...#","#...#",".###."],
'7':["#####","....#","...#.","..#..",".#...",".#...",".#..."],
'8':[".###.","#...#","#...#",".###.","#...#","#...#",".###."],
'9':[".###.","#...#","#...#",".####","....#","....#",".###."],
'.':[".....",".....",".....",".....",".....","..##.","..##."],
',':[".....",".....",".....",".....","..##.","...#.","..#.."],
':':[".....","..##.","..##.",".....","..##.","..##.","....."],
'+':[".....","..#..","..#..","#####","..#..","..#..","....."],
'-':[".....",".....",".....","#####",".....",".....","....."],
'>':["#....",".#...","..#..","...#.","..#..",".#...","#...."],
'%':["##..#","##..#","...#.","..#..",".#...","#..##","#..##"],
'/':["....#","....#","...#.","..#..",".#...","#....","#...."],
'?':[".###.","#...#","....#","...#.","..#..",".....","..#.."],
'$':["..#..",".####","#.#..",".###.","..#.#","####.","..#.."],
' ':["....."]*7,
}
_MAP = {"'": '', '"': '', '(': '', ')': '', '_': '-', '&': '+', ';': ',', '#': '', '!': '.', '@': '', '[': '', ']': '',
        '|': '/', '\\': '/', '*': '+', '=': '-', '<': '', '~': '-', '`': '', '{': '', '}': '', '^': '', '\t': ' ', '\n': ' '}
def safe(s):
    out = []
    for ch in str(s).upper():
        if ch in G: out.append(ch)
        elif ch in _MAP: out.append(_MAP[ch])
        else: out.append(' ')
    return ''.join(out)
def wrap(s, n): return textwrap.wrap(safe(s), n, break_long_words=True, break_on_hyphens=False) or ['']
def clip(s, n):
    s = safe(s).strip()
    return s if len(s) <= n else s[:max(0, n - 2)].rstrip() + '..'
def tw(s, k=1): return max(0, len(s) * 6 - 1) * k

def text_cells(s, cx, cy, k=1):
    cells = set()
    for i, ch in enumerate(s):
        for r, row in enumerate(G[ch]):
            for c, v in enumerate(row):
                if v == '#':
                    for dy in range(k):
                        for dx in range(k):
                            cells.add((cx + (i * 6 + c) * k + dx, cy + r * k + dy))
    return cells

def path_d(cells):
    rows = {}
    for x, y in cells: rows.setdefault(y, []).append(x)
    out = []
    for y in sorted(rows):
        xs = sorted(rows[y]); s = p = xs[0]
        for x in xs[1:] + [None]:
            if x is None or x != p + 1:
                n = p - s + 1
                out.append(f'M{s*U} {y*U}h{n*U}v{U}h{-n*U}z')
                if x is not None: s = x
            if x is not None: p = x
    return ''.join(out)
def P(cells, color): return f'<path d="{path_d(cells)}" fill="{color}"/>' if cells else ''
def shift(cells, dx, dy): return {(x + dx, y + dy) for x, y in cells}
BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
def bayer(x, y): return (BAYER[y % 4][x % 4] + 0.5) / 16

def cut_rect(x0, y0, x1, y1, ins=(0,)):
    cells = set()
    for y in range(y0, y1):
        d = 0; top, bot = y - y0, y1 - 1 - y
        if top < len(ins): d = max(d, ins[top])
        if bot < len(ins): d = max(d, ins[bot])
        for x in range(x0 + d, x1 - d): cells.add((x, y))
    return cells

def _rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _hex(c): return '#%02x%02x%02x' % tuple(max(0, min(255, int(v))) for v in c)
def shade(h, f): return _hex(tuple(v * f for v in _rgb(h)))
def tint(h, f): return _hex(tuple(v + (255 - v) * f for v in _rgb(h)))

THEMES = {
 'dark': dict(border='#232a4a', panel='#05060d', ink='#e6edf3', strong='#f0f6fc', dim='#7d8da8', muted='#6f7fa3',
              divider='#2a3150', empty='#10131f', hilite='#0b1020',
              green='#00e5a0', cyan='#4cc9f0', purple='#9b8cff', gold='#f5c542', red='#ff5f57', grey='#4b5a78'),
 'light': dict(border='#5d86b0', panel='#f6fbff', ink='#0e2036', strong='#071426', dim='#4b6584', muted='#3d5a80',
               divider='#7aa5cf', empty='#c3dcf2', hilite='#e3f1ff',
               green='#067a53', cyan='#0b5f99', purple='#5a3fc0', gold='#a56d00', red='#c2312b', grey='#7f97b2'),
}
SKY = ['#a9d6ff', '#bfe2ff', '#d3ecff', '#e4f5ff']

ICONS = {
 'trophy': [".XXXXXX.","XXXXXXXX","X.XXXX.X",".XXXXXX.","..XXXX..","...XX...","...XX...","..XXXX.."],
 'paper':  ["XXXXXX..","X....XX.","X.XX..XX","X....XXX","X.XXXX.X","X......X","X.XXXX.X","XXXXXXXX"],
 'flag':   ["XXXXXX..","XXXXXXX.","XXXXXX..","X.......","X.......","X.......","X.......","X......."],
 'medal':  [".X....X.","..X..X..","..XXXX..",".XXXXXX.","XXXXXXXX","XXXXXXXX",".XXXXXX.","..XXXX.."],
 'bulb':   ["..XXXX..",".XXXXXX.",".XXXXXX.",".XXXXXX.","..XXXX..","..X..X..","..XXXX..","...XX..."],
 'star':   ["...XX...","...XX...","XXXXXXXX",".XXXXXX.","..XXXX..",".XXXXXX.",".XX..XX.","XX....XX"],
 'shield': ["XXXXXXXX","XXXXXXXX","XXXXXXXX","XXXXXXXX",".XXXXXX.",".XXXXXX.","..XXXX..","...XX..."],
 'ship':   ["....X....","...XXX...",".XXXXXXX.","XXXXXXXXX","XX.XXX.XX"],
}
def icon_cells(name, cx, cy, s=1):
    cells = set()
    for r, row in enumerate(ICONS[name]):
        for c, v in enumerate(row):
            if v == 'X':
                for dy in range(s):
                    for dx in range(s): cells.add((cx + c * s + dx, cy + r * s + dy))
    return cells

def cloud_cells(cx, cy, w):
    body, under = set(), set()
    bumps = [(-w * .5, w * .52), (0.0, w * .8), (w * .5, w * .58)]
    for x in range(-w, w + 1):
        top = 0.0
        for bx, r in bumps:
            d = x - bx
            if abs(d) <= r: top = max(top, math.sqrt(r * r - d * d))
        top = max(top, 1.0 if abs(x) <= w - 1 else 0.0)
        for y in range(-int(top), 1):
            (under if y == 0 else body).add((cx + x, cy + y))
    return body, under

class Scene:
    def __init__(self, wc, hc, theme='dark', static=False, seed=1, star_div=90):
        self.wc, self.hc, self.theme, self.static, self.seed, self.star_div = wc, hc, theme, static, seed, star_div
        self.t = THEMES[theme]
        self.content, self.occ, self.defs = [], [], []
    # ---- content helpers
    def add(self, s):
        if s: self.content.append(s)
    def occupy(self, x0, y0, x1, y1): self.occ.append((x0, y0, x1, y1))
    def c(self, name): return self.t.get(name, name)
    def text(self, s, x, y, k=1, color='ink'):
        s = safe(s)
        if x + tw(s, k) > 297: OVERFLOW.append((s, x + tw(s, k)))
        self.add(P(text_cells(s, x, y, k), self.c(color)))
        self.occupy(x - 1, y - 1, x + tw(s, k) + 1, y + 7 * k + 1)
        return x + tw(s, k)
    def text_r(self, s, xr, y, k=1, color='ink'):
        s = safe(s); return self.text(s, xr - tw(s, k), y, k, color)
    def box(self, x, y, w, h, accent, fill='panel'):
        col = self.c(accent)
        self.add(P(cut_rect(x, y, x + w, y + h, [1]), col))
        self.add(P(cut_rect(x + 1, y + 1, x + w - 1, y + h - 1, [0]), self.c(fill)))
        self.occupy(x - 1, y - 1, x + w + 1, y + h + 1)
    def dotted(self, x0, x1, y, color='divider'):
        self.add(P({(x, y) for x in range(x0, x1) if x % 4 != 3}, self.c(color)))
    def pop(self, inner, start, T):
        if self.static: return f'<g>{inner}</g>'
        return (f'<g><animate attributeName="opacity" values="0;1" keyTimes="0;{min(start/T, .999):.4f}" calcMode="discrete" '
                f'dur="{T}s" begin="0s" fill="freeze"/>{inner}</g>')
    def blink(self, lo=1.8, hi=4.0, rnd=None):
        rnd = rnd or random
        return '' if self.static else (f'<animate attributeName="opacity" values="1;0.1;1" keyTimes="0;0.5;0.75" calcMode="discrete" '
                                       f'dur="{rnd.uniform(lo,hi):.1f}s" begin="{rnd.uniform(0,3):.1f}s" repeatCount="indefinite"/>')
    # ---- backdrops
    def _free(self, x0, y0, x1, y1):
        return not any(not (x1 < a or x0 > c or y1 < b or y0 > d) for a, b, c, d in self.occ)
    def _stars(self):
        rnd = random.Random(self.seed); wc, hc = self.wc, self.hc
        sc = {'#3b4468': set(), '#8f9bc4': set(), '#ffffff': set()}; tws = []
        for _ in range(int(wc * hc / self.star_div)):
            x, y = rnd.randint(2, wc - 3), rnd.randint(2, hc - 3)
            if not self._free(x, y, x, y): continue
            r = rnd.random()
            if r < .55: sc['#3b4468'].add((x, y))
            elif r < .87: sc['#8f9bc4'].add((x, y))
            elif r < .95: sc['#ffffff'].add((x, y))
            elif self._free(x - 1, y - 1, x + 1, y + 1):
                tws.append(({(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)}, rnd.choice(['#ffffff', '#ffe9a8', '#9fc4ff'])))
        out = [P(cells, col) for col, cells in sc.items()]
        for cells, col in tws: out.append(f'<path d="{path_d(cells)}" fill="{col}">{self.blink(rnd=rnd)}</path>')
        return ''.join(out)
    def _sky(self):
        W, H = self.wc * U, self.hc * U; n = len(SKY); out = []
        edges = [round(i * self.hc / n) for i in range(n + 1)]
        for i in range(n):
            out.append(f'<rect x="0" y="{edges[i]*U}" width="{W}" height="{(edges[i+1]-edges[i])*U}" fill="{SKY[i]}"/>')
        for i in range(n - 1):
            self.defs.append(f'<pattern id="sk{i}" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="{SKY[i]}"/>'
                             f'<path d="M0 0h3v3h-3zM3 3h3v3h-3z" fill="{SKY[i+1]}"/></pattern>')
            y = (edges[i + 1] - 2) * U
            out.append(f'<rect x="0" y="{y}" width="{W}" height="{2*U}" fill="url(#sk{i})"/>')
        return ''.join(out)
    def _clouds(self):
        rnd = random.Random(self.seed + 99); wc, hc = self.wc, self.hc; out = []
        want = max(1, wc * hc // 6000)
        for _ in range(60):
            if want <= 0: break
            w = rnd.randint(6, 11); cx = rnd.randint(w + 4, wc - w - 4); cy = rnd.randint(8, hc - 4)
            if self._free(cx - w - 1, cy - 9, cx + w + 1, cy + 1):
                body, under = cloud_cells(cx, cy, w)
                out.append(P(body, '#ffffff') + P(under, '#cfe3f7'))
                self.occupy(cx - w - 1, cy - 9, cx + w + 1, cy + 1); want -= 1
        return ''.join(out)
    def svg(self):
        wc, hc = self.wc, self.hc; W, H = wc * U, hc * U
        defs = list(self.defs); body = [P(cut_rect(0, 0, wc, hc, [2, 1]), self.t['border'])]
        inner = cut_rect(1, 1, wc - 1, hc - 1, [1])
        if self.theme == 'dark':
            body += [P(inner, '#000000'), self._stars()]
        else:
            sky = self._sky(); defs.append(f'<clipPath id="inn"><path d="{path_d(inner)}"/></clipPath>')
            body += [f'<g clip-path="url(#inn)">{sky}</g>', self._clouds()]
        body += self.content
        d = f'<defs>{"".join(self.defs + [x for x in defs if x not in self.defs])}</defs>\n' if (defs or self.defs) else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}" shape-rendering="crispEdges">\n{d}' + '\n'.join(b for b in body if b) + '\n</svg>')
