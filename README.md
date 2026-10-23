# Fábrica de historias · historias reales y curiosas de Argentina

Genera y publica solo un video corto por día (Reels, Shorts y TikTok) con historias reales, virales y poco conocidas de Argentina, dos días por semana de La Plata. Todo corre gratis en GitHub Actions: la IA elige la historia, busca el respaldo en Wikipedia, escribe el guion, lo revisa, lo narra con voz argentina y lo arma con ilustraciones hechas con IA.

## Qué hace cada día

1. **Elige la historia** de la serie del día: Gemini propone candidatas y se queda con la primera que tiene respaldo en Wikipedia, para no inventar.
2. **Escribe el guion** con gancho fuerte en la primera frase y lo mejor antes del segundo 10. Dura lo que la historia necesite, sin relleno, con tope de 58 segundos.
3. **Lo revisa**: compara cada dato con Wikipedia, chequea que la historia cierre y que el título tenga hasta 40 caracteres.
4. **Lo narra** con la voz de Gemini (respaldo: voz de Microsoft) y sincroniza los subtítulos con Whisper.
5. **Lo ilustra**: un dibujo por escena con zoom lento (Cloudflare o Pollinations, gratis). Si la escena muestra un lugar real, prueba un clip de Pixabay sin textos ni logos.
6. **Arma la portada** con el título en la zona central, para que no se corte en la grilla de Instagram.
7. **Publica** en las redes que estén en `true` y te manda un mail con el video y el texto (para subirlo a TikTok a mano).

## Series

| Día | Serie | Hora |
|---|---|---|
| Lunes | Lo hizo un argentino | 20:00 |
| Martes | La Plata secreta | 19:00 |
| Miércoles | Caso real | 21:00 |
| Jueves | El argentino que... | 20:30 |
| Viernes | Se hizo viral | 19:00 |
| Sábado | La Plata secreta | 13:00 |
| Domingo | Leyendas argentinas | 13:30 |

Se cambian en `config.json` (`plan_semanal` y `horarios`). El reloj corre cada 30 minutos; si GitHub se atrasa, publica igual hasta 3 horas después.

## Secretos (Settings → Secrets and variables → Actions)

| Secreto | Para qué | ¿Obligatorio? |
|---|---|---|
| `GEMINI_API_KEY` | Guion, revisión y voz (Google AI Studio, nivel gratuito, proyecto propio de esta fábrica) | Sí |
| `PIXABAY_API_KEY` | Clips de lugares reales | Sí |
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
- **Reporte semanal de competencia**: los lunes, cómo le fue a cada serie (necesita `YT_API_KEY`, opcional).

## Conectar las redes

### Instagram (se publica solo desde el primer día)

Requisito: la cuenta de Instagram tiene que ser **profesional** (creador o empresa). Se cambia desde la app en *Configuración → Tipo de cuenta*.

1. Entrá a https://developers.facebook.com → **Mis apps → Crear app** → tipo **Empresa** (o "Otro").
2. Dentro de la app, agregá el producto **Instagram** → **Configuración de la API con inicio de sesión de Instagram**.
3. En **Generar tokens de acceso**, agregá tu cuenta de Instagram, aceptá los permisos y copiá el token.
4. Guardalo como secreto `IG_TOKEN`.
5. **Para que el token se renueve solo** (vence cada 60 días): creá un token de GitHub en https://github.com/settings/personal-access-tokens/new con **Repository access: solo `fabrica-historias`** y **Permissions → Secrets: Read and write**. Guardalo como secreto `GH_PAT`.
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
2. **Google Auth Platform** (https://console.cloud.google.com/auth/overview): elegí tipo **Externo** y completá nombre y mail. En **Información de la marca** poné como página principal la dirección de tu repo nuevo (por ejemplo `https://github.com/TU-USUARIO/fabrica-historias`), como política de privacidad el link a `PRIVACIDAD.md` de este repo y como dominio autorizado `github.com`. Después, en **Público**, tocá **Publicar app** (tiene que quedar **En producción**). Si queda en "Prueba", el permiso vence cada 7 días y se corta todo. El aviso de "requiere verificación" se ignora: no hace falta para usarla vos.
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

- **Usuario, días, horarios, duración, voz y estilo de dibujo:** `config.json`.
- **Cómo escribe el narrador:** `prompts/maestro.md`. Reglas de formato: `prompts/formato.md`. Revisión: `prompts/revision.md`.
- **Música:** subí uno o varios `.mp3` de suspenso o misterio libres de derechos a `assets/` (ver `assets/LEEME.md`).

## Si algo falla

- GitHub te manda un mail automático cuando una ejecución falla, y el motivo queda arriba de todo en la ejecución.
- Todo queda registrado en `publicaciones/` (un archivo por día) y en `data/historial.json`.
