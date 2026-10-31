"""Dibujitos de fútbol hechos con código (sin IA): pelota, arco, botín, guante, copa, medalla, silbato,
tarjetas, banderín, camiseta, estadio, cronómetro, megáfono, VAR, botella de agua, zapatilla con tapones,
corneta, bombo, bandera, micrófono, escudo genérico, cámara de fotos, diario, billete, avión, valija...

Uso: icono("pelota", 400, colores={"principal": (117, 170, 219)}) -> Image RGBA cuadrada."""
import math

from PIL import Image, ImageDraw, ImageFilter

N = (17, 17, 17)
B = (255, 255, 255)
AM = (255, 212, 0)
RO = (214, 40, 40)
VE = (40, 150, 70)
CE = (117, 170, 219)
GR = (150, 150, 160)
DO = (232, 180, 40)
MA = (140, 90, 50)
L = 12  # grosor del contorno sobre un lienzo de 512


def _lienzo():
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _pelota(d, c):
    d.ellipse([56, 56, 456, 456], fill=B, outline=N, width=L)
    cx, cy, r = 256, 256, 70
    pts = [(cx + r * math.cos(math.radians(-90 + 72 * k)), cy + r * math.sin(math.radians(-90 + 72 * k))) for k in range(5)]
    d.polygon(pts, fill=N)
    for k, (x, y) in enumerate(pts):
        a = math.radians(-90 + 72 * k)
        x2, y2 = cx + 165 * math.cos(a), cy + 165 * math.sin(a)
        d.line([x, y, x2, y2], fill=N, width=L)
        q = [(x2 + 52 * math.cos(a + math.radians(s)), y2 + 52 * math.sin(a + math.radians(s))) for s in (0, 72, 144, 216, 288)]
        d.polygon(q, fill=N)
    d.ellipse([56, 56, 456, 456], outline=N, width=L)


def _arco(d, c):
    d.rectangle([40, 130, 472, 420], fill=(235, 240, 245))
    for x in range(60, 472, 34):
        d.line([x, 130, x, 420], fill=GR, width=3)
    for y in range(150, 420, 34):
        d.line([40, y, 472, y], fill=GR, width=3)
    d.rectangle([28, 118, 484, 140], fill=B, outline=N, width=8)
    d.rectangle([28, 118, 50, 440], fill=B, outline=N, width=8)
    d.rectangle([462, 118, 484, 440], fill=B, outline=N, width=8)
    d.line([0, 440, 512, 440], fill=N, width=8)


def _botin(d, c):
    p = c.get("principal", N)
    d.polygon([(70, 300), (120, 170), (250, 170), (300, 250), (440, 290), (460, 360), (70, 360)], fill=p, outline=N)
    d.line([(70, 300), (120, 170), (250, 170), (300, 250), (440, 290), (460, 360), (70, 360), (70, 300)], fill=N, width=L)
    for k in range(4):
        d.line([150 + k * 30, 190, 200 + k * 30, 230], fill=B, width=8)
    d.polygon([(250, 260), (420, 300), (430, 330), (250, 300)], fill=AM)
    for x in (100, 170, 250, 330, 410):
        d.rectangle([x, 360, x + 26, 400], fill=GR, outline=N, width=6)


def _guante(d, c):
    p = c.get("principal", (60, 200, 120))
    d.rounded_rectangle([140, 230, 380, 470], 50, fill=p, outline=N, width=L)
    for k, x in enumerate((150, 210, 270, 330)):
        top = 70 if k in (1, 2) else 100
        d.rounded_rectangle([x, top, x + 56, 280], 28, fill=p, outline=N, width=L)
    d.rounded_rectangle([60, 250, 170, 330], 36, fill=p, outline=N, width=L)
    d.rectangle([150, 400, 370, 460], fill=B, outline=N, width=L)


