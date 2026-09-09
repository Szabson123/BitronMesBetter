from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MSSQL
    eclipse_host: str = Field(alias="ECLIPSE_HOST")
    eclipse_user: str = Field(alias="ECLIPSE_USER")
    eclipse_password: str = Field(alias="ECLIPSE_PASSWORD")
    eclipse_database: str = Field(alias="ECLIPSE_NAME")

    # PostgreSQL
    postgres_host: str = Field(alias="DB_HOST")
    postgres_user: str = Field(alias="DB_USER")
    postgres_password: str = Field(alias="DB_PASSWORD")
    postgres_database: str = Field(alias="DB_NAME")
    postgres_port: str = Field(alias="DB_PORT")

    # MySQL
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_user: str = Field(alias="MYSQL_USER")
    mysql_password: str = Field(alias="MYSQL_PASSWORD")
    mysql_database: str = Field(alias="MYSQL_DATABASE")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()