"""Las 12 comunas de Manizales (límites de OpenStreetMap) llevadas a la rejilla del mapa."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))

# número oficial -> nombre en OSM (relaciones admin_level=8 de Manizales)
NUMERO = {
    'Comuna Atardeceres': 1, 'Comuna San José': 2, 'Comuna Cumanday': 3, 'Comuna La Estación': 4,
    'Comuna Ciudadela del Norte': 5, 'Comuna Ecoturística Cerro de Oro': 6, 'Comuna Tesorito': 7,
    'Comuna Palogrande': 8, 'Comuna Universitaria': 9, 'Comuna La Fuente': 10, 'Comuna La Macarena': 11,
    'Comuna Nuevo Horizonte': 12,
}


def rings(members):
    """Une los tramos 'outer' de una relación en anillos cerrados de (lon, lat)."""
    segs = [[(p['lon'], p['lat']) for p in m['geometry']] for m in members
            if m['type'] == 'way' and m.get('role', 'outer') in ('outer', '') and m.get('geometry')]
    out = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        out.append(ring)
    return out


def centroid(ring):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-12:
        return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    return cx / (3 * a), cy / (3 * a)


def inside(x, y, poly):
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def load(geo):
    """[{nombre, numero, lat, lon, anillos (en tiles)}] ordenadas por número."""
    with open(os.path.join(ROOT, 'data', 'osm', 'comunas.json'), encoding='utf-8') as f:
        rels = json.load(f)['elements']
    out = []
    for r in rels:
        name = r['tags']['name']
        rs = rings(r['members'])
        main = max(rs, key=len)
        lon, lat = centroid(main)
        out.append({'nombre': name.replace('Comuna ', ''), 'numero': NUMERO.get(name, 0),
                    'lat': round(lat, 5), 'lon': round(lon, 5),
                    'anillos': [[geo(lo, la) for lo, la in ring] for ring in rs]})
    return sorted(out, key=lambda c: c['numero'])


def assign(cells, comunas):
    """{celda: índice de comuna} para las celdas cuyo centro cae dentro de algún límite."""
    out = {}
    for (x, y) in cells:
        for i, c in enumerate(comunas):
            if any(inside(x + 0.5, y + 0.5, ring) for ring in c['anillos']):
                out[(x, y)] = i
                break
    return out
