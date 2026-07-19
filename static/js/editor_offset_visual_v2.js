(function () {
  "use strict";

  function startEditorOffsetV2() {
    try {
      window.EditorOffsetV2.Bootstrap.start();
    } catch (error) {
      const status = document.getElementById("ev2-status-message");
      if (status) {
        status.textContent = error && error.message
          ? error.message
          : "No se pudo iniciar el Editor V2.";
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startEditorOffsetV2, { once: true });
  } else {
    startEditorOffsetV2();
  }
})();
