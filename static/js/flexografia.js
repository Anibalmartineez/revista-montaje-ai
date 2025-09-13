document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tooltip-icon').forEach(icon => {
    icon.addEventListener('click', () => {
      icon.classList.toggle('show');
    });
  });

  const form = document.getElementById('vista-previa-form');
  const previewContainer = document.getElementById('preview-container');
  const img = document.getElementById('preview-img');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    previewContainer.innerHTML = '<p>Generando vista previa...</p>';
    // Limpiar cualquier imagen previa mientras se genera una nueva
    img.removeAttribute('src');
    try {
      const formData = new FormData(form);
      const resp = await fetch(form.action, { method: 'POST', body: formData });
      const json = await resp.json();
      if (!resp.ok) throw new Error(json.error || 'Error en vista previa');
      if (json.preview_url) {
        const cacheBust = (typeof crypto !== 'undefined' && crypto.randomUUID)
          ? crypto.randomUUID()
          : Date.now();
        img.onload = () => {
          previewContainer.innerHTML = '';
          previewContainer.appendChild(img);
        };
        img.onerror = () => {
          img.removeAttribute('src');
          previewContainer.innerHTML = '<p>Error al cargar la vista previa.</p>';
        };
        img.src = json.preview_url + '?v=' + cacheBust;
      } else {
        previewContainer.innerHTML = '<p>No se pudo generar la vista previa.</p>';
      }
    } catch (err) {
      img.removeAttribute('src');
      previewContainer.innerHTML = `<p>${err.message}</p>`;
    }
  });
});
