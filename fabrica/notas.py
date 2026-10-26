"""Material que le das vos a la fábrica, sin depender de la búsqueda de Gemini:
- data/notas.md: el buzón. Pegás links de notas (una por línea, con un comentario opcional) y la fábrica las usa.
- data/anecdotas.json: la reserva de anécdotas de series y películas, con el link de la nota de cada una.
Lo que ya se usó queda anotado en data/estado.json para no repetirlo."""
import html
import re

from . import util

CABECERA = {"User-Agent": "Mozilla/5.0 (fabrica-futbol; bot educativo)"}


def texto_de(url, maximo=9000):
    """Baja una nota y deja solo el texto de los párrafos."""
    try:
        r = util.pedir("GET", url, headers=CABECERA, intentos=2, timeout=40)
        if r is None or r.status_code != 200:
            return ""
        h = r.text
        h = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", h)
        titulo = re.search(r"(?is)<title[^>]*>(.*?)</title>", h)
        parrafos = re.findall(r"(?is)<p[^>]*>(.*?)</p>", h)
        limpio = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in parrafos]
        limpio = [re.sub(r"\s+", " ", p) for p in limpio if len(p) > 60]
        cuerpo = "\n".join(limpio)
        if len(cuerpo) < 300:
            return ""
        cab = html.unescape(re.sub(r"\s+", " ", titulo.group(1))).strip() if titulo else url
        return f"NOTA: {cab}\n{url}\n{cuerpo[:maximo]}"
    except Exception as e:  # noqa
        util.log("No pude leer la nota", url, ":", util.ocultar(e))
        return ""


def _usadas():
    return set(util.leer_json("data/estado.json", {}).get("notas_usadas", []))


def marcar_usada(clave):
    estado = util.leer_json("data/estado.json", {})
    lista = estado.setdefault("notas_usadas", [])
    if clave not in lista:
        lista.append(clave)
    estado["notas_usadas"] = lista[-500:]
    util.guardar_json("data/estado.json", estado)


def buzon():
    """Próxima nota del buzón sin usar: (url, comentario, texto) o None."""
    ruta = util.RAIZ / "data" / "notas.md"
    if not ruta.exists():
        return None
    usadas = _usadas()
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        m = re.search(r"https?://\S+", linea)
        if not m or linea.strip().startswith(("#", ">")):
            continue
        url = m.group(0).rstrip(").,")
        if url in usadas:
            continue
        comentario = linea.replace(m.group(0), "").strip(" -*:·")
        texto = texto_de(url)
        if texto:
            return url, comentario, texto
        marcar_usada(url)  # no se pudo leer: que no la vuelva a intentar cada día
        util.avisar("No pude leer una nota del buzón", f"{url} (probá con otro link de la misma noticia)")
    return None


def reserva():
    """Anécdotas sin usar de la reserva, agrupadas por la producción con más anécdotas pendientes.
    Devuelve (produccion, [anécdotas]) o None."""
    datos = util.leer_json("data/anecdotas.json", [])
    usadas = _usadas()
    libres = [a for a in datos if isinstance(a, dict) and a.get("anecdota") and a.get("id") not in usadas]
    if not libres:
        return None
    por_prod = {}
    for a in libres:
        por_prod.setdefault(a.get("produccion", "?"), []).append(a)
    prod = max(por_prod, key=lambda k: len(por_prod[k]))
    return prod, por_prod[prod]
