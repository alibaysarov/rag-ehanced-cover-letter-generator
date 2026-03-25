from pydantic import BaseModel

class RAGChunkAndSrc(BaseModel):
    chunks:list[str]
    source_id:str=None

class RAGUpsertResult(BaseModel):
    ingested:int 

class RAGSearchResult(BaseModel):
    contexts:list[str]
    sources:list[dict]

class RAGQueryResult(BaseModel):
    answer:str
    sources:list[str]
    num_contexts:int