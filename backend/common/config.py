from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置，从 .env 读取"""

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "quant_user"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "quant_trading"

    # 服务
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:5000"

    # 交易所
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    OKX_API_KEY: str = ""
    OKX_API_SECRET: str = ""
    OKX_PASSPHRASE: str = ""

    # 安全
    ENCRYPTION_KEY: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
