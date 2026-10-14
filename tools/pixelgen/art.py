"""Tiles y sprites de Manizales Pixel, dibujados por código (paleta limitada, tile de 16 px)."""
from px import Img, C, rnd

T = 16
N, E, S, W = 1, 2, 4, 8

OUT = C('#2a2733')        # contorno de sprites
OUT_G = C('#2f5038')      # borde del terreno

# (base, oscuro, claro) por tono de pasto; cada comuna usa uno
GRASS = [
    (C('#6fae52'), C('#5d9a48'), C('#84c064')),   # verde fresco
    (C('#a6b84e'), C('#93a644'), C('#b9c961')),   # amarillento
    (C('#7f9c4c'), C('#6f8b43'), C('#92ad5a')),   # oliva
    (C('#57a05e'), C('#488c52'), C('#6bb46f')),   # verde frío
]
BG = (C('#4d8c82'), C('#457f77'), C('#5a998d'))
ROAD = (C('#bdb6c8'), C('#a9a1b6'), C('#d0cadb'), C('#8b8499'))      # vías secundarias de la capa Calles
AVENUE = (C('#76738a'), C('#6a6779'), C('#858299'), C('#d9d3e2'))    # avenidas principales: asfalto con bordillo
LINE = C('#f2d36b')                                                    # línea central amarilla
PLAZA = (C('#ddd3c0'), C('#c9bea9'), C('#ebe4d6'), C('#a39883'))
STREET = (C('#8d8a9c'), C('#807d90'), C('#9b98aa'), C('#d9d3e2'))    # calles de barrio: mismo asfalto, más angostas
WATER = (C('#63bfc6'), C('#4aa5b3'), C('#b9ebe6'), C('#357f93'))
STONE = (C('#8a949b'), C('#6c7780'), C('#a7b0b3'), C('#454f5a'))

ROOFS = {
    'teja':    (C('#c9573e'), C('#a13f31'), C('#e07a55')),
    'teja2':   (C('#d9783f'), C('#b25c2e'), C('#eb9a5c')),
    'azul':    (C('#4f73a8'), C('#3a577f'), C('#6f93c4')),
    'morado':  (C('#8b5c9e'), C('#6b4479'), C('#a87bb8')),
    'pizarra': (C('#566072'), C('#3f4757'), C('#737e92')),
}
TRIMS = {'rojo': C('#b8402f'), 'azul': C('#2f609c'), 'verde': C('#2f7d4f'), 'ocre': C('#d39a25'), 'cafe': C('#6b4526')}
WALLS = {'blanco': (C('#f3eedf'), C('#d6cdb6')), 'crema': (C('#efe0b8'), C('#d2c093')),
         'celeste': (C('#cfe0e6'), C('#aec3cc')), 'rosa': (C('#eccfc4'), C('#d0b0a4'))}
# (tejado, color de zócalo/puertas, muro): combinaciones típicas de casa de bahareque
ESTILOS = [('teja', 'rojo', 'blanco'), ('teja', 'azul', 'blanco'), ('teja', 'verde', 'crema'),
           ('teja2', 'ocre', 'blanco'), ('teja2', 'cafe', 'crema'), ('azul', 'azul', 'celeste'),
           ('morado', 'cafe', 'rosa'), ('pizarra', 'rojo', 'blanco')]
FORMAS = 6

WOOD, WOOD_D, WOOD_L = C('#9a6a3c'), C('#6b4526'), C('#c08a50')
GLASS = C('#3b4d6b')
PINE = (C('#3a7d5c'), C('#2a5f47'), C('#4f9a6d'))
LEAF_G = (C('#5fa648'), C('#447f3a'), C('#86c25e'))
LEAF_Y = (C('#e2b73a'), C('#c08f2b'), C('#f3d76a'))      # guayacán amarillo
LEAF_P = (C('#e58fb0'), C('#c56a90'), C('#f6bdd0'))      # guayacán rosado
LEAF_S = (C('#a9c9a0'), C('#7fa37d'), C('#e4f0da'))      # yarumo plateado
CANE = (C('#a3c04c'), C('#7f9c3a'), C('#c6dc72'))