def _copa(d, c):
    p = c.get("principal", DO)
    d.arc([60, 110, 200, 290], 90, 270, fill=N, width=L * 2)
    d.arc([312, 110, 452, 290], 270, 90, fill=N, width=L * 2)
    d.pieslice([120, -40, 392, 340], 0, 180, fill=p, outline=N, width=L)
    d.rectangle([120, 60, 392, 150], fill=p)
    d.line([120, 60, 392, 60], fill=N, width=L)
    d.line([120, 60, 120, 150], fill=N, width=L)
    d.line([392, 60, 392, 150], fill=N, width=L)
    d.rectangle([226, 330, 286, 400], fill=p, outline=N, width=L)
    d.rounded_rectangle([150, 400, 362, 470], 12, fill=MA, outline=N, width=L)
    d.ellipse([200, 120, 312, 232], fill=(255, 235, 140))
    d.text((256, 176), "1", fill=N, anchor="mm")


def _medalla(d, c):
    d.polygon([(170, 20), (240, 20), (300, 230), (230, 230)], fill=CE, outline=N)
    d.polygon([(342, 20), (272, 20), (212, 230), (282, 230)], fill=RO, outline=N)
    d.ellipse([116, 200, 396, 480], fill=c.get("principal", DO), outline=N, width=L)
    d.ellipse([170, 254, 342, 426], outline=(180, 130, 20), width=10)
    _estrella(d, 256, 340, 60, N)


def _estrella(d, cx, cy, r, color):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        a = math.radians(-90 + 36 * k)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)


def _silbato(d, c):
    d.ellipse([60, 180, 300, 420], fill=GR, outline=N, width=L)
    d.rounded_rectangle([180, 180, 470, 290], 20, fill=GR, outline=N, width=L)
    d.ellipse([140, 260, 220, 340], fill=N)
    d.arc([10, 60, 200, 260], 180, 330, fill=RO, width=14)


def _tarjeta(d, c, color):
    d.rounded_rectangle([150, 60, 390, 450], 24, fill=(0, 0, 0, 90))
    d.rounded_rectangle([130, 40, 370, 430], 24, fill=color, outline=N, width=L)


def _banderin(d, c):
    d.rectangle([150, 40, 172, 480], fill=B, outline=N, width=6)
    d.polygon([(172, 50), (440, 120), (172, 200)], fill=c.get("principal", AM), outline=N)
    d.line([(172, 50), (440, 120), (172, 200)], fill=N, width=L)
    d.ellipse([110, 450, 212, 490], fill=VE)


def _camiseta(d, c):
    p = c.get("principal", CE)
    s = c.get("secundario", B)
    contorno = [(150, 60), (210, 40), (256, 80), (302, 40), (362, 60), (480, 150), (420, 240), (380, 210),
                (380, 470), (132, 470), (132, 210), (92, 240), (32, 150)]
    d.polygon(contorno, fill=s)
    if c.get("rayas", True):
        for x in range(150, 380, 70):
            d.rectangle([x, 45, x + 35, 470], fill=p)
    im_mask = None  # noqa
    d.line(contorno + [contorno[0]], fill=N, width=L)
    d.arc([210, 20, 302, 110], 20, 160, fill=N, width=L)
    if c.get("numero"):
        d.text((256, 280), str(c["numero"]), fill=N, anchor="mm")


def _estadio(d, c):
    d.ellipse([20, 180, 492, 470], fill=(70, 70, 85), outline=N, width=L)
    d.ellipse([90, 230, 422, 420], fill=VE, outline=N, width=8)
    d.line([256, 232, 256, 418], fill=B, width=5)
    d.ellipse([226, 300, 286, 350], outline=B, width=5)
    for x in (60, 452):
        d.rectangle([x - 8, 40, x + 8, 230], fill=GR, outline=N, width=5)
        d.rectangle([x - 40, 30, x + 40, 80], fill=(255, 250, 210), outline=N, width=6)


