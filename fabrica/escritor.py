"""Escribe el guion, el carrusel y los textos con Gemini (clave gratuita de Google AI Studio)."""
import json
import re

from . import util

API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


def _prompt(nombre):
    return (util.RAIZ / "prompts" / nombre).read_text(encoding="utf-8")


def _json_de(texto):
    t = re.sub(r"```(?:json)?", "", texto or "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("La IA no devolvió JSON: " + t[:200])
    return json.loads(t[a:b + 1])


LISTA = "https://generativelanguage.googleapis.com/v1beta/models"
_DESCARTAR = ("image", "tts", "audio", "live", "embed", "native", "exp", "computer", "robotics", "vision", "omni")
# Motivos por los que Google bloquea el pedido por su contenido (no tiene sentido probar otro modelo)
BLOQUEOS = ("PROHIBITED_CONTENT", "SAFETY", "BLOCKLIST", "SPII", "OTHER", "IMAGE_SAFETY", "RECITATION")
_SEGURIDAD = [{"category": c, "threshold": "BLOCK_ONLY_HIGH"} for c in
              ("HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT",
               "HARM_CATEGORY_DANGEROUS_CONTENT")]


class Bloqueado(RuntimeError):
    """Google rechazó el pedido por su contenido (pasa con el pedido, no con el modelo)."""
_modelo_ok = None  # el primer modelo que anduvo en esta ejecución se reusa


def _version(nombre):
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", nombre)
    return float(m.group(1)) if m else 0.0


def _descubrir(clave):
    """Pide a Google la lista de modelos vigentes y ordena los Flash del más nuevo al más viejo.
    Así, cuando Google retire un modelo, la fábrica encuentra sola el reemplazo."""
    try:
        r = util.pedir("GET", LISTA, headers={"x-goog-api-key": clave}, params={"pageSize": 1000}, timeout=60)
        modelos = r.json().get("models", []) if r is not None and r.status_code == 200 else []
    except Exception as e:  # noqa
        util.log("No pude listar los modelos de Gemini:", util.ocultar(str(e)))
        return []
    nombres = []
    for m in modelos:
        n = m.get("name", "").split("/")[-1]
        if ("generateContent" in m.get("supportedGenerationMethods", []) and "flash" in n
                and not any(x in n for x in _DESCARTAR)):
            nombres.append(n)
    # primero Flash común, después Lite; dentro de cada grupo, estable antes que preview y versión más nueva primero
    nombres.sort(key=lambda n: ("lite" in n, "preview" in n, -_version(n), n))
    return nombres


def _cuerpo(sistema, usuario, temperatura, modelo, con_pensamiento, con_seguridad=True):
    gen = {"responseMimeType": "application/json", "maxOutputTokens": 32768}
    moderno = "latest" in modelo or _version(modelo) >= 3
    if moderno:
        # Gemini 3+: Google recomienda temperatura 1.0 y, si no se aclara, piensa "a fondo" y gasta
        # todo el cupo de salida pensando. Con nivel bajo alcanza para guiones cortos.
        if con_pensamiento:
            gen["thinkingConfig"] = {"thinkingLevel": util.config().get("gemini_pensamiento", "low")}
    else:
        gen["temperature"] = temperatura
    cuerpo = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        # usuario puede ser texto o una lista de partes (texto + imágenes)
        "contents": [{"role": "user", "parts": usuario if isinstance(usuario, list) else [{"text": usuario}]}],
        "generationConfig": gen,
    }
    if con_seguridad:
        cuerpo["safetySettings"] = _SEGURIDAD
    return cuerpo


def _mensaje(r):
    try:
        return r.json()["error"]["message"][:220]
    except Exception:  # noqa
        return (getattr(r, "text", "") or "")[:220]


