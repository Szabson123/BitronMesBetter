from pydantic import BaseModel


class BinRequest(BaseModel):
    msn: str


class BateryCheckRequest(BaseModel):
    sn: str