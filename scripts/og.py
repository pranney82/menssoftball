#!/usr/bin/env python3
"""Build og-image.png (the link preview card) from the live season data.

Run from the repo root after any data update:  python3 scripts/og.py
Shows: team, season, record and place, title count, and the next game
(or the last result once the season is over).
"""
import json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'scripts', 'fonts')
W, H = 1200, 630
INK, PANEL = (26, 27, 31), (34, 36, 40)
SUN, CREAM, MUTED, DIM = (255, 218, 36), (254, 252, 245), (185, 182, 172), (133, 130, 122)
SCALE = 2  # draw at 2x, downsample for crisp edges


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f'Outfit-{weight}.ttf'), size * SCALE)


def load(*p):
    with open(os.path.join(ROOT, *p)) as f:
        return json.load(f)


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f'{n}th'
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def game_dt(g):
    m = re.match(r'(\d+):(\d+)\s*(AM|PM)', g.get('time') or '', re.I)
    if not g.get('weekDate') or not m:
        return None
    h = int(m[1]) % 12 + (12 if m[3].upper() == 'PM' else 0)
    return datetime.fromisoformat(g['weekDate']).replace(hour=h, minute=int(m[2]))


def field_name(loc):
    m = re.match(r'^HP\s*(\d+)$', loc or '', re.I)
    return f'Hobgood Park, Field {m[1]}' if m else (loc or '')