def gemini(sistema, usuario, temperatura=0.9):
    global _modelo_ok
    clave = util.secreto("GEMINI_API_KEY")
    if not clave:
        raise RuntimeError("Falta el secreto GEMINI_API_KEY (Settings → Secrets and variables → Actions)")
    preferidos = ([_modelo_ok] if _modelo_ok else []) + util.config().get("gemini_modelos", ["gemini-flash-latest"])
    probados, errores, descubiertos, bloqueos = set(), [], False, 0
    cola = list(preferidos)
    while cola or not descubiertos:
        if not cola:
            descubiertos = True
            cola = [m for m in _descubrir(clave) if m not in probados][:5]
            if cola:
                util.log("Busco modelos vigentes de Gemini:", ", ".join(cola))
            continue
        modelo = cola.pop(0)
        if modelo in probados:
            continue
        probados.add(modelo)
        texto, fin = "", ""
        # Si el modelo no acepta algún ajuste (pensamiento o filtros), pruebo sin él.
        for ajustes in ((True, True), (False, True), (False, False)):
            r = util.pedir("POST", API.format(modelo=modelo), headers={"x-goog-api-key": clave},
                           json=_cuerpo(sistema, usuario, temperatura, modelo, *ajustes),
                           intentos=1 if descubiertos else 3, espera=15, timeout=240)
            if r is not None and r.status_code == 400 and any(x in _mensaje(r).lower() for x in ("think", "safety")):
                continue
            break
        if r is None or r.status_code != 200:
            errores.append(f"{modelo}: {getattr(r, 'status_code', '?')} {_mensaje(r)}")
            continue
        datos = r.json()
        cand = (datos.get("candidates") or [{}])[0]
        en_pedido = (datos.get("promptFeedback") or {}).get("blockReason", "")
        fin = cand.get("finishReason", "") or en_pedido
        donde = "en lo que le mandamos" if en_pedido and not datos.get("candidates") else "en lo que la IA escribió"
        partes = (cand.get("content") or {}).get("parts", [])
        texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
        try:
            resultado = _json_de(texto)
            if _modelo_ok != modelo:
                util.log("Modelo de Gemini usado:", modelo)
            _modelo_ok = modelo
            return resultado
        except Exception as e:  # noqa
            errores.append(f"{modelo}: respuesta sin JSON (motivo: {fin or 'desconocido'}) {str(e)[:80]}")
            if fin in BLOQUEOS:
                bloqueos += 1
                if bloqueos >= 2:  # dos modelos distintos lo rechazan: es el contenido del pedido
                    raise Bloqueado(f"Google bloqueó el pedido por su contenido ({fin}, {donde})")
    raise RuntimeError("Gemini falló con todos los modelos: " + " | ".join(errores))


def _limpiar(s, voz=False):
    s = str(s or "").replace("—", ", ").replace("–", ", ")
    s = re.sub(r"(\d)\s?%", r"\1 por ciento", s)
    s = EMOJI_RE.sub("", s)
    return re.sub(r"\s+", " ", s).replace(" ,", ",").strip()


_SIGLAS = ["FBI", "CIA", "NASA", "ONU", "AFA", "FIFA", "UNLP", "YPF", "DNI", "EEUU", "URSS", "ARA", "PFA", "SIDE"]
_SIGLAS_RE = re.compile(r"\b(" + "|".join(sorted(_SIGLAS, key=len, reverse=True)) + r")\b", re.IGNORECASE)
_SIGLAS_MAP = {s.lower(): s for s in _SIGLAS}


def _siglas(s, oracion=False):
    """Siglas siempre en mayúscula y, si es un título, mayúscula al principio."""
    s = _SIGLAS_RE.sub(lambda m: _SIGLAS_MAP.get(m.group(0).lower(), m.group(0)), s or "")
    if oracion:
        for i, c in enumerate(s):
            if c.isalpha():
                s = s[:i] + c.upper() + s[i + 1:]
                break
    return s


_EMOJI_REEMPLAZO = {"📅": "🗓️", "📆": "🗓️"}  # los calendarios muestran una fecha fija ("JULY 17") que confunde


def _emoji(e, defecto):
    e = str(e or "").strip()
    for viejo, nuevo in _EMOJI_REEMPLAZO.items():
        e = e.replace(viejo, nuevo)
    return e[:4] if e else defecto


def _broll(b):
    """Búsquedas en inglés para los videos de stock de la escena (una o dos)."""
    lista = b if isinstance(b, list) else [b]
    limpias = [re.sub(r"[^A-Za-z0-9 \-]", "", str(x or "")).strip()[:60] for x in lista]
    return [x for x in limpias if len(x) > 2][:2]


