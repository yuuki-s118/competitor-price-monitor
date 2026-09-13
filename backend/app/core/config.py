from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリ全体の設定。環境変数 / .env から読み込む(12-factor)。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Competitor Price Monitor"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/price_monitor"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "dev-only-secret-key-please-override-in-env-file-3f9a2c"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    rakuten_app_id: str = ""
    rakuten_access_key: str = ""
    rakuten_allowed_origin: str = "https://github.com"


settings = Settings()
