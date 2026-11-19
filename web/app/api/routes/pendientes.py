"""Rutas de pendientes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import usuario_actual
from app.models import Usuario
from app.schemas import PendientesOut
from app.services import pendientes as svc

router = APIRouter(prefix="/pendientes", tags=["pendientes"])


@router.get("", response_model=PendientesOut)
def pendientes(
    solo_mios: bool = False,
    solo_vencidos: bool = Query(False),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    return svc.listar(db, usuario, solo_mios, solo_vencidos)
