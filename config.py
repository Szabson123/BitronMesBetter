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
    metrology_mysql_host: str = Field(default="localhost", alias="METROLOGY_MYSQL_HOST")
    metrology_mysql_user: str = Field(alias="METROLOGY_MYSQL_USER")
    metrology_mysql_password: str = Field(alias="METROLOGY_MYSQL_PASSWORD")
    metrology_mysql_database: str = Field(alias="METROLOGY_MYSQL_DATABASE")
    metrology_mysql_port: int = Field(default=3306, alias="METROLOGY_MYSQL_PORT")

    application_mysql_host: str = Field(default="localhost", alias="APPLICATION_MYSQL_HOST")
    application_mysql_user: str = Field(alias="APPLICATION_MYSQL_USER")
    application_mysql_password: str = Field(alias="APPLICATION_MYSQL_PASSWORD")
    application_mysql_database: str = Field(alias="APPLICATION_MYSQL_DATABASE")
    application_mysql_port: int = Field(default=3306, alias="APPLICATION_MYSQL_PORT")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()