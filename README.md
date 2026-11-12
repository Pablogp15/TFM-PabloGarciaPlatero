# MiniPaint AI

Plataforma web para el pintado de miniaturas que combina inventario de pinturas,
generación de imágenes con inteligencia artificial y guías paso a paso adaptadas
a las pinturas que el usuario posee.

Este repositorio contiene el desarrollo del Trabajo de Fin de Máster.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic |
| Base de datos | PostgreSQL 16 + pgvector |
| Infraestructura | Docker Compose |

## Estructura

```
.
├── backend/            # API, modelos y migraciones
│   ├── app/
│   │   ├── api/        # routers de la API v1
│   │   ├── core/       # configuración y seguridad
│   │   ├── data/       # catálogo inicial empaquetado
│   │   ├── db/         # base declarativa y sesiones
│   │   ├── models/     # 14 tablas del dominio
│   │   ├── schemas/    # contratos de entrada y salida
│   │   ├── scripts/    # comandos de administración
│   │   ├── services/   # lógica de negocio
│   │   └── storage/    # abstracción y backend local de imágenes
│   ├── alembic/        # migraciones
│   └── tests/
├── frontend/           # SPA
├── infra/              # inicialización de la base de datos
└── docker-compose.yml
```

## Puesta en marcha local: Anaconda Prompt y Docker

En una **Anaconda Prompt**, inicia el servicio Qwen y mantén esa terminal abierta:

```cmd
conda activate qwen2511
cd /d C:\Users\pablo\TFM\minipaintAI
powershell -NoProfile -File .\scripts\run_gpu_service.ps1
```

El lanzador lee la configuración con precedencia **variables de la terminal >
`.env` > valores predeterminados**, comprueba CUDA, dependencias, pesos locales y
que el puerto esté libre. Carga el modelo una vez, con un trabajador y sin
recarga automática. No reinstala paquetes ni descarga pesos. Espera a que
`http://localhost:8188/healthz` indique `"model":"ready"`.

En otra terminal, desde esta carpeta:

```powershell
docker compose up -d --build
```

