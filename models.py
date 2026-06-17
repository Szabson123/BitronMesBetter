from pydantic import BaseModel


class BinRequest(BaseModel):
    msn: str


class BateryCheckRequest(BaseModel):
    sn: str


class UnlockRequest(BaseModel):
    phase_id: int
    internal_code: int
    password_attempt: str