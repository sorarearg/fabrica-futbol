"""Busca en Wikipedia (gratis, sin clave) el respaldo de cada historia, para que el guion
solo use hechos que están documentados."""
import re

from . import util

API = "https://{idioma}.wikipedia.org/w/api.php"
CABECERA = {"User-Agent": "fabrica-historias/1.0 (https://github.com; bot educativo)"}


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
