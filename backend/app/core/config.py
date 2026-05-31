import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Explicitly load .env from project root
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env", override=True)
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)


class Settings(BaseSettings):
    app_name: str = "Nigeria Construction AI Platform"
    env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    production_domain: str = ""
    # Log silencing
    tf_enable_onednn_opts: str = "0"
    tf_cpp_min_log_level: str = "2"
    numexpr_max_threads: int = 8

    api_key: str = "change-me"
    jwt_secret: str = "change-me"
    jwt_refresh_secret: str = "change-me-refresh"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    jwt_refresh_expires_minutes: int = 10080

    # DB Config (Switched to Postgres for production-readiness)
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/construction_ai"
    redis_url: str = "redis://localhost:6379/0"

    chroma_persist_dir: str = "data/processed/vector_indexes"

    openai_api_key: str = ""
    gemini_api_key: str = ""
    gemini_default_model: str = "gemini-1.5-flash"
    groq_api_key: str = ""
    groq_default_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_default_model: str = "google/gemini-flash-1.5"
    huggingface_api_key: str = ""
    huggingfacehub_api_token: str = ""
    llm_default_model: str = "gpt-4o-mini"
    
    openweather_api_key: str = ""
    weather_cache_ttl: int = 1800

    model_registry_path: str = str(
        Path(__file__).resolve().parents[2] / "artifacts" / "models"
    )

    user_agent: str = "NigeriaConstructionAI/1.0"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        case_sensitive=False,
        protected_namespaces=("settings_",),
        extra="ignore",
    )


settings = Settings()

import os
if settings.user_agent:
    os.environ["USER_AGENT"] = settings.user_agent

# Silencing early-import noise
os.environ["TF_ENABLE_ONEDNN_OPTS"] = settings.tf_enable_onednn_opts
os.environ["TF_CPP_MIN_LOG_LEVEL"] = settings.tf_cpp_min_log_level
os.environ["NUMEXPR_MAX_THREADS"] = str(settings.numexpr_max_threads)
