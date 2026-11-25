from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    vercel: bool = False  # Vercel sets VERCEL=1
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    lookback_hours: int = 24


settings = Settings()