def validar(d):
    cfg = util.config()
    escenas = []
    for e in d.get("escenas", []):
        voz = _limpiar(e.get("texto_voz") or e.get("texto"), voz=True)
        if voz:
            escenas.append({"texto_voz": voz,
                            "texto_pantalla": _siglas(_limpiar(e.get("texto_pantalla"))),
                            "emoji": _emoji(e.get("emoji"), "📜"),
                            "prompt": str(e.get("prompt") or "").strip(),
                            "broll": _broll(e.get("broll"))})
    if escenas and not escenas[0]["texto_pantalla"]:
        escenas[0]["texto_pantalla"] = " ".join(escenas[0]["texto_voz"].split()[:6])
    carrusel = []
    for p in d.get("carrusel", []) or []:
        if p.get("titulo"):
            carrusel.append({"titulo": _siglas(_limpiar(p["titulo"]), True),
                             "cuerpo": _siglas(_limpiar(p.get("cuerpo") or p.get("texto")), True),
                             "emoji": _emoji(p.get("emoji"), "📜")})
    palabras = sum(len(e["texto_voz"].split()) for e in escenas)
    tope = int(cfg.get("palabras_max", 150))
    if len(escenas) < 4:
        raise ValueError(f"Guion corto: {len(escenas)} escenas")
    if palabras > tope + 15:  # un margen chico: el revisor después lo ajusta
        raise ValueError(f"Guion largo: {palabras} palabras (tope {tope})")
    tags = []
    for h in d.get("hashtags", []):
        h = "#" + re.sub(r"[^\wáéíóúñü]", "", str(h).lower().lstrip("#"))
        if len(h) > 2 and h not in tags:
            tags.append(h)
    for fijo in ("#argentina", "#historias"):
        if fijo not in tags:
            tags.append(fijo)
    mini = d.get("miniatura") or {}
    return {
        "titulo": _siglas(_limpiar(d.get("titulo")), True)[:95],
        "descripcion": _siglas(_limpiar(d.get("descripcion")), True),
        "hashtags": tags[:8],
        "miniatura": {"linea1": _siglas(_limpiar(mini.get("linea1") or d.get("titulo")), True),
                      "linea2": _siglas(_limpiar(mini.get("linea2"))),
                      "emoji": _emoji(mini.get("emoji"), escenas[0]["emoji"]),
                      "prompt": str(mini.get("prompt") or escenas[0]["prompt"])},
        "fuentes": [_limpiar(x)[:120] for x in (d.get("fuentes") or []) if _limpiar(x)][:5],
        "escenas": escenas,
        "carrusel": carrusel[:10],
        "palabras": palabras,
    }


def _material(fuentes, nivel):
    """Videos de referencia de YouTube (opcional, solo si hay YT_API_KEY y canales en la serie).
    nivel 0: todo el material; 1: solo los títulos; 2: sin material."""
    if nivel >= 2 or not fuentes:
        return ""
    bloques = []
    for i, f in enumerate(fuentes, 1):
        texto = f.get("transcripcion") or f.get("descripcion") or ""
        cab = (f'VIDEO DE REFERENCIA {i} · "{f["titulo"]}" · canal {f["canal"]} · {f.get("vistas", "?")} vistas, '
               f'{f.get("score", "?")} veces su promedio')
        bloques.append(cab + ("\n" + texto[:3000] if nivel == 0 and texto else ""))
    return "\n\n".join(bloques)


def _previos(titulos_previos):
    return "\n".join("- " + t for t in titulos_previos[:60]) or "- (ninguno todavía)"


def elegir_tema(serie, titulos_previos, tema=None, material_yt=""):
    """Paso 1: la IA propone historias candidatas con sus artículos de Wikipedia.
    Paso 2: se busca el respaldo en Wikipedia y se queda con la primera que esté documentada."""
    from . import wiki
    if tema:
        pedido = (f'Tema pedido: "{tema}".\n' + serie["prompt"] + "\n\n"
                  "Devolvé UNA candidata sobre ese tema exacto. ")
    else:
        pedido = (serie["prompt"] + "\n\nTemas ya publicados (NO repetir ni hacer variantes muy parecidas):\n" +
                  _previos(titulos_previos) + "\n\n" +
                  (("VIDEOS QUE FUNCIONARON EN CANALES PARECIDOS (solo como pista de qué engancha):\n" +
                    material_yt[:4000] + "\n\n") if material_yt else "") +
                  "Proponé 4 historias reales candidatas, distintas entre sí, ordenadas de la que más puede "
                  "explotar en redes a la que menos. Que sean poco conocidas o con un dato que casi nadie sabe. ")
    pedido += ('Para cada una: "tema" (una frase con quién, qué y cuándo), "gancho" (la primera frase del video) y '
               '"wikipedia" (de 1 a 3 títulos de artículos de Wikipedia en español que cuenten esos hechos; '
               'el título exacto si lo sabés). Respondé solo JSON: {"candidatas": [{"tema": "...", "gancho": "...", '
               '"wikipedia": ["..."]}]}')
    sistema = _prompt("maestro.md")
    try:
        candidatas = [c for c in gemini(sistema, pedido, temperatura=1.0).get("candidatas", []) if isinstance(c, dict)]
    except Exception as e:  # noqa
        util.log("No pude elegir el tema con candidatas:", util.ocultar(e))
        candidatas = []
    if tema and not candidatas:
        candidatas = [{"tema": tema, "gancho": "", "wikipedia": [tema]}]
    for c in candidatas[:4]:
        consultas = [x for x in (c.get("wikipedia") or []) if x][:3]
        if tema:
            consultas.append(tema)
        articulos = wiki.material(consultas)
        if articulos:
            util.log("Tema elegido:", c.get("tema"), "· respaldo:", ", ".join(a["titulo"] for a in articulos))
            return c, articulos
        util.log("Sin respaldo en Wikipedia, descarto:", c.get("tema"))
    if candidatas:
        util.avisar("Historia sin respaldo en Wikipedia",
                    "Ninguna candidata tuvo artículo en Wikipedia; el guion se escribe con cuidado extra.")
        return candidatas[0], []
    return None, []


