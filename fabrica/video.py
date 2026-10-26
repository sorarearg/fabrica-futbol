#!/usr/bin/env python3
"""
Fábrica de Shorts — renderizador.

Recibe un "spec" JSON (lo arma n8n con Gemini) y genera:
  out/video.mp4   1080x1920, voz argentina, imágenes stickman, subtítulos palabra por palabra
  out/thumb.jpg   miniatura / portada (también es el primer fotograma del video)
  out/meta.json   duración y datos útiles

Uso:  python render.py spec.json
Variables de entorno (secretos de GitHub):
  CF_ACCOUNT_ID, CF_API_TOKEN   -> imágenes con Cloudflare Workers AI (FLUX schnell, gratis)
  POLLINATIONS_KEY              -> (opcional) respaldo de imágenes
  TTS_VOICE                     -> por defecto es-AR-TomasNeural (alternativa: es-AR-ElenaNeural)
  TTS_RATE                      -> por defecto +15%
  TTS_MAX_PAUSA                 -> pausa máxima entre palabras, en segundos (por defecto 0.28)
  TTS_ENGINE                    -> edge (defecto) | silent (solo para pruebas locales)
"""
import asyncio, base64, json, os, random, re, subprocess, sys, textwrap, time, urllib.parse
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from . import marca as mk

W, H, FPS = 1080, 1920, 30
IMG_SIZE, IMG_Y = 1080, 380          # imagen cuadrada en el centro
SUB_Y = 1570                          # centro de los subtítulos (zona segura, arriba de la UI de las apps)
PAD = 0.06                            # respiro entre escenas (seg)
COLA = 0.10                           # silencio que queda después de la última palabra de cada escena
INTRO = 0.5                           # la miniatura se ve el primer medio segundo
BG = (255, 255, 255)
ACCENT = (255, 212, 0)                # amarillo
DARK = (17, 17, 17)

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
OUT = ROOT / "out"
WORK = ROOT / "work"

STYLE = ("Simple 2D stickman cartoon illustration, thick clean black outlines, flat colors, "
         "a few accents of yellow and green, plain white background, minimalist explainer video style, "
         "centered composition, expressive stick figure, no text, no letters, no words, no numbers. Scene: ")

VOICE = os.getenv("TTS_VOICE", "es-AR-TomasNeural")
RATE = os.getenv("TTS_RATE", "+15%")
MAX_PAUSA = float(os.getenv("TTS_MAX_PAUSA", "0.28"))   # ninguna pausa dentro de una escena dura más que esto
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")


# ---------------------------------------------------------------- utilidades
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise RuntimeError("Falló: " + " ".join(cmd[:6]))
    return r.stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", str(path)]).strip())


def font(size):
    return mk.fuente("titulo", size)


def ass_font_name():
    if (FONTS / "Anton-Regular.ttf").exists():
        return "Anton"
    return "Poppins" if mk._ruta_fuente("bold") and "Poppins" in mk._ruta_fuente("bold") else "DejaVu Sans"


def wrap_to_width(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, max_w, max_lines, start, min_size=40):
    size = start
    while size > min_size:
        fnt = font(size)
        lines = wrap_to_width(draw, text, fnt, max_w)
        if len(lines) <= max_lines:
            return fnt, lines
        size -= 4
    fnt = font(min_size)
    return fnt, wrap_to_width(draw, text, fnt, max_w)[:max_lines]


# ---------------------------------------------------------------- imágenes
def gen_image_cloudflare(prompt, seed):
    acc, tok = os.getenv("CF_ACCOUNT_ID"), os.getenv("CF_API_TOKEN")
    if not (acc and tok):
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    cuerpos = [{"prompt": (STYLE + prompt)[:1900], "steps": 6, "seed": int(seed) % 2_000_000_000},
               {"prompt": (STYLE + prompt)[:1000]}]
    ultimo = ""
    for cuerpo in cuerpos:
        r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json=cuerpo, timeout=120)
        if r.status_code == 200:
            datos = r.json().get("result") or {}
            if datos.get("image"):
                return base64.b64decode(datos["image"])
            ultimo = f"200 sin imagen: {str(r.text)[:200]}"
            continue
        ultimo = f"{r.status_code}: {r.text[:300]}"
        if r.status_code in (401, 403, 404):
            break
    raise RuntimeError("Cloudflare " + ultimo)


