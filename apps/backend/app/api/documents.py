"""HTTP routes for document upload and library access.



Purpose: Exposes POST /documents/upload, GET /documents, GET /documents/{id},

GET /documents/{id}/file, and DELETE /documents/{id}.

Interactions: Mounted by main.py. Delegates file handling to document_storage.py,

database access to document_repository.py, and response shapes to schemas/document.py.

Called by the frontend through lib/api.ts.

"""



from uuid import UUID



from fastapi import APIRouter, File, HTTPException, UploadFile, status

from fastapi.responses import FileResponse



from app.schemas.document import (

    DeleteDocumentResponse,

    DocumentListResponse,

    DocumentResponse,

)

from app.services.document_repository import (

    create_document,

    delete_document,

    get_document,

    list_documents,

)

from app.services.document_storage import (

    delete_local_pdf,

    resolve_document_path,

    save_pdf_upload,

)



router = APIRouter(prefix="/documents", tags=["documents"])





@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)

async def upload_document(file: UploadFile = File(...)) -> DocumentResponse:

    stored_filename, original_filename, destination = await save_pdf_upload(file)



    try:

        return create_document(

            filename=stored_filename,

            original_filename=original_filename,

            file_path=str(destination),

        )

    except RuntimeError as exc:

        destination.unlink(missing_ok=True)

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=str(exc),

        ) from exc





@router.get("", response_model=DocumentListResponse)

def get_documents() -> DocumentListResponse:

    try:

        documents = list_documents()

    except RuntimeError as exc:

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=str(exc),

        ) from exc



    return DocumentListResponse(documents=documents, total=len(documents))





@router.get("/{document_id}/file")

def get_document_file(document_id: UUID) -> FileResponse:

    try:

        document = get_document(document_id)

    except RuntimeError as exc:

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=str(exc),

        ) from exc



    if document is None:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Document not found.",

        )



    file_path = resolve_document_path(document.file_path)

    return FileResponse(

        path=file_path,

        media_type="application/pdf",

        filename=document.original_filename,

        content_disposition_type="inline",

    )





@router.delete("/{document_id}", response_model=DeleteDocumentResponse)

def remove_document(document_id: UUID) -> DeleteDocumentResponse:

    try:

        document = delete_document(document_id)

    except RuntimeError as exc:

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=str(exc),

        ) from exc



    if document is None:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Document not found.",

        )



    delete_local_pdf(document.file_path)

    return DeleteDocumentResponse(id=document.id)





@router.get("/{document_id}", response_model=DocumentResponse)

def get_document_by_id(document_id: UUID) -> DocumentResponse:

    try:

        document = get_document(document_id)

    except RuntimeError as exc:

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=str(exc),

        ) from exc



    if document is None:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Document not found.",

        )



    return document


