"""Punto de entrada: python -m fabrica.main generar | publicar --base-url URL | reporte"""
import argparse
import html
import json
import os
import shutil
import sys

from . import util

SALIDA = util.RAIZ / "out"
SITIO = SALIDA / "sitio"


def _series_del_dia(cfg):
    """Series a probar hoy, en orden. Si el día tiene una lista, rota: primero la que hace más que no sale.
    Al final van las de respaldo, por si ninguna tiene una idea buena."""
    forzada = (os.getenv("SERIE") or "").strip().lower()
    if forzada in cfg["series"]:
        return [forzada]
    del_dia = cfg["plan_semanal"][str(util.ahora().isoweekday())]
    lista = del_dia if isinstance(del_dia, list) else [del_dia]
    historial = util.leer_json("data/historial.json", [])
    ultima = {}
    for i, h in enumerate(historial):
        ultima[h.get("serie")] = i
    lista = sorted(lista, key=lambda k: ultima.get(k, -1))
    # las prioritarias (por ejemplo, anécdotas de series en tendencia) van primero si no salieron hace poco
    import datetime as _dt
    hoy = util.ahora().date()
    for k, dias in (cfg.get("prioritarias") or {}).items():
        if k in lista:
            fechas = [h.get("fecha", "") for h in historial if h.get("serie") == k]
            reciente = any(f and (hoy - _dt.date.fromisoformat(f)).days < int(dias) for f in fechas)
            lista.remove(k)
            if reciente:
                lista.append(k)
            else:
                lista.insert(0, k)
    for r in cfg.get("series_respaldo", []):
        if r not in lista and r in cfg["series"]:
            lista.append(r)
    return [k for k in lista if k in cfg["series"]]


def _serie_del_dia(cfg):
    return _series_del_dia(cfg)[0]


def _escribir_con_respaldo(cfg, escritor, fuentes, titulos, tema):
    """Prueba las series del día en orden; si una no tiene ideas buenas, avisa y pasa a la siguiente."""
    avisos = []
    for clave in _series_del_dia(cfg):
        serie = cfg["series"][clave]
        util.log("Serie:", serie["nombre"])
        try:
            contenido = escritor.escribir(serie, fuentes, titulos, tema)
            if avisos:
                util.avisar_mail("La fábrica cambió de serie por falta de ideas buenas",
                            "\n".join(avisos) + f"\n\nSalió en su lugar: {serie['nombre']}.")
            return clave, serie, contenido
        except escritor.SinIdeas as e:
            avisos.append(str(e))
            util.log("Sin ideas buenas:", e)
            if tema:
                break
    util.avisar_mail("La fábrica no encontró ninguna idea buena hoy", "\n".join(avisos))
    raise RuntimeError("Ninguna serie tuvo una idea con el puntaje mínimo: " + " | ".join(avisos))


def _fecha_tapa(contenido):
    """Fecha para la tapa del diario: la de hoy en actualidad; si no, el año de la historia si aparece en el texto."""
    import re as _re
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]
    hoy = util.ahora()
    if contenido.get("datos_futbol"):
        return f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"
    texto = " ".join([contenido.get("tema", ""), contenido["escenas"][0].get("texto_pantalla", "")])
    m = _re.search(r"\b(18|19|20)\d{2}\b", texto)
    return f"Año {m.group(0)}" if m else ""


