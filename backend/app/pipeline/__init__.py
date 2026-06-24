"""
Pipeline de procesamiento estilo pipes & filters (Capa 3 / worker):

    Ingestar -> Normalizar -> Extraer -> Detectar -> Sintetizar

Cada filtro es un módulo desacoplado y testeable de forma aislada. La
orquestación (group/chord paralelo) vive en `app.worker`.
"""
