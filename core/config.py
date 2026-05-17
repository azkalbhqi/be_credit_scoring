import os

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://openpg:password@localhost:5432/credit_scoring")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AIzaSyBNmpHSuX5xmCBUd9MyQt1FxXj0PqN5iB4")

settings = Settings()
