"""Router de autenticación (RNF-001): login LDAP -> JWT, /me, /logout."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..auth import ldap
from ..auth.deps import CurrentUser, get_current_user
from ..auth.tokens import crear_token
from ..db import get_db
from ..models import Rol, Usuario, UsuarioRol
from ..schemas.api import LoginIn, LoginOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _roles_de(db: Session, usuario_id) -> list[str]:
    return list(
        db.execute(
            select(Rol.nombre).join(UsuarioRol, UsuarioRol.rol_id == Rol.id).where(
                UsuarioRol.usuario_id == usuario_id
            )
        ).scalars()
    )


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    if not ldap.autenticar(body.username, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    # Espeja la identidad de LDAP en la BD (RBAC + clasificación).
    usuario = db.execute(select(Usuario).where(Usuario.username == body.username)).scalar_one_or_none()
    if usuario is None:
        usuario = Usuario(username=body.username, nombre=body.username, nivel_habilitacion="PUBLICO")
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    roles = _roles_de(db, usuario.id)
    token = crear_token(
        sub=usuario.username, uid=str(usuario.id),
        nivel=usuario.nivel_habilitacion, roles=roles, unidad=usuario.unidad,
    )
    audit.registrar(db, accion="LOGIN", actor_id=str(usuario.id), entidad_tipo="usuario", entidad_id=str(usuario.id))

    return LoginOut(
        token=token,
        usuario=UsuarioOut(
            id=str(usuario.id), username=usuario.username, nombre=usuario.nombre,
            unidad=usuario.unidad, nivel_habilitacion=usuario.nivel_habilitacion, roles=roles,
        ),
    )


@router.get("/me", response_model=UsuarioOut)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    u = db.get(Usuario, uuid.UUID(user.id))
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return UsuarioOut(
        id=str(u.id), username=u.username, nombre=u.nombre, unidad=u.unidad,
        nivel_habilitacion=u.nivel_habilitacion, roles=user.roles,
    )


@router.post("/logout")
def logout(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    audit.registrar(db, accion="LOGIN", actor_id=user.id, entidad_tipo="usuario",
                    entidad_id=user.id, detalle={"evento": "logout"})
    return {"ok": True}
