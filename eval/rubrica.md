# Rúbrica de evaluación del tutor (conjunto dorado)

Cada caso del golden set se presenta al modelo (system prompt + texto + historial +
entrada del estudiante) y su respuesta se califica en cinco dimensiones binarias.
**Un caso se aprueba solo si cumple todas las dimensiones marcadas en sus `criterios`.**

| Dimensión | Pregunta del evaluador | Pasa si... |
|---|---|---|
| `no_da_respuesta` | ¿El turno evita entregar o confirmar la respuesta? | No aparece la respuesta ni reformulada |
| `una_pregunta_o_pista` | ¿Hay exactamente una pregunta o una pista? | Ni cuestionario ni monólogo |
| `anclaje_texto` | ¿Dirige al estudiante al texto cuando corresponde? | Cita, ubica o pide citar el pasaje |
| `nivel` | ¿La exigencia corresponde al nivel esperado del caso? | Coincide con el `nivel` del caso |
| `tono` | ¿Tono cercano, específico, sin elogio vacío ni regaño? | Juicio del evaluador |

Además, toda respuesta debe cumplir dos condiciones globales:
- **Longitud:** máximo ~75 palabras.
- **Idioma:** el del caso (en inglés se admite andamiaje breve en la lengua de apoyo).

## Procedimiento

1. Correr el golden set completo contra el modelo candidato (script en fase de arnés,
   noviembre) — mismos casos, temperatura fija, 3 repeticiones por caso.
2. Calificación: automática preliminar (modelo evaluador con esta rúbrica) + revisión
   humana de todos los fallos y de una muestra del 20% de los aprobados.
3. **Umbral de aceptación: ≥ 90% de casos aprobados en las 3 repeticiones.** Un modelo
   que no supera el umbral no se despliega, sin excepciones.
4. Todo fallo real nuevo detectado en producción se convierte en caso del golden set.

## Registro de resultados

| Fecha | Modelo | Versión prompt | Casos | Aprobados | % | ¿Pasa? |
|---|---|---|---|---|---|---|
| (pendiente) | | | | | | |
