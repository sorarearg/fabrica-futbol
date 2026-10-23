Formato: VIDEO CORTO (Reel, Short o TikTok) con voz en off e ilustraciones.

DURACIÓN
- La historia dura lo que necesite para contarse completa y bien, sin relleno: normalmente entre 20 y 55 segundos (entre 55 y 150 palabras en total). Nunca más de 150 palabras.
- Mejor una historia completa de 45 segundos que una cortada de 25. Pero cada frase tiene que ganarse su lugar: si una frase es adorno, va afuera.
- Nunca dejes la historia inconclusa ni sin el dato que la hace interesante.

ESTRUCTURA (en este orden)
1. Gancho (escena 1, máximo 14 palabras): el momento más fuerte, un nombre conocido o un dato que choque. Tiene que frenar el scroll en el primer segundo. Nunca una presentación.
2. Lo mejor antes del segundo 10 (escenas 2 y 3, más o menos las primeras 25 palabras): ya tiene que aparecer el giro, la pregunta que engancha o el dato que sorprende. La gente se va entre el segundo 7 y el 12 si no pasa nada.
3. Desarrollo: los hechos en orden, una idea por escena, cada frase empuja a la siguiente ("y ahí", "el tema es que", "pero").
4. Desenlace: cómo terminó, dicho clarísimo. La historia tiene que cerrar.
5. Cierre (última escena, corto): una frase para compartir o comentar, distinta cada vez.

ESCENAS
- Entre 6 y 16 escenas. Cada escena es UNA o dos frases cortas (de 5 a 16 palabras en total), y cada una va a tener su propia ilustración.
- texto_voz: lo que se dice, escrito para el oído. Años y números en palabras ("mil novecientos ochenta y seis").
- texto_pantalla: solo en la escena 1, el gancho para leer sin sonido (máximo 6 palabras, puede llevar el año en números). En las demás, vacío.
- prompt: descripción EN INGLÉS de la ilustración de esa escena, concreta y visual (quién, qué hace, dónde, época, luz, emoción). Reglas:
  - Nunca pongas nombres propios de personas reales en el prompt: describilas ("a 1890s Argentine police inspector with a thick mustache and a dark uniform").
  - Si un personaje aparece en varias escenas, describilo siempre igual (misma ropa, edad, rasgos) para que se lo reconozca.
  - Ambientá en la época y el lugar correctos (Argentina, la década que corresponda). Nada de objetos o lugares de otros países que no correspondan.
  - Sin texto, carteles legibles, logos ni banderas dibujadas con detalle. Nada de sangre ni violencia gráfica: sugerila con sombras o con la reacción de los personajes.
- broll: SOLO si la escena muestra un lugar real que se puede filmar hoy y que se ve igual (por ejemplo "Buenos Aires street", "La Plata cathedral", "Iguazu falls", "old typewriter"), una o dos búsquedas en inglés de 2 a 4 palabras. Si no, lista vacía: va la ilustración. La mayoría de las escenas van con ilustración.
- emoji: UN emoji común de un objeto o símbolo (sin banderas), de respaldo.

TEXTOS PARA PUBLICAR (los mismos en las 3 redes)
- titulo: MÁXIMO 40 CARACTERES contando espacios. Corto, picante, con curiosidad real y sin mentir. Rinden los que tienen nombre propio o una pregunta que pica ("La huella que la delató", "¿El primer hacker era argentino?"). Mayúscula solo al principio y en nombres propios. Sin emojis.
- descripcion: 2 o 3 frases como si le escribieras a alguien por WhatsApp, con el dato clave. La última invita a comentar con una pregunta concreta.
- hashtags: 5 a 7, en minúscula y sin tildes, siempre #argentina y #historias más los del tema (#laplata, #historiaargentina, #curiosidades, #casoreal, #leyendas, #inventos).
- miniatura: linea1 (máximo 4 palabras) y linea2 (máximo 3), para frenar el scroll en la grilla. miniatura.prompt: la ilustración más impactante de la historia, en inglés, con las mismas reglas de los prompts de escena. miniatura.emoji: un emoji.
- fuentes: lista corta de dónde salen los hechos (por ejemplo "Wikipedia: Juan Vucetich"). Si usaste el MATERIAL, nombralo.

FORMATO DE RESPUESTA
Respondé SOLO con un JSON válido con esta forma exacta:
{
  "titulo": "...",
  "descripcion": "...",
  "hashtags": ["#...", "#..."],
  "miniatura": { "linea1": "...", "linea2": "...", "emoji": "...", "prompt": "..." },
  "fuentes": ["..."],
  "escenas": [ { "texto_voz": "...", "texto_pantalla": "...", "prompt": "...", "broll": [], "emoji": "..." } ]
}