# ---------------------------------------------------------------- tiles

def grass(tone, v):
    base, dark, light = GRASS[tone]
    img = Img(T, T, base)
    for i in range(7):
        x = int(rnd(i, v, tone * 7 + 1) * 16)
        y = int(rnd(i, v, tone * 7 + 2) * 15)
        if rnd(i, v, tone * 7 + 3) > 0.45:
            img.set(x, y, light)
        else:
            img.set(x, y, dark)
            img.set(x, y + 1, dark)
    return img


def background(v):
    base, dark, light = BG
    img = Img(T, T, base)
    for i in range(3):
        x = int(rnd(i, v, 41) * 12)
        y = int(rnd(i, v, 42) * 16)
        img.hline(x, x + 2, y, light if i < 2 else dark)
    return img


def strip(mask, pal, inset, kind, seed=0, line=None):
    """Tramo de vía o río que se une con los vecinos indicados en `mask`.
    En avenidas, `line` dice hacia qué vecinos sigue la línea amarilla (por defecto, todos)."""
    lm = mask if line is None else line
    base, dark, light, edge = pal
    lo, hi = inset, T - 1 - inset

    def inside(x, y):
        cx, cy = lo <= x <= hi, lo <= y <= hi
        if cx and cy:
            return True
        if cy and x < lo:
            return bool(mask & W)
        if cy and x > hi:
            return bool(mask & E)
        if cx and y < lo:
            return bool(mask & N)
        if cx and y > hi:
            return bool(mask & S)
        return False

    img = Img(T, T)
    for y in range(T):
        for x in range(T):
            if not inside(x, y):
                continue
            if not (inside(x - 1, y) and inside(x + 1, y) and inside(x, y - 1) and inside(x, y + 1)):
                img.set(x, y, edge)
                continue
            r = rnd(x, y, mask + (0 if kind == 'water' else seed))
            c = base
            if kind == 'avenue':
                c = dark if r < 0.10 else (light if r < 0.16 else base)
                cx_, cy_ = x in (7, 8), y in (7, 8)
                arm = ((lm & E and x >= 8) or (lm & W and x <= 7)) and y == 7 \
                    or ((lm & S and y >= 8) or (lm & N and y <= 7)) and x == 7
                if arm and ((x if y == 7 else y) // 2) % 2 == 0 and not (cx_ and cy_ and bin(lm).count('1') > 2):
                    c = LINE
            elif kind == 'road':
                c = dark if r < 0.07 else (light if r < 0.15 else base)
            elif kind == 'water':
                # `seed` desplaza los brillos: con dos valores se obtiene la animación del río
                if (y + seed * 2) % 5 == 2 and rnd((x + seed * 2) // 3, y, 0) < 0.35:
                    c = light
                elif r < 0.10:
                    c = dark
            img.set(x, y, c)
    return img


def cliff(left_end, right_end, v):
    base, dark, light, deep = STONE
    img = Img(T, T)
    img.rect(0, 0, T, 11, base)
    img.hline(0, T - 1, 0, light)
    img.hline(0, T - 1, 9, dark)
    img.hline(0, T - 1, 10, deep)
    for i in range(4):
        x = int(rnd(i, v, 51) * 15)
        y0 = 2 + int(rnd(i, v, 52) * 4)
        img.vline(x, y0, y0 + 2 + int(rnd(i, v, 53) * 3), dark)
        img.set(x + 1, y0, light)
    img.rect(0, 11, T, 2, (30, 70, 72, 110))      # sombra sobre el fondo
    if left_end:
        img.vline(0, 0, 10, deep)
    if right_end:
        img.vline(T - 1, 0, 10, deep)
    return img


def edge(mask):
    """Borde oscuro en los lados del tile que dan al vacío."""
    img = Img(T, T)
    if mask & N:
        img.hline(0, T - 1, 0, OUT_G)
    if mask & S:
        img.hline(0, T - 1, T - 1, OUT_G)
    if mask & W:
        img.vline(0, 0, T - 1, OUT_G)
    if mask & E:
        img.vline(T - 1, 0, T - 1, OUT_G)
    return img


# ---------------------------------------------------------------- casas

def house(estilo, v):
    """Casa de 1 tile de ancho.
    v: 0 una planta, 1 con chimenea, 2 dos plantas con balcón, 3 hastial al frente, 4 tienda, 5 edificio."""
    roof, trim, wall = ESTILOS[estilo]
    R, Rd, Rl = ROOFS[roof]
    TR = TRIMS[trim]
    WL, WD = WALLS[wall]
    if v == 5:
        return _edificio(TR)
    tall = v == 2
    h = 26 if tall else 20
    wall_h = 14 if tall else 8
    img = Img(16, h)
    wy = h - 1 - wall_h                       # primera fila del muro
    img.rect(2, wy, 12, wall_h, WL)
    img.rect(11, wy, 3, wall_h, WD)
    ry = 3
    if v == 3:
        # hastial: las dos aguas bajan desde la cumbrera y dejan ver el muro triangular
        for k in range(7):
            y = 2 + k
            xl, xr = 7 - k, 8 + k
            if k >= 2:
                img.hline(xl + 2, xr - 2, y, WL)
            img.hline(xl, xl + 1, y, Rl if k < 6 else Rd)
            img.hline(xr - 1, xr, y, Rd if k == 6 else R)
        img.rect(2, 9, 12, 2, WL)
        img.rect(11, 9, 3, 2, WD)
        img.rect(7, 5, 2, 2, GLASS)
    else:
        img.hline(2, 13, wy, WD)              # sombra del alero
        for y in range(ry, wy):
            k = y - ry
            x0 = 2 if k == 0 else 1
            img.hline(x0, 15 - x0, y, R)
            if k % 2 == 1 and y < wy - 1:
                for x in range(2 + (k // 2 % 2) * 2, 14, 4):
                    img.set(x, y, Rd)
        img.hline(2, 13, ry, Rl)
        img.hline(1, 14, wy - 1, Rd)
    if v == 1:
        img.rect(10, 1, 2, 3, STONE[0])
        img.set(11, 1, STONE[1])
    img.hline(2, 13, h - 2, TR)               # zócalo de color
    if v == 4:
        for x in range(2, 14):                # toldo a rayas
            img.set(x, wy + 1, TR if x % 2 == 0 else WL)
            img.set(x, wy + 2, TR if x % 2 == 0 else WL)
        img.rect(3, h - 6, 5, 3, GLASS)
        img.set(4, h - 5, C('#8fb0d0'))
        img.rect(10, h - 6, 2, 5, TR)
    else:
        door_x = 4 if v == 1 else 7
        img.rect(door_x, h - 5, 2, 4, TR)
        img.set(door_x + 1, h - 3, WL)
        for wx in ((8, 11) if v == 1 else (3, 11)):
            img.rect(wx, h - 6, 2, 2, GLASS)
    if tall:
        for wx in (3, 7, 11):
            img.rect(wx, wy + 2, 2, 3, GLASS)
        img.hline(2, 13, wy + 6, TR)          # balcón corrido
        for x in range(2, 14, 2):
            img.set(x, wy + 5, TR)
    return img.outline(OUT)


def _edificio(accent):
    """Edificio de 4 pisos para el centro."""
    L, M, D = C('#dedbd0'), C('#bdb9ab'), C('#8a8676')
    img = Img(16, 31)
    img.rect(2, 5, 12, 25, L)
    img.rect(11, 5, 3, 25, M)
    img.hline(2, 13, 5, D)
    img.rect(9, 2, 3, 3, M)                   # tanque de agua
    img.hline(9, 11, 2, L)
    for f in range(4):
        y = 8 + f * 5
        for wx in (3, 6, 9):
            img.rect(wx, y, 2, 3, GLASS)
        img.set(12, y, D)
        img.hline(2, 13, y + 3, accent if f % 2 == 0 else M)
    img.rect(7, 26, 2, 4, D)
    return img.outline(OUT)


# ---------------------------------------------------------------- vegetación

def pine(v):
    """v: 0 alto de tres pisos, 1 joven de dos pisos."""
    base, dark, light = PINE
    img = Img(16, 27)
    img.rect(7, 21, 2, 5, WOOD_D)
    for tier in range(v, 3):
        top = 1 + tier * 5
        for r in range(9):
            hw = (r * (4 + tier)) // 8
            y = top + r
            for x in range(7 - hw, 9 + hw):
                c = base
                if x - 7.5 < -hw * 0.35:
                    c = light
                elif x - 7.5 > hw * 0.45 or r == 8:
                    c = dark
                img.set(x, y, c)
    return shadow(img.outline(OUT), 7.5, 25.5, 5.0)


def shadow(img, cx, cy, rx):
    """Sombra suave en el suelo, solo donde el sprite es transparente."""
    for y in range(int(cy - 2), int(cy + 2)):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if ((x - cx) / rx) ** 2 + ((y - cy) / 1.6) ** 2 <= 1.0 and img.get(x, y)[3] == 0:
                img.set(x, y, (28, 52, 40, 80))
    return img


def round_tree(pal, v, trunk=None):
    base, dark, light = pal
    img = Img(16, 24)
    img.rect(7, 15, 2, 7, trunk or WOOD_D)
    img.set(7, 16, WOOD if trunk is None else C('#f2efe2'))
    cx, cy, r = 7.5, 8.0 + (v % 2), 6.3
    for y in range(24):
        for x in range(16):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= r * r:
                c = base
                if (dx + 2) ** 2 + (dy + 2.5) ** 2 <= 8:
                    c = light
                elif dx + dy > 4.5:
                    c = dark
                elif rnd(x, y, 70 + v) < 0.16:     # racimos de hojas
                    c = dark if dx + dy > 0 else light
                img.set(x, y, c)
    return shadow(img.outline(OUT), 7.5, 22.0, 5.0)


def palma():
    """Palma de cera: tronco claro y muy alto con penacho pequeño."""
    img = Img(16, 32)
    trunk, ring = C('#ddd8c6'), C('#aaa48f')
    for y in range(8, 31):
        img.set(7, y, ring if y % 4 == 0 else trunk)
        img.set(8, y, ring if y % 4 == 0 else C('#c4bea9'))
    base, dark, light = PINE
    for (x, y) in ((1, 4), (2, 9), (14, 4), (13, 9), (7, 1), (4, 2), (11, 2)):
        img.line(7 if x < 8 else 8, 7, x, y, dark if y > 5 else base)
    for (x, y) in ((2, 4), (13, 4), (5, 2), (10, 2), (7, 2)):
        img.set(x, y + 1, light)
    img.rect(7, 6, 2, 2, dark)
    return img.outline(OUT)


def guadua():
    """Mata de guadua: varios tallos delgados que se abren arriba."""
    base, dark, light = CANE
    img = Img(16, 27)
    for i, (x0, x1, top) in enumerate(((7, 3, 4), (8, 8, 1), (9, 13, 5), (6, 5, 9))):
        img.line(x0, 25, x1, top, base if i % 2 == 0 else dark)
        for k in range(3):
            img.set(x1 - 1 + k, top + (k % 2), light)
            img.set(x1 - 2 + k * 2, top + 2, LEAF_G[0])
        for y in range(top + 5, 25, 5):
            img.set(int(round(x0 + (x1 - x0) * (25 - y) / float(25 - top))), y, light)
    return img.outline(OUT)


def bush(pal):
    base, dark, light = pal
    img = Img(12, 9)
    img.ellipse(5.5, 4.5, 4.4, 2.9, base)
    img.hline(3, 5, 3, light)
    img.hline(5, 8, 6, dark)
    return img.outline(OUT)


def flores(v):
    img = Img(12, 8)
    petals = (C('#e2473f'), C('#f3d76a'), C('#f6f1e4'), C('#e58fb0'))
    for i, (x, y) in enumerate(((1, 2), (4, 4), (7, 1), (9, 5), (5, 6), (2, 6))):
        img.set(x, y + 1, LEAF_G[1])
        img.set(x, y, petals[(i + v) % 4])
    return img


def roca(v):
    base, dark, light, deep = STONE
    img = Img(12, 9)
    img.ellipse(5.5, 5.0, 4.2 - v, 2.8, base)
    img.hline(3, 5, 3, light)
    img.hline(5, 8 - v, 6, dark)
    return img.outline(OUT)


# ---------------------------------------------------------------- carros (celdas de 16x16)

CARROS = [  # (carrocería, sombra, tipo)
    (C('#d2493c'), C('#a23229'), 'auto'),
    (C('#3f6fb5'), C('#2c4f85'), 'auto'),
    (C('#eeeae0'), C('#bfbaaa'), 'auto'),
    (C('#f2c230'), C('#c2931c'), 'taxi'),
    (C('#4f8a4a'), C('#386636'), 'jeep'),
    (C('#f0ece2'), C('#3f8f9c'), 'buseta'),
]
TIRE, LAMP, TAIL = C('#2a2733'), C('#ffe98a'), C('#c8322c')
CARGA = C('#d39a25')


def carro(i, vista):
    """vista: 0 de lado mirando a la derecha, 1 bajando (de frente), 2 subiendo (de espaldas)."""
    body, shade, kind = CARROS[i]
    img = Img(16, 16)
    largo = kind == 'buseta'
    if vista == 0:
        x0, x1 = (1, 14) if largo else (2, 13)
        top = 4 if largo else 6
        img.rect(x0, 9, x1 - x0 + 1, 4, body)
        img.hline(x0, x1, 12, shade)
        if kind == 'jeep':
            img.rect(8, 6, 2, 3, body)                 # parabrisas
            img.set(9, 7, GLASS)
            img.rect(3, 6, 4, 3, CARGA)                # carga de racimos
            img.set(4, 6, C('#7f9c3a'))
            img.set(6, 7, C('#b8801c'))
        else:
            cx0, cx1 = (x0, x1 - 1) if largo else (x0 + 2, x1 - 3)
            img.rect(cx0, top, cx1 - cx0 + 1, 9 - top, body)
            for x in range(cx0 + 1, cx1, 3 if largo else 4):
                img.rect(x, top + 1, 2, 2, GLASS)
            if largo:
                img.hline(x0, x1, 9, shade)
                img.hline(cx0, cx1, top, shade)
            if kind == 'taxi':
                img.hline(x0 + 4, x0 + 6, top - 1, TIRE)
        img.set(x1, 10, LAMP)
        img.set(x0, 10, TAIL)
        for wx in (x0 + 2, x1 - 3):
            img.rect(wx, 12, 2, 2, TIRE)
    else:
        y0, y1 = (2, 14) if largo else (4, 13)
        img.rect(4, y0, 8, y1 - y0 + 1, body)
        img.vline(11, y0, y1, shade)
        if kind == 'jeep':
            if vista == 1:
                img.rect(5, y0 + 1, 6, 4, CARGA)
                img.hline(5, 10, y0 + 6, GLASS)
            else:
                img.hline(5, 10, y0 + 2, GLASS)
                img.rect(5, y0 + 4, 6, 4, CARGA)
        else:
            roof0 = y0 + (2 if vista == 1 else 4)
            roof1 = y1 - (4 if vista == 1 else 2)
            img.rect(5, roof0, 6, roof1 - roof0 + 1, shade if largo else body)
            img.rect(5, roof1 + 1 if vista == 1 else roof0 - 2, 6, 2, GLASS)
            if kind == 'taxi':
                img.hline(6, 9, (roof0 + roof1) // 2, TIRE)
        for lx in (5, 10):
            img.set(lx, y1 if vista == 1 else y0, LAMP if vista == 1 else TAIL)
        for wy in (y0 + 1, y1 - 2):
            img.rect(3, wy, 1, 2, TIRE)
            img.rect(12, wy, 1, 2, TIRE)
    return img.outline(OUT)


# ---------------------------------------------------------------- hitos

def _spire(img, x0, x1, y_base, y_top, pal):
    """Aguja que se estrecha desde [x0, x1] en y_base hasta 2 px en y_top."""
    L, M, D = pal
    span = y_base - y_top
    cx = (x0 + x1) / 2.0
    half = (x1 - x0 + 1) / 2.0
    for y in range(y_top, y_base + 1):
        t = (y - y_top) / float(span)
        hw = 1 + (half - 1) * t
        for x in range(int(round(cx - hw + 0.5)), int(round(cx + hw - 0.5)) + 1):
            img.set(x, y, L if x < cx - hw * 0.3 else (D if x > cx + hw * 0.3 else M))


def catedral():
    """Catedral Basílica de Manizales: neogótica de concreto, aguja central y torres laterales."""
    L, M, D = C('#d2cfc1'), C('#b0ac9c'), C('#8a8676')
    DK = C('#5e5b52')
    GOLD = C('#e0b84c')
    img = Img(48, 84)
    pal = (L, M, D)
    c = 23.5
    # nave
    img.rect(8, 50, 32, 32, M)
    img.rect(8, 50, 3, 32, L)
    img.rect(36, 50, 4, 32, D)
    # torres laterales
    for x0 in (5, 33):
        img.rect(x0, 38, 10, 44, M)
        img.rect(x0, 38, 2, 44, L)
        img.rect(x0 + 8, 38, 2, 44, D)
        _spire(img, x0, x0 + 9, 37, 18, pal)
        img.vline(x0 + 4, 14, 17, DK)
        img.hline(x0 + 3, x0 + 5, 15, DK)
        for wy in (42, 52, 62):
            img.rect(x0 + 4, wy, 2, 6, GLASS)
            img.set(x0 + 4, wy, DK)
        img.hline(x0, x0 + 9, 49, D)
        img.hline(x0, x0 + 9, 60, D)
        img.rect(x0 + 3, 74, 4, 8, DK)
        img.hline(x0 + 4, x0 + 5, 73, DK)
    # torre central
    img.rect(17, 28, 14, 54, M)
    img.rect(17, 28, 3, 54, L)
    img.rect(28, 28, 3, 54, D)
    _spire(img, 17, 30, 27, 5, pal)
    img.vline(23, 0, 5, GOLD)
    img.vline(24, 0, 5, GOLD)
    img.hline(22, 25, 2, GOLD)
    img.hline(17, 30, 28, D)
    img.hline(17, 30, 40, D)
    for wx in (20, 26):
        img.rect(wx, 31, 2, 7, GLASS)
        img.set(wx, 31, DK)
    # rosetón
    img.disc(c, 48.5, 4.2, DK)
    img.disc(c, 48.5, 3.0, C('#5b7fb0'))
    img.disc(c, 48.5, 1.0, GOLD)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        img.set(int(c + dx + 0.5), int(48.5 + dy), C('#c8553d'))
    # portada principal en arco apuntado
    img.rect(20, 66, 8, 16, DK)
    img.hline(21, 26, 65, DK)
    img.hline(22, 25, 64, DK)
    img.hline(23, 24, 63, DK)
    img.rect(21, 68, 6, 14, WOOD_D)
    img.vline(23, 68, 81, WOOD)
    img.vline(24, 68, 81, DK)
    # atrio
    img.rect(3, 80, 42, 2, L)
    img.hline(3, 44, 81, D)
    return img.outline(OUT)


def torre_chipre():
    """Torre al Cielo (Chipre): fuste esbelto con mirador en voladizo."""
    L, M, D = C('#f1f2ee'), C('#d1d6d8'), C('#9aa4ad')
    RED = C('#d24c3e')
    img = Img(26, 64)
    # fuste con leve ensanche en la base
    for y in range(20, 62):
        hw = 2 if y < 50 else 2 + (y - 50) // 4
        for x in range(12 - hw + 1, 13 + hw):
            img.set(x, y, L if x <= 11 else (D if x >= 12 + hw else M))
    img.vline(13, 20, 61, M)
    # mirador
    for i, hw in enumerate((5, 9, 11, 9, 6)):
        y = 14 + i
        for x in range(13 - hw, 13 + hw):
            img.set(x, y, L if i == 0 else (D if i == 4 else M))
    for x in range(4, 22, 2):
        img.set(x, 16, GLASS)
    img.hline(3, 22, 13, RED)                 # baranda del corredor volado
    # cabina y antena
    img.rect(10, 8, 6, 5, M)
    img.rect(10, 8, 2, 5, L)
    img.hline(11, 14, 10, GLASS)
    img.vline(12, 1, 7, D)
    img.vline(13, 3, 7, M)
    img.set(12, 1, RED)
    img.rect(8, 62, 10, 1, D)
    return img.outline(OUT)


def torre_cable():
    """Torre de Herveo (El Cable): torre de madera en celosía."""
    img = Img(26, 62)
    top_y, bot_y = 8, 60
    lx0, rx0, lx1, rx1 = 9, 16, 2, 23

    def span(y):
        t = (y - top_y) / float(bot_y - top_y)
        return int(round(lx0 + (lx1 - lx0) * t)), int(round(rx0 + (rx1 - rx0) * t))

    for y in range(top_y, bot_y + 1):
        lx, rx = span(y)
        img.set(lx, y, WOOD_L)
        img.set(lx + 1, y, WOOD)
        img.set(rx, y, WOOD_D)
        img.set(rx - 1, y, WOOD)
    levels = [8, 16, 25, 35, 47, 60]
    for a, b in zip(levels, levels[1:]):
        la, ra = span(a)
        lb, rb = span(b)
        img.line(la + 1, a, rb - 1, b, WOOD_D)
        img.line(ra - 1, a, lb + 1, b, WOOD)
        img.hline(lb, rb, b, WOOD_L)
    img.hline(9, 16, 8, WOOD_L)
    # caseta superior con techo de teja
    img.rect(7, 4, 12, 4, WOOD)
    img.hline(7, 18, 7, WOOD_D)
    R, Rd, Rl = ROOFS['teja']
    img.hline(8, 17, 3, R)
    img.hline(10, 15, 2, R)
    img.hline(12, 13, 1, Rl)
    img.hline(6, 19, 4, Rd)
    return img.outline(OUT)


def pin():
    """Marcador provisional para hitos que aún no tienen sprite propio."""
    img = Img(11, 15)
    red, dark = C('#e2473f'), C('#a52f2f')
    img.disc(5, 5, 4.2, red)
    for i in range(5):
        img.hline(5 - (4 - i) // 2, 5 + (4 - i) // 2, 9 + i, red if i < 3 else dark)
    img.disc(5, 5, 1.5, C('#fff4e0'))
    return img.outline(OUT)


# ---------------------------------------------------------------- catálogo de objetos del mapa

def catalogo():
    """Lista ordenada (nombre, sprite) de todo lo que cabe en una celda de 16x32 de la capa de objetos."""
    items = []
    for v in range(FORMAS):
        for e in range(len(ESTILOS) if v != 5 else 4):
            items.append(('casa_%d_%d' % (v, e), house(e, v)))
    items += [('pino_0', pine(0)), ('pino_1', pine(1)),
              ('arbol_0', round_tree(LEAF_G, 0)), ('arbol_1', round_tree(LEAF_G, 1)),
              ('guayacan_0', round_tree(LEAF_Y, 0)), ('guayacan_1', round_tree(LEAF_Y, 1)),
              ('guayacan_rosado_0', round_tree(LEAF_P, 0)), ('guayacan_rosado_1', round_tree(LEAF_P, 1)),
              ('yarumo_0', round_tree(LEAF_S, 0, C('#cfc9b8'))), ('yarumo_1', round_tree(LEAF_S, 1, C('#cfc9b8'))),
              ('palma_0', palma()), ('guadua_0', guadua()),
              ('arbusto_0', bush(LEAF_G)), ('arbusto_1', bush(PINE)),
              ('flores_0', flores(0)), ('flores_1', flores(1)), ('roca_0', roca(0)), ('roca_1', roca(1))]
    return items
