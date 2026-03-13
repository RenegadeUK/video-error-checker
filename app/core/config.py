import os


class Settings:
    app_name: str = "Video Error Checker"
    web_port: int = int(os.getenv("WEB_PORT", "8080"))
    postgres_db: str = os.getenv("POSTGRES_DB", "video_checker")
    postgres_user: str = os.getenv("POSTGRES_USER", "video_checker")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "video_checker")
    postgres_host: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
