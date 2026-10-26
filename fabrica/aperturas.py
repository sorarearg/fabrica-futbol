"""Aperturas por serie: cada video arranca sobre un "objeto de papel" del fútbol con la foto del protagonista.
Todas comparten estilo (papel de época) y dejan lo importante entre y=285 e y=1635 (zona visible en la grilla)."""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from . import marca as mk

W, H = 1080, 1920
PAPEL, TINTA, ROJO, AMARILLO = (243, 235, 216), (28, 24, 20), (176, 30, 38), (255, 212, 0)


def _papel(color=PAPEL, semilla=7):
    im = Image.new("RGB", (W, H), color)
    d = ImageDraw.Draw(im)
    r = random.Random(semilla)
    for _ in range(14000):
        x, y = r.randrange(W), r.randrange(H)
        v = r.randint(-18, 8)
        d.point((x, y), fill=tuple(max(0, min(255, c + v)) for c in color))
    return im, d


def _foto(img_path, ancho, alto, gris=True):
    f = Image.open(img_path).convert("RGB")
    if gris:
        f = ImageOps.autocontrast(ImageOps.grayscale(f).convert("RGB"), cutoff=1)
        f = Image.blend(f, Image.new("RGB", f.size, (120, 100, 70)), 0.12)
    return ImageOps.fit(f, (ancho, alto), Image.LANCZOS, centering=(0.5, 0.3))


