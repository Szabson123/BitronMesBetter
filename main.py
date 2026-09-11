import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, status, HTTPException
from utils.collector_ends import main_util_collector_program_names
from utils.lighting_linked_serial import main_lighting_linked_serials
from utils.check_bin import process_single_msn
from utils.batery import main_util_batery_check
from utils.blocking_machine import get_assembly_form, get_counted_fails, get_counter, increment_or_create_counter, pass_password

from collections import defaultdict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymysql.cursors import DictCursor

from aidon_utils.get_pallet_info_spea import get_sns_from_pallets

from models import BateryCheckRequest, UnlockRequest
from typing import List, Optional, Tuple, Literal, Dict
from database import CONNECTION_STRING, CONNECTION_STRING_LOCAL_POSTGRES, MYSQL_DATABASES, MYSQL_CONFIG
from pyodbc import connect
import pymysql

from pydantic import BaseModel, Field
import asyncio
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pools = {}
scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)

def run_aoi_sync_job():
    try:
        pool = pools.get("postgres")
        if not pool:
            logger.warning("Pula połączeń Postgres nie jest jeszcze gotowa.")
            return

        with pool.connection() as pg_conn:
            pg_conn.row_factory = dict_row
            process_all_aoi_databases(pg_conn=pg_conn)

    except Exception as e:
        logger.error("Błąd podczas cyklicznej synchronizacji AOI: %s", e, exc_info=True)


async def aoi_sync_task():
    await asyncio.to_thread(run_aoi_sync_job)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pools["postgres"] = ConnectionPool(
        conninfo=CONNECTION_STRING_LOCAL_POSTGRES,
        min_size=2,
        max_size=10,
        open=True
    )

    scheduler.add_job(
        aoi_sync_task,
        trigger="interval",
        seconds=5,
        id="aoi_sync_job",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler AOI uruchomiony (interwał: 5s).")

    yield

    scheduler.shutdown(wait=False)
    pools["postgres"].close()
    logger.info("Scheduler i pule bazodanowe zostały zamknięte.")


app = FastAPI(lifespan=lifespan)

def get_db():
    with pools["postgres"].connection() as conn:
        conn.row_factory = dict_row
        yield conn


@app.get('/mes/health-check/')
async def health_check():
    return {"message": "I'm okay, thanks :)"}


@app.get('/mes/get-collector/{id}/')
async def collector_program_names(id: int):
    data = main_util_collector_program_names(id)
    return data


@app.get('/mes/lighting_linked_serial/{id}/')
async def lighting_linked_serial_func(id: str):
    data = main_lighting_linked_serials(id)
    return data


@app.post('/mes/check_bins/')
async def bin_list_checker(requests: List[str]):
    final_result = {}
    
    with connect(CONNECTION_STRING) as conn:
        cursor = conn.cursor()
        for sn in requests:
            final_result[sn] = process_single_msn(cursor, sn)
            
    return final_result


@app.post('/mes/check-batery/')
async def check_batery(request_data: BateryCheckRequest):
    serial_number = request_data.sn

    data = main_util_batery_check(serial_number)
    return data


@app.get('/mes/machine-block-info/')
def get_machine_block_info(phase_id: int, internal_code: int, conn: psycopg.Connection = Depends(get_db)):

    with conn.cursor() as cursor:
        counter = get_counter(cursor, phase_id)
        if counter <= 200:
            increment_or_create_counter(cursor, phase_id)
        else: counter = 200

    with connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        data = get_counted_fails(cur, counter, phase_id, internal_code)
    
    if not data:
        return {"success": "Mozna produkowac", "status": "can_produce", "message": ""}
    
    if data[1] >= 3:
        return {"error": "Mamy ponad 3 błędy tego samego typu należy wpisac hasło", "status": "pass_password", "message": f"{data[0]}"}

    return {"success": "Mozna produkowac", "status": "can_produce", "message": ""}


@app.post('/mes/unlock/')
def unlock_machine(data: UnlockRequest, conn: psycopg.Connection = Depends(get_db)):
    with conn.cursor() as cursor:
        success = pass_password(cursor, data.phase_id, data.internal_code, data.password_attempt)
        
    if not success:
        return {"status": "error", "message": "Błędne hasło!"}
        
    return {"status": "success", "message": "Licznik zresetowany, odblokowano."}


class PalletInRequest(BaseModel):
    pallet: str


class SnSRequest(BaseModel):
    sn: str
    result: str

class PalletOutRequest(BaseModel):
    pallet: str
    items: List[SnSRequest]


class FVTPalletRequest(BaseModel):
    pallet_number: str = Field(..., example="15028383-15028383-01")


class FVTItemDetail(BaseModel):
    place_num: int = Field(..., ge=1, example=1)
    previous_station_result: Literal["PASS", "FAIL"] = Field(..., example="PASS")


class FVTPalletResponse(BaseModel):
    pallet_number: str = Field(..., example="15028383-15028383-01")
    items: Dict[str, FVTItemDetail]

class HTTPError(BaseModel):
    detail: str


def process_pallet_check_in(pallet: str, conn: psycopg.Connection) -> dict:
    with conn.cursor(row_factory=dict_row) as cursor:
        data = get_sns_from_pallets(cursor, pallet)
        
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active pallet not found: {pallet}"
        )
        
    first_row = data[0]
    return {
        "pallet_number": pallet,
        "pallet_id": first_row["pallet_id"],
        "db_board_id": first_row["db_board_id"],
        "boards": [
            {
                "sn": row["sn"],
                "place_num": row["place_num"],
            }
            for row in data if row.get("sn") is not None
        ]
    }

