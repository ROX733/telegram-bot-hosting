import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

APP_NAME = "Telegram Bot Hosting Control API"
API_SECRET = os.getenv("API_SECRET", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hosting.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(60))
    runtime: Mapped[str] = mapped_column(String(20), default="python")
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME, version="0.1.0")


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_SECRET is not configured. Set it in Railway Variables.",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, API_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ProjectCreate(BaseModel):
    owner_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]*$")
    runtime: str = Field(default="python", pattern=r"^python$")


class ProjectOut(BaseModel):
    id: int
    owner_id: str
    name: str
    runtime: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@app.get("/")
def root():
    return {"name": APP_NAME, "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"ok": True, "service": "control-api"}


@app.post("/api/v1/projects", response_model=ProjectOut, dependencies=[Depends(require_api_key)])
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        owner_id=payload.owner_id.strip(),
        name=payload.name.strip(),
        runtime="python",
        status="created",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/v1/projects", response_model=list[ProjectOut], dependencies=[Depends(require_api_key)])
def list_projects(owner_id: str, db: Session = Depends(get_db)):
    statement = select(Project).where(Project.owner_id == owner_id).order_by(Project.id.desc())
    return list(db.scalars(statement).all())