def _pedido(serie, titulos_previos, candidata, material):
    elegido = ""
    if candidata:
        elegido = (f'HISTORIA ELEGIDA: {candidata.get("tema", "")}\n'
                   f'Idea de gancho (mejorala si podés): {candidata.get("gancho", "")}\n\n')
    material = material or ("(No hay material de referencia: usá solo hechos archiconocidos y seguros. "
                            "Ante la duda, contalo sin el dato.)")
    return (serie["prompt"] + "\n\n" + elegido + _prompt("formato.md") + "\n\n"
            "Temas ya publicados (NO repetir):\n" + _previos(titulos_previos) + "\n\n"
            "MATERIAL DE REFERENCIA (los hechos del guion tienen que salir de acá; el texto tiene que ser nuestro, "
            "nunca copiado ni traducido frase por frase):\n\n" + material)


_SISTEMA_MINIMO = ("Sos un narrador argentino que cuenta historias reales y curiosas de Argentina en videos cortos. "
                   "Escribís en español rioplatense, con voseo, claro y con suspenso. Nunca inventás datos.")


def _acortar_titulo(contenido, sistema):
    tope = int(util.config().get("titulo_max", 40))
    if len(contenido["titulo"]) <= tope:
        return contenido
    try:
        r = gemini(sistema, f'Este título de video tiene {len(contenido["titulo"])} caracteres y el máximo es {tope}: '
                            f'"{contenido["titulo"]}". Historia: {contenido["escenas"][0]["texto_voz"]} '
                            f'Escribí 3 títulos alternativos cortos y picantes de máximo {tope} caracteres '
                            '(contando espacios), sin emojis, en español rioplatense. Respondé solo JSON: '
                            '{"titulos": ["...", "...", "..."]}', temperatura=0.8)
        for t in r.get("titulos", []):
            t = _siglas(_limpiar(t), True)
            if 8 <= len(t) <= tope:
                util.log("Título acortado:", contenido["titulo"], "→", t)
                contenido["titulo"] = t
                return contenido
    except Exception as e:  # noqa
        util.log("No pude acortar el título:", util.ocultar(e))
    corto = contenido["miniatura"]["linea1"]
    if len(corto) <= tope:
        contenido["titulo"] = corto
    return contenido


def escribir(serie, fuentes, titulos_previos, tema=None):
    from . import wiki
    sistema = _prompt("maestro.md")
    candidata, articulos = elegir_tema(serie, titulos_previos, tema, _material(fuentes, 1))
    material = wiki.como_texto(articulos)
    borrador = None
    for intento, (sis, mat) in enumerate(((sistema, material), (sistema, material[:5000]), (_SISTEMA_MINIMO, material[:5000]))):
        try:
            borrador = validar(gemini(sis, _pedido(serie, titulos_previos, candidata, mat)))
            break
        except Bloqueado as e:
            util.avisar("Google bloqueó el pedido, reintento", str(e))
        except ValueError as e:
            util.log("Borrador inválido, reintento:", e)
    if borrador is None:
        raise RuntimeError("No se pudo escribir el guion después de 3 intentos")
    util.log("Borrador:", borrador["titulo"], f'({borrador["palabras"]} palabras)')
    final = borrador
    try:
        para_revisar = {k: v for k, v in borrador.items() if k not in ("palabras", "carrusel")}
        chequeo = ("\n\nMATERIAL DE REFERENCIA (para chequear cada dato):\n" + material[:12000]) if material else \
            "\n\n(No hubo material de referencia: sacá todo dato que no sea archiconocido y seguro.)"
        revisado = gemini(sistema, _prompt("revision.md") + "\n\nJSON A REVISAR:\n" +
                          json.dumps(para_revisar, ensure_ascii=False) + chequeo, temperatura=0.6)
        final = validar(revisado)
        util.log("Revisado:", final["titulo"], f'({final["palabras"]} palabras)')
    except Exception as e:  # noqa
        util.log("La revisión falló, uso el borrador:", util.ocultar(e))
    final = _acortar_titulo(final, sistema)
    final["wikipedia"] = [{"titulo": a["titulo"], "url": a["url"], "idioma": a["idioma"]} for a in articulos]
    final["tema"] = (candidata or {}).get("tema", "")
    return final
