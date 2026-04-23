from utils.lighting_linked_serial import get_all_childs
from database import CONNECTION_STRING
from pyodbc import connect


def get_measure_bin(cursor, checking_id):
    query = '''SELECT m.[Measure], m.[Item]
               FROM [Measure].[dbo].[HeaderDataLog] h
               INNER JOIN [Measure].[dbo].[MeasureDataLog] m ON h.IDMeasure = m.IDMeasure
               WHERE h.MSN = ?
               AND m.UnitMeasure = 'BIN_GROUP' '''
    cursor.execute(query, checking_id)
    rows = cursor.fetchall()
    return [(row[0], row[1]) for row in rows] if rows else []


def process_single_msn(cursor, target_id: str):
    data = get_all_childs(cursor, target_id)
    
    len_id = len(target_id)
    found_serials = {target_id}

    for item in data:
        # Zrobione tak żeby użyc tej samej funkcji co wczesniej a nie pisac tego samego 2 raz
        _, serial, _ = item
        if not serial: continue

        if len_id == 24 and target_id[:16] == serial[:16]:
            found_serials.add(serial)
        elif len_id < 24 and target_id[:11] == serial[:11]:
            found_serials.add(serial)

    transformed_list = []
    for sn in found_serials:
        bin_data = get_measure_bin(cursor, sn)
        
        for measure, item in bin_data:
            transformed_list.append({
                sn: {
                    "bin": measure,
                    "item": item
                }
            })
    
    return transformed_list