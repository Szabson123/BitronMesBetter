from pydantic import BaseModel


class BinRequest(BaseModel):
    msn: str