#!/usr/bin/env python3
"""
Prueba de carga / RNF-004: sube el corpus y cronometra la generación del briefing.
Objetivo: 50 documentos procesados en < 3 minutos.

Uso:  python scripts/loadtest.py
Requiere: pip install httpx   (y el stack corriendo: docker compose up)
"""
from __future__ import annotations

import glob
import os
import time

import httpx

BASE = os.environ.get("LOADTEST_BASE", "https://localhost/api")
USER = os.environ.get("LOADTEST_USER", "operaciones")
PASS = os.environ.get("LOADTEST_PASS", os.environ.get("LDAP_DEMO_PASSWORD", "demo1234"))
CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")


def main():
    archivos = sorted(glob.glob(os.path.join(CORPUS, "*")))
    if not archivos:
        raise SystemExit("No hay corpus. Ejecuta primero: python scripts/gen_corpus.py")

    with httpx.Client(verify=False, timeout=120) as c:
        tok = c.post(f"{BASE}/auth/login", json={"username": USER, "password": PASS}).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}

        print(f"Subiendo {len(archivos)} documentos...")
        t0 = time.time()
        files = [("files", (os.path.basename(p), open(p, "rb"))) for p in archivos]
        r = c.post(f"{BASE}/fuentes", files=files, headers=h)
        r.raise_for_status()
        print(f"  carga OK en {time.time()-t0:.1f}s")

        print("Generando briefing...")
        t1 = time.time()
        gen = c.post(f"{BASE}/briefings", json={"titulo": "Briefing de prueba (loadtest)"}, headers=h).json()
        bid = gen["briefing_id"]

        # Poll hasta que exista contenido en la versión activa.
        while time.time() - t1 < 600:
            det = c.get(f"{BASE}/briefings/{bid}", headers=h).json()
            if det.get("contenido"):
                break
            time.sleep(2)

        dt = time.time() - t1
        print(f"\nBriefing generado en {dt:.1f}s ({len(archivos)} documentos).")
        print("RNF-004:", "OK ✅ (< 180s)" if dt < 180 else "FUERA DE PRESUPUESTO ❌ (>= 180s)")


if __name__ == "__main__":
    main()
