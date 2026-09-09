from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, status, HTTPException
from utils.collector_ends import main_util_collector_program_names
from utils.lighting_linked_serial import main_lighting_linked_serials
from utils.check_bin import process_single_msn
from utils.batery import main_util_batery_check
from utils.blocking_machine import get_assembly_form, get_counted_fails, get_counter, increment_or_create_counter, pass_password

from aidon_utils.get_pallet_info_spea import get_sns_from_pallets

from models import BateryCheckRequest, UnlockRequest
from typing import List, Optional, Tuple
from database import CONNECTION_STRING, CONNECTION_STRING_LOCAL_POSTGRES, MYSQL_CONFIG
from pyodbc import connect
import pymysql

from pydantic import BaseModel, Field

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pools = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    pools["postgres"] = ConnectionPool(
        conninfo=CONNECTION_STRING_LOCAL_POSTGRES,
        min_size=2,
        max_size=10,
        open=True
    )
    yield
    pools["postgres"].close()

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


@app.post("/mes/aidon/ict/pallet/in/")
def aidon_spea_pallet_check_in(payload: PalletInRequest, conn: psycopg.Connection = Depends(get_db)):
    pallet = payload.pallet
    with conn.cursor(row_factory=dict_row) as cursor:
        data = get_sns_from_pallets(cursor, pallet)
        
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            error=f"Pallet not found: {pallet}"
        )
        
    return {
        "pallet_number": pallet,
        "pallet_id": data[0]["pallet_id"],
        "db_board_id": data[0]["db_board_id"],
        "boards": [
            {
                "sn": row["sn"],
                "place_num": row["place_num"],
            }
            for row in data if row["sn"] is not None
        ]
    }


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
        FROM your_app_palletfullinfo 
        WHERE pallet_number = %s AND full_used = FALSE 
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        (pallet_number,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def update_pallet_sn_results(cur: psycopg.Cursor, pallet_id: int, items_data: List[Tuple[str, bool]]) -> None:

    cur.executemany(
        """
        UPDATE your_app_sntoboard AS sb
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
