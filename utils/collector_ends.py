from database import CONNECTION_STRING
from pyodbc import connect

def get_all_machines(cursor, rack):
    query = '''SELECT TOP (1000) [IdCollector], [Type], [Rack], [InternalCode]
                FROM [Measure].[dbo].[Collectors]
                WHERE Rack = ?'''
    cursor.execute(query, (rack, ))
    return cursor.fetchall()

def get_all_collectors_settings(cursor, collectors_ids):
    if not collectors_ids:
        return []
    
    place_holders = ', '.join(['?'] * len(collectors_ids))
    query = f'''SELECT [IdCollector], [Setting], [Value]
                FROM [Measure].[dbo].[CollectorsSettings]
                WHERE IdCollector IN ({place_holders})
                AND(Setting = 'VariantName' OR Setting = 'ProgramName')'''
    cursor.execute(query, collectors_ids) 
    return cursor.fetchall()


def main_util_collector_program_names(rack):
    with connect(CONNECTION_STRING) as conn:
        cursor = conn.cursor()

        data = get_all_machines(cursor, rack)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in data]

        collectors_ids = [row[0] for row in data]
        additional_data = get_all_collectors_settings(cursor, collectors_ids)

        settings_map = {}
        for id_coll, setting, value in additional_data:
            if id_coll not in settings_map:
                settings_map[id_coll] = {}
            settings_map[id_coll][setting] = value

        for item in results:
            item.update(settings_map.get(item["IdCollector"], {}))
        
        return results


