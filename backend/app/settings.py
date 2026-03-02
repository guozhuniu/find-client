from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "sqlite:///backend/data/app.db"


settings = Settings()

