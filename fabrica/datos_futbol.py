"""Datos reales del fútbol de esta semana: football-data.org (plan gratis, 10 pedidos por minuto)
más una búsqueda de Gemini en Google para las ligas que football-data no cubre."""
import datetime as dt
import time

from . import util

API = "https://api.football-data.org/v4"
NOMBRES = {"PL": "Premier League", "PD": "LaLiga", "SA": "Serie A", "BL1": "Bundesliga", "FL1": "Ligue 1",
           "CL": "Champions League", "BSA": "Brasileirão", "PPL": "Liga de Portugal", "DED": "Eredivisie",
           "ELC": "Championship inglesa"}
LIGAS_CON_TABLA = ("PL", "PD", "SA", "BL1", "FL1", "BSA", "PPL", "DED")


class SinDatos(RuntimeError):
    pass


def _get(ruta, **params):
    clave = util.secreto("FOOTBALL_DATA_KEY")
    if not clave:
        raise SinDatos("Falta el secreto FOOTBALL_DATA_KEY")
    r = util.pedir("GET", API + ruta, params=params, headers={"X-Auth-Token": clave}, intentos=3, espera=20, timeout=60)
    time.sleep(6.5)  # el plan gratis permite 10 pedidos por minuto
    if r is None or r.status_code != 200:
        raise SinDatos(f"football-data {ruta}: {getattr(r, 'status_code', '?')} {(getattr(r, 'text', '') or '')[:160]}")
    return r.json()


def _equipo(t):
    return (t or {}).get("shortName") or (t or {}).get("name") or "?"


def _tablas(ligas):
    tablas = {}
    for c in ligas:
        if c not in LIGAS_CON_TABLA:
            continue
        try:
            d = _get(f"/competitions/{c}/standings")
            total = next((s for s in d.get("standings", []) if s.get("type") == "TOTAL"), None)
            if total:
                tablas[c] = total.get("table", [])
        except SinDatos as e:
            util.log("Sin tabla:", e)
    return tablas


def _goleadores(ligas, cuantos=10):
    goleadores = {}
    for c in ligas:
        if c not in LIGAS_CON_TABLA and c != "CL":
            continue
        try:
            goleadores[c] = _get(f"/competitions/{c}/scorers", limit=cuantos).get("scorers", [])
        except SinDatos as e:
            util.log("Sin goleadores:", e)
    return goleadores


def _texto_tabla(c, tabla, filas=6):
    lineas = [f'{f["position"]}. {_equipo(f["team"])} {f["points"]} pts ({f["playedGames"]} PJ, '
              f'{f.get("won", 0)}G {f.get("draw", 0)}E {f.get("lost", 0)}P'
              + (f', racha {f["form"]}' if f.get("form") else "") + ")" for f in tabla[:filas]]
    return f"TABLA {NOMBRES.get(c, c)} (primeros {filas}):\n" + "\n".join(lineas)


def _texto_goleadores(c, lista):
    lineas = []
    for g in lista[:8]:
        j = g.get("player") or {}
        marca = "  ← ARGENTINO" if (j.get("nationality") or "").lower() == "argentina" else ""
        lineas.append(f'{j.get("name", "?")} ({j.get("nationality", "?")}, {_equipo(g.get("team"))}): '
                      f'{g.get("goals", 0)} goles, {g.get("assists") or 0} asistencias, {g.get("playedMatches", "?")} PJ{marca}')
    return f"GOLEADORES {NOMBRES.get(c, c)}:\n" + "\n".join(lineas)


def _posicion(tablas, c, equipo_id):
    for f in tablas.get(c, []):
        if (f.get("team") or {}).get("id") == equipo_id:
            return f["position"], len(tablas[c])
    return None, None


