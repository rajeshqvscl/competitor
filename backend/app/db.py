import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://your_user:your_password@your-neon-host/dairy_competitor?sslmode=require"

    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(__file__), "..", ".env"), extra="ignore")
    api_v1_prefix: str = "/api"


settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
