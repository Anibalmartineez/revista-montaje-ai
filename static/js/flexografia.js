document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('vista-previa-form');
  const previewContainer = document.getElementById('preview-container');
  const img = document.getElementById('preview-img');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    previewContainer.innerHTML = '<p>Generando vista previa...</p>';
    try {
      const formData = new FormData(form);
      const resp = await fetch(form.action, { method: 'POST', body: formData });
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
