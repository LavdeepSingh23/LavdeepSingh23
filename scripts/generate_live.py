#!/usr/bin/env python3
"""Builds the two live pixel panels (activity + contribution invaders) as dark/light SVGs.
Run by .github/workflows/update-live.yml. Standard library only (plus pxlib.py next to this file)."""
import os, re, sys, datetime, json, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pxlib import *

USER = os.environ.get('GH_USER', 'LavdeepSingh23')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
OUT = os.environ.get('OUT_DIR', 'assets/live')
NO_API = os.environ.get('LIVE_NO_API') == '1'
MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

def http_get(url, accept=None):
    h = {'User-Agent': 'pixel-profile-readme'}
    if accept: h['Accept'] = accept
    if TOKEN and 'api.github.com' in url: h['Authorization'] = f'Bearer {TOKEN}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

# ---------------- data ----------------
def fetch_calendar():
    html = http_get(f'https://github.com/users/{USER}/contributions')
    tips = {}
    for m in re.finditer(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        txt = m.group(2); n = re.match(r'\s*(\d[\d,]*)\s+contribution', txt)
        tips[m.group(1)] = int(n.group(1).replace(',', '')) if n else 0
    days = []
    for m in re.finditer(r'<td\b[^>]*>', html):
        tag = m.group(0)
        if 'data-date' not in tag: continue
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        idm = re.match(r'contribution-day-component-(\d+)-(\d+)', a.get('id', ''))
        if not idm: continue
        days.append(dict(date=datetime.date.fromisoformat(a['data-date']), row=int(idm.group(1)), col=int(idm.group(2)),
                         level=int(a.get('data-level', '0')), count=tips.get(a['id'], 0)))
    if not days: raise RuntimeError('no contribution cells found')
    tm = re.search(r'([\d,]+)\s+contributions\s+in\s+the\s+last\s+year', html, re.S)
    total = int(tm.group(1).replace(',', '')) if tm else sum(d['count'] for d in days)
    return days, total

def streak(days):
    by = {d['date']: d['count'] for d in days}
    d = datetime.datetime.now(datetime.timezone.utc).date()
    if not by.get(d): d -= datetime.timedelta(days=1)
    n = 0
    while by.get(d, 0) > 0: n += 1; d -= datetime.timedelta(days=1)
    return n

def fetch_activity():
    if NO_API: return [], []
    try:
        repos = json.loads(http_get(f'https://api.github.com/users/{USER}/repos?sort=pushed&per_page=15&type=owner'))
        repos = [r for r in repos if not r.get('fork')]
    except Exception as e:
        print('repo list failed:', e); return [], []
    recent = [dict(name=r['name'], lang=r.get('language') or '', date=r['pushed_at'][:10]) for r in repos[:3]]
    commits = []
    for r in repos[:5]:
        try:
            for c in json.loads(http_get(f"https://api.github.com/repos/{USER}/{r['name']}/commits?author={USER}&per_page=3")):
                commits.append(dict(repo=r['name'], msg=c['commit']['message'].split('\n')[0], date=c['commit']['author']['date'][:10]))
        except Exception as e:
            print('commits failed for', r['name'], e)
    commits.sort(key=lambda c: c['date'], reverse=True)
    return commits[:4], recent

def fmt(date_str):
    d = datetime.date.fromisoformat(date_str); return f'{d.day} {MON[d.month - 1]}'

# ---------------- panels ----------------
def activity(theme, static, st, total, commits, repos):
    now = datetime.datetime.now(datetime.timezone.utc)
    n_c, n_r = max(len(commits), 1), max(len(repos), 1)
    H = 71 + n_c * 18 + 6 + 10 + n_r * 10 + 6
    s = Scene(300, H, theme, static, 61)
    s.text('LIVE ACTIVITY', 8, 6, 2, 'green'); s.text_r(f'UPDATED {now.day} {MON[now.month-1]} {now.year}', 294, 9, 1, 'muted'); s.dotted(8, 294, 23)
    s.text('CURRENT STREAK', 8, 29, 1, 'muted'); s.text(f'{st} DAYS', 8, 39, 2, 'strong')
    s.text('12 MONTH TOTAL', 150, 29, 1, 'muted'); s.text(f'{total}', 150, 39, 2, 'strong')
    s.dotted(8, 294, 57)
    s.text('LATEST COMMITS', 8, 62, 1, 'cyan')
    y = 72
    if commits:
        for c in commits:
            s.text(clip(c['repo'], 24), 8, y, 1, 'green'); s.text_r(fmt(c['date']), 294, y, 1, 'muted')
            s.text(clip(c['msg'], 47), 8, y + 9, 1, 'ink'); y += 18
    else:
        s.text('NO COMMIT DATA YET', 8, y, 1, 'ink'); s.text('RUN THE UPDATE ACTION ONCE', 8, y + 9, 1, 'dim'); y += 18
    y += 4
    s.text('RECENTLY UPDATED REPOS', 8, y, 1, 'purple'); y += 10
    if repos:
        for r in repos:
            s.text(clip(r['name'], 28), 8, y, 1, 'ink'); s.text(clip(r['lang'], 10), 190, y, 1, 'dim'); s.text_r(fmt(r['date']), 294, y, 1, 'muted'); y += 10
    else:
        s.text('NO REPO DATA YET', 8, y, 1, 'dim')
    return s.svg()

LEVELS = {'dark': ['#0b5d3b', '#0f8f5b', '#00c47d', '#00e5a0'], 'light': ['#9fe3c3', '#5cc99c', '#26a874', '#0a7f55']}

def game(theme, static, days, total):
    cols = max(d['col'] for d in days) + 1; pitch = 5; gw = cols * pitch - 1
    x0, y0 = (300 - gw) // 2, 30; ys = y0 + 7 * pitch + 6; H = ys + 5 + 6
    s = Scene(300, H, theme, static, 71); t = s.t
    s.text('CONTRIBUTION INVADERS', 8, 6, 2, 'green'); s.dotted(8, 294, 23)
    s.occupy(x0 - 1, y0 - 1, x0 + gw + 1, ys + 8)
    cell = lambda col, row: (x0 + col * pitch, y0 + row * pitch)
    targets = {}
    for d in days:
        if d['level'] > 0: targets.setdefault(d['col'], []).append(d['row'])
    shots = [(c, r) for c in sorted(targets) for r in sorted(targets[c], reverse=True)]
    dt = min(0.22, 36.0 / max(len(shots), 1)); t0 = 1.0
    sched, tt, last = [], t0, None
    for c, r in shots:
        if last is not None and c != last: tt += 0.05
        sched.append((c, r, tt)); tt += dt; last = c
    T = max(tt + 2.5, 4.0)
    empty = {(cx + a, cy + b) for d in days for cx, cy in [cell(d['col'], d['row'])] for a in range(4) for b in range(4)}
    s.add(P(empty, t['empty']))
    hit = {(c, r): ti for c, r, ti in sched}
    for d in days:
        if d['level'] <= 0: continue
        cx, cy = cell(d['col'], d['row']); col = LEVELS[theme][min(d['level'], 4) - 1]
        body = P({(cx + a, cy + b) for a in range(4) for b in range(4)}, col)
        if static or (d['col'], d['row']) not in hit: s.add(body); continue
        h = hit[(d['col'], d['row'])] + 0.14; kt1, kt2 = h / T, (h + 0.09) / T
        s.add(body.replace('/>', f'><animate attributeName="fill" values="{col};#ffffff" keyTimes="0;{kt1:.4f}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>'
                           f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;{kt1:.4f};{kt2:.4f}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></path>'))
    ship = icon_cells('ship', 0, ys, 1); shipx = lambda c: (x0 + c * pitch + 2 - 4) * U
    if static or not sched:
        s.add(f'<g transform="translate({shipx(0)},0)">{P(ship, t["cyan"])}</g>'); return s.svg()
    kts = [0.0] + [ti / T for _, _, ti in sched]; vals = [f'{shipx(sched[0][0])},0'] + [f'{shipx(c)},0' for c, _, _ in sched]
    s.add(f'<g>{P(ship, t["cyan"])}<animateTransform attributeName="transform" type="translate" calcMode="discrete" '
          f'values="{";".join(vals)}" keyTimes="{";".join(f"{k:.4f}" for k in kts)}" dur="{T:.2f}s" repeatCount="indefinite"/></g>')
    lt, lx, ly, lo = [0.0], [0], [0], [0]
    for c, r, ti in sched:
        x = (x0 + c * pitch + 1) * U; ysrc = (ys - 4) * U; yend = (y0 + r * pitch + 2) * U
        for dtm, yy, op in [(0.0, ysrc, 1), (0.05, (ysrc + yend) // 2, 1), (0.10, yend, 1), (0.14, yend, 0)]:
            lt.append((ti + dtm) / T); lx.append(x); ly.append(yy); lo.append(op)
    fmtv = lambda v: ';'.join(str(int(a)) for a in v)
    kt = ';'.join(f'{k:.4f}' for k in lt)
    s.add(f'<rect width="{U}" height="{3*U}" fill="{t["gold"] if theme=="dark" else "#d6402a"}" opacity="0">'
          f'<animate attributeName="x" values="{fmtv(lx)}" keyTimes="{kt}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>'
          f'<animate attributeName="y" values="{fmtv(ly)}" keyTimes="{kt}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="{fmtv(lo)}" keyTimes="{kt}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></rect>')
    return s.svg()

def main():
    os.makedirs(OUT, exist_ok=True)
    days, total = fetch_calendar(); st = streak(days); commits, repos = fetch_activity()
    print(f'calendar: {len(days)} days, total {total}, streak {st}; commits {len(commits)}, repos {len(repos)}')
    for theme in ('dark', 'light'):
        for static, suffix in ((False, ''),):
            open(os.path.join(OUT, f'activity-{theme}.svg'), 'w').write(activity(theme, static, st, total, commits, repos))
            open(os.path.join(OUT, f'game-{theme}.svg'), 'w').write(game(theme, static, days, total))
    if os.environ.get('LIVE_PREVIEW'):
        for theme in ('dark', 'light'):
            open(os.path.join(OUT, f'prev-activity-{theme}.svg'), 'w').write(activity(theme, True, st, total, commits, repos))
            open(os.path.join(OUT, f'prev-game-{theme}.svg'), 'w').write(game(theme, True, days, total))

if __name__ == '__main__':
    main()
