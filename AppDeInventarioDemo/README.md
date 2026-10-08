# Atlas · Control de inventario

Demo full-stack de Krateroi para administrar un catálogo, existencias y movimientos con una interfaz web y persistencia SQLite local. La aplicación no necesita paquetes externos: usa HTML/CSS/JavaScript nativos y Python 3.11+ (biblioteca estándar).

## Iniciar en Windows

1. Instala Python 3.11 o superior y asegúrate de tener `py` o `python` en PATH.
2. Ejecuta `run-atlas.bat` o, desde esta carpeta, `python -m backend`.
3. Abre <http://127.0.0.1:8765/>. Mantén la ventana del servidor abierta mientras usas la aplicación.
4. Para detener el servidor, pulsa `Ctrl+C`.

El primer inicio crea `backend\data\inventory.sqlite3`, instala el esquema y carga un conjunto reproducible de demostración. El servidor sirve la interfaz y la API desde el mismo origen, y escucha solo en `127.0.0.1`. Si el puerto predeterminado está ocupado, inicia con `run-atlas.bat --port 8766` y abre el puerto indicado.

## Funcionalidad

- Tablero con valoración del inventario al costo, valor potencial de venta, ventas de los últimos 30 días, margen bruto, indicadores de stock y tendencia mensual.
- Catálogo con búsqueda sin distinción de mayúsculas ni acentos, categoría, estado, archivo reversible, edición y paginación.
- Registro transaccional de compras, ventas y ajustes; las salidas no pueden dejar stock negativo y cada movimiento conserva el costo y precio vigentes al registrarse.
- Protección frente a reintentos de movimientos mediante claves de idempotencia.
- Historial filtrable y exportación CSV UTF-8 que neutraliza fórmulas de hojas de cálculo.
- Supuestos económicos editables y persistentes en SQLite, con equilibrio, contribución, escenarios de clientes y recuperación simple.
- Reinicio explícito de datos demo, controles de integridad y script de copia coherente de la base mientras el servidor sigue activo.

## Persistencia y operación

- Base por defecto: `backend\data\inventory.sqlite3`. Se puede cambiar con `ATLAS_DATABASE` o `--database`.
- El esquema es versionado (`PRAGMA user_version`); el servidor conserva el historial y rechaza una base creada por una versión futura.
- Para crear una copia online, ejecuta `python -m backend.backup`. La copia queda en `backups\` con fecha. También se admite `--database RUTA` y `--output RUTA`; no se sobrescriben archivos existentes.
- Para restaurar una copia, detén el servidor y sustituye el archivo activo por la copia verificada; luego vuelve a iniciarlo. Conserva otra copia del archivo anterior hasta verificar el arranque.
- Ejecuta las pruebas automatizadas con `python -m unittest discover -s backend\tests -v`.

## Seguridad y alcance

La API valida entradas, restringe el host/origen, limita el tamaño del cuerpo y emite cabeceras de seguridad. Aun así, este es un prototipo local **sin autenticación, autorización multiusuario, cifrado, auditoría de acceso ni operación de producción**. No lo enlaces a una IP pública o de red, no lo uses con información sensible/real y restringe el acceso a la carpeta y a sus copias. El archivo SQLite no está cifrado.

Los importes son CLP nominales. Una venta estima ingresos al precio de lista; no integra POS, facturación, IVA, pagos ni proveedores. El modelo financiero es hipotético, no cotización ni garantía. Consulta [`INFORME_ECONOMICO.md`](INFORME_ECONOMICO.md) y [`INVESTIGACION_PROYECTOS.md`](INVESTIGACION_PROYECTOS.md).

## Estructura

```text
index.html / styles.css / app.js    interfaz responsive
backend/server.py                   HTTP localhost y API JSON
backend/inventory.py                validación, reglas, reportes y operaciones
backend/database.py / schema.sql    SQLite, migración inicial y datos demo
backend/tests/                      pruebas HTTP, concurrencia e integridad
backend/backup.py                   copia online verificable
```