def _pegar_con_sombra(im, capa, x, y, borde=12, color_borde=(250, 246, 236)):
    marco = Image.new("RGB", (capa.width + 2 * borde, capa.height + 2 * borde), color_borde)
    marco.paste(capa, (borde, borde))
    sombra = Image.new("RGBA", (marco.width + 40, marco.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle([20, 26, marco.width + 20, marco.height + 26], fill=(0, 0, 0, 110))
    sombra = sombra.filter(ImageFilter.GaussianBlur(12))
    im.paste(sombra, (x - 20, y - 20), sombra)
    im.paste(marco, (x, y))


def _texto(d, xy, texto, estilo, ancho, lineas, grande, chico, color, interlineado=1.05, anchor="ma"):
    fnt, ls = mk.ajustar(d, texto, estilo, ancho, lineas, grande, chico)
    x, y = xy
    for ln in ls:
        d.text((x, y), ln, font=fnt, fill=color, anchor=anchor)
        y = d.textbbox((x, y), ln, font=fnt, anchor=anchor)[3] + int(fnt.size * (interlineado - 1) + 8)
    return y


def tablero(img, l1, l2, dato, usuario):
    """Tablero de estadio: el resultado o el número grande en luces amarillas (batacazos, récords, insólitos, campeones)."""
    im, d = _papel((22, 26, 30))
    d.rounded_rectangle([70, 300, W - 70, 820], 36, fill=(8, 10, 12), outline=(70, 75, 80), width=8)
    for x in range(100, W - 100, 22):  # puntitos de las luces
        for y in (330, 790):
            d.ellipse([x, y, x + 8, y + 8], fill=(60, 55, 20))
    y = _texto(d, (W // 2, 360), (l1 or "").upper(), "titulo" if mk.es_anton() else "bold", W - 220, 2, 96, 50, (235, 235, 235))
    _texto(d, (W // 2, max(y + 10, 520)), (dato or "").upper(), "titulo" if mk.es_anton() else "bold", W - 200, 1, 230, 90, AMARILLO)
    _pegar_con_sombra(im, _foto(img, W - 240, 620, gris=False), 108, 900, color_borde=(40, 44, 48))
    if l2:
        d.rounded_rectangle([140, 1555, W - 140, 1640], 14, fill=AMARILLO)
        _texto(d, (W // 2, 1572), l2.upper(), "bold", W - 320, 1, 54, 30, TINTA)
    return im


def entrada(img, l1, l2, dato, usuario):
    """Entrada del partido: previas y pedidos especiales."""
    im, d = _papel((30, 36, 44))
    x0, y0, x1, y1 = 80, 300, W - 80, 1640
    d.rounded_rectangle([x0, y0, x1, y1], 30, fill=PAPEL)
    d.rectangle([x0, y0 + 30, x1, y0 + 170], fill=ROJO)
    _texto(d, (W // 2, y0 + 60), "ENTRADA · PLATEA", "titulo" if mk.es_anton() else "bold", W - 300, 1, 80, 40, (250, 240, 220))
    for x in range(x0 + 20, x1 - 10, 34):  # troquel
        d.ellipse([x, y1 - 330, x + 14, y1 - 316], fill=(30, 36, 44))
    y = _texto(d, (W // 2, y0 + 210), (l1 or "").upper(), "diario", W - 240, 2, 110, 56, TINTA)
    if dato:
        y = _texto(d, (W // 2, y + 6), dato, "diario_texto", W - 260, 1, 56, 32, ROJO)
    _pegar_con_sombra(im, _foto(img, W - 300, max(300, y1 - 360 - y - 30)), 138, y + 16)
    _texto(d, (W // 2, y1 - 290), (l2 or "").upper(), "bold", W - 300, 2, 56, 30, TINTA)
    d.text((x0 + 40, y1 - 110), "Nº 000" + str(random.Random(l1).randint(100, 999)), font=mk.fuente("semibold", 34), fill=(110, 100, 90))
    return im


MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def almanaque(img, l1, l2, dato, usuario, fecha=None):
    """Hoja de almanaque arrancada con la fecha: Un día como hoy."""
    import datetime as dt
    fecha = fecha or dt.date.today()
    im, d = _papel((52, 40, 32))
    x0, y0, x1 = 120, 300, W - 120
    d.rectangle([x0, y0, x1, 1640], fill=(250, 247, 238))
    d.rectangle([x0, y0, x1, y0 + 150], fill=ROJO)
    for x in range(x0 + 30, x1, 70):  # anillos
        d.ellipse([x, y0 - 22, x + 30, y0 + 8], fill=(150, 150, 150))
    _texto(d, (W // 2, y0 + 25), MESES[fecha.month - 1] + (f" · {dato}" if dato else ""), "titulo" if mk.es_anton() else "bold", x1 - x0 - 60, 1, 100, 50, (255, 255, 255))
    d.text((x0 + 40, y0 + 175), str(fecha.day), font=mk.fuente("titulo" if mk.es_anton() else "bold", 250), fill=TINTA)
    _texto(d, (x0 + 330, y0 + 210), (l1 or "").upper(), "bold", x1 - x0 - 360, 3, 64, 34, TINTA, anchor="la")
    _pegar_con_sombra(im, _foto(img, x1 - x0 - 80, 640), x0 + 28, y0 + 520)
    if l2:
        _texto(d, (W // 2, y0 + 520 + 640 + 50), l2, "diario_texto", x1 - x0 - 80, 1, 50, 30, (90, 70, 50))
    return im


def recibo(img, l1, l2, dato, usuario, titulo="RECIBO DE HABERES"):
    """Recibo de sueldo o contrato: ¿Cuánto ganaba...? y Pases insólitos."""
    im, d = _papel((40, 48, 44))
    x0, y0, x1, y1 = 110, 300, W - 110, 1640
    d.rectangle([x0, y0, x1, y1], fill=(252, 250, 242))
    _texto(d, (x0 + 40, y0 + 40), titulo, "diario_texto", x1 - x0 - 80, 1, 54, 22, TINTA, anchor="la")
    d.line([(x0 + 30, y0 + 120), (x1 - 30, y0 + 120)], fill=TINTA, width=3)
    _pegar_con_sombra(im, _foto(img, 300, 380), x1 - 360, y0 + 150, borde=8)
    y = _texto(d, (x0 + 40, y0 + 170), (l1 or "").upper(), "bold", 470, 4, 64, 34, TINTA, anchor="la")
    for k in range(6):  # renglones del recibo
        yy = max(y, y0 + 580) + k * 60
        d.line([(x0 + 40, yy), (x1 - 40, yy)], fill=(200, 195, 180), width=2)
        d.rectangle([x0 + 40, yy - 34, x0 + 40 + 260 - k * 25, yy - 20], fill=(170, 160, 140))
        d.rectangle([x1 - 240, yy - 34, x1 - 40, yy - 20], fill=(170, 160, 140))
    d.rectangle([x0 + 30, y1 - 330, x1 - 30, y1 - 120], outline=TINTA, width=4)
    _texto(d, (x0 + 60, y1 - 300), "TOTAL", "bold", 300, 1, 44, 30, TINTA, anchor="la")
    _texto(d, (x1 - 60, y1 - 250), dato or "", "titulo" if mk.es_anton() else "bold", x1 - x0 - 300, 1, 120, 50, ROJO, anchor="ra")
    if l2:
        _texto(d, (W // 2, y1 - 95), l2, "diario_texto", x1 - x0 - 80, 1, 42, 26, (90, 70, 50))
    return im


def figurita(img, l1, l2, dato, usuario):
    """Figurita de álbum de época (álbum inventado): ídolos del ascenso y apodos."""
    im, d = _papel((200, 40, 40))
    for k in range(0, W + H, 60):  # fondo rayado de álbum
        d.line([(k, 0), (k - H, H)], fill=(185, 32, 32), width=24)
    x0, y0, x1, y1 = 150, 300, W - 150, 1640
    d.rounded_rectangle([x0, y0, x1, y1], 28, fill=(250, 246, 232))
    d.rounded_rectangle([x0 + 24, y0 + 24, x1 - 24, y1 - 260], 16, fill=(30, 90, 160))
    foto = _foto(img, x1 - x0 - 80, y1 - y0 - 330, gris=False)
    im.paste(foto, (x0 + 40, y0 + 40))
    d.rectangle([x0, y1 - 240, x1, y1 - 120], fill=AMARILLO)
    _texto(d, (W // 2, y1 - 225), (l1 or "").upper(), "titulo" if mk.es_anton() else "bold", x1 - x0 - 60, 1, 90, 40, TINTA)
    _texto(d, (W // 2, y1 - 100), (l2 or dato or "").upper(), "bold", x1 - x0 - 60, 1, 50, 28, TINTA)
    d.ellipse([x1 - 150, y0 - 30, x1 - 10, y0 + 110], fill=AMARILLO, outline=TINTA, width=5)
    d.text((x1 - 80, y0 + 40), str(random.Random(l1).randint(1, 400)), font=mk.fuente("bold", 52), fill=TINTA, anchor="mm")
    return im


def vitrina(img, l1, l2, dato, usuario):
    """La vitrina de las cábalas: el objeto (o el protagonista) en una vitrina de museo con su plaquita."""
    im, d = _papel((24, 20, 18))
    for r in range(600, 0, -20):  # luz cenital
        c = int(24 + (600 - r) / 600 * 40)
        d.ellipse([W // 2 - r, 200 - r // 3, W // 2 + r, 200 + r], fill=(c, c - 4, c - 8))
    x0, y0, x1, y1 = 150, 320, W - 150, 1300
    im.paste(_foto(img, x1 - x0, y1 - y0, gris=False), (x0, y0))
    vidrio = Image.new("RGBA", (x1 - x0, y1 - y0), (200, 220, 230, 40))
    ImageDraw.Draw(vidrio).polygon([(0, 0), (160, 0), (0, 300)], fill=(255, 255, 255, 50))
    im.paste(vidrio, (x0, y0), vidrio)
    d.rectangle([x0 - 20, y0 - 20, x1 + 20, y1 + 20], outline=(180, 160, 110), width=14)
    d.rectangle([x0 - 60, y1 + 20, x1 + 60, y1 + 120], fill=(60, 45, 35))
    d.rounded_rectangle([200, 1380, W - 200, 1620], 12, fill=(196, 168, 100), outline=(120, 95, 50), width=6)
    y = _texto(d, (W // 2, 1405), (l1 or "").upper(), "diario", W - 460, 2, 64, 34, TINTA)
    _texto(d, (W // 2, y + 4), l2 or dato or "", "diario_texto", W - 460, 1, 40, 26, (60, 45, 30))
    return im


DISENOS = {"tablero": tablero, "entrada": entrada, "almanaque": almanaque, "recibo": recibo,
           "contrato": lambda *a: recibo(*a, titulo="CONTRATO DE TRANSFERENCIA"),
           "figurita": figurita, "vitrina": vitrina}


def armar(tipo, img, l1, l2, dato, usuario, veredicto, path):
    from . import video
    im = DISENOS[tipo](img, l1, l2, dato, usuario)
    if usuario:
        ImageDraw.Draw(im).text((W // 2, 1740), usuario, font=mk.fuente("bold", 40), fill=(240, 240, 240), anchor="mm",
                                stroke_width=3, stroke_fill=(0, 0, 0))
    if veredicto:
        tmp = path.with_suffix(".sello.png")
        video.sello(veredicto, tmp, 560)
        s = Image.open(tmp)
        im.paste(s, (W - s.width - 30, 1640 - int(s.height * 0.9)), s)
        tmp.unlink(missing_ok=True)
    im.convert("RGB").save(path, "JPEG", quality=92)