def _cronometro(d, c):
    d.rectangle([226, 30, 286, 80], fill=GR, outline=N, width=8)
    d.ellipse([76, 80, 436, 440], fill=B, outline=N, width=L)
    for k in range(12):
        a = math.radians(30 * k)
        d.line([256 + 140 * math.cos(a), 260 + 140 * math.sin(a), 256 + 160 * math.cos(a), 260 + 160 * math.sin(a)],
               fill=N, width=8)
    d.pieslice([116, 120, 396, 400], -90, 180, fill=(255, 225, 120))
    d.line([256, 260, 256, 140], fill=N, width=12)
    d.line([256, 260, 340, 300], fill=RO, width=10)
    d.ellipse([240, 244, 272, 276], fill=N)


def _megafono(d, c):
    d.polygon([(110, 200), (380, 70), (380, 440), (110, 310)], fill=c.get("principal", RO), outline=N)
    d.line([(110, 200), (380, 70), (380, 440), (110, 310), (110, 200)], fill=N, width=L)
    d.rounded_rectangle([50, 190, 120, 320], 16, fill=GR, outline=N, width=L)
    for k in range(3):
        d.arc([380 - 30 + k * 30, 170 - k * 40, 460 + k * 30, 340 + k * 40], -40, 40, fill=N, width=10)


def _var(d, c):
    d.rounded_rectangle([40, 70, 472, 370], 24, fill=N, outline=GR, width=10)
    d.rectangle([70, 100, 442, 340], fill=(40, 120, 200))
    d.text((256, 220), "VAR", fill=B, anchor="mm")
    d.rectangle([236, 370, 276, 440], fill=GR, outline=N, width=6)
    d.rounded_rectangle([150, 440, 362, 480], 10, fill=GR, outline=N, width=6)


def _bombo(d, c):
    d.ellipse([60, 120, 452, 230], fill=(240, 230, 210), outline=N, width=L)
    d.rectangle([60, 175, 452, 400], fill=c.get("principal", CE))
    d.ellipse([60, 345, 452, 455], fill=c.get("principal", CE), outline=N, width=L)
    d.rectangle([60, 175, 452, 400], outline=None)
    d.line([60, 175, 60, 400], fill=N, width=L)
    d.line([452, 175, 452, 400], fill=N, width=L)
    for x in range(80, 452, 60):
        d.line([x, 190, x + 30, 390], fill=B, width=6)
    d.ellipse([60, 120, 452, 230], outline=N, width=L)
    d.line([420, 60, 330, 160], fill=MA, width=14)
    d.ellipse([400, 30, 460, 90], fill=B, outline=N, width=8)


def _bandera(d, c):
    d.rectangle([60, 30, 82, 490], fill=MA, outline=N, width=6)
    p = c.get("principal", CE)
    s = c.get("secundario", B)
    d.rectangle([82, 50, 470, 150], fill=p)
    d.rectangle([82, 150, 470, 250], fill=s)
    d.rectangle([82, 250, 470, 350], fill=p)
    if c.get("sol", True):
        d.ellipse([246, 170, 306, 230], fill=DO, outline=(180, 120, 20), width=4)
    d.rectangle([82, 50, 470, 350], outline=N, width=L)


def _microfono(d, c):
    d.rounded_rectangle([186, 40, 326, 280], 70, fill=GR, outline=N, width=L)
    for y in range(80, 260, 30):
        d.line([200, y, 312, y], fill=(110, 110, 120), width=5)
    d.arc([136, 160, 376, 360], 0, 180, fill=N, width=L)
    d.rectangle([246, 360, 266, 440], fill=N)
    d.rounded_rectangle([170, 440, 342, 470], 10, fill=N)


def _escudo(d, c):
    p = c.get("principal", RO)
    s = c.get("secundario", B)
    forma = [(96, 60), (416, 60), (416, 260), (256, 470), (96, 260)]
    d.polygon(forma, fill=s)
    d.polygon([(96, 60), (256, 60), (256, 470), (96, 260)], fill=p)
    d.line(forma + [forma[0]], fill=N, width=L)
    _estrella(d, 256, 140, 40, DO)


