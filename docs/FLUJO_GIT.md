# Flujo de trabajo Git — TIENDAS S.M

Estrategia: **GitHub Flow** (ramas de corta vida que salen de `main` y vuelven por Pull Request).
Se eligió porque el MVP es pequeño, el ritmo es semanal y se quiere integrar cambios pequeños y frecuentes.

## Reglas
1. `main` es la **línea base**: está protegida y no se escribe directamente en ella.
2. Cada tarea del tablero se trabaja en su propia rama, creada desde `main` actualizada.
3. Se integra con un **Pull Request**; el PR debe tener revisión de código antes de fusionarse.
4. Se fusiona con **"Create a merge commit"** (no squash) para conservar los commits atómicos.
5. Después de fusionar, se borra la rama y se actualiza `main` local (`git pull`).

## Nombres de ramas
| Prefijo | Uso | Ejemplo |
| --- | --- | --- |
| `feature/` | funcionalidad nueva | `feature/abonos-de-credito` |
| `fix/` | corrección de un error | `fix/plazo-del-credito` |
| `refactor/` | mejora interna sin cambiar el comportamiento | `refactor/dividir-repositorio` |
| `docs/` | documentación | `docs/readme` |

## Mensajes de commit
Formato: `tipo(alcance): qué se hizo` y, si hace falta, una línea en blanco y el **por qué**.
Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`. Un commit = un cambio lógico.

## Revisión de código (checklist)
- [ ] ¿Las pruebas pasan y cubren el cambio (casos normales y de error)?
- [ ] ¿Se cumple la Definition of Done del tablero?
- [ ] ¿Nombres claros, funciones pequeñas, sin duplicación ni números mágicos?
- [ ] ¿No hay contraseñas, claves ni datos reales de clientes?
- [ ] ¿El cambio traza a una historia o requisito (HU/RF)?
- [ ] ¿La deuda técnica nueva quedó registrada en el backlog?

## Versionamiento (SemVer: MAYOR.MENOR.PARCHE)
- MAYOR: cambio que rompe la compatibilidad. MENOR: funcionalidad nueva compatible. PARCHE: corrección de error.
- Mientras el sistema esté en desarrollo inicial se usa `0.x.y`.
- Los releases se etiquetan con tags anotados (`v0.1.0`).
