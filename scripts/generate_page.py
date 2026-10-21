#!/usr/bin/env python3
"""Builds the one-page pixel README: assets/page-light.svg and assets/page-dark.svg.

One continuous scene, no panels:
  * sky that moves from morning to sunset (light) or dusk to deep night (dark)
  * a pixel path down the left with a little walker that visits every section
  * grass ledges with trees and spinning wind turbines between sections
  * dark mode extras: aurora, planets, shooting stars
  * live activity (streak, totals, commits, contribution invaders) pulled from GitHub

Run from the repo root:   python scripts/generate_page.py
Standard library only. Live data needs network + (optionally) GITHUB_TOKEN; offline it falls back to
scripts/live_snapshot.json. The avatar comes from scripts/avatar_cells.json (rebuilt from assets/avatar.png
when Pillow + numpy are installed and that json is missing)."""
import os, re, sys, math, json, random, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pxlib as px

U = 2                      # one pixel cell = 2 screen px
px.U = U
px.G['@'] = [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."]

# dark mode swaps the neon green for a retro coral (light mode keeps its deeper green)
px.THEMES['dark']['green'] = '#ff8a7a'
CORAL = '#ff8a7a'

WC = 450                   # 450 cells * 2px = 900px wide
L, R = 24, 426             # text column
TRACK = 11                 # x of the path down the left side
LINE = 11                  # body line pitch
TOTAL = 8                  # numbered sections
USER = os.environ.get('GH_USER', 'LavdeepSingh23')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

# --------------------------------------------------------------------------- sky
SKY_STOPS = {
    # morning peach -> day blue -> pastel sunset (kept pale so dark ink stays readable)
    'light': [(0.00, '#ffe3bd'), (0.06, '#ffefd8'), (0.11, '#eef0ff'), (0.20, '#bbddff'), (0.45, '#a6d4ff'),
              (0.60, '#d3eeff'), (0.68, '#ece9ff'), (0.76, '#ffeadb'), (0.88, '#ffd5d0'), (1.00, '#ecd0ee')],
    # dusk -> night deepens
    'dark': [(0.00, '#141a46'), (0.12, '#0a0f2c'), (0.35, '#04061a'), (0.70, '#02030a'), (1.00, '#060418')],
}
def _lerp(a, b, t):
    ra, rb = px._rgb(a), px._rgb(b)
    return px._hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))
