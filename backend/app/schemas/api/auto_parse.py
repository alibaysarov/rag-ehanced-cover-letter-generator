from pydantic import BaseModel

class AutoParseResponse(BaseModel):
    total:int
    generated:int