def _camara(d, c):
    d.rounded_rectangle([50, 150, 462, 430], 30, fill=(50, 50, 60), outline=N, width=L)
    d.rectangle([170, 100, 300, 160], fill=(50, 50, 60), outline=N, width=L)
    d.ellipse([166, 196, 346, 376], fill=(30, 30, 40), outline=GR, width=14)
    d.ellipse([216, 246, 296, 326], fill=(80, 120, 170))
    d.rectangle([380, 180, 430, 210], fill=AM)


def _diario(d, c):
    d.polygon([(70, 90), (440, 60), (460, 440), (90, 470)], fill=(236, 226, 202), outline=N)
    d.line([(70, 90), (440, 60), (460, 440), (90, 470), (70, 90)], fill=N, width=L)
    d.rectangle([110, 110, 420, 170], fill=N)
    for k in range(7):
        d.line([120, 210 + k * 30, 260, 205 + k * 30], fill=GR, width=10)
        d.line([290, 200 + k * 30, 420, 195 + k * 30], fill=GR, width=10)


def _billete(d, c):
    for k, dx in enumerate((40, 0)):
        d.rounded_rectangle([40 + dx, 150 - dx, 470 + dx - 40, 380 - dx], 16, fill=(110, 190, 110) if k else (90, 170, 90),
                            outline=N, width=L)
    d.ellipse([200, 165, 300, 285], outline=N, width=10)
    d.text((256, 225), "$", fill=N, anchor="mm")


def _avion(d, c):
    d.polygon([(40, 280), (420, 200), (480, 230), (440, 270), (60, 320)], fill=B, outline=N)
    d.line([(40, 280), (420, 200), (480, 230), (440, 270), (60, 320), (40, 280)], fill=N, width=L)
    d.polygon([(220, 250), (300, 120), (350, 120), (300, 240)], fill=CE, outline=N)
    d.polygon([(220, 290), (290, 420), (340, 420), (300, 280)], fill=CE, outline=N)
    d.polygon([(60, 290), (60, 190), (110, 190), (130, 270)], fill=CE, outline=N)


def _valija(d, c):
    d.rounded_rectangle([190, 70, 322, 150], 20, outline=N, width=L)
    d.rounded_rectangle([60, 130, 452, 450], 30, fill=MA, outline=N, width=L)
    d.rectangle([60, 260, 452, 290], fill=(100, 60, 30))
    d.rectangle([230, 250, 282, 300], fill=DO, outline=N, width=6)


def _zapatilla(d, c):  # botín clásico de cuero, para historias de época
    d.polygon([(60, 320), (110, 180), (260, 160), (330, 260), (460, 300), (460, 370), (60, 370)], fill=(60, 40, 25))
    d.line([(60, 320), (110, 180), (260, 160), (330, 260), (460, 300), (460, 370), (60, 370), (60, 320)], fill=N, width=L)
    for k in range(5):
        d.line([140 + k * 28, 200, 190 + k * 28, 250], fill=B, width=6)
    for x in (100, 180, 260, 340, 420):
        d.rectangle([x, 370, x + 22, 405], fill=(60, 40, 25), outline=N, width=5)


def _pelota_vieja(d, c):
    d.ellipse([56, 56, 456, 456], fill=(170, 110, 60), outline=N, width=L)
    for k in range(-2, 3):
        d.arc([56 + abs(k) * 50, 56, 456 - abs(k) * 50, 456], 270 if k < 0 else 90, 90 if k < 0 else 270, fill=N, width=6)
    d.line([256, 56, 256, 456], fill=N, width=6)
    for y in (200, 236, 272, 308):
        d.line([236, y, 276, y + 8], fill=(240, 230, 210), width=6)


def _corazon(d, c):
    p = c.get("principal", RO)
    d.ellipse([70, 90, 270, 290], fill=p)
    d.ellipse([242, 90, 442, 290], fill=p)
    d.polygon([(80, 230), (432, 230), (256, 450)], fill=p)
    d.arc([70, 90, 270, 290], 140, 360, fill=N, width=L)
    d.arc([242, 90, 442, 290], 180, 40, fill=N, width=L)
    d.line([(85, 245), (256, 450), (427, 245)], fill=N, width=L)


