"""Qué es tendencia hoy en el fútbol, para conectar cada video con lo que la gente está buscando.
Fuentes gratis: lo más leído de Wikipedia en español (sin clave), noticias del día vía Gemini con búsqueda
en Google (nivel gratuito) y, si está el secreto opcional YT_API_KEY, los videos de deportes en tendencia
en YouTube Argentina. Se calcula una vez por día y queda guardado en data/tendencias.json."""
import datetime as dt

from . import util

CABECERA = {"User-Agent": "fabrica-futbol/1.0 (https://github.com; bot educativo)"}


def _mas_leidos_wikipedia(fecha, cuantos=300):
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/es.wikipedia.org/all-access/"
           f"{fecha:%Y/%m/%d}")
    r = util.pedir("GET", url, headers=CABECERA, intentos=2, timeout=40)
    if r is None or r.status_code != 200:
        return []
    arts = ((r.json().get("items") or [{}])[0]).get("articles", [])
    fuera = ("Especial:", "Wikipedia:", "Portada", "Anexo:Episodios", "Archivo:", "Ayuda:")
    return [(a["article"].replace("_", " "), a.get("views", 0)) for a in arts[:cuantos]
            if not a["article"].startswith(fuera)]


def _youtube(clave):
    r = util.pedir("GET", "https://www.googleapis.com/youtube/v3/videos",
                   params={"part": "snippet", "chart": "mostPopular", "regionCode": "AR", "videoCategoryId": 17,
                           "maxResults": 25, "key": clave}, intentos=2, timeout=40)
    if r is None or r.status_code != 200:
        return []
    return [i["snippet"]["title"] for i in r.json().get("items", [])]


def hoy(cfg=None):
    """Devuelve el texto de tendencias de hoy (lo calcula una sola vez por día)."""
    from . import escritor
    guardadas = util.leer_json("data/tendencias.json", {})
    fecha = util.ahora().date()
    clave = fecha.isoformat()
    if clave in guardadas:
        return guardadas[clave].get("texto", "")
    partes = []
    # 1) Lo más leído de Wikipedia ayer, filtrado a fútbol por la IA
    try:
        leidos = _mas_leidos_wikipedia(fecha - dt.timedelta(days=1))
        if leidos:
            lista = "\n".join(f"{t} ({v} visitas)" for t, v in leidos)
            r = escritor.gemini("Sos un analista de tendencias de fútbol.",
                                "Estos son los artículos más leídos ayer en Wikipedia en español. Quedate SOLO con los "
                                "relacionados con el fútbol (jugadores, técnicos, clubes, torneos, partidos) y explicá en "
                                "pocas palabras por qué pueden estar en tendencia si lo sabés con seguridad (si no, dejalo "
                                'vacío). Respondé solo JSON: {"futbol": [{"articulo": "...", "visitas": 0, "por_que": "..."}]}'
                                "\n\n" + lista, temperatura=0.3)
            items = [x for x in r.get("futbol", []) if isinstance(x, dict) and x.get("articulo")][:15]
            if items:
                partes.append("LO MÁS BUSCADO DE FÚTBOL EN WIKIPEDIA (ayer):\n" + "\n".join(
                    f'- {x["articulo"]} ({x.get("visitas", "?")} visitas){": " + x["por_que"] if x.get("por_que") else ""}'
                    for x in items))
    except Exception as e:  # noqa
        util.log("Tendencias de Wikipedia fallaron:", util.ocultar(e))
    # 2) Noticias del día (Gemini busca en Google)
    try:
        r = escritor.gemini("Sos un periodista deportivo argentino muy riguroso. Nunca inventás datos.",
                            f"Buscá en Google las noticias de fútbol más comentadas en Argentina hoy ({fecha:%d/%m/%Y}) y "
                            "ayer: fútbol argentino (Liga Profesional, la Selección, el ascenso), argentinos en el exterior y "
                            "lo más viral del fútbol mundial. Solo temas que aparezcan en noticias de estos dos días. "
                            'Respondé solo JSON: {"temas": [{"tema": "...", "por_que": "..."}]}', temperatura=0.3, buscar=True)
        temas = [x for x in r.get("temas", []) if isinstance(x, dict) and x.get("tema")][:12]
        if temas:
            partes.append("LO MÁS COMENTADO HOY EN LAS NOTICIAS DE FÚTBOL:\n" + "\n".join(
                f'- {x["tema"]}{": " + x["por_que"] if x.get("por_que") else ""}' for x in temas))
    except Exception as e:  # noqa
        util.log("Tendencias de noticias fallaron:", util.ocultar(e))
    # 3) YouTube (opcional)
    clave_yt = util.secreto("YT_API_KEY")
    if clave_yt:
        try:
            titulos = _youtube(clave_yt)
            if titulos:
                partes.append("VIDEOS DE DEPORTES EN TENDENCIA EN YOUTUBE ARGENTINA (solo los títulos):\n" +
                              "\n".join("- " + t for t in titulos[:20]))
        except Exception as e:  # noqa
            util.log("Tendencias de YouTube fallaron:", util.ocultar(e))
    texto = "\n\n".join(partes)
    guardadas = {k: v for k, v in guardadas.items() if k >= (fecha - dt.timedelta(days=14)).isoformat()}
    guardadas[clave] = {"texto": texto}
    util.guardar_json("data/tendencias.json", guardadas)
    util.log("Tendencias de hoy:", f"{len(partes)} fuentes" if partes else "ninguna")
    return texto
