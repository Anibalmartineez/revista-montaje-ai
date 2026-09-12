"""Gated PDF candidate renderer owned by Editor Offset V2."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from editor_offset_v2.application.preview_service import PreviewService, PreviewServiceError
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.job_repository import JobRepository, JobRepositoryError


class PdfFinalServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.issues: tuple[object, ...] = ()
        super().__init__(message)


@dataclass(frozen=True)
class PdfFinalResult:
    path: Path
    job_id: str
    revision: int
    faces: tuple[str, ...]
    dpi: int
    sha256: str


class PdfFinalService:
    """Create a deterministic, gated PDF from the V2 raster compositor."""

    def __init__(self, jobs: JobRepository):
        self._jobs = jobs
        self._preview = PreviewService(jobs)

    def render(
        self,
        job_id: str,
        *,
        face: str = "front",
        dpi: int = 150,
        allow_mirror_bleed: bool = False,
    ) -> PdfFinalResult:
        try:
            layout = self._jobs.read_layout(job_id)
        except JobRepositoryError as exc:
            status = 404 if exc.code == "JOB_NOT_FOUND" else 400 if exc.code == "INVALID_JOB_ID" else 500
            raise PdfFinalServiceError(exc.code, exc.message, status) from exc
        if validate_layout_v2(layout):
            raise PdfFinalServiceError("INVALID_LAYOUT", "The saved Layout V2 is invalid", 500)
        if face not in {"front", "back", "both"}:
            raise PdfFinalServiceError("INVALID_PDF_FINAL_FACE", "face must be front, back or both", 400)
        if isinstance(allow_mirror_bleed, bool) is False:
            raise PdfFinalServiceError("INVALID_PDF_FINAL_OPTION", "allow_mirror_bleed must be boolean", 400)
        faces = (
            tuple(item for item in ("front", "back") if layout["export"]["faces"].get(item))
            if face == "both" else (face,)
        )
        if not faces or any(item not in layout["faces"]["enabled"] for item in faces):
            raise PdfFinalServiceError("PDF_FINAL_FACE_DISABLED", "The requested output face is not enabled", 422)
        if face == "both" and len(faces) != 2:
            raise PdfFinalServiceError("PDF_FINAL_FACE_DISABLED", "Both output faces must be enabled", 422)

        pngs: list[bytes] = []
        for item in faces:
            try:
                preview = self._preview.render(
                    job_id,
                    face=item,
                    dpi=dpi,
                    allow_mirror_bleed=allow_mirror_bleed,
                )
                pngs.append(preview.path.read_bytes())
            except PreviewServiceError as exc:
                raise PdfFinalServiceError(
                    f"PDF_FINAL_{exc.code}",
                    f"PDF final is blocked by Preview validation: {exc.message}",
                    exc.status_code,
                ) from exc

        sheet = layout["sheet"]["size_mm"]
        points_per_mm = 72.0 / 25.4
        with fitz.open() as output:
            for png_data in pngs:
                page = output.new_page(
                    width=float(sheet["width"]) * points_per_mm,
                    height=float(sheet["height"]) * points_per_mm,
                )
                page.insert_image(page.rect, stream=png_data, keep_proportion=False)
            output.set_metadata({
                "format": "PDF 1.7",
                "title": f"Editor Offset V2 {layout['job']['name']}",
                "author": "Editor Offset Visual V2",
                "subject": "Gated V2 PDF candidate",
            })
            pdf_data = output.tobytes(garbage=4, deflate=True, no_new_id=True)

        outputs = self._jobs.job_path(job_id) / "outputs"
        outputs.mkdir(exist_ok=True)
        face_key = "both" if len(faces) == 2 else faces[0]
        target = outputs / f"pdf_final_r{layout['job']['revision']}_{face_key}_{dpi}.pdf"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=outputs, prefix=".pdf-final-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(pdf_data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
        except OSError as exc:
            raise PdfFinalServiceError("PDF_FINAL_PUBLISH_FAILED", "The PDF could not be published", 500) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return PdfFinalResult(
            path=target,
            job_id=job_id,
            revision=layout["job"]["revision"],
            faces=faces,
            dpi=dpi,
            sha256=hashlib.sha256(pdf_data).hexdigest(),
        )


__all__ = ["PdfFinalResult", "PdfFinalService", "PdfFinalServiceError"]
