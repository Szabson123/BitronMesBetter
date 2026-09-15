import pyodbc 
from database import CONNECTION_STRING

def get_last_goldens_check(
    goldens_map: dict[str, str], 
    assembly_form_id: int, 
    pos_in_rack: int
) -> set[str]:
    if not goldens_map:
        return set()

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
          AND [TestDateTime] >= DATEADD(hour, -8, GETDATE())
        ORDER BY [TestDateTime] DESC;
    """

    params = [*golden_sns, pos_in_rack, assembly_form_id]

    with pyodbc.connect(CONNECTION_STRING) as mssql_conn:
        with mssql_conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    tested_types = set()
    for row in rows:
        msn = row[0]
        sample_type = goldens_map.get(msn)
        if sample_type:
            tested_types.add(sample_type)

    return tested_types

def get_goldens_for_test(conn, internal_code: str) -> dict[str, str]:
    query = """
        SELECT 
            TRIM(ms.sn) AS sn,
            TRIM(tn.compute_name) AS compute_name
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
        # Obsługa zarówno słownika (dict_row), jak i krotki (tuple)
        if isinstance(row, dict):
            sn = str(row.get("sn", "")).strip()
            c_name = str(row.get("compute_name", "")).strip()
        else:
            sn = str(row[0]).strip()
            c_name = str(row[1]).strip()

        if sn:
            goldens[sn] = c_name

    return goldens