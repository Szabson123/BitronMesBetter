from typing import Any, Dict, List
import psycopg


def get_sns_from_pallets(cursor: psycopg.Cursor, pallet_number: str) -> List[Dict[str, Any]]:
    query = """
        SELECT 
            p.id AS pallet_id,
            p.db_board_id,
            p.pallet_number,
            s.id AS sn_to_board_id,
            s.sn,
            s.place_num
        FROM aidon_palletfullinfo p
        LEFT JOIN aidon_sntoboard s ON s.pallet_id = p.id
        WHERE p.pallet_number = %s 
          AND p.full_used = FALSE
        ORDER BY s.place_num ASC;
    """
    cursor.execute(query, (pallet_number,))
    return cursor.fetchall()

