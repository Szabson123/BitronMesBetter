from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from utils.collector_ends import main_util_collector_program_names
from utils.lighting_linked_serial import main_lighting_linked_serials
from utils.check_bin import process_single_msn
from utils.batery import main_util_batery_check
from utils.blocking_machine import get_assembly_form, get_counted_fails, get_counter, increment_or_create_counter, pass_password
from models import BateryCheckRequest
from typing import List
from database import CONNECTION_STRING, CONNECTION_STRING_LOCAL_POSTGRES
from pyodbc import connect

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
    
    if data[1] >= 3:
        return {"error": "Mamy ponad 3 błędy tego samego typu należy wpisac hasło", "status": "pass_password", "message": f"{data[0]}"}

    return {"success": "Mozna produkowac", "status": "can_produce", "message": ""}


@app.post('/mes/unlock/')
def unlock_machine(phase_id: int, internal_code: int, password_attempt: str, conn: psycopg.Connection = Depends(get_db)):
    with conn.cursor() as cursor:
        success = pass_password(cursor, phase_id, internal_code, password_attempt)
        
    if not success:
        return {"status": "error", "message": "Błędne hasło!"}
        
    return {"status": "success", "message": "Licznik zresetowany, odblokowano."}