"""Georreferenciación: transformación (lon, lat) -> tile del mapa.

1. Ajuste inicial con los marcadores de lugares.png que Jerson identificó.
2. Afinado tipo ICP: las avenidas reales de OpenStreetMap se acercan a las avenidas trazadas en Calles.png.
Uso: python georef.py  -> escribe data/georef.json, imprime errores y el lugar real más cercano a cada marcador,
                          y deja tools/previews/georef.png (gris = Calles.png, rojo = avenidas OSM proyectadas).
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OSM = os.path.join(ROOT, 'data', 'osm')
OUT = os.path.join(ROOT, 'data', 'georef.json')

# marcador de la capa lugares.png -> lugar real (según recuerda Jerson, 13-oct-2026)
CONTROL = {
    1: ('Monumento a los Colonizadores', 5.07699, -75.52781),
    2: ('Torre al Cielo (Chipre)', 5.07247, -75.52497),
    3: ('Gobernación de Caldas', 5.06871, -75.51754),
    5: ('Catedral Basílica', 5.06738, -75.51732),
    6: ('Mall Plaza', 5.06578, -75.49012),
    7: ('Ecoparque Alcázares', 5.06487, -75.53274),
}

# avenidas que se pintan como principales: nombre en OSM -> rótulo en el mapa
AVENIDAS = {
    'Avenida Kevin Ángel': 'Av. Kevin Ángel',
    'Avenida Santander': 'Av. Santander',
    'Avenida Paralela': 'Av. Paralela',
    'Carretera Panamericana': 'Vía Panamericana',
    'Carretera Panamericana Manizales - Medellín': 'Vía Panamericana',
    'Avenida Centenario': 'Av. Centenario',
    'Avenida 12 de Octubre': 'Av. 12 de Octubre',
    'Avenida Alberto Mendoza Hoyos': 'Av. Alberto Mendoza',
    'Avenida Bernardo Arango': 'Av. Bernardo Arango',
    'Avenida Gilberto Alzate Avendaño': 'Av. Gilberto Alzate',
    'Avenida Marcelino Palacio': 'Av. Marcelino Palacio',
    'Avenida José Restrepo': 'Av. José Restrepo',
}
LON0, LAT0 = -75.505, 5.062


def basis(lon, lat, degree):
    a, b = (lon - LON0) * 100.0, (lat - LAT0) * 100.0
    out = [1.0, a, b]
    if degree >= 2:
        out += [a * a, a * b, b * b]
    return out


def lstsq(rows, ys, weights):
    """Mínimos cuadrados ponderados por ecuaciones normales + eliminación gaussiana."""
    n = len(rows[0])
    M = [[0.0] * n for _ in range(n)]
    v = [0.0] * n
    for r, y, w in zip(rows, ys, weights):
        for i in range(n):
            v[i] += w * r[i] * y
            for j in range(n):
                M[i][j] += w * r[i] * r[j]
    for i in range(n):
        p = max(range(i, n), key=lambda k: abs(M[k][i]))
        M[i], M[p], v[i], v[p] = M[p], M[i], v[p], v[i]
        for k in range(i + 1, n):
            f = M[k][i] / M[i][i]
            for j in range(i, n):
                M[k][j] -= f * M[i][j]
            v[k] -= f * v[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (v[i] - sum(M[i][j] * x[j] for j in range(i + 1, n))) / M[i][i]
    return x


class Georef:
    def __init__(self, cx, cy, degree):
        self.cx, self.cy, self.degree = cx, cy, degree

    def __call__(self, lon, lat):
        b = basis(lon, lat, self.degree)
        return sum(c * t for c, t in zip(self.cx, b)), sum(c * t for c, t in zip(self.cy, b))

    @staticmethod
    def fit(pairs, degree, weights=None):
        weights = weights or [1.0] * len(pairs)
        rows = [basis(lo, la, degree) for (lo, la), _ in pairs]
        return Georef(lstsq(rows, [g[0] for _, g in pairs], weights),
                      lstsq(rows, [g[1] for _, g in pairs], weights), degree)

    def save(self, path=OUT):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'lon0': LON0, 'lat0': LAT0, 'grado': self.degree, 'cx': self.cx, 'cy': self.cy}, f, indent=1)

    @staticmethod
    def load(path=OUT):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return Georef(d['cx'], d['cy'], d['grado'])


def avenue_ways():
    """[(rótulo, [(lon, lat), ...])] de las avenidas principales en OSM."""
    with open(os.path.join(OSM, 'vias.json'), encoding='utf-8') as f:
        data = json.load(f)
    out = []
    for e in data['elements']:
        name = e.get('tags', {}).get('name')
        if name in AVENIDAS:
            out.append((AVENIDAS[name], [(p['lon'], p['lat']) for p in e['geometry']]))
    return out


def densify(pts, step):
    """Puntos cada `step` tiles a lo largo de una polilínea ya proyectada."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    if pts:
        out.append(pts[-1])
    return out


