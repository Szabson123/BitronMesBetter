import pyodbc 
from database import CONNECTION_STRING
from datetime import datetime

def get_last_goldens_check(goldens_map: dict[str, dict], assembly_form_id: str, pos_in_rack: int, validity_minutes: int = 480):
    if not goldens_map:
        return {}

    golden_sns = list(goldens_map.keys())
    placeholders = ", ".join(["?"] * len(golden_sns))

    query = f"""
        SELECT 
            [MSN],
            [Result],
            [TestDateTime]
        FROM [Measure].[dbo].[HeaderDataLog]
        WHERE [MSN] IN ({placeholders})
          AND [PosinRack] = ?
          AND [IdParts] = ?
          AND [TestDateTime] >= DATEADD(minute, -?, GETDATE())
        ORDER BY [TestDateTime] DESC;
    """

    params = [*golden_sns, pos_in_rack, assembly_form_id, validity_minutes]

    with pyodbc.connect(CONNECTION_STRING) as mssql_conn:
        with mssql_conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    latest_per_type: dict[str, datetime] = {}
    
    for row in rows:
        msn = str(row[0]).strip()
        test_dt = row[2]
        
        golden_entry = goldens_map.get(msn)
        if golden_entry:
            sample_type = golden_entry["type"]
            if sample_type and sample_type not in latest_per_type:
                latest_per_type[sample_type] = test_dt

    return latest_per_type


def get_goldens_for_test(conn, internal_code: str) -> dict[str, dict]:
    query = """
        SELECT 
            TRIM(ms.sn) AS sn,
            TRIM(tn.compute_name) AS compute_name,
            ms.details
        FROM public.goldensample_mastersample ms
        INNER JOIN public.goldensample_typename tn 
            ON ms.master_type_id = tn.id
        INNER JOIN public.goldensample_mastersample_endcodes msec 
            ON ms.id = msec.mastersample_id
        INNER JOIN public.goldensample_endcode ec 
            ON msec.endcode_id = ec.id
        WHERE TRIM(ec.code) = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (str(internal_code).strip(),))
        rows = cur.fetchall()

    goldens = {}
    for row in rows:
        if isinstance(row, dict):
            sn = str(row.get("sn", "")).strip()
            c_name = str(row.get("compute_name", "")).strip()
            details = row.get("details")
        else:
            sn = str(row[0]).strip()
            c_name = str(row[1]).strip()
            details = row[2]

        if sn:
            goldens[sn] = {
                "type": c_name,
                "details": str(details) if details is not None else ""
            }

    return goldens