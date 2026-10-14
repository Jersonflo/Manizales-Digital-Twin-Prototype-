"""Lienzo RGBA mínimo + lectura/escritura de PNG usando solo la librería estándar."""
import struct
import zlib


def C(hexstr, a=255):
    h = hexstr.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


CLEAR = (0, 0, 0, 0)


def rnd(x, y, s=0):
    """Ruido determinista 0..1 por coordenada (mismo resultado en cada build)."""
    n = (x * 374761393 + y * 668265263 + s * 982451653) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffff) / 65536.0


class Img:
    def __init__(self, w, h, fill=CLEAR):
        self.w, self.h = w, h
        self.d = bytearray(bytes(fill) * (w * h))

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            return tuple(self.d[i:i + 4])
        return CLEAR

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            self.d[i:i + 4] = bytes(c)

    def rect(self, x, y, w, h, c):
        for yy in range(max(0, y), min(self.h, y + h)):
            x0, x1 = max(0, x), min(self.w, x + w)
            if x1 > x0:
                i = (yy * self.w + x0) * 4
                self.d[i:i + (x1 - x0) * 4] = bytes(c) * (x1 - x0)

    def hline(self, x0, x1, y, c):
        self.rect(min(x0, x1), y, abs(x1 - x0) + 1, 1, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, min(y0, y1), 1, abs(y1 - y0) + 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        e = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * e
            if e2 >= dy:
                e += dy
                x0 += sx
            if e2 <= dx:
                e += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        """Disco con centro en coordenadas de medio píxel permitidas (cx, cy float)."""
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.set(x, y, c)

    def blit(self, o, dx, dy):
        """Pega `o` respetando alfa (0 = no pinta, 255 = tapa, intermedio = mezcla)."""
        for y in range(o.h):
            ty = dy + y
            if ty < 0 or ty >= self.h:
                continue
            x0, x1 = max(0, -dx), min(o.w, self.w - dx)
            if x1 <= x0:
                continue
            src = o.d[(y * o.w + x0) * 4:(y * o.w + x1) * 4]
            al = src[3::4]
            di = (ty * self.w + dx + x0) * 4
            if min(al) == 255:
                self.d[di:di + len(src)] = src
                continue
            if max(al) == 0:
                continue
            d = self.d
            for k, a in enumerate(al):
                if a == 0:
                    continue
                j, s = di + k * 4, k * 4
                if a == 255:
                    d[j:j + 4] = src[s:s + 4]
                else:
                    ia = 255 - a
                    d[j] = (src[s] * a + d[j] * ia) // 255
                    d[j + 1] = (src[s + 1] * a + d[j + 1] * ia) // 255
                    d[j + 2] = (src[s + 2] * a + d[j + 2] * ia) // 255
                    d[j + 3] = max(d[j + 3], a)

    def outline(self, c):
        """Contorno de 1 px alrededor de todo lo opaco (el sprite necesita 1 px de margen)."""
        hits = []
        for y in range(self.h):
            for x in range(self.w):
                if self.d[(y * self.w + x) * 4 + 3] == 0:
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if self.get(nx, ny)[3] == 255:
                            hits.append((x, y))
                            break
        for x, y in hits:
            self.set(x, y, c)
        return self

    def crop(self, x, y, w, h):
        o = Img(w, h)
        o.blit(self, -x, -y)
        return o

    def scaled(self, k):
        o = Img(self.w * k, self.h * k)
        for y in range(self.h):
            row = bytearray()
            for x in range(self.w):
                i = (y * self.w + x) * 4
                row += self.d[i:i + 4] * k
            for r in range(k):
                j = ((y * k + r) * o.w) * 4
                o.d[j:j + len(row)] = row
        return o

    def flipped(self):
        o = Img(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                o.set(self.w - 1 - x, y, self.get(x, y))
        return o

    def save(self, path):
        raw = bytearray()
        stride = self.w * 4
        for y in range(self.h):
            raw.append(0)
            raw += self.d[y * stride:(y + 1) * stride]

        def chunk(tag, data):
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

        with open(path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n')
            f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', self.w, self.h, 8, 6, 0, 0, 0)))
            f.write(chunk(b'IDAT', zlib.compress(bytes(raw), 9)))
            f.write(chunk(b'IEND', b''))


def load(path):
    """Lee PNG de 8 bits RGB/RGBA sin entrelazado (lo que exportan las capas de referencia)."""
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    pos, idat, w, h, ctype = 8, bytearray(), 0, 0, 6
    while pos < len(data):
        n, tag = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b'IHDR':
            w, h, depth, ctype, _, _, inter = struct.unpack('>IIBBBBB', body)
            assert depth == 8 and ctype in (2, 6) and inter == 0, (path, depth, ctype, inter)
        elif tag == b'IDAT':
            idat += body
    bpp = 4 if ctype == 6 else 3
    raw = zlib.decompress(bytes(idat))
    stride = w * bpp
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += stride + 1
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    img = Img(w, h)
    if bpp == 4:
        img.d = out
    else:
        d = bytearray(w * h * 4)
        d[0::4], d[1::4], d[2::4] = out[0::3], out[1::3], out[2::3]
        d[3::4] = b'\xff' * (w * h)
        img.d = d
    return img
