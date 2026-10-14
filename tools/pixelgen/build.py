"""Arma el mapa de Manizales a partir de las capas de Reference/ y de OpenStreetMap, y lo deja listo para Godot.

Uso: python build.py        (antes, una vez: python georef.py para la transformación lon/lat -> tile)
Genera:
  Tiles/manizales_tiles.png, manizales_objetos.png, manizales_montanas.png, manizales_tileset.tres
  Sprites/carros.png, Sprites/cabina.png, Sprites/nube_*.png, Sprites/hitos/*.png
  Shaders/vaiven.tres (material de los árboles)
  Scenes/ManizalesPixel.tscn        (se reescribe entera: no editarla a mano, editar este script)
  data/mapa.json                    (rejilla, comunas, vías, hitos: lo usará la capa de clima)
  tools/previews/*.png              (vistas de control)
Fuentes: capas de Reference/ alineadas como sus Sprite2D en Scenes/Manizales.tscn; avenidas, hitos y cable
aéreo de OpenStreetMap (© colaboradores de OpenStreetMap, ODbL) en data/osm/.
"""
import base64
import json
import math
import os
import struct
import sys
from collections import deque

import art
import art_extra as X
import comunas as comunas_mod
import hitos_info
import px
from px import Img, rnd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
REF = os.path.join(ROOT, 'Reference')
PREV = os.path.join(ROOT, 'tools', 'previews')
DATA = os.path.join(ROOT, 'data')

SCALE = 3            # escala de los Sprite2D de referencia en la escena
CELL = 42            # px de mundo de la escena vieja que ocupa un tile nuevo (= 14 px de la referencia)
MARGIN = 4           # tiles de fondo alrededor
T = art.T
N, E, S, W = art.N, art.E, art.S, art.W
COLS = 64            # columnas del atlas de tiles
OBJ_COLS, OBJ_H = 16, 32
MT_W, MT_H = 96, 64  # celda del atlas de montañas
SRC_TILES, SRC_OBJ, SRC_MT = 0, 1, 2
ROW_GRASS, ROW_BG, ROW_CLIFF, ROW_EDGE, ROW_RIVER, ROW_AV, ROW_ST, ROW_PLAZA, ROW_AV2 = range(9)
# avenidas: un tile por (vecinos con vía, vecinos que son avenida) -> la línea amarilla solo sigue la avenida
AV_PAIRS = [(m, l) for m in range(16) for l in range(16) if l & ~m == 0]
RIVER_FRAMES = 4
ROAD_REACH = 12      # tiles que una avenida puede salir de la ciudad antes de cortarse

# archivo, centro del Sprite2D en la escena
LAYERS = {
    'comunas': ('Comunas.png', 3452, 2176),
    'calles':  ('Calles.png', 4290, 2394),
    'barrios': ('Barrios.png', 3852, 2357),
    'agua':    ('Agua.png', 4161, 2581),
    'lugares': ('lugares.png', 3256, 2545),
}

# sprite, nombre, marcador de lugares.png (si Jerson lo identificó) o coordenadas reales (lat, lon) de OSM
HITOS = [
    ('colonizadores', 'Monumento a los Colonizadores', 1, None),
    ('torre_chipre', 'Torre al Cielo', 2, None),
    ('gobernacion', 'Gobernación de Caldas', 3, None),
    ('catedral', 'Catedral Basílica', 5, None),
    ('bolivar', 'Plaza de Bolívar', None, (5.06802, -75.51755)),
    ('mall_plaza', 'Mall Plaza', 6, None),
    ('ecoparque', 'Ecoparque Alcázares', 7, None),
    ('plaza_toros', 'Plaza de Toros', 9, None),
    ('ecoparque', 'Ecoparque Los Yarumos', None, (5.06782, -75.48308)),
    ('torre_cable', 'Torre de Herveo · El Cable', None, (5.05616, -75.48641)),
    ('universidad', 'U. Nacional · Palogrande', None, (5.05690, -75.49159)),
    ('recinto', 'Recinto del Pensamiento', None, (5.04046, -75.44562)),
    ('estadio', 'Estadio Palogrande', None, (5.05703, -75.49009)),
    ('bosque', 'Bosque Popular El Prado', None, (5.03497, -75.47781)),
]
SPRITES = {
    'catedral': art.catedral, 'torre_chipre': art.torre_chipre, 'torre_cable': art.torre_cable,
    'colonizadores': X.colonizadores, 'gobernacion': X.gobernacion, 'bolivar': X.bolivar,
    'mall_plaza': X.mall_plaza, 'plaza_toros': X.plaza_toros, 'ecoparque': X.ecoparque,
    'universidad': X.universidad, 'recinto': X.recinto, 'estacion_cable': X.estacion_cable,
    'estadio': X.estadio, 'bosque': X.bosque, 'nevado': lambda: X.mountain(96, 64, 9, nevado=True),
}
NEVADO = (152, 50)   # el Nevado del Ruiz queda al oriente-sureste; se pinta al fondo, fuera de escala
MONTANAS = [(88, 58), (72, 50), (60, 42), (52, 36), (44, 30), (36, 24)]


# ------------------------------------------------------------------ lectura de capas

