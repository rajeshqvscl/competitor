import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Default to a local SQLite file so the app runs without a real Postgres host.
    # Set DATABASE_URL in backend/.env (e.g. a Neon connection string) to use Postgres.
    database_url: str = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'local.db')}"

    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(__file__), "..", ".env"), extra="ignore")
    api_v1_prefix: str = "/api"


settings = Settings()

is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
