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

MYSQL_DATABASES = {
    "aoi_metrology_aidon": {
        "host": settings.metrology_mysql_host,
        "user": settings.metrology_mysql_user,
        "password": settings.metrology_mysql_password,
        "database": settings.metrology_mysql_database,
        "port": settings.metrology_mysql_port
    },
    "aoi_application_aidon": {
        "host": settings.application_mysql_host,
        "user": settings.application_mysql_user,
        "password": settings.application_mysql_password,
        "database": settings.application_mysql_database,
        "port": settings.application_mysql_port
    },
}

MYSQL_CONFIG = {
    "host": settings.application_mysql_host,
    "user": settings.application_mysql_user,
    "password": settings.application_mysql_password,
    "database": settings.application_mysql_database,
    "port": settings.application_mysql_port,
    "cursorclass": pymysql.cursors.DictCursor,
}