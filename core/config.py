import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv(override=True)

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

    # Supabase Storage Configurations
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")

    # Auth configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET")

settings = Settings()

# Validation list of required configuration variables
required_vars = {
    "DATABASE_URL": settings.DATABASE_URL,
    "GEMINI_API_KEY": settings.GEMINI_API_KEY,
    "SUPABASE_URL": settings.SUPABASE_URL,
    "SUPABASE_KEY": settings.SUPABASE_KEY,
    "JWT_SECRET": settings.JWT_SECRET,
}

missing_vars = [var for var, value in required_vars.items() if not value]


