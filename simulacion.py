import os
import fitz
from PIL import Image, ImageDraw


def generar_simulacion_avanzada(base_img_path, advertencias, lpi, output_path):
    """Genera una imagen PNG con la simulación avanzada.

    Se superpone la imagen base con las advertencias marcadas y un patrón de
    puntos para simular la lineatura especificada. El resultado se guarda en
    ``output_path``.
    """

    base = Image.open(base_img_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    colores = {
        "texto_pequeno": "red",
        "trama_debil": "purple",
        "imagen_baja": "orange",
        "overprint": "blue",
        "sin_sangrado": "darkgreen",
    }

    for adv in advertencias or []:
        bbox = adv.get("bbox") or adv.get("box")
        if not bbox or len(bbox) != 4:
            continue
        x0, y0, x1, y1 = bbox
        color = colores.get(adv.get("tipo"), "red")
        draw.rectangle([x0, y0, x1, y1], outline=color, width=2)

    try:
        lpi_val = float(lpi) if lpi else 1.0
    except Exception:
        lpi_val = 1.0
    spacing = max(2, (600 / lpi_val) * 4)
    radius = spacing / 2
    step = int(spacing)
    alpha = int(0.2 * 255)
    width, height = base.size
    for y in range(0, height, step):
        for x in range(0, width, step):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(0, 0, 0, alpha))

    compuesto = Image.alpha_composite(base, overlay).convert("RGB")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    compuesto.save(output_path, "PNG")
    return output_path


