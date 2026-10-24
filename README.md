# Fábrica de fútbol · mitos, historias, récords y actualidad

Genera y publica solo un video corto por día (Reels y Shorts) de fútbol. Todo corre gratis en GitHub Actions: la IA propone varias ideas, les pone puntaje, se queda con la mejor que tenga respaldo (Wikipedia o datos reales de la semana), escribe el guion, lo revisa, lo narra con voz argentina y lo arma con fotos libres de Wikimedia Commons e ilustraciones hechas con IA. La portada es una tapa de diario de época.

## Qué hace cada día

1. **Elige la serie**: la del día o, si el día rota, la que hace más que no sale.
2. **Busca ideas** y las puntúa de 1 a 10. Si ninguna llega al mínimo (`puntaje_minimo`), no publica algo flojo: cambia a una serie de respaldo y te avisa por mail.
3. **Actualidad**: baja tablas, resultados y goleadores de football-data.org y, para las ligas que no cubre, Gemini busca en Google las noticias del finde. Solo entran datos con fuente.
5. **Escribe y revisa** el guion: gancho fuerte, lo mejor antes del segundo 10, duración libre hasta 58 segundos, título de hasta 40 caracteres.
6. **Imágenes**: foto real del jugador cuando su artículo de Wikipedia tiene una con licencia libre (con el crédito en la descripción); si no, ilustración.
7. **Mitos**: al final cae el sello del veredicto (VERDAD, MITO, A MEDIAS o NUNCA SE PROBÓ).

## Semana

| Día | Serie | Hora |
|---|---|---|
| Lunes | Actualidad del finde | 18:30 |
| Martes | Mitos del fútbol | 20:00 |
| Miércoles | ¿Qué fue de...? | 20:00 |
| Jueves | Rota: Ídolos del ascenso / ¿Cuánto ganaba...? | 20:00 |
| Viernes | La previa | 19:00 |
| Sábado | Mitos del fútbol | 13:00 |
| Domingo | Rota: Récords raros / Partidos insólitos / Pases insólitos / Apodos / Cábalas | 20:30 |

Se cambia en `config.json` (`plan_semanal` y `horarios`).

## Pedidos programados (videos a pedido para una fecha)

Para un video puntual en un día puntual (por ejemplo, la historia de las finales de Boca en la Sudamericana el día antes de la final), editá `data/pedidos.json` desde GitHub (abrilo → ícono del lápiz) y agregá una línea por fecha:

```json
"2026-11-27": { "tema": "Las finales de Boca en la Copa Sudamericana", "hora": "19:00", "en_lugar_del_del_dia": false }
```

- **fecha** (la clave): año-mes-día.
- **tema**: lo que querés que cuente, con tus palabras.
- **hora**: a qué hora se publica (hora de Argentina).
- **en_lugar_del_del_dia**: `false` sale como video extra y el de la grilla sale igual; `true` lo reemplaza.
- **serie** (opcional): por defecto `especial` (tono de previa de partido grande, con el contexto de las noticias de esos días). También podés poner `mitos`, `insolitos`, `ascenso`, etcétera.
- Para dos pedidos el mismo día, poné una lista: `"2026-11-27": [ {...}, {...} ]`.
- Antes de programarlo, podés probarlo con **Muestra corta** (serie `especial`, el tema y 60 segundos).
- Lo publica el workflow **Extras**. Si falla, lo reintenta una vez.

## Tendencias

Antes de elegir la idea de cada día, la fábrica mira qué es tendencia en el fútbol: lo más leído ayer en Wikipedia en español, las noticias más comentadas del día (Gemini busca en Google) y, si cargás el secreto opcional `YT_API_KEY`, los videos de deportes en tendencia en YouTube Argentina. Las ideas que se conectan de verdad con eso suman puntos, y la conexión se usa en el gancho (por ejemplo: el ídolo histórico del club que juega la final hoy). Se calcula una vez por día y queda en `data/tendencias.json`. Se apaga con `"usar_tendencias": false` en `config.json`.

## Un día como hoy (videos extra, solo cuando vale la pena)

