#!/usr/bin/env python3
"""Builds the one-page pixel README (assets/page-light.svg and assets/page-dark.svg).
One continuous scene, no panels. Uses pxlib.py for the pixel font and themes.
Run from the repo root:  python scripts/generate_page.py
The avatar is read from assets/avatar.png (needs Pillow and numpy: pip install pillow numpy)."""
import os, re, sys, math, random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pxlib as px

U = 2                      # one pixel cell = 2 screen px (the old panels used 3, which is why text looked huge)
px.U = U
px.G['@'] = [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."]

# taller, smoother daylight gradient for the whole page
def _lerp(a, b, t):
    ra, rb = px._rgb(a), px._rgb(b)
    return px._hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))
px.SKY[:] = [_lerp('#98ccff', '#eaf7ff', i / 11) for i in range(12)]

WC = 450                   # 450 cells * 2px = 900px wide
L, R = 24, 426             # text column
TRACK = 11                 # x of the progress track that links the sections
LINE = 11                  # body line pitch
TOTAL = 7                  # number of numbered sections


class Page(px.Scene):
    def text(self, s, x, y, k=1, color='ink'):
        s = px.safe(s)
        if x + px.tw(s, k) > self.wc - 12: print('OVERFLOW:', s, x + px.tw(s, k))
        self.add(px.P(px.text_cells(s, x, y, k), self.c(color)))
        self.occupy(x - 1, y - 1, x + px.tw(s, k) + 1, y + 7 * k + 1)
        return x + px.tw(s, k)

    def clouds(self, want):
        rnd = random.Random(self.seed + 99); out = []
        for _ in range(900):
            if want <= 0: break
            w = rnd.randint(6, 12); cx = rnd.randint(w + 4, self.wc - w - 4); cy = rnd.randint(14, self.hc - 70)
            top = int(w * 0.85) + 2
            if self._free(cx - w - 2, cy - top, cx + w + 2, cy + 2):
                body, under = px.cloud_cells(cx, cy, w)
                out.append(px.P(body, '#ffffff') + px.P(under, '#cfe3f7'))
                self.occupy(cx - w - 2, cy - top, cx + w + 2, cy + 2); want -= 1
        return ''.join(out)

    def render(self):
        W, H = self.wc * U, self.hc * U
        if self.theme == 'dark':
            body = [f'<rect width="{W}" height="{H}" fill="#02030a"/>', self._stars()]
        else:
            body = [self._sky(), self.clouds(self.hc // 38)]
        body += self.content
        defs = f'<defs>{"".join(self.defs)}</defs>\n' if self.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
                f'shape-rendering="crispEdges" role="img" aria-label="Lavdeep Singh, one page pixel profile">\n{defs}'
                + '\n'.join(b for b in body if b) + '\n</svg>')


def disc(cx, cy, r):
    return {(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r * 0.6}


AV_COLS, AV_ROWS, AV_ROW0 = 69, 69, 4          # native pixel grid of assets/avatar.png (crop = head and shoulders)
AV_B, AV_P = (26.34, 26.2), (16.5, 17.5)         # block size (x, y) and grid offset (x, y) of that image
_AV_CACHE = {}

def avatar_cells():
    """Reads assets/avatar.png, samples it back down to its native pixel grid, and returns {color: cells}."""
    if _AV_CACHE: return _AV_CACHE
    from PIL import Image
    import numpy as np
    im = Image.open(os.path.join(ROOT, 'assets', 'avatar.png')).convert('RGB')
    a = np.asarray(im)
    H, W, _ = a.shape
    grid = []
    for j in range(AV_ROWS):
        row = []
        for i in range(AV_COLS):
            cx = AV_P[0] + (i + 0.5) * AV_B[0]
            cy = AV_P[1] + (AV_ROW0 + j - 0.5) * AV_B[1]
            x0, x1 = int(max(0, cx - 6)), int(min(W, cx + 7)); y0_, y1 = int(max(0, cy - 6)), int(min(H, cy + 7))
            row.append(tuple(int(v) for v in np.median(a[y0_:y1, x0:x1].reshape(-1, 3), axis=0)))
        grid.append(row)
    flat = Image.new('RGB', (AV_COLS, AV_ROWS))
    flat.putdata([c for r in grid for c in r])
    q = flat.quantize(colors=28, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    by = {}
    for j in range(AV_ROWS):
        for i in range(AV_COLS):
            by.setdefault(px._hex(q.getpixel((i, j))), set()).add((i, j))
    _AV_CACHE.update(by)
    return _AV_CACHE

def avatar_svg(theme, ax, ay):
    frame = '#5a3fc0' if theme == 'light' else '#6d4bd8'
    out = [px.P(px.cut_rect(ax, ay, ax + AV_COLS + 2, ay + AV_ROWS + 2, [1]), frame)]
    for col, cells in avatar_cells().items():
        out.append(px.P(px.shift(cells, ax + 1, ay + 1), col))
    return ''.join(out)


def hills(s, top):
    layers = {
        'light': ['#7be08f', '#4cc06b', '#2f9e57'],
        'dark': ['#0d1330', '#141d44', '#1c2a5e'],
    }[s.theme]
    for i, col in enumerate(layers):
        cells = set()
        for x in range(s.wc):
            h = 9 + 5 * math.sin(x / (31 + i * 9) + i * 1.7) + 2.5 * math.sin(x / (11 + i * 3) + i)
            t = int(top + i * 7 - h + 6)
            for y in range(t, s.hc): cells.add((x, y))
        s.add(px.P(cells, col))
    s.occupy(0, top - 14, s.wc, s.hc)


def layout(s):
    c = s.c
    nodes = []

    def cpl(x): return max(8, (R - x + 1) // 6)

    def heading(n, title, color, y):
        nodes.append(y + 6)
        s.add(px.P(px.cut_rect(TRACK - 2, y + 5, TRACK + 2, y + 9, [0]), c(color)))
        s.text(title, L, y, 2, color)
        s.text_r(f'{n:02d} / {TOTAL:02d}', R, y + 4, 1, 'dim')
        s.dotted(L, R, y + 19)
        return y + 28

    def kv(label, value, y, lc='cyan', vc='ink', col=72):
        s.text(label, L, y, 1, lc)
        s.text(':', L + col - 9, y, 1, 'dim')
        lines = px.wrap(value, cpl(L + col))
        for i, l in enumerate(lines): s.text(l, L + col, y + i * LINE, 1, vc)
        return y + len(lines) * LINE

    # ------------------------------------------------------------------ hero
    y0 = 20
    ay = y0 + 8
    s.add(avatar_svg(s.theme, L, ay))
    s.occupy(L - 1, ay - 1, L + AV_COLS + 3, ay + AV_ROWS + 3)
    hx = L + AV_COLS + 18
    s.text('COMPUTER ENGINEERING . THAPAR INSTITUTE', hx, y0 + 2, 1, 'dim')
    name = px.safe('LAVDEEP SINGH')
    s.add(px.P(px.text_cells(name, hx + 1, y0 + 15, 3), c('cyan')))          # pixel drop shadow
    s.text(name, hx, y0 + 13, 3, 'strong')
    ty = y0 + 41
    end = s.text('> NOTEBOOKS INTO THINGS THAT RUN', hx, ty, 1, 'green')
    s.add(f'<path d="{px.path_d(px.cut_rect(end + 3, ty, end + 8, ty + 7))}" fill="{c("green")}">{s.blink(0.9, 1.1)}</path>')
    s.text('ML . DATA . RESEARCH . SOFTWARE', hx, ty + 14, 1, 'dim')
    s.text('DEGREE.EXE . CLASS OF 2028', hx, ty + 28, 1, 'ink')
    bx, by, bw = hx, ty + 40, 130
    s.add(px.P(px.cut_rect(bx, by, bx + bw, by + 6, [1]), c('border')))
    s.add(px.P(px.cut_rect(bx + 1, by + 1, bx + bw - 1, by + 5, [0]), c('empty')))
    s.add(px.P(px.cut_rect(bx + 1, by + 1, bx + 1 + int((bw - 2) * .55), by + 5, [0]), c('green')))
    s.text('55%', bx + bw + 6, by - 1, 1, 'green')
    if s.theme == 'light':
        cx, cy = 404, y0 + 20
        s.add(px.P(disc(cx, cy, 10), '#ff9f1c') + px.P(disc(cx, cy, 8), '#ffd23f') + px.P(disc(cx - 2, cy - 2, 4), '#fff0a6'))
        rays = set()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            for i in range(14, 19):
                for a in (0, 1):
                    rays.add((cx + dx * i + (a if dx == 0 else 0), cy + dy * i + (a if dy == 0 else 0)))
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            for i in (11, 12, 13):
                rays |= {(cx + dx * i + a, cy + dy * i + b) for a in (0, 1) for b in (0, 1)}
        s.add(px.P(rays, '#ffb703'))
        s.occupy(cx - 22, cy - 22, cx + 22, cy + 22)
    else:
        cx, cy = 404, y0 + 20
        moon = disc(cx, cy, 10); shade = moon - disc(cx + 4, cy - 3, 9)
        s.add(px.P(moon, '#f1f4ff') + px.P(shade, '#aab6dc'))
        s.add(px.P(disc(cx - 5, cy + 3, 2) | disc(cx - 2, cy - 5, 1) | disc(cx - 6, cy - 3, 1), '#8f9bc4'))
        s.occupy(cx - 14, cy - 14, cx + 14, cy + 14)
    y = y0 + 76 + 26

    # ------------------------------------------------------------------ 01 at a glance
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
    y += 18

    # ------------------------------------------------------------------ 02 achievements
    y = heading(2, 'ACHIEVEMENTS', 'gold', y)
    items = [
        ('paper', 'PUBLISHED . IEEE', 'COMPUTINGCON 2025', 'DIABETES PREDICTION'),
        ('trophy', 'WINNER', 'NIOHACK 2026', 'HACKATHON'),
        ('trophy', 'WINNER', 'QUANTUMHACKS 2026', 'HACKATHON'),
        ('flag', 'FINALIST', 'OOSC 4.0', 'IIIT ALLAHABAD'),
        ('medal', 'TOP 10', 'HACKMOL 6.0', 'HACKATHON'),
        ('bulb', 'FELLOW', 'RESEARCH FELLOWSHIP', 'UNDERGRAD . NLP'),
        ('star', 'AMBASSADOR', 'GOOGLE GEMINI', 'STUDENT AMBASSADOR'),
        ('shield', 'REPRESENTATIVE', 'STUDENT PLACEMENT REP', 'TIET'),
    ]
    for i, (ic, lab, title, sub) in enumerate(items):
        x = L + (i % 2) * 212; yy = y + (i // 2) * 38
        s.add(px.P(px.icon_cells(ic, x, yy + 1, 2), c('gold')))
        s.occupy(x - 1, yy, x + 17, yy + 18)
        s.text(lab, x + 24, yy, 1, 'gold')
        s.text(title, x + 24, yy + 11, 1, 'strong')
        s.text(sub, x + 24, yy + 22, 1, 'dim')
    y += 4 * 38 + 10

    # ------------------------------------------------------------------ 03 projects
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
         'BETTER PREDICTION WITH FEWER FEATURES.',
         'SPARSE PCA, RANDOM FOREST, XGBOOST, CATBOOST, OPTUNA.',
         '94.6% ACCURACY, 92.9% F1, AND AN IEEE CONFERENCE PUBLICATION AT COMPUTINGCON 2025.'),
    ]
    for name_, col, stats, skills, prob, appr, res in projects:
        s.add(px.P(px.cut_rect(L - 11, y + 4, L - 7, y + 8), c(col)))
        s.text(name_, L, y, 2, col); y += 20
        if stats != skills:
            s.text(stats, L, y, 1, col); y += 14
        y = kv('SKILLS', skills, y, lc='dim', vc='dim')
        y += 3
        y = kv('PROBLEM', prob, y, lc='dim')
        y = kv('APPROACH', appr, y, lc='dim')
        y = kv('RESULT', res, y, lc='dim')
        y += 16
    s.add(px.P(px.cut_rect(L - 11, y + 4, L - 7, y + 8), c('grey')))
    s.text('EV BATTERY RUL', L, y, 2, 'strong'); y += 20
    s.text('REMAINING USEFUL LIFE PREDICTION', L, y, 1, 'grey'); y += 14
    y = kv('STATUS', 'RESEARCH IN PROGRESS', y, lc='dim')
    y += 18

    # ------------------------------------------------------------------ 04 timeline
    y = heading(4, 'TIMELINE', 'purple', y)
    s.text('GIT LOG --GRAPH . AUG 2024 TO NOW', L, y, 1, 'dim'); y += 16
    rows = [
        ('AUG 2024', 'JOINED THAPAR INSTITUTE', 0), ('APR 2025', 'HACKMOL 6.0 . TOP 10', 0),
        ('SEP 2025', 'IEEE ACCEPTED . COMPUTINGCON 2025', 0), ('DEC 2025', 'IEEE PAPER PUBLISHED', 0),
        ('JAN 2026', 'UNDERGRAD RESEARCH FELLOWSHIP', 0), ('JUN 2026', 'GOOGLE GEMINI STUDENT AMBASSADOR', 0),
        ('AUG 2026', 'OOSC 4.0 FINALIST . IIIT ALLAHABAD', 1), ('AUG 2026', 'QUANTUMHACKS 2026 . WINNER', 1),
        ('SEP 2026', 'NIOHACK 2026 . WINNER', 1), ('SEP 2026', 'STUDENT PLACEMENT REPRESENTATIVE', 1),
    ]
    ty0 = y
    for i, (d, e, hot) in enumerate(rows):
        yy = y + i * 13
        s.add(px.P(px.cut_rect(L + 1, yy + 2, L + 5, yy + 6), c('gold' if hot else 'purple')))
        s.text(d, L + 12, yy, 1, 'gold' if hot else 'dim')
        s.text(e, L + 72, yy, 1, 'gold' if hot else 'ink')
    y += len(rows) * 13
    s.text('+ FOUR MILESTONES IN TWO MONTHS', L + 72, y - 2, 1, 'gold'); y += 13
    s.add(px.P(px.cut_rect(L + 1, y + 2, L + 5, y + 6), c('green')))
    s.text('NOW', L + 12, y, 1, 'green'); s.text('HEAD . NEXT: ???', L + 72, y, 1, 'strong')
    s.add(px.P({(L + 2, yy2) for yy2 in range(ty0 + 4, y + 2) if yy2 % 4 != 3}, c('divider')))
    y += 11 + 18

    # ------------------------------------------------------------------ 05 stack
    y = heading(5, 'STACK', 'green', y)
    groups = [
        ('LANGUAGE', 'green', ['PYTHON', 'C++', 'C', 'JAVA', 'SQL', 'PL/SQL']),
        ('ML', 'cyan', ['SCIKIT-LEARN', 'PANDAS', 'NUMPY', 'TENSORFLOW']),
        ('NLP', 'cyan', ['SENTENCE-BERT', 'TF-IDF']),
        ('ENSEMBLE', 'purple', ['K-MEANS', 'DBSCAN', 'RANDOM FOREST', 'XGBOOST', 'CATBOOST', 'OPTUNA']),
        ('TOOLS', 'purple', ['GIT', 'GITHUB', 'JUPYTER', 'STREAMLIT', 'MYSQL']),
    ]
    for lab, col, its in groups:
        s.text(lab, L, y, 1, col)
        x = L + 72; yy = y
        for it in its:
            w = px.tw(px.safe(it)) + 10
            if x + w > R: x = L + 72; yy += LINE + 2
            s.add(px.P(px.cut_rect(x, yy + 2, x + 3, yy + 5), c(col)))
            s.text(it, x + 7, yy, 1, 'ink'); x += w + 8
        y = yy + LINE + 8
    y += 12

    # ------------------------------------------------------------------ 06 k-means on me
    y = heading(6, 'K-MEANS, BUT ON ME', 'gold', y)
    ys = y
    clusters = [
        ('0', 'RESEARCH', 'purple', 'NLP, SEMANTIC REPRESENTATIONS, CLUSTERING'),
        ('1', 'BUILD', 'green', 'ML SYSTEMS, DATA PROJECTS, DASHBOARDS'),
        ('2', 'COMPETE', 'gold', 'HACKATHONS, FINALS, ONE MORE FEATURE AT 3AM'),
        ('3', 'FUNDAMENTALS', 'cyan', 'DSA, C++, SOFTWARE ENGINEERING'),
    ]
    for n_, nm, col, desc in clusters:
        s.text(f'CLUSTER {n_} . {nm}', L, y, 1, col); y += 12
        for l in px.wrap(desc, (290 - L) // 6):
            s.text(l, L, y, 1, 'dim'); y += LINE
        y += 6
    s.dotted(L, 290, y)
    y += 8
    for lab, val in (('INERTIA', 'HIGH'), ('SILHOUETTE SCORE', 'STILL TUNING'), ('OPTIMAL K', 'ASK ME AGAIN NEXT SEMESTER')):
        s.text(lab, L, y, 1, 'strong'); s.text(':', L + 17 * 6, y, 1, 'dim'); s.text(val, L + 18 * 6 + 4, y, 1, 'ink'); y += LINE
    # scatter plot on the right
    rnd = random.Random(7); mid = (ys + y) // 2
    cents = [(332, mid - 38, 'purple'), (392, mid - 30, 'green'), (336, mid + 26, 'gold'), (394, mid + 30, 'cyan')]
    s.occupy(300, ys - 4, R, y + 4)
    for cx, cy, col in cents:
        pts = set()
        for _ in range(60):
            px_ = int(rnd.gauss(0, 4.2)); py_ = int(rnd.gauss(0, 4.2))
            for a in (0, 1):
                for b in (0, 1): pts.add((cx + px_ + a, cy + py_ + b))
        s.add(px.P(pts, c(col)))
        s.add(px.P(px.text_cells('+', cx - 2, cy - 3, 1), c('strong')))
    y += 18

    # ------------------------------------------------------------------ 07 contact
    y = heading(7, 'CONTACT', 'cyan', y)
    y = kv('LINKEDIN', 'LINKEDIN.COM/IN/LAVDEEP-SINGH-109802210', y, lc='gold', vc='cyan', col=72) + 3
    y = kv('GITHUB', 'GITHUB.COM/LAVDEEPSINGH23', y, lc='gold', vc='cyan', col=72) + 3
    y = kv('EMAIL', 'ITS.LAVDEEP.SINGH@GMAIL.COM', y, lc='gold', vc='cyan', col=72) + 14
    end = s.text('> THANKS FOR READING', L, y, 1, 'green')
    s.add(f'<path d="{px.path_d(px.cut_rect(end + 3, y, end + 8, y + 7))}" fill="{c("green")}">{s.blink(0.9, 1.1)}</path>')
    y += 8

    # progress track linking every section heading
    s.add(px.P({(TRACK, yy) for yy in range(nodes[0], nodes[-1]) if yy % 4 != 3}, c('divider')))
    return y


def build(theme):
    probe = Page(WC, 3000, theme, static=False, seed=5)
    end = layout(probe)
    hc = end + 52
    s = Page(WC, hc, theme, static=False, seed=5, star_div=240)
    layout(s)
    hills(s, hc - 34)
    return s.render()


if __name__ == '__main__':
    out = os.path.join(ROOT, 'assets')
    for theme in ('light', 'dark'):
        svg = build(theme)
        with open(os.path.join(out, f'page-{theme}.svg'), 'w') as f: f.write(svg)
        print(theme, len(svg) // 1024, 'KB')
