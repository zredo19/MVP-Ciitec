"""
Genera las versiones EN BLANCO de las páginas 1 y 6 de la plantilla institucional.

Las PNG originales (1.PNG, 6.PNG) traen cifras de ejemplo "quemadas" en la imagen
(donut 25.672, FUERZA SLC 2.305/5.911/8.216, Ops Guardián 513/331/170, página 6
TOTAL 389 / NOP 69, y la caja "Gráficos eliminados intencionalmente"). Para que el
motor de overlay (RF-008, EXPORT_STYLE=overlay) pueda rellenar esas casillas con los
datos reales del briefing, se borran rellenando cada caja con el color de FONDO de la
celda (color modal de la región: blanco, gris, rojo o cian) y la caja-placeholder con
blanco.

Uso:  python scripts/blank_template.py
- Respalda los originales en backend/app/templates/_originales/.
- Sobrescribe 1.PNG y 6.PNG con la versión en blanco.
"""
from __future__ import annotations

import os
import shutil

from PIL import Image

TPL = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "templates")
ORIG = os.path.join(TPL, "_originales")

# (x0, y0, x1, y1).  fill=None -> color modal (fondo de la celda); fill=(r,g,b) -> color fijo.
CAJAS: dict[str, list[tuple[tuple[int, int, int, int], tuple[int, int, int] | None]]] = {
    "1.PNG": [
        # Donut PARTE DE FUERZA INSTITUCIONAL: se limpia toda la celda (pie + cifras)
        # a blanco; el overlay imprime el TOTAL real en su lugar.
        ((179, 134, 259, 232), (255, 255, 255)),
        # FUERZA SLC (celdas blancas, valor en columna derecha)
        ((624, 105, 674, 125), None),   # 2.305
        ((624, 140, 674, 162), None),   # 5.911
        ((624, 172, 674, 193), None),   # 8.216 (TOTAL)
        # Relevos
        ((450, 374, 495, 393), None),   # N°77
        ((448, 417, 497, 435), None),   # N.°46
        ((533, 417, 612, 433), None),   # Del xxx al xxx
        # Ops Guardián Soberano — FUERZA ACTUAL (celdas grises)
        ((503, 527, 537, 545), None),   # 513
        ((503, 557, 537, 573), None),   # 331
        ((503, 586, 537, 602), None),   # 170
        # Ops Guardián — TRABAJOS DE TIERRA (celdas blancas)
        ((546, 527, 594, 544), None),   # 2.760 Mts
        ((616, 527, 666, 544), None),   # 2.190 Mts
        ((546, 557, 594, 573), None),   # 6.000 Mts
        ((616, 557, 666, 573), None),   # 2.100 Mts
        ((546, 586, 594, 602), None),   # 3.820 Mts
        ((618, 586, 662, 602), None),   # 690 Mts
    ],
    "6.PNG": [
        ((48, 250, 95, 285), None),          # TOTAL 389 (celda blanca)
        ((118, 250, 205, 287), None),        # NOP 69 (celda roja)
        ((306, 392, 556, 576), (255, 255, 255)),  # caja "Gráficos eliminados" -> blanco
    ],
}


def _modal(im: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    region = im.crop(box).convert("RGB")
    colores = region.getcolors(maxcolors=region.width * region.height)
    return max(colores, key=lambda c: c[0])[1]


def main() -> None:
    os.makedirs(ORIG, exist_ok=True)
    for nombre, cajas in CAJAS.items():
        ruta = os.path.join(TPL, nombre)
        respaldo = os.path.join(ORIG, nombre)
        if not os.path.exists(respaldo):
            shutil.copy2(ruta, respaldo)        # respalda 1 sola vez
        src = respaldo                          # siempre parte del original
        im = Image.open(src).convert("RGB")
        px = im.load()
        for box, fill in cajas:
            color = fill if fill is not None else _modal(im, box)
            x0, y0, x1, y1 = box
            for x in range(x0, x1):
                for y in range(y0, y1):
                    px[x, y] = color
        im.save(os.path.join(TPL, nombre))
        print(f"{nombre}: {len(cajas)} casillas blanqueadas  ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
