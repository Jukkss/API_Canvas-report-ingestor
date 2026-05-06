from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Canvas Report Processor"
    app_version: str = "0.1.0"
    canvas_base_url: str = "https://pucminas.instructure.com"
    request_timeout_seconds: float = 30.0
    max_redirects: int = 10
    default_encoding: str = "utf-8"
    fallback_encoding: str = "latin1"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CANVAS_PROCESSOR_",
    )


settings = Settings()