@app.post("/mes/aidon/ict/pallet/in/")
def aidon_spea_pallet_check_in(payload: PalletInRequest, conn: psycopg.Connection = Depends(get_db)):
    return process_pallet_check_in(payload.pallet, conn)

@app.post("/mes/aidon/fct/application/pallet/")
def aidon_fct_application_pallet(payload: PalletInRequest, conn: psycopg.Connection = Depends(get_db)):
    return process_pallet_check_in(payload.pallet, conn)


def normalize_and_validate_items(items: List[SnSRequest]) -> List[Tuple[str, bool]]:
    normalized = []
    for item in items:
        res = item.result.strip().upper()
        if res not in ("PASS", "FAIL"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "STATUS": "ERROR",
                    "MESSAGE": f"INVALID RESULT '{item.result}' FOR SN {item.sn}. MUST BE PASS OR FAIL"
                }
            )
        normalized.append((item.sn, res == "PASS"))
    return normalized


def get_active_pallet_id(cur: psycopg.Cursor, pallet_number: str) -> Optional[int]:
    cur.execute(
        """
        SELECT id 
        FROM aidon_palletfullinfo 
        WHERE pallet_number = %s AND full_used = FALSE 
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        (pallet_number,)
    )
    row = cur.fetchone()
    if not row:
        return None
    
    return row["id"] if isinstance(row, dict) else row[0]


def update_pallet_sn_results(cur: psycopg.Cursor, pallet_id: int, items_data: List[Tuple[str, bool]]) -> None:
    cur.executemany(
        """
        UPDATE aidon_sntoboard AS sb
        SET 
            ict_result = val.new_res,
            full_result = CASE 
                WHEN sb.full_result IS FALSE THEN FALSE
                ELSE val.new_res
            END
        FROM (VALUES (%s, %s::boolean)) AS val(sn, new_res)
        WHERE sb.pallet_id = %s AND sb.sn = val.sn
        """,
        [(sn, res, pallet_id) for sn, res in items_data]
    )


@app.post("/mes/aidon/ict/pallet/out/")
def aidon_spea_pallet_check_in(payload: PalletOutRequest, conn: psycopg.Connection = Depends(get_db)):
    pallet_num = payload.pallet.strip().upper()

    if not payload.items:
        return {
            "STATUS": "SUCCESS",
            "MESSAGE": f"NO ITEMS TO PROCESS FOR PALLET {pallet_num}"
        }

    items_to_update = normalize_and_validate_items(payload.items)

    with conn.cursor() as cur:
        pallet_id = get_active_pallet_id(cur, pallet_num)
        
        if pallet_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "STATUS": "ERROR",
                    "MESSAGE": f"ACTIVE PALLET {pallet_num} NOT FOUND"
                }
            )

        update_pallet_sn_results(cur, pallet_id, items_to_update)
        conn.commit()

    return {"success": f"success, {pallet_num}"}


@app.post("/mes/aidon/fct/metrology/pallet/")
def aidon_fct_metrology_pallet_check(payload: FVTPalletRequest, conn: psycopg.Connection = Depends(get_db)):
    pallet_num = payload.pallet_number.strip().upper()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, pallet_number 
            FROM aidon_palletfullinfo 
            WHERE UPPER(pallet_number) = %s AND full_used = FALSE 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (pallet_num,),
        )
        pallet_row = cur.fetchone()

        if not pallet_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active pallet not found (full_used=False): {payload.pallet_number}",
            )

        pallet_id = pallet_row["id"] if isinstance(pallet_row, dict) else pallet_row[0]

        cur.execute(
            """
            SELECT sn, place_num, full_result 
            FROM aidon_sntoboard 
            WHERE pallet_id = %s AND sn IS NOT NULL
            ORDER BY place_num ASC
            """,
            (pallet_id,),
        )
        rows = cur.fetchall()

    items_dict = {}
    for row in rows:
        sn = row["sn"]
        place_num = row["place_num"]
        full_res = row["full_result"]

        prev_result = "PASS" if full_res is True else "FAIL"

        items_dict[sn] = FVTItemDetail(
            place_num=place_num,
            previous_station_result=prev_result,
        )

    return FVTPalletResponse(pallet_number=payload.pallet_number, items=items_dict,)


def create_new_pallet(pg_conn: psycopg.Connection, records: list[dict], product: str, db_name: str | None = None) -> int:
    if not records:
        return 0

    grouped_boards = defaultdict(list)
    for row in records:
        grouped_boards[row["dbboardid"]].append(row)

    inserted_pallets_count = 0

    with pg_conn.cursor() as cur:
        for db_board_id, board_records in grouped_boards.items():
            pallet_row_data = next(
                (r for r in board_records if int(r.get("subboardid", -1)) == 0),
                None
            )

            if not pallet_row_data or not pallet_row_data.get("barcode"):
                logger.warning(
                    "[%s] Brak wpisu palety (subboardid=0) dla dbboardid=%s. Pomijam.",
                    product,
                    db_board_id
                )
                continue

            pallet_number = pallet_row_data["barcode"].strip()

            cur.execute(
                """
                INSERT INTO aidon_palletfullinfo (
                    db_board_id,
                    pallet_number,
                    product,
                    full_used,
                    created_at
                )
                VALUES (%s, %s, %s, FALSE, NOW())
                ON CONFLICT (product, db_board_id, pallet_number) DO NOTHING
                RETURNING id;
                """,
                (db_board_id, pallet_number, product),
            )
            pallet_row = cur.fetchone()

            if not pallet_row:
                logger.warning(
                    "[%s] Paleta %s (db_board_id=%s) już istnieje w bazie. Pomijam.",
                    product,
                    pallet_number,
                    db_board_id,
                )
                continue

            pallet_id = pallet_row["id"] if isinstance(pallet_row, dict) else pallet_row[0]

            sorted_boards = sorted(board_records, key=lambda x: int(x.get("subboardid", 0)))
            sn_entries = []

            for row in sorted_boards:
                sub_id = int(row.get("subboardid", 0))
                barcode = row.get("barcode")

                if sub_id > 0 and barcode:
                    report_res = row.get("reportresult")
                    confirm_res = row.get("confirmresult")
                    aoi_pass = (report_res == 1) or (confirm_res == 1)

                    sn_entries.append((
                        pallet_id,
                        barcode.strip(),
                        sub_id,
                        None,
                        aoi_pass,
                    ))

            if sn_entries:
                cur.executemany(
                    """
                    INSERT INTO aidon_sntoboard (
                        pallet_id,
                        sn,
                        place_num,
                        ict_result,
                        full_result
                    )
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    sn_entries,
                )

            inserted_pallets_count += 1

        pg_conn.commit()

    logger.info("[%s] Utworzono %d nowych palet z powiązanymi SN.", product, inserted_pallets_count)
    return inserted_pallets_count