def generar(simulado=False):
    cfg = util.config()
    os.environ.setdefault("TTS_VOICE", cfg.get("voz", "es-AR-TomasNeural"))
    os.environ.setdefault("TTS_RATE", str(cfg.get("voz_velocidad", "+15%")))
    os.environ.setdefault("TTS_MAX_PAUSA", str(cfg.get("voz_pausa_maxima", 0.28)))
    from . import carrusel, escritor, investigar, montaje  # importa después de fijar la voz

    efe = ped = None
    if os.getenv("MODO") == "pedido":
        ped = _pedido_pendiente(cfg)
        if not ped:
            util.log("No hay pedidos programados para fabricar ahora.")
            return
        os.environ["SERIE"] = ped.get("serie") or "especial"
        os.environ["TEMA"] = ped["tema"]
        _marcar_pedido(ped["id"], "intento")
    elif os.getenv("MODO") == "efemeride":
        efe = _efemeride_pendiente(cfg)
        if not efe:
            util.log("No hay efemérides pendientes para publicar ahora.")
            return
        os.environ["SERIE"] = "undia"
        os.environ["TEMA"] = efe["tema"]
    elif not simulado:
        _sumar_intento()
    clave_serie = _serie_del_dia(cfg)
    serie = cfg["series"][clave_serie]
    fecha = util.ahora().strftime("%Y-%m-%d")

    historial = util.leer_json("data/historial.json", [])
    usados = {f for h in historial for f in h.get("fuentes", [])}
    titulos = [h["titulo"] for h in reversed(historial)]

    fuentes = []
    clave_yt = util.secreto("YT_API_KEY")
    if clave_yt and serie.get("canales") and not simulado:
        try:
            fuentes = investigar.fuera_de_serie(serie["canales"], clave_yt, usados, cfg.get("fuentes_por_video", 2))
            util.log("Videos de referencia:", [f'{f["canal"]}: {f["titulo"]} (x{f["score"]})' for f in fuentes])
        except Exception as e:  # noqa
            util.log("La investigación en YouTube falló, sigo sin referencias:", e)

    if simulado:
        contenido = escritor.validar(json.loads((util.RAIZ / "data" / "ejemplo_contenido.json").read_text(encoding="utf-8")))
        contenido["wikipedia"] = [{"titulo": "Branco", "url": "https://es.wikipedia.org/wiki/Branco",
                                   "idioma": "es"}]
    else:
        clave_serie, serie, contenido = _escribir_con_respaldo(cfg, escritor, fuentes, titulos,
                                                               (os.getenv("TEMA") or "").strip() or None)
    contenido["fecha_tapa"] = _fecha_tapa(contenido)
    contenido["serie_clave"] = clave_serie

    nombre_carpeta = fecha + (f"-efe{efe['n']}" if efe else "") + (f"-ped{ped['n']}" if ped else "")
    carpeta = SITIO / nombre_carpeta
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    carpeta.mkdir(parents=True)
    placas = []
    if contenido.get("carrusel") and cfg.get("carrusel_dias"):
        placas = carrusel.generar(contenido, serie["nombre"], cfg["usuario"], carpeta)
    video_path, thumb_path = montaje.generar(contenido, serie["nombre"], cfg["usuario"], carpeta)
    shutil.rmtree(carpeta / "_trabajo", ignore_errors=True)
    (carpeta / "spec.json").unlink(missing_ok=True)
    meta_video = util.leer_json(str((carpeta / "meta.json").relative_to(util.RAIZ)), {}) or {}
    (carpeta / "meta.json").unlink(missing_ok=True)
    (SITIO / "index.html").write_text("<meta charset='utf-8'><p>Fábrica de fútbol</p>", encoding="utf-8")

    firma = _firma(cfg, contenido, meta_video)
    tags = " ".join(contenido["hashtags"])
    publicacion = {
        "fecha": fecha,
        "serie": clave_serie,
        "serie_nombre": serie["nombre"],
        "titulo": contenido["titulo"],
        "caption": f'{contenido["titulo"]}\n\n{contenido["descripcion"]}\n\n{firma}\n\n{tags}'.strip(),
        "descripcion_youtube": f'{contenido["descripcion"]}\n\n{firma}\n\n{tags} #shorts'.strip(),
        "tags": [t.lstrip("#") for t in contenido["hashtags"]],
        "guion": " ".join(e["texto_voz"] for e in contenido["escenas"]),
        "fuentes": [f["id"] for f in fuentes],
        "fuentes_detalle": [{"canal": f["canal"], "titulo": f["titulo"], "score": f.get("score") or f.get("pais", "")}
                            for f in fuentes],
        "archivos": {"video": f"{nombre_carpeta}/video.mp4", "portada": f"{nombre_carpeta}/thumb.jpg",
                     "placas": [f"{nombre_carpeta}/{p.name}" for p in placas]},
        "extra": bool(efe) or bool(ped and not ped.get("en_lugar_del_del_dia")),
        "efemeride_n": efe["n"] if efe else None,
        "pedido_id": ped["id"] if ped else None,
        "contenido": contenido,
        "video": meta_video,
    }
    util.guardar_json("out/publicacion.json", publicacion)
    util.log("Listo:", contenido["titulo"])


def _firma(cfg, contenido, meta_video):
    lineas = [cfg.get("firma", "")]
    if contenido.get("datos_futbol"):
        lineas.append("Datos: football-data.org.")
    wiki = contenido.get("wikipedia") or []
    if wiki:
        lineas.append("Fuente: Wikipedia (" + ", ".join(w["titulo"] for w in wiki) + ").")
    creditos = meta_video.get("creditos") or []
    if creditos:
        lineas.append("Fotos: " + "; ".join(creditos) + ".")
    return "\n".join(x for x in lineas if x)


def publicar(base_url):
    from . import publicar as pub
    cfg = util.config()
    p = util.leer_json("out/publicacion.json")
    base = base_url.rstrip("/") + "/"
    url = lambda rel: base + rel  # noqa
    video_local = SITIO / p["archivos"]["video"]
    hoy_carrusel = util.ahora().isoweekday() in cfg.get("carrusel_dias", [])
    quiere = cfg.get("publicar", {})
    resultados = {}

    def intentar(nombre, fn):
        try:
            resultados[nombre] = {"ok": True, "id": fn()}
        except Exception as e:  # noqa
            resultados[nombre] = {"ok": False, "error": str(e)[:300]}
        util.log(nombre, resultados[nombre])

    if quiere.get("instagram_reel"):
        intentar("instagram_reel", lambda: pub.instagram_reel(url(p["archivos"]["video"]),
                                                              url(p["archivos"]["portada"]), p["caption"]))
    if quiere.get("instagram_carrusel") and hoy_carrusel:
        intentar("instagram_carrusel", lambda: pub.instagram_carrusel([url(x) for x in p["archivos"]["placas"]],
                                                                      p["caption"]))
    if quiere.get("youtube"):
        intentar("youtube", lambda: pub.youtube(video_local, p["titulo"], p["descripcion_youtube"], p["tags"],
                                                cfg.get("youtube_privacidad", "public")))
    if quiere.get("tiktok"):
        intentar("tiktok", lambda: pub.tiktok(video_local, p["caption"], cfg.get("tiktok_privacidad", "SELF_ONLY")))
    if quiere.get("facebook"):
        intentar("facebook", lambda: pub.facebook_reel(video_local, p["caption"], p["titulo"]))

    historial = util.leer_json("data/historial.json", [])
    historial.append({"fecha": p["fecha"], "hora": util.ahora().strftime("%H:%M"), "serie": p["serie"],
                      "titulo": p["titulo"], "fuentes": p["fuentes"], "resultados": resultados,
                      "extra": p.get("extra", False)})
    util.guardar_json("data/historial.json", historial[-400:])
    if p.get("efemeride_n") is not None:
        _marcar_efemeride(p["fecha"], p["efemeride_n"], "publicada")
    if p.get("pedido_id"):
        _marcar_pedido(p["pedido_id"], "publicado")
    _registro(p, resultados, base)
    _mail_diario(p, resultados, base)
    resumen(base_url, resultados)

    if resultados and not any(r["ok"] for r in resultados.values()):
        util.log("No se pudo publicar en ninguna red")
        sys.exit(1)


