"""Montañas, nubes y los hitos de Manizales Pixel (sprites grandes que no van en la rejilla de 16x32)."""
from px import Img, C, rnd
from art import OUT, STONE, GLASS, WOOD, WOOD_D, CANE

# ---------------------------------------------------------------- montañas y nubes

HILL = (C('#5f9e5a'), C('#4a8650'), C('#3a6e45'), C('#7cb66b'))
HILL_OUT = C('#2f5038')


def mountain(w, h, v, nevado=False):
    """Montaña con ladera iluminada a la izquierda y rayado en la ladera en sombra, como el mapa ilustrado."""
    base, dark, deep, light = HILL
    img = Img(w, h)
    top = 6 if nevado else 1
    cx = w / 2.0 - 0.5 + (rnd(v, 1, 61) - 0.5) * w * 0.12
    for y in range(top, h - 1):
        t = (y - top) / float(h - 1 - top)
        hw = max(1.0, (w / 2.0 - 1.5) * (t ** 0.8))
        ridge = cx + (rnd(y // 3, v, 62) - 0.5) * 2.0
        snow = nevado and t < 0.30 + (rnd(y, v, 63) - 0.5) * 0.08
        for x in range(int(cx - hw), int(cx + hw) + 1):
            if not 1 <= x <= w - 2:
                continue
            lit = x < ridge
            if snow:
                c = C('#f4f7fb') if lit else C('#c9d6e4')
            elif lit:
                c = light if ridge - x < 2.5 and t < 0.85 else base
            else:
                c = deep if (x - int(y * 0.7)) % 4 == 0 and t > 0.15 else dark
            if t > 0.92:
                c = dark if lit else deep
            img.set(x, y, c)
    if nevado:                                 # fumarola del volcán
        for i, (px_, py_, r) in enumerate(((cx, 4.0, 2.2), (cx + 3, 2.5, 2.0), (cx + 6, 2.0, 1.6))):
            img.disc(px_, py_, r, C('#e8ecef') if i else C('#d4dae0'))
    return img.outline(HILL_OUT)


def cloud(v):
    img = Img(46, 22)
    white, shade, edge = C('#ffffff', 235), C('#d8eaf2', 235), C('#8db4c6', 235)
    for (x, y, r) in ((12, 13, 7), (22, 9, 8.5), (32, 12, 7), (17, 14, 6), (28, 14, 6.5)):
        img.disc(x + (v % 2) * 2, y, r, white)
    for y in range(15, 22):
        for x in range(46):
            if img.get(x, y)[3]:
                img.set(x, y, shade)
    for i in range(8):                        # punteado de acuarela
        x, y = int(rnd(i, v, 81) * 30) + 8, int(rnd(i, v, 82) * 6) + 14
        if img.get(x, y)[3]:
            img.set(x, y, edge)
    return img.outline(edge)


# ---------------------------------------------------------------- hitos

BRONZE = (C('#a5803f'), C('#7a5a2e'), C('#c9a25a'))
CREAM = (C('#ece2c8'), C('#cfc2a2'), C('#f7f1e1'))


def colonizadores():
    """Monumento a los Colonizadores (Chipre): grupo escultórico en bronce sobre base de piedra."""
    base, dark, light = BRONZE
    img = Img(38, 40)
    img.rect(5, 27, 28, 11, STONE[0])
    img.rect(5, 27, 3, 11, STONE[2])
    img.rect(29, 27, 4, 11, STONE[1])
    img.rect(3, 25, 32, 3, STONE[2])
    img.ellipse(19, 18, 14, 7, base)
    for (x, y, r) in ((8, 13, 2.6), (14, 9, 2.4), (21, 7, 2.6), (28, 11, 2.4), (32, 16, 2.2)):
        img.disc(x, y, r, base)
        img.set(int(x) - 1, int(y) - 1, light)
    img.line(21, 6, 24, 1, base)              # brazo en alto con el hacha
    img.line(22, 6, 25, 1, dark)
    img.hline(23, 27, 1, dark)
    for x in range(8, 32, 3):
        img.vline(x, 18, 24, dark)
    img.hline(6, 32, 24, dark)
    img.line(6, 17, 12, 13, light)
    return img.outline(OUT)


def gobernacion():
    """Palacio de la Gobernación de Caldas: fachada neoclásica frente a la Plaza de Bolívar."""
    base, dark, light = CREAM
    img = Img(50, 42)
    img.rect(2, 11, 46, 29, base)
    img.rect(42, 11, 6, 29, dark)
    img.hline(2, 47, 11, light)
    for x in range(3, 48, 3):
        img.set(x, 10, dark)                  # balaustrada
    img.hline(2, 47, 9, dark)
    for row, y in enumerate((14, 22, 30)):
        for x in range(4, 46, 5):
            if 15 <= x <= 33:
                continue
            img.rect(x, y, 2, 5 if row < 2 else 6, GLASS)
            img.hline(x, x + 1, y - 1, dark)
    # pórtico central con columnas y frontón
    img.rect(17, 9, 16, 31, light)
    for x in range(18, 33, 3):
        img.vline(x, 13, 37, dark)
    for k in range(6):
        img.hline(17 + k, 32 - k, 8 - k, light if k else dark)
    img.hline(17, 32, 9, dark)
    img.rect(23, 31, 4, 9, WOOD_D)
    img.hline(16, 33, 39, dark)
    # bandera de Colombia
    img.vline(25, 0, 3, OUT)
    img.hline(26, 28, 0, C('#f2c230'))
    img.hline(26, 28, 1, C('#2f609c'))
    img.hline(26, 28, 2, C('#d2493c'))
    return img.outline(OUT)


def mall_plaza():
    """Centro comercial Mall Plaza: caja moderna con fachada de vidrio y franja roja."""
    img = Img(50, 32)
    img.rect(2, 7, 46, 23, C('#e4e4e8'))
    img.rect(40, 7, 8, 23, C('#c4c4cc'))
    img.rect(2, 5, 46, 4, C('#d63a3a'))
    for x in range(6, 44, 4):
        img.hline(x, x + 1, 6, C('#ffffff'))
    img.rect(4, 12, 42, 10, C('#6fa8c9'))
    for x in range(4, 46, 6):
        img.vline(x, 12, 21, C('#4f86a8'))
        img.line(x + 2, 21, x + 5, 13, C('#a8d4ea'))
    img.rect(20, 23, 10, 7, GLASS)
    img.hline(18, 31, 22, C('#d63a3a'))
    return img.outline(OUT)


def plaza_toros():
    """Plaza de Toros de Manizales: ruedo ovalado con arcadas de estilo mudéjar."""
    wall, wall_d, rim = C('#c8674a'), C('#9e4a35'), C('#f1e6cf')
    img = Img(50, 32)
    img.ellipse(24.5, 18, 22.5, 12.5, wall)
    for x in range(3, 47):
        for y in range(18, 32):
            if img.get(x, y) == wall and ((x - 24.5) / 22.5) ** 2 + ((y - 18) / 12.5) ** 2 > 0.80:
                img.set(x, y, wall_d)
    img.ellipse(24.5, 13, 21, 8.5, rim)
    img.ellipse(24.5, 13.5, 17, 6, C('#e2c58f'))
    img.ellipse(24.5, 13.5, 15.5, 4.8, C('#ecd3a0'))
    for x in range(5, 46, 5):
        dy = 4.5 * max(0.0, 1 - ((x - 24.5) / 23.0) ** 2) ** 0.5
        y = int(19 + dy)
        img.rect(x, y, 2, 4, wall_d)
        img.set(x, y - 1, wall_d)
    return img.outline(OUT)


def ecoparque():
    """Portada de ecoparque: arco de guadua con techo de paja y letrero verde."""
    base, dark, light = CANE
    img = Img(34, 32)
    for x in (5, 27):
        img.rect(x, 9, 2, 22, base)
        img.vline(x + 1, 9, 30, dark)
        for y in range(12, 30, 5):
            img.set(x, y, light)
    img.rect(3, 8, 28, 3, WOOD)
    img.hline(3, 30, 10, WOOD_D)
    for k in range(6):
        img.hline(4 + k * 2, 29 - k * 2, 7 - k, C('#c9a75a') if k % 2 else C('#b08d46'))
    img.rect(9, 12, 16, 5, C('#3f7d4a'))
    for x in range(11, 23, 2):
        img.set(x, 14, C('#e4f0da'))
    return img.outline(OUT)


def estacion_cable():
    """Estación del cable aéreo: cubierta inclinada y rueda motriz."""
    img = Img(32, 28)
    img.rect(3, 14, 26, 13, C('#dcdcd6'))
    img.rect(24, 14, 5, 13, C('#bdbdb5'))
    img.rect(1, 10, 30, 4, C('#3f8f9c'))
    img.hline(1, 30, 13, C('#2c6b76'))
    img.rect(5, 17, 22, 4, GLASS)
    img.rect(13, 22, 6, 5, C('#555a66'))
    img.disc(15.5, 6.5, 3.4, C('#8a949b'))
    img.disc(15.5, 6.5, 1.4, C('#454f5a'))
    return img.outline(OUT)


def universidad():
    """Edificio universitario en ladrillo (campus Palogrande)."""
    brick, brick_d, mortar = C('#b65f3e'), C('#94492f'), C('#cf8a68')
    img = Img(42, 36)
    img.rect(2, 8, 38, 26, brick)
    img.rect(34, 8, 6, 26, brick_d)
    for y in range(10, 34, 3):
        img.hline(2, 39, y, mortar if y % 2 else brick_d)
    img.hline(2, 39, 8, C('#e8dcc8'))
    for y in (12, 19, 26):
        for x in range(5, 36, 5):
            img.rect(x, y, 3, 4, GLASS)
    img.rect(17, 27, 8, 7, C('#e8dcc8'))
    img.rect(19, 28, 4, 6, WOOD_D)
    return img.outline(OUT)


def recinto():
    """Pabellón de guadua del Recinto del Pensamiento."""
    straw, straw_d = C('#d4bd68'), C('#ad9548')
    img = Img(42, 32)
    for x in (6, 13, 20, 27, 34):
        img.rect(x, 17, 2, 13, CANE[0])
        img.vline(x + 1, 17, 29, CANE[1])
    for k in range(13):
        y = 4 + k
        hw = 3 + int(k * 1.4)
        img.hline(20 - hw, 21 + hw, y, straw)
        for x in range(20 - hw, 22 + hw, 4):
            img.set(x + (k % 2), y, straw_d)
    img.hline(5, 36, 17, straw_d)
    img.rect(20, 1, 2, 3, CANE[1])
    img.hline(4, 37, 30, C('#8a7a52'))
    return img.outline(OUT)


def bolivar():
    """Bolívar Cóndor de la Plaza de Bolívar."""
    base, dark, light = BRONZE
    img = Img(18, 28)
    img.rect(6, 18, 6, 9, STONE[0])
    img.rect(6, 18, 2, 9, STONE[2])
    img.rect(5, 17, 8, 2, STONE[2])
    img.rect(8, 6, 2, 11, base)
    img.disc(8.5, 5, 1.6, base)
    for k in range(2):
        img.line(8, 9 + k, 1, 4 + k, dark if k else base)
        img.line(9, 9 + k, 16, 4 + k, dark if k else base)
    img.set(8, 4, light)
    return img.outline(OUT)


def estadio():
    """Estadio Palogrande: tribunas ovaladas con cubierta, cancha y torres de luz."""
    stand, stand_d, roof = C('#c9c9c4'), C('#a3a39d'), C('#f2f2ee')
    img = Img(58, 38)
    img.ellipse(28.5, 21, 26, 15, stand_d)
    img.ellipse(28.5, 20, 25, 14, stand)
    for k in range(3):                         # gradas
        img.ellipse(28.5, 19.5, 22 - k * 2.5, 11.5 - k * 1.5, stand_d if k % 2 == 0 else stand)
    img.ellipse(28.5, 19.5, 15, 7.5, C('#5aa04f'))
    for x in range(14, 44, 4):                 # franjas del césped
        img.vline(x, 13, 26, C('#4c9045'))
    img.hline(18, 39, 19, C('#f4f4f4'))
    img.ellipse(28.5, 19.5, 2.5, 2, C('#f4f4f4'))
    img.ellipse(28.5, 19.5, 1.5, 1, C('#5aa04f'))
    img.vline(28, 13, 26, C('#f4f4f4'))
    for x0 in (8, 40):                         # cubiertas laterales
        img.rect(x0, 9, 10, 3, roof)
        img.hline(x0, x0 + 9, 11, C('#c4c4be'))
    for x in (3, 54):                          # torres de luz
        img.vline(x, 2, 22, C('#6c7780'))
        img.rect(x - 1, 1, 3, 2, C('#ffe98a'))
    return img.outline(OUT)


def bosque():
    """Portada del Bosque Popular El Prado: arco de madera con kiosco."""
    img = Img(36, 34)
    for x in (4, 29):
        img.rect(x, 12, 3, 20, WOOD)
        img.vline(x + 2, 12, 31, WOOD_D)
    img.rect(2, 9, 32, 4, WOOD_D)
    img.hline(2, 33, 9, WOOD)
    from art import ROOFS
    R, Rd, Rl = ROOFS['teja']
    for k in range(6):
        img.hline(6 + k * 2, 29 - k * 2, 8 - k, Rl if k == 5 else (R if k % 2 else Rd))
    img.rect(9, 14, 18, 6, C('#2f6b47'))
    for x in range(11, 25, 2):
        img.set(x, 16, C('#f3d76a'))
        img.set(x + 1, 17, C('#e4f0da'))
    img.hline(2, 33, 32, C('#8a7a52'))
    return img.outline(OUT)


# ---------------------------------------------------------------- clima

ICONOS = ['sol', 'luna', 'sol_nube', 'luna_nube', 'nublado', 'niebla', 'llovizna', 'lluvia', 'tormenta']


def _nube_icono(img, dx, dy, color, sombra):
    for (x, y, r) in ((5, 9, 3.2), (9, 7, 4.0), (12, 10, 2.8)):
        img.disc(x + dx, y + dy, r, color)
    img.rect(3 + dx, 10 + dy, 11, 3, color)
    img.hline(3 + dx, 13 + dx, 12 + dy, sombra)


def iconos_clima():
    """Hoja de 9 iconos de 16x16 en el orden de ICONOS."""
    sol, sol_l = C('#f5c242'), C('#fde58a')
    luna = C('#e9e4c8')
    blanco, gris, gris_d = C('#f7f9fb'), C('#c9d2dc'), C('#8d99a8')
    agua = C('#5fb0e6')
    sheet = Img(16 * len(ICONOS), 16)
    for i, name in enumerate(ICONOS):
        img = Img(16, 16)
        if name in ('sol', 'sol_nube'):
            cx, cy = (7.5, 7.5) if name == 'sol' else (6, 6)
            for k in range(8):
                import math
                a = k * math.pi / 4
                img.set(int(round(cx + math.cos(a) * 6.2)), int(round(cy + math.sin(a) * 6.2)), sol)
            img.disc(cx, cy, 4.2, sol)
            img.disc(cx - 1, cy - 1, 1.6, sol_l)
        if name in ('luna', 'luna_nube'):
            cx, cy = (7.5, 7.5) if name == 'luna' else (6, 6)
            img.disc(cx, cy, 5, luna)
            img.disc(cx + 2.5, cy - 1.5, 4.2, (0, 0, 0, 0))
            for y in range(16):
                for x in range(16):
                    if (x - cx - 2.5) ** 2 + (y - cy + 1.5) ** 2 <= 4.2 ** 2:
                        img.set(x, y, (0, 0, 0, 0))
        if name in ('sol_nube', 'luna_nube'):
            _nube_icono(img, 1, 2, blanco, gris)
        if name in ('nublado', 'llovizna', 'lluvia', 'tormenta'):
            _nube_icono(img, 2, -3, gris, gris_d)
            _nube_icono(img, -1, 0, blanco if name == 'nublado' else gris, gris_d)
        if name == 'niebla':
            for k, y in enumerate((4, 7, 10, 13)):
                img.hline(2 + (k % 2) * 2, 13 - (k % 2), y, gris if k % 2 else blanco)
        if name == 'llovizna':
            for x in (4, 8, 12):
                img.set(x, 14, agua)
        if name == 'lluvia':
            for x in (4, 8, 12):
                img.vline(x, 13, 15, agua)
        if name == 'tormenta':
            img.line(9, 11, 7, 14, sol)
            img.line(7, 14, 9, 14, sol)
            img.line(9, 14, 7, 16, sol)
            img.vline(4, 13, 15, agua)
        img.outline(C('#2a2733', 200))
        sheet.blit(img, i * 16, 0)
    return sheet


def resplandor():
    """Halo de luz cálida para farolas y ventanas (se pinta en modo aditivo)."""
    img = Img(32, 32)
    for y in range(32):
        for x in range(32):
            d = ((x - 15.5) ** 2 + (y - 15.5) ** 2) ** 0.5 / 16.0
            a = max(0.0, 1.0 - d) ** 2.2
            if a > 0.01:
                img.set(x, y, (255, 214, 140, int(255 * a)))
    return img


def gota():
    img = Img(2, 6)
    img.vline(0, 0, 5, C('#bfe6ff', 200))
    img.vline(1, 2, 5, C('#8cc8f0', 160))
    return img


def gondola():
    img = Img(9, 10)
    img.vline(4, 0, 2, OUT)
    img.rect(1, 3, 7, 6, C('#d24c3e'))
    img.rect(2, 4, 5, 2, GLASS)
    img.hline(1, 7, 8, C('#a23229'))
    return img.outline(OUT)
