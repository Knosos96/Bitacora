"""Rutas de compromisos."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import usuario_actual
from app.models import Usuario
from app.schemas import CompromisoOut, CompromisoPatch
from app.services import compromisos as svc

router = APIRouter(prefix="/compromisos", tags=["compromisos"])


@router.patch("/{compromiso_id}", response_model=CompromisoOut)
def resolver_compromiso(
    compromiso_id: uuid.UUID,
    datos: CompromisoPatch,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    return svc.resolver(db, compromiso_id, datos, usuario)