def _fuego(d, c):
    d.polygon([(256, 30), (360, 200), (410, 160), (420, 330), (340, 470), (172, 470), (92, 330), (120, 190),
               (170, 240)], fill=(255, 120, 30), outline=N)
    d.polygon([(256, 200), (320, 330), (300, 440), (212, 440), (192, 330)], fill=AM)


def _rayo(d, c):
    d.polygon([(290, 20), (100, 290), (240, 290), (200, 490), (420, 200), (280, 200), (340, 20)], fill=AM, outline=N)
    d.line([(290, 20), (100, 290), (240, 290), (200, 490), (420, 200), (280, 200), (340, 20), (290, 20)], fill=N, width=L)


def _signo(d, c, txt, color):
    d.ellipse([56, 56, 456, 456], fill=color, outline=N, width=L)
    d.text((256, 256), txt, fill=B, anchor="mm")


DIBUJOS = {
    "pelota": _pelota, "arco": _arco, "botin": _botin, "guante": _guante, "copa": _copa, "medalla": _medalla,
    "silbato": _silbato, "tarjeta_amarilla": lambda d, c: _tarjeta(d, c, AM),
    "tarjeta_roja": lambda d, c: _tarjeta(d, c, RO), "banderin": _banderin, "camiseta": _camiseta,
    "estadio": _estadio, "cronometro": _cronometro, "megafono": _megafono, "var": _var, "bombo": _bombo,
    "bandera": _bandera, "microfono": _microfono, "escudo": _escudo, "camara": _camara, "diario": _diario,
    "billete": _billete, "avion": _avion, "valija": _valija, "botin_viejo": _zapatilla,
    "pelota_vieja": _pelota_vieja, "corazon": _corazon, "fuego": _fuego, "rayo": _rayo,
    "pregunta": lambda d, c: _signo(d, c, "?", (40, 120, 200)), "alerta": lambda d, c: _signo(d, c, "!", RO),
}

# palabras en castellano que la IA puede usar → dibujo
SINONIMOS = {"balon": "pelota", "gol": "pelota", "trofeo": "copa", "campeon": "copa", "titulo": "copa",
             "arquero": "guante", "atajada": "guante", "arbitro": "silbato", "referi": "silbato",
             "expulsion": "tarjeta_roja", "roja": "tarjeta_roja", "amarilla": "tarjeta_amarilla",
             "hinchada": "bombo", "hinchas": "bombo", "cancha": "estadio", "tiempo": "cronometro",
             "minuto": "cronometro", "prensa": "microfono", "periodista": "microfono", "foto": "camara",
             "plata": "billete", "pase": "billete", "sueldo": "billete", "viaje": "avion", "seleccion": "bandera",
             "argentina": "bandera", "club": "escudo", "noticia": "diario", "record": "medalla",
             "polemica": "var", "amor": "corazon", "racha": "fuego", "rapido": "rayo", "misterio": "pregunta"}


def nombres():
    return sorted(DIBUJOS)


def resolver(nombre):
    n = str(nombre or "").lower().strip().replace(" ", "_")
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        n = n.replace(a, b)
    if n in DIBUJOS:
        return n
    return SINONIMOS.get(n)


def icono(nombre, tam=400, colores=None, sombra=True):
    n = resolver(nombre) or "pelota"
    im, d = _lienzo()
    from PIL import ImageFont
    from . import carteles
    d.font = carteles.fuente("titulo", 150)  # para los textos dentro de los dibujos (VAR, $, ?, !)
    DIBUJOS[n](d, dict(colores or {}))
    if sombra:
        s = Image.new("RGBA", (560, 560), (0, 0, 0, 0))
        a = im.getchannel("A").point(lambda v: 120 if v > 10 else 0)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 255))
        sh.putalpha(a)
        s.alpha_composite(sh, (24, 30))
        s = s.filter(ImageFilter.GaussianBlur(10))
        s.alpha_composite(im, (0, 0))
        im = s
    _ = ImageFont
    return im.resize((tam, tam), Image.LANCZOS)