A principio de mes (y desde el día 25, también para el mes siguiente) la fábrica lee en Wikipedia las efemérides futboleras de cada día (cumpleaños, goles, títulos, partidos históricos), arma un ranking y se queda con las importantes: ídolos históricos de 60 años o más (o ya fallecidos) y hechos que cualquier futbolero argentino reconoce, con puntaje 8 o más. Te manda el calendario por mail y queda en `data/efemerides-calendario.md`. Para descartar una, cambiá su `"estado"` a `"descartada"` en `data/efemerides.json`.

- Si no hay ninguna importante, ese día no sale nada extra.
- Si hay una o varias, sale una en cada horario de efemérides (10:30, 12:00, 15:30 y 17:00), de la más importante a la menos.
- No cuentan para la grilla: el video del día sale igual.
- Se ajusta en `config.json` → `efemerides` (`umbral`, `horarios`, `activas`). Para que puedan salir más por día, sumá horarios.


## Secretos (Settings → Secrets and variables → Actions)

| Secreto | Para qué | ¿Obligatorio? |
|---|---|---|
| `GEMINI_API_KEY` | Guion, revisión y voz (Google AI Studio, nivel gratuito, proyecto propio de esta fábrica) | Sí |
| `PIXABAY_API_KEY` | Clips de stock (casi no se usan) | Sí |
| `FOOTBALL_DATA_KEY` | Tablas, resultados y goleadores (football-data.org, plan gratis) | Sí |
| `CF_ACCOUNT_ID` y `CF_API_TOKEN` | Ilustraciones con Cloudflare Workers AI (cupo gratis diario, sin tarjeta) | Recomendado |
| `POLLINATIONS_KEY` | Respaldo de ilustraciones (si no está, usa Pollinations libre) | No |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Publicar en YouTube | Al conectar YouTube |
| `IG_TOKEN`, `GH_PAT` | Publicar en Instagram y renovar el token solo | Al conectar Instagram |
| `FB_PAGE_TOKEN`, `FB_PAGE_ID` | Publicar en Facebook (opcional) | Al conectar Facebook |
| `SMTP_USER`, `SMTP_PASS` | Mail diario (Gmail con contraseña de aplicación) | Para TikTok a mano |

Las claves nunca van en el código ni en el chat: siempre acá.

## Botones (pestaña Actions)

- **Muestra corta**: escribe el guion completo, arma la portada y los primeros segundos del video, sin publicar. Podés elegir la serie y un tema puntual. El resultado queda en la carpeta `muestras/ultima` (abrí el `README.md` de esa carpeta para verlo todo junto).
- **Publicación diaria**: la que corre sola. Con *Run workflow* se puede forzar una serie o un tema, y destildar "publicar" para solo generar.
- **Probar conexiones**: revisa en un minuto si las llaves de Instagram, Facebook y YouTube andan, sin publicar nada. Usalo cada vez que cambies una llave.
- **Extras (pedidos programados y efemérides)**: el reloj de los videos extra. Con *Run workflow* podés fabricar ya el pedido de hoy o la próxima efeméride importante.
- **Reporte semanal de competencia**: los lunes, cómo le fue a cada serie (necesita `YT_API_KEY`, opcional).

## Conectar las redes

### Instagram (se publica solo desde el primer día)

Requisito: la cuenta de Instagram tiene que ser **profesional** (creador o empresa). Se cambia desde la app en *Configuración → Tipo de cuenta*.

1. Entrá a https://developers.facebook.com → **Mis apps → Crear app** → tipo **Empresa** (o "Otro").
2. Dentro de la app, agregá el producto **Instagram** → **Configuración de la API con inicio de sesión de Instagram**.
3. En **Generar tokens de acceso**, agregá tu cuenta de Instagram, aceptá los permisos y copiá el token.
4. Guardalo como secreto `IG_TOKEN`.
5. **Para que el token se renueve solo** (vence cada 60 días): creá un token de GitHub en https://github.com/settings/personal-access-tokens/new con **Repository access: solo `fabrica-futbol`** y **Permissions → Secrets: Read and write**. Guardalo como secreto `GH_PAT`.
6. En `config.json` poné `"instagram_reel": true`.

### Facebook (Reels en una página, se publica solo desde el primer día)

La API de Meta solo publica en **páginas**, no en perfiles personales.

