import os
import fitz
from PIL import Image
from pdf2image import convert_from_path


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


def generar_preview_virtual(ruta_pdf):
    """Convierte páginas del PDF a imágenes para vista previa simple."""
    output_dir = "preview_temp"
    os.makedirs(output_dir, exist_ok=True)
    for archivo in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, archivo))
    paginas = convert_from_path(ruta_pdf, dpi=150)
    for i, pagina in enumerate(paginas):
        nombre = f"pag_{i+1}.jpg"
        pagina.save(os.path.join(output_dir, nombre), "JPEG")