def ink_counts(name, origin):
    """{(cx, cy): nº de píxeles con tinta} de una capa, ya en coordenadas de tile."""
    fname, pcx, pcy = LAYERS[name]
    img = px.load(os.path.join(REF, fname))
    transparent_bg = img.d[3] == 0
    ox, oy = origin
    counts = {}
    stride = img.w * 4
    for y in range(img.h):
        row = img.d[y * stride:(y + 1) * stride]
        if transparent_bg:
            marks = row[3::4]
            if max(marks) <= 80:
                continue
            xs = [x for x, a in enumerate(marks) if a > 80]
        else:
            xs = [x for x in range(img.w) if min(row[x * 4:x * 4 + 3]) < 200]
        cy = int((pcy + SCALE * (y - img.h / 2.0) - oy) // CELL)
        for x in xs:
            cx = int((pcx + SCALE * (x - img.w / 2.0) - ox) // CELL)
            counts[(cx, cy)] = counts.get((cx, cy), 0) + 1
    return counts, img


def thin(counts, minimum):
    """Celdas con tinta suficiente; repara uniones en diagonal para que la línea no se corte."""
    cells = {c for c, n in counts.items() if n >= minimum}
    for (x, y) in list(cells):
        for dx in (-1, 1):
            if (x + dx, y + 1) in cells and (x + dx, y) not in cells and (x, y + 1) not in cells:
                a, b = (x + dx, y), (x, y + 1)
                cells.add(a if counts.get(a, 0) >= counts.get(b, 0) else b)
    return cells


RING = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def skeleton(cells, counts):
    """Adelgaza a 1 tile de ancho: quita celdas de bloques 2x2 sin cortar la línea."""
    cells = set(cells)
    changed = True
    while changed:
        changed = False
        for (x, y) in sorted(cells, key=lambda c: (counts.get(c, 0), c)):
            if (x, y) not in cells:
                continue
            in_block = any(all((x + a + i, y + b + j) in cells for i in (0, 1) for j in (0, 1))
                           for a in (-1, 0) for b in (-1, 0))
            if not in_block:
                continue
            ring = [(x + dx, y + dy) in cells for dx, dy in RING]
            if 2 <= sum(ring) <= 6 and sum(1 for i in range(8) if not ring[i] and ring[(i + 1) % 8]) == 1:
                cells.discard((x, y))
                changed = True
    return cells


def nmask(cells, x, y):
    return (N if (x, y - 1) in cells else 0) | (E if (x + 1, y) in cells else 0) \
        | (S if (x, y + 1) in cells else 0) | (W if (x - 1, y) in cells else 0)


def components(cells):
    out, seen = [], set()
    for c in cells:
        if c not in seen:
            comp = set(bfs_dist([c], lambda nb: nb in cells))
            seen |= comp
            out.append(comp)
    return out


def grid():
    """Origen (en px de la escena vieja) y tamaño de la rejilla: caja de la capa de comunas + margen."""
    fname, pcx, pcy = LAYERS['comunas']
    cw, ch = 2278, 1422
    origin = (pcx - SCALE * cw / 2.0 - MARGIN * CELL, pcy - SCALE * ch / 2.0 - MARGIN * CELL)
    return origin, int(SCALE * cw // CELL) + 1 + 2 * MARGIN, int(SCALE * ch // CELL) + 1 + 2 * MARGIN


def vnoise(x, y, seed, scale):
    """Ruido de valor suavizado (0..1) para agrupar cosas en manchas."""
    fx, fy = x / scale, y / scale
    ix, iy = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = rnd(ix, iy, seed) + (rnd(ix + 1, iy, seed) - rnd(ix, iy, seed)) * tx
    b = rnd(ix, iy + 1, seed) + (rnd(ix + 1, iy + 1, seed) - rnd(ix, iy + 1, seed)) * tx
    return a + (b - a) * ty


def bfs_dist(sources, passable, limit=10 ** 6, diag=False):
    dist = {c: 0 for c in sources}
    dq = deque(sources)
    steps = RING if diag else ((1, 0), (-1, 0), (0, 1), (0, -1))
    while dq:
        x, y = dq.popleft()
        if dist[(x, y)] >= limit:
            continue
        for dx, dy in steps:
            nb = (x + dx, y + dy)
            if nb not in dist and passable(nb):
                dist[nb] = dist[(x, y)] + 1
                dq.append(nb)
    return dist


# ------------------------------------------------------------------ mapa

def load_markers(origin):
    """Punta inferior de cada marcador rojo de lugares.png, en coordenadas de tile (id desde 1)."""
    _, lug = ink_counts('lugares', origin)
    _, lcx, lcy = LAYERS['lugares']
    seen, out = set(), []
    stride = lug.w * 4
    for y in range(lug.h):
        for x in range(lug.w):
            if lug.d[y * stride + x * 4 + 3] > 80 and (x, y) not in seen:
                comp, dq = [], deque([(x, y)])
                seen.add((x, y))
                while dq:
                    a, b = dq.popleft()
                    comp.append((a, b))
                    for na, nb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= na < lug.w and 0 <= nb < lug.h and (na, nb) not in seen \
                                and lug.d[nb * stride + na * 4 + 3] > 80:
                            seen.add((na, nb))
                            dq.append((na, nb))
                if len(comp) < 20:
                    continue
                by = max(b for _, b in comp)
                tips = [a for a, b in comp if b == by]
                bx = sum(tips) / float(len(tips))
                out.append({'id': len(out) + 1,
                            'x': round((lcx + SCALE * (bx - lug.w / 2.0) - origin[0]) / CELL, 2),
                            'y': round((lcy + SCALE * (by - lug.h / 2.0) - origin[1]) / CELL, 2)})
    return out


def osm_elements(name):
    with open(os.path.join(DATA, 'osm', name), encoding='utf-8') as f:
        return json.load(f)['elements']


def build_map():
    import georef
    geo = georef.Georef.load()
    origin, GW, GH = grid()

    def inb(x, y):
        return 0 <= x < GW and 0 <= y < GH

    # tierra: todo lo que queda encerrado por los contornos de comunas
    com_counts, _ = ink_counts('comunas', origin)
    outline = {c for c in com_counts if inb(*c)}
    outside = set(bfs_dist([(0, 0)], lambda c: inb(*c) and c not in outline))
    land = {(x, y) for y in range(GH) for x in range(GW) if (x, y) not in outside}

    # comunas: componentes del interior; el contorno se reparte al vecino más cercano
    region, sizes = {}, []
    for c in sorted(land - outline, key=lambda c: (c[1], c[0])):
        if c in region:
            continue
        rid = len(sizes)
        comp = bfs_dist([c], lambda nb: nb in land and nb not in outline)
        for k in comp:
            region[k] = rid
        sizes.append(len(comp))
    small = {r for r, n in enumerate(sizes) if n < 10}
    region = {c: r for c, r in region.items() if r not in small}

    def spread():
        dq = deque(region.keys())
        while dq:
            x, y = dq.popleft()
            for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nb in land and nb not in region:
                    region[nb] = region[(x, y)]
                    dq.append(nb)

    spread()

    # avenidas reales (OSM) proyectadas a la rejilla
    av_counts, av_name = {}, {}
    for label, pts in georef.avenue_ways():
        for (gx, gy) in georef.densify([geo(*p) for p in pts], 0.3):
            c = (int(gx), int(gy))
            if inb(*c):
                av_counts[c] = av_counts.get(c, 0) + 1
                av_name.setdefault(c, label)
    av_raw = thin(av_counts, 1)
    near = bfs_dist(list(land), lambda c: inb(*c), ROAD_REACH, diag=True)
    av_raw = {c for c in av_raw if c in near}
    for _ in range(2):                         # las dobles calzadas se funden en una sola vía
        av_raw |= {(x, y) for (x, y) in near if (x, y) not in av_raw and (
            ((x, y - 1) in av_raw and (x, y + 1) in av_raw) or ((x - 1, y) in av_raw and (x + 1, y) in av_raw))}
    for (x, y) in av_raw:                      # la vía que sale de la ciudad lleva su franja de tierra
        if (x, y) not in land:
            for dx, dy in ((0, 0),) + RING:
                if inb(x + dx, y + dy):
                    land.add((x + dx, y + dy))
    spread()
    for c in land:
        region.setdefault(c, 0)
    ids = sorted(set(region.values()))
    remap = {r: i for i, r in enumerate(ids)}
    region = {c: remap[r] for c, r in region.items()}

    # tono de pasto por comuna, distinto al de sus vecinas
    adj = {i: set() for i in range(len(ids))}
    for (x, y), r in region.items():
        for nb in ((x + 1, y), (x, y + 1)):
            r2 = region.get(nb)
            if r2 is not None and r2 != r:
                adj[r].add(r2)
                adj[r2].add(r)
    tone = {}
    for r in range(len(ids)):
        used = {tone[a] for a in adj[r] if a in tone}
        tone[r] = next((t for t in ((r + k) % 4 for k in range(4)) if t not in used), r % 4)

    # calles de barrio (Barrios.png) y ríos (Agua.png)
    st_counts = ink_counts('barrios', origin)[0]
    rv_counts = ink_counts('agua', origin)[0]
    all_counts = dict(st_counts)
    for c in av_raw:
        all_counts[c] = all_counts.get(c, 0) + 1000      # al adelgazar se conserva la avenida
    st_raw = {c for c in thin(st_counts, 5) if c in land}
    net = skeleton(av_raw | st_raw, all_counts)
    avenue = net & av_raw
    street = net - avenue
    for _ in range(2):                         # calle encajonada entre dos tramos de avenida -> avenida
        fill = {(x, y) for (x, y) in street if ((x - 1, y) in avenue and (x + 1, y) in avenue)
                or ((x, y - 1) in avenue and (x, y + 1) in avenue)}
        avenue |= fill
        street -= fill
    for comp in components(avenue):            # pedazos sueltos de avenida -> calle
        if len(comp) < 5:
            avenue -= comp
            street |= comp
    river = skeleton({c for c in thin(rv_counts, 5) if inb(*c)}, rv_counts)
    road = avenue | street

    # rótulos de avenidas: la celda más central de cada una dentro de la ciudad
    labels = []
    by_name = {}
    for c in avenue:
        by_name.setdefault(av_name.get(c, ''), []).append(c)
    for name, cells in sorted(by_name.items()):
        cells = [c for c in cells if region.get(c) is not None and near.get(c, 99) == 0] or cells
        if not name or len(cells) < 6:
            continue
        mx = sum(c[0] for c in cells) / len(cells)
        my = sum(c[1] for c in cells) / len(cells)
        cx, cy = min(cells, key=lambda c: (c[0] - mx) ** 2 + (c[1] - my) ** 2)
        labels.append((name, cx, cy))

    # hitos
    markers = {m['id']: m for m in load_markers(origin)}
    hitos = []
    for key, name, marker, latlon in HITOS:
        if marker:
            gx, gy = markers[marker]['x'], markers[marker]['y']
        else:
            gx, gy = geo(latlon[1], latlon[0])
        hitos.append({'sprite': key, 'nombre': name, 'x': round(gx, 2), 'y': round(gy, 2)})

    # Plaza de Bolívar: la Gobernación al norte, la Catedral al sur y el Bolívar Cóndor al costado,
    # repartidos alrededor de la Catedral (los sprites son más grandes que la escala real).
    by_key = {h['sprite']: h for h in hitos}
    plaza = set()
    if {'catedral', 'gobernacion', 'bolivar'} <= set(by_key):
        cx, cy = by_key['catedral']['x'], by_key['catedral']['y'] - 2.0
        by_key['catedral'].update(x=round(cx, 2), y=round(cy + 2.0, 2))
        by_key['gobernacion'].update(x=round(cx, 2), y=round(cy - 2.6, 2))
        by_key['bolivar'].update(x=round(cx - 3.2, 2), y=round(cy + 0.4, 2))
        plaza = {(x, y) for x in range(int(cx) - 4, int(cx) + 3) for y in range(int(cy) - 3, int(cy) + 2)}
    for h in hitos:                            # todo hito queda sobre tierra
        gx, gy = int(h['x']), int(h['y'])
        for dx, dy in ((0, 0),) + RING:
            if inb(gx + dx, gy + dy):
                land.add((gx + dx, gy + dy))
                region.setdefault((gx + dx, gy + dy), region.get((gx, gy), 0))
    plaza = {c for c in plaza if c in land and c not in avenue}

    # cable aéreo: líneas y estaciones
    cables, stations = [], []
    for e in osm_elements('cable.json'):
        kind = e.get('tags', {}).get('aerialway')
        pts = [geo(p['lon'], p['lat']) for p in e.get('geometry', [])]
        if kind == 'gondola':
            cables.append({'nombre': e['tags'].get('name', ''), 'puntos': [(round(x, 2), round(y, 2)) for x, y in pts]})
        elif kind == 'station' and pts:
            sx = sum(p[0] for p in pts) / len(pts)
            sy = sum(p[1] for p in pts) / len(pts)
            stations.append({'nombre': 'Estación ' + e['tags'].get('name', ''), 'x': round(sx, 2), 'y': round(sy, 2)})
    for st in stations:
        hitos.append({'sprite': 'estacion_cable', 'nombre': st['nombre'], 'x': st['x'], 'y': st['y'] + 0.6, 'menor': True})

    # distancia a la vía más cercana (para sembrar casas y vegetación)
    dist = bfs_dist(list(road), lambda c: c in land)

    def density(x, y):
        return sum(1 for dy in range(-4, 5) for dx in range(-4, 5) if (x + dx, y + dy) in road)

    # hitos grandes que quedan casi en la misma fila y se tapan: se separan en horizontal
    big = [h for h in hitos if not h.get('menor') and h['sprite'] not in ('catedral', 'gobernacion', 'bolivar')]
    for a in big:
        for b in big:
            if a is b or abs(a['y'] - b['y']) > 2.0:
                continue
            gap = (SPRITES[a['sprite']]().w + SPRITES[b['sprite']]().w) / 2.0 / T + 0.3
            if a['x'] <= b['x'] and b['x'] - a['x'] < gap:
                push = gap - (b['x'] - a['x'])
                a['x'] = round(a['x'] - push / 2.0, 2)
                b['x'] = round(b['x'] + push / 2.0, 2)

    # Bosque Popular: arboleda densa alrededor de la portada
    arboleda = set()
    for h in hitos:
        if h['sprite'] == 'bosque':
            for dy in range(-6, 5):
                for dx in range(-7, 8):
                    c = (int(h['x']) + dx, int(h['y']) + dy)
                    if dx * dx / 49.0 + dy * dy / 30.0 <= 1.0 and inb(*c):
                        land.add(c)
                        region.setdefault(c, region.get((int(h['x']), int(h['y'])), 0))
                        arboleda.add(c)
    # el Nevado del Ruiz se dibuja como hito (para poder hacerle clic), fuera de escala
    hitos.append({'sprite': 'nevado', 'nombre': 'Nevado del Ruiz', 'x': NEVADO[0] + 0.5, 'y': NEVADO[1] + 1.0})

    # espacio que ocupa cada hito: ahí no van casas ni árboles
    busy = set(road) | (river & land) | plaza
    for h in hitos:
        s = SPRITES[h['sprite']]()
        hw = s.w / 2.0 / T + 0.5
        for y in range(int(h['y'] - s.h * 0.55 / T), int(h['y']) + 1):
            for x in range(int(h['x'] - hw), int(h['x'] + hw) + 1):
                busy.add((x, y))

    estilos = [0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7]
    bajas = [0, 0, 1, 1, 3, 3, 4]
    objects = []

    def casa(x, y, centro):
        k = rnd(x, y, 8)
        if centro:
            v = 2 if k < 0.30 else (5 if k < 0.45 else bajas[int(rnd(x, y, 9) * len(bajas))])
        else:
            v = 2 if k < 0.12 else bajas[int(rnd(x, y, 9) * len(bajas))]
        e = estilos[int(rnd(x, y, 10) * len(estilos))]
        return 'casa_%d_%d' % (v, e % 4 if v == 5 else e)

    for (x, y) in sorted(land, key=lambda c: (c[1], c[0])):
        if (x, y) in busy:
            continue
        if (x, y) in arboleda and (x, y) not in road:
            if rnd(x, y, 14) < 0.72:
                k = rnd(x, y, 15)
                objects.append((x, y, 'pino_0' if k < 0.35 else 'arbol_%d' % (k < 0.6) if k < 0.75
                                else 'guadua_0' if k < 0.85 else 'yarumo_0' if k < 0.93 else 'arbusto_0'))
            continue
        d = dist.get((x, y), 99)
        r = rnd(x, y, 7)
        name = None
        if d == 1 and r < 0.62:
            name = casa(x, y, density(x, y) >= 24)
        elif d == 2 and r < 0.22:
            name = casa(x, y, False)
        elif d >= 2:
            grove = rnd(x // 5, y // 5, 11)
            p = 0.08 + (0.30 if grove > 0.62 else 0.0) + (0.10 if d >= 5 else 0.0)
            v = int(rnd(x, y, 13) * 2)
            if r < p:
                k = rnd(x, y, 12)
                yellow = tone[region[(x, y)]] == 1
                if k < 0.28:
                    name = 'pino_%d' % v
                elif k < 0.40:
                    name = 'arbol_%d' % v
                elif k < (0.66 if yellow else 0.54):
                    name = 'guayacan_%d' % v
                elif k < (0.72 if yellow else 0.63):
                    name = 'guayacan_rosado_%d' % v
                elif k < 0.70:
                    name = 'yarumo_%d' % v
                elif k < 0.80:
                    name = 'guadua_0'
                elif k < 0.85:
                    name = 'palma_0'
                else:
                    name = 'arbusto_%d' % v
            elif r > 0.94:
                name = ('flores_%d' if r > 0.975 else 'roca_%d' if r > 0.96 else 'arbusto_%d') % v
        if name:
            objects.append((x, y, name))

    # montañas alrededor: en el vacío, sin tapar la ciudad (que quede despejado arriba)
    # agrupadas en cordilleras con ruido suave: bordean la ciudad y se ralean a lo lejos
    mountains = []
    taken = {NEVADO}
    dland = bfs_dist(list(land), lambda c: inb(*c), 40, diag=True)
    for (x, y) in sorted(((x, y) for y in range(GH) for x in range(GW)), key=lambda c: rnd(c[0], c[1], 90)):
        d = dland.get((x, y), 99)
        if d < 3 or (x, y) in river:
            continue
        if any((x + dx, y + dy) in land for dx in range(-3, 4) for dy in range(-4, 1)):
            continue
        n = vnoise(x, y, 93, 9.0)
        p = (0.75 if n > 0.58 else 0.04) * (1.0 if d <= 12 else 0.55)
        if rnd(x, y, 91) > p:
            continue
        if any((x + dx, y + dy) in taken for dx in range(-3, 4) for dy in range(-1, 2)) \
                or any((x + dx, y + dy) in taken for dx in range(-1, 2) for dy in range(-2, 3)):
            continue
        if abs(x - NEVADO[0]) < 7 and abs(y - NEVADO[1]) < 5:
            continue
        v = 0 if n > 0.78 else (1 if n > 0.68 else 2 + int(rnd(x, y, 92) * (len(MONTANAS) - 2)))
        if d <= 4:
            v = max(v, 3)                      # pegadas a la ciudad, colinas bajas
        taken.add((x, y))
        mountains.append((x, y, v))

    # comunas oficiales (límites de OSM): cada celda de tierra queda en la comuna que la contiene
    # o, si cae fuera del perímetro urbano, en la más cercana
    com = comunas_mod.load(geo)
    region = comunas_mod.assign(land, com)
    dq = deque(region.keys())
    while dq:
        x, y = dq.popleft()
        for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nb in land and nb not in region:
                region[nb] = region[(x, y)]
                dq.append(nb)
    centers = []
    for i in range(len(com)):
        cells = [c for c, r in region.items() if r == i]
        centers.append((sum(c[0] for c in cells) / len(cells), sum(c[1] for c in cells) / len(cells)))
    for c in land:
        if c not in region:
            region[c] = min(range(len(com)), key=lambda i: (centers[i][0] - c[0]) ** 2 + (centers[i][1] - c[1]) ** 2)
    adj = {i: set() for i in range(len(com))}
    for (x, y), r in region.items():
        for nb in ((x + 1, y), (x, y + 1)):
            r2 = region.get(nb)
            if r2 is not None and r2 != r:
                adj[r].add(r2)
                adj[r2].add(r)
    tone = {}
    for r in range(len(com)):
        used = {tone[a] for a in adj[r] if a in tone}
        tone[r] = next((t for t in ((r + k) % 4 for k in range(4)) if t not in used), r % 4)
    for i, c in enumerate(com):
        cells = sorted(cc for cc, r in region.items() if r == i)
        mx, my = centers[i]
        bx, by = min(cells, key=lambda cc: (cc[0] - mx) ** 2 + (cc[1] - my) ** 2)
        c.update(celdas=cells, insignia=(bx * T + 8, by * T + 8))
        del c['anillos']
    ids = list(range(len(com)))

    # los rótulos de avenidas no se montan sobre los nombres de los hitos
    def crowded(c):
        return any(abs(c[0] - h['x']) < 5 and -1 < c[1] - h['y'] < 4 for h in hitos if not h.get('menor'))

    for i, (name, cx, cy) in enumerate(labels):
        if crowded((cx, cy)):
            free = [c for c in by_name[name] if c in avenue and not crowded(c)]
            if free:
                labels[i] = (name,) + min(free, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)

    return {'GW': GW, 'GH': GH, 'land': land, 'region': region, 'tone': tone, 'comunas': len(ids),
            'avenue': avenue, 'street': street, 'river': river, 'plaza': plaza, 'objects': objects,
            'hitos': hitos, 'markers': list(markers.values()), 'labels': labels, 'cables': cables, 'com': com,
            'mountains': mountains}


# ------------------------------------------------------------------ atlas

def build_atlases():
    tiles = Img(COLS * T, 9 * T)

    def put(img, col, row):
        tiles.blit(img, col * T, row * T)

    for tone in range(4):
        for v in range(4):
            put(art.grass(tone, v), tone * 4 + v, ROW_GRASS)
    for v in range(6):
        put(art.background(v), v, ROW_BG)
    for i in range(16):
        put(art.cliff(bool(i & 1), bool(i & 2), i >> 2), i, ROW_CLIFF)
    for m in range(16):
        if m:
            put(art.edge(m), m, ROW_EDGE)
        for f in range(RIVER_FRAMES):
            put(art.strip(m, art.WATER, 3, 'water', f), m * RIVER_FRAMES + f, ROW_RIVER)
        put(art.strip(m, art.STREET, 4, 'road', 9), m, ROW_ST)
    for v in range(4):
        put(plaza_tile(v), v, ROW_PLAZA)
    for i, (m, l) in enumerate(AV_PAIRS):
        put(art.strip(m, art.AVENUE, 2, 'avenue', line=l), i % COLS, ROW_AV if i < COLS else ROW_AV2)

    cat = art.catalogo()
    objs = Img(OBJ_COLS * T, ((len(cat) + OBJ_COLS - 1) // OBJ_COLS) * OBJ_H)
    index = {}
    for i, (name, s) in enumerate(cat):
        assert s.w <= T and s.h <= OBJ_H, name
        cx, cy = i % OBJ_COLS, i // OBJ_COLS
        objs.blit(s, cx * T + (T - s.w) // 2, cy * OBJ_H + OBJ_H - s.h)     # centrado abajo
        index[name] = (cx, cy)

    mts = [X.mountain(w, h, i) for i, (w, h) in enumerate(MONTANAS)]
    mt_img = Img(len(mts) * MT_W, MT_H)
    for i, s in enumerate(mts):
        mt_img.blit(s, i * MT_W + (MT_W - s.w) // 2, MT_H - s.h)

    cars = Img(3 * T, len(art.CARROS) * T)
    for i in range(len(art.CARROS)):
        for v in range(3):
            cars.blit(art.carro(i, v), v * T, i * T)
    return tiles, objs, index, mt_img, cars


def plaza_tile(v):
    base, dark, light, edge = art.PLAZA
    img = Img(T, T, base)
    for y in range(T):
        for x in range(T):
            if (x // 4 + y // 4) % 2 == 0:
                img.set(x, y, light)
            if x % 4 == 0 or y % 4 == 0:
                img.set(x, y, dark if rnd(x, y, 95 + v) < 0.7 else base)
    return img


VEGETACION = ('pino', 'arbol', 'guayacan', 'yarumo', 'palma', 'guadua', 'arbusto')


def layer_cells(m, obj_index):
    """Celdas por capa: (x, y, fuente, atlas_x, atlas_y)."""
    land, region, tone = m['land'], m['region'], m['tone']
    road = m['avenue'] | m['street']
    L = {k: [] for k in ('Fondo', 'Terreno', 'Bordes', 'Rios', 'Vias', 'Plazas', 'Objetos', 'Montanas')}
    for y in range(m['GH']):
        for x in range(m['GW']):
            L['Fondo'].append((x, y, SRC_TILES, int(rnd(x, y, 2) * 6), ROW_BG))
            if (x, y) in land:
                L['Terreno'].append((x, y, SRC_TILES, tone[region[(x, y)]] * 4 + int(rnd(x, y, 1) * 4), ROW_GRASS))
                e = 15 ^ nmask(land, x, y)
                if e:
                    L['Bordes'].append((x, y, SRC_TILES, e, ROW_EDGE))
            elif (x, y - 1) in land:
                ends = (0 if (x - 1, y - 1) in land else 1) | (0 if (x + 1, y - 1) in land else 2)
                L['Terreno'].append((x, y, SRC_TILES, ends | (int(rnd(x, y, 3) * 4) << 2), ROW_CLIFF))
            if (x, y) in m['river']:
                L['Rios'].append((x, y, SRC_TILES, nmask(m['river'], x, y) * RIVER_FRAMES, ROW_RIVER))
            if (x, y) in m['avenue']:
                i = AV_PAIRS.index((nmask(road, x, y), nmask(m['avenue'], x, y)))
                L['Vias'].append((x, y, SRC_TILES, i % COLS, ROW_AV if i < COLS else ROW_AV2))
            elif (x, y) in m['street']:
                L['Vias'].append((x, y, SRC_TILES, nmask(road, x, y), ROW_ST))
            if (x, y) in m['plaza']:
                L['Plazas'].append((x, y, SRC_TILES, int(rnd(x, y, 4) * 4), ROW_PLAZA))
    for (x, y, name) in m['objects']:
        ax, ay = obj_index[name]
        L['Objetos'].append((x, y, SRC_OBJ, ax, ay))
    for (x, y, v) in m['mountains']:
        L['Montanas'].append((x, y, SRC_MT, v, 0))
    return L


# ------------------------------------------------------------------ Godot

BG_COLOR = 'Color(0.302, 0.549, 0.51, 1)'


def tile_data(cells):
    raw = struct.pack('<H', 0)
    for (x, y, src, ax, ay) in cells:
        raw += struct.pack('<hhHHHH', x, y, src, ax, ay, 0)
    return base64.b64encode(raw).decode('ascii')


def write_tileset(path, used_tiles, obj_index, obj_rows):
    out = ['[gd_resource type="TileSet" format=3]', '',
           '[ext_resource type="Texture2D" path="res://Tiles/manizales_tiles.png" id="1"]',
           '[ext_resource type="Texture2D" path="res://Tiles/manizales_objetos.png" id="2"]',
           '[ext_resource type="Texture2D" path="res://Tiles/manizales_montanas.png" id="3"]',
           '[ext_resource type="Material" path="res://Shaders/vaiven.tres" id="4"]', '',
           '[sub_resource type="TileSetAtlasSource" id="tiles"]',
           'texture = ExtResource("1")',
           'texture_region_size = Vector2i(16, 16)']
    for (ax, ay) in sorted(used_tiles, key=lambda t: (t[1], t[0])):
        if ay == ROW_RIVER:
            out.append('%d:%d/animation_speed = 3.0' % (ax, ay))
            out += ['%d:%d/animation_frame_%d/duration = 1.0' % (ax, ay, f) for f in range(RIVER_FRAMES)]
        out.append('%d:%d/0 = 0' % (ax, ay))
    out += ['', '[sub_resource type="TileSetAtlasSource" id="objetos"]',
            'texture = ExtResource("2")',
            'texture_region_size = Vector2i(16, 32)']
    for name, (ax, ay) in sorted(obj_index.items(), key=lambda kv: (kv[1][1], kv[1][0])):
        out += ['%d:%d/0 = 0' % (ax, ay),
                '%d:%d/0/texture_origin = Vector2i(0, 8)' % (ax, ay),
                '%d:%d/0/y_sort_origin = 8' % (ax, ay)]
        if name.startswith(VEGETACION):
            out.append('%d:%d/0/material = ExtResource("4")' % (ax, ay))
    out += ['', '[sub_resource type="TileSetAtlasSource" id="montanas"]',
            'texture = ExtResource("3")',
            'texture_region_size = Vector2i(%d, %d)' % (MT_W, MT_H)]
    for i in range(len(MONTANAS)):
        out += ['%d:0/0 = 0' % i,
                '%d:0/0/texture_origin = Vector2i(0, %d)' % (i, MT_H // 2 - T // 2),
                '%d:0/0/y_sort_origin = 8' % i]
    out += ['', '[resource]', 'tile_size = Vector2i(16, 16)',
            'sources/0 = SubResource("tiles")', 'sources/1 = SubResource("objetos")',
            'sources/2 = SubResource("montanas")', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out))
    with open(os.path.join(ROOT, 'Shaders', 'vaiven.tres'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(['[gd_resource type="ShaderMaterial" format=3]', '',
                           '[ext_resource type="Shader" path="res://Shaders/vaiven.gdshader" id="1"]', '',
                           '[resource]', 'shader = ExtResource("1")',
                           'shader_parameter/celdas = Vector2(%d, %d)' % (OBJ_COLS, obj_rows), '']))


def write_scene(path, m, L):
    W_, H_ = m['GW'] * T, m['GH'] * T
    keys = sorted({h['sprite'] for h in m['hitos']})
    o = ['[gd_scene format=4]', '',
         '[ext_resource type="TileSet" path="res://Tiles/manizales_tileset.tres" id="ts"]',
         '[ext_resource type="Texture2D" path="res://Sprites/carros.png" id="carros"]',
         '[ext_resource type="Texture2D" path="res://Sprites/cabina.png" id="cabina"]',
         '[ext_resource type="Texture2D" path="res://Sprites/nube_0.png" id="nube0"]',
         '[ext_resource type="Texture2D" path="res://Sprites/nube_1.png" id="nube1"]',
         '[ext_resource type="Script" path="res://Scripts/camara.gd" id="camara"]',
         '[ext_resource type="Script" path="res://Scripts/trafico.gd" id="trafico"]',
         '[ext_resource type="Script" path="res://Scripts/cable.gd" id="cable"]',
         '[ext_resource type="Script" path="res://Scripts/nubes.gd" id="nubes"]',
         '[ext_resource type="Script" path="res://Scripts/info_hitos.gd" id="info"]',
         '[ext_resource type="Script" path="res://Scripts/clima.gd" id="clima"]',
         '[ext_resource type="Script" path="res://Scripts/clima_mapa.gd" id="clima_mapa"]',
         '[ext_resource type="Script" path="res://Scripts/clima_ui.gd" id="clima_ui"]',
         '[ext_resource type="Texture2D" path="res://Sprites/clima_iconos.png" id="iconos"]',
         '[ext_resource type="Texture2D" path="res://Sprites/resplandor.png" id="resplandor"]',
         '[ext_resource type="Texture2D" path="res://Sprites/gota.png" id="gota"]']
    for key in keys:
        o.append('[ext_resource type="Texture2D" path="res://Sprites/hitos/%s.png" id="%s"]' % (key, key))
    o += ['', '[node name="ManizalesPixel" type="Node2D"]', '',
          '[node name="Agua" type="ColorRect" parent="."]',
          'offset_left = -6000.0', 'offset_top = -6000.0',
          'offset_right = %d.0' % (W_ + 6000), 'offset_bottom = %d.0' % (H_ + 6000),
          'mouse_filter = 2', 'color = %s' % BG_COLOR, '']

    def layer(name, parent='.', extra=()):
        o.append('[node name="%s" type="TileMapLayer" parent="%s"]' % (name, parent))
        o.extend(extra)
        o.append('tile_map_data = PackedByteArray("%s")' % tile_data(L[name]))
        o.append('tile_set = ExtResource("ts")')
        o.append('')

    def etiqueta(parent, name, text, x, y, size=10, z=30, color=None):
        w = max(40, len(text) * size * 0.62)
        o.extend(['[node name="%s" type="Label" parent="%s"]' % (name, parent),
                  'z_index = %d' % z,
                  'offset_left = %.1f' % (x - w / 2), 'offset_top = %.1f' % y,
                  'offset_right = %.1f' % (x + w / 2), 'offset_bottom = %.1f' % (y + size + 4),
                  'theme_override_colors/font_outline_color = Color(0.16, 0.15, 0.2, 1)',
                  'theme_override_constants/outline_size = 4',
                  'theme_override_font_sizes/font_size = %d' % size,
                  'text = "%s"' % text, 'horizontal_alignment = 1'])
        if color:
            o.append('theme_override_colors/font_color = %s' % color)
        o.append('')

    layer('Fondo')
    layer('Terreno')
    layer('Bordes')
    layer('Rios')
    layer('Vias', extra=['unique_name_in_owner = true'])
    layer('Plazas')
    o += ['[node name="Mundo" type="Node2D" parent="."]', 'y_sort_enabled = true', '']
    layer('Montanas', 'Mundo', extra=['y_sort_enabled = true'])
    layer('Objetos', 'Mundo', extra=['y_sort_enabled = true'])
    o += ['[node name="Trafico" type="Node2D" parent="Mundo"]', 'y_sort_enabled = true',
          'script = ExtResource("trafico")', 'hoja = ExtResource("carros")',
          'tipos = %d' % len(art.CARROS), '',
          '[node name="Hitos" type="Node2D" parent="Mundo"]', 'y_sort_enabled = true', '']
    used = {}
    for h in m['hitos']:
        s = SPRITES[h['sprite']]()
        tipo, texto, fuente = hitos_info.info(h['nombre'])
        base = ''.join(ch for ch in h['nombre'].title() if ch.isalnum())[:28] or h['sprite']
        used[base] = used.get(base, 0) + 1
        node = base if used[base] == 1 else '%s%d' % (base, used[base])
        o += ['[node name="%s" type="Sprite2D" parent="Mundo/Hitos"]' % node,
              'position = Vector2(%d, %d)' % (round(h['x'] * T), round(h['y'] * T)),
              'texture = ExtResource("%s")' % h['sprite'],
              'offset = Vector2(0, %s)' % (-s.h / 2.0),
              'metadata/nombre = "%s"' % h['nombre'],
              'metadata/tipo = "%s"' % tipo, 'metadata/info = "%s"' % texto, 'metadata/fuente = "%s"' % fuente, '']
        if not h.get('menor'):
            etiqueta('Mundo/Hitos/' + node, 'Nombre', h['nombre'], 0, 2, 9, color='Color(1, 0.96, 0.85, 1)')

    # cable aéreo por encima de todo lo que está en el suelo
    o += ['[node name="Cable" type="Node2D" parent="."]', 'z_index = 25',
          'script = ExtResource("cable")', 'cabina = ExtResource("cabina")', 'separacion = 70.0', '']
    for i, c in enumerate(m['cables']):
        pts = ', '.join('%.1f, %.1f' % (x * T, y * T - 14) for x, y in c['puntos'])
        o += ['[node name="Linea%d" type="Line2D" parent="Cable"]' % (i + 1),
              'points = PackedVector2Array(%s)' % pts, 'width = 1.0',
              'default_color = Color(0.17, 0.16, 0.22, 0.85)', 'metadata/nombre = "%s"' % c['nombre'], '']

    o += ['[node name="Rotulos" type="Node2D" parent="."]', 'z_index = 30', '']
    for i, (name, x, y) in enumerate(m['labels']):
        etiqueta('Rotulos', 'Via%d' % i, name, x * T + 8, y * T - 6, 8, color='Color(0.95, 0.93, 1, 1)')

    # luces de noche: farolas a lo largo de las vías y ventanas encendidas en las casas
    faroles = [((x * T + 8), (y * T + 8)) for (x, y) in sorted(m['avenue']) if (x * 7 + y * 3) % 4 == 0]         + [((x * T + 8), (y * T + 8)) for (x, y) in sorted(m['street']) if (x * 5 + y * 3) % 7 == 0]
    ventanas = [(x * T + 8, (y + 1) * T - 7) for (x, y, name) in m['objects'] if name.startswith('casa')]
    ventanas += [(h['x'] * T, h['y'] * T - 12) for h in m['hitos'] if h['sprite'] not in ('nevado', 'bolivar')]

    def packed(pts):
        return 'PackedVector2Array(%s)' % ', '.join('%.1f, %.1f' % p for p in pts)

    o += ['[node name="Clima" type="Node" parent="."]', 'unique_name_in_owner = true',
          'script = ExtResource("clima")', '',
          '[node name="ClimaMapa" type="Node2D" parent="." node_paths=PackedStringArray("nubes")]',
          'unique_name_in_owner = true', 'z_index = 34', 'script = ExtResource("clima_mapa")',
          'nubes = NodePath("../Nubes")', 'resplandor = ExtResource("resplandor")', 'gota = ExtResource("gota")',
          'iconos = ExtResource("iconos")', 'faroles = %s' % packed(faroles), 'ventanas = %s' % packed(ventanas), '',
          '[node name="ClimaUI" type="CanvasLayer" parent="."]', 'layer = 6',
          'script = ExtResource("clima_ui")', 'iconos = ExtResource("iconos")', '']
    o += ['[node name="Nubes" type="Node2D" parent="."]', 'z_index = 40',
          'script = ExtResource("nubes")',
          'texturas = Array[Texture2D]([ExtResource("nube0"), ExtResource("nube1")])',
          'area = Rect2(0, 0, %d, %d)' % (W_, H_), '',
          '[node name="Info" type="CanvasLayer" parent="." node_paths=PackedStringArray("hitos")]', 'layer = 5',
          'script = ExtResource("info")', 'hitos = NodePath("../Mundo/Hitos")', '',
          '[node name="Creditos" type="CanvasLayer" parent="."]', '',
          '[node name="Texto" type="Label" parent="Creditos"]',
          'anchors_preset = 3', 'anchor_left = 1.0', 'anchor_top = 1.0', 'anchor_right = 1.0', 'anchor_bottom = 1.0',
          'offset_left = -260.0', 'offset_top = -20.0', 'offset_right = -6.0', 'offset_bottom = -4.0',
          'grow_horizontal = 0', 'grow_vertical = 0',
          'theme_override_colors/font_outline_color = Color(0.16, 0.15, 0.2, 1)',
          'theme_override_constants/outline_size = 3', 'theme_override_font_sizes/font_size = 9',
          'text = "Vías, hitos y cable: © colaboradores de OpenStreetMap"', 'horizontal_alignment = 2', '',
          '[node name="Camara" type="Camera2D" parent="."]',
          'position = Vector2(%d, %d)' % (int(W_ * 0.36), int(H_ * 0.5)),
          'script = ExtResource("camara")',
          'limite = Rect2(0, 0, %d, %d)' % (W_, H_), '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(o))


# ------------------------------------------------------------------ vista previa

def render(m, L, tiles, objs, mts):
    img = Img(m['GW'] * T, m['GH'] * T)
    cache = {}

    def crop(src, ax, ay):
        key = (src, ax, ay)
        if key not in cache:
            if src == SRC_TILES:
                cache[key] = tiles.crop(ax * T, ay * T, T, T)
            elif src == SRC_OBJ:
                cache[key] = objs.crop(ax * T, ay * OBJ_H, T, OBJ_H)
            else:
                cache[key] = mts.crop(ax * MT_W, 0, MT_W, MT_H)
        return cache[key]

    for name in ('Fondo', 'Terreno', 'Bordes', 'Rios', 'Vias', 'Plazas'):
        for (x, y, src, ax, ay) in L[name]:
            img.blit(crop(src, ax, ay), x * T, y * T)
    draw = []
    for (x, y, src, ax, ay) in L['Objetos'] + L['Montanas']:
        s = crop(src, ax, ay)
        draw.append(((y + 1) * T, x * T + T // 2 - s.w // 2, s))
    for h in m['hitos']:
        s = SPRITES[h['sprite']]()
        draw.append((int(h['y'] * T), int(h['x'] * T) - s.w // 2, s))
    for by, x0, s in sorted(draw, key=lambda d: (d[0], d[1])):
        img.blit(s, x0, by - s.h)
    for c in m['cables']:
        pts = [(x * T, y * T - 14) for x, y in c['puntos']]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            img.line(int(x0), int(y0), int(x1), int(y1), (43, 40, 56, 255))
    img.save(os.path.join(PREV, 'mapa_preview.png'))
    for name, (cx, cy) in {'centro': (0.33, 0.50), 'oriente': (0.52, 0.58)}.items():
        img.crop(int(cx * img.w) - 300, int(cy * img.h) - 190, 600, 380).scaled(3).save(os.path.join(PREV, 'zoom_%s.png' % name))


def main():
    for d in (PREV, DATA, os.path.join(ROOT, 'Tiles'), os.path.join(ROOT, 'Sprites', 'hitos'),
              os.path.join(ROOT, 'Scenes'), os.path.join(ROOT, 'Shaders')):
        os.makedirs(d, exist_ok=True)
    m = build_map()
    tiles, objs, obj_index, mts, cars = build_atlases()
    L = layer_cells(m, obj_index)

    tiles.save(os.path.join(ROOT, 'Tiles', 'manizales_tiles.png'))
    objs.save(os.path.join(ROOT, 'Tiles', 'manizales_objetos.png'))
    mts.save(os.path.join(ROOT, 'Tiles', 'manizales_montanas.png'))
    cars.save(os.path.join(ROOT, 'Sprites', 'carros.png'))
    X.gondola().save(os.path.join(ROOT, 'Sprites', 'cabina.png'))
    X.iconos_clima().save(os.path.join(ROOT, 'Sprites', 'clima_iconos.png'))
    X.resplandor().save(os.path.join(ROOT, 'Sprites', 'resplandor.png'))
    X.gota().save(os.path.join(ROOT, 'Sprites', 'gota.png'))
    with open(os.path.join(DATA, 'comunas.json'), 'w', encoding='utf-8') as f:
        json.dump([{'numero': c['numero'], 'nombre': c['nombre'], 'lat': c['lat'], 'lon': c['lon'],
                    'insignia': c['insignia'], 'celdas': [v for cc in c['celdas'] for v in cc]} for c in m['com']],
                  f, ensure_ascii=False, separators=(',', ':'))
    for v in range(2):
        X.cloud(v).save(os.path.join(ROOT, 'Sprites', 'nube_%d.png' % v))
    for key in {h['sprite'] for h in m['hitos']}:
        SPRITES[key]().save(os.path.join(ROOT, 'Sprites', 'hitos', key + '.png'))

    used = {(ax, ay) for name in L if name not in ('Objetos', 'Montanas') for (_, _, src, ax, ay) in L[name]}
    used |= {(c, r) for r in (ROW_GRASS, ROW_CLIFF, ROW_ST) for c in range(16)}
    used |= {(i % COLS, ROW_AV if i < COLS else ROW_AV2) for i in range(len(AV_PAIRS))}
    used |= {(c, ROW_BG) for c in range(6)} | {(c, ROW_EDGE) for c in range(1, 16)} \
        | {(c * RIVER_FRAMES, ROW_RIVER) for c in range(16)} | {(c, ROW_PLAZA) for c in range(4)}
    write_tileset(os.path.join(ROOT, 'Tiles', 'manizales_tileset.tres'), used, obj_index, objs.h // OBJ_H)
    write_scene(os.path.join(ROOT, 'Scenes', 'ManizalesPixel.tscn'), m, L)

    with open(os.path.join(DATA, 'mapa.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'ancho': m['GW'], 'alto': m['GH'], 'tile': T, 'comunas': m['comunas'],
            'tierra': [[x, y, m['region'][(x, y)]] for (x, y) in sorted(m['land'])],
            'avenidas': sorted(m['avenue']), 'calles': sorted(m['street']), 'rios': sorted(m['river']),
            'hitos': m['hitos'], 'marcadores': m['markers'], 'cable': m['cables'],
        }, f, ensure_ascii=False, separators=(',', ':'))

    render(m, L, tiles, objs, mts)
    print('rejilla %dx%d | tierra %d | avenidas %d | calles %d | rio %d | objetos %d | montañas %d | hitos %d | rótulos %d'
          % (m['GW'], m['GH'], len(m['land']), len(m['avenue']), len(m['street']), len(m['river']),
             len(m['objects']), len(m['mountains']), len(m['hitos']), len(m['labels'])))


if __name__ == '__main__':
    sys.exit(main())
