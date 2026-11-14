import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

APP_NAME = "Telegram Bot Hosting Control API"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo_client = None
    app.state.db = None

    mongodb_uri = os.getenv("MONGODB_URI")
    if mongodb_uri:
        client = AsyncMongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)
        try:
            await client.admin.command("ping")
        except Exception:
            await client.close()
            raise
        app.state.mongo_client = client
        app.state.db = client["telegram_hosting"]

    try:
        yield
    finally:
        if app.state.mongo_client is not None:
            await app.state.mongo_client.close()


app = FastAPI(title=APP_NAME, version="0.2.0", lifespan=lifespan)


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    api_secret = os.getenv("API_SECRET", "")
    if not api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_SECRET is not configured. Set it in Railway Variables.",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, api_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def get_database(request: Request):
    database = request.app.state.db
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is not configured. Set MONGODB_URI in Railway Variables.",
        )
    return database


class ProjectCreate(BaseModel):
    owner_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]*$")
    runtime: str = Field(default="python", pattern=r"^python$")


class ProjectOut(BaseModel):
    id: str
    owner_id: str
    name: str
    runtime: str
    status: str
    created_at: datetime


def serialize_project(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "owner_id": document["owner_id"],
        "name": document["name"],
        "runtime": document.get("runtime", "python"),
        "status": document.get("status", "created"),
        "created_at": document["created_at"],
    }


@app.get("/")
async def root():
    return {"name": APP_NAME, "version": "0.2.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"ok": True, "service": "control-api"}


@app.get("/ping-db")
async def ping_db(request: Request):
    if request.app.state.mongo_client is None:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "message": "Set MONGODB_URI in Railway Variables."},
        )
    try:
        await request.app.state.mongo_client.admin.command("ping")
        return {"ok": True, "message": "MongoDB is reachable"}
    except PyMongoError:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "MongoDB connection failed"},
        )


@app.post(
    "/api/v1/projects",
    response_model=ProjectOut,
    dependencies=[Depends(require_api_key)],
)
async def create_project(payload: ProjectCreate, db=Depends(get_database)):
    document = {
        "owner_id": payload.owner_id.strip(),
        "name": payload.name.strip(),
        "runtime": "python",
        "status": "created",
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.projects.insert_one(document)
    document["_id"] = result.inserted_id
    return serialize_project(document)


@app.get(
    "/api/v1/projects",
    response_model=list[ProjectOut],
    dependencies=[Depends(require_api_key)],
)
async def list_projects(
    owner_id: str = Query(min_length=1, max_length=80),
    db=Depends(get_database),
):
    cursor = db.projects.find({"owner_id": owner_id}).sort("created_at", -1).limit(100)
    return [serialize_project(document) async for document in cursor]
