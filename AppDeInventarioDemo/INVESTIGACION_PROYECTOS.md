# Investigación estática de proyectos de VSC

## Alcance y método

Se completó un levantamiento estático de **81/81 raíces de primer nivel** ajenas a `AppDeInventarioDemo` que estaban dentro de `C:\Users\tomax\Desktop\VSC` en el momento de la revisión. La enumeración incluye `.github`, copias con nombres separados y carpetas vacías; no trata las copias como repositorios diferentes ni afirma que sus contenidos sean idénticos. `AITools` se excluyó deliberadamente.

Para cada raíz se observó el listado/estructura y, donde estaban presentes, manifests, README y archivos de entrada pertinentes para estimar stack y función. Se revisó código/documentación adicional de los análogos cercanos descritos abajo. **No se ejecutaron los 81 proyectos ni sus pruebas**, no se leyó contenido de `.env`, bases de datos, binarios, documentos, modelos, dependencias, cachés, logs ni artefactos de build. Una carpeta `tests` prueba su presencia, no que pase. “Sin evidencia” se refiere a los elementos inspeccionados; no descarta que la capacidad exista en otra parte.

No se copiaron archivos ni código fuente de esos proyectos a Atlas: se tomaron decisiones de arquitectura y UX a partir de sus patrones.

## Inventario de raíces revisadas

