from pydantic import BaseModel, Field


class Entity(BaseModel):
    """A single entity extracted from text."""
    name: str = Field(..., description="Name of the entity")
    entity_type: str = Field(..., description="Type: Person, Organization, Technology, Concept, Location, Event")
    description: str = Field(default="", description="Brief description of the entity from context")


class Relationship(BaseModel):
    """A relationship between two entities."""
    source: str = Field(..., description="Name of the source entity")
    target: str = Field(..., description="Name of the target entity")
    relation_type: str = Field(..., description="Type of relationship, e.g. WORKS_AT, USES, PART_OF")
    description: str = Field(default="", description="Description of the relationship")


class ExtractionResult(BaseModel):
    """Result of entity and relationship extraction from a text chunk."""
    entities: list[Entity] = []
    relationships: list[Relationship] = []


class IngestRequest(BaseModel):
    """Request to ingest a document."""
    text: str = Field(..., description="The document text to ingest")
    source_name: str = Field(default="uploaded_document", description="Name/identifier of the source document")


class IngestResponse(BaseModel):
    """Response after document ingestion."""
    message: str
    entities_created: int
    relationships_created: int
    source_name: str


class QueryRequest(BaseModel):
    """Request to ask a question."""
    query: str = Field(..., description="Natural language question")


class QueryResponse(BaseModel):
    """Response to a question with graph-enhanced context."""
    answer: str
    sources: list[dict] = Field(default_factory=list, description="Source entities and relationships used")
    subgraph: dict = Field(default_factory=dict, description="Relevant subgraph snippet")


class GraphStats(BaseModel):
    """Statistics about the knowledge graph."""
    total_entities: int
    total_relationships: int
    entity_types: dict[str, int]
    relationship_types: dict[str, int]