def get_latest_db_board_id_for_product(cur: psycopg.Cursor, product_host: str) -> int:
    cur.execute("SELECT COALESCE(MAX(db_board_id), 0) AS max_id FROM aidon_palletfullinfo WHERE product = %s;", (product_host,))
    row = cur.fetchone()
    return row["max_id"] if isinstance(row, dict) else row[0]


def process_single_database(pg_conn: psycopg.Connection, db_key: str, db_config: dict, last_db_board_id: int):
    query = """
        SELECT 
            bc.dbboardid, 
            bc.subboardid, 
            bc.barcode, 
            b.testtime, 
            b.reportresult, 
            b.confirmresult 
        FROM aoidatav4.t_barcodes bc 
        JOIN aoidatav4.t_boards b ON bc.dbboardid = b.dbboardid
        WHERE b.dbboardid > %s
        ORDER BY b.dbboardid ASC
        LIMIT 500;
    """
    host_identifier = db_config.get("host", db_key)

    try:
        with pymysql.connect(**db_config, cursorclass=DictCursor) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (last_db_board_id,))
                records = cursor.fetchall()

            if not records:
                return {"database": db_key, "product": host_identifier, "status": "no_new_data", "count": 0}

            logger.info("[%s (%s)] Znaleziono %d nowych rekordów. Zapis do Postgresa...", db_key, host_identifier, len(records))
            created_count = create_new_pallet(pg_conn=pg_conn, records=records, product=host_identifier, db_name=db_key)

            return {
                "database": db_key,
                "product": host_identifier,
                "status": "processed",
                "records_fetched": len(records),
                "pallets_created": created_count,
                "last_processed_id": records[-1]["dbboardid"]
            }

    except pymysql.MySQLError as e:
        logger.error("[%s (%s)] Błąd połączenia/zapytania MySQL: %s", db_key, host_identifier, e)
        return {"database": db_key, "product": host_identifier, "status": "error", "error": str(e)}


