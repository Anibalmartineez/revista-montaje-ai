(function () {
  "use strict";

  const contextElement = document.getElementById("editor-offset-v2-context");
  const newJobButton = document.getElementById("ev2-new-job");
  const statusMessage = document.getElementById("ev2-status-message");

  if (!contextElement || !newJobButton || !statusMessage) {
    return;
  }

  let context;
  try {
    context = JSON.parse(contextElement.textContent || "{}");
  } catch (error) {
    statusMessage.textContent = "No se pudo leer el contexto inicial del Editor V2.";
    return;
  }

  newJobButton.addEventListener("click", async function () {
    newJobButton.disabled = true;
    statusMessage.textContent = "Creando job V2…";

    try {
      const response = await fetch(context.create_job_url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok || !payload.open_url) {
        throw new Error(payload.error?.message || "No se pudo crear el job V2.");
      }
      window.location.assign(payload.open_url);
    } catch (error) {
      statusMessage.textContent = error.message || "Error inesperado al crear el job V2.";
      newJobButton.disabled = false;
    }
  });
})();
