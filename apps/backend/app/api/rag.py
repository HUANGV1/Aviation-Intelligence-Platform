"""HTTP routes for semantic search over embedded document chunks."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchError, search_document_chunks

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=SearchResponse)
def search_chunks(request: SearchRequest) -> SearchResponse:
    try:
        return search_document_chunks(
            request.query,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except SearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
