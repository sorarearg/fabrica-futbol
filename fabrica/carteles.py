"""Carteles animados hechos con código (sin IA de imágenes): marcador, palabras que aparecen, número que
cuenta, tabla de posiciones, comparación con barras, línea de tiempo y ficha de jugador, sobre fondos de
cancha, pizarra táctica, diario viejo o noche de estadio. Todo gratis, en GitHub.

Uso: render({"tipo": "marcador", ...}, segundos, destino_mp4)
El contenido va entre y=230 y y=1040 para no pisar los subtítulos (centro en y=1160)."""
import math
import random
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
RAIZ = Path(__file__).resolve().parent.parent
AMARILLO = (255, 212, 0)
BLANCO = (255, 255, 255)
NEGRO = (17, 17, 17)
CELESTE = (117, 170, 219)
ROJO = (214, 40, 40)
TIPOS = ("marcador", "palabras", "numero", "tabla", "comparacion", "linea_tiempo", "ficha", "dibujo", "dibujos",
         "titular", "cita", "jugada", "formacion")
FONDOS = ("cancha", "pizarra", "diario", "noche", "cesped", "red", "papelitos", "figuritas")
FONDO_POR_TIPO = {"marcador": "noche", "palabras": "diario", "numero": "cancha", "tabla": "pizarra",
                  "comparacion": "noche", "linea_tiempo": "diario", "ficha": "figuritas", "dibujo": "papelitos",
                  "dibujos": "cesped", "titular": "diario", "cita": "red", "jugada": "pizarra",
                  "formacion": "cancha"}

_RUTAS = {
    "titulo": ["fonts/Anton-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"],
    "negrita": ["fonts/Poppins-ExtraBold.ttf", "fonts/Poppins-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "diario": ["fonts/OldStandard-Bold.ttf", "fonts/AbrilFatface-Regular.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
}
_CACHE = {}


def fuente(estilo, tam):
    clave = (estilo, tam)
    if clave not in _CACHE:
        for r in _RUTAS[estilo]:
            p = Path(r) if r.startswith("/") else RAIZ / r
            if p.exists():
                _CACHE[clave] = ImageFont.truetype(str(p), tam)
                break
        else:
            _CACHE[clave] = ImageFont.load_default()
    return _CACHE[clave]


# ---------------------------------------------------------------- curvas de animación
def _lim(x):
    return max(0.0, min(1.0, x))


def suave(x):
    x = _lim(x)
    return 1 - (1 - x) ** 3


def rebote(x):
    x = _lim(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _ancho(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f)
    return b[2] - b[0]


def _ajustar(d, txt, estilo, tam, max_w, min_tam=40):
    while tam > min_tam and _ancho(d, txt, fuente(estilo, tam)) > max_w:
        tam -= 4
    return fuente(estilo, tam)


def _texto_c(d, cx, y, txt, f, color, borde=0, color_borde=NEGRO):
    d.text((cx, y), txt, font=f, fill=color, anchor="ma", stroke_width=borde, stroke_fill=color_borde)


def _pegar(base, capa, cx, cy, escala=1.0, alfa=1.0, angulo=0.0):
    """Pega una capa RGBA centrada en (cx, cy) con escala, transparencia y giro."""
    if escala <= 0.01 or alfa <= 0.01:
        return
    c = capa
    if abs(escala - 1) > 0.01:
        c = c.resize((max(1, int(c.width * escala)), max(1, int(c.height * escala))), Image.BICUBIC)
    if angulo:
        c = c.rotate(angulo, resample=Image.BICUBIC, expand=True)
    if alfa < 0.99:
        a = c.getchannel("A").point(lambda v: int(v * alfa))
        c = c.copy()
        c.putalpha(a)
    base.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))


