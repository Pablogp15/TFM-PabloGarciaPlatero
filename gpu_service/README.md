# Servicio local Qwen-Image-Edit-2511

Servicio FastAPI en Windows, separado del backend Docker. Mantiene el pipeline
DiffSynth cargado, usa CUDA con offload a disco/CPU y serializa inferencias para
la RTX 4060 de 8 GB. Conserva `edit_image_auto_resize=True` y `zero_cond_t=True`.

## Arranque desde Anaconda Prompt

```cmd
conda activate qwen2511
cd /d C:\Users\pablo\TFM\minipaintAI
powershell -NoProfile -File .\scripts\run_gpu_service.ps1
```

Después inicia `docker compose up -d --build` en otra terminal. La alternativa
`powershell -NoProfile -File .\scripts\start-local.ps1` gestiona ambos procesos.
Cada lanzador comprueba el puerto antes de cargar Qwen. No uses `--reload` ni
varios trabajadores Uvicorn: cada proceso cargaría su propio modelo.

La configuración común está en `scripts/local-config.ps1`: terminal, `.env`,
valores predeterminados, por ese orden. Las rutas relativas se resuelven contra
`minipaintAI`, independientemente del directorio desde el que se invoque el script.

| Variable | Valor predeterminado / origen |
|---|---|
| `MINICONDA_ROOT` | `..\miniconda3` |
| `GPU_CONDA_ENV` | `qwen2511` |
| `MINICONDA_PYTHON` | Opcional: intérprete completo, preferente sobre los anteriores |
| `DIFFSYNTH_MODEL_BASE_PATH` | `..\AI\qwenImageEdit\models` |
| `GENERATION_SERVICE_URL` | `http://host.docker.internal:8188` desde Docker |
| `GENERATION_SERVICE_TOKEN` | Obligatorio, secreto aleatorio de al menos 32 caracteres |
| `GENERATION_MODEL_NAME` | `Qwen-Image-Edit-2511` |
| `GPU_SERVICE_HOST` | `0.0.0.0`, accesible desde Docker |
| `GPU_PRELOAD` | `true` |
| `GPU_MAX_INPUT_BYTES` | `10485760` |
| `GPU_RESULT_TTL_SECONDS` | `900` |

El lanzador traduce el token a `GPU_SERVICE_TOKEN`, el modelo a `GPU_MODEL_NAME`
y obtiene `GPU_SERVICE_PORT` de la URL. No imprime secretos. Para el trabajador
nativo Windows usa `GENERATION_SERVICE_URL=http://127.0.0.1:8188`.

## Contrato interno

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/healthz` | `status`, modelo `loading/ready/error` y trabajo activo |
| POST | `/v1/jobs` | `202`, `job_id` |
| GET | `/v1/jobs/{id}` | Estado, etapa, porcentaje y métricas |
| GET | `/v1/jobs/{id}/result` | PNG con `Cache-Control: no-store` |
| POST | `/v1/jobs/{id}/cancel` | Solicita cancelación cooperativa |

Todos los endpoints `/v1/*` exigen `X-Internal-Token`. El JSON de creación
contiene `source_image_b64`, `prompt`, `negative_prompt`, `num_inference_steps`,
`width`, `height` y `seed`. No hay acceso directo a rutas de archivos del cliente.

El cuerpo HTTP se limita a 14 MiB antes de deserializar, incluyendo peticiones
por fragmentos. La imagen decodificada se limita a 10 MiB, 4096 px por lado y
24 MP, JPEG/PNG/WebP; se valida por contenido, se aplica orientación EXIF y se
recodifica sin metadatos. El prompt debe contener texto tras quitar espacios.

Durante carga se devuelve `503` con `X-GPU-Retryable: true`; ante ocupación,
`429`. Son las únicas respuestas de admisión que el trabajador reintenta. Un
fallo de carga devuelve `503` sin esa cabecera. La cancelación cambia el estado
visible pero mantiene la reserva GPU hasta que termine el hilo. No publica
resultados tardíos de trabajos cancelados. El resultado temporal en memoria
se limpia en la siguiente admisión tras su TTL; la copia persistente está en
el almacenamiento del backend.

## Comprobaciones y diagnóstico

El arranque ejecuta `python -m gpu_service.preflight` para verificar fragmentos
de pesos e índices, processor, dependencias y CUDA sin cargar Qwen. También
imprime versiones y revisión DiffSynth para registrar el entorno de ejecución.

Entorno verificado el 8 de noviembre de 2026:

- Python 3.11.17, torch 2.6.0+cu124, transformers 4.57.1.
- FastAPI 0.162.0, Uvicorn 0.54.0, Pydantic 2.14.2, Pillow 12.3.0.
- DiffSynth-Studio: `974cfa37f27ac55eba3b6d10efa21f876900572d`.

`requirements.txt` fija las dependencias web verificadas. No instales las del
backend en `qwen2511` ni actualices torch/transformers durante el arranque.
Conserva el entorno existente; para reproducirlo, registra además
`conda list --explicit` en un archivo local, sin publicar URLs con credenciales.

Si aparece `ModuleNotFoundError: diffsynth` tras mover carpetas, desde
`qwen2511` ejecuta:

```cmd
cd /d C:\Users\pablo\TFM\AI\qwenImageEdit\DiffSynth-Studio
python -m pip install -e . --no-deps
```

Si faltan pesos, corrige `DIFFSYNTH_MODEL_BASE_PATH`; no se descargan durante el
arranque. Si CUDA falla, verifica que el intérprete configurado sea el de
`qwen2511`. Si se ocupa el puerto, detén la instancia anterior antes de iniciar
otra. Si Docker no conecta, comprueba `/healthz` desde el trabajador y las
reglas locales de red; no desactives el cortafuegos.

## Pruebas sin GPU

Desde `backend`, ejecuta `.venv\Scripts\python.exe -m pytest`. Las pruebas
`test_gpu_service.py` sustituyen solo la inferencia: cubren la API ASGI real,
validación, carga única, exclusión tras cancelación y adaptador HTTP.
Las de PostgreSQL necesitan `TEST_DATABASE_URL` apuntando a una base exclusiva
de pruebas: las fixtures recrean sus tablas. Nunca uses la base de la aplicación.