| # | Raíz de primer nivel | Evidencia estática observada y límite de la conclusión |
|---:|---|---|
| 1 | `.github` | Configuración/contenido GitHub, incluye `appmod`; no es una aplicación clasificable ni muestra un modelo de inventario. |
| 2 | `AIBetter` | `appAI.py`, `ollama_ai.py`, directorio `databases`; utilidades Python. No se confirmó API, esquema ni pruebas. |
| 3 | `Aplicacion` | `Aplicacion.py`, `.spec`, `compile_biosec.py`; utilidad Python con señal de empaquetado. No se verificó app web ni tests. |
| 4 | `AsymGame` | `index.html`, `Main.js`, `GameMechanics.js`, `src`, música y SFX; juego web JS. Sin persistencia comprobada. |
| 5 | `AsymGame - Copy` | Estructura de juego JS con `src` y recursos; copia contada como otra raíz, sin asumir igualdad de código. |
| 6 | `Battle Test` | `main.lua`, `Character.lua`, `UI.lua` y recursos; juego Lua con entidades/UI separadas. |
| 7 | `BioSec Aplicacion - Copy` | `Aplicacion.py` y reporte JSON; utilidad Python. No se observó backend web ni suite de pruebas. |
| 8 | `BusMap` | HTML/CSS/JS, servidor local `serve.py`, `data`, `scripts`; README describe mapas, rutas y horarios. No se encontró persistencia relacional. |
| 9 | `C PLUS PLUS TRAINER` | Sitio de ejercicios HTML/CSS/JS con README; no se observó proyecto compilable de C++ ni backend. |
| 10 | `Chat-AI` | SillyTavern, `package.json`, `src`, plugins, Dockerfile y manifiestos de pruebas Electron/Playwright/Jest; app extensible. |
| 11 | `ClaudeKrateroi` | Node ESM; `src/api`, `dominio`, `datos`, `motor`, `agentes`, `web`, `tests`, `docs`; README presenta API/dominio y dashboard. |
| 12 | `CodeToDiagram` | Next/React/TypeScript, parsers Tree-sitter, Docker y tests; README describe análisis en worker del navegador, exportación y descarte al recargar. |
| 13 | `colina-3d (1)` | Subcarpeta `colina-3d` con React y dependencias deck.gl/MapLibre según manifest/README; sin backend comprobado. |
| 14 | `ComicTest` | HTML, JS, CSS, `src`, docs y recursos; proyecto comic/minijuego web, sin BD comprobada. |
| 15 | `consultoria_page` | Next/React por `package.json`, `app`, `components`, `lib`, `public`; no se encontró evidencia de persistencia/backend. |
| 16 | `crm-demo` | Electron y frontend vanilla modular. README y `src/js/datos/almacen.js` describen persistencia de usuario y fallback `localStorage`; hay `validacion.js` y prueba de humo. |
| 17 | `CumplimientoDeDatos` | Directorio vacío según listado; propósito y stack no verificables. |
| 18 | `cupo-k` | Next/React por manifest; `app`, `components`, `lib`, `public`; no se comprobó backend ni persistencia. |
| 19 | `CyberPatch-Dashboard` | Dash/Plotly/pandas por README y `requirements.txt`; `app.py`, generador de datos y `data`. Dashboard con datos de ejemplo, no CRUD verificado. |
| 20 | `DemoComp` | `assets`, `downloads`, `media`, `build`; sin fuente o manifest de aplicación identificable en raíz. |
| 21 | `Derecho` | `index.html` y sitio estático; sin backend o manifest detectado. |
| 22 | `DerechoMap` | TypeScript/JS con MapLibre por manifest, `src`, `data`, `scripts`, `public`, README e `INICIAR.bat`; sin persistencia detectada. |
| 23 | `DIA.LAW` | Código Python en `Python` (`Applicaction.py`, `Database.py`, `GenerativeAI.py`); hay archivo `.db`, no leído; BD efectiva/tests no confirmados. |
| 24 | `Extensions` | Colección heterogénea; `AgenteVozJuridico` declara Fastify/Zod/dotenv con `src` y `tests`; no se asigna stack único al contenedor. |
| 25 | `firma-correo` | Herramientas Python/HTML, recursos y README para generar/previsualizar firmas; no se detectó persistencia. |
| 26 | `FocusFlow` | `Focusflow.py`, JSON de configuración/misiones y lanzadores; utilidad local Python, sin backend web comprobado. |
| 27 | `GaWD` | Juego/sitio HTML, JS, `battle-hud.html`, `js`, `assets` y README; no se observó backend. |
| 28 | `GoP` | Juego JavaScript/HTML (`gameplay.js`, `MainMenu.html`, `start.html`) y recursos; sin manifest/backend detectado. |
| 29 | `GoPGodot` | `project.godot`, addons y recursos; juego Godot, sin persistencia web comprobada. |
| 30 | `GSaS` | Escenas HTML/JS e imágenes; sin manifest, backend o persistencia detectados. |
| 31 | `GSaS2` | Juego web JS/HTML/CSS y recursos 3D; no se verificó backend ni BD. |
| 32 | `IA2` | `ApplicationRunner.py` y `databases`; propósito y uso efectivo de BD no confirmados. |
| 33 | `InstagramPrompter` | Node por `package.json`, `src`, `scripts`, `test`, README y `.env.example`; no se constató BD/despliegue. |
| 34 | `Introduction` | Proyecto visual HTML/CSS/JS con recursos y `reactor7`; sin backend comprobado. |
| 35 | `KRATEROI V1` | Next/React según manifest, `app`, `components`, `lib`, `public` y README; no se comprobó flujo full-stack. |
| 36 | `krateroi_page_framework` | Vanilla/Vite + NestJS según manifests/README; DTO/class-validator, API/IA/Telegram/colas y Compose Redis/Postgres. Módulo de BD consultado declara que aún no hay entidades/persistencia de la app. |
| 37 | `Krateroi-main` | Vanilla/Vite + NestJS, Docker/Compose, API, DTO y módulos Telegram/IA/BD/colas. README y `database.module.ts` indican que aún no guarda datos; no se detectaron tests. |
| 38 | `Krateroi-OLD` | Página HTML/JS e imagen; sin backend, manifest o persistencia detectados. |
| 39 | `krateroi-page` | Sitio HTML con `src`, `assets` e instrucciones de refactorización; sin backend comprobado. |
| 40 | `KrateroiPagina` | Estructura Vanilla/Vite y NestJS, DTOs y Compose observados; el módulo BD consultado indica que no persiste. Raíz separada, no se presume idéntica a `Krateroi-main`. |
| 41 | `MapaChile` | React/TypeScript/Vite y MapLibre por manifest, `src`, `public`, `raw_data`, `scripts`; sin BD/backend identificados. |
| 42 | `MapaChileTodo` | Mapa TS/JS con MapLibre por manifest, `src`, `data`, `scripts`, README; sin persistencia detectada. |
| 43 | `MarcaPersonal` | Sitio HTML/CSS/JS estático; sin backend/manifest observado. |
| 44 | `mecanico` | Raíz con `.vscode` y subcarpeta `mecanico`; evidencia insuficiente para inferir stack. |
| 45 | `Minesweeper` | Juego web JS/HTML/CSS con módulos de juego y recursos; no se detectó backend. |
| 46 | `MODCreator` | README/manifests describen Python/CustomTkinter, motor Java, extensión VS Code y puente WebSocket; `lib`, `tools`, `out`. |
| 47 | `n8n-local` | Docker Compose, workflows, scripts e integraciones; README. No se inspeccionaron valores de entorno ni datos. |
| 48 | `Pagina Groupon` | HTML/JS de tienda/cupones; `BaseDeDatos.js` es solo nombre observado y no demuestra BD efectiva. |
| 49 | `PaginaGolf` | Sitio estático con `index.html`, sitemap, webmanifest, README, assets/tools; sin backend detectado. |
| 50 | `PaginaPrueba2` | Astro/Node; manifest declara LibSQL, Zod/correo; README indica suscripción de doble confirmación, asistente, docs y `.env.example`. |
| 51 | `PaginaPruebaTEST` | HTML/JS/TS y dependencias Express/CORS/Nodemailer/ExcelJS; no se confirmó persistencia ni tests. |
| 52 | `PaginaTio` | Sitio HTML y subcarpeta `backend`; manifest de backend declara Express/CORS/Nodemailer; BD no comprobada. |
| 53 | `paldat` | `nes_sprite_editor.py`; utilidad Python puntual, sin manifest/tests detectados. |
| 54 | `Pause Aheader` | Juego Lua (`main.lua`) y sprites; sin backend. |
| 55 | `PeakMapper` | Preact/TypeScript/Vite/Three.js, Node, `data`, `server`, `src`, `tests`; README documenta sincronización/caché local y planificador; Vitest declarado. |
| 56 | `PhoneExtender` | Directorio vacío según listado; sin propósito/stack verificables. |
| 57 | `Ping Pong` | Juego web JS/HTML/CSS; sin backend ni persistencia detectados. |
| 58 | `Portfolio` | Sitio/portfolio HTML/CSS/JS y assets; sin backend observado. |
| 59 | `PVZ clone` | Juego Lua con módulos de cámara, enemigos, estado, mapa, torretas y oleadas; sin backend. |
| 60 | `Recetario` | HTML/CSS/JS y servidor local Node sin dependencias (`servidor.js`); README describe búsqueda/filtros/edición/importación. No se atribuye BD. |
| 61 | `Roblox` | `.luaurc`, `default.project.json`, `src`, `tools` y proyecto binario no leído; estructura Roblox/Lua. |
| 62 | `RobuxConverter` | Sitio HTML/JS/CSS, páginas temáticas, Netlify/Vercel y README; no se detectó backend. |
| 63 | `RobuxConverter - Copy` | Variante HTML/JS/CSS y README; raíz contabilizada aparte, sin manifest/backend. |
| 64 | `SoftwareCuponesDemo` | Monorepo TS con Electron/React, web, paquetes compartidos/DB, collector/servicio; docs describen SQLite, migraciones versionadas, IPC tipado y persistencia local. |
| 65 | `SpecsDetector` | Python/FastAPI/Uvicorn en `requirements.txt`, `server.py`, `monitor.py`, `fixer.py`, `static`; sin BD/tests confirmados. |
| 66 | `Sur Reclicado` | Páginas HTML/JS, recursos y directorios de plugins WordPress; no se confirmó servidor/backend activo. |
| 67 | `TBOIServer` | Scripts `.bat`/PowerShell y README; automatización, no app web identificada. |
| 68 | `TelegramGoToDoListDemo` | Node/Express, `node:sqlite`, Telegram/To Do, Compose, `src`, `data`, `web`, `android`, tests Node; README describe cola/sync y `src/db.js` tablas. |
| 69 | `test` | Un `test.py`; sin contexto suficiente para inferir más que Python. |
| 70 | `Timeless` | Juego Lua con `conf.lua`, `main.lua`, `src`, assets y README; sin backend web. |
| 71 | `Trader Agent` | Agentes/herramientas Python y scripts, README/`requirements.txt`; no se observó BD o web. |
| 72 | `Transcript-Krat` | Python con `pyproject.toml`, API/web, tests, Docker/Compose, `src`, plugins/docs/deploy; no se inspeccionaron modelos. |
| 73 | `TwitterTracker` | Electron/Node; manifest anidado declara webhook Express/SQLite; `index.html`, `renderer.js`, `preload.js` y `TwitterWebhookServer`. |
| 74 | `VNGame` | C++ por `CMakeLists.txt`, `src`, `scripts`, `tests` y recursos; sin backend/persistencia inferidos. |
| 75 | `votos` | Sitio estático HTML/CSS/JS; sin backend/manifest observados. |
| 76 | `votos - Copy` | Variante con `server.js`, `viewer.html`, `debug.html`; Node aparente, manifest/BD no confirmados. |
| 77 | `Wake Me Anywhere` | Android/Kotlin/Gradle, `app`, `installer`, `scripts`, wrapper y README; no se inspeccionaron secretos locales ni backend. |
| 78 | `Website3Dtest` | Página HTML y assets/modelos 3D no leídos; sin backend observado. |
| 79 | `Whisper-Transcriptor` | Python y dependencias en `requirements.txt`, `main.py`, audio, `queue_server.py`, plugins/dashboard; directorio de modelos excluido. |
| 80 | `wowzers` | Sitio/juego HTML/JS/CSS; sin manifest/backend/persistencia comprobados. |
| 81 | `Zuma-Sweep` | Juego web HTML/CSS/JS, README y módulos; sin backend/BD/tests detectados. |

