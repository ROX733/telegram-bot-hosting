# Telegram Bot Hosting Platform

Initial control-plane API for a Telegram bot hosting platform.

## Current stage

This repository currently contains the first FastAPI control API scaffold. It can:
- expose a health endpoint at `/health`
- create project metadata records
- list project records by owner ID
- use PostgreSQL on Railway (or SQLite for local development)

**This stage does not execute uploaded bot code yet.** Bot execution will be added only after the deployment/isolation design is configured. Do not upload third-party code or real bot tokens at this stage.

## Deploy on Railway

1. Create a new Railway project and deploy this GitHub repository.
2. Add a PostgreSQL database service to the same Railway project.
3. In the API service Variables, set:
   - `API_SECRET`: a long random secret (keep it private)
   - `DATABASE_URL`: reference Railway PostgreSQL's `DATABASE_URL` variable
4. Railway uses `railway.json` to start Uvicorn and health-check `/health`.

## API

- `GET /` — service information
- `GET /health` — health check
- `POST /api/v1/projects` — create project metadata (requires `X-API-Key`)
- `GET /api/v1/projects?owner_id=...` — list project metadata (requires `X-API-Key`)

Example create request:

```http
POST /api/v1/projects
Content-Type: application/json
X-API-Key: YOUR_API_SECRET

{
  "owner_id": "telegram-user-id",
  "name": "My test bot",
  "runtime": "python"
}
```

## Security notes

- Never commit `.env`, bot tokens, API keys, or credentials.
- Keep the GitHub repository private.
- Use Railway Variables for secrets.
- Never run untrusted uploaded Python code inside this API service.
- Before accepting public users, add per-user authentication, quotas, abuse controls, and isolated execution services.
