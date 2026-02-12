from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.models.db import get_session
from app.models.entities import Document, Project
from app.models.schemas import DocType, DocumentCreate, DocumentRead, DocumentUpdate

router = APIRouter(tags=["documents"])

ALLOWED_DOC_TYPES: set[DocType] = {
    "problem",
    "vision",
    "tdr",
    "retrospective",
}


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    project_id: UUID,
    payload: DocumentCreate,
    session: Session = Depends(get_session),
) -> DocumentRead:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if payload.type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document type",
        )

    doc = Document(
        project_id=project_id,
        type=payload.type,
        content=payload.content,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


@router.get("/documents/{doc_id}", response_model=DocumentRead)
def get_document(
    doc_id: UUID,
    session: Session = Depends(get_session),
) -> DocumentRead:
    doc = session.get(Document, doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


@router.put("/documents/{doc_id}", response_model=DocumentRead)
def update_document(
    doc_id: UUID,
    payload: DocumentUpdate,
    session: Session = Depends(get_session),
) -> DocumentRead:
    doc = session.get(Document, doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    doc.content = payload.content
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
def list_documents(
    project_id: UUID,
    type_filter: Optional[DocType] = Query(None, alias="type"),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> list[DocumentRead]:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    query = select(Document).where(Document.project_id == project_id)

    if type_filter is not None:
        query = query.where(Document.type == type_filter)

    if search:
        query = query.where(Document.content.contains(search))

    docs = session.exec(query).all()
    return docs