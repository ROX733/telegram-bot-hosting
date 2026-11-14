# Telegram Bot Hosting Platform

Initial FastAPI control-plane API for a Telegram bot hosting platform, using MongoDB Atlas.

## Current stage

The API currently supports:
- `GET /` service information
- `GET /health` Railway health check
- `GET /ping-db` MongoDB connectivity check
- `POST /api/v1/projects` create project metadata (requires `X-API-Key`)
- `GET /api/v1/projects?owner_id=...` list project metadata (requires `X-API-Key`)

**Important:** This is still only the control API scaffold. It does not yet accept uploads, store Telegram bot tokens, or execute users' bot code. Do not submit real bot tokens or user files until those features and isolated runtimes have been implemented.

## Railway configuration

Deploy this repository to Railway. In the API service's Variables, configure:

- `API_SECRET`: a long random secret generated privately. Never commit or share it.
- `MONGODB_URI`: your MongoDB Atlas connection string, stored only as a Railway variable.

Example URI shape (replace placeholders in Railway, not in this file):

```
mongodb+srv://DB_USERNAME:DB_PASSWORD@YOUR_CLUSTER.mongodb.net/?appName=YOUR_APP
```

In MongoDB Atlas, create a database user and allow network access from the Railway service. For initial connectivity testing, Atlas network access rules must permit the Railway outbound connection; prefer a restricted allowlist where practical. Never put the real URI in GitHub.

Railway uses `railway.json` to start Uvicorn and health-check `/health`. After setting variables, redeploy if Railway does not automatically redeploy.

## API example

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

## Security and next development stages

- Keep all credentials in Railway Variables, not source code.
- The repository may be public, so assume everything committed here is publicly readable.
- Never log Telegram bot tokens or MongoDB credentials.
- Before accepting public uploads, implement authenticated TBC requests, upload validation, per-user quotas, premium entitlement checks, encrypted token storage, abuse controls, and isolated per-bot execution.
- Never execute untrusted uploaded Python code inside this API service or its shared process.
- The planned free tier is one bot per user; additional bots require an active premium entitlement. This limit must be enforced by the backend, not only by TBC menu buttons.
