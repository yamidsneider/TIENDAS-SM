# TIENDAS S.M

**Sistema de gestión de inventario, ventas y créditos para tiendas de barrio.**

MVP académico de *Ingeniería de Software I* (Universidad de Pamplona).
Autor: Yamid Sneider Merchan Castro.

## Tecnología
- **Python 3** (solo biblioteca estándar), **SQLite** y, más adelante, **Tkinter** para la interfaz de escritorio.
- Pruebas con `unittest`. Dinero como enteros en pesos colombianos (sin centavos).

## Cómo correr las pruebas
Desde la carpeta del proyecto:

    python -m unittest discover -s tests -v

Resultado esperado: `OK (expected failures=1)`. La falla esperada es la deuda técnica DT-02
(el vencimiento del crédito ignora el plazo del cliente) y está registrada en el backlog.

## Flujo de trabajo
Se usa **GitHub Flow**: la rama `main` está protegida y todo cambio entra por Pull Request.
Ver [`docs/FLUJO_GIT.md`](docs/FLUJO_GIT.md).

## Tablero y backlog
Tablero Kanban: <https://github.com/users/yamidsneider/projects/1>

## Estado
- Implementado: dominio, persistencia SQLite, control de inventario, control de crédito y venta a crédito (CU-01), abonos.
- Pendiente: interfaz Tkinter, lotes y vencimientos (Should Have), alertas y las entidades de CR-02.

## Uso de IA
Parte del código se generó con apoyo de IA y fue revisado por el desarrollador, que debe poder explicarlo.
No se usan datos reales de clientes en pruebas ni en herramientas de IA.
