from typing import List

from pydantic import BaseModel, Field


class EditorAdvisorReport(BaseModel):
    fortalezas_actuales: List[str] = Field(default_factory=list)
    problemas_detectados: List[str] = Field(default_factory=list)
    riesgos_tecnicos: List[str] = Field(default_factory=list)
    dependencias: List[str] = Field(default_factory=list)
    mejoras_recomendadas: List[str] = Field(default_factory=list)
    validaciones_necesarias: List[str] = Field(default_factory=list)
    problemas_ux_visuales: List[str] = Field(default_factory=list)
    riesgos_dom_listeners: List[str] = Field(default_factory=list)
    cambios_css_only_seguros: List[str] = Field(default_factory=list)
    cambios_html_js_riesgosos: List[str] = Field(default_factory=list)
    zonas_peligrosas_de_tocar: List[str] = Field(default_factory=list)
    checklist_ux_antes: List[str] = Field(default_factory=list)
    checklist_ux_despues: List[str] = Field(default_factory=list)
    fase_safe_sugerida: str = ""
    proximo_paso_sugerido: str = ""
    prompt_para_codex: str = ""
