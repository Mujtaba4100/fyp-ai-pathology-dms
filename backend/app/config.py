from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    # FastAPI
    APP_NAME: str = os.getenv("APP_NAME", "EMR System")
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"

    # JWT & Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Hugging Face Serverless Inference Engine
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    HF_MODEL: str = os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct")

    # PostgreSQL (for text extraction + embeddings)
    # If provided, this is the primary connection string (e.g., Neon hosted Postgres).
    # When set, it overrides the POSTGRES_* settings below.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "emr_system")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")

settings = Settings()
