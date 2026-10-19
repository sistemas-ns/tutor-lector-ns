# Esquema del dataset (JSONL)

Un diálogo por línea, JSON válido. Archivos UTF-8 sin BOM.

```json
{
  "id": "es-0001",
  "idioma": "es",
  "nivel": "inferencial",
  "situacion": "respuesta superficial",
  "fuente": "docente",
  "system_ref": "socratico-es-v1",
  "texto": "Fragmento usado en la sesión (3-10 líneas).",
  "messages": [
    {"role": "user", "content": "primer mensaje del estudiante"},
    {"role": "assistant", "content": "turno del tutor"},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

## Campos

| Campo | Valores | Notas |
|---|---|---|
| `id` | `es-0001`, `en-0001`, ... | Único en todo el dataset; prefijo = idioma |
| `idioma` | `es` / `en` | Idioma de la tutoría |
| `nivel` | `literal` / `inferencial` / `critico` | Nivel predominante trabajado |
| `situacion` | texto libre corto | Situación de la guía de anotación que cubre |
| `fuente` | `docente` / `sintetico` / `real` | `real` solo seudonimizado y autorizado |
| `system_ref` | nombre del prompt en `prompts/` | El texto completo se inyecta al entrenar |
| `texto` | string | Fragmento leído; sin derechos de terceros |
| `messages` | lista role/content | Alterna `user` (estudiante) y `assistant` (tutor); empieza con `user` y termina con `assistant` |

## Composición al entrenar

El script de entrenamiento arma cada ejemplo así:

1. `system` = contenido del prompt referido por `system_ref`.
2. Primer `user` = `"TEXTO:\n" + texto + "\n\nESTUDIANTE: " + messages[0].content`.
3. El resto de `messages` tal cual.

Así el dataset no repite el prompt de sistema en cada línea y cambiar el prompt no
obliga a regenerar el dataset.

## Validación

`python scripts/validar_dataset.py` verifica: JSON válido por línea, campos
obligatorios, valores permitidos, alternancia y cierre de roles, ids únicos, turnos del
tutor ≤ ~75 palabras, y reporta estadísticas por idioma/nivel/situación/fuente.