def resumen(modo="finde"):
    """modo "finde": lo que pasó del viernes al lunes. modo "previa": lo que se viene y cómo llegan.
    Devuelve el texto con los datos (para Gemini) o levanta SinDatos."""
    cfg = util.config()
    ligas = cfg.get("ligas", list(NOMBRES))
    hoy = util.ahora().date()
    if modo == "finde":
        desde = hoy - dt.timedelta(days=(hoy.weekday() - 4) % 7 or 7)  # el viernes anterior
        hasta = hoy
        estado = "FINISHED"
    else:
        desde, hasta, estado = hoy, hoy + dt.timedelta(days=3), "SCHEDULED,TIMED"
    partidos = _get("/matches", competitions=",".join(ligas), dateFrom=desde.isoformat(),
                    dateTo=hasta.isoformat(), status=estado).get("matches", [])
    tablas = _tablas(ligas)
    goleadores = _goleadores(ligas)
    if not partidos and not tablas:
        raise SinDatos("football-data no devolvió partidos ni tablas")

    bloques, batacazos = [], []
    por_liga = {}
    for m in partidos:
        c = (m.get("competition") or {}).get("code", "?")
        por_liga.setdefault(c, []).append(m)
    for c, lista in por_liga.items():
        lineas = []
        for m in lista:
            loc, vis = _equipo(m.get("homeTeam")), _equipo(m.get("awayTeam"))
            if modo == "finde":
                ft = (m.get("score") or {}).get("fullTime") or {}
                gl, gv = ft.get("home"), ft.get("away")
                if gl is None:
                    continue
                lineas.append(f"{loc} {gl}-{gv} {vis}")
                if c in tablas and gl != gv:
                    gan, per = (m["homeTeam"], m["awayTeam"]) if gl > gv else (m["awayTeam"], m["homeTeam"])
                    pg, n = _posicion(tablas, c, gan.get("id"))
                    pp, _ = _posicion(tablas, c, per.get("id"))
                    if pg and pp and pg - pp >= max(7, n // 3):
                        batacazos.append(f"{NOMBRES.get(c, c)}: {_equipo(gan)} ({pg}°) le ganó {max(gl, gv)}-{min(gl, gv)} "
                                         f"a {_equipo(per)} ({pp}°)")
            else:
                lineas.append(f'{loc} vs {vis} ({(m.get("utcDate") or "")[:10]})')
        if lineas:
            bloques.append(f"PARTIDOS {NOMBRES.get(c, c)}:\n" + "\n".join(lineas[:20]))
    texto = []
    if batacazos:
        texto.append("POSIBLES BATACAZOS (ganó un equipo de mucho más abajo en la tabla):\n" + "\n".join(batacazos))
    argentinos = [f'{(g.get("player") or {}).get("name")} ({_equipo(g.get("team"))}, {NOMBRES.get(c, c)}): {g.get("goals")} goles'
                  for c, lista in goleadores.items() for g in lista
                  if ((g.get("player") or {}).get("nationality") or "").lower() == "argentina"]
    if argentinos:
        texto.append("ARGENTINOS ENTRE LOS GOLEADORES DE LAS LIGAS GRANDES:\n" + "\n".join(argentinos))
    texto += bloques
    texto += [_texto_tabla(c, t) for c, t in tablas.items()]
    texto += [_texto_goleadores(c, g) for c, g in goleadores.items() if g]
    cab = (f"DATOS DE football-data.org ({'del ' + desde.strftime('%d/%m') + ' al ' + hasta.strftime('%d/%m')})"
           if modo == "finde" else f"DATOS DE football-data.org (próximos partidos del {desde:%d/%m} al {hasta:%d/%m})")
    return cab + "\n\n" + "\n\n".join(texto)


def buscar_otras_ligas(modo="finde"):
    """Gemini busca en Google argentinos destacados y batacazos en ligas que football-data no cubre.
    Devuelve (texto, fuentes). Si la búsqueda falla, devuelve ("", [])."""
    from . import escritor
    hoy = util.ahora().date()
    desde = hoy - dt.timedelta(days=4)
    if modo == "finde":
        pedido = (f"Buscá en Google noticias deportivas publicadas entre el {desde:%d/%m/%Y} y el {hoy:%d/%m/%Y} sobre: "
                  "1) futbolistas argentinos que hicieron goles, fueron figura o salieron campeones este fin de semana en ligas "
                  "fuera de las cinco grandes de Europa (por ejemplo Estados Unidos, México, Japón, Corea, China, Arabia Saudita, "
                  "Turquía, Grecia, Chile, Uruguay, Paraguay, Colombia, Ecuador, Australia); 2) batacazos o rachas muy llamativas en "
                  "cualquier liga; 3) campeones definidos este fin de semana.")
    else:
        pedido = (f"Buscá en Google noticias deportivas publicadas entre el {desde:%d/%m/%Y} y el {hoy:%d/%m/%Y} sobre futbolistas "
                  "argentinos en racha en ligas fuera de las cinco grandes de Europa y finales o definiciones de campeonato de "
                  "este fin de semana en cualquier liga.")
    pedido += (" Incluí SOLO datos que aparezcan en las noticias, con el resultado y la fecha. Si no encontrás nada confirmado, "
               'devolvé la lista vacía. Respondé solo JSON: {"hallazgos": [{"dato": "...", "medio": "..."}]}')
    try:
        r = escritor.gemini("Sos un periodista deportivo argentino muy riguroso. Nunca inventás datos.", pedido,
                            temperatura=0.3, buscar=True)
        hallazgos = [h for h in r.get("hallazgos", []) if isinstance(h, dict) and h.get("dato")]
        fuentes = list(escritor.ULTIMAS_FUENTES)
        if not hallazgos:
            return "", []
        texto = "OTRAS LIGAS (búsqueda en Google de noticias del finde):\n" + "\n".join(
            f'- {h["dato"]} ({h.get("medio", "")})' for h in hallazgos[:10])
        util.log("Búsqueda en Google:", len(hallazgos), "hallazgos")
        return texto, fuentes
    except Exception as e:  # noqa
        util.log("La búsqueda en Google falló, sigo solo con football-data:", util.ocultar(e))
        return "", []
