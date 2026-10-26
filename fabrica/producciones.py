"""Catálogo de series, películas y documentales de fútbol (Maradona, Messi, Tévez, Neymar, Pelé, Coppola...).
Se arma solo con Gemini + búsqueda en Google, se actualiza una vez por mes para sumar estrenos y queda en
data/producciones.json (y una lista legible en data/producciones.md). Podés agregar producciones a mano."""
import datetime as dt
import random

from . import util

ARCHIVO = "data/producciones.json"


def _guardar(datos):
    util.guardar_json(ARCHIVO, datos)
    lineas = ["# Series, películas y documentales de fútbol", "",
              "Lo arma la fábrica sola y lo actualiza una vez por mes. Para sumar una a mano, agregala en "
              "`data/producciones.json` con el mismo formato.", ""]
    for p in sorted(datos.get("lista", []), key=lambda x: (str(x.get("protagonista", "")), str(x.get("titulo", "")))):
        lineas.append(f'- **{p.get("titulo")}** ({p.get("plataforma", "?")}, {p.get("anio", "?")}) · '
                      f'{p.get("protagonista", "")} · usada {p.get("usos", 0)} veces')
    (util.RAIZ / "data" / "producciones.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


CATEGORIAS = [("es", "Categoría:Películas sobre fútbol"), ("es", "Categoría:Documentales sobre fútbol"),
              ("es", "Categoría:Series de televisión sobre fútbol"), ("es", "Categoría:Películas biográficas sobre deportistas"),
              ("en", "Category:Association football films"),
              ("en", "Category:Documentary films about association football"),
              ("en", "Category:Association football television series"),
              ("en", "Category:Documentary television series about association football")]


def _desde_wikipedia():
    """Títulos de las categorías de películas, series y documentales de fútbol de Wikipedia (gratis, sin clave)."""
    titulos = []
    for idioma, cat in CATEGORIAS:
        try:
            r = util.pedir("GET", f"https://{idioma}.wikipedia.org/w/api.php",
                           params={"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": "page",
                                   "cmlimit": 500, "format": "json", "formatversion": 2},
                           headers={"User-Agent": "fabrica-futbol/1.0 (bot educativo)"}, intentos=2, timeout=40)
            miembros = ((r.json().get("query") or {}).get("categorymembers") or []) if r is not None and r.status_code == 200 else []
            titulos += [f'{m["title"]} [{idioma}]' for m in miembros]
        except Exception as e:  # noqa
            util.log("Categoría de Wikipedia falló:", cat, util.ocultar(e))
    return titulos


def catalogo():
    """Devuelve el catálogo, actualizándolo si pasaron más de 30 días."""
    from . import escritor
    datos = util.leer_json(ARCHIVO, {})
    hoy = util.ahora().date()
    ultima = datos.get("actualizado")
    if ultima and (hoy - dt.date.fromisoformat(ultima)).days < 30 and datos.get("lista"):
        return datos
    conocidas = [p.get("titulo", "") for p in datos.get("lista", [])]
    pedido = (f"Hoy es {hoy:%d/%m/%Y}. Buscá en Google y armá la lista más completa posible de series, películas y "
              "documentales sobre fútbol y futbolistas con alcance en Argentina: biografías y documentales de leyendas "
              "argentinas y mundiales (Maradona, Messi, Tévez, Pelé, Neymar, Cristiano Ronaldo, Zidane, Ronaldinho, "
              "Batistuta, Riquelme, Bilardo, Menotti, la Selección en los Mundiales, Boca, River, clubes, representantes "
              "como Guillermo Coppola, etc.), de cualquier plataforma (Netflix, Prime Video, Disney+, Max, Star+, Apple TV, "
              "YouTube, cine o TV). Incluí también los estrenos recientes. Solo producciones que existan de verdad."
              + (("\nYa tengo estas (no las repitas): " + "; ".join(conocidas[:150])) if conocidas else "") +
              '\nRespondé solo JSON: {"producciones": [{"titulo": "...", "plataforma": "...", "anio": 2021, '
              '"protagonista": "...", "tipo": "serie|película|documental"}]}')
    try:
        r = escritor.gemini("Sos un especialista en cine y series de deportes. Nunca inventás títulos.", pedido,
                            temperatura=0.2, buscar=True, sin_busqueda_ok=True)
        nuevas = [p for p in r.get("producciones", []) if isinstance(p, dict) and p.get("titulo")]
    except Exception as e:  # noqa
        util.log("No pude actualizar el catálogo de producciones:", util.ocultar(e))
        nuevas = []
    # Wikipedia: categorías de películas, series y documentales de fútbol, filtradas por la IA (sin búsqueda)
    try:
        de_wiki = _desde_wikipedia()
        if de_wiki:
            r = escritor.gemini("Sos un especialista en cine y series de deportes. Nunca inventás títulos.",
                                "Estos son títulos de Wikipedia de películas, series y documentales de fútbol. Quedate SOLO "
                                "con los que tratan sobre futbolistas, técnicos, dirigentes, representantes, selecciones o "
                                "clubes REALES y que le pueden interesar a un futbolero argentino (leyendas argentinas y "
                                "mundiales, Mundiales, grandes clubes). Descartá ficción pura sin personas reales."
                                + (("\nYa tengo estas (no las repitas): " + "; ".join(conocidas[:150])) if conocidas else "") +
                                '\nRespondé solo JSON: {"producciones": [{"titulo": "...", "plataforma": "...", "anio": 2021, '
                                '"protagonista": "...", "tipo": "serie|película|documental", "wikipedia": "título exacto"}]}'
                                "\n\n" + "\n".join(de_wiki[:900]), temperatura=0.2)
            nuevas += [p for p in r.get("producciones", []) if isinstance(p, dict) and p.get("titulo")]
    except Exception as e:  # noqa
        util.log("No pude sumar el catálogo de Wikipedia:", util.ocultar(e))
    lista = datos.get("lista", [])
    vistos = {str(p.get("titulo", "")).lower() for p in lista}
    for p in nuevas:
        if str(p["titulo"]).lower() not in vistos:
            p["usos"] = 0
            lista.append(p)
            vistos.add(str(p["titulo"]).lower())
    sin_busqueda = escritor._BUSQUEDA.get("anda") is False
    fecha = (hoy - dt.timedelta(days=27)) if sin_busqueda else hoy  # sin búsqueda, vuelve a intentar en 3 días
    datos = {"actualizado": fecha.isoformat() if nuevas or lista else None, "lista": lista}
    _guardar(datos)
    util.log(f"Catálogo de producciones: {len(lista)} ({len(nuevas)} nuevas)")
    return datos


def elegir():
    """Una producción del catálogo: de las menos usadas, al azar."""
    lista = catalogo().get("lista", [])
    if not lista:
        return None
    menos = min(p.get("usos", 0) for p in lista)
    return random.choice([p for p in lista if p.get("usos", 0) == menos])


def sumar_uso(titulo):
    datos = util.leer_json(ARCHIVO, {})
    for p in datos.get("lista", []):
        if p.get("titulo") == titulo:
            p["usos"] = p.get("usos", 0) + 1
    _guardar(datos)