def main():
    cfg = load('data', 'config.json')
    season = next(s for s in cfg['seasons'] if s['id'] == cfg['activeSeason'])
    aliases = [a.lower() for a in cfg.get('teamAliases', [])] + [cfg.get('teamShort', '').lower()]
    is_us = lambda n: any(a and a in (n or '').lower() for a in aliases)
    base = os.path.join('data', season['folder'])
    standings = load(base, 'standings.json')
    schedule = load(base, 'schedule.json')
    champs = [s for s in cfg['seasons'] if s.get('champion')]
    titles = len(champs)

    us = next((r for r in standings if is_us(r['team'])), None)
    ours = [g for g in schedule if is_us(g.get('home')) or is_us(g.get('away'))]
    now = datetime.now(ZoneInfo('America/New_York')).replace(tzinfo=None)
    upcoming = sorted([g for g in ours if 'homeScore' not in g and not g.get('note') and game_dt(g) and game_dt(g) > now], key=game_dt)
    played = [g for g in ours if 'homeScore' in g]

    S = SCALE
    img = Image.new('RGB', (W * S, H * S), INK)

    # Warm glow behind the logo
    glow = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(glow).ellipse([(-60) * S, (40) * S, (540) * S, (640) * S], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(120 * S))
    img = Image.composite(Image.new('RGB', img.size, (70, 60, 20)), img, glow)
    d = ImageDraw.Draw(img)

    # Logo on a panel disc
    cx, cy, r = 255, 300, 190
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=PANEL)
    logo = Image.open(os.path.join(ROOT, 'logo.png')).convert('RGBA')
    ls = int(2 * r * 0.98) * S
    logo = logo.resize((ls, ls), Image.LANCZOS)
    img.paste(logo, (cx * S - ls // 2, cy * S - ls // 2), logo)

    x = 500
    def text(xy, s, f, fill):
        d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill)
    def width(s, f):
        return d.textlength(s, font=f) / S

    # Eyebrow
    eyebrow = f"{season['label'].upper()}  ·  MEN'S SLOW PITCH"
    text((x, 70), eyebrow, font(700, 20), DIM)

    # Team name
    text((x, 98), 'Sunshine on a', font(800, 46), CREAM)
    text((x, 148), 'Ranney Day', font(800, 46), SUN)

    # Record + place
    y = 222
    if us:
        rec = f"{us['w']}-{us['l']}" + (f"-{us['t']}" if us.get('t') else '')
        fr = font(900, 132)
        text((x - 4, y - 18), rec, fr, SUN)
        rx = x + width(rec, fr) + 26
        text((rx, y + 22), ordinal(us['rank']).upper(), font(800, 40), CREAM)
        text((rx, y + 68), 'PLACE', font(700, 20), DIM)
        sm = re.match(r'^W(\d+)', str(us.get('streak') or ''))
        if sm and int(sm[1]) >= 3:
            text((rx, y + 96), f"{sm[1]}-GAME WIN STREAK", font(700, 20), SUN)

    # Divider
    y = 400
    d.rectangle([x * S, y * S, 1120 * S, (y + 2) * S], fill=(48, 50, 54))

    # Next game, or last result when the season is done
    y = 422
    if upcoming:
        g = upcoming[0]
        home = is_us(g['home'])
        opp = g['away'] if home else g['home']
        dt = game_dt(g)
        label = 'PLAYOFFS' if g.get('playoff') else 'NEXT UP'
        text((x, y), label, font(700, 20), SUN)
        opp_row = next((s for s in standings if s['team'] == opp), None)
        line = f"{'vs' if home else 'at'} {opp}"
        fo = font(800, 42)
        while width(line, fo) > 620 and fo.size > 28 * S:
            fo = font(800, fo.size // S - 2)
        text((x, y + 28), line, fo, CREAM)
        if opp_row:
            ox = x + width(line, fo) + 16
            text((ox, y + 44), f"({opp_row['w']}-{opp_row['l']})", font(500, 24), DIM)
        when = f"{dt.strftime('%a, %b')} {dt.day}  ·  {g['time']}  ·  {field_name(g.get('location'))}"
        text((x, y + 86), when, font(500, 24), MUTED)
    elif played:
        g = played[-1]
        home = is_us(g['home'])
        u, o = (g['homeScore'], g['awayScore']) if home else (g['awayScore'], g['homeScore'])
        opp = g['away'] if home else g['home']
        text((x, y), 'LAST RESULT', font(700, 20), SUN)
        text((x, y + 28), f"{'W' if u > o else 'L'} {u}-{o} {'vs' if home else 'at'} {opp}", font(800, 42), CREAM)

    # Title chip
    if titles:
        if titles > 1:
            chip = f"{titles}× CHAMPS"
        else:
            lm = re.match(r'(\w+)\s+\d{2}(\d{2})', champs[0]['label'])
            chip = f"{lm[1].upper()} '{lm[2]} CHAMPS" if lm else 'CHAMPS'
        fc = font(800, 18)
        cw = width(chip, fc) + 36
        cx0, cy0 = 1120 - cw, 72
        d.rounded_rectangle([cx0 * S, (cy0 - 6) * S, 1120 * S, (cy0 + 26) * S], radius=16 * S, fill=SUN)
        text((cx0 + 18, cy0 - 1), chip, fc, INK)

    # Brand bar
    d.rectangle([0, (H - 12) * S, W * S, H * S], fill=SUN)

    img = img.resize((W, H), Image.LANCZOS)
    out = os.path.join(ROOT, 'og-image.png')
    img.save(out, optimize=True)

    # Point the meta tags at this exact image so iMessage and others refetch it
    import hashlib
    ver = hashlib.sha1(open(out, 'rb').read()).hexdigest()[:10]
    desc = f"{season['label']} men's slow pitch"
    if us:
        desc += f". {us['w']}-{us['l']}, {ordinal(us['rank'])} place"
    if upcoming:
        g = upcoming[0]; home = is_us(g['home']); dt = game_dt(g)
        desc += f". Next: {'vs' if home else 'at'} {g['away'] if home else g['home']}, {dt.strftime('%a %b')} {dt.day}, {g['time']}"
    idx = os.path.join(ROOT, 'index.html')
    h = open(idx).read()
    h = re.sub(r'(og-image\.png)(\?v=\w+)?"', rf'\1?v={ver}"', h)
    h = re.sub(r'(<meta (?:property="og|name="twitter):description" content=")[^"]*"', rf'\g<1>{desc}"', h)
    open(idx, 'w').write(h)
    print('og-image.png written, version', ver)
    print(desc)


if __name__ == '__main__':
    main()