def process_all_aoi_databases(pg_conn: psycopg.Connection):
    results = []
    for db_key, config in MYSQL_DATABASES.items():
        product_host = config.get("host", db_key)

        with pg_conn.cursor() as cur:
            last_id = get_latest_db_board_id_for_product(cur, product_host)

        logger.info("[%s] Synchronizacja AOI od id > %d", product_host, last_id)
        results.append(process_single_database(
            pg_conn=pg_conn, db_key=db_key, db_config=config, last_db_board_id=last_id
        ))

    return results


@app.post("/mes/aidon/aoi/sync/")
def sync_aoi_pallets(conn: psycopg.Connection = Depends(get_db)):
    return {"status": "completed", "details": process_all_aoi_databases(pg_conn=conn)}


@app.post("/mes/aidon/aoi/")
def get_recent_aoi_boards():
    query = """
        SELECT 
            bc.dbboardid, 
            bc.subboardid, 
            bc.barcode, 
            b.testtime, 
            b.reportresult, 
            b.confirmresult 
        FROM aoidatav4.t_barcodes bc 
        JOIN aoidatav4.t_boards b ON bc.dbboardid = b.dbboardid
        ORDER BY b.dbboardid DESC
        LIMIT 20;
    """

    with pymysql.connect(**MYSQL_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            records = cursor.fetchall()

    return {"count": len(records), "data": records}