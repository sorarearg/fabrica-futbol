"""Fotos reales de jugadores con licencia libre (Wikimedia Commons, vía la foto principal de su artículo
de Wikipedia). Solo se usan licencias que permiten uso comercial, y se guarda el crédito para la descripción."""
import re

import requests

from . import util

CABECERA = {"User-Agent": "fabrica-futbol/1.0 (https://github.com; bot educativo)"}
COMMONS = "https://commons.wikimedia.org/w/api.php"
_OK = re.compile(r"^(cc0|public domain|pd\b|pd-|cc[ -]by(-sa)?[ -]?\d|cc[ -]by(-sa)?$|attribution)", re.I)
_NO = re.compile(r"\b(nc|nd|non[- ]?commercial|no[- ]?deriv|fair use|non-free)\b", re.I)
_cache = {}


def _api(url, **params):
    params.update({"format": "json", "formatversion": 2})
    r = util.pedir("GET", url, params=params, headers=CABECERA, intentos=2, timeout=40)
    return r.json() if r is not None and r.status_code == 200 else {}


def _archivo_principal(nombre):
    for idioma in ("es", "en"):
        d = _api(f"https://{idioma}.wikipedia.org/w/api.php", action="query", titles=nombre, prop="pageimages",
                 piprop="name", redirects=1)
        paginas = (d.get("query") or {}).get("pages") or []
        if paginas and paginas[0].get("pageimage"):
            return paginas[0]["pageimage"]
        # si el título no coincide exacto, busca el artículo más parecido
        b = _api(f"https://{idioma}.wikipedia.org/w/api.php", action="query", list="search", srsearch=nombre, srlimit=1)
        hits = (b.get("query") or {}).get("search") or []
        if hits and hits[0]["title"] != nombre:
            d = _api(f"https://{idioma}.wikipedia.org/w/api.php", action="query", titles=hits[0]["title"],
                     prop="pageimages", piprop="name", redirects=1)
            paginas = (d.get("query") or {}).get("pages") or []
            if paginas and paginas[0].get("pageimage"):
                return paginas[0]["pageimage"]
    return None


def _limpio(html):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()
    # Commons a veces repite el nombre dos veces seguidas ("Fulano Fulano"): queda una sola
    mitad = len(t) // 2
    if t and len(t) % 2 == 0 and t[:mitad] == t[mitad:]:
        t = t[:mitad]
    m = re.match(r"^(.+?)\s+\1$", t)
    if m:
        t = m.group(1)
    if t.lower() in ("unknown author", "unknown", "autor desconocido", "desconocido"):
        t = "autor desconocido"
    return t


def _info(archivo):
    d = _api(COMMONS, action="query", titles="File:" + archivo if not archivo.startswith("File:") else archivo,
             prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=1280)
    paginas = (d.get("query") or {}).get("pages") or []
    return (paginas[0].get("imageinfo") or [{}])[0] if paginas else {}


def _licencia_ok(info):
    meta = info.get("extmetadata") or {}
    lic = _limpio((meta.get("LicenseShortName") or {}).get("value"))
    return lic, bool(_OK.search(lic) and not _NO.search(lic))


def _vertical_en_commons(nombre):
    """Busca en Commons otra foto de la misma persona en formato vertical (con licencia libre)."""
    apellido = nombre.split()[-1].lower()
    d = _api(COMMONS, action="query", list="search", srnamespace=6, srsearch=f'"{nombre}"', srlimit=15)
    for hit in (d.get("query") or {}).get("search") or []:
        titulo = hit["title"]
        if apellido not in titulo.lower() or not re.search(r"\.(jpe?g|png)$", titulo, re.I):
            continue
        info = _info(titulo)
        w, h = info.get("width", 0), info.get("height", 0)
        lic, ok = _licencia_ok(info)
        if ok and w >= 400 and h / max(w, 1) >= 1.2:
            return titulo.replace("File:", ""), info, lic
    return None


def foto(nombre, destino):
    """Baja la foto principal del artículo de Wikipedia de esa persona si su licencia es libre.
    Devuelve {"ruta", "credito"} o None."""
    nombre = (nombre or "").strip()
    if len(nombre) < 3:
        return None
    if nombre in _cache:
        return _cache[nombre]
    resultado = None
    try:
        archivo = _archivo_principal(nombre)
        # si la foto principal es horizontal, se prueba conseguir una vertical de la misma persona
        if archivo:
            inf = _info(archivo)
            if inf.get("width", 0) > inf.get("height", 1) * 1.05:
                try:
                    vert = _vertical_en_commons(nombre)
                    if vert:
                        util.log("Foto vertical de", nombre, ":", vert[0])
                        archivo = vert[0]
                except Exception as e:  # noqa
                    util.log("Búsqueda de foto vertical falló:", util.ocultar(e))
        if archivo:
            d = _api(COMMONS, action="query", titles="File:" + archivo, prop="imageinfo",
                     iiprop="url|extmetadata|size", iiurlwidth=1280)
            paginas = (d.get("query") or {}).get("pages") or []
            info = (paginas[0].get("imageinfo") or [{}])[0] if paginas else {}
            meta = info.get("extmetadata") or {}
            licencia = _limpio((meta.get("LicenseShortName") or {}).get("value"))
            autor = _limpio((meta.get("Artist") or {}).get("value"))[:80] or "autor desconocido"
            url = info.get("thumburl") or info.get("url")
            if url and _OK.search(licencia) and not _NO.search(licencia) and min(info.get("width", 0), info.get("height", 0)) >= 300:
                r = requests.get(url, headers=CABECERA, timeout=60)
                if r.status_code == 200 and len(r.content) > 8000:
                    destino.write_bytes(r.content)
                    resultado = {"ruta": destino, "credito": f"{autor} ({licencia}), Wikimedia Commons",
                                 "nombre": nombre}
                    util.log("Foto de", nombre, "·", licencia)
            elif url:
                util.log("Foto de", nombre, "descartada por licencia:", licencia or "?")
    except Exception as e:  # noqa
        util.log("No pude bajar la foto de", nombre, ":", util.ocultar(e))
    _cache[nombre] = resultado
    return resultado
