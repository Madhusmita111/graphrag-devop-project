from pydantic import BaseModel, Field
from typing import List, Dict


# =============================
# API REQUEST MODELS
# =============================

class IngestRequest(BaseModel):
    text: str = Field(..., description="Document text to ingest")
    source_name: str = Field(default="uploaded_document")


class QueryRequest(BaseModel):
    query: str = Field(..., description="User question")


# =============================
# API RESPONSE MODELS
# =============================

class IngestResponse(BaseModel):
    message: str
    entities_created: int
    relationships_created: int
    source_name: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict] = Field(default_factory=list)
    subgraph: Dict = Field(default_factory=dict)


# =============================
# OPTIONAL (FOR FUTURE USE)
# =============================

class GraphStats(BaseModel):
    total_entities: int
    total_relationships: int