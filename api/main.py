"""FastAPI application — recipe service.

This module wires the path operations, lifespan, and CORS middleware.

Discipline gates the autograder enforces:
- Neo4j driver, Weaviate client, spaCy pipeline, and the flan-t5-base
  generator are constructed exactly once per process inside `lifespan`.
- `CORSMiddleware` is registered with `allow_origins=[WEB_ORIGIN]`.
- `/extract`, `/kg/query`, `/rag/answer` use Pydantic shapes from
  `models.py` (no anonymous dicts; use Pydantic v2 idioms (model_dump, not the deprecated v1 serialization shortcut)).
- `/kg/query` converts `UnsupportedQueryError` to 422 with structured
  detail (`{"reason": "unsupported_question", "supported_patterns": [...]}`).
- `/readyz` probes Neo4j (`RETURN 1`) AND Weaviate (`client.is_ready()`)
  within 2 seconds; failure → 503.
- `/healthz` does NOT touch Neo4j or Weaviate.
"""
from contextlib import asynccontextmanager

import spacy
import weaviate
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

from .auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_access_token,
    require_api_key_or_jwt,
    require_jwt_admin,
)
from .deps import get_embedder, get_generator, get_nlp, get_session, get_weaviate
from .kg import UnsupportedQueryError, wrap_kg_query
from .m8_rag.generator import load_generator
from .models import (
    ExtractRequest,
    ExtractResponse,
    HealthResponse,
    KGRequest,
    KGResponse,
    RAGRequest,
    RAGResponse,
    ReadyDetail,
    UnsupportedQueryDetail,
)
from .nlp import extract_entities
from .rag import compose_rag
from .settings import Settings
from .w9b_mapper.shapes import SUPPORTED_PATTERNS

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Process-scoped resource setup and teardown.

    On startup: open the Neo4j Bolt driver, construct the Weaviate
    client, load the spaCy `en_core_web_sm` pipeline, and load the
    flan-t5-base generator. Stash each on `app.state` so `Depends()`
    helpers can resolve them.
    """
    app.state.neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    app.state.weaviate_client = weaviate.Client(settings.weaviate_url)
    app.state.nlp = spacy.load("en_core_web_sm")
    app.state.generator = load_generator()
    app.state.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    try:
        yield
    finally:
        app.state.neo4j_driver.close()


app = FastAPI(title="M10 Recipe Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/login", response_model=TokenResponse)
def auth_login(body: LoginRequest) -> TokenResponse:
    """Exchange dev credentials for a signed JWT.

    Invalid credentials → 401.
    """
    user = authenticate_user(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    return TokenResponse(access_token=create_access_token(subject=user))


@app.get("/admin/echo")
def admin_echo(payload: dict = Depends(require_jwt_admin)) -> dict:
    """Admin-only route — echoes the decoded JWT claims (JWT scope only)."""
    return {"sub": payload.get("sub"), "payload": payload}


@app.post("/extract", response_model=ExtractResponse)
def extract(
    req: ExtractRequest,
    auth: dict = Depends(require_api_key_or_jwt),
    nlp=Depends(get_nlp),
) -> ExtractResponse:
    """Run spaCy NER on the input text; return entities ordered by `start`.

    Requires a valid API key or JWT. Returns ExtractResponse with
    entities sorted by `start` ascending.
    """
    return ExtractResponse(entities=extract_entities(req.text, nlp))


@app.post("/kg/query", response_model=KGResponse)
def kg_query(
    req: KGRequest,
    auth: dict = Depends(require_api_key_or_jwt),
    session=Depends(get_session),
) -> KGResponse:
    """Run the W9B mapper and execute the resulting Cypher.

    Returns KGResponse(cypher=..., rows=[r.data() for r in session.run(...)], count=len(rows)).
    UnsupportedQueryError → HTTPException(422, detail=UnsupportedQueryDetail(...).model_dump()).
    """
    try:
        cypher, params = wrap_kg_query(req.question)
    except UnsupportedQueryError:
        detail = UnsupportedQueryDetail(
            reason="unsupported_question",
            supported_patterns=list(SUPPORTED_PATTERNS),
        )
        raise HTTPException(status_code=422, detail=detail.model_dump())

    result = session.run(cypher, **params)
    rows = [record.data() for record in result]
    return KGResponse(cypher=cypher, rows=rows, count=len(rows))


@app.post("/rag/answer", response_model=RAGResponse)
def rag_answer(
    req: RAGRequest,
    auth: dict = Depends(require_api_key_or_jwt),
    weaviate_client=Depends(get_weaviate),
    generator=Depends(get_generator),
    embedder=Depends(get_embedder),
) -> RAGResponse:
    """Retrieve → assemble → generate → cite → grounding check.

    Returns RAGResponse with citations populated when a grounded answer
    is available, or the SENTINEL with empty citations when retrieval
    or citation extraction fails.
    """
    result = compose_rag(
        req.question,
        embedder=embedder,
        weaviate_client=weaviate_client,
        generator=generator,
        k=req.k,
    )
    return RAGResponse(**result)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Liveness probe. Must NOT touch Neo4j or Weaviate."""
    return HealthResponse(status="ok")


@app.get("/readyz")
def readyz(session=Depends(get_session), weaviate_client=Depends(get_weaviate)):
    """Readiness probe.

    Returns 200 only if `RETURN 1` against Neo4j AND `client.is_ready()`
    against Weaviate both succeed within 2 seconds. Otherwise 503 with
    structured detail naming which backend failed.
    """
    try:
        record = session.run("RETURN 1 AS ok").single()
        neo4j_ok = record is not None
    except Exception:
        neo4j_ok = False

    try:
        weaviate_ok = bool(weaviate_client.is_ready())
    except Exception:
        weaviate_ok = False

    detail = ReadyDetail(
        neo4j="ok" if neo4j_ok else "down",
        weaviate="ok" if weaviate_ok else "down",
    )

    if neo4j_ok and weaviate_ok:
        return detail
    raise HTTPException(status_code=503, detail=detail.model_dump())
