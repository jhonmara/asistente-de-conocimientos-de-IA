
# Guía de Demo – Mini RAG Assistant (Pro)

Este guion te lleva **paso a paso** para correr y demostrar el proyecto delante de tu entrevistador.

---

## 0) Requisitos
- **OpenAI API Key** (variable `OPENAI_API_KEY`).
- **Python 3.10+** y `pip`.
- **Node 18+** (para el front con Vite).
- **Opcional:** Docker + Docker Compose (para demo con Postgres).

> Nota: El backend está listo para **SQLite por defecto** (más simple). Con Docker puedes usar Postgres.

---

## 1) Clonar / Abrir el proyecto
Si ya tienes el zip parchado, descomprímelo y entra a la carpeta raíz.

```bash
unzip mini-rag-assistant-fixed-patched.zip
cd mini-rag-assistant-fixed-check
```

Estructura clave:
```
backend/
  app/
    main.py           # API FastAPI (health, chat, ingest)
    rag/
      chunker.py      # Divide textos en chunks
      store.py        # VectorStore con FAISS + embeddings OpenAI
    db/
      models.py       # SQLAlchemy (ChatMessage, FileAsset, Note)
    tools/wiki.py     # Tool de Wikipedia
  requirements.txt
frontend/
  src/App.jsx         # UI React simple para chatear
docker-compose.yml    # Orquesta db (Postgres), api y web (Vite)
```

---

## 2) Opción A – Correr rápido (sin Docker, SQLite)

### 2.1 Backend
```bash
cd backend
cp .env.example .env
# Abre .env y pega tu OPENAI_API_KEY (y opcionalmente cambia modelos)
# DATABASE_URL=sqlite:///./app.db   # por defecto
python -m venv .venv && source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Prueba salud:
```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

### 2.2 Frontend (otra terminal)
```bash
cd frontend
npm install
npm run dev -- --host
```
Abre: http://localhost:5173 (el front llama a `http://localhost:8000`).

---

## 3) Opción B – Docker Compose (con Postgres)

```bash
# En la raíz del proyecto
cp backend/.env.example backend/.env
# Asegúrate de poner tu OPENAI_API_KEY dentro de backend/.env
docker compose up --build
```
- API: http://localhost:8000  
- Web: http://localhost:5173

> Si quieres que el backend use Postgres, edita `backend/.env`:
> ```env
> DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/ragdb
> ```

---

## 4) Demo básica (sin RAG)

**Objetivo:** validar que el chat responde.

**cURL:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Explícame qué es este proyecto en 2 líneas", "use_rag": false, "use_wiki": false}'
```

**Qué mostrar**
- Respuesta breve en español.
- Explicar que `use_rag=false` consulta solo al modelo (sin contexto).

---

## 5) Ingesta y RAG (con FAISS)

### 5.1 Crear un archivo de prueba
Crea un archivo `notas.txt` con contenido reconocible:
```
Mini RAG Assistant: Proyecto de demostración para entrevista.
Usa FastAPI, OpenAI y FAISS para recuperar contexto relevante.
Las piezas se dividen en chunks de ~800 caracteres con overlap.
```

### 5.2 Ingestar el archivo
```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@notas.txt"
```
Debe devolver algo como: `{"ok": true, "chunks": N}`.

### 5.3 Preguntar con RAG
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"¿Qué tecnologías usa el proyecto?", "use_rag": true, "use_wiki": false}'
```
**Qué destacar:**
- Verás “(Herramientas: RAG)” al final.
- Verás “Fuentes: [...] score=…” listando fragmentos recuperados.
- Explica cómo el contexto recuperado guía la respuesta.

---

## 6) Tool calling: Wikipedia

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"¿Quién es Alan Turing?", "use_rag": false, "use_wiki": true}'
```
**Qué destacar:**
- Al final: “(Herramientas: wiki)”.  
- Explica que `wiki_lookup` llama a la API pública de Wikipedia para sumar contexto.

---

## 7) Frontend (demo visual)
- Abre http://localhost:5173
- Envia un mensaje normal.
- Sube un archivo desde **cURL** (o agrega un botón en el front si deseas), y vuelve a preguntar con RAG activo desde el front (si tu App.jsx lo soporta).  
- Explica que el front usa Vite/React y que podrías desplegarlo en Vercel fácilmente.

---

## 8) Persistencia y telemetría
- Menciona que los **embeddings** y metadatos se guardan en `./data` (FAISS + JSONL).  
- Las **conversaciones** se guardan en la base (SQLite por defecto).  
- Reinicia el backend y verifica que el contexto persiste (consulta RAG nuevamente).

---

## 9) Guion de 5–7 minutos para la entrevista

1. **Arquitectura en 30s:** FastAPI (API), VectorStore FAISS + embeddings OpenAI, DB con SQLAlchemy, Front con React/Vite.
2. **Ping de salud:** `GET /api/health` → ok.
3. **Chat sin RAG (20s):** `use_rag=false` para mostrar baseline del modelo.
4. **Ingesta (40s):** subo `notas.txt` → chunks + persistencia.
5. **Chat con RAG (1m):** `use_rag=true` → muestra “Herramientas: RAG” y “Fuentes: …”. Explica chunking y scoring (cosine/IP normalizado).
6. **Tool wiki (30s):** `use_wiki=true` → integra contexto externo (Wikipedia).
7. **Persistencia (30s):** reinicio y los vectores siguen, DB guarda las conversaciones.
8. **Escalabilidad (1m):** cambiar a Postgres con Compose; reemplazar FAISS por ChromaDB si el equipo ya usa Mongo; fácil swap del `VectorStore`.
9. **Seguridad/Costos (30s):** claves en `.env`, temperatura 0.2, `text-embedding-3-small` por costo/latencia; puedes cambiar a `-large` para calidad.
10. **Roadmap (30s):** auth, uploads PDF/CSV, streaming SSE, tests, despliegue a Railway/Render.

---

## 10) Publicar en GitHub (rápido)

```bash
git init
git add .
git commit -m "feat: mini rag assistant (fastapi + openai + faiss + react)"
# crea repo vacío en GitHub y reemplaza URL debajo:
git remote add origin https://github.com/TU_USUARIO/mini-rag-assistant.git
git branch -M main
git push -u origin main
```

Tips:
- Añade badges y una sección de “Demo rápida” en el README.
- Incluye capturas de pantalla del front y un diagrama simple (Mermaid) de arquitectura.

---

## 11) Solución de problemas comunes

- **FAISS no instala** (especialmente en Windows/M1):
  - Usa Docker Compose (recomendado) o instala `faiss-cpu` con `pip install --only-binary :all: faiss-cpu`.
  - Alternativa rápida: cambiar a **ChromaDB** (persist_directory) con `pip install chromadb` y adaptar `VectorStore`.

- **401 de OpenAI**: verifica `OPENAI_API_KEY` en `.env` y reinicia.
- **CORS** desde el front: el backend ya permite `allow_origins="*"`, verifica que apuntas a `http://localhost:8000`.
- **Postgres** no arranca en compose: borra volumen `pgdata` y reinicia: `docker compose down -v && docker compose up --build`.

---

## 12) Qué resaltan los entrevistadores
- Claridad del **flujo end-to-end** (ingesta → recuperación → generación).
- Buenos **trade-offs** (simplicidad SQLite vs Postgres; costo/latencia embeddings).
- **Extensibilidad**: tools (Wiki), más stores (Chroma, Mongo), auth, observabilidad.
- **Código limpio** y explicable en 5 minutos.
