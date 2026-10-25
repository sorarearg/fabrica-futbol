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
                            temperatura=0.2, buscar=True)
        nuevas = [p for p in r.get("producciones", []) if isinstance(p, dict) and p.get("titulo")]
    except Exception as e:  # noqa
        util.log("No pude actualizar el catálogo de producciones:", util.ocultar(e))
        nuevas = []
    lista = datos.get("lista", [])
    vistos = {str(p.get("titulo", "")).lower() for p in lista}
    for p in nuevas:
        if str(p["titulo"]).lower() not in vistos:
            p["usos"] = 0
            lista.append(p)
            vistos.add(str(p["titulo"]).lower())
    datos = {"actualizado": hoy.isoformat() if nuevas or lista else None, "lista": lista}
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