## Análogos estudiados en más detalle

- **SoftwareCuponesDemo:** `README.md`, `docs/07-database.md`, `packages/db`, `packages/shared`, `services/collector`, `services/web`. Aporta el ejemplo más próximo de catálogo persistente, SQLite, migraciones y contratos compartidos.
- **TelegramGoToDoListDemo:** `README.md`, `src/db.js`, `src/parser.js`, `src/store.js`, `src/sync.js`, `test/`. Muestra persistencia, pruebas de almacén y separación entre lógica de negocio/sync.
- **crm-demo:** `README.md`, `src/README.md`, `src/js/datos/almacen.js`, `src/js/lib/validacion.js` y prueba de humo. Aporta organización vanilla, almacenamiento local y validación.
- **Krateroi-main, KrateroiPagina, krateroi_page_framework:** README, controladores/API, DTOs y módulo de base de datos. Aportan separación de interfaz, gateway y validación, con un límite importante: el módulo de BD consultado declara que aún no implementa almacenamiento del producto.
- **Recetario:** README y `servidor.js`; aporta un catálogo local con búsqueda, filtros, edición e importación, sin evidencia suficiente para atribuirle persistencia de BD.
- **BusMap, PeakMapper, CyberPatch-Dashboard:** README, manifests y carpetas de datos/tests. Aportan patrones de dashboard, filtro/mapa, sincronización o caché; no se tomaron como evidencia de CRUD de inventario.
- **ClaudeKrateroi, CodeToDiagram, PaginaPrueba2, MODCreator:** README/manifests/tests relevantes para capas API/dominio, procesamiento local, validación, despliegue y división por subsistema; no son análogos de inventario.

## Decisiones aplicadas a Atlas

1. **Persistencia verificable:** SQLite y esquema versionado siguen el patrón de `SoftwareCuponesDemo`; un almacén real evita presentar datos volátiles como si se guardaran.
2. **Fronteras simples:** API local, lógica de inventario y acceso de datos están separados, combinando el patrón API/validación visto en Krateroi con un almacén que sí persiste.
3. **Reglas de negocio en servidor y BD:** restricciones para SKU, cantidades, ventas e idempotencia impiden depender solo de validaciones del navegador.
4. **Pruebas centradas en reglas:** HTTP, concurrencia, integridad, historial valorizado y exportación cubren riesgos propios de inventario más relevantes que copiar suites de UI no relacionadas.
5. **Límite explícito:** se sirve únicamente en loopback; la persistencia es un único archivo local sin autenticación. No se presenta como SaaS/multiusuario/producción ni se recomienda almacenar datos sensibles.

**Trazabilidad de la revisión:** resumen estático de las 81 raíces y sus observaciones disponible en el historial de trabajo; los nombres y hechos anteriores son el alcance comprobado. Los proyectos no se arrancaron ni se auditaron exhaustivamente archivo por archivo.
