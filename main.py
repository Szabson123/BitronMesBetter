from fastapi import FastAPI
from utils.collector_ends import main_util_collector_program_names
from utils.lighting_linked_serial import main_lighting_linked_serials
from utils.check_bin import process_single_msn
from models import BinRequest
from typing import List
from database import CONNECTION_STRING
from pyodbc import connect

app = FastAPI()

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