"""
Autenticación contra LDAP/AD (RNF-001).

En el MVP el directorio es un OpenLDAP en docker-compose con los usuarios demo.
La verificación de credenciales es un BIND real con el DN del usuario; si el
bind tiene éxito, la credencial es válida. No se guardan contraseñas locales.
"""
from __future__ import annotations

import ldap3

from ..config import settings


def _server() -> ldap3.Server:
    return ldap3.Server(
        host=settings.ldap_host,
        port=settings.ldap_port,
        use_ssl=False,
        get_info=ldap3.NONE,
    )


def autenticar(username: str, password: str) -> bool:
    """True si el bind con (DN del usuario, password) tiene éxito."""
    if not username or not password:
        return False
    user_dn = settings.ldap_user_dn_template.format(username=username)
    try:
        conn = ldap3.Connection(_server(), user=user_dn, password=password, auto_bind=True)
        conn.unbind()
        return True
    except ldap3.core.exceptions.LDAPException:
        return False
