from config import settings

CONNECTION_STRING = (
    f'Driver={{ODBC Driver 17 for SQL Server}};'
    f'Server={settings.eclipse_host};'
    f'DATABASE={settings.eclipse_database};'
    f'UID={settings.eclipse_user};'
    f'PWD={settings.eclipse_password}'
)