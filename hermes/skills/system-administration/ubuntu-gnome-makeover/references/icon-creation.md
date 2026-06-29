# Custom Icon Creation — Hermes + LM Studio Style

A complete Python/PIL recipe for generating a 1024×1024 RGBA PNG icon that matches the modern flat squircle-badge style of Hermes Desktop and LM Studio.

## Style Summary

| Element | Hermes Desktop | LM Studio | Combined Icon |
|---------|---------------|-----------|---------------|
| Shape | Rounded square (R≈220/1024) | Rounded square (R≈220/1024) | Same |
| Background | Neutral gray ~(147,147,147) | Purple ~(124,105,222) | Gray→Purple gradient |
| Interior | Profile silhouette | Brain icon | Magic wand + sparkles |
| Aesthetic | Minimalist flat | Minimalist flat | Minimalist flat |
| Size | 1024×1024 PNG RGBA | 1024×1024 PNG RGBA | Same |

## Full Generation Script

```python
from PIL import Image, ImageDraw
import math

SIZE = 1024
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Colors — gradient: Hermes gray top → LM Studio purple bottom
BG_TOP = (90, 90, 110, 255)
BG_BOT = (124, 105, 222, 255)
WHITE = (255, 255, 255, 255)
LIGHT = (232, 229, 255, 255)
SOFT = (200, 195, 240, 200)
DIM = (150, 140, 200, 150)

def gradient_color(y, h, c1, c2):
    t = y / h
    return (int(c1[0] + (c2[0]-c1[0])*t),
            int(c1[1] + (c2[1]-c1[1])*t),
            int(c1[2] + (c2[2]-c1[2])*t), 255)

# 1. Draw rounded-square background
RADIUS = 220
MARGIN = 16
for y in range(MARGIN, SIZE - MARGIN + 1):
    col = gradient_color(y - MARGIN, SIZE - 2*MARGIN, BG_TOP, BG_BOT)
    for x in range(MARGIN, SIZE - MARGIN + 1):
        # Compute rounded-rect corner clipping
        if x < MARGIN + RADIUS and y < MARGIN + RADIUS:
            dx, dy = x - (MARGIN + RADIUS), y - (MARGIN + RADIUS)
            if dx*dx + dy*dy > RADIUS*RADIUS: continue
        elif x < MARGIN + RADIUS and y > SIZE - MARGIN - RADIUS:
            dx, dy = x - (MARGIN + RADIUS), y - (SIZE - MARGIN - RADIUS)
            if dx*dx + dy*dy > RADIUS*RADIUS: continue
        elif x > SIZE - MARGIN - RADIUS and y < MARGIN + RADIUS:
            dx, dy = x - (SIZE - MARGIN - RADIUS), y - (MARGIN + RADIUS)
            if dx*dx + dy*dy > RADIUS*RADIUS: continue
        elif x > SIZE - MARGIN - RADIUS and y > SIZE - MARGIN - RADIUS:
            dx, dy = x - (SIZE - MARGIN - RADIUS), y - (SIZE - MARGIN - RADIUS)
            if dx*dx + dy*dy > RADIUS*RADIUS: continue
        draw.point((x, y), fill=col)

# 2. Draw star sparkles
def draw_star(cx, cy, r, color, alpha=255):
    pts = []
    for i in range(10):
        a = math.pi/2 + i * math.pi/5
        rad = r if i % 2 == 0 else r * 0.4
        px = cx + rad * math.cos(a)
        py = cy - rad * math.sin(a)
        pts.append((px, py))
    draw.polygon(pts, fill=(*color[:3], alpha))

draw_star(700, 280, 72, WHITE)        # Main sparkle (top-right)
draw_star(380, 720, 48, LIGHT)        # Medium (bottom-left)
draw_star(740, 600, 28, SOFT)         # Small (center-right)

# 3. Decorative dots
for cx, cy, r in [(280, 480, 14), (760, 740, 10),
                   (340, 240, 8),  (640, 800, 6)]:
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=DIM)

# 4. Magic wand
cx, cy = 540, 560
angle = -0.5    # ~ -30°
wand_len = 260
thick = 20
cos_a, sin_a = math.cos(angle), math.sin(angle)
x1 = cx - wand_len/2 * cos_a
y1 = cy - wand_len/2 * sin_a
x2 = cx + wand_len/2 * cos_a
y2 = cy + wand_len/2 * sin_a

draw.line((x1, y1, x2, y2), fill=WHITE, width=thick)
# Highlight for 3D effect
hx, hy = -sin_a * 4, cos_a * 4
draw.line((x1+hx, y1+hy, x2+hx, y2+hy), fill=(255,255,255,200), width=6)

# Tip glow
for r in range(40, 4, -6):
    al = int(100 * (1 - r/40))
    draw.ellipse((x2-r, y2-r, x2+r, y2+r), fill=(255, 255, 255, al))
draw.ellipse((x2-12, y2-12, x2+12, y2+12), fill=WHITE)

img.save('custom-icon.png')
```

## Applying the Icon

```bash
# For a folder on desktop:
gio set ~/Desktop/MyFolder metadata::custom-icon "file://$PWD/custom-icon.png"

# For a script — create a .desktop launcher instead:
cat > ~/Desktop/MyLauncher.desktop << EOF
[Desktop Entry]
Name=My App
Exec=bash /path/to/script.sh
Icon=$PWD/custom-icon.png
Type=Application
Terminal=true
EOF
chmod +x ~/Desktop/MyLauncher.desktop
```