def sky_colors(theme, n):
    stops, out = SKY_STOPS[theme], []
    for i in range(n):
        t = i / (n - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1: out.append(_lerp(c0, c1, (t - t0) / (t1 - t0))); break
    return out


class Page(px.Scene):
    def text(self, s, x, y, k=1, color='ink'):
        s = px.safe(s)
        if x + px.tw(s, k) > self.wc - 12: print('OVERFLOW:', s, x + px.tw(s, k))
        self.add(px.P(px.text_cells(s, x, y, k), self.c(color)))
        self.occupy(x - 1, y - 1, x + px.tw(s, k) + 1, y + 7 * k + 1)
        return x + px.tw(s, k)

    # ---- occupancy mask (for effects that must stay off the text)
    def mask(self):
        grid = [bytearray(self.wc) for _ in range(self.hc)]
        for x0, y0, x1, y1 in self.occ:
            x0, x1 = max(0, x0), min(self.wc - 1, x1)
            if x1 < x0: continue
            for y in range(max(0, y0), min(self.hc - 1, y1) + 1): grid[y][x0:x1 + 1] = b'\x01' * (x1 - x0 + 1)
        return grid

    # ---- light: drifting clouds
    def clouds(self, want):
        rnd = random.Random(self.seed + 99); out = []
        for _ in range(1500):
            if want <= 0: break
            w = rnd.randint(6, 12); cx = rnd.randint(w + 14, self.wc - w - 14); cy = rnd.randint(14, self.hc - 70)
            top = int(w * 0.85) + 2; drift = rnd.randint(5, 10)
            if self._free(cx - w - 2 - drift, cy - top, cx + w + 2 + drift, cy + 2):
                body, under = px.cloud_cells(cx, cy, w)
                dur = rnd.uniform(38, 80)
                anim = (f'<animateTransform attributeName="transform" type="translate" values="0 0;{drift*U} 0;0 0;{-drift*U} 0;0 0" '
                        f'dur="{dur:.0f}s" begin="-{rnd.uniform(0, dur):.0f}s" repeatCount="indefinite"/>')
                out.append(f'<g>{anim}{px.P(body, "#ffffff")}{px.P(under, "#cfe3f7")}</g>')
                self.occupy(cx - w - 2 - drift, cy - top, cx + w + 2 + drift, cy + 2); want -= 1
        return ''.join(out)

    # ---- dark: aurora, planets, shooting stars
    def aurora(self, grid, ribbons):
        rnd = random.Random(self.seed + 5); groups = {}
        cols = ['#2fd0c0', '#3dc8ff', '#7d9bff', '#b48cff', '#ff8fb8']
        for base_y, amp, thick, strength, phase in ribbons:
            for x in range(self.wc):
                crest = base_y + amp * math.sin(x / 80 + phase) + amp * 0.4 * math.sin(x / 27 + phase * 2)
                curtain = 0.55 + 0.45 * math.sin(x / 5.5 + 3 * math.sin(x / 41 + phase))
                ci = min(len(cols) - 1, int((x / self.wc) * len(cols) + 0.5 * math.sin(x / 70 + phase) + 0.5))
                seg = min(3, x * 4 // self.wc)
                for k in range(int(thick)):
                    y = int(crest + k)
                    if y < 0 or y >= self.hc or grid[y][x]: continue
                    t = k / thick
                    cov = ((1 - t) ** 1.7) * strength * curtain
                    if px.bayer(x, y) < cov: groups.setdefault((ci, seg), set()).add((x, y))
        out = []
        for (ci, seg), cells in sorted(groups.items()):
            dur = 5 + seg * 1.7 + ci * 0.6
            out.append(f'<g>{px.P(cells, cols[ci])}<animate attributeName="opacity" values="0.55;1;0.55" dur="{dur:.1f}s" '
                       f'begin="-{rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/></g>')
        return ''.join(out)

    def planet(self, cx, cy, r, bands, ring=None, craters=False):
        layers, ldir = {}, (-0.55, -0.6, 0.58)
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                nx, ny = (x - cx) / r, (y - cy) / r; d = nx * nx + ny * ny
                if d > 1.0: continue
                lum = max(0, nx * ldir[0] + ny * ldir[1] + math.sqrt(1 - d) * ldir[2]) + (px.bayer(x, y) - 0.5) * 0.24
                f = 1.15 if lum > 0.62 else (0.82 if lum > 0.3 else 0.48)
                bi = int(((ny + 1) / 2 * len(bands) * 1.0 + 0.5 * math.sin(nx * 3.2)) % len(bands)) if len(bands) > 1 else 0
                layers.setdefault(px.shade(bands[bi], f), set()).add((x, y))
        out = []
        back, front = set(), set()
        if ring:
            a, b, tilt = int(r * 1.9), r * 0.4, 0.22
            for x in range(cx - a - 1, cx + a + 2):
                for y in range(cy - r, cy + r + 1):
                    yr = (y - cy) - tilt * (x - cx); e = ((x - cx) / a) ** 2 + (yr / b) ** 2
                    if 0.5 <= e <= 1.0: (front if yr > 0 else back).add((x, y))
            out.append(px.P(back, ring))
        out += [px.P(cells, col) for col, cells in layers.items()]
        if craters:
            cr = set()
            for dx, dy, rr in ((-2, -1, 1), (2, 2, 1), (-1, 3, 1), (3, -2, 1)):
                cr |= {(cx + dx + a, cy + dy + b) for a in (0, 1) for b in (0, 1)}
            out.append(px.P(cr, px.shade(bands[0], 0.6)))
        if ring: out.append(px.P(front, ring))
        return ''.join(out)

    def deco_dark(self):
        rnd = random.Random(self.seed + 21); out = []
        specs = [('ring', 10, ['#d8b07a', '#c99c64', '#d8b07a'], '#ecd9ae'), ('gas', 13, ['#7fa7e8', '#a9c4f0', '#6a8fd6', '#c3b5f0', '#7a6ad0'], None),
                 ('rocky', 6, ['#b9bccb'], None), ('red', 8, ['#d9694a', '#c2553a', '#d9694a'], None)]
        for kind, r, bands, ring in specs:
            a = int(r * 1.9) if ring else r
            for _ in range(4000):
                cx = rnd.randint(a + 28, self.wc - a - 6); cy = rnd.randint(r + 30, self.hc - 120)
                if self._free(cx - a - 3, cy - r - 3, cx + a + 3, cy + r + 3):
                    out.append(self.planet(cx, cy, r, bands, ring=ring, craters=(kind == 'rocky')))
                    self.occupy(cx - a - 3, cy - r - 3, cx + a + 3, cy + r + 3); break
        return ''.join(out)

    def shooting(self):
        rnd = random.Random(self.seed + 8); out = []
        for i, (yf, dur, begin) in enumerate([(0.05, 11, 2), (0.30, 14, 6), (0.58, 17, 9), (0.82, 13, 4)]):
            x0 = rnd.randint(250, 430) * U; y0 = int(self.hc * yf) * U
            dx, dy, mv = -110 * U // 1, 55 * U // 1, 1.3 / dur
            segs = [(1, 3, '#dfe8ff'), (4, 7, '#9fb4e8'), (8, 11, '#5a6ea8'), (12, 15, '#2b3866')]
            g = px.P({(0, 0), (1, 0), (0, 1), (1, 1)}, '#ffffff')
            for a, b, col in segs: g += px.P({(i_, -(i_ // 2)) for i_ in range(a, b + 1)} | {(i_ + 1, -(i_ // 2)) for i_ in range(a, b + 1)}, col)
            out.append(f'<g transform="translate({x0} {y0})" opacity="0"><g>{g}'
                       f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx} {dy};{dx} {dy}" keyTimes="0;{mv:.4f};1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/></g>'
                       f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.001;{mv*0.85:.4f};{mv:.4f};1" calcMode="discrete" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/></g>')
        return ''.join(out)

    def render(self):
        W, H = self.wc * U, self.hc * U
        px.SKY[:] = sky_colors(self.theme, 36)
        body, deco = [self._sky()], ''
        if self.theme == 'dark':
            deco = self.deco_dark()
            grid = self.mask()
            deco = self.aurora(grid, [(26, 20, 84, 0.66, 0.5), (self.hc - 210, 14, 70, 0.46, 2.2), (self.hc * 0.48, 16, 64, 0.28, 4.0)]) + deco
            body += [deco, self._stars(), self.shooting()]
        else:
            body.append(self.clouds(self.hc // 36))
        body += self.content
        defs = f'<defs>{"".join(self.defs)}</defs>\n' if self.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
                f'shape-rendering="crispEdges" role="img" aria-label="Lavdeep Singh, one page pixel profile">\n{defs}'
                + '\n'.join(b for b in body if b) + '\n</svg>')


def disc(cx, cy, r):
    return {(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r * 0.6}


# --------------------------------------------------------------------------- avatar
AV_COLS, AV_ROWS, AV_ROW0 = 69, 69, 4
AV_B, AV_P = (26.34, 26.2), (16.5, 17.5)
_AV = {}
def avatar_cells():
    if _AV: return _AV
    jp = os.path.join(HERE, 'avatar_cells.json')
    if os.path.exists(jp):
        _AV.update({c: {tuple(p) for p in v} for c, v in json.load(open(jp)).items()}); return _AV
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'avatar.png')).convert('RGB')); H, W, _ = a.shape
    flat = Image.new('RGB', (AV_COLS, AV_ROWS)); data = []
    for j in range(AV_ROWS):
        for i in range(AV_COLS):
            cx = AV_P[0] + (i + 0.5) * AV_B[0]; cy = AV_P[1] + (AV_ROW0 + j - 0.5) * AV_B[1]
            data.append(tuple(int(v) for v in np.median(a[int(max(0, cy - 6)):int(min(H, cy + 7)), int(max(0, cx - 6)):int(min(W, cx + 7))].reshape(-1, 3), axis=0)))
    flat.putdata(data)
    q = flat.quantize(colors=28, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    for j in range(AV_ROWS):
        for i in range(AV_COLS): _AV.setdefault(px._hex(q.getpixel((i, j))), set()).add((i, j))
    json.dump({c: sorted(v) for c, v in _AV.items()}, open(jp, 'w'), separators=(',', ':'))
    return _AV
_SUBJ = {}
def avatar_subject():
    """Cuts the figure out of the avatar's purple background (flood fill from the edges, stopped by the black outline)."""
    if _SUBJ: return _SUBJ
    N = AV_COLS; grid = [[None] * N for _ in range(AV_ROWS)]
    for col, cells in avatar_cells().items():
        for i, j in cells: grid[j][i] = col
    def rgb(h): return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
    def is_bg(col):
        r, g, b = rgb(col); luma = .3 * r + .59 * g + .11 * b
        return b - r >= 7 and 25 <= luma <= 95
    bg, stack = set(), [(i, j) for j in range(AV_ROWS) for i in range(N) if (i in (0, N - 1) or j in (0, AV_ROWS - 1)) and is_bg(grid[j][i])]
    while stack:
        i, j = stack.pop()
        if (i, j) in bg: continue
        bg.add((i, j))
        for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = i + a, j + b
            if 0 <= x < N and 0 <= y < AV_ROWS and (x, y) not in bg and is_bg(grid[y][x]): stack.append((x, y))
    subj = {(i, j) for j in range(AV_ROWS) for i in range(N)} - bg
    comps, seen = [], set()                              # keep only the biggest connected piece (drops stray specks)
    for c0 in subj:
        if c0 in seen: continue
        comp, st = set(), [c0]
        while st:
            c_ = st.pop()
            if c_ in seen or c_ not in subj: continue
            seen.add(c_); comp.add(c_)
            st += [(c_[0] + a, c_[1] + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        comps.append(comp)
    subj = max(comps, key=len)
    _SUBJ.update(cells=subj, grid=grid); return _SUBJ

def avatar_svg(theme, ax, ay):
    sj = avatar_subject(); subj, grid = sj['cells'], sj['grid']; by = {}
    rim = {(i, j) for i, j in subj if any((i + a, j + b) not in subj and 0 <= i + a < AV_COLS and 0 <= j + b < AV_ROWS - 6
                                           for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for i, j in subj:
        if j >= AV_ROWS - 9 and px.bayer(i, j) >= (AV_ROWS - j) / 9.0: continue   # soft dithered fade at the bottom edge
        col = grid[j][i]
        if theme == 'dark' and (i, j) in rim and (i + j) % 2 == 0: col = '#6c78c8'   # dotted moonlight rim so the dark turban reads on a night sky
        by.setdefault(col, set()).add((i + ax, j + ay))
    cx, cy, out = ax + AV_COLS // 2, ay + 30, []
    glow = {}
    for y in range(cy - 46, cy + 46):                           # soft dithered halo behind the figure
        for x in range(cx - 46, cx + 46):
            d = math.hypot(x - cx, (y - cy) * 1.05) / 44.0
            if d >= 1: continue
            cov = (1 - d) ** 1.5 * 0.62
            if px.bayer(x, y) < cov: glow.setdefault('in' if d < 0.55 else 'out', set()).add((x, y))
    gc = {'dark': ('#323f94', '#222c70'), 'light': ('#fffaf0', '#fff1d6')}[theme]
    out.append(px.P(glow.get('out', set()), gc[1]) + px.P(glow.get('in', set()), gc[0]))
    out += [px.P(cells, col) for col, cells in by.items()]
    return ''.join(out)


# --------------------------------------------------------------------------- live data
def http_get(url, accept=None):
    h = {'User-Agent': 'pixel-profile-readme'}
    if accept: h['Accept'] = accept
    if TOKEN and 'api.github.com' in url: h['Authorization'] = f'Bearer {TOKEN}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=12) as r:
        return r.read().decode('utf-8', 'replace')

def fetch_calendar():
    html = http_get(f'https://github.com/users/{USER}/contributions')
    tips = {}
    for m in re.finditer(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        n = re.match(r'\s*(\d[\d,]*)\s+contribution', m.group(2)); tips[m.group(1)] = int(n.group(1).replace(',', '')) if n else 0
    days = []
    for m in re.finditer(r'<td\b[^>]*>', html):
        tag = m.group(0)
        if 'data-date' not in tag: continue
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tag)); idm = re.match(r'contribution-day-component-(\d+)-(\d+)', a.get('id', ''))
        if not idm: continue
        days.append(dict(date=datetime.date.fromisoformat(a['data-date']), row=int(idm.group(1)), col=int(idm.group(2)),
                         level=int(a.get('data-level', '0')), count=tips.get(a['id'], 0)))
    if not days: raise RuntimeError('no contribution cells found')
    tm = re.search(r'([\d,]+)\s+contributions\s+in\s+the\s+last\s+year', html, re.S)
    return days, int(tm.group(1).replace(',', '')) if tm else sum(d['count'] for d in days)

def streak(days):
    by = {d['date']: d['count'] for d in days}; d = datetime.datetime.now(datetime.timezone.utc).date()
    if not by.get(d): d -= datetime.timedelta(days=1)
    n = 0
    while by.get(d, 0) > 0: n += 1; d -= datetime.timedelta(days=1)
    return n

def fetch_activity():
    try:
        repos = [r for r in json.loads(http_get(f'https://api.github.com/users/{USER}/repos?sort=pushed&per_page=15&type=owner')) if not r.get('fork')]
    except Exception as e:
        print('repo list failed:', e); return [], []
    recent = [dict(name=r['name'], lang=r.get('language') or '', date=r['pushed_at'][:10]) for r in repos[:3]]; commits = []
    for r in repos[:5]:
        try:
            for c in json.loads(http_get(f"https://api.github.com/repos/{USER}/{r['name']}/commits?author={USER}&per_page=3")):
                commits.append(dict(repo=r['name'], msg=c['commit']['message'].split('\n')[0], date=c['commit']['author']['date'][:10]))
        except Exception as e: print('commits failed for', r['name'], e)
    commits.sort(key=lambda c: c['date'], reverse=True)
    return commits[:4], recent

def get_live():
    snap = json.load(open(os.path.join(HERE, 'live_snapshot.json')))
    live = dict(total=snap['total'], streak=snap['streak'], cols=snap['cols'], cells=[tuple(c) for c in snap['cells']],
                updated=datetime.date.fromisoformat(snap['updated']), commits=[], repos=[], source='snapshot')
    if os.environ.get('LIVE_NO_API') == '1': return live
    try:
        days, total = fetch_calendar(); commits, repos = fetch_activity()
        live.update(total=total, streak=streak(days), cols=max(d['col'] for d in days) + 1,
                    cells=[(d['col'], d['row'], d['level']) for d in days if d['level'] > 0],
                    updated=datetime.datetime.now(datetime.timezone.utc).date(), commits=commits, repos=repos, source='live')
    except Exception as e:
        print('live fetch failed, using snapshot:', e)
    print('live data source:', live['source'])
    return live

def fmt(date_str):
    d = datetime.date.fromisoformat(date_str); return f'{d.day} {MON[d.month - 1]}'


# --------------------------------------------------------------------------- scenery
SCN = {
    'light': dict(back='#a9ecb8', front='#4cc06b', edge='#8fe39f', trunk='#8a5a2b', leaf=('#2f9e57', '#4cc06b', '#1f7a46'),
                  tower='#f6f9fc', tshade='#a9bfd6', blade='#ffffff', bshade='#8fa9c4'),
    'dark': dict(back='#121c44', front='#1a2858', edge='#3a52a8', trunk='#2a2450', leaf=('#14404f', '#22657a', '#0d2d38'),
                 tower='#8f9bc4', tshade='#4b5a86', blade='#cfd8f5', bshade='#4b5a86'),
}

def line_cells(x0, y0, ang, n):
    return {(round(x0 + i * math.cos(ang)), round(y0 + i * math.sin(ang))) for i in range(1, n + 1)}

def tree(s, x, ty, rnd):
    c = SCN[s.theme]; out = []
    if rnd.random() < 0.55:                                    # round tree
        r = rnd.randint(4, 6); th = rnd.randint(3, 5)
        out.append(px.P({(x + a, ty - b) for a in (0, 1) for b in range(th)}, c['trunk']))
        cy = ty - th - r + 1; blob = disc(x, cy, r)
        out.append(px.P(blob, c['leaf'][0]))
        out.append(px.P({(a, b) for a, b in blob if (a - x) + (b - cy) < -r * 0.6}, c['leaf'][1]))
        out.append(px.P({(a, b) for a, b in blob if (a - x) + (b - cy) > r * 0.9}, c['leaf'][2]))
        box = (x - r - 1, cy - r - 1, x + r + 2, ty + 1)
    else:                                                      # pine
        h = rnd.randint(11, 17); out.append(px.P({(x + a, ty - b) for a in (0, 1) for b in range(3)}, c['trunk']))
        cells, hi = set(), set()
        for k in range(h):
            half = 1 + int(k * 0.42) if k < h - 1 else 0
            half = min(half, 5)
            for dx in range(-half, half + 2): cells.add((x + dx, ty - 3 - (h - 1 - k)))
        for a, b in cells:
            if a - x < 0: hi.add((a, b))
        out.append(px.P(cells, c['leaf'][2])); out.append(px.P({(a, b) for a, b in cells if a <= x and (a + b) % 2 == 0} | {(a, b) for a, b in hi if (a + b) % 3 == 0}, c['leaf'][0]))
        box = (x - 7, ty - 3 - h, x + 8, ty + 1)
    s.add(''.join(out)); s.occupy(*box)

def turbine(s, x, ty, rnd):
    c = SCN[s.theme]; h = rnd.choice([16, 19, 22]); bl = rnd.choice([7, 8, 9]); hy = ty - h
    tower = {(x + a, ty - b) for a in (0, 1) for b in range(h)}
    s.add(px.P(tower, c['tower']) + px.P({(x + 1, ty - b) for b in range(h)}, c['tshade']))
    s.add(px.P({(x - 1, hy - 1), (x, hy - 1), (x - 1, hy), (x, hy), (x + 1, hy), (x + 1, hy - 1)}, c['tshade']))
    dur = rnd.uniform(1.5, 2.3); begin = rnd.uniform(0, 1.5); frames = []
    for k in range(4):
        cells, sh = set(), set()
        for m in range(3):
            ang = math.radians(-90 + 30 * k + 120 * m)
            ln = line_cells(x, hy, ang, bl); cells |= ln; sh |= {(a + 1, b + 1) for a, b in ln}
        vals = ';'.join('1' if i == k else '0' for i in range(4))
        anim = (f'<animate attributeName="opacity" values="{vals}" keyTimes="0;0.25;0.5;0.75" calcMode="discrete" '
                f'dur="{dur:.2f}s" begin="-{begin:.2f}s" repeatCount="indefinite"/>')
        frames.append(f'<g opacity="{1 if k == 0 else 0}">{anim}{px.P(sh - cells, c["bshade"])}{px.P(cells, c["blade"])}</g>')
    s.add(''.join(frames))
    if s.theme == 'dark':
        s.add(f'<path d="{px.path_d({(x - 1, hy - 2), (x, hy - 2)})}" fill="#ff5f57">{s.blink(1.0, 1.6, rnd)}</path>')
    s.occupy(x - bl - 2, hy - bl - 2, x + bl + 3, ty + 2)

def strip(s, y, idx):
    """A grass ledge with trees and turbines. Returns the y where the next section starts."""
    c = SCN[s.theme]; rnd = random.Random(300 + idx); yb = y + 30; ph = rnd.uniform(0, 6)
    ftop = lambda x: int(yb - (4 + 3.0 * math.sin(x / 36 + ph) + 1.5 * math.sin(x / 12 + ph)))
    btop = lambda x: int(yb - (10 + 5.0 * math.sin(x / 58 + ph + 1) + 2 * math.sin(x / 21)))
    for top, col, base in ((btop, c['back'], yb + 2), (ftop, c['front'], yb + 4)):
        cells = set()
        for x in range(s.wc):
            for yy in range(top(x), base + 8):
                if yy <= base or px.bayer(x, yy) < 1 - (yy - base) / 8: cells.add((x, yy))
        s.add(px.P(cells, col))
    s.add(px.P({(x, ftop(x)) for x in range(s.wc)}, c['edge']))
    placed = []
    n_turb = {0: 0, 1: 2, 2: 3, 3: 0, 4: 1, 5: 2, 6: 0}.get(idx, 1)
    n_tree = {0: 5, 1: 3, 2: 3, 3: 6, 4: 5, 5: 3, 6: 6}.get(idx, 4)
    for kind, n in (('t', n_turb), ('r', n_tree)):
        tries = 0
        while n and tries < 80:
            tries += 1; x = rnd.randint(34, R - 6)
            if any(abs(x - p) < (30 if kind == 't' else 20) for p in placed): continue
            placed.append(x); n -= 1
            (turbine if kind == 't' else tree)(s, x, ftop(x) + 1, rnd)
    s.occupy(0, yb - 12, s.wc, yb + 14)
    return yb + 16


# --------------------------------------------------------------------------- walker
SPR = ["..tttt..", ".tttttt.", "tttttttt", "tttttttt", ".ssssss.", ".gggggg.", ".ssssss.", ".bbbbbb.", ".hhhhhh.", "hhhhhhhh", ".hhhhhh."]
LEGS = (["..l..l..", "..l..l.."], ["...ll...", "...ll..."])
def sprite_cells(frame, theme):
    pal = dict(t='#2a2a33' if theme == 'light' else '#4a4a66', s='#e0a67a', g='#0b0b10', b='#1a1a22',
               h='#067a53' if theme == 'light' else CORAL, l='#394156' if theme == 'light' else '#7d8da8')
    by = {}
    for r, row in enumerate(SPR + list(LEGS[frame])):
        for cc, ch in enumerate(row):
            if ch != '.': by.setdefault(pal[ch], set()).add((TRACK - 4 + cc, r))
    return by

def walker(s, nodes):
    speed, hold = 42.0, 2.2
    ev, t = [(0.0, nodes[0])], 0.0
    ev.append((hold, nodes[0])); t = hold
    for a, b in zip(nodes, nodes[1:]):
        t += abs(b - a) / speed; ev.append((t, b)); t += hold; ev.append((t, b))
    T = t + 0.6; ev.append((T, nodes[-1]))
    vals = ';'.join(f'0 {(y - 17) * U}' for _, y in ev); kts = ';'.join(f'{tm / T:.4f}' for tm, _ in ev)
    frames = []
    for f in (0, 1):
        body = ''.join(px.P(cells, col) for col, cells in sprite_cells(f, s.theme).items())
        v = '1;0' if f == 0 else '0;1'
        frames.append(f'<g opacity="{1 if f == 0 else 0}"><animate attributeName="opacity" values="{v}" keyTimes="0;0.5" calcMode="discrete" dur="0.5s" repeatCount="indefinite"/>{body}</g>')
    s.add(f'<g><animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{kts}" dur="{T:.1f}s" repeatCount="indefinite"/>{"".join(frames)}</g>')


# --------------------------------------------------------------------------- page
def hills(s, top):
    layers = {'light': ['#7be08f', '#4cc06b', '#2f9e57'], 'dark': ['#0d1330', '#141d44', '#1c2a5e']}[s.theme]
    for i, col in enumerate(layers):
        cells = set()
        for x in range(s.wc):
            h = 9 + 5 * math.sin(x / (31 + i * 9) + i * 1.7) + 2.5 * math.sin(x / (11 + i * 3) + i)
            for y in range(int(top + i * 7 - h + 6), s.hc): cells.add((x, y))
        s.add(px.P(cells, col))
    s.occupy(0, top - 14, s.wc, s.hc)


def layout(s, live):
    c = s.c; nodes = []; rnd = random.Random(s.seed + 1)

    def cpl(x): return max(8, (R - x + 1) // 6)

    def heading(n, title, color, y):
        nodes.append(y + 6)
        s.add(px.P(px.cut_rect(TRACK - 2, y + 5, TRACK + 2, y + 9, [0]), c(color)))
        sh = px.shade(c(color), 0.38) if s.theme == 'dark' else px.shade(c(color), 1.9)
        s.add(px.P(px.text_cells(px.safe(title), L + 1, y + 1, 2), sh))
        s.text(title, L, y, 2, color)
        s.text_r(f'{n:02d} / {TOTAL:02d}', R, y + 4, 1, 'dim')
        s.dotted(L, R, y + 19)
        return y + 28

    def kv(label, value, y, lc='cyan', vc='ink', col=72):
        s.text(label, L, y, 1, lc); s.text(':', L + col - 9, y, 1, 'dim')
        lines = px.wrap(value, cpl(L + col))
        for i, l in enumerate(lines): s.text(l, L + col, y + i * LINE, 1, vc)
        return y + len(lines) * LINE

    # ---------------------------------------------------------------- hero
    y0 = 20; ay = y0 + 8
    s.add(avatar_svg(s.theme, L, ay)); s.occupy(L - 1, ay - 1, L + AV_COLS + 1, ay + AV_ROWS + 1)
    hx = L + AV_COLS + 18
    s.text('COMPUTER ENGINEERING . THAPAR INSTITUTE', hx, y0 + 2, 1, 'dim')
    name = px.safe('LAVDEEP SINGH')
    s.add(px.P(px.text_cells(name, hx + 1, y0 + 15, 3), c('cyan')))
    s.text(name, hx, y0 + 13, 3, 'strong')
    ty = y0 + 41; tag = px.safe('> NOTEBOOKS INTO THINGS THAT RUN'); n = len(tag); step, T = 12, 14.0   # typing effect
    t_ev = [(0.0, 0)] + [(0.5 + 0.08 * i, i * step) for i in range(1, n + 1)] + [(11.0, 0), (T, 0)]
    kt = ';'.join(f'{t / T:.4f}' for t, _ in t_ev)
    s.defs.append(f'<clipPath id="tc"><rect x="{hx * U}" y="{ty * U - 2}" width="{n * step}" height="{8 * U + 4}">'
                  f'<animate attributeName="width" values="{";".join(str(w) for _, w in t_ev)}" keyTimes="{kt}" calcMode="discrete" dur="{T}s" repeatCount="indefinite"/></rect></clipPath>')
    s.add(f'<g clip-path="url(#tc)">{px.P(px.text_cells(tag, hx, ty, 1), c("green"))}</g>')
    s.occupy(hx - 1, ty - 1, hx + px.tw(tag) + 12, ty + 8)
    cur = px.path_d(px.cut_rect(0, ty, 5, ty + 7))
    s.add(f'<path d="{cur}" fill="{c("green")}" transform="translate({(hx + n * 6 + 3) * U} 0)">'
          f'<animateTransform attributeName="transform" type="translate" values="{";".join(f"{hx * U + w + 6} 0" for _, w in t_ev)}" keyTimes="{kt}" calcMode="discrete" dur="{T}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="1;0.15;1" keyTimes="0;0.5;0.75" calcMode="discrete" dur="0.9s" repeatCount="indefinite"/></path>')
    s.text('ML . DATA . RESEARCH . SOFTWARE', hx, ty + 14, 1, 'dim')
    s.text('DEGREE.EXE . CLASS OF 2028', hx, ty + 28, 1, 'ink')
    bx, by, bw = hx, ty + 40, 130
    s.add(px.P(px.cut_rect(bx, by, bx + bw, by + 6, [1]), c('border')))
    s.add(px.P(px.cut_rect(bx + 1, by + 1, bx + bw - 1, by + 5, [0]), c('empty')))
    s.add(px.P(px.cut_rect(bx + 1, by + 1, bx + 1 + int((bw - 2) * .55), by + 5, [0]), c('green')))
    s.text('55%', bx + bw + 6, by - 1, 1, 'green')
    cx, cy = 404, y0 + 20
    if s.theme == 'light':
        s.add(px.P(disc(cx, cy, 10), '#ff9f1c') + px.P(disc(cx, cy, 8), '#ffd23f') + px.P(disc(cx - 2, cy - 2, 4), '#fff0a6'))
        rays = set()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            for i in range(14, 19):
                for a in (0, 1): rays.add((cx + dx * i + (a if dx == 0 else 0), cy + dy * i + (a if dy == 0 else 0)))
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            for i in (11, 12, 13): rays |= {(cx + dx * i + a, cy + dy * i + b) for a in (0, 1) for b in (0, 1)}
        s.add(f'<path d="{px.path_d(rays)}" fill="#ffb703"><animate attributeName="opacity" values="1;0.55;1" dur="3.2s" repeatCount="indefinite"/></path>')
        s.occupy(cx - 22, cy - 22, cx + 22, cy + 22)
    else:
        moon = disc(cx, cy, 10); shade = moon - disc(cx + 4, cy - 3, 9)
        s.add(px.P(moon, '#f1f4ff') + px.P(shade, '#aab6dc'))
        s.add(px.P(disc(cx - 5, cy + 3, 2) | disc(cx - 2, cy - 5, 1) | disc(cx - 6, cy - 3, 1), '#8f9bc4'))
        s.occupy(cx - 14, cy - 14, cx + 14, cy + 14)
    y = y0 + 76 + 26

    # ---------------------------------------------------------------- 01 at a glance
    y = heading(1, 'AT A GLANCE', 'green', y)
    s.text('FOR RECRUITERS', L, y, 1, 'gold'); y += 14
    y = kv('FOCUS', 'ML, DATA AND RESEARCH', y)
    y = kv('DEGREE', 'B.TECH COMPUTER ENGINEERING, TIET', y)
    y = kv('BATCH', 'CLASS OF 2028', y)
    y = kv('OPEN FIRST', 'ENERLYTICS AI, SEE PROJECTS BELOW', y)
    y += 9
    s.text('FOR DEVELOPERS', L, y, 1, 'gold'); y += 14
    y = kv('START WITH', 'ACADHUB, THE SCHEMA: 12 ENTITIES, TRIGGERS, VIEWS, PROCEDURES', y)
    y = kv('THEN', 'ENERLYTICS AI: PCA + K-MEANS PIPELINE, STREAMLIT DASHBOARD', y)
    y = kv('ALSO', 'SO DUPLICATE DETECTION: SENTENCE-BERT, K-MEANS, DBSCAN', y)
    y = kv('WORKING ON', 'CODE I CAN EXPLAIN LINE BY LINE', y)
    y = kv('WELCOME', 'HONEST CODE REVIEW', y)
    y = strip(s, y + 4, 0)

    # ---------------------------------------------------------------- 02 achievements
    y = heading(2, 'ACHIEVEMENTS', 'gold', y)
    items = [('paper', 'PUBLISHED . IEEE', 'COMPUTINGCON 2025', 'DIABETES PREDICTION'), ('trophy', 'WINNER', 'NIOHACK 2026', 'HACKATHON'),
             ('trophy', 'WINNER', 'QUANTUMHACKS 2026', 'HACKATHON'), ('flag', 'FINALIST', 'OOSC 4.0', 'IIIT ALLAHABAD'),
             ('medal', 'TOP 10', 'HACKMOL 6.0', 'HACKATHON'), ('bulb', 'FELLOW', 'RESEARCH FELLOWSHIP', 'UNDERGRAD . NLP'),
             ('star', 'AMBASSADOR', 'GOOGLE GEMINI', 'STUDENT AMBASSADOR'), ('shield', 'REPRESENTATIVE', 'STUDENT PLACEMENT REP', 'TIET')]
    spark_col = '#ff9f1c' if s.theme == 'light' else '#fff3b0'
    for i, (ic, lab, title, sub) in enumerate(items):
        x = L + (i % 2) * 212; yy = y + (i // 2) * 38
        s.add(px.P(px.icon_cells(ic, x, yy + 1, 2), c('gold'))); s.occupy(x - 1, yy, x + 17, yy + 18)
        if ic in ('trophy', 'star', 'medal', 'paper'):
            for k, (sx, sy) in enumerate(((x + 19, yy - 1), (x - 4, yy + 11))):
                plus = {(sx, sy), (sx - 1, sy), (sx + 1, sy), (sx, sy - 1), (sx, sy + 1)}
                s.add(f'<path d="{px.path_d(plus)}" fill="{spark_col}">{s.blink(1.6, 3.2, rnd)}</path>')
        s.text(lab, x + 24, yy, 1, 'gold'); s.text(title, x + 24, yy + 11, 1, 'strong'); s.text(sub, x + 24, yy + 22, 1, 'dim')
    y = strip(s, y + 4 * 38 - 4, 1)

    # ---------------------------------------------------------------- 03 projects
    y = heading(3, 'PROJECTS', 'cyan', y)
    projects = [
        ('ENERLYTICS AI', 'green', '52,585 BUILDINGS . 4 CLUSTERS . $0.3M FLAGGED', 'PCA . K-MEANS . ANOMALY DETECTION . STREAMLIT',
         'SMART BUILDINGS BURN ENERGY IN PATTERNS NOBODY HAS LABELLED.',
         'PCA + K-MEANS BEHAVIOURAL SEGMENTATION, ANOMALY DETECTION, STREAMLIT ANALYTICS DASHBOARD.',
         '4 BEHAVIOURAL CLUSTERS AND OPTIMIZATION INSIGHTS WORTH UP TO $0.3M IN POTENTIAL SAVINGS.'),
        ('ACADHUB', 'cyan', '12 ENTITIES . ROLE-BASED ACCESS . 10+ REPORTS', 'MYSQL . PL/SQL . TRIGGERS . VIEWS . TRANSACTIONS',
         'LMS, WEBKIOSK AND PREVIOUS-YEAR PAPERS LIVE IN THREE DIFFERENT PLACES.',
         'MYSQL AND PL/SQL: PROCEDURES, TRIGGERS, VIEWS AND TRANSACTIONS.',
         'ONE PLATFORM WITH 12 INTERCONNECTED ENTITIES, ROLE-BASED ACCESS CONTROL AND 10+ ACADEMIC ANALYTICS REPORTS.'),
        ('SO DUPLICATE DETECTION', 'purple', 'TF-IDF . SENTENCE-BERT . K-MEANS . DBSCAN', 'TF-IDF . SENTENCE-BERT . K-MEANS . DBSCAN',
         'WHICH PROGRAMMING QUESTIONS ARE SECRETLY THE SAME QUESTION?',
         'TF-IDF BASELINE, SENTENCE-BERT EMBEDDINGS, K-MEANS AND DBSCAN CLUSTERING.',
         'AN UNSUPERVISED PIPELINE EVALUATED ON CLUSTER PURITY AND RECALL. MY UNDERGRADUATE RESEARCH FELLOWSHIP PROJECT.'),
        ('DIABETES PREDICTION', 'gold', '94.6% ACCURACY . 92.9% F1 . IEEE PUBLISHED', 'SPARSE PCA . RANDOM FOREST . XGBOOST',
         'BETTER PREDICTION WITH FEWER FEATURES.', 'SPARSE PCA, RANDOM FOREST, XGBOOST, CATBOOST, OPTUNA.',
         '94.6% ACCURACY, 92.9% F1, AND AN IEEE CONFERENCE PUBLICATION AT COMPUTINGCON 2025.'),
    ]
    for name_, col, stats, skills, prob, appr, res in projects:
        s.add(px.P(px.cut_rect(L - 11, y + 4, L - 7, y + 8), c(col)))
        s.text(name_, L, y, 2, col); y += 20
        if stats != skills: s.text(stats, L, y, 1, col); y += 14
        y = kv('SKILLS', skills, y, lc='dim', vc='dim'); y += 3
        y = kv('PROBLEM', prob, y, lc='dim'); y = kv('APPROACH', appr, y, lc='dim'); y = kv('RESULT', res, y, lc='dim')
        y += 16
    s.add(px.P(px.cut_rect(L - 11, y + 4, L - 7, y + 8), c('grey')))
    s.text('EV BATTERY RUL', L, y, 2, 'strong'); y += 20
    s.text('REMAINING USEFUL LIFE PREDICTION', L, y, 1, 'grey'); y += 14
    y = kv('STATUS', 'RESEARCH IN PROGRESS', y, lc='dim')
    y = strip(s, y + 2, 2)

    # ---------------------------------------------------------------- 04 timeline
    y = heading(4, 'TIMELINE', 'purple', y)
    s.text('GIT LOG --GRAPH . AUG 2024 TO NOW', L, y, 1, 'dim'); y += 16
    rows = [('AUG 2024', 'JOINED THAPAR INSTITUTE', 0), ('APR 2025', 'HACKMOL 6.0 . TOP 10', 0),
            ('SEP 2025', 'IEEE ACCEPTED . COMPUTINGCON 2025', 0), ('DEC 2025', 'IEEE PAPER PUBLISHED', 0),
            ('JAN 2026', 'UNDERGRAD RESEARCH FELLOWSHIP', 0), ('JUN 2026', 'GOOGLE GEMINI STUDENT AMBASSADOR', 0),
            ('AUG 2026', 'OOSC 4.0 FINALIST . IIIT ALLAHABAD', 1), ('AUG 2026', 'QUANTUMHACKS 2026 . WINNER', 1),
            ('SEP 2026', 'NIOHACK 2026 . WINNER', 1), ('SEP 2026', 'STUDENT PLACEMENT REPRESENTATIVE', 1)]
    ty0 = y; TT = 12.0
    for i, (d, e, hot) in enumerate(rows):
        yy = y + i * 13
        halo = px.P(px.cut_rect(L - 1, yy - 1, L + 7, yy + 9, [1]), c('gold' if hot else 'purple'))
        tt = 0.4 + i * 0.45
        s.add(f'<g opacity="0">{halo}<animate attributeName="opacity" values="0;0.45;0" keyTimes="0;{tt / TT:.4f};{(tt + 0.35) / TT:.4f}" calcMode="discrete" dur="{TT}s" repeatCount="indefinite"/></g>')
        s.add(px.P(px.cut_rect(L + 1, yy + 2, L + 5, yy + 6), c('gold' if hot else 'purple')))
        s.text(d, L + 12, yy, 1, 'gold' if hot else 'dim'); s.text(e, L + 72, yy, 1, 'gold' if hot else 'ink')
    y += len(rows) * 13
    s.text('+ FOUR MILESTONES IN TWO MONTHS', L + 72, y - 2, 1, 'gold'); y += 13
    s.add(px.P(px.cut_rect(L + 1, y + 2, L + 5, y + 6), c('green')))
    s.text('NOW', L + 12, y, 1, 'green'); s.text('HEAD . NEXT: ???', L + 72, y, 1, 'strong')
    s.add(px.P({(L + 2, yy2) for yy2 in range(ty0 + 4, y + 2) if yy2 % 4 != 3}, c('divider')))
    y = strip(s, y + 11, 3)

    # ---------------------------------------------------------------- 05 stack
    y = heading(5, 'STACK', 'green', y)
    groups = [('LANGUAGE', 'green', ['PYTHON', 'C++', 'C', 'JAVA', 'SQL', 'PL/SQL']), ('ML', 'cyan', ['SCIKIT-LEARN', 'PANDAS', 'NUMPY', 'TENSORFLOW']),
              ('NLP', 'cyan', ['SENTENCE-BERT', 'TF-IDF']), ('ENSEMBLE', 'purple', ['K-MEANS', 'DBSCAN', 'RANDOM FOREST', 'XGBOOST', 'CATBOOST', 'OPTUNA']),
              ('TOOLS', 'purple', ['GIT', 'GITHUB', 'JUPYTER', 'STREAMLIT', 'MYSQL'])]
    for lab, col, its in groups:
        s.text(lab, L, y, 1, col); x = L + 72; yy = y
        for it in its:
            w = px.tw(px.safe(it)) + 10
            if x + w > R: x = L + 72; yy += LINE + 2
            s.add(px.P(px.cut_rect(x, yy + 2, x + 3, yy + 5), c(col))); s.text(it, x + 7, yy, 1, 'ink'); x += w + 8
        y = yy + LINE + 8
    y = strip(s, y, 4)

    # ---------------------------------------------------------------- 06 k-means on me
    y = heading(6, 'K-MEANS, BUT ON ME', 'gold', y); ys = y
    clusters = [('0', 'RESEARCH', 'purple', 'NLP, SEMANTIC REPRESENTATIONS, CLUSTERING'), ('1', 'BUILD', 'green', 'ML SYSTEMS, DATA PROJECTS, DASHBOARDS'),
                ('2', 'COMPETE', 'gold', 'HACKATHONS, FINALS, ONE MORE FEATURE AT 3AM'), ('3', 'FUNDAMENTALS', 'cyan', 'DSA, C++, SOFTWARE ENGINEERING')]
    for n_, nm, col, desc in clusters:
        s.text(f'CLUSTER {n_} . {nm}', L, y, 1, col); y += 12
        for l in px.wrap(desc, (290 - L) // 6): s.text(l, L, y, 1, 'dim'); y += LINE
        y += 6
    s.dotted(L, 290, y); y += 8
    for lab, val in (('INERTIA', 'HIGH'), ('SILHOUETTE SCORE', 'STILL TUNING'), ('OPTIMAL K', 'ASK ME AGAIN NEXT SEMESTER')):
        s.text(lab, L, y, 1, 'strong'); s.text(':', L + 17 * 6, y, 1, 'dim'); s.text(val, L + 18 * 6 + 4, y, 1, 'ink'); y += LINE
    r2 = random.Random(7); mid = (ys + y) // 2; s.occupy(300, ys - 4, R, y + 4)
    for cx, cy, col in [(332, mid - 38, 'purple'), (392, mid - 30, 'green'), (336, mid + 26, 'gold'), (394, mid + 30, 'cyan')]:
        pts = set()
        for _ in range(60):
            a_, b_ = int(r2.gauss(0, 4.2)), int(r2.gauss(0, 4.2))
            for p in (0, 1):
                for q in (0, 1): pts.add((cx + a_ + p, cy + b_ + q))
        s.add(px.P(pts, c(col))); s.add(px.P(px.text_cells('+', cx - 2, cy - 3, 1), c('strong')))
    y = strip(s, y + 2, 5)

    # ---------------------------------------------------------------- 07 live activity
    y = heading(7, 'LIVE ACTIVITY', 'green', y)
    u = live['updated']; s.text(f'UPDATED {u.day} {MON[u.month - 1]} {u.year}', L, y, 1, 'dim'); y += 15
    s.text('CURRENT STREAK', L, y, 1, 'dim'); s.text('12 MONTH TOTAL', L + 200, y, 1, 'dim'); y += 11
    s.text(f'{live["streak"]} DAYS', L, y, 3, 'strong'); s.text(f'{live["total"]}', L + 200, y, 3, 'strong'); y += 30
    s.dotted(L, R, y); y += 9
    s.text('LATEST COMMITS', L, y, 1, 'cyan'); y += 13
    if live['commits']:
        for cm in live['commits']:
            s.text(px.clip(cm['repo'], 30), L, y, 1, 'green'); s.text_r(fmt(cm['date']), R, y, 1, 'dim')
            s.text(px.clip(cm['msg'], 66), L, y + 10, 1, 'ink'); y += 22
    else:
        s.text('NO COMMIT DATA YET', L, y, 1, 'ink'); s.text('RUN THE UPDATE ACTION ONCE', L, y + 10, 1, 'dim'); y += 22
    y += 4; s.text('RECENTLY UPDATED REPOS', L, y, 1, 'purple'); y += 13
    if live['repos']:
        for r_ in live['repos']:
            s.text(px.clip(r_['name'], 34), L, y, 1, 'ink'); s.text(px.clip(r_['lang'], 12), L + 230, y, 1, 'dim'); s.text_r(fmt(r_['date']), R, y, 1, 'dim'); y += 11
    else:
        s.text('NO REPO DATA YET', L, y, 1, 'dim'); y += 11
    y += 12; s.dotted(L, R, y); y += 9
    s.text('CONTRIBUTION INVADERS', L, y, 1, 'gold'); s.text_r('A PIXEL SHIP SHOOTS DOWN THE LAST 12 MONTHS', R, y, 1, 'dim'); y += 15
    game(s, live, y); y += 7 * 7 + 6 + 12
    y = strip(s, y, 6)

    # ---------------------------------------------------------------- 08 contact
    y = heading(8, 'CONTACT', 'cyan', y)
    y = kv('LINKEDIN', 'LINKEDIN.COM/IN/LAVDEEP-SINGH-109802210', y, lc='gold', vc='cyan') + 3
    y = kv('GITHUB', 'GITHUB.COM/LAVDEEPSINGH23', y, lc='gold', vc='cyan') + 3
    y = kv('EMAIL', 'ITS.LAVDEEP.SINGH@GMAIL.COM', y, lc='gold', vc='cyan') + 14
    end = s.text('> THANKS FOR READING', L, y, 1, 'green')
    s.add(f'<path d="{px.path_d(px.cut_rect(end + 3, y, end + 8, y + 7))}" fill="{c("green")}">{s.blink(0.9, 1.1)}</path>')
    y += 8

    # the path down the left side, and the walker that visits each section
    s.add(px.P({(xx, yy) for xx in (TRACK - 1, TRACK) for yy in range(nodes[0], nodes[-1]) if yy % 6 < 4}, c('divider')))
    walker(s, nodes)
    return y


LEVELS = {'dark': ['#5b2a5e', '#9a3a7c', '#e0527a', '#ff8a7a'], 'light': ['#8fdcb8', '#4cc79a', '#1f9f6c', '#0a7f55']}

def game(s, live, y0):
    pitch, body, cols = 7, 5, live['cols']; gw = cols * pitch - 2
    x0 = L + (R - L - gw) // 2; ys = y0 + 7 * pitch + 6; t = s.t; theme = s.theme
    s.occupy(x0 - 1, y0 - 1, x0 + gw + 1, ys + 9)
    box = lambda col, row: {(x0 + col * pitch + a, y0 + row * pitch + b) for a in range(body) for b in range(body)}
    allc = set()
    for col in range(cols):
        for row in range(7): allc |= box(col, row)
    if theme == 'light': s.add(px.P(allc, '#ffffff').replace('/>', ' fill-opacity="0.5"/>'))
    else: s.add(px.P(allc, t['empty']))
    targets = {}
    for col, row, lvl in live['cells']: targets.setdefault(col, []).append(row)
    shots = [(cc, r) for cc in sorted(targets) for r in sorted(targets[cc], reverse=True)]
    dt = min(0.22, 36.0 / max(len(shots), 1)); tt, last, sched = 1.0, None, []
    for cc, r in shots:
        if last is not None and cc != last: tt += 0.05
        sched.append((cc, r, tt)); tt += dt; last = cc
    T = max(tt + 2.5, 4.0); hit = {(cc, r): ti for cc, r, ti in sched}
    for col, row, lvl in live['cells']:
        color = LEVELS[theme][min(lvl, 4) - 1]; cell = px.P(box(col, row), color)
        h = hit.get((col, row))
        if h is None: s.add(cell); continue
        k1, k2 = (h + 0.14) / T, (h + 0.23) / T
        s.add(cell.replace('/>', f'><animate attributeName="fill" values="{color};#ffffff" keyTimes="0;{k1:.4f}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>'
                              f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;{k1:.4f};{k2:.4f}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></path>'))
    ship = px.icon_cells('ship', 0, ys, 1); shipx = lambda cc: (x0 + cc * pitch + 2 - 4) * U
    if not sched:
        s.add(f'<g transform="translate({shipx(0)},0)">{px.P(ship, t["cyan"])}</g>'); return
    kts = [0.0] + [ti / T for _, _, ti in sched]; vals = [f'{shipx(sched[0][0])},0'] + [f'{shipx(cc)},0' for cc, _, _ in sched]
    s.add(f'<g>{px.P(ship, t["cyan"])}<animateTransform attributeName="transform" type="translate" calcMode="discrete" '
          f'values="{";".join(vals)}" keyTimes="{";".join(f"{k:.4f}" for k in kts)}" dur="{T:.2f}s" repeatCount="indefinite"/></g>')
    lt, lx, ly, lo = [0.0], [0], [0], [0]
    for cc, r, ti in sched:
        x = (x0 + cc * pitch + 2) * U; ysrc = (ys - 4) * U; yend = (y0 + r * pitch + 2) * U
        for dtm, yy, op in [(0.0, ysrc, 1), (0.05, (ysrc + yend) // 2, 1), (0.10, yend, 1), (0.14, yend, 0)]:
            lt.append((ti + dtm) / T); lx.append(x); ly.append(yy); lo.append(op)
    f_ = lambda v: ';'.join(str(int(a)) for a in v); ktt = ';'.join(f'{k:.4f}' for k in lt)
    s.add(f'<rect width="{U}" height="{3 * U}" fill="{t["gold"] if theme == "dark" else "#d6402a"}" opacity="0">'
          f'<animate attributeName="x" values="{f_(lx)}" keyTimes="{ktt}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>'
          f'<animate attributeName="y" values="{f_(ly)}" keyTimes="{ktt}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="{f_(lo)}" keyTimes="{ktt}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></rect>')


def build(theme, live):
    probe = Page(WC, 9000, theme, static=False, seed=5)
    end = layout(probe, live); hc = end + 52
    s = Page(WC, hc, theme, static=False, seed=5, star_div=240)
    layout(s, live)
    if theme == 'light':                                   # the sun sets behind the last hills
        cx, cy = 372, hc - 30
        sun = disc(cx, cy, 19); sun = {(x, y) for x, y in sun if not (y > cy - 6 and y % 4 == 0)}
        s.add(px.P(sun, '#ff8a3c') + px.P({(x, y) for x, y in sun if y < cy - 8 and (x - cx) + (y - cy) < -6}, '#ffb347'))
    hills(s, hc - 34)
    return s.render()


if __name__ == '__main__':
    live = get_live()
    out = os.path.join(ROOT, 'assets')
    for theme in ('light', 'dark'):
        svg = build(theme, live)
        with open(os.path.join(out, f'page-{theme}.svg'), 'w') as f: f.write(svg)
        print(theme, len(svg) // 1024, 'KB')