def resumen(base_url, res=None):
    """Escribe el resumen visible en la pestaña Actions de GitHub (con las placas a la vista)."""
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    p = util.leer_json("out/publicacion.json")
    if not (destino and p):
        return
    base = base_url.rstrip("/") + "/"
    md = [f'## {p["serie_nombre"]}: {p["titulo"]}', ""]
    for red, r in (res or {}).items():
        md.append(f'- **{red}**: ' + ("✅ publicado" if r["ok"] else "❌ " + r["error"]))
    v = p.get("video") or {}
    if v:
        md += [f'Voz: {v.get("voz", "?")} · {v.get("duracion", "?")} s · fondos: {v.get("clips_stock", 0)} de '
               f'{v.get("clips", 0)} clips de {v.get("banco") or "stock"}, {v.get("clips_propios", 0)} propios, '
               f'{v.get("postales", 0)} postales de Argentina · música: {v.get("musica") or "no"}', ""]
    md += ["", f'[▶️ Ver el video]({base}{p["archivos"]["video"]}) · [Portada]({base}{p["archivos"]["portada"]})', ""]
    md += [" ".join(f'<img src="{base}{x}" width="180">' for x in p["archivos"]["placas"]), ""]
    md += ["**Texto para publicar:**", "", "```", p["caption"], "```", "", "**Guion:** " + p["guion"]]
    with open(destino, "a", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def _registro(p, res, base):
    lineas = [f'# {p["fecha"]} · {p["serie_nombre"]}', "", f'**{p["titulo"]}**', ""]
    for red, r in res.items():
        lineas.append(f'- {red}: ' + ("publicado (" + str(r["id"]) + ")" if r["ok"] else "ERROR: " + r["error"]))
    lineas += ["", "Basado en: " + ("; ".join(f'{f["canal"]} - {f["titulo"]} (x{f["score"]})'
                                              for f in p["fuentes_detalle"]) or "tema propio"),
               "", "## Texto", "", p["caption"], "", "## Guion", "", p["guion"]]
    ruta = util.RAIZ / "publicaciones" / f'{p["fecha"]}.md'
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _mail_diario(p, res, base):
    from . import publicar as pub
    e = html.escape
    filas = "".join(
        f'<li><b>{e(red)}</b>: {"✅ publicado" if r["ok"] else "❌ " + e(r["error"])}</li>' for red, r in res.items())
    estado = util.leer_json("data/estado.json", {})
    aviso = f'<p style="color:#b00">⚠️ {e(estado["ig_aviso"])}</p>' if estado.get("ig_aviso") else ""
    cuerpo = (f'<h2>{e(p["serie_nombre"])}: {e(p["titulo"])}</h2><ul>{filas}</ul>{aviso}'
              f'<p><a href="{base}{p["archivos"]["video"]}">Video</a> · '
              f'<a href="{base}{p["archivos"]["portada"]}">Portada</a> · '
              + (f' · <a href="{base}{p["archivos"]["placas"][0]}">Carrusel</a>' if p["archivos"]["placas"] else "")
              + ' (los links duran hasta mañana)</p>'
              f'<p><b>Texto:</b><br>{e(p["caption"]).replace(chr(10), "<br>")}</p>'
              f'<hr><p style="color:#666">{e(p["guion"])}</p>')
    try:
        pub.mail(f'Short del día: {p["titulo"]}', cuerpo)
    except Exception as ex:  # noqa
        util.log("No pude mandar el mail:", ex)


def _rendimiento(cfg, clave_yt, dias=30):
    """Cómo le fue a cada serie nuestra en los últimos días (YouTube + Instagram)."""
    from . import investigar
    from . import publicar as pub
    hist = util.leer_json("data/historial.json", [])
    desde = (util.ahora() - util.timedelta(days=dias)).strftime("%Y-%m-%d")
    recientes = [h for h in hist if h.get("fecha", "") >= desde]
    yt_ids = [h["resultados"]["youtube"]["id"] for h in recientes
              if h.get("resultados", {}).get("youtube", {}).get("ok")]
    yt = investigar.estadisticas_youtube(yt_ids, clave_yt) if (clave_yt and yt_ids) else {}
    filas = []
    for h in recientes:
        res = h.get("resultados", {})
        fila = {"fecha": h["fecha"], "hora": h.get("hora", ""), "serie": h["serie"], "titulo": h["titulo"],
                "vistas": 0, "guardados": 0, "compartidos": 0, "comentarios": 0, "likes": 0}
        if res.get("youtube", {}).get("ok"):
            m = yt.get(res["youtube"]["id"], {})
            fila["vistas"] += m.get("vistas", 0)
            fila["likes"] += m.get("likes", 0)
            fila["comentarios"] += m.get("comentarios", 0)
        for red in ("instagram_reel", "instagram_carrusel"):
            if res.get(red, {}).get("ok"):
                m = pub.instagram_metricas(res[red]["id"])
                fila["vistas"] += m.get("views", m.get("reach", 0))
                fila["guardados"] += m.get("saved", 0)
                fila["compartidos"] += m.get("shares", 0)
                fila["comentarios"] += m.get("comments", 0)
                fila["likes"] += m.get("likes", 0)
        filas.append(fila)
    por_serie = {}
    for f in filas:
        nombre = cfg["series"].get(f["serie"], {}).get("nombre", f["serie"])
        a = por_serie.setdefault(nombre, {"posts": 0, "vistas": 0, "guardados": 0, "compartidos": 0,
                                          "comentarios": 0})
        a["posts"] += 1
        for k in ("vistas", "guardados", "compartidos", "comentarios"):
            a[k] += f[k]
    return filas, por_serie


# ---------------------------------------------------------------- muestra corta
def muestra():
    """Escribe el guion completo, arma la portada y solo los primeros segundos del video, sin publicar."""
    import subprocess
    cfg = util.config()
    os.environ.setdefault("TTS_VOICE", cfg.get("voz", "es-AR-TomasNeural"))
    os.environ.setdefault("TTS_RATE", str(cfg.get("voz_velocidad", "+10%")))
    os.environ.setdefault("TTS_MAX_PAUSA", str(cfg.get("voz_pausa_maxima", 0.32)))
    from . import escritor, montaje
    tema = (os.getenv("TEMA") or "").strip() or None
    segundos = float(os.getenv("SEGUNDOS") or 12)
    util.log("Muestra · tema:", tema or "lo elige la IA")
    titulos = [h["titulo"] for h in reversed(util.leer_json("data/historial.json", []))]
    clave_serie, serie, contenido = _escribir_con_respaldo(cfg, escritor, [], titulos, tema)
    contenido["fecha_tapa"] = _fecha_tapa(contenido)
    contenido["serie_clave"] = clave_serie
    carpeta = SALIDA / "muestra"
    shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True)
    montaje.generar(contenido, serie["nombre"], cfg.get("usuario", ""), carpeta, segundos_max=segundos)
    meta = json.loads((carpeta / "meta.json").read_text(encoding="utf-8"))
    (carpeta / "meta.json").unlink()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(carpeta / "video.mp4"), "-vf",
                    "fps=10,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse",
                    str(carpeta / "muestra.gif")], check=False)
    tope = int(cfg.get("titulo_max", 40))
    md = [f'# Muestra · {serie["nombre"]}', "",
          f'**Idea elegida:** {contenido.get("tema", "")} (puntaje {contenido.get("puntaje", "?")})', "",
          f'**Título:** {contenido["titulo"]} ({len(contenido["titulo"])} de {tope} caracteres)', "",
          f'**Duración del video completo:** {meta["voz_seg"]:.0f} segundos · {contenido["palabras"]} palabras · '
          f'{len(contenido["escenas"])} escenas', "",
          f'**Esta muestra:** primeros {meta["duracion"]:.0f} segundos · voz: {meta["voz"]} · '
          f'imágenes: {", ".join(f"{k} ({v})" for k, v in (meta.get("imagenes") or {}).items()) or "?"}', "",
          "![Muestra](muestra.gif) ![Portada](thumb.jpg)", "",
          "[▶️ Ver los segundos de video con sonido](video.mp4)", "", "## Guion completo", ""]
    md += [f'{i}. {e["texto_voz"]}' for i, e in enumerate(contenido["escenas"], 1)]
    md += ["", "## Texto para publicar", "", contenido["descripcion"], "", " ".join(contenido["hashtags"]), "",
           "## De dónde salen los datos", ""]
    md += [f'- [{w["titulo"]}]({w["url"]})' for w in contenido.get("wikipedia") or []] or ["- (sin artículo de Wikipedia)"]
    md += [f"- {x}" for x in contenido.get("fuentes") or []]
    md += [f'- [{w.get("titulo") or "noticia"}]({w["url"]})' for w in contenido.get("web") or [] if w.get("url")]
    if meta.get("creditos"):
        md += ["", "## Fotos", ""] + [f"- {c}" for c in meta["creditos"]]
    if contenido.get("veredicto"):
        md.insert(4, f'**Veredicto:** {contenido["veredicto"]}')
        md.insert(5, "")
    (carpeta / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    util.guardar_json("out/muestra/contenido.json", contenido)
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    if destino:
        repo, rama = os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GITHUB_REF_NAME", "main")
        base = f"https://github.com/{repo}/blob/{rama}/muestras/ultima/"
        resumen_md = "\n".join(md).replace("](muestra.gif)", f"]({base}muestra.gif?raw=true)") \
            .replace("](thumb.jpg)", f"]({base}thumb.jpg?raw=true)").replace("](video.mp4)", f"]({base}video.mp4)")
        with open(destino, "a", encoding="utf-8") as f:
            f.write(resumen_md + "\n")
    util.log("Muestra lista:", contenido["titulo"])


# ---------------------------------------------------------------- horarios
VENTANA = (30, 60)  # se arranca entre 60 y 30 minutos antes del horario (el reloj corre cada 30 min)
TARDE_MAX = 180     # si el reloj de GitHub se atrasa, publica igual hasta 3 horas después del horario
INTENTOS_MAX = 2    # si falla, lo reintenta una vez más ese día (no más, para no llenarte de avisos)


def _intentos(fecha):
    return int((util.leer_json("data/estado.json", {}).get("intentos") or {}).get(fecha, 0))


def _sumar_intento():
    """Anota que el reloj arrancó a fabricar hoy (se guarda aunque la corrida falle)."""
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return
    estado = util.leer_json("data/estado.json", {})
    hoy = util.ahora().strftime("%Y-%m-%d")
    intentos = {k: v for k, v in (estado.get("intentos") or {}).items() if k >= hoy}  # solo el de hoy
    intentos[hoy] = intentos.get(hoy, 0) + 1
    estado["intentos"] = intentos
    util.guardar_json("data/estado.json", estado)


def _objetivo(cfg, momento=None):
    momento = momento or util.ahora()
    h = (cfg.get("horarios") or {}).get(str(momento.isoweekday()))
    if not h:
        return None
    hh, mm = (int(x) for x in str(h).split(":")[:2])
    return momento.replace(hour=hh, minute=mm, second=0, microsecond=0)


def toca():
    """Lo usa el reloj de GitHub cada 30 minutos: ¿hay que fabricar y publicar ahora?"""
    cfg = util.config()
    si, motivo = True, "ejecución manual"
    if os.getenv("GITHUB_EVENT_NAME") == "schedule":
        ahora = util.ahora()
        objetivo = _objetivo(cfg, ahora)
        hoy = ahora.strftime("%Y-%m-%d")
        if not cfg.get("fabrica_activa", True):
            si, motivo = False, "la fábrica está apagada (config.json → fabrica_activa: false)"
        elif any(x.get("en_lugar_del_del_dia") for x in _pedidos_de(hoy)):
            si, motivo = False, "hoy sale un pedido programado en lugar del video de la grilla"
        elif objetivo is None:
            si, motivo = False, "hoy no tiene horario"
        elif any(h.get("fecha") == hoy and not h.get("extra") for h in util.leer_json("data/historial.json", [])):
            si, motivo = False, "hoy ya se publicó"
        elif _intentos(hoy) >= INTENTOS_MAX:
            si, motivo = False, f"hoy ya se intentó {INTENTOS_MAX} veces y falló; mañana sigue normal"
        else:
            faltan = (objetivo - ahora).total_seconds() / 60
            if VENTANA[0] <= faltan < VENTANA[1]:
                si, motivo = True, f"faltan {faltan:.0f} minutos para las {objetivo:%H:%M}"
            elif -TARDE_MAX <= faltan <= 0:
                si = True
                motivo = (f"ya pasaron {-faltan:.0f} minutos de las {objetivo:%H:%M} y hoy no salió nada "
                          f"(el reloj se atrasó o falló): publico apenas esté listo")
            else:
                si, motivo = False, f"faltan {faltan:.0f} minutos para las {objetivo:%H:%M}"
    util.log("¿Toca publicar?", "sí" if si else "no", "·", motivo)
    salida = os.getenv("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"si={'true' if si else 'false'}\n")


# ---------------------------------------------------------------- pedidos programados
def _pedidos_de(fecha_iso):
    """Pedidos del archivo data/pedidos.json para una fecha (acepta uno solo o una lista)."""
    datos = util.leer_json("data/pedidos.json", {})
    lista = datos.get(fecha_iso) or []
    if isinstance(lista, dict):
        lista = [lista]
    salida = []
    for n, x in enumerate(lista, 1):
        if isinstance(x, dict) and str(x.get("tema", "")).strip():
            x = dict(x)
            x["n"], x["id"], x["fecha"] = n, f"{fecha_iso}#{n}", fecha_iso
            salida.append(x)
    return salida


def _estado_pedidos():
    return util.leer_json("data/estado.json", {}).get("pedidos", {})


def _marcar_pedido(pid, que):
    estado = util.leer_json("data/estado.json", {})
    ped = estado.setdefault("pedidos", {})
    actual = ped.setdefault(pid, {"intentos": 0, "estado": "pendiente"})
    if que == "intento":
        actual["intentos"] += 1
    else:
        actual["estado"] = que
    # solo se guardan los de los últimos 30 días
    import datetime as _dt
    limite = (util.ahora().date() - _dt.timedelta(days=30)).isoformat()
    estado["pedidos"] = {k: v for k, v in ped.items() if k[:10] >= limite}
    util.guardar_json("data/estado.json", estado)


def _hora_pedido(ped, ahora):
    hh, mm = (int(x) for x in str(ped.get("hora") or "19:00").split(":")[:2])
    return ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _pedido_listo(ahora):
    """El pedido de hoy que hay que fabricar ahora: desde 50 minutos antes de su hora y hasta 3 horas después."""
    est = _estado_pedidos()
    for ped in _pedidos_de(ahora.date().isoformat()):
        e = est.get(ped["id"], {})
        if e.get("estado") == "publicado" or e.get("intentos", 0) >= 2:
            continue
        faltan = (_hora_pedido(ped, ahora) - ahora).total_seconds() / 60
        if -TARDE_MAX <= faltan <= 50:
            return ped
    return None


def _pedido_pendiente(cfg):
    return _pedido_listo(util.ahora()) if os.getenv("GITHUB_EVENT_NAME") == "schedule" else \
        next((p for p in _pedidos_de(util.ahora().date().isoformat())
              if _estado_pedidos().get(p["id"], {}).get("estado") != "publicado"), None)


def esperar_pedido():
    """Con el video del pedido listo, espera a su hora exacta antes de publicar."""
    import time
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return
    p = util.leer_json("out/publicacion.json", {})
    if not p.get("pedido_id"):
        return
    ped = next((x for x in _pedidos_de(p["pedido_id"][:10]) if x["id"] == p["pedido_id"]), None)
    if not ped:
        return
    segundos = (_hora_pedido(ped, util.ahora()) - util.ahora()).total_seconds()
    if 0 < segundos < 70 * 60:
        util.log(f"Pedido listo. Espero {segundos / 60:.0f} minutos para publicarlo a las {ped.get('hora')}.")
        time.sleep(segundos)


def toca_extra():
    """Reloj de los videos extra: primero los pedidos programados (data/pedidos.json), después las efemérides."""
    cfg = util.config()
    salida = os.getenv("GITHUB_OUTPUT")
    modo, motivo = "", ""
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        modo = (os.getenv("MODO_MANUAL") or "pedido").strip()
        motivo = "ejecución manual"
    elif not cfg.get("fabrica_activa", True):
        motivo = "la fábrica está apagada (config.json → fabrica_activa: false)"
    else:
        ped = _pedido_listo(util.ahora())
        if ped:
            modo, motivo = "pedido", f'pedido programado: {ped["tema"]} ({ped.get("hora", "19:00")})'
    if not modo and os.getenv("GITHUB_EVENT_NAME") == "schedule" and cfg.get("fabrica_activa", True):
        si = _toca_efemeride_si(cfg)
        modo, motivo = ("efemeride", si) if si.startswith("toca") else ("", si)
    util.log("¿Toca un video extra?", modo or "no", "·", motivo)
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"si={'true' if modo else 'false'}\nmodo={modo}\n")


# ---------------------------------------------------------------- efemérides (videos extra)
def _ranking_dia(cfg, fecha):
    """Ranking de las efemérides futboleras de una fecha: quedan las de puntaje mayor o igual al umbral."""
    from . import escritor, wiki
    umbral = float(cfg.get("efemerides", {}).get("umbral", 8))
    lineas = wiki.efemerides(fecha)
    if not lineas:
        return []
    pedido = (f"Fecha: {fecha.day} de {wiki.MESES[fecha.month - 1]} de {fecha.year}. Estas son las efemérides futboleras de "
              "un día como ese según Wikipedia:\n" + "\n".join(lineas) + "\n\n"
              "Armá un ranking de las que valen un video para una cuenta argentina de fútbol. Reglas: solo ídolos "
              f"históricos de verdad (jugadores o técnicos nacidos en {fecha.year - 60} o antes, o ya fallecidos), "
              "leyendas de la Selección o de un club (también de equipos chicos o del ascenso), o hechos históricos "
              "(goles, títulos, partidos) que un futbolero argentino reconoce. Puntaje de 1 a 10 por importancia global "
              "para el público argentino: 10 = Maradona, Messi, Pelé, un Mundial ganado; 8 = ídolo enorme de un club "
              "grande o figura mundial; 6 = ídolo de un club chico conocido; menos = poco conocido. Cada candidata "
              "basada en UNA línea de la lista. Respondé solo JSON: {\"ranking\": [{\"tema\": \"...\", "
              "\"wikipedia\": [\"...\"], \"puntaje\": 9}]}")
    r = escritor.gemini("Sos un historiador del fútbol argentino, riguroso y exigente.", pedido, temperatura=0.4)
    elegidas = []
    for c in r.get("ranking", []):
        try:
            pts = float(c.get("puntaje", 0))
        except (TypeError, ValueError):
            pts = 0
        if c.get("tema") and pts >= umbral:
            elegidas.append({"tema": c["tema"], "wikipedia": c.get("wikipedia") or [], "puntaje": pts,
                             "estado": "pendiente", "intentos": 0})
    elegidas.sort(key=lambda c: -c["puntaje"])
    for i, c in enumerate(elegidas):
        c["n"] = i + 1
    return elegidas


def _planear_mes(cfg, hoy):
    """Calendario de efemérides: arma de una vez el ranking de todos los días que faltan del mes
    (y desde el día 25, también el mes que viene). Te avisa por mail y queda en data/efemerides-calendario.md."""
    import calendar
    import datetime as _dt
    datos = util.leer_json("data/efemerides.json", {})
    dias = []
    meses = [(hoy.year, hoy.month)]
    if hoy.day >= 25:
        meses.append((hoy.year + (hoy.month == 12), hoy.month % 12 + 1))
    for anio, mes in meses:
        for d in range(1, calendar.monthrange(anio, mes)[1] + 1):
            f = _dt.date(anio, mes, d)
            if f >= hoy and f.isoformat() not in datos:
                dias.append(f)
    if not dias:
        return datos
    util.log(f"Planifico las efemérides de {len(dias)} días…")
    nuevos = 0
    for f in dias:
        try:
            datos[f.isoformat()] = _ranking_dia(cfg, f)
            nuevos += 1
        except Exception as e:  # noqa
            util.log("Ranking del", f, "falló:", util.ocultar(e))
    datos = {k: v for k, v in datos.items() if k >= (hoy - _dt.timedelta(days=45)).isoformat()}
    util.guardar_json("data/efemerides.json", datos)
    # calendario legible
    nombres_dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    md = ["# Calendario de efemérides (Un día como hoy)", "",
          "Se arma solo a principio de mes. Para descartar una, cambiá su \"estado\" a \"descartada\" en "
          "`data/efemerides.json`.", ""]
    for k in sorted(datos):
        if k < hoy.isoformat() or not datos[k]:
            continue
        f = _dt.date.fromisoformat(k)
        md.append(f"**{nombres_dias[f.weekday()]} {f.day}/{f.month}**")
        md += [f'- {c["tema"]} ({c["puntaje"]:g}) · {c["estado"]}' for c in datos[k]]
        md.append("")
    if len(md) == 4:
        md.append("Por ahora no hay efemérides importantes en las próximas semanas.")
    (util.RAIZ / "data" / "efemerides-calendario.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if nuevos:
        util.avisar_mail("Calendario de efemérides listo", "\n".join(md[4:]) or "Sin efemérides importantes.")
    return datos


def _ranking_efemerides(cfg, hoy):
    datos = util.leer_json("data/efemerides.json", {})
    if hoy.isoformat() not in datos or (hoy.day >= 25 and not any(k > hoy.replace(day=28).isoformat() for k in datos)):
        datos = _planear_mes(cfg, hoy)
    return datos


def _marcar_efemeride(fecha, n, estado):
    datos = util.leer_json("data/efemerides.json", {})
    for c in datos.get(fecha, []):
        if c.get("n") == n:
            c["estado"] = estado
    util.guardar_json("data/efemerides.json", datos)


def _efemeride_pendiente(cfg):
    """La próxima efeméride importante de hoy que todavía no salió (y que no falló dos veces)."""
    hoy = util.ahora().date()
    datos = _ranking_efemerides(cfg, hoy)
    for c in datos.get(hoy.isoformat(), []):
        if c.get("estado") == "pendiente" and c.get("intentos", 0) < 2:
            c["intentos"] = c.get("intentos", 0) + 1
            util.guardar_json("data/efemerides.json", datos)
            return c
    return None


def _toca_efemeride_si(cfg):
    """Devuelve "toca ..." si en este horario corresponde publicar una efeméride; si no, el motivo."""
    conf = cfg.get("efemerides", {})
    ahora = util.ahora()
    hoy = ahora.date()
    if not conf.get("activas", True):
        return "las efemérides están apagadas (config.json → efemerides.activas)"
    horarios = []
    for h in conf.get("horarios", ["10:30", "12:00", "15:30", "17:00"]):
        hh, mm = (int(x) for x in h.split(":"))
        horarios.append(ahora.replace(hour=hh, minute=mm, second=0, microsecond=0))
    vencidos = [h for h in horarios if h <= ahora]
    publicadas_hoy = sum(1 for x in util.leer_json("data/historial.json", [])
                         if x.get("fecha") == hoy.isoformat() and x.get("extra") and x.get("serie") == "undia")
    if not vencidos:
        return "todavía no llegó el primer horario de efemérides"
    if publicadas_hoy >= len(vencidos):
        return f"ya salieron {publicadas_hoy} efemérides hoy; la próxima, en el siguiente horario"
    if (ahora - vencidos[-1]).total_seconds() > 150 * 60 and len(vencidos) == len(horarios):
        return "ya pasaron los horarios de efemérides de hoy"
    pendientes = [c for c in _ranking_efemerides(cfg, hoy).get(hoy.isoformat(), [])
                  if c.get("estado") == "pendiente" and c.get("intentos", 0) < 2]
    if pendientes:
        return f'toca la efeméride: {pendientes[0]["tema"]} ({pendientes[0]["puntaje"]:g})'
    return "hoy no hay (más) efemérides importantes"


def esperar():
    """Con el video listo, espera al minuto exacto del horario antes de publicar."""
    import time
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return
    objetivo = _objetivo(util.config())
    if not objetivo:
        return
    segundos = (objetivo - util.ahora()).total_seconds()
    if 0 < segundos < 70 * 60:
        util.log(f"Video listo. Espero {segundos / 60:.0f} minutos para publicar a las {objetivo:%H:%M}.")
        time.sleep(segundos)


def reporte():
    from . import escritor, investigar
    from . import publicar as pub
    cfg = util.config()
    clave = util.secreto("YT_API_KEY")
    if not clave:
        util.log("Sin YT_API_KEY no hay reporte")
        return
    cache = util.leer_json("data/canales.json", {})
    vistos, filas = set(), []
    for s in list(cfg["series"].values()):
        for b in s.get("canales", []):
            if b.lower() in vistos:
                continue
            vistos.add(b.lower())
            m = investigar.metricas_canal(b, clave, cache)
            if m:
                filas.append(m)
    util.guardar_json("data/canales.json", cache)
    propias, por_serie = _rendimiento(cfg, clave)
    nuestro = "\n".join(
        f'- {serie}: {a["posts"]} publicaciones, {a["vistas"] // max(a["posts"], 1)} vistas promedio, '
        f'{a["guardados"]} guardados, {a["compartidos"]} compartidos, {a["comentarios"]} comentarios'
        for serie, a in sorted(por_serie.items(), key=lambda x: -x[1]["vistas"] / max(x[1]["posts"], 1)))
    mejores = sorted(propias, key=lambda f: -f["vistas"])[:3]
    peores = sorted(propias, key=lambda f: f["vistas"])[:3]
    resumen = "\n\n".join(
        f'CANAL {f["canal"]} | {f["videos_por_semana"]} videos/semana | vistas típicas {f["mediana"]} | '
        f'{f["pct_shorts"]}% Shorts\n' + "\n".join(
            f'  - "{t["titulo"]}" ({t["vistas"]} vistas, {t["veces"]} veces lo normal)' for t in f["top"])
        for f in filas)
    sistema = ("Sos analista de contenido de una cuenta argentina sin cara de Shorts y Reels de fútbol: mitos, "
               "historias, récords insólitos, ídolos de antes y actualidad. Respondé en español rioplatense natural.")
    pedido = ("Con estas métricas de canales de referencia, devolvé un JSON con: "
              '{"patrones": ["..."], "formatos_que_rinden": ["..."], "estructuras_virales": ["..."], '
              '"ideas": [{"serie": "...", "titulo": "...", "miniatura": "..."}]} '
              "con 5 patrones, 5 formatos, 5 estructuras y 10 ideas originales adaptadas a Argentina para nuestras "
              "series (" + ", ".join(s["nombre"] for s in cfg["series"].values()) + "). "
              'Además sumá "series_reforzar": ["..."] y "series_cambiar": [{"serie": "...", "por_que": "...", '
              '"propuesta": "..."}] mirando NUESTRO RENDIMIENTO (si todavía hay pocos datos, decilo).\n\n'
              "NUESTRO RENDIMIENTO (últimos 30 días, por serie):\n" + (nuestro or "(todavía sin datos)") +
              "\n\nCOMPETENCIA:\n" + resumen)
    try:
        a = escritor.gemini(sistema, pedido, temperatura=0.7)
    except Exception as ex:  # noqa
        a = {"patrones": [f"No se pudo analizar: {ex}"]}
    fecha = util.ahora().strftime("%Y-%m-%d")
    md = [f"# Reporte de competencia · {fecha}", "", "| Canal | Videos/semana | Vistas típicas | % Shorts |",
          "|---|---|---|---|"]
    md += [f'| {f["canal"]} | {f["videos_por_semana"]} | {f["mediana"]:,} | {f["pct_shorts"]}% |' for f in filas]
    for titulo, clave_a in [("Patrones", "patrones"), ("Formatos que rinden", "formatos_que_rinden"),
                            ("Estructuras virales", "estructuras_virales")]:
        md += ["", f"## {titulo}", ""] + [f"- {x}" for x in a.get(clave_a, [])]
    md += ["", "## Cómo nos fue (últimos 30 días)", ""]
    if por_serie:
        md += ["| Serie | Publicaciones | Vistas promedio | Guardados | Compartidos | Comentarios |",
               "|---|---|---|---|---|---|"]
        md += [f'| {k} | {a["posts"]} | {a["vistas"] // max(a["posts"], 1):,} | {a["guardados"]} | '
               f'{a["compartidos"]} | {a["comentarios"]} |'
               for k, a in sorted(por_serie.items(), key=lambda x: -x[1]["vistas"] / max(x[1]["posts"], 1))]
        md += ["", "Lo que mejor anduvo: " + "; ".join(f'{f["titulo"]} ({f["vistas"]:,})' for f in mejores),
               "", "Lo que peor anduvo: " + "; ".join(f'{f["titulo"]} ({f["vistas"]:,})' for f in peores)]
    else:
        md += ["Todavía no hay publicaciones para medir."]
    horas = {}
    for f in propias:
        if f.get("hora"):
            franja = f["hora"][:2] + " h"
            x = horas.setdefault(franja, {"posts": 0, "vistas": 0})
            x["posts"] += 1
            x["vistas"] += f["vistas"]
    if horas:
        md += ["", "## Por horario de publicación", "", "| Franja | Publicaciones | Vistas promedio |", "|---|---|---|"]
        md += [f'| {k} | {v["posts"]} | {v["vistas"] // max(v["posts"], 1):,} |' for k, v in
               sorted(horas.items(), key=lambda x: -x[1]["vistas"] / max(x[1]["posts"], 1))]
    md += ["", "## Qué reforzar y qué cambiar", ""]
    md += [f"- Reforzar: {x}" for x in a.get("series_reforzar", [])]
    md += [f'- Cambiar **{x.get("serie", "")}**: {x.get("por_que", "")} → {x.get("propuesta", "")}'
           for x in a.get("series_cambiar", []) if isinstance(x, dict)]
    md += ["", "## Ideas para las próximas semanas", ""]
    md += [f'- **{i.get("serie", "")}**: {i.get("titulo", "")} · miniatura: "{i.get("miniatura", "")}"'
           for i in a.get("ideas", [])]
    md += ["", "## Lo que más rindió en cada canal", "", resumen]
    ruta = util.RAIZ / "reportes" / f"{fecha}.md"
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(md) + "\n", encoding="utf-8")
    try:
        pub.mail(f"Reporte semanal de competencia · {fecha}",
                 "<pre style='font-family:Arial;white-space:pre-wrap'>" + html.escape("\n".join(md)) + "</pre>")
    except Exception as ex:  # noqa
        util.log("No pude mandar el mail:", ex)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["generar", "publicar", "resumen", "reporte", "toca", "esperar", "probar", "muestra", "toca_extra",
                            "esperar_pedido"])
    ap.add_argument("--base-url", default="")
    ap.add_argument("--simulado", action="store_true")
    a = ap.parse_args()
    try:
        if a.accion == "toca":
            toca()
        elif a.accion == "esperar":
            esperar()
        elif a.accion == "generar":
            generar(a.simulado)
        elif a.accion == "publicar":
            publicar(a.base_url)
        elif a.accion == "resumen":
            resumen(a.base_url)
        elif a.accion == "muestra":
            muestra()
        elif a.accion == "toca_extra":
            toca_extra()
        elif a.accion == "esperar_pedido":
            esperar_pedido()
        elif a.accion == "probar":
            from . import probar
            probar.probar()
        else:
            reporte()
    except Exception as error:  # noqa
        import traceback
        print(util.ocultar(traceback.format_exc()), flush=True)
        util.avisar_error(a.accion, error)
        sys.exit(1)
