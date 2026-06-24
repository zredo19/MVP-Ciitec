from app import crypto


def test_roundtrip_bytes():
    data = b"informacion reservada \x00\x01"
    assert crypto.decrypt(crypto.encrypt(data)) == data


def test_roundtrip_str():
    txt = "Incidente en Antofagasta — RESERVADO"
    token = crypto.encrypt_str(txt)
    assert token != txt
    assert crypto.decrypt_str(token) == txt


def test_encrypted_text_typedecorator():
    col = crypto.EncryptedText()
    almacenado = col.process_bind_param("dato sensible", None)
    assert almacenado != "dato sensible"
    assert col.process_result_value(almacenado, None) == "dato sensible"
    assert col.process_bind_param(None, None) is None
