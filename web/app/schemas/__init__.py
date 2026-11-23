"""Esquemas Pydantic — un módulo por dominio (alineado a services/routes).

Uso: `from app.schemas import EventoOut, UsuarioIn`
"""
from app.schemas.area import AreaIn, AreaOut, AreaPatch, AreaRef
from app.schemas.auth import LoginIn, TokenOut
from app.schemas.claves import ClaveApiCreada, ClaveApiIn, ClaveApiOut
from app.schemas.compromiso import CompromisoIn, CompromisoOut, CompromisoPatch, CompromisoPendienteOut
from app.schemas.evento import (
    AuditoriaOut,
    CambioEstadoIn,
    EventoBusquedaOut,
    EventoDetalleOut,
    EventoIn,
    EventoOut,
    EventoPatch,
    EventosPagina,
    Meta,
    SeguimientoIn,
    SeguimientoOut,
)
from app.schemas.kpi import Indicador, KpiListaOut, TableroOut
from app.schemas.pendientes import PendientesOut
from app.schemas.roles import RolPersonalizadoIn, RolPersonalizadoOut, RolPersonalizadoPatch
from app.schemas.subtipo import SubtipoIn, SubtipoOut, SubtipoPatch
from app.schemas.superadmin import (
    ActividadOut,
    CuentaHistoricaOut,
    ExpedienteCuentaOut,
    PendienteHistoricoCompOut,
    ReferenciaArchivoOut,
    RegistroHistoricoOut,
    RespaldoArchivoOut,
    SuperArchivosOut,
    SuperPendientesOut,
    SuperResumenOut,
)
from app.schemas.usuario import UsuarioIn, UsuarioOut, UsuarioPatch, UsuarioRef

__all__ = [
    "AreaIn", "AreaOut", "AreaPatch", "AreaRef",
    "AuditoriaOut",
    "CambioEstadoIn",
    "ClaveApiCreada", "ClaveApiIn", "ClaveApiOut",
    "CompromisoIn", "CompromisoOut", "CompromisoPatch", "CompromisoPendienteOut",
    "EventoBusquedaOut", "EventoDetalleOut", "EventoIn", "EventoOut", "EventoPatch", "EventosPagina",
    "Indicador", "KpiListaOut",
    "LoginIn",
    "Meta",
    "PendientesOut",
    "RolPersonalizadoIn", "RolPersonalizadoOut", "RolPersonalizadoPatch",
    "SeguimientoIn", "SeguimientoOut",
    "SubtipoIn", "SubtipoOut", "SubtipoPatch",
    "ActividadOut", "CuentaHistoricaOut", "ExpedienteCuentaOut",
    "PendienteHistoricoCompOut", "ReferenciaArchivoOut", "RegistroHistoricoOut",
    "RespaldoArchivoOut", "SuperArchivosOut", "SuperPendientesOut", "SuperResumenOut",
    "TableroOut",
    "TokenOut",
    "UsuarioIn", "UsuarioOut", "UsuarioPatch", "UsuarioRef",
]
