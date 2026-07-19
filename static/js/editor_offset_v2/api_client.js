(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ApiClient = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  class ApiError extends Error {
    constructor(message, status, code, issues) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code || "HTTP_ERROR";
      this.issues = issues || [];
    }
  }

  async function requestJson(url, options) {
    const response = await fetch(url, options);
    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new ApiError("El servidor devolvió una respuesta no válida.", response.status);
    }
    if (!response.ok || !payload.ok) {
      const apiError = payload.error || {};
      throw new ApiError(
        apiError.message || "La operación del Editor V2 falló.",
        response.status,
        apiError.code,
        apiError.issues,
      );
    }
    return payload;
  }

  class EditorApiClient {
    async createJob(url, name) {
      return requestJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(name ? { name } : {}),
      });
    }

    async getJob(url) {
      return requestJson(url, { method: "GET" });
    }

    async saveLayout(url, baseRevision, layout) {
      return requestJson(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ base_revision: baseRevision, layout }),
      });
    }
  }

  return Object.freeze({ ApiError, EditorApiClient, requestJson });
});
