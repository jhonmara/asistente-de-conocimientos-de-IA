# Despliegue
- Construir imagen backend: `docker build -t mini-rag-api .`
- Variables importantes: `OPENAI_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`
- Exponer puerto 8000 (API) y 5173 (frontend dev) o servir estático tras `npm run build`.
