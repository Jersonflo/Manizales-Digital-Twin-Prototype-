"""Hoja de revisión: todos los sprites y tiles ampliados sobre pasto. Uso: python sheet.py"""
import os
import art
from px import Img

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'previews')
os.makedirs(OUT, exist_ok=True)

rows = [
    [art.catedral(), art.torre_chipre(), art.torre_cable(), art.pin()]
    + [art.carro(i, v) for i in range(len(art.CARROS)) for v in range(3)],
    [s for name, s in art.catalogo() if name.startswith('casa') and int(name.split('_')[2]) < 5],
    [s for name, s in art.catalogo() if not name.startswith('casa')],
]
w = max(sum(s.w + 3 for s in r) for r in rows) + 6
h = sum(max(s.h for s in r) + 6 for r in rows) + 60
sheet = Img(w, h)
for ty in range(0, h, 16):
    for tx in range(0, w, 16):
        sheet.blit(art.grass((tx // 128) % 4, (tx // 16 + ty // 16) % 4), tx, ty)
y = 3
for r in rows:
    rh = max(s.h for s in r)
    x = 3
    for s in r:
        sheet.blit(s, x, y + rh - s.h)
        x += s.w + 3
    y += rh + 6
tiles = [art.strip(m, art.ROAD, 3, 'road') for m in (5, 10, 15, 3, 6, 12, 9, 0)]
tiles += [art.strip(m, art.STREET, 4, 'road', 9) for m in (5, 10, 15, 3)]
tiles += [art.strip(m, art.WATER, 3, 'water', f) for m in (5, 10) for f in (0, 1)]
for i, t in enumerate(tiles):
    sheet.blit(t, 4 + i * 18, y)
for i in range(6):
    sheet.blit(art.background(i), 4 + i * 16, y + 22)
    sheet.blit(art.cliff(i == 0, i == 5, i), 4 + i * 16, y + 22)
sheet.scaled(4).save(os.path.join(OUT, 'hoja_sprites.png'))
print('ok', w, h)