def gen_image_pollinations(prompt, seed):
    """Pollinations con clave (opcional, secreto POLLINATIONS_KEY)."""
    key = os.getenv("POLLINATIONS_KEY")
    if not key:
        return None
    q = urllib.parse.quote((STYLE + prompt)[:1500])
    r = requests.get(f"https://gen.pollinations.ai/image/{q}",
                     params={"width": 768, "height": 1344, "seed": seed, "key": key, "nologo": "true"}, timeout=180)
    r.raise_for_status()
    return _si_es_imagen(r)


def gen_image_pollinations_libre(prompt, seed):
    """Pollinations sin clave ni cuenta (gratis, más lento y con límite de pedidos por minuto)."""
    q = urllib.parse.quote((STYLE + prompt)[:1500])
    r = requests.get(f"https://image.pollinations.ai/prompt/{q}",
                     params={"width": 768, "height": 1344, "seed": seed, "nologo": "true", "model": "flux"},
                     timeout=180)
    r.raise_for_status()
    return _si_es_imagen(r)


def _si_es_imagen(r):
    tipo = r.headers.get("content-type", "")
    if "image" not in tipo or len(r.content) < 5000:
        raise RuntimeError(f"no devolvió una imagen ({tipo}, {len(r.content)} bytes)")
    return r.content


MOTORES_IMAGEN = {"gen_image_cloudflare": "Cloudflare", "gen_image_pollinations": "Pollinations (con clave)",
                  "gen_image_pollinations_libre": "Pollinations (libre)"}
ULTIMO_MOTOR = {"nombre": None}


def fallback_card(text, path, emoji=""):
    """Sin IA de imágenes: placa de marca con emoji grande y el texto de pantalla."""
    im = Image.new("RGB", (1024, 1024), mk.CREMA)
    d = ImageDraw.Draw(im)
    if emoji and not text.strip():
        mk.pegar_emoji(im, emoji, (512, 512), 600)
        im.save(path)
        return
    tiene_emoji = mk.pegar_emoji(im, emoji, (512, 330), 380) if emoji else False
    texto = text.upper() if mk.es_anton() else text
    estilo = "titulo" if mk.es_anton() else "bold"
    fnt, lines = mk.ajustar(d, texto, estilo, 880, 3 if tiene_emoji else 6, 110, 56)
    lh = fnt.size * 1.08
    y = (600 if tiene_emoji else 512 - lh * len(lines) / 2)
    for ln in lines:
        d.text((512, y), ln, font=fnt, fill=DARK, anchor="ma")
        y += lh
    im.save(path)


def _avisar_motor(nombre, texto):
    try:
        from . import util
        util.avisar(f"El motor de imágenes {MOTORES_IMAGEN.get(nombre, nombre)} no anda",
                    texto[:600] + " · Sigo con el siguiente motor (o con tarjetas).")
    except Exception:  # noqa
        pass


_ROTOS = {}  # motores que fallaron de forma permanente en esta ejecución (no se reintentan con cada imagen)


def make_image(prompt, fallback_text, path, seed, emoji=""):
    """Devuelve el nombre del motor que dibujó la imagen, o "tarjeta" si ninguno anduvo."""
    for fn in (gen_image_cloudflare, gen_image_pollinations, gen_image_pollinations_libre):
        if _ROTOS.get(fn.__name__, 0) >= 2:
            continue
        for attempt in range(3):
            try:
                data = fn(prompt, seed + attempt)
                if data is None:
                    break
                path.write_bytes(data)
                Image.open(path).convert("RGB").save(path, "PNG")
                ULTIMO_MOTOR["nombre"] = MOTORES_IMAGEN.get(fn.__name__, fn.__name__)
                return ULTIMO_MOTOR["nombre"]
            except Exception as e:  # noqa
                texto = str(e)
                print(f"[img] {fn.__name__} intento {attempt+1}: {texto[:400]}")
                if any(c in texto for c in ("400", "401", "402", "403", "404")):
                    # error de configuración o de pago: no tiene sentido insistir con este motor
                    _ROTOS[fn.__name__] = _ROTOS.get(fn.__name__, 0) + 1
                    if _ROTOS[fn.__name__] == 2:
                        _avisar_motor(fn.__name__, texto)
                    break
                time.sleep(6 * (attempt + 1))
    fallback_card(fallback_text, path, emoji)
    return "tarjeta"


