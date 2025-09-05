document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('vista-previa-btn');
  const form = document.querySelector('form[action="/revision"]');
  const previewContainer = document.getElementById('preview-container');
  const img = document.getElementById('preview-img');

  if (!btn) return;

  btn.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!form) return;
    const data = new FormData(form);
    previewContainer.innerHTML = '<p>Generando vista previa...</p>';
    try {
      const resp = await fetch('/vista_previa_tecnica', { method: 'POST', body: data });
      const json = await resp.json();
      if (!resp.ok) throw new Error(json.error || 'Error en vista previa');
      if (json.preview_url) {
        img.src = json.preview_url + '?v=' + Date.now();
        previewContainer.innerHTML = '';
        previewContainer.appendChild(img);
      } else {
        previewContainer.innerHTML = '<p>No se pudo generar la vista previa.</p>';
      }
    } catch (err) {
      previewContainer.innerHTML = `<p>${err.message}</p>`;
    }
  });
});
