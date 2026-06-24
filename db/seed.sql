-- Seed mínimo para demo. Los usuarios se autentican por LDAP; acá se espeja
-- la identidad + habilitación de seguridad para RBAC (RNF-001, RNF-002).

INSERT INTO roles (id, nombre) VALUES
    (1, 'Oficial de Operaciones'),
    (2, 'Analista de Operaciones'),
    (3, 'Asesor de Operaciones'),
    (4, 'Comandante'),
    (5, 'Auditor'),
    (6, 'Administrador del Sistema'),
    (7, 'Oficial de Seguridad')
ON CONFLICT (id) DO NOTHING;

-- Usuarios demo (deben existir también en OpenLDAP con las mismas credenciales).
INSERT INTO usuarios (username, nombre, unidad, nivel_habilitacion) VALUES
    ('operaciones', 'Oficial de Operaciones', 'I Brigada', 'RESERVADO'),
    ('analista',    'Analista de Operaciones', 'I Brigada', 'RESERVADO'),
    ('comandante',  'Comandante',              'Puesto de Mando', 'SECRETO'),
    ('auditor',     'Auditor',                 'Inspectoría', 'SECRETO'),
    ('admin',       'Administrador',           'TI', 'SECRETO')
ON CONFLICT (username) DO NOTHING;

INSERT INTO usuario_roles (usuario_id, rol_id)
SELECT u.id, r.id FROM usuarios u JOIN roles r ON
    (u.username='operaciones' AND r.id=1) OR
    (u.username='analista'    AND r.id=2) OR
    (u.username='comandante'  AND r.id=4) OR
    (u.username='auditor'     AND r.id=5) OR
    (u.username='admin'       AND r.id=6)
ON CONFLICT DO NOTHING;
