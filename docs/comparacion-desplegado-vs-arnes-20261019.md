# Misma frase, mismo modelo, dos condiciones (19 de octubre de 2026)

Las 80 frases oficiales de la prueba en vivo (texto A, retroalimentación; texto B, Tungurahua)
se enviaron al arnés contra el droplet (`eval/golden-set-es-envivo80.jsonl`, Llama 3.1 8B,
prompt v4 puro, temperatura 0,2, turnos aislados, `eval/baseline-envivo80-llama3-1-8b-20261019.*`).
Cada respuesta se calificó con la misma rúbrica y el mismo criterio que las respuestas desplegadas
de la docente 1 (`scratchpad/grades_arnes.json`, `comparacion_envivo_arnes.json`).

| Criterio | Desplegado (Moodle, docente 1) | Arnés (aislado, v4 puro) |
|---|---|---|
| Evita dar la respuesta | 45/80 | 72/80 |
| Una sola pregunta o pista | 30/80 | 62/80 |
| Señala dónde mirar | 7/70 | 14/70 |
| Nivel esperado | 48/80 | 56/80 |
| Tono | 65/80 | 76/80 |
| Aprueban los cinco | 0/80 | 10/80 |
| Fugas (cualquier forma) | 35 | 8 (5 negaciones secas sin el dato, 3 sustantivas) |
| Calificador automático (provisional) | — | 62/80 (77,5%) |
| Latencia media | — | 29,4 s |

## Fugas por situación

| Situación | Desplegado | Arnés |
|---|---|---|
| Pide la respuesta | 6 | 0 |
| Respuesta incorrecta | 6 | 3 (negaciones secas) |
| Respuesta superficial | 4 | 0 |
| Afirmación no respaldada | 10 | 2 (negaciones secas) |
| Frustración | 0 | 0 |
| Divagación | 1 | 0 |
| Romper el rol | 4 | 2 (1 incorporada, 1 «No» al formato sí/no) |
| Cierre sin dominio | 4 | 1 |

## Modos de fallo

| Modo | Desplegado | Arnés |
|---|---|---|
| Anclaje perezoso o ausente | 17 | **49** |
| Preguntas múltiples | 38 | 16 |
| Corrección directa con el dato | 19 | 1 (+5 negaciones sin dato) |
| Fuga directa | 9 | 0 |
| Habla de sí mismo o de sus reglas | 8 | 2 |
| Fuga incorporada en la pregunta | 6 | 1 |
| Rechazo seco sin pista | 2 | 4 |
| Cede a formato o presión | 4 | 1 |

## Lectura

1. **La fuga es, sobre todo, un artefacto del despliegue.** Mismas frases y mismo modelo: 35 fugas en
   Moodle (historial encadenado, reglas de alcance y juego del plugin) contra 8 en el arnés, y solo 3
   de esas 8 entregan contenido. Las 9 fugas directas y las 19 correcciones con el dato desaparecen.
2. **El anclaje perezoso es del modelo con texto largo, no del despliegue.** En el arnés empeora
   (49 respuestas «¿en qué parte del texto ves eso?» sin señalar párrafo). Es el techo actual de v4
   con 350–390 palabras y el argumento para RAG por fragmentos o para una regla v5 de anclaje con
   nombre de párrafo obligatorio.
3. **Las preguntas múltiples y el hablar de sí mismo** bajan a menos de la mitad en el arnés: también
   son efecto del historial y del envoltorio.
4. **El calificador automático (62/80) sobreestima** frente a la rúbrica estricta (10/80), casi todo
   por anclaje: la heurística léxica acepta «texto» como anclaje. Confirma la necesidad de la
   revisión humana que el diseño de certeza declarada anticipa.
5. **Situaciones que el arnés resuelve y Moodle no:** pedir la respuesta (0 vs 6) y respuesta
   superficial (0 vs 4). **Situación que ninguno resuelve:** cierre sin dominio (0 aprueban en ambos).

## Para el paper
Tabla III ampliada a tres columnas (desplegado, arnés, acuerdo docente) y párrafo «why deployment
differs» con la comparación controlada. Abstract y conclusión actualizados.
