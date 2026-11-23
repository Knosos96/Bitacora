from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(BASE_DIR / 'bitacora.db').as_posix()}"
    secret_key: str = "dev-inseguro-cambiar"
    zona_horaria: str = "America/Bogota"
    token_horas: int = 12
    seed_super_correo: str = "superusuario@zgroup.com"
    seed_super_nombre: str = "Superusuario ZGROUP"
    seed_super_clave: str = "SuperSegura123"


settings = Settings()
