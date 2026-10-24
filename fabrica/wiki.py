"""Busca en Wikipedia (gratis, sin clave) el respaldo de cada historia, para que el guion
solo use hechos que están documentados."""
import re

from . import util

API = "https://{idioma}.wikipedia.org/w/api.php"
CABECERA = {"User-Agent": "fabrica-futbol/1.0 (https://github.com; bot educativo)"}


def _get(idioma, **params):
    params.update({"format": "json", "formatversion": 2})
    r = util.pedir("GET", API.format(idioma=idioma), params=params, headers=CABECERA, intentos=2, timeout=40)
    if r is None or r.status_code != 200:
        return {}
    try:
        return r.json()
    except Exception:  # noqa
        return {}


def buscar_titulo(consulta, idioma="es"):
    """Devuelve el título del artículo que mejor coincide con la consulta, o None."""
    consulta = re.sub(r"^wikipedia\s*:\s*", "", str(consulta or ""), flags=re.I).strip()
    if len(consulta) < 3:
        return None
    d = _get(idioma, action="query", list="search", srsearch=consulta, srlimit=1)
    hits = (d.get("query") or {}).get("search") or []
    return hits[0]["title"] if hits else None


def extracto(titulo, idioma="es", maximo=7000):
    """Texto plano del artículo (sin tablas ni referencias), recortado."""
    d = _get(idioma, action="query", prop="extracts|info", explaintext=1, exsectionformat="plain",
             inprop="url", titles=titulo, redirects=1)
    paginas = (d.get("query") or {}).get("pages") or []
    if not paginas or paginas[0].get("missing"):
        return None
    p = paginas[0]
    texto = re.sub(r"\n{3,}", "\n\n", p.get("extract") or "").strip()
    # se cortan las secciones finales que no aportan a la historia
    texto = re.split(r"\n\s*(Referencias|Bibliografía|Enlaces externos|Véase también|Notas)\s*\n", texto)[0]
    if len(texto) < 300:
        return None
    return {"titulo": p.get("title", titulo), "url": p.get("fullurl", ""), "texto": texto[:maximo]}


def material(consultas, maximo_total=12000):
    """Prueba cada consulta (en español y, si no aparece, en inglés) y junta los artículos encontrados."""
    juntados, vistos = [], set()
    for c in consultas or []:
        for idioma in ("es", "en"):
            try:
                t = buscar_titulo(c, idioma)
                if not t or t in vistos:
                    continue
                e = extracto(t, idioma, maximo=maximo_total // 2)
                if e:
                    vistos.add(t)
                    e["idioma"] = idioma
                    juntados.append(e)
                    break
            except Exception as ex:  # noqa
                util.log("Wikipedia falló:", util.ocultar(ex))
        if sum(len(x["texto"]) for x in juntados) >= maximo_total:
            break
    return juntados


def como_texto(articulos):
    return "\n\n".join(f'ARTÍCULO DE WIKIPEDIA ({a["idioma"]}): {a["titulo"]}\n{a["texto"]}' for a in articulos)


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
_FUTBOL = re.compile(r"f[úu]tbol|futbolista|gol(es)?\b|mundial|copa |selecci[óo]n|libertadores|campe[óo]n|"
                     r"club atl[ée]tico|boca juniors|river plate|independiente|racing|san lorenzo|estudiantes|"
                     r"gimnasia|newell|rosario central|v[ée]lez|hurac[áa]n|lan[úu]s|banfield|arquero|delantero|"
                     r"centrocampista|defensor|entrenador de f|footballer|football", re.I)


def efemerides(fecha):
    """Lo que pasó un día como hoy en el fútbol, según las páginas de Wikipedia del día (español e inglés)."""
    lineas = []
    paginas = [("es", f"{fecha.day} de {MESES[fecha.month - 1]}"),
               ("en", fecha.strftime("%B ") + str(fecha.day))]
    for idioma, titulo in paginas:
        e = extracto(titulo, idioma, maximo=60000)
        if not e:
            continue
        seccion = ""
        for ln in e["texto"].splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if len(ln) < 40 and not re.match(r"^\d", ln):
                seccion = ln
                continue
            if _FUTBOL.search(ln) and re.match(r"^\d{3,4}", ln):
                lineas.append(f"[{idioma} · {seccion}] {ln[:220]}")
    return lineas[:80]
