import fitz
from PIL import Image
from io import BytesIO


def montar_pdf(input_path, output_path, paginas_por_cara=4):
    """Monta un PDF en pliegos de 2 o 4 páginas por cara."""
    doc = fitz.open(input_path)
    if len(doc) == 0:
        raise Exception("El PDF está vacío o corrupto.")

    total_paginas = len(doc)
    while total_paginas % 4 != 0:
        doc.insert_page(-1)
        total_paginas += 1

    salida = fitz.open()
    A4_WIDTH, A4_HEIGHT = fitz.paper_size("a4")
    paginas = list(range(1, total_paginas + 1))
    hojas = []

    while paginas:
        if paginas_por_cara == 4 and len(paginas) >= 8:
            frente = [paginas[-1], paginas[0], paginas[2], paginas[-3]]
            dorso = [paginas[1], paginas[-2], paginas[-4], paginas[3]]
            hojas.append((frente, dorso))
            paginas = paginas[4:-4]
        elif paginas_por_cara == 2 and len(paginas) >= 4:
            frente = [paginas[-1], paginas[0]]
            dorso = [paginas[1], paginas[-2]]
            hojas.append((frente, dorso))
            paginas = paginas[2:-2]
        else:
            frente = paginas[:paginas_por_cara]
            dorso = paginas[paginas_por_cara:paginas_por_cara*2]
            hojas.append((frente, dorso))
            paginas = paginas[paginas_por_cara*2:]

    def insertar_pagina(nueva_pagina, idx, pos, paginas_por_cara, rotar=0):
        if not idx or idx < 1 or idx > len(doc):
            return
        pagina = doc[idx - 1]
        pix = pagina.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if rotar != 0:
            img = img.rotate(rotar, expand=True)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        if paginas_por_cara == 4:
            x = (pos % 2) * (A4_WIDTH / 2)
            y = (pos // 2) * (A4_HEIGHT / 2)
            rect = fitz.Rect(x, y, x + A4_WIDTH / 2, y + A4_HEIGHT / 2)
        elif paginas_por_cara == 2:
            ancho_paisaje = A4_HEIGHT
            alto_paisaje = A4_WIDTH
            x = (pos % 2) * (ancho_paisaje / 2)
            y = 0
            rect = fitz.Rect(x, y, x + (ancho_paisaje / 2), alto_paisaje)
        else:
            rect = fitz.Rect(0, 0, A4_WIDTH, A4_HEIGHT)

        nueva_pagina.insert_image(rect, stream=buffer)
        buffer.close()

    for frente, dorso in hojas:
        if paginas_por_cara == 2:
            ancho = A4_HEIGHT
            alto = A4_WIDTH
        else:
            ancho = A4_WIDTH
            alto = A4_HEIGHT

        pag_frente = salida.new_page(width=ancho, height=alto)
        for j, idx in enumerate(frente):
            insertar_pagina(pag_frente, idx, j, paginas_por_cara, rotar=0)

        pag_dorso = salida.new_page(width=ancho, height=alto)
        for j, idx in enumerate(dorso):
            rotacion = 180 if paginas_por_cara == 2 else 0
            insertar_pagina(pag_dorso, idx, j, paginas_por_cara, rotar=rotacion)

    salida.save(output_path)