def generar_preview_interactivo(input_path, output_folder="preview_temp"):
    """Genera una vista previa interactiva del montaje del PDF."""
    os.makedirs(output_folder, exist_ok=True)
    doc = fitz.open(input_path)
    total_paginas = len(doc)
    while total_paginas % 4 != 0:
        doc.insert_page(-1)
        total_paginas += 1

    paginas = list(range(1, total_paginas + 1))
    hojas = []
    while len(paginas) >= 4:
        frente = [paginas[0], paginas[-1]]
        dorso = [paginas[1], paginas[-2]]
        hojas.append((frente, dorso))
        paginas = paginas[2:-2]

    imagenes = {}
    for i in range(1, total_paginas + 1):
        page = doc[i - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        img_path = os.path.join(output_folder, f"pag_{i}.jpg")
        pix.save(img_path)
        imagenes[i] = img_path

    hojas_js = str(
        [
            [
                [f"/preview_temp/pag_{i}.jpg" for i in frente],
                [f"/preview_temp/pag_{i}.jpg" for i in dorso],
            ]
            for frente, dorso in hojas
        ]
    )
    vista = """<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='UTF-8'>
<title>Vista previa del montaje</title>
<style>
body {font-family:'Poppins',sans-serif;background:#f4f4f4;text-align:center;margin:0;padding:40px;}
.hoja {display:flex;justify-content:center;gap:30px;margin:30px auto;}
.pagina {background:#fff;box-shadow:0 0 15px rgba(0,0,0,0.2);padding:10px;border-radius:12px;}
.pagina img {width:300px;border-radius:8px;}
button {margin:8px;padding:12px 24px;font-size:16px;border:none;border-radius:8px;cursor:pointer;background-color:#007bff;color:white;}
</style>
</head>
<body>
<h1>📰 Vista previa del Pliego <span id='nro'>1</span></h1>
<div id='frente' class='hoja'></div>
<div id='dorso' class='hoja' style='display:none;'></div>
<div>
  <button onclick='mostrarDorso()'>Ver dorso</button>
  <button onclick='anterior()'>Anterior</button>
  <button onclick='siguiente()'>Siguiente</button>
</div>
<form action='/generar_pdf_final' method='post' style='margin-top:30px;'>
  <input type='hidden' name='modo_montaje' value='2'>
  <button type='submit'>🖨️ Montar PDF final</button>
</form>
<script>
const hojas = __HOJAS__;
let indice = 0;
function cargar(){
  document.getElementById('nro').innerText = indice + 1;
  const frente = document.getElementById('frente');
  const dorso = document.getElementById('dorso');
  frente.innerHTML = '';
  dorso.innerHTML = '';
  hojas[indice][0].forEach(p=>{frente.innerHTML += `<div class='pagina'><img src='${p}'><br>${p}</div>`;});
  hojas[indice][1].forEach(p=>{dorso.innerHTML += `<div class='pagina'><img src='${p}'><br>${p}</div>`;});
  frente.style.display='flex';
  dorso.style.display='none';
}
function mostrarDorso(){const frente=document.getElementById('frente');const dorso=document.getElementById('dorso');if(frente.style.display==='flex'){frente.style.display='none';dorso.style.display='flex';}else{dorso.style.display='none';frente.style.display='flex';}}
function siguiente(){if(indice < hojas.length-1){indice++;cargar();}}
function anterior(){if(indice>0){indice--;cargar();}}
cargar();
</script>
</body>
</html>"""
    vista = vista.replace("__HOJAS__", hojas_js)
    with open(os.path.join(output_folder, "preview.html"), "w", encoding="utf-8") as f:
        f.write(vista)


def generar_preview_virtual(ruta_pdf, advertencias=None, dpi=150, output_dir="preview_temp"):
    """Convierte las páginas del PDF a imágenes y superpone advertencias.

    Parameters
    ----------
    ruta_pdf: str
        Ruta al PDF de entrada.
    advertencias: list[dict] | dict | None
        Estructura con advertencias y sus coordenadas. Puede ser una lista de
        diccionarios con claves como ``page`` / ``pagina`` (0-index), ``bbox``
        (x0, y0, x1, y1) en puntos PDF y ``tipo`` / ``label`` para mostrar.
    dpi: int
        Resolución utilizada para rasterizar el PDF.
    output_dir: str
        Carpeta donde se guardarán las imágenes generadas.

    Returns
    -------
    list[str]
        Lista de rutas absolutas a las imágenes generadas.
    """

    os.makedirs(output_dir, exist_ok=True)
    for archivo in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, archivo))

    doc = fitz.open(ruta_pdf)
    zoom = dpi / 72.0
    resultados = []

    # Normaliza ``advertencias`` a un diccionario por página
    advertencias_por_pagina: dict[int, list] = {}
    if advertencias:
        if isinstance(advertencias, dict):
            for k, v in advertencias.items():
                try:
                    idx = int(k)
                except Exception:
                    continue
                advertencias_por_pagina[idx] = v or []
        else:
            for item in advertencias:
                idx = item.get("page", item.get("pagina", 0))
                advertencias_por_pagina.setdefault(idx, []).append(item)

    color_map = {
        "texto_pequeno": (255, 0, 0, 120),
        "trama_debil": (255, 255, 0, 120),
        "sin_sangrado": (255, 165, 0, 120),
        "error_color": (0, 0, 255, 120),
    }

    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        base = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")

        def dashed_rectangle(box, color, width: int = 2, dash: int = 5):
            x0, y0, x1, y1 = box
            x = x0
            while x < x1:
                draw.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=width)
                draw.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=width)
                x += dash * 2
            y = y0
            while y < y1:
                draw.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=width)
                draw.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=width)
                y += dash * 2

        page_warnings = advertencias_por_pagina.get(i, [])
        for adv in page_warnings:
            bbox = adv.get("bbox") or adv.get("box")
            if not bbox or len(bbox) != 4:
                continue
            x0, y0, x1, y1 = [coord * zoom for coord in bbox]
            tipo = (adv.get("tipo") or adv.get("type") or "").lower()
            color = color_map.get(tipo, (255, 0, 255, 120))
            if tipo in {"sin_sangrado", "fuera_margen", "fuera_area"}:
                dashed_rectangle([x0, y0, x1, y1], color[:3], width=2)
            elif tipo in {"imagen_fuera_cmyk", "fuera_cmyk", "color_rgb", "rgb"}:
                draw.rectangle([x0, y0, x1, y1], outline=(128, 0, 128), width=2)
                draw.text((x0 + 3, y0 + 3), "RGB", fill=(128, 0, 128))
            else:
                draw.rectangle([x0, y0, x1, y1], outline=color[:3], width=2, fill=color)
            label = adv.get("label") or adv.get("mensaje") or tipo
            if label:
                draw.text((x0 + 3, y0 + 3), label, fill=color[:3])

        if not page_warnings:
            draw.text((10, 10), "✔", fill=(0, 128, 0, 255))

        compuesto = Image.alpha_composite(base, overlay).convert("RGB")
        nombre = f"pag_{i+1}.jpg"
        ruta_img = os.path.join(output_dir, nombre)
        compuesto.save(ruta_img, "JPEG")
        resultados.append(ruta_img)

    doc.close()
    return resultados
