"""Pydantic request/response models for the recipe service.

These are the typed-boundary contracts. They must mirror the TypeScript
interfaces in `web/lib/types.ts` exactly — drift produces silent render
failures in the Next.js frontend.
"""
from typing import List, Literal

from pydantic import BaseModel, Field


# --- /extract --------------------------------------------------------

class ExtractRequest(BaseModel):
    """Request body for POST /extract.

    The request field has a length constraint that gates 422 on empty
    or oversized input.
    """
    text: str = Field(..., min_length=1, max_length=5000)


class Entity(BaseModel):
    """A single named-entity span.

    Field names must match the corresponding TypeScript Entity
    interface in `web/lib/types.ts` exactly.
    """
    text: str
    label: str
    start: int
    end: int


class ExtractResponse(BaseModel):
    """Response body for POST /extract.

    Per the Evaluation Methodology, the returned list is ordered by
    start offset ascending.
    """
    entities: List[Entity]


# --- /kg/query -------------------------------------------------------

class KGRequest(BaseModel):
    """Request body for POST /kg/query.

    The question field has a length constraint.
    """
    question: str = Field(..., min_length=1, max_length=500)


class KGResponse(BaseModel):
    """Response body for POST /kg/query."""
    cypher: str
    rows: List[dict]
    count: int


class UnsupportedQueryDetail(BaseModel):
    """Structured detail returned on 422 from /kg/query."""
    reason: Literal["unsupported_question"]
    supported_patterns: List[str]


# --- /rag/answer -----------------------------------------------------

class RAGRequest(BaseModel):
    """Request body for POST /rag/answer.

    The question field has a length constraint; `k` is a bounded
    integer with a default.
    """
    question: str = Field(..., min_length=1, max_length=500)
    k: int = Field(4, ge=1, le=10)


class Citation(BaseModel):
    """One citation: chunk id and retrieval score.

    Field names must match the TypeScript Citation interface.
    """
    chunk_id: int
    score: float


class RAGResponse(BaseModel):
    """Response body for POST /rag/answer.

    Grounding contract: when `answer` is not the empty-retrieval
    sentinel, `len(citations) > 0` is required.
    """
    answer: str
    citations: List[Citation]
    confidence: float


# --- Health / readiness ---------------------------------------------

class HealthResponse(BaseModel):
    """Liveness response."""
    status: str


class ReadyDetail(BaseModel):
    """Readiness detail naming each backend's status."""
    neo4j: str
    weaviate: str
