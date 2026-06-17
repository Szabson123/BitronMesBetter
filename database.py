from config import settings


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