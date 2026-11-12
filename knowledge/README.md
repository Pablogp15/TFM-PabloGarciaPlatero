# Documentos de pintado

Coloca aquí los documentos y un manifiesto JSON por documento. No incluyas
documentos personales en control de versiones.

El manual `manual_tecnicas_miniaturas.md` es una síntesis didáctica asistida por IA,
autorizada por el usuario para su importación y pendiente de revisión práctica
experta. No es el corpus sintético reservado a las pruebas automatizadas; tampoco
constituye una validación de contenido del TFM. Su manifiesto conserva la procedencia.

La biblioteca web «Guías» se obtiene de los apartados prácticos 02–23 del mismo
manual. Al modificarlo, actualizar su versión en el JSON y regenerar el catálogo:

```powershell
backend/.venv/Scripts/python.exe scripts/export_techniques.py
cd frontend
npx prettier --write src/features/techniques/catalog.json
```

Después reconstruir el frontend e importar de nuevo el manifiesto para actualizar
la versión activa del RAG. Los cambios de nivel se leen del campo «Nivel» del texto;
si es un rango, la biblioteca utiliza la dificultad superior.

Ejemplo de manifiesto:

```json
{
  "file": "tecnicas.pdf",
  "document_key": "tecnicas-personales",
  "title": "Técnicas de pintado",
  "author": "Autor del documento",
  "source": "Procedencia del documento",
  "permission": "Uso autorizado por el titular",
  "language": "es",
  "synthetic": false
}
```

Importación después de instalar los modelos y arrancar los servicios RAG:

```powershell
docker compose -f docker-compose.yml -f docker-compose.rag.yml run --rm guide-worker python -m app.scripts.import_knowledge /knowledge/tecnicas.json --model-path /models/multilingual-e5-small --revision local-v1
```

La importación conserva versiones anteriores para mantener la trazabilidad de las
guías, pero solo recupera la versión activa. Los documentos con `synthetic: true`
se reservan para pruebas y no habilitan la generación desde la web.
