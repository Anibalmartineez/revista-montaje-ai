def generar_montaje(ancho, alto, separacion, bobina, cantidad):
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    import tempfile

    etiquetas_x = bobina // (ancho + separacion)
    etiquetas_y = 2

    etiquetas_por_repeticion = etiquetas_x * etiquetas_y
    repeticiones = (cantidad + etiquetas_por_repeticion - 1) // etiquetas_por_repeticion

    archivo = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(archivo.name, pagesize=(bobina * mm, 330 * mm))

    for i in range(etiquetas_x):
        for j in range(etiquetas_y):
            x = i * (ancho + separacion) * mm
            y = j * (alto + separacion) * mm
            c.rect(x, y, ancho * mm, alto * mm)

    c.drawString(20, 20, f"Total: {etiquetas_x} x {etiquetas_y} = {etiquetas_por_repeticion} por pasada")
    c.drawString(20, 10, f"Repeticiones necesarias: {repeticiones}")
    c.save()
    return archivo.name
