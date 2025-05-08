from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Google ADK API key
    api_key: str = None
    
    # Base URL for the API
    base_url: str = "http://localhost:8000"
    
    # Qdrant settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()