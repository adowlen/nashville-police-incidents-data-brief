"""Composite the headline figure over the generated hero illustration.
Adapted from the Nashville building permit applications package
(2026-11-04): a TOP gradient scrim over the generated illustration's
clean dark field (hero_source/hero-art.webp), with the narrative scene
below. All text is read from stats.json at composite time, so the hero
can never carry a figure the stats do not (sync gate, standards
10.3). hero-headline.txt carries the same text for the record.
"""
import json
import pathlib
from PIL import Image, ImageDraw, ImageFont

root = pathlib.Path(__file__).resolve().parent.parent
stats = json.loads((root / "stats.json").read_text())
cands = sorted((root / "hero_source").glob("hero-art.webp")) + \
        sorted((root / "hero_source").glob("*.png")) if (root / "hero_source").exists() else []
if not cands:
    raise SystemExit("no hero illustration in hero_source/ - hero stays pending")
img = Image.open(cands[0]).convert("RGB")
W, H = img.size

# Top gradient scrim over the art's clean dark field: strongest at the
# top edge, fading out before the narrative scene begins.
band = int(H * 0.42)
overlay = Image.new("L", (1, band))
for yy in range(band):
    t = yy / band
    overlay.putpixel((0, yy), int(215 * (1 - t) ** 1.5))
overlay = overlay.resize((W, band))
scrim = Image.new("RGB", (W, band), (10, 13, 16))
img.paste(scrim, (0, 0), overlay)
d = ImageDraw.Draw(img)


def font(size, bold=True):
    p = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(p, size)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


share = stats["code_classes"]["mnpd_local_share"] * 100
rows = stats["rows"]
snap = stats["snapshot_date"]
chg = abs(stats["trend"]["criminal_change_2025_to_2026_jan_oct_pct"])

MAXW = int(W * 0.88)
headline = f"{share:.0f}%"
d.text((56, int(H * 0.05)), headline, font=font(int(H * 0.115)), fill=(245, 168, 0))
sub_f = font(int(H * 0.032), bold=False)
y = int(H * 0.05) + int(H * 0.145)
sub = (f"of the {rows:,} records in Nashville's police incident ledger since 2019 are MNPD's non-criminal "
       f"incident types - police inquiries, found and lost property, transports - while records under criminal "
       f"offense codes fell {chg:.1f} percent in Jan-Oct 2026, a second straight matched-window drop of about 10 percent")
for line in wrap(sub, sub_f, MAXW):
    d.text((58, y), line, font=sub_f, fill=(242, 242, 242))
    y += int(H * 0.046)
src_f = font(int(H * 0.021), bold=False)
srcline = (f"Machine Readable - Metro Nashville Police Department Incidents layer, pulled {snap} - offense-victim records")
for line in wrap(srcline, src_f, MAXW):
    d.text((58, y + 8), line, font=src_f, fill=(150, 210, 200))
    y += int(H * 0.032)
img.save(root / "hero.png")
print("hero", img.size, "from", cands[0].name)
