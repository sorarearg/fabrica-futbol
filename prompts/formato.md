Formato: VIDEO CORTO (Reel o Short) con voz en off, fotos libres e ilustraciones.

DURACIÓN
- La historia dura lo que necesite, sin relleno: normalmente entre 20 y 55 segundos (entre 55 y 150 palabras en total). Nunca más de 150 palabras.
- Nunca dejes la historia inconclusa ni sin el dato que la hace interesante.

ESTRUCTURA
1. Gancho (escena 1, máximo 14 palabras): el momento más fuerte, un nombre conocido o un dato que choque.
2. Lo mejor antes del segundo 10 (más o menos las primeras 25 palabras): el giro o el dato que sorprende.
3. Desarrollo: los hechos en orden, una idea por escena.
4. Desenlace clarísimo (en Mitos: el veredicto).
5. Cierre corto para compartir o comentar, coherente con lo que se contó: si ya diste un veredicto, no preguntes "¿mito o verdad?" (preguntá otra cosa: otra anécdota, etiquetar a alguien, una opinión).

ESCENAS
- Entre 6 y 16 escenas. Cada escena es una o dos frases cortas (de 5 a 16 palabras en total).
- texto_voz: lo que se dice, escrito para el oído (números en palabras).
- texto_pantalla: solo en la escena 1, el gancho para leer sin sonido (máximo 6 palabras, puede llevar números). En las demás, vacío.
- foto: CADA persona real que se nombra (jugador, técnico, dirigente, representante) tiene que tener su nombre en el campo foto en al menos una escena. Para un equipo, podés poner su estadio ("Estadio Jorge Luis Hirschi"), nunca un escudo. Si en esa escena el protagonista es un jugador o técnico real y conocido, su nombre completo como figura en Wikipedia ("Diego Maradona", "Claudio Caniggia"). Se va a buscar una foto real con licencia libre. Si no, vacío. Usalo en las escenas donde se habla de esa persona.
- prompt: descripción EN INGLÉS de una ilustración para esa escena (se usa si no hay foto): concreta y visual (qué pasa, dónde, época, luz, emoción).
  - Nunca nombres de personas reales en el prompt: describilas ("a curly-haired Argentine striker in a light blue and white striped shirt").
  - Camisetas genéricas o con los colores del club, sin escudos, sponsors ni números. Nada de logos ni texto legible.
  - Época correcta (estadios, ropa, pelota de esos años).
- broll: lista vacía (casi nunca hace falta). Solo para algo filmable que se ve igual hoy ("stadium crowd night", "football on grass").
- emoji: UN emoji de respaldo (⚽, 🏆, 🧤, 🥅, 📰, 💰...).

TEXTOS PARA PUBLICAR
- titulo: MÁXIMO 40 CARACTERES contando espacios. Corto, picante, con nombre propio o una pregunta que pica ("¿Argentina drogó a Brasil?", "Lo cambiaron por pelotas"). Sin emojis.
- descripcion: 2 o 3 frases como por WhatsApp, con el dato clave. La última invita a comentar con una pregunta concreta que no contradiga el veredicto (si ya se dijo que es verdad, no preguntes si es mito).
- hashtags: 5 a 7, minúscula y sin tildes, siempre #futbol y #futbolargentino más los del tema (#mundial, #seleccionargentina, #premierleague, #mitos, #historiasdelfutbol...).
- miniatura: linea1 (máximo 4 palabras) y linea2 (máximo 3) para la tapa del diario; miniatura.foto: el nombre del protagonista principal tal como figura en Wikipedia (es la foto de la tapa del diario que abre el video; si es un equipo, su estadio); miniatura.dato: el dato corto y grande de la apertura del video (máximo 14 caracteres): el resultado ("3 – 1"), el número del récord ("13 GOLES"), la cifra ("US$ 300.000"), el precio del pase ("100 PELOTAS"), la fecha del partido ("SÁB 21/11"), "CAMPEÓN 2026" o el año ("1986"). miniatura.prompt: la ilustración más impactante, en inglés, con las mismas reglas.
- veredicto: solo en Mitos, uno de VERDAD, MITO, A MEDIAS o NUNCA SE PROBÓ. En las demás series, vacío.
- fuentes: de dónde salen los hechos (por ejemplo "Wikipedia: Branco" o "football-data.org").

FORMATO DE RESPUESTA
Respondé SOLO con un JSON válido con esta forma exacta:
{
  "titulo": "...",
  "descripcion": "...",
  "hashtags": ["#...", "#..."],
  "miniatura": { "linea1": "...", "linea2": "...", "emoji": "...", "foto": "...", "dato": "...", "prompt": "..." },
  "veredicto": "",
  "fuentes": ["..."],
  "escenas": [ { "texto_voz": "...", "texto_pantalla": "...", "foto": "", "prompt": "...", "broll": [], "emoji": "..." } ]
}