def load_pois():
    out = []
    for name in ('pois.json', 'extra.json'):
        with open(os.path.join(OSM, name), encoding='utf-8') as fh:
            for e in json.load(fh)['elements']:
                t = e.get('tags', {})
                if 'name' not in t or 'highway' in t:
                    continue
                c = e.get('center') or {'lat': e.get('lat'), 'lon': e.get('lon')}
                out.append((t['name'], c['lat'], c['lon']))
    return out


def main():
    import build
    from px import Img
    with open(os.path.join(ROOT, 'data', 'mapa.json'), encoding='utf-8') as fh:
        _d = json.load(fh)
        hitos = {h['id']: h for h in (_d.get('marcadores') or _d['hitos'])}
    ctrl = [((lon, lat), (hitos[i]['x'], hitos[i]['y'])) for i, (_, lat, lon) in CONTROL.items()]
    g = Georef.fit(ctrl, 1)

    # celdas de avenida trazadas a mano en Calles.png (destino del ICP)
    origin, GW, GH = build.grid()
    target = set(build.thin(build.ink_counts('calles', origin)[0], 3))
    offsets = sorted(((dx, dy) for dx in range(-6, 7) for dy in range(-6, 7)), key=lambda d: d[0] ** 2 + d[1] ** 2)
    ways = avenue_ways()
    samples = []
    for _, pts in ways:
        for k in range(0, len(pts), 1):
            samples.append(pts[k])

    for it, radius in enumerate((6, 5, 4, 3, 3, 2.5, 2.5, 2.5)):
        degree = 1 if it < 3 else 2
        pairs, weights = list(ctrl), [40.0] * len(ctrl)
        for lon, lat in samples:
            gx, gy = g(lon, lat)
            cx, cy = int(gx), int(gy)
            for dx, dy in offsets:
                if (cx + dx, cy + dy) in target:
                    tx, ty = cx + dx + 0.5, cy + dy + 0.5
                    if math.hypot(tx - gx, ty - gy) <= radius:
                        pairs.append(((lon, lat), (tx, ty)))
                        weights.append(1.0)
                    break
        g = Georef.fit(pairs, degree, weights)
        err = sum(math.hypot(g(*p)[0] - t[0], g(*p)[1] - t[1]) for p, t in pairs[len(ctrl):]) / max(1, len(pairs) - len(ctrl))
        print('iteración %d (grado %d): %d pares, error medio %.2f tiles' % (it, degree, len(pairs) - len(ctrl), err))
    g.save()

    print('marcadores de control (error en tiles):')
    for i, (name, lat, lon) in CONTROL.items():
        gx, gy = g(lon, lat)
        print('  %2d %-32s %.1f' % (i, name, math.hypot(gx - hitos[i]['x'], gy - hitos[i]['y'])))
    pois = load_pois()
    print('lugar real más cercano a cada marcador:')
    for i, h in sorted(hitos.items()):
        best = sorted(((math.hypot(g(lo, la)[0] - h['x'], g(lo, la)[1] - h['y']), n) for n, la, lo in pois))[:3]
        print('  %2d  ' % i + ' | '.join('%s (%.1f)' % (n, d) for d, n in best))

    # vista de control
    img = Img(GW * 4, GH * 4, (40, 70, 70, 255))
    for (x, y) in target:
        img.rect(x * 4, y * 4, 4, 4, (200, 200, 200, 255))
    for _, pts in ways:
        for (x, y) in densify([g(*p) for p in pts], 0.25):
            img.rect(int(x * 4), int(y * 4), 2, 2, (230, 60, 50, 255))
    for i, h in hitos.items():
        img.rect(int(h['x'] * 4) - 2, int(h['y'] * 4) - 2, 5, 5, (255, 220, 60, 255))
    img.save(os.path.join(ROOT, 'tools', 'previews', 'georef.png'))


if __name__ == '__main__':
    main()
