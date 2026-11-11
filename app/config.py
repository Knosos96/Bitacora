from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://bitacora:bitacora@localhost:5432/bitacora"
    secret_key: str = "dev-inseguro-cambiar"
    zona_horaria: str = "America/Bogota"
    token_horas: int = 12


settings = Settings()
