from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "YourEmailValidator"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_DB: str
    SMTP_SERVER: str
    SMTP_PORT: int
    LOGIN_EMAIL: str
    SENDER_EMAIL: str
    LOGIN_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus

        password = quote_plus(self.MYSQL_PASSWORD)
        return f"mysql+mysqlconnector://{self.MYSQL_USER}:{password}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