# ---------------------------------------------------------------- fondos
def _vineta(im, fuerza=0.55):
    m = Image.new("L", (W // 4, H // 4), 0)
    dm = ImageDraw.Draw(m)
    for k in range(40):
        t = k / 40
        dm.ellipse([-W // 8 * (1 - t) - 60 + t * 60, -H // 8 * (1 - t) - 60 + t * 60,
                    W // 4 + W // 8 * (1 - t) + 60 - t * 60, H // 4 + H // 8 * (1 - t) + 60 - t * 60],
                   fill=int(255 * t))
    m = m.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))
    negro = Image.new("RGB", (W, H), (0, 0, 0))
    m = m.point(lambda v: int(255 - (255 - v) * fuerza))
    return Image.composite(im, negro, m)


def _ruido(im, cant, semilla, colores):
    rnd = random.Random(semilla)
    d = ImageDraw.Draw(im)
    for _ in range(cant):
        x, y = rnd.randrange(W), rnd.randrange(H)
        r = rnd.choice((1, 1, 2))
        d.ellipse([x, y, x + r, y + r], fill=rnd.choice(colores))


def fondo_cancha(semilla=1):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    franja = 160
    for k in range(H // franja + 1):
        c = (34, 120, 52) if k % 2 == 0 else (40, 134, 58)
        d.rectangle([0, k * franja, W, (k + 1) * franja], fill=c)
    blanco = (230, 240, 230)
    d.rectangle([60, 120, W - 60, H - 120], outline=blanco, width=8)
    d.line([60, H // 2, W - 60, H // 2], fill=blanco, width=8)
    d.ellipse([W // 2 - 190, H // 2 - 190, W // 2 + 190, H // 2 + 190], outline=blanco, width=8)
    d.ellipse([W // 2 - 14, H // 2 - 14, W // 2 + 14, H // 2 + 14], fill=blanco)
    d.rectangle([W // 2 - 330, 120, W // 2 + 330, 420], outline=blanco, width=8)
    d.rectangle([W // 2 - 150, 120, W // 2 + 150, 230], outline=blanco, width=8)
    d.rectangle([W // 2 - 330, H - 420, W // 2 + 330, H - 120], outline=blanco, width=8)
    d.rectangle([W // 2 - 150, H - 230, W // 2 + 150, H - 120], outline=blanco, width=8)
    _ruido(im, 9000, semilla, [(28, 104, 44), (50, 146, 66)])
    return _vineta(im.filter(ImageFilter.GaussianBlur(1)), 0.6)


def fondo_pizarra(semilla=1):
    rnd = random.Random(semilla)
    im = Image.new("RGB", (W, H), (30, 52, 42))
    _ruido(im, 25000, semilla, [(38, 62, 50), (26, 44, 36), (44, 70, 58)])
    d = ImageDraw.Draw(im)
    tiza = (205, 214, 206)
    d.rectangle([70, 140, W - 70, H - 140], outline=(120, 140, 125), width=5)
    d.line([70, H // 2, W - 70, H // 2], fill=(120, 140, 125), width=5)
    d.ellipse([W // 2 - 150, H // 2 - 150, W // 2 + 150, H // 2 + 150], outline=(120, 140, 125), width=5)
    for _ in range(9):  # cruces y círculos de jugadas
        x, y = rnd.randrange(140, W - 140), rnd.choice([rnd.randrange(1300, 1760), rnd.randrange(160, 230)])
        if rnd.random() < 0.5:
            d.line([x - 22, y - 22, x + 22, y + 22], fill=tiza, width=7)
            d.line([x - 22, y + 22, x + 22, y - 22], fill=tiza, width=7)
        else:
            d.ellipse([x - 24, y - 24, x + 24, y + 24], outline=tiza, width=7)
    for _ in range(3):  # flechas de tiza
        x0, y0 = rnd.randrange(150, W - 300), rnd.randrange(1350, 1700)
        x1, y1 = x0 + rnd.randrange(120, 260), y0 - rnd.randrange(60, 200)
        d.line([x0, y0, (x0 + x1) // 2, y0 - 40, x1, y1], fill=tiza, width=6, joint="curve")
        d.polygon([(x1, y1), (x1 - 34, y1 + 6), (x1 - 12, y1 + 30)], fill=tiza)
    return _vineta(im, 0.5)


def fondo_diario(semilla=1):
    rnd = random.Random(semilla)
    im = Image.new("RGB", (W, H), (236, 226, 202))
    _ruido(im, 30000, semilla, [(222, 210, 184), (244, 236, 214), (210, 196, 168)])
    d = ImageDraw.Draw(im)
    gris = (176, 166, 146)
    cols = 3
    ancho = (W - 160) // cols
    for c in range(cols):  # columnas de texto de fondo
        x = 80 + c * ancho
        y = 140
        while y < H - 120:
            largo = ancho - 40 if rnd.random() > 0.12 else rnd.randrange(80, ancho - 60)
            d.rectangle([x, y, x + largo, y + 10], fill=gris)
            y += 26 if rnd.random() > 0.08 else 70
    im = im.filter(ImageFilter.GaussianBlur(2))
    capa = Image.new("RGBA", (W, H), (236, 226, 202, 150))
    im = Image.alpha_composite(im.convert("RGBA"), capa).convert("RGB")
    return _vineta(im, 0.35)


def fondo_noche(semilla=1):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([0, y, W, y], fill=(int(10 + 10 * t), int(16 + 30 * t), int(40 + 30 * t)))
    luz = Image.new("RGB", (W, H), (0, 0, 0))
    dl = ImageDraw.Draw(luz)
    for cx in (140, W - 140):  # torres de iluminación
        for k in range(3):
            for j in range(4):
                x, y = cx - 90 + j * 60, 130 + k * 50
                dl.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(255, 250, 220))
    luz = luz.filter(ImageFilter.GaussianBlur(26))
    im = _sumar_img(im, luz)
    d = ImageDraw.Draw(im)
    for cx in (140, W - 140):
        for k in range(3):
            for j in range(4):
                x, y = cx - 90 + j * 60, 130 + k * 50
                d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(255, 255, 240))
    # tribuna (siluetas de cabezas) abajo
    rnd = random.Random(semilla)
    for fila in range(7):
        y = H - 330 + fila * 50
        for x in range(-20, W + 20, 46):
            xx = x + rnd.randrange(-8, 8) + (23 if fila % 2 else 0)
            tono = 8 + fila * 3
            d.ellipse([xx - 20, y - 22, xx + 20, y + 18], fill=(tono, tono + 4, tono + 14))
            d.rectangle([xx - 26, y + 10, xx + 26, y + 70], fill=(tono, tono + 4, tono + 14))
    _ruido(im, 300, semilla + 1, [(80, 90, 120)])
    return _vineta(im, 0.5)


def _sumar_img(a, b):
    from PIL import ImageChops
    return ImageChops.add(a, b)


def fondo_cesped(semilla=1):
    rnd = random.Random(semilla)
    im = Image.new("RGB", (W, H), (36, 110, 48))
    d = ImageDraw.Draw(im)
    for _ in range(26000):  # briznas
        x, y = rnd.randrange(W), rnd.randrange(H)
        largo = rnd.randrange(14, 40)
        tono = rnd.randrange(-18, 26)
        d.line([x, y, x + rnd.randrange(-6, 7), y - largo], fill=(40 + tono, 128 + tono, 54 + tono // 2), width=2)
    d.line([0, 1500, W, 1420], fill=(235, 240, 235), width=16)
    return _vineta(im.filter(ImageFilter.GaussianBlur(1.2)), 0.6)


def fondo_red(semilla=1):
    im = Image.new("RGB", (W, H), (18, 22, 30))
    luz = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(luz).ellipse([W // 2 - 600, 300, W // 2 + 600, 1300], fill=(60, 80, 110))
    from PIL import ImageChops
    im = ImageChops.add(im, luz.filter(ImageFilter.GaussianBlur(160)))
    d = ImageDraw.Draw(im)
    paso = 72
    for k in range(-H // paso, W // paso + H // paso):  # malla en rombos
        x = k * paso
        d.line([x, 0, x + H, H], fill=(205, 210, 220), width=4)
        d.line([x, 0, x - H, H], fill=(205, 210, 220), width=4)
    im = im.filter(ImageFilter.GaussianBlur(2.5))
    capa = Image.new("RGBA", (W, H), (10, 14, 22, 120))
    im = Image.alpha_composite(im.convert("RGBA"), capa).convert("RGB")
    return _vineta(im, 0.6)


def fondo_papelitos(semilla=1):
    rnd = random.Random(semilla)
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([0, y, W, y], fill=(int(20 + 40 * t), int(60 + 60 * t), int(120 + 40 * t)))
    for _ in range(420):  # papelitos y serpentinas
        x, y = rnd.randrange(W), rnd.randrange(H)
        c = rnd.choice([B_ for B_ in ((255, 255, 255), (117, 170, 219), (255, 212, 0), (240, 240, 240))])
        a = rnd.uniform(0, math.pi)
        w, h = rnd.randrange(14, 30), rnd.randrange(6, 12)
        pts = [(x + w * math.cos(a) - h * math.sin(a), y + w * math.sin(a) + h * math.cos(a)),
               (x - w * math.cos(a) - h * math.sin(a), y - w * math.sin(a) + h * math.cos(a)),
               (x - w * math.cos(a) + h * math.sin(a), y - w * math.sin(a) - h * math.cos(a)),
               (x + w * math.cos(a) + h * math.sin(a), y + w * math.sin(a) - h * math.cos(a))]
        d.polygon(pts, fill=c)
    im = im.filter(ImageFilter.GaussianBlur(1.5))
    return _vineta(im, 0.5)


def fondo_figuritas(semilla=1):
    rnd = random.Random(semilla)
    im = Image.new("RGB", (W, H), (226, 200, 120))
    d = ImageDraw.Draw(im)
    for y in range(-40, H, 300):
        for x in range(-60 + (y // 300 % 2) * 110, W, 230):
            col = rnd.choice([(117, 170, 219), (214, 40, 40), (40, 150, 70), (30, 60, 140), (250, 250, 250)])
            d.rounded_rectangle([x, y, x + 200, y + 270], 14, fill=(250, 246, 236), outline=(150, 130, 90), width=4)
            d.rectangle([x + 14, y + 14, x + 186, y + 200], fill=col)
            d.ellipse([x + 70, y + 50, x + 130, y + 110], fill=(0, 0, 0, 0), outline=(250, 246, 236), width=5)
            d.rectangle([x + 14, y + 210, x + 186, y + 230], fill=(200, 190, 170))
    im = im.filter(ImageFilter.GaussianBlur(5))
    capa = Image.new("RGBA", (W, H), (40, 30, 10, 90))
    im = Image.alpha_composite(im.convert("RGBA"), capa).convert("RGB")
    return _vineta(im, 0.5)


FABRICA_FONDO = {"cancha": fondo_cancha, "pizarra": fondo_pizarra, "diario": fondo_diario, "noche": fondo_noche,
                 "cesped": fondo_cesped, "red": fondo_red, "papelitos": fondo_papelitos,
                 "figuritas": fondo_figuritas}


# ---------------------------------------------------------------- piezas
def _caja(w, h, color, radio=28, sombra=True, borde=None):
    pad = 30
    capa = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if sombra:
        s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).rounded_rectangle([pad + 6, pad + 14, pad + w + 6, pad + h + 14], radio, fill=(0, 0, 0, 140))
        capa = Image.alpha_composite(capa, s.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle([pad, pad, pad + w, pad + h], radio, fill=color,
                        outline=borde, width=6 if borde else 0)
    return capa, d, pad


def _tono_texto(fondo_nombre):
    return NEGRO if fondo_nombre == "diario" else BLANCO


# ---------------------------------------------------------------- tipos
def _marcador(c, base, t, dur, fondo):
    loc, vis = str(c.get("local", "LOCAL")).upper(), str(c.get("visita", "VISITA")).upper()
    gl, gv = int(c.get("goles_local", 0) or 0), int(c.get("goles_visita", 0) or 0)
    det = str(c.get("detalle", "")).upper()
    im = base.copy()
    # tablero
    caja, d, p = _caja(960, 520, (14, 14, 18, 245), 36, borde=(60, 60, 70))
    d.rectangle([p + 40, p + 300, p + 920, p + 304], fill=(50, 50, 60))
    fe = _ajustar(d, max(loc, vis, key=len), "titulo", 78, 380)
    _texto_c(d, p + 230, p + 50, loc, fe, BLANCO)
    _texto_c(d, p + 730, p + 50, vis, fe, BLANCO)
    k = suave((t - 0.5) / 1.0)
    for cx, g in ((p + 230, gl), (p + 730, gv)):
        d.rounded_rectangle([cx - 120, p + 150, cx + 120, p + 290], 18, fill=(30, 30, 36))
        val = int(round(g * k)) if t < 1.5 else g
        f = fuente("titulo", 150)
        _texto_c(d, cx, p + 130, str(val), f, AMARILLO)
    _texto_c(d, p + 480, p + 175, "–", fuente("titulo", 120), (120, 120, 130))
    if det:
        fd = _ajustar(d, det, "negrita", 46, 860, 26)
        _texto_c(d, p + 480, p + 350, det, fd, (200, 200, 210))
    if c.get("aclaracion"):
        fa = _ajustar(d, str(c["aclaracion"]).upper(), "negrita", 40, 860, 24)
        _texto_c(d, p + 480, p + 420, str(c["aclaracion"]).upper(), fa, AMARILLO)
    e = rebote(t / 0.45)
    _pegar(im, caja, W / 2, 620, 0.6 + 0.4 * e, _lim(t / 0.25))
    # destello al terminar de contar
    if 1.45 < t < 1.9:
        a = 1 - (t - 1.45) / 0.45
        fl = Image.new("RGBA", (W, H), (255, 255, 255, int(70 * a)))
        im.alpha_composite(fl)
    return im


def _palabras(c, base, t, dur, fondo):
    txt = str(c.get("texto", "")).upper().split()
    resaltar = {str(x).upper() for x in (c.get("resaltar") or [])}
    color = _tono_texto(fondo)
    im = base.copy()
    d0 = ImageDraw.Draw(im)
    # armado de renglones
    f = fuente("titulo", 150 if len(txt) <= 4 else 124 if len(txt) <= 7 else 100)
    renglones, act = [], []
    for w in txt:
        prueba = " ".join(act + [w])
        if act and _ancho(d0, prueba, f) > 900:
            renglones.append(act)
            act = [w]
        else:
            act.append(w)
    if act:
        renglones.append(act)
    alto = f.size * 1.18
    y0 = 640 - alto * len(renglones) / 2
    paso = min(0.32, max(0.12, (dur * 0.55) / max(1, len(txt))))
    k = 0
    for r, fila in enumerate(renglones):
        anchos = [_ancho(d0, w, f) for w in fila]
        esp = f.size * 0.28
        x = W / 2 - (sum(anchos) + esp * (len(fila) - 1)) / 2
        for w, aw in zip(fila, anchos):
            ti = t - 0.15 - k * paso
            if ti > 0:
                capa = Image.new("RGBA", (int(aw + 60), int(f.size * 1.5)), (0, 0, 0, 0))
                dc = ImageDraw.Draw(capa)
                limpia = w.strip(".,;:!?¡¿\"'")
                if limpia in resaltar:
                    dc.rectangle([8, f.size * 0.12, aw + 52, f.size * 1.32], fill=AMARILLO)
                    dc.text((30, 0), w, font=f, fill=NEGRO)
                else:
                    borde = 6 if color == BLANCO else 0
                    dc.text((30, 0), w, font=f, fill=color, stroke_width=borde, stroke_fill=NEGRO)
                e = rebote(ti / 0.3)
                _pegar(im, capa, x + aw / 2, y0 + r * alto + f.size * 0.7, 0.4 + 0.6 * e, _lim(ti / 0.12))
            x += aw + esp
            k += 1
    return im


def _numero(c, base, t, dur, fondo):
    valor = float(c.get("valor", 0) or 0)
    dec = int(c.get("decimales", 0) or 0)
    pre, suf = str(c.get("prefijo", "")), str(c.get("sufijo", "")).upper()
    det = str(c.get("detalle", "")).upper()
    im = base.copy()
    k = suave((t - 0.2) / max(0.8, min(1.8, dur * 0.5)))
    v = valor * k
    num = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    caja, d, p = _caja(940, 560, (12, 12, 16, 230), 40)
    fn = _ajustar(d, pre + f"{valor:,.{dec}f}", "titulo", 260, 860, 90)
    _texto_c(d, p + 470, p + 40, pre + num, fn, AMARILLO, 4, NEGRO)
    if suf:
        fs = _ajustar(d, suf, "titulo", 110, 860, 50)
        _texto_c(d, p + 470, p + 330, suf, fs, BLANCO)
    if det:
        fd = _ajustar(d, det, "negrita", 42, 860, 24)
        _texto_c(d, p + 470, p + 470, det, fd, (190, 190, 200))
    _pegar(im, caja, W / 2, 640, 0.7 + 0.3 * rebote(t / 0.4), _lim(t / 0.2))
    return im


def _tabla(c, base, t, dur, fondo):
    filas = (c.get("filas") or [])[:6]
    resaltar = c.get("resaltar")
    titulo = str(c.get("titulo", "POSICIONES")).upper()
    im = base.copy()
    d = ImageDraw.Draw(im)
    ft = _ajustar(d, titulo, "titulo", 84, 920, 40)
    a = _lim(t / 0.3)
    capa = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((W / 2, 20), titulo, font=ft, fill=BLANCO, anchor="ma", stroke_width=5,
                              stroke_fill=NEGRO)
    _pegar(im, capa, W / 2, 310, 1, a)
    fila_h = 112
    y0 = 420
    fe = fuente("negrita", 50)
    for i, f in enumerate(filas):
        f = list(f) + ["", "", ""]
        pos, eq, pts = str(f[0]), str(f[1]).upper(), str(f[2])
        ti = t - 0.25 - i * 0.18
        if ti <= 0:
            continue
        dest = (resaltar is not None and str(resaltar) in (str(i), pos)) or (
            isinstance(resaltar, str) and resaltar.upper() == eq)
        fondo_fila = (*AMARILLO, 250) if dest else (250, 250, 250, 235)
        tc = NEGRO
        caja, dc, p = _caja(900, fila_h - 16, fondo_fila, 18, sombra=True)
        dc.rounded_rectangle([p, p, p + 110, p + fila_h - 16], 18, fill=(17, 17, 17, 255) if not dest else (17, 17, 17, 255))
        dc.text((p + 55, p + (fila_h - 16) / 2), pos, font=fuente("titulo", 56), fill=AMARILLO if not dest else BLANCO,
                anchor="mm")
        fe2 = _ajustar(dc, eq, "negrita", 50, 600, 28)
        dc.text((p + 140, p + (fila_h - 16) / 2), eq, font=fe2, fill=tc, anchor="lm")
        dc.text((p + 870, p + (fila_h - 16) / 2), pts, font=fuente("titulo", 60), fill=tc, anchor="rm")
        x = W / 2 + (1 - suave(ti / 0.35)) * 900
        _pegar(im, caja, x, y0 + i * fila_h + fila_h / 2, 1, _lim(ti / 0.2))
    _ = fe
    return im


def _comparacion(c, base, t, dur, fondo):
    izq, der = c.get("izq") or {}, c.get("der") or {}
    titulo = str(c.get("titulo", "")).upper()
    unidad = str(c.get("unidad", "")).upper()
    vi, vd = float(izq.get("valor", 0) or 0), float(der.get("valor", 0) or 0)
    tope = max(vi, vd, 1)
    im = base.copy()
    d = ImageDraw.Draw(im)
    if titulo:
        ft = _ajustar(d, titulo, "titulo", 86, 940, 40)
        _texto_c(d, W / 2, 240, titulo, ft, BLANCO, 5)
    alto_max = 420
    base_y = 960
    for k, (lado, v, color) in enumerate(((izq, vi, CELESTE), (der, vd, AMARILLO))):
        cx = 300 if k == 0 else W - 300
        ti = t - 0.2 - k * 0.25
        g = suave(ti / 0.9)
        h = alto_max * (v / tope) * g
        d.rounded_rectangle([cx - 130, base_y - h, cx + 130, base_y], 22, fill=color, outline=NEGRO, width=6)
        val = v * g
        txt = (f"{val:,.0f}" if v >= 10 or v == int(v) else f"{val:.1f}").replace(",", ".")
        _texto_c(d, cx, base_y - h - 120, txt, fuente("titulo", 100), BLANCO, 5)
        nombre = str(lado.get("nombre", "")).upper()
        fn = _ajustar(d, nombre, "negrita", 50, 400, 26)
        _texto_c(d, cx, base_y + 20, nombre, fn, BLANCO, 4)
    if unidad:
        _texto_c(d, W / 2, base_y + 90, unidad, fuente("negrita", 40), AMARILLO, 3)
    vs = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    dv = ImageDraw.Draw(vs)
    dv.ellipse([10, 10, 190, 190], fill=ROJO, outline=BLANCO, width=8)
    dv.text((100, 100), "VS", font=fuente("titulo", 80), fill=BLANCO, anchor="mm")
    _pegar(im, vs, W / 2, 700, rebote((t - 0.1) / 0.4), _lim(t / 0.2))
    return im


def _linea_tiempo(c, base, t, dur, fondo):
    hitos = (c.get("hitos") or [])[:5]
    color = _tono_texto(fondo)
    im = base.copy()
    d = ImageDraw.Draw(im)
    x = 250
    y0, y1 = 300, 1020
    n = max(1, len(hitos))
    paso_t = min(0.55, max(0.3, dur * 0.7 / n))
    largo = suave(t / (paso_t * n)) * (y1 - y0)
    d.line([x, y0, x, y0 + largo], fill=color, width=10)
    for i, h in enumerate(hitos):
        h = list(h) + ["", ""]
        y = y0 + (y1 - y0) * (i + 0.5) / n
        ti = t - i * paso_t - 0.1
        if ti <= 0:
            continue
        e = rebote(ti / 0.35)
        r = 34 * e
        d.ellipse([x - r, y - r, x + r, y + r], fill=AMARILLO, outline=NEGRO, width=6)
        capa = Image.new("RGBA", (720, 200), (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        borde = 5 if color == BLANCO else 0
        dc.text((0, 10), str(h[0]).upper(), font=fuente("titulo", 82), fill=ROJO if color == NEGRO else AMARILLO,
                stroke_width=borde, stroke_fill=NEGRO)
        ftx = _ajustar(dc, str(h[1]), "negrita", 44, 700, 26)
        dc.text((0, 112), str(h[1]), font=ftx, fill=color, stroke_width=3 if color == BLANCO else 0, stroke_fill=NEGRO)
        dx = (1 - suave(ti / 0.35)) * 120
        _pegar(im, capa, x + 70 + 360 + dx, y, 1, _lim(ti / 0.2))
    return im


def _ficha(c, base, t, dur, fondo):
    nombre = str(c.get("nombre", "")).upper()
    datos = (c.get("datos") or [])[:4]
    im = base.copy()
    caja, d, p = _caja(800, 760, (250, 246, 236, 255), 30, borde=AMARILLO)
    d.rounded_rectangle([p + 20, p + 20, p + 780, p + 300], 22, fill=(28, 96, 160))
    # silueta genérica de jugador
    cx, cy = p + 400, p + 160
    d.ellipse([cx - 60, cy - 110, cx + 60, cy + 10], fill=(18, 50, 90))
    d.rounded_rectangle([cx - 130, cy + 20, cx + 130, cy + 160], 50, fill=(18, 50, 90))
    fn = _ajustar(d, nombre, "titulo", 84, 740, 40)
    d.rectangle([p + 20, p + 300, p + 780, p + 410], fill=NEGRO)
    _texto_c(d, p + 400, p + 312, nombre, fn, AMARILLO)
    for i, dato in enumerate(datos):
        dato = list(dato) + ["", ""]
        y = p + 440 + i * 76
        ti = t - 0.5 - i * 0.2
        if ti <= 0:
            continue
        d.text((p + 60, y), str(dato[0]).upper(), font=fuente("negrita", 40), fill=(90, 90, 90))
        d.text((p + 740, y - 6), str(dato[1]).upper(), font=_ajustar(d, str(dato[1]).upper(), "titulo", 56, 380, 30),
               fill=NEGRO, anchor="ra")
        if i < len(datos) - 1:
            d.line([p + 60, y + 66, p + 740, y + 66], fill=(210, 200, 180), width=3)
    giro = (1 - suave(t / 0.5)) * -14
    _pegar(im, caja, W / 2, 650, 0.75 + 0.25 * rebote(t / 0.5), _lim(t / 0.2), giro)
    return im


def _ico(nombre, tam, colores=None):
    from . import dibujos_futbol
    clave = (str(nombre), tam, str(colores))
    if clave not in _ICOS:
        _ICOS[clave] = dibujos_futbol.icono(nombre, tam, colores)
    return _ICOS[clave]


_ICOS = {}


def _colores(c):
    """Colores opcionales del dibujo: "colores": ["celeste", "blanco"] o códigos RGB."""
    nombres = {"celeste": CELESTE, "blanco": BLANCO, "rojo": ROJO, "amarillo": AMARILLO, "negro": (30, 30, 30),
               "azul": (30, 60, 140), "verde": (40, 150, 70), "bordo": (120, 20, 40), "naranja": (240, 120, 30),
               "violeta": (100, 50, 150), "gris": (150, 150, 160), "dorado": (232, 180, 40)}
    lista = c.get("colores") or []
    out = {}
    for k, v in zip(("principal", "secundario"), lista):
        if isinstance(v, str) and v.lower() in nombres:
            out[k] = nombres[v.lower()]
        elif isinstance(v, (list, tuple)) and len(v) == 3:
            out[k] = tuple(int(x) for x in v)
    return out


def _leyenda(im, txt, y, color=BLANCO, tam=96, t=1.0, estilo="titulo"):
    if not txt:
        return
    d = ImageDraw.Draw(im)
    f = _ajustar(d, txt, estilo, tam, 960, 40)
    capa = Image.new("RGBA", (W, int(f.size * 1.6)), (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((W / 2, 10), txt, font=f, fill=color, anchor="ma",
                              stroke_width=6 if color == BLANCO else 0, stroke_fill=NEGRO)
    _pegar(im, capa, W / 2, y, 0.8 + 0.2 * suave(t / 0.3), _lim(t / 0.2))


def _dibujo(c, base, t, dur, fondo):
    im = base.copy()
    ic = _ico(c.get("dibujo"), 560, _colores(c))
    e = rebote(t / 0.5)
    giro = math.sin(t * 2.4) * 4
    _pegar(im, ic, W / 2, 560 + math.sin(t * 3) * 10, 0.3 + 0.7 * e, _lim(t / 0.15), giro)
    _leyenda(im, str(c.get("texto", "")).upper(), 900, _tono_texto(fondo), 100, t - 0.35)
    return im


def _dibujos(c, base, t, dur, fondo):
    im = base.copy()
    items = (c.get("items") or [])[:3]
    n = max(1, len(items))
    tam = 330 if n == 3 else 400
    for i, it in enumerate(items):
        it = it if isinstance(it, dict) else {"dibujo": it}
        cx = W * (i + 0.5) / n
        ti = t - 0.15 - i * 0.35
        if ti <= 0:
            continue
        ic = _ico(it.get("dibujo"), tam, _colores(it))
        _pegar(im, ic, cx, 560, 0.3 + 0.7 * rebote(ti / 0.45), _lim(ti / 0.15))
        txt = str(it.get("texto", "")).upper()
        if txt:
            d = ImageDraw.Draw(im)
            f = _ajustar(d, txt, "titulo", 70, W / n - 40, 30)
            _texto_c(d, cx, 800, txt, f, BLANCO, 5)
    if c.get("texto"):
        _leyenda(im, str(c["texto"]).upper(), 330, AMARILLO, 90, t)
    return im


def _titular(c, base, t, dur, fondo):
    im = base.copy()
    diario = str(c.get("diario", "EL DIARIO DEL HINCHA")).upper()
    fecha = str(c.get("fecha", "")).upper()
    tit = str(c.get("texto", "")).upper()
    caja = Image.new("RGBA", (960, 760), (0, 0, 0, 0))
    d = ImageDraw.Draw(caja)
    d.rectangle([0, 0, 960, 760], fill=(244, 236, 214), outline=NEGRO, width=8)
    fd = _ajustar(d, diario, "diario", 92, 900, 40)
    d.text((480, 30), diario, font=fd, fill=NEGRO, anchor="ma")
    d.line([30, 150, 930, 150], fill=NEGRO, width=6)
    d.line([30, 162, 930, 162], fill=NEGRO, width=2)
    if fecha:
        d.text((480, 172), fecha, font=fuente("negrita", 32), fill=(80, 80, 80), anchor="ma")
    palabras, renglones, act = tit.split(), [], []
    f = fuente("titulo", 150 if len(tit) < 18 else 118 if len(tit) < 34 else 92)
    for w in palabras:
        if act and _ancho(d, " ".join(act + [w]), f) > 880:
            renglones.append(act)
            act = [w]
        else:
            act.append(w)
    if act:
        renglones.append(act)
    y = 240
    for r in renglones[:3]:
        d.text((480, y), " ".join(r), font=f, fill=NEGRO, anchor="ma")
        y += f.size * 1.08
    for k in range(4):
        d.rectangle([40 + k * 225, y + 30, 230 + k * 225, y + 44], fill=(170, 160, 140))
    k = suave(t / 0.45)
    giro = (1 - k) * 380
    _pegar(im, caja, W / 2, 640, 0.15 + 0.85 * k, _lim(t / 0.1), giro)
    if c.get("sello") and t > 0.9:
        _sello(im, str(c["sello"]).upper(), W / 2 + 230, 920, t - 0.9)
    return im


def _sello(im, txt, cx, cy, ti):
    capa = Image.new("RGBA", (560, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f = _ajustar(d, txt, "titulo", 110, 500, 40)
    d.rounded_rectangle([10, 10, 550, 190], 20, outline=ROJO, width=12)
    d.text((280, 100), txt, font=f, fill=ROJO, anchor="mm")
    _pegar(im, capa, cx, cy, 2.2 - 1.2 * suave(ti / 0.25), _lim(ti / 0.1), -12)


def _cita(c, base, t, dur, fondo):
    im = base.copy()
    d = ImageDraw.Draw(im)
    txt = str(c.get("texto", ""))
    autor = str(c.get("autor", "")).upper()
    f = fuente("negrita", 96 if len(txt) < 40 else 78 if len(txt) < 80 else 62)
    renglones, act = [], []
    for w in txt.split():
        if act and _ancho(d, " ".join(act + [w]), f) > 860:
            renglones.append(act)
            act = [w]
        else:
            act.append(w)
    if act:
        renglones.append(act)
    alto = f.size * 1.25 * len(renglones)
    y0 = 640 - alto / 2
    _pegar(im, _comillas(), 170, y0 - 70, rebote(t / 0.4), _lim(t / 0.15))
    total = sum(len(r) for r in renglones)
    visibles = int(total * suave((t - 0.2) / max(0.6, dur * 0.55))) if t > 0.2 else 0
    k = 0
    for i, r in enumerate(renglones):
        trozo = []
        for w in r:
            if k < visibles:
                trozo.append(w)
            k += 1
        if trozo:
            d.text((110, y0 + i * f.size * 1.25), " ".join(trozo), font=f, fill=BLANCO, stroke_width=4,
                   stroke_fill=NEGRO)
    if autor and t > 0.4:
        _leyenda(im, "— " + autor, y0 + alto + 60, AMARILLO, 64, t - 0.4, "negrita")
    return im


def _comillas():
    """Comillas dibujadas (no dependen de la tipografía)."""
    capa = Image.new("RGBA", (220, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for x in (20, 120):
        d.ellipse([x, 70, x + 80, 150], fill=AMARILLO)
        d.polygon([(x + 6, 100), (x + 60, 10), (x + 82, 22), (x + 50, 100)], fill=AMARILLO)
    return capa


def _jugada(c, base, t, dur, fondo):
    """Pizarra: jugadores (O propios, X rivales) y la flecha de la jugada que se dibuja sola."""
    im = base.copy()
    d = ImageDraw.Draw(im)
    tiza = (235, 240, 235)
    puntos = c.get("pases") or [[300, 900], [500, 700], [760, 520], [540, 330]]
    rivales = c.get("rivales") or [[620, 640], [420, 480], [700, 380]]
    for i, (x, y) in enumerate(rivales[:6]):
        if t > 0.1 + i * 0.08:
            d.line([x - 34, y - 34, x + 34, y + 34], fill=(255, 120, 120), width=12)
            d.line([x - 34, y + 34, x + 34, y - 34], fill=(255, 120, 120), width=12)
    for i, (x, y) in enumerate(puntos[:-1]):
        if t > 0.1 + i * 0.08:
            d.ellipse([x - 38, y - 38, x + 38, y + 38], outline=tiza, width=12)
    largo_t = max(0.0, (t - 0.5) / max(0.8, dur * 0.55))
    tramos = len(puntos) - 1
    avance = suave(largo_t) * tramos
    for k in range(tramos):
        if avance <= k:
            break
        (x0, y0), (x1, y1) = puntos[k], puntos[k + 1]
        f = min(1.0, avance - k)
        xe, ye = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        for j in range(0, 20):  # línea punteada
            a, b = j / 20, (j + 0.55) / 20
            if a > f:
                break
            b = min(b, f)
            d.line([x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b], fill=AMARILLO,
                   width=12)
        if f < 1 or k == tramos - 1:
            ang = math.atan2(y1 - y0, x1 - x0)
            pts = [(xe, ye), (xe - 50 * math.cos(ang - 0.45), ye - 50 * math.sin(ang - 0.45)),
                   (xe - 50 * math.cos(ang + 0.45), ye - 50 * math.sin(ang + 0.45))]
            d.polygon(pts, fill=AMARILLO)
    if avance >= tramos - 0.02:
        x, y = puntos[-1]
        _pegar(im, _ico("pelota", 120), x, y, rebote((t - 0.5 - max(0.8, dur * 0.55)) / 0.3), 1)
    _leyenda(im, str(c.get("texto", "")).upper(), 1010, AMARILLO, 80, t - 0.3)
    return im


def _formacion(c, base, t, dur, fondo):
    """Once titular sobre la cancha: "esquema": "4-3-3" y "nombres" (de atrás para adelante, arquero primero)."""
    im = base.copy()
    d = ImageDraw.Draw(im)
    try:
        lineas = [int(x) for x in str(c.get("esquema", "4-4-2")).split("-")]
    except ValueError:
        lineas = [4, 4, 2]
    nombres = [str(x).upper() for x in (c.get("nombres") or [])]
    filas = [1] + lineas
    y_ini, y_fin = 1000, 300
    k = 0
    col = _colores(c).get("principal", CELESTE)
    for f, cant in enumerate(filas):
        y = y_ini + (y_fin - y_ini) * f / max(1, len(filas) - 1)
        for j in range(cant):
            x = W * (j + 1) / (cant + 1)
            ti = t - 0.1 - k * 0.07
            if ti > 0:
                r = 40 * rebote(ti / 0.3)
                d.ellipse([x - r, y - r, x + r, y + r], fill=AMARILLO if f == 0 else col, outline=NEGRO, width=6)
                if k < len(nombres) and nombres[k]:
                    fn = _ajustar(d, nombres[k], "negrita", 34, W / (cant + 1) - 10, 20)
                    _texto_c(d, x, y + 46, nombres[k], fn, BLANCO, 4)
            k += 1
    if c.get("texto"):
        _leyenda(im, str(c["texto"]).upper(), 230, AMARILLO, 80, t)
    return im


DIBUJAR = {"dibujo": _dibujo, "dibujos": _dibujos, "titular": _titular, "cita": _cita, "jugada": _jugada,
           "formacion": _formacion,"marcador": _marcador, "palabras": _palabras, "numero": _numero, "tabla": _tabla,
           "comparacion": _comparacion, "linea_tiempo": _linea_tiempo, "ficha": _ficha}


def valido(c):
    """True si el cartel tiene lo mínimo para dibujarse."""
    if not isinstance(c, dict) or c.get("tipo") not in TIPOS:
        return False
    tipo = c["tipo"]
    if tipo == "marcador":
        return bool(c.get("local") and c.get("visita")) and str(c.get("goles_local", "")).strip() != ""
    if tipo == "palabras":
        return 1 <= len(str(c.get("texto", "")).split()) <= 10
    if tipo == "numero":
        try:
            float(c.get("valor"))
            return True
        except (TypeError, ValueError):
            return False
    if tipo == "tabla":
        return len(c.get("filas") or []) >= 2
    if tipo == "comparacion":
        return bool((c.get("izq") or {}).get("nombre") and (c.get("der") or {}).get("nombre"))
    if tipo == "linea_tiempo":
        return len(c.get("hitos") or []) >= 2
    if tipo == "ficha":
        return bool(c.get("nombre") and c.get("datos"))
    if tipo == "dibujo":
        from . import dibujos_futbol
        return bool(dibujos_futbol.resolver(c.get("dibujo")))
    if tipo == "dibujos":
        from . import dibujos_futbol
        items = c.get("items") or []
        return 2 <= len(items) <= 3 and all(
            dibujos_futbol.resolver(i.get("dibujo") if isinstance(i, dict) else i) for i in items)
    if tipo in ("titular", "cita"):
        return 2 <= len(str(c.get("texto", "")).split()) <= (12 if tipo == "titular" else 30)
    if tipo == "jugada":
        return True
    if tipo == "formacion":
        return bool(re.fullmatch(r"\d(-\d){1,3}", str(c.get("esquema", "")))) and \
            sum(int(x) for x in str(c["esquema"]).split("-")) == 10
    return False


def render(c, dur, destino, semilla=1):
    """Dibuja el cartel cuadro por cuadro y lo pasa a ffmpeg. Devuelve la ruta del mp4."""
    tipo = c["tipo"]
    fondo = c.get("fondo") if c.get("fondo") in FONDOS else FONDO_POR_TIPO[tipo]
    base = FABRICA_FONDO[fondo](semilla).convert("RGBA")
    # leve acercamiento del fondo para que no quede quieto
    grande = base.resize((int(W * 1.08), int(H * 1.08)), Image.BICUBIC)
    cuadros = max(1, int(round(dur * FPS)))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-r", str(FPS), str(destino)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(cuadros):
            t = i / FPS
            z = 1 + 0.08 * (i / max(1, cuadros - 1))
            ancho, alto = int(W * z), int(H * z)
            fondo_t = grande.resize((ancho, alto), Image.BILINEAR) if abs(z - 1.08) > 0.002 else grande
            x0, y0 = (ancho - W) // 2, (alto - H) // 2
            cuadro = fondo_t.crop((x0, y0, x0 + W, y0 + H))
            cuadro = DIBUJAR[tipo](c, cuadro, t, dur, fondo)
            proc.stdin.write(cuadro.convert("RGB").tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló armando el cartel {tipo}")
    return Path(destino)
