import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils import calcular_etiquetas_por_fila

def test_calcular_etiquetas_por_fila_example():
    assert calcular_etiquetas_por_fila(330, 100, 3, 0) == 3

def test_calcular_etiquetas_por_fila_margin():
    assert calcular_etiquetas_por_fila(330, 100, 3, 50) == 2


def test_calcular_etiquetas_por_fila_decimales():
    """Funciona con tamaños y separaciones decimales."""
    resultado = calcular_etiquetas_por_fila(500, 123.3, 2.5, 10)
    assert resultado == 3