def portada_historia(img_path, l1, l2, usuario, path):
    """Portada: la ilustración de fondo a pantalla completa y el título grande en la zona central,
    para que no se corte ni en la grilla de Instagram (4:5 y 1:1) ni en YouTube o TikTok."""
    base = Image.open(img_path).convert("RGB")
    esc = max(W / base.width, H / base.height)
    base = base.resize((int(base.width * esc + 1), int(base.height * esc + 1)), Image.LANCZOS)
    x, y = (base.width - W) // 2, (base.height - H) // 2
    im = base.crop((x, y, x + W, y + H))
    # oscurecido parejo y más fuerte en la franja del texto
    sombra = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(sombra)
    for yy in range(H):
        d = abs(yy - 960) / 960
        ds.line([(0, yy), (W, yy)], fill=int(165 * max(0.0, 1 - d * 1.15) + 40))
    im = Image.composite(Image.new("RGB", (W, H), (8, 8, 12)), im, sombra)
    d = ImageDraw.Draw(im)
    estilo = "titulo" if mk.es_anton() else "bold"
    t1 = (l1 or "").upper()
    fnt1, lines1 = mk.ajustar(d, t1, estilo, W - 150, 3, 168, 80)
    lh1 = fnt1.size * (1.0 if mk.es_anton() else 1.08)
    alto = lh1 * len(lines1)
    fnt2 = lines2 = None
    if l2:
        fnt2, lines2 = mk.ajustar(d, l2.upper(), estilo, W - 260, 1, 104, 56)
        alto += fnt2.size * 1.35 + 26
    # todo el texto entra en la franja 640..1280 (centro de la grilla 1:1 y 4:5)
    yy = 960 - alto / 2
    for ln in lines1:
        d.text((W // 2, yy), ln, font=fnt1, fill=(255, 255, 255), anchor="ma", stroke_width=6, stroke_fill=(0, 0, 0))
        yy += lh1
    if lines2:
        yy += 26
        tw = d.textlength(lines2[0], font=fnt2)
        caja = fnt2.size * 1.35
        d.rounded_rectangle([W / 2 - tw / 2 - 34, yy, W / 2 + tw / 2 + 34, yy + caja], 20, fill=ACCENT)
        d.text((W // 2, yy + caja / 2), lines2[0], font=fnt2, fill=DARK, anchor="mm")
    if usuario:
        d.text((W // 2, 1420), usuario, font=mk.fuente("semibold", 40), fill=(255, 255, 255), anchor="ma",
               stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(path, "JPEG", quality=92)


ROJO_SELLO = (196, 22, 34)
PAPEL = (243, 235, 216)
TINTA = (28, 24, 20)


def sello(texto, path, ancho=760):
    """Sello de veredicto (MITO, VERDAD, A MEDIAS, NUNCA SE PROBÓ), torcido como un sello de goma."""
    from PIL import ImageFilter
    alto = 230
    im = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    color = (22, 140, 60, 240) if texto == "VERDAD" else (ROJO_SELLO + (240,))
    d.rounded_rectangle([10, 10, ancho - 10, alto - 10], 26, outline=color, width=16)
    d.rounded_rectangle([34, 34, ancho - 34, alto - 34], 16, outline=color, width=4)
    fnt, lineas = mk.ajustar(d, texto, "titulo" if mk.es_anton() else "bold", ancho - 120, 1, 130, 50)
    d.text((ancho // 2, alto // 2), lineas[0], font=fnt, fill=color, anchor="mm")
    # textura gastada
    import random
    r = random.Random(len(texto))
    px = im.load()
    for _ in range(ancho * alto // 9):
        x, y = r.randrange(ancho), r.randrange(alto)
        if px[x, y][3]:
            px[x, y] = px[x, y][:3] + (r.randint(60, 200),)
    im = im.filter(ImageFilter.GaussianBlur(0.6)).rotate(-9, expand=True, resample=Image.BICUBIC)
    im.save(path)
    return path


def portada_diario(img_path, l1, l2, usuario, nombre_diario, fecha, veredicto, path):
    """Tapa de diario de época. Todo lo importante (titular, foto y sello) queda entre y=285 y y=1635,
    la zona que se ve en la grilla de Instagram (4:5) y en la vista cuadrada."""
    import random
    from PIL import ImageFilter, ImageOps
    im = Image.new("RGB", (W, H), PAPEL)
    d = ImageDraw.Draw(im)
    r = random.Random(7)
    for _ in range(14000):  # grano de papel
        x, y = r.randrange(W), r.randrange(H)
        v = r.randint(200, 232)
        d.point((x, y), fill=(v, v - 8, v - 24))
    # cabezal
    fm, lm = mk.ajustar(d, nombre_diario.upper(), "diario", W - 140, 1, 120, 60)
    d.text((W // 2, 330), lm[0], font=fm, fill=TINTA, anchor="mm")
    d.line([(60, 410), (W - 60, 410)], fill=TINTA, width=7)
    d.line([(60, 423), (W - 60, 423)], fill=TINTA, width=2)
    fs = mk.fuente("diario_texto", 34)
    d.text((70, 440), fecha or "Edición especial", font=fs, fill=TINTA)
    d.text((W - 70, 440), "Edición especial" if fecha else "", font=fs, fill=TINTA, anchor="ra")
    d.line([(60, 492), (W - 60, 492)], fill=TINTA, width=2)
    # titular
    ft, lt = mk.ajustar(d, (l1 or "").upper(), "diario", W - 120, 2, 150, 70)
    y = 515
    for ln in lt:
        d.text((W // 2, y), ln, font=ft, fill=TINTA, anchor="ma")
        y += int(ft.size * 1.05)
    if l2:
        f2, l2s = mk.ajustar(d, l2, "diario_texto", W - 200, 1, 58, 36)
        d.text((W // 2, y + 6), l2s[0], font=f2, fill=(90, 70, 50), anchor="ma")
        y += int(f2.size * 1.4)
    # foto en blanco y negro con marco, como en un diario
    tope = 1560
    caja_y0 = max(y + 24, 760)
    caja_alto = tope - caja_y0
    foto = Image.open(img_path).convert("RGB")
    foto = ImageOps.grayscale(foto).convert("RGB")
    foto = ImageOps.autocontrast(foto, cutoff=1)
    foto = Image.blend(foto, Image.new("RGB", foto.size, (120, 100, 70)), 0.12)  # tono sepia suave
    caja_ancho = W - 220
    foto = ImageOps.fit(foto, (caja_ancho, caja_alto), Image.LANCZOS, centering=(0.5, 0.3))
    marco = Image.new("RGB", (caja_ancho + 24, caja_alto + 24), (250, 246, 236))
    marco.paste(foto, (12, 12))
    sombra = Image.new("RGBA", (marco.width + 40, marco.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle([20, 26, marco.width + 20, marco.height + 26], fill=(0, 0, 0, 110))
    sombra = sombra.filter(ImageFilter.GaussianBlur(12))
    x0 = (W - marco.width) // 2
    im.paste(sombra, (x0 - 20, caja_y0 - 20), sombra)
    im.paste(marco, (x0, caja_y0))
    # columnas de texto falso a los costados del pie
    for k in range(4):
        yy = tope + 30 + k * 26
        d.rectangle([90, yy, W // 2 - 30, yy + 10], fill=(160, 150, 132))
        d.rectangle([W // 2 + 30, yy, W - 90 - (60 if k == 3 else 0), yy + 10], fill=(160, 150, 132))
    if veredicto:
        tmp = Path(str(path) + ".sello.png")
        sello(veredicto, tmp, 700)
        s_im = Image.open(tmp)
        im.paste(s_im, ((W - s_im.width) // 2, tope - s_im.height - 40), s_im)
        tmp.unlink(missing_ok=True)
    if usuario:
        d.text((W // 2, 1735), usuario, font=mk.fuente("bold", 40), fill=TINTA, anchor="mm")
    im.save(path, "JPEG", quality=92)


# ---------------------------------------------------------------- voz
async def tts_edge(text, mp3_path):
    import edge_tts
    try:
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    except TypeError:  # versiones viejas de edge-tts
        comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    words = []
    with open(mp3_path, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append([s, s + ch["duration"] / 1e7, ch["text"]])
    return words


def tts_silent(text, mp3_path):
    """Solo para pruebas sin internet: audio mudo con tiempos estimados."""
    toks = text.split()
    dur = max(1.5, len(toks) * 0.36)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{dur:.2f}",
         "-c:a", "libmp3lame", "-b:a", "64k", str(mp3_path)])
    step = dur / len(toks)
    return [[i * step, (i + 1) * step, t] for i, t in enumerate(toks)]


def synth(text, mp3_path):
    if TTS_ENGINE == "silent":
        return tts_silent(text, mp3_path)
    last = None
    for attempt in range(4):
        try:
            words = asyncio.run(tts_edge(text, mp3_path))
            if mp3_path.exists() and mp3_path.stat().st_size > 1000:
                return words
        except Exception as e:  # noqa
            last = e
            print(f"[tts] intento {attempt+1}: {e}")
            time.sleep(5 * (attempt + 1))
    print(f"[tts] Sin voz hoy ({last}): el video sale solo con texto en pantalla")
    return tts_silent(text, mp3_path)


_PRONUNCIA = {"ARCA": "Arca", "ANSES": "Anses", "AFIP": "Afip", "CUIT": "Cuit", "CUIL": "Cuil", "IVA": "Iva",
              "ARBA": "Arba", "AGIP": "Agip", "IIBB": "Ingresos Brutos", "BCRA": "Banco Central", "FMI": "Fondo Monetario"}


def texto_voz(t):
    """Ajustes para que la voz lea natural: siglas que se dicen como palabra y puntos suspensivos."""
    t = re.sub(r"\.{2,}|…", ",", t or "")
    for sigla, dicha in _PRONUNCIA.items():
        t = re.sub(r"\b" + sigla + r"\b", dicha, t)
    return re.sub(r"\s+", " ", t).strip()


def compactar(mp3_path, words, wav_path):
    """Saca los silencios de más que mete el TTS: al principio, entre palabras (las pausas largas
    se acortan a MAX_PAUSA) y al final. Devuelve las palabras con los tiempos corridos."""
    dur = duration(mp3_path)
    words = sorted([w for w in words if w[1] > w[0] or w[2]], key=lambda w: w[0])
    cortes = []
    if words:
        inicio = max(0.0, words[0][0] - 0.04)
        if inicio > 0.02:
            cortes.append((0.0, inicio))
        for a, b in zip(words, words[1:]):
            if b[0] - a[1] > MAX_PAUSA:
                cortes.append((a[1] + MAX_PAUSA / 2, b[0] - MAX_PAUSA / 2))
        fin = min(dur, words[-1][1] + COLA)
        if dur - fin > 0.02:
            cortes.append((fin, dur + 1))
    filtro = "aresample=44100"
    if cortes:
        expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in cortes)
        filtro += f",asetnsamples=n=64:p=0,aselect='not({expr})',asetpts=N/SR/TB"
    run(["ffmpeg", "-y", "-i", str(mp3_path), "-af", filtro, "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)])

    def corrido(t):
        return t - sum(min(b, t) - a for a, b in cortes if t > a)

    return [[corrido(w[0]), corrido(w[1]), w[2]] for w in words], duration(wav_path)


def align_words(text, words, dur):
    """Usa las palabras del guion (con puntuación) y los tiempos del TTS."""
    toks = text.split()
    if words and len(words) == len(toks):
        return [[w[0], w[1], t] for w, t in zip(words, toks)]
    if words:
        return words
    step = dur / max(1, len(toks))
    return [[i * step, (i + 1) * step, t] for i, t in enumerate(toks)]


# ---------------------------------------------------------------- subtítulos (ASS)
def ass_time(t):
    t = max(0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def chunk_words(words, max_words=3, max_chars=18):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x[2] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or re.search(r"[.,;:?!…]$", w[2]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def clean_sub(t):
    return re.sub(r"[{}\\]", "", t).upper()


def build_ass(all_words, path, start_at):
    fname = ass_font_name()
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{fname},104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,8,3,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    eventos = []
    for ch in chunk_words(all_words):
        for i, w in enumerate(ch):
            s = w[0]
            e = ch[i + 1][0] if i + 1 < len(ch) else w[1] + 0.25
            parts = []
            for j, x in enumerate(ch):
                t = clean_sub(x[2])
                parts.append("{\\c&H0000D4FF&}" + t + "{\\c&H00FFFFFF&}" if j == i else t)
            txt = "{\\pos(%d,%d)\\fscx100\\fscy100}" % (W // 2, SUB_Y) + " ".join(parts)
            eventos.append([s, e, txt])
    eventos.sort(key=lambda x: x[0])
    # Nunca dos subtítulos a la vez: cada uno termina justo cuando arranca el siguiente
    # (y si el hueco es cortito, se estira para que no parpadee).
    for k in range(len(eventos) - 1):
        sig = eventos[k + 1][0]
        if eventos[k][1] > sig or sig - eventos[k][1] < 0.4:
            eventos[k][1] = sig
    lines = []
    for s, e, txt in eventos:
        s = max(s, start_at)
        if e - s < 0.02:
            continue
        lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Sub,,0,0,0,,{txt}")
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- lienzo y miniatura
def make_canvas(header, path, usuario=""):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 16], fill=ACCENT)
    fnt, lines = fit_text(d, header.upper(), W - 140, 2, 84, 52)
    lh = fnt.size * 1.12
    y = 190 - lh * len(lines) / 2 + 20
    for ln in lines:
        d.text((W // 2, y), ln, font=fnt, fill=DARK, anchor="ma")
        y += lh
    if usuario:
        d.text((W // 2, y + 8), usuario, font=mk.fuente("semibold", 34), fill=(110, 110, 110), anchor="ma")
    im.save(path)


def make_thumbnail(img_path, l1, l2, path):
    im = Image.new("RGB", (W, H), ACCENT)
    d = ImageDraw.Draw(im)
    # texto grande dentro del recorte 4:5 del perfil de Instagram (y 285..1635)
    fnt1, lines1 = fit_text(d, l1.upper(), W - 110, 2, 190, 90)
    y = 330
    for ln in lines1:
        d.text((W // 2, y), ln, font=fnt1, fill=DARK, anchor="ma",
               stroke_width=3, stroke_fill=DARK)
        y += fnt1.size * 1.02
    if l2:
        fnt2, lines2 = fit_text(d, l2.upper(), W - 200, 1, 130, 70)
        tw = d.textlength(lines2[0], font=fnt2)
        box_h = fnt2.size * 1.25
        y += 18
        d.rounded_rectangle([W / 2 - tw / 2 - 40, y, W / 2 + tw / 2 + 40, y + box_h], 24, fill=DARK)
        d.text((W // 2, y + box_h / 2), lines2[0], font=fnt2, fill=ACCENT, anchor="mm")
        y += box_h
    # imagen
    y = int(y + 50)
    size = min(900, 1600 - y)
    pic = Image.open(img_path).convert("RGB").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], 48, fill=255)
    shadow = Image.new("RGBA", (size + 60, size + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([30, 40, size + 30, size + 40], 48, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    x = (W - size) // 2
    im.paste(shadow, (x - 30, y - 30), shadow)
    frame = Image.new("RGB", (size + 16, size + 16), DARK)
    fmask = Image.new("L", frame.size, 0)
    ImageDraw.Draw(fmask).rounded_rectangle([0, 0, size + 16, size + 16], 56, fill=255)
    im.paste(frame, (x - 8, y - 8), fmask)
    im.paste(pic, (x, y), mask)
    im.save(path, "JPEG", quality=92)


# ---------------------------------------------------------------- video
def render_scene(canvas, img, dur, out, zoom_in):
    frames = max(1, round(dur * FPS))
    if zoom_in:
        z = f"1+0.10*on/{frames}"
    else:
        z = f"1.10-0.10*on/{frames}"
    flt = (f"[1:v]scale=1620:1620,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
           f":d={frames}:s={IMG_SIZE}x{IMG_SIZE}:fps={FPS}[z];"
           f"[0:v][z]overlay=0:{IMG_Y}:shortest=1,format=yuv420p[v]")
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(canvas),
         "-i", str(img), "-filter_complex", flt, "-map", "[v]", "-frames:v", str(frames),
         "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out)])


def render_still(img, dur, out):
    frames = max(1, round(dur * FPS))
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(img),
         "-vf", f"scale={W}:{H},format=yuv420p", "-frames:v", str(frames), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out)])


def main(spec_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    if isinstance(spec, str):
        spec = json.loads(spec)
    escenas = spec["escenas"]
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    seed = random.randint(1, 10_000_000)

    # 1) imágenes
    img_kinds = []
    for i, esc in enumerate(escenas):
        img_kinds.append(make_image(esc["prompt"], esc.get("pantalla") or esc["texto"], WORK / f"img{i}.png",
                                    seed + i, esc.get("emoji", "")))
    mini = spec.get("miniatura", {})
    thumb_src = WORK / "img_thumb.png"
    if mini.get("prompt"):
        make_image(mini["prompt"], "", thumb_src, seed + 999, mini.get("emoji", ""))
    else:
        thumb_src = WORK / "img0.png"

    # 2) miniatura + lienzo
    make_thumbnail(thumb_src, mini.get("linea1", spec["titulo"]), mini.get("linea2", ""), OUT / "thumb.jpg")
    make_canvas(spec.get("titulo_pantalla") or spec["titulo"], WORK / "canvas.png", spec.get("usuario", ""))

    # 3) voz por escena + tiempos
    all_words, seg_durs, t0 = [], [], 0.0
    for i, esc in enumerate(escenas):
        mp3 = WORK / f"voz{i}.mp3"
        dicho = texto_voz(esc["texto"])
        words = synth(dicho, mp3)
        words = align_words(dicho, words, duration(mp3))
        words, d = compactar(mp3, words, WORK / f"voz{i}.wav")
        for w in words:
            all_words.append([w[0] + t0, w[1] + t0, w[2]])
        seg = d + PAD
        seg_durs.append(seg)
        t0 += seg

    # 4) audio completo (con respiros)
    n = len(escenas)
    ins, flt = [], ""
    for i in range(n):
        ins += ["-i", str(WORK / f"voz{i}.wav")]
        flt += f"[{i}:a]aresample=44100,apad=pad_dur={PAD}[a{i}];"
    flt += "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", flt, "-map", "[out]", "-c:a", "pcm_s16le",
         str(WORK / "voz.wav")])

    # 5) segmentos de video
    segs = []
    render_still(OUT / "thumb.jpg", INTRO, WORK / "seg_intro.mp4")
    segs.append(WORK / "seg_intro.mp4")
    for i in range(n):
        d = seg_durs[i] - (INTRO if i == 0 else 0)
        render_scene(WORK / "canvas.png", WORK / f"img{i}.png", d, WORK / f"seg{i}.mp4", zoom_in=(i % 2 == 0))
        segs.append(WORK / f"seg{i}.mp4")
    (WORK / "lista.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in segs))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(WORK / "lista.txt"), "-c", "copy",
         str(WORK / "mudo.mp4")])

    # 6) subtítulos + mezcla final (música opcional en assets/music.mp3)
    build_ass(all_words, WORK / "subs.ass", start_at=INTRO)
    music = ROOT / "assets" / "music.mp3"
    cmd = ["ffmpeg", "-y", "-i", str(WORK / "mudo.mp4"), "-i", str(WORK / "voz.wav")]
    vf = f"ass={WORK / 'subs.ass'}:fontsdir={FONTS}"
    if music.exists():
        cmd += ["-stream_loop", "-1", "-i", str(music), "-filter_complex",
                f"[0:v]{vf}[v];[2:a]volume=0.07[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", vf, "-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT / "video.mp4")]
    run(cmd)

    meta = {"job_id": spec.get("job_id"), "duracion": round(duration(OUT / "video.mp4"), 2),
            "escenas": n, "imagenes": img_kinds, "voz": VOICE}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False))


def generar(contenido, serie_nombre, usuario, carpeta):
    """Arma video.mp4 y thumb.jpg en `carpeta` a partir del contenido escrito por la IA."""
    global OUT, WORK
    OUT = Path(carpeta)
    WORK = OUT / "_trabajo"
    spec = {
        "job_id": contenido.get("job_id"),
        "titulo": contenido["titulo"],
        "titulo_pantalla": serie_nombre,
        "usuario": usuario,
        "miniatura": contenido.get("miniatura", {}),
        "escenas": [{"texto": e["texto_voz"], "pantalla": e.get("texto_pantalla", ""),
                     "emoji": e.get("emoji", ""), "prompt": e.get("prompt", "")} for e in contenido["escenas"]],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    main(OUT / "spec.json")
    return OUT / "video.mp4", OUT / "thumb.jpg"


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "spec.json")
