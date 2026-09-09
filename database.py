from config import settings
import pymysql

CONNECTION_STRING = (
    f'Driver={{ODBC Driver 17 for SQL Server}};'
    f'Server={settings.eclipse_host};'
    f'DATABASE={settings.eclipse_database};'
    f'UID={settings.eclipse_user};'
    f'PWD={settings.eclipse_password}'
)

CONNECTION_STRING_LOCAL_POSTGRES = (
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
)

CONNECTION_STRING_MYSQL = (
    f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
    f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
)

MYSQL_CONFIG = {
    "host": settings.mysql_host,
    "user": settings.mysql_user,
    "password": settings.mysql_password,
    "database": settings.mysql_database,
    "port": settings.mysql_port,
    "cursorclass": pymysql.cursors.DictCursor,
}