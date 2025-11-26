from __future__ import annotations

import os
import subprocess
from typing import Optional

import fitz  # PyMuPDF

# Módulo utilitario para normalizar PDFs generados; no altera parámetros de
# sangrado ni geometría, solo compatibilidad y metadatos.


def _rewrite_with_pymupdf(
    src: str,
    dst: str,
    pdf_version: str = "1.4",
    disable_compression: bool = True,
    linearize: bool = False,
    xmp_title: str = "Montaje Offset Inteligente",
    creator: str = "Creativa CTP",
):
    """
    Vuelca el PDF con PyMuPDF, fija metadatos básicos y deja la estructura legible
    por Illustrator/Indesign. No usa object streams ni xref streams.
    """
    doc = fitz.open(src)
    # metadatos mínimos
    meta = doc.metadata or {}
    meta["format"] = f"PDF {pdf_version}"
    meta["title"] = meta.get("title") or xmp_title
    meta["creator"] = meta.get("creator") or creator
    meta["producer"] = meta.get("producer") or "Montaje Offset Inteligente"
    doc.set_metadata(meta)
    # guardado “amigable” (sin compress agresivo, sin linearize)
    doc.save(
        dst,
        deflate=not disable_compression,
        garbage=0,
        clean=False,
        incremental=False,
    )
    doc.close()


def _have_exe(name: str) -> bool:
    from shutil import which

    return which(name) is not None


def _qpdf_rewrite(
    src: str,
    dst: str,
    force_version: str = "1.4",
    disable_obj_streams: bool = True,
    decompress: bool = True,
):
    """
    Usa qpdf si está disponible para desactivar object streams/xref streams y forzar versión.
    """
    args = ["qpdf", "--warning-exit-0", "--no-warn", "--linearize=disable"]
    if disable_obj_streams:
        args += ["--object-streams=disable"]
    if decompress:
        args += ["--stream-data=uncompress"]
    if force_version:
        args += ["--force-version=" + force_version]
    args += [src, dst]
    subprocess.run(args, check=True)


def _ghostscript_pdfx1a(src: str, dst: str) -> bool:
    """
    Intenta convertir a PDF/X-1a con Ghostscript si está instalado.
    Retorna True si se generó dst, False si no se pudo.
    """
    if not _have_exe("gs"):
        return False
    # Joboptions aproximados para X-1a (sin transparencias ni object streams)
    args = [
        "gs",
        "-dBATCH",
        "-dNOPAUSE",
        "-dSAFER",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.3",
        "-dPDFSETTINGS=/prepress",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        "-dDownsampleColorImages=false",
        "-dDownsampleGrayImages=false",
        "-dDownsampleMonoImages=false",
        "-dColorImageDownsampleType=/None",
        "-dAutoRotatePages=/None",
        "-sOutputFile=" + dst,
        src,
    ]
    try:
        subprocess.run(args, check=True)
        return os.path.exists(dst) and os.path.getsize(dst) > 0
    except Exception:
        return False


def to_adobe_compatible(src: str) -> Optional[str]:
    """
    Genera una copia _ADOBE.pdf versión 1.4, sin object streams/xref streams
    y con metadatos mínimos. Prioriza qpdf; si no está, usa PyMuPDF.
    """
    base, _ = os.path.splitext(src)
    dst = base + "_ADOBE.pdf"
    try:
        if _have_exe("qpdf"):
            _qpdf_rewrite(src, dst, force_version="1.4", disable_obj_streams=True, decompress=True)
        else:
            _rewrite_with_pymupdf(src, dst, pdf_version="1.4", disable_compression=True)
        return dst
    except Exception as e:
        print("[WARN] to_adobe_compatible failed:", e)
        return None


def to_pdfx1a(src: str) -> Optional[str]:
    """
    Intenta producir _PDFX1a.pdf. Si no hay Ghostscript, hace fallback a 1.4 “amigable”.
    """
    base, _ = os.path.splitext(src)
    dst = base + "_PDFX1a.pdf"
    # Intento con Ghostscript
    if _ghostscript_pdfx1a(src, dst):
        return dst
    # Fallback “amigable” (no es 100% X-1a, pero abre bien en suites Adobe)
    try:
        if _have_exe("qpdf"):
            _qpdf_rewrite(src, dst, force_version="1.4", disable_obj_streams=True, decompress=True)
        else:
            _rewrite_with_pymupdf(src, dst, pdf_version="1.4", disable_compression=True)
        return dst
    except Exception as e:
        print("[WARN] to_pdfx1a fallback failed:", e)
        return None


def apply_pdf_compat(path_in: str, mode: Optional[str]) -> Optional[str]:
    """
    Enruta según el modo. Devuelve la ruta del nuevo PDF o None si no aplica.
    """
    if not mode:
        return None
    mode = mode.strip().lower()
    if mode == "adobe_compatible":
        return to_adobe_compatible(path_in)
    if mode == "pdfx1a":
        return to_pdfx1a(path_in)
    return None