1. Creá la página desde tu perfil: https://www.facebook.com/pages/create (mismo nombre y foto que en Instagram; categoría "Creador digital" o "Medios y noticias").
2. Vinculá Instagram a la página: en la página, *Configuración → Cuentas vinculadas → Instagram*.
3. En tu app de developers.facebook.com: *Casos de uso → Agregar caso de uso → "Administrar todo en tu página"*. Permisos: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
4. En https://developers.facebook.com/tools/explorer elegí la app, tocá **Generate Access Token** (token de usuario), tildá esos permisos y elegí tu página.
5. Hacelo durar: https://developers.facebook.com/tools/debug/accesstoken → pegá el token → **Extend Access Token** y copiá el nuevo.
6. En el Explorer, con ese token largo, consultá `me/accounts`. De tu página copiá `access_token` (este no vence) e `id`.
7. Guardá los secretos `FB_PAGE_TOKEN` y `FB_PAGE_ID`, y en `config.json` poné `"facebook": true`.
8. **Publicá la app de Meta** (si no, los Reels de Facebook solo los ves vos): en *Configuración de la app → Básica* completá la URL de la política de privacidad y la de eliminación de datos (sirve el link a `PRIVACIDAD.md`), un ícono de 1024×1024 y la categoría; después tocá **Publicar** en el menú izquierdo.

### YouTube (se publica solo desde el primer día)

1. Podés reusar el cliente de Google de la otra fábrica (mismo ID y secreto, y agregá la página principal y la privacidad de este repo). Lo único nuevo es el **refresh token** del canal nuevo: hacé el paso 4 entrando con la cuenta del canal nuevo.
2. **Google Auth Platform** (https://console.cloud.google.com/auth/overview): elegí tipo **Externo** y completá nombre y mail. En **Información de la marca** poné como página principal la dirección de tu repo nuevo (por ejemplo `https://github.com/TU-USUARIO/fabrica-futbol`), como política de privacidad el link a `PRIVACIDAD.md` de este repo y como dominio autorizado `github.com`. Después, en **Público**, tocá **Publicar app** (tiene que quedar **En producción**). Si queda en "Prueba", el permiso vence cada 7 días y se corta todo. El aviso de "requiere verificación" se ignora: no hace falta para usarla vos.
3. **Clientes → Crear cliente → Aplicación web**. En *URI de redireccionamiento autorizados* poné `https://developers.google.com/oauthplayground`. Copiá el **ID de cliente** y el **secreto**.
4. Entrá a https://developers.google.com/oauthplayground:
   1. Tocá el engranaje, tildá **Use your own OAuth credentials** y pegá el ID y el secreto.
   2. A la izquierda escribí `https://www.googleapis.com/auth/youtube.upload` y tocá **Authorize APIs**. Entrá con la cuenta del canal; si aparece "app no verificada", tocá **Avanzado → Ir a la app**.
   3. Tocá **Exchange authorization code for tokens** y copiá el **Refresh token**.
5. Guardá los secretos `YT_CLIENT_ID`, `YT_CLIENT_SECRET` y `YT_REFRESH_TOKEN`.
6. En `config.json` poné `"youtube": true`.
7. Listo: los videos salen públicos. (Desde 2026 Google ya no deja en privado lo que suben las apps sin verificar. Si algún día un video aparece como privado con un aviso, hay que pedir la auditoría en el formulario "YouTube API Services - Audit and Quota Extension Form".)

### TikTok (más adelante)

TikTok exige crear una app en https://developers.tiktok.com con **Content Posting API** y aprobarla. Hasta entonces, los videos subidos por API quedan en privado. Mientras tanto, el mail diario te trae el video y el texto para subirlo desde el celular en 30 segundos. Cuando quieras activarlo, avisame y lo configuramos juntos.

## Cómo cambiar cosas

- **Usuario, días, horarios, duración, voz, nombre del diario, puntaje mínimo y estilo de dibujo:** `config.json`.
- **Cómo escribe el narrador:** `prompts/maestro.md`. Reglas de formato: `prompts/formato.md`. Revisión: `prompts/revision.md`.
- **Música:** subí uno o varios `.mp3` épicos o deportivos libres de derechos a `assets/` (ver `assets/LEEME.md`).

## Si algo falla

- GitHub te manda un mail automático cuando una ejecución falla, y el motivo queda arriba de todo en la ejecución.
- Todo queda registrado en `publicaciones/` (un archivo por día) y en `data/historial.json`.
