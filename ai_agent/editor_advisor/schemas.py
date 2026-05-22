from typing import List

from pydantic import BaseModel, Field


class EditorAdvisorReport(BaseModel):
    fortalezas_actuales: List[str] = Field(default_factory=list)
    problemas_detectados: List[str] = Field(default_factory=list)
    riesgos_tecnicos: List[str] = Field(default_factory=list)
    dependencias: List[str] = Field(default_factory=list)
    mejoras_recomendadas: List[str] = Field(default_factory=list)
    validaciones_necesarias: List[str] = Field(default_factory=list)
    proximo_paso_sugerido: str = ""