La web está en [http://localhost:8080](http://localhost:8080) y la API en
[http://localhost:8000/docs](http://localhost:8000/docs). El servicio `migrate`
aplica las migraciones existentes y carga el catálogo de forma idempotente.
Para detener: `docker compose down` y `Ctrl+C` en la terminal Qwen. Los volúmenes
se conservan.

Si aún no tienes `.env`, copia `.env.example` y reemplaza sus secretos. Valores
habituales (rutas relativas a `minipaintAI`, también se admiten absolutas):

```dotenv
MINICONDA_ROOT=..\miniconda3
GPU_CONDA_ENV=qwen2511
DIFFSYNTH_MODEL_BASE_PATH=..\AI\qwenImageEdit\models
GENERATION_PROVIDER=http
GENERATION_SERVICE_URL=http://host.docker.internal:8188
```

`MINICONDA_PYTHON` permite indicar el intérprete exacto. El lanzador utiliza ese
intérprete o el de `MINICONDA_ROOT\envs\GPU_CONDA_ENV`, aunque se invoque desde
otro entorno. `GENERATION_SERVICE_TOKEN` debe ser un secreto aleatorio de al
menos 32 caracteres y se comparte únicamente entre trabajador y servicio GPU.
Si ejecutas también el trabajador directamente en Windows, cambia su URL a
`http://127.0.0.1:8188`.

### Generar desde la web

1. Inicia sesión y abre un proyecto.
2. Sube la foto en «Imágenes» con tipo «Imagen de origen».
3. En «Generar con IA», selecciona esa foto y escribe el prompt, o usa «Crear
   prompt con el proyecto» para obtener una propuesta editable con los datos y
   colores guardados. El esquema no se envía automáticamente: revisa el prompt.
4. Para reproducir la prueba inicial, elige «Borrador»: 768 × 768 y 20 pasos;
   escribe `42` como semilla.
5. Pulsa «Generar imagen». El progreso y el resultado aparecerán en el proyecto;
   el resultado permanece disponible después de recargar la página.

El backend guarda un trabajo en PostgreSQL. Un trabajador envía imagen y
parámetros por HTTP a Qwen, consulta el progreso y almacena el PNG validado.
El navegador nunca recibe el token interno ni accede directamente al servicio
GPU. Las imágenes y prompts se procesan en este equipo.

Solo se ejecuta una inferencia simultánea. Al cancelar, el modelo termina el
paso actual antes de liberar la GPU. Una nueva petición espera si el servicio
está ocupado o cargando, dentro del límite total de 1800 segundos. Una
interrupción de red o una respuesta ambigua al enviar no provoca reenvíos
automáticos que puedan duplicar la generación.

El puerto GPU escucha en `0.0.0.0:8188` para permitir el acceso desde Docker;
los endpoints `/v1/*` exigen token. No abras ese puerto al exterior. nginx
publica únicamente la aplicación y su API autenticada.

### Alternativa: lanzador único

```powershell
.\scripts\start-local.ps1
```

Inicia Qwen, espera al modelo y levanta Compose. `Ctrl+C` detiene ambos. No lo
uses mientras el servicio independiente ocupe el puerto; el lanzador rechazará
ese arranque para evitar una segunda instancia. Más detalles, diagnóstico y
versiones verificadas en [gpu_service/README.md](gpu_service/README.md).

## Desarrollo local sin Docker

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

alembic upgrade head
python -m app.scripts.seed_catalog
uvicorn app.main:app --reload
```

> En Windows, psycopg asíncrono no admite el `ProactorEventLoop`. Con
> `--reload` uvicorn usa un bucle compatible; si arrancas sin recarga, añade
> `--loop asyncio:SelectorEventLoop`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Base de datos

### Roles

- `minipaint_migrator`: propietario del esquema. Solo lo usa Alembic.
- `minipaint_app`: rol de la aplicación. Puede leer y escribir filas, pero no
  crear tablas ni truncarlas.

El rol de aplicación se crea en `infra/db/init/01-app-role.sh`, que se ejecuta
una única vez al inicializar el volumen de PostgreSQL.

### Migraciones

```bash
cd backend
alembic upgrade head       # aplicar
alembic downgrade base     # revertir todo
alembic current            # versión aplicada
alembic upgrade head --sql # ver el SQL sin conectar
```

Las migraciones están divididas en cuatro revisiones:

| Revisión | Contenido |
|---|---|
| `0001_extensions` | Extensión `vector` (pgvector) |
| `0002_core` | Usuarios, catálogo, inventario y proyectos |
| `0003_ai` | Generaciones, guías, progreso y corpus RAG |
| `0004_wishlist` | Deseados separados e indicador de poca cantidad; migra los datos existentes |

### Modelo de datos

| Grupo | Tablas |
|---|---|
| Identidad | `users`, `refresh_tokens` |
| Catálogo, inventario y deseados | `paints`, `user_paints`, `wishlist_items` |
| Proyectos | `projects`, `project_scheme_colors`, `project_images` |
| Generación | `generations`, `generation_events` |
| Guías | `guides`, `guide_steps`, `guide_step_paints` |
| Progreso | `progress_entries` |
| Corpus RAG | `knowledge_documents` |

## Autenticación

La sesión se apoya en tres cookies y **no usa `localStorage`**:

| Cookie | Contenido | Atributos |
|---|---|---|
| `mp_access` | JWT de acceso (15 min) | `HttpOnly`, `Path=/api`, `SameSite=Lax` |
| `mp_refresh` | Token opaco de refresco (14 días) | `HttpOnly`, `Path=/api/v1/auth`, `SameSite=Lax` |
| `mp_csrf` | Token CSRF firmado con HMAC | legible por JS, `Path=/` |

- Las contraseñas se almacenan con **Argon2id** (`pwdlib`).
- Del token de refresco solo se guarda su hash SHA-256 en `refresh_tokens`.
- Cada refresco **rota** el token. Si se reutiliza uno ya rotado, se revocan
  todas las sesiones del usuario.
- Toda petición mutante exige la cabecera `X-CSRF-Token` con el mismo valor que
  la cookie `mp_csrf` (*double submit* firmado).
- La clave `SECRET_KEY` firma los JWT y los tokens CSRF. Es obligatoria y debe
  tener al menos 32 caracteres.

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/auth/csrf` | Emite o reutiliza el token CSRF |
| `POST` | `/api/v1/auth/register` | Crea la cuenta e inicia sesión |
| `POST` | `/api/v1/auth/login` | Inicia sesión |
| `POST` | `/api/v1/auth/refresh` | Rota la sesión |
| `POST` | `/api/v1/auth/logout` | Revoca el refresco y borra cookies |
| `GET` | `/api/v1/auth/me` | Usuario autenticado |

### Cliente

- `src/lib/http.ts` centraliza las peticiones con `credentials: 'include'`,
  inyecta `X-CSRF-Token` y, ante un `401`, intenta un único refresco compartido
  entre todas las peticiones concurrentes antes de reintentar.
- TanStack Query cachea la sesión (`useSession`) y se vacía al iniciar o cerrar
  sesión para no mezclar datos de usuarios distintos.
- `RequireAuth` protege las rutas privadas y redirige a `/login`.
- Nunca se guardan tokens en `localStorage` ni en el estado de React.

### Pruebas

`tests/test_auth_api.py` recorre el flujo completo contra PostgreSQL. Se omite
salvo que se defina `TEST_DATABASE_URL`:

```bash
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/minipaint_test"
pytest tests/test_auth_api.py
```

El cliente HTTP del frontend tiene pruebas unitarias con Vitest (`npm test`):
inyección de la cabecera CSRF, refresco único ante peticiones concurrentes,
reintento tras un `401` y traducción de errores.

## Catálogo e inventario

### Catálogo inicial

El catálogo se carga con un comando idempotente, no con una migración de datos:

```bash
cd backend
python -m app.scripts.seed_catalog
```

- Incluye **142 pinturas** de Vallejo (Game Color, Model Color, Xpress Color),
  Green Stuff World (Acrylic Color, Intensity Ink, Metallic Color, Fluor Color)
  y Citadel (Base, Layer, Shade, Contrast, Technical, Dry).
- La clave natural es `(brand, range_name, name)`. Repetir el comando actualiza
  los datos existentes sin duplicarlos ni cambiar su identificador, por lo que
  los inventarios siguen siendo válidos.
- Los valores hexadecimales son referencias aproximadas para mostrar y comparar
  colores; no son mediciones colorimétricas oficiales.
- Al cargar cada pintura se calculan sus coordenadas CIELAB, que permiten buscar
  colores parecidos con distancia euclídea en ese espacio.

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/paints` | Busca y pagina el catálogo (`q`, `brand`, `range_name`, `paint_type`, `finish`, `limit`, `offset`) |
| `GET` | `/api/v1/paints/facets` | Marcas, gamas, tipos y acabados para los filtros |
| `GET` | `/api/v1/paints/by-color?hex_color=RRGGBB` | Pinturas ordenadas por proximidad CIELAB al color |
| `GET` | `/api/v1/paints/{id}` | Detalle de una pintura activa |
| `GET` | `/api/v1/paints/{id}/similar` | Pinturas de color parecido ordenadas por distancia |
| `GET` | `/api/v1/inventory` | Inventario del usuario (`running_low`, `brand`, `q`, paginación) |
| `GET` | `/api/v1/inventory/stats` | Totales de pinturas propias, botes, marcas y pinturas con poca cantidad |
| `POST` | `/api/v1/inventory` | Añade una pintura; si ya existe devuelve `200` con la existente |
| `PATCH` | `/api/v1/inventory/{id}` | Actualiza cantidad, indicador `running_low` o notas |
| `DELETE` | `/api/v1/inventory/{id}` | Quita la pintura del inventario |
| `GET` | `/api/v1/wishlist` | Deseados personales paginados (`limit`, `offset`) |
| `GET` | `/api/v1/wishlist/paint-ids` | Identificadores guardados para los corazones del catálogo |
| `POST` | `/api/v1/wishlist` | Guarda `paint_id` en deseados sin duplicarlo |
| `DELETE` | `/api/v1/wishlist/{paint_id}` | Quita un deseo propio sin modificar el inventario |

- El catálogo exige sesión aunque sea información compartida.
- Todas las operaciones de inventario se acotan al usuario del token. Un
  elemento ajeno responde `404` para no revelar su existencia.
- Las escrituras exigen la cabecera `X-CSRF-Token`.

### Interfaz

- `/paints`: búsqueda, filtros por marca, gama, tipo y acabado, paginación,
  búsqueda por HEX con disco de matices y control de tonos claros/oscuros,
  pinturas ordenadas por similitud CIELAB, alta en el inventario y corazón para deseados.
- `/inventory`: estadísticas de pinturas propias, control de cantidad, botón «queda poco»,
  filtro para mostrar solo las marcadas, notas y eliminación con confirmación.
- `/wishlist`: apartado independiente de deseados; el corazón permite quitarlos y el
  botón de inventario permite registrar su posesión. Una pintura puede estar en ambas listas.
- Estas rutas están protegidas por `RequireAuth` y enlazadas desde la cabecera y
  el panel principal.

### Pruebas

```bash
cd backend
pytest tests/test_colors.py tests/test_catalog_data.py
```

`tests/test_catalog_inventory_api.py` cubre el flujo completo contra PostgreSQL
y también se omite salvo que se defina `TEST_DATABASE_URL`.

## Proyectos e imágenes

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/projects` | Lista los proyectos del usuario (`status`, `q`, paginación) |
| `POST` | `/api/v1/projects` | Crea un proyecto |
| `GET` | `/api/v1/projects/{id}` | Detalle de un proyecto propio |
| `PATCH` | `/api/v1/projects/{id}` | Actualiza nombre, tema, escala, descripción o estado |
| `DELETE` | `/api/v1/projects/{id}` | Elimina el proyecto y sus datos asociados |
| `GET` | `/api/v1/projects/{id}/scheme-colors` | Esquema de color del proyecto |
| `PUT` | `/api/v1/projects/{id}/scheme-colors` | Sustituye el esquema completo de forma atómica |
| `GET` | `/api/v1/projects/{id}/images` | Imágenes del proyecto (`kind`, paginación) |
| `POST` | `/api/v1/projects/{id}/images` | Sube una imagen (`kind` + `file`, `multipart/form-data`) |
| `GET` | `/api/v1/projects/{id}/images/{image_id}` | Sirve la imagen con sesión autenticada |
| `DELETE` | `/api/v1/projects/{id}/images/{image_id}` | Elimina una imagen y su archivo |

- Todas las operaciones se acotan al usuario autenticado. Un proyecto o una
  imagen de otro usuario responde `404` para no revelar su existencia.
- Las escrituras exigen la cabecera `X-CSRF-Token`.
- El estado `generating` está reservado al trabajador de generación de la fase 4:
  la API rechaza con `422` que el cliente lo asigne.
- Los colores del esquema deben indicar `paint_id`, `hex_override` o ambos. El
  hexadecimal se normaliza a `#RRGGBB` en mayúsculas.

### Imágenes

- Formatos admitidos: **JPEG, PNG y WebP**. Se valida el contenido real con
  Pillow, no la extensión ni el MIME declarado por el cliente.
- Límites: **10 MB**, **4096 px por lado**, **24 MP** y **50 imágenes por
  proyecto** (configurables con `MAX_UPLOAD_BYTES`, `MAX_IMAGE_DIMENSION`,
  `MAX_IMAGE_PIXELS` y `MAX_IMAGES_PER_PROJECT`).
- Antes de guardar se aplica la orientación EXIF y se recodifica la imagen para
  eliminar metadatos (EXIF, texto PNG y similares).
- La deduplicación se hace por `(project_id, checksum)`: subir el mismo contenido
  devuelve `200` con la imagen existente; una imagen nueva devuelve `201`.
- Las claves de almacenamiento tienen la forma
  `projects/{project_id}/{uuid}.{ext}` y solo se sirven a través de la API
  autenticada. No se exponen como archivos estáticos.
- `ImageStorage` abstrae el backend. La implementación actual
  (`LocalImageStorage`) escribe de forma atómica y protege frente a *path
  traversal*; se puede sustituir por MinIO o S3 sin cambiar los servicios.
- En Docker el directorio `/app/storage` se monta en el volumen `storage`. En
  desarrollo local se usa `backend/storage` (ignorado por Git).
- Al eliminar un proyecto se borran primero sus generaciones (la FK de imagen de
  origen es `RESTRICT`), después el proyecto con sus cascadas y, tras confirmar
  la transacción, los archivos del almacenamiento.

### Interfaz

- `/projects`: listado con búsqueda y filtro por estado, creación de proyectos y
  paginación.
- `/projects/:projectId`: edición de datos y estado, editor de esquema de color
  basado en rol, color y notas, subida de imágenes de origen y avance, galería y
  eliminación con confirmación.
- Ambas rutas están protegidas por `RequireAuth` y enlazadas desde la cabecera y
  el panel principal.

### Pruebas

```bash
cd backend
pytest tests/test_image_validation.py tests/test_storage_local.py
```

`tests/test_projects_api.py` cubre CRUD, propiedad, CSRF, validación, esquema de
color, deduplicación, límites, referencias de generación y limpieza del
almacenamiento. Se omite salvo que se defina `TEST_DATABASE_URL`.

## Calidad

```bash
# Backend
cd backend
ruff check .
mypy app
pytest

# Frontend
cd frontend
npm run lint
npm run format:check
npm test
npm run build
```

## Estado

Implementado: configuración, migraciones, autenticación, catálogo e inventario,
gestión de proyectos e imágenes, cola persistida de generaciones, trabajador,
integración HTTP con el servicio local Qwen-Image-Edit, cancelación, progreso y
almacenamiento de resultados. La generación real requiere configurar el entorno
Conda, CUDA y los pesos locales. El módulo RAG dispone de importación documental,
recuperación, trabajador CPU, generación estructurada y seguimiento de pasos.
La revisión experta de las recomendaciones y la evaluación con usuarios siguen
pendientes. El ensayo real detectó que validar identificadores no basta para
garantizar la corrección semántica de pinturas y citas.

## Guías y biblioteca de técnicas

```powershell
docker compose -f docker-compose.yml -f docker-compose.rag.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.rag.yml exec -T ollama ollama pull qwen3-vl:4b-instruct-q4_K_M
docker compose -f docker-compose.yml -f docker-compose.rag.yml run --rm guide-worker python -m app.scripts.import_knowledge /knowledge/manual_tecnicas_miniaturas.json --model-path /models/multilingual-e5-small --revision local-v1
```

Se necesita el codificador local en `rag_models/multilingual-e5-small`. Ollama y
los embeddings se ejecutan en CPU; el servicio de imágenes Conda sigue separado.
La migración `0005_guides_rag` añade contexto, estado y seguimiento de las guías.

- `/guides` muestra las 22 técnicas del manual con ilustraciones, ordenadas por
  dificultad; las fichas se abren en un diálogo accesible. Veladuras es avanzada.
- En cada proyecto, «Guías de pintado» utiliza una imagen guardada y las pinturas
  del inventario con cantidad positiva; excluye los deseados y advierte «queda poco».
- Los pasos guardan completado, notas y minutos; mantienen las fuentes y el
  inventario usados al generarlos. Las citas deben revisarse antes de pintar.
- Los pasos de aplicación catalogados requieren identificadores de pintura.
  Las comprobaciones de preparación pueden usar `other` sin pinturas. La
  validación no demuestra que un color descrito o una cita sean adecuados.

La importación y actualización del manual se explican en [knowledge/README.md](knowledge/README.md).
El manual asistido por IA está autorizado para el corpus local, con revisión
experta pendiente. Las pruebas conservan sus documentos sintéticos aparte.
Los ensayos reales y sus fallos se registran en `validation/rag-real-guide*.json`.
