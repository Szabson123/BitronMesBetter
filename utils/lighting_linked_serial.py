from database import CONNECTION_STRING
from pyodbc import connect

def get_all_childs(cursor, id: str):
    query = '''SELECT TOP (1000) [Container], [Child], [FeedDate]
                FROM [Eclipse].[dbo].[LinkIdTraceability]
                WHERE Container = ?'''
    
    cursor.execute(query, (id, ))
    return cursor.fetchall()


def main_lighting_linked_serials(id: str):
    with connect(CONNECTION_STRING) as conn:
        cursor = conn.cursor()
        data = get_all_childs(cursor, id)

        result = {}
        for item in data:
            parent_id, serial, timestamp = item
            result[serial] = timestamp

        print(result)
        return result
