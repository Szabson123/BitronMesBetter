from typing import Any, Dict, List
import psycopg


def get_sns_from_pallets(cursor: psycopg.Cursor, pallet_number: str) -> List[Dict[str, Any]]:
    query = """
        WITH latest_pallet AS (
            SELECT id, db_board_id, pallet_number
            FROM aidon_palletfullinfo
            WHERE pallet_number = %s 
              AND full_used = FALSE
            ORDER BY id DESC
            LIMIT 1
        )
        SELECT 
            p.id AS pallet_id,
            p.db_board_id,
            p.pallet_number,
            s.id AS sn_to_board_id,
            s.sn,
            s.place_num
        FROM latest_pallet p
        LEFT JOIN aidon_sntoboard s ON s.pallet_id = p.id
        ORDER BY s.place_num ASC;
    """
    cursor.execute(query, (pallet_number,))
    return cursor.fetchall()
