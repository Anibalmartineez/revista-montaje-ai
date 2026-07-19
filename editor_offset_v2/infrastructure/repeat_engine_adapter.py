"""Isolated Layout V2 adapter for the existing Step & Repeat PRO engine."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from engines import step_repeat_pro_engine

from editor_offset_v2.domain.geometry import (
    Bounds,
    Point,
    Size,
    SlotGeometry,
    bleed_polygon,
    oriented_size,
    polygon_within_bounds,
    productive_size,
    slots_overlap,
    validate_finite,
)
from editor_offset_v2.domain.repeat_contract import (
    RepeatIssueV2,
    RepeatMetricsV2,
    RepeatResultV2,
)


SUPPORTED_ZONES: Final = frozenset(
    {"auto", "top", "bottom", "left", "right", "center", "fill"}
)
ZONE_ALIASES: Final = {"none": "auto"}
FLOW_ALIASES: Final = {
    "manual": "auto",
    "none": "auto",
    "rows": "horizontal",
    "columns": "vertical",
}
SUPPORTED_FLOWS: Final = frozenset({"auto", "horizontal", "vertical"})


@dataclass(frozen=True)
class _WorkPlan:
    work: dict[str, Any]
    source: dict[str, Any]
    horizontal_rotation: int | None
    vertical_rotation: int | None
    input_swapped: bool


class RepeatEngineAdapter:
    """Translate only valid Layout V2 data to and from the legacy engine boundary."""

    def __init__(
        self,
        engine: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._engine = engine or step_repeat_pro_engine.build_step_repeat_slots

    def propose(
        self,
        layout: Mapping[str, object],
        work_ids: Sequence[str],
        face: str,
        settings: Mapping[str, object],
        *,
        operation_id: str,
        generated_at: str,
        apply_mode: str,
    ) -> RepeatResultV2:
        source_layout = copy.deepcopy(dict(layout))
        printable = self._printable_bounds(source_layout)
        retained_slots = self._retained_slots(
            source_layout,
            work_ids,
            face,
            apply_mode,
        )
        empty_metrics = self._metrics(printable, (), retained_slots)
        plans, issues = self._work_plans(source_layout, work_ids, face)
        requested = sum(int(plan.work["requested_forms"]) for plan in plans)
        if issues:
            return self._failure(
                operation_id,
                generated_at,
                requested,
                empty_metrics,
                issues,
            )

        counts = {plan.work["id"]: int(plan.work["requested_forms"]) for plan in plans}
        legacy_slots, incomplete = self._run_counts(
            source_layout,
            plans,
            counts,
            face,
            settings,
        )
        warnings: list[str] = []
        if incomplete is not None:
            if not settings["allow_partial"]:
                issue = RepeatIssueV2(
                    code="INCOMPLETE_IMPOSITION",
                    level="error",
                    message="No caben todas las formas solicitadas y la parcialidad está desactivada.",
                    path="$.settings.allow_partial",
                )
                return self._failure(
                    operation_id,
                    generated_at,
                    requested,
                    empty_metrics,
                    (issue,),
                )
            counts, legacy_slots = self._find_partial_counts(
                source_layout,
                plans,
                counts,
                face,
                settings,
                incomplete,
            )
            if legacy_slots is None:
                issue = RepeatIssueV2(
                    code="NOTHING_PLACED",
                    level="error",
                    message="Ninguna forma seleccionada cabe dentro del área imprimible.",
                )
                return self._failure(
                    operation_id,
                    generated_at,
                    requested,
                    empty_metrics,
                    (issue,),
                )
            warnings.append("La propuesta es parcial: no caben todas las formas solicitadas.")

        assert legacy_slots is not None
        if settings["fill_remaining_space"]:
            counts, legacy_slots = self._fill_remaining_capacity(
                source_layout,
                plans,
                counts,
                legacy_slots,
                face,
                settings,
                printable,
            )

        slots, conversion_issues = self._normalize_slots(
            source_layout,
            plans,
            legacy_slots,
            face,
            operation_id,
            printable,
            apply_mode,
        )
        if conversion_issues:
            return self._failure(
                operation_id,
                generated_at,
                requested,
                empty_metrics,
                conversion_issues,
            )

        placed = len(slots)
        unplaced = max(0, requested - placed)
        overproduced = max(0, placed - requested)
        if unplaced and not warnings:
            warnings.append(f"Quedaron {unplaced} formas sin colocar.")
        if overproduced:
            warnings.append(f"La propuesta sobreproduce {overproduced} formas.")
        return RepeatResultV2(
            success=True,
            operation_id=operation_id,
            generated_at=generated_at,
            slots=tuple(slots),
            requested=requested,
            placed=placed,
            unplaced=unplaced,
            overproduced=overproduced,
            warnings=tuple(warnings),
            metrics=self._metrics(printable, tuple(slots), retained_slots),
            issues=tuple(
                RepeatIssueV2("PARTIAL_IMPOSITION", "warning", warning)
                for warning in warnings
            ),
        )

    @staticmethod
    def _failure(
        operation_id: str,
        generated_at: str,
        requested: int,
        metrics: RepeatMetricsV2,
        issues: Sequence[RepeatIssueV2],
    ) -> RepeatResultV2:
        return RepeatResultV2(
            success=False,
            operation_id=operation_id,
            generated_at=generated_at,
            slots=(),
            requested=requested,
            placed=0,
            unplaced=requested,
            overproduced=0,
            warnings=(),
            metrics=metrics,
            issues=tuple(issues),
        )

    @staticmethod
    def _printable_bounds(layout: Mapping[str, object]) -> Bounds:
        sheet = layout["sheet"]
        assert isinstance(sheet, Mapping)
        size = sheet["size_mm"]
        margins = sheet["printable_margins_mm"]
        assert isinstance(size, Mapping) and isinstance(margins, Mapping)
        width = float(size["width"])
        height = float(size["height"])
        return Bounds(
            float(margins["left"]),
            width - float(margins["right"]),
            float(margins["bottom"]),
            height - float(margins["top"]),
        )

    @staticmethod
    def _rotation_plan(work: Mapping[str, object]) -> tuple[int | None, int | None, bool]:
        rotations = tuple(int(value) for value in work["allowed_rotations_deg"])
        horizontal = next((value for value in (0, 180) if value in rotations), None)
        vertical = next((value for value in (90, 270) if value in rotations), None)
        return horizontal, vertical, horizontal is None

    def _work_plans(
        self,
        layout: Mapping[str, object],
        work_ids: Sequence[str],
        face: str,
    ) -> tuple[list[_WorkPlan], tuple[RepeatIssueV2, ...]]:
        works = {item["id"]: item for item in layout["works"]}
        assets = {item["id"]: item for item in layout["assets"]}
        plans: list[_WorkPlan] = []
        issues: list[RepeatIssueV2] = []
        for index, work_id in enumerate(work_ids):
            work = works.get(work_id)
            if work is None:
                issues.append(
                    RepeatIssueV2(
                        "WORK_NOT_FOUND",
                        "error",
                        "El work seleccionado no existe.",
                        f"$.work_ids[{index}]",
                        work_id=work_id,
                    )
                )
                continue
            source_name = "front_source" if face == "front" else "back_source"
            source = work.get(source_name)
            if not isinstance(source, dict):
                issues.append(
                    RepeatIssueV2(
                        "SOURCE_NOT_FOUND",
                        "error",
                        f"El work no tiene fuente para la cara {face}.",
                        f"$.works[{work_id}].{source_name}",
                        work_id=work_id,
                    )
                )
                continue
            asset = assets.get(source.get("asset_id"))
            if asset is None:
                issues.append(
                    RepeatIssueV2(
                        "ASSET_NOT_FOUND",
                        "error",
                        "La fuente del work referencia un asset inexistente.",
                        f"$.works[{work_id}].{source_name}.asset_id",
                        work_id=work_id,
                        asset_id=source.get("asset_id"),
                    )
                )
                continue
            if asset.get("status") != "ready":
                issues.append(
                    RepeatIssueV2(
                        "NON_EXPORTABLE_ASSET",
                        "error",
                        "Repeat requiere un asset físico con estado ready; los placeholders no son válidos.",
                        f"$.assets[{asset['id']}].status",
                        work_id=work_id,
                        asset_id=asset["id"],
                    )
                )
                continue
            page = next(
                (item for item in asset["pages"] if item["number"] == source.get("page")),
                None,
            )
            if page is None:
                issues.append(
                    RepeatIssueV2(
                        "PAGE_NOT_FOUND",
                        "error",
                        "La página seleccionada no existe en el asset.",
                        f"$.works[{work_id}].{source_name}.page",
                        work_id=work_id,
                        asset_id=asset["id"],
                    )
                )
                continue
            if page["boxes_mm"].get(source.get("pdf_box")) is None:
                issues.append(
                    RepeatIssueV2(
                        "PDF_BOX_NOT_FOUND",
                        "error",
                        "La caja PDF seleccionada está ausente.",
                        f"$.works[{work_id}].{source_name}.pdf_box",
                        work_id=work_id,
                        asset_id=asset["id"],
                    )
                )
                continue
            horizontal, vertical, swapped = self._rotation_plan(work)
            plans.append(
                _WorkPlan(
                    work=copy.deepcopy(work),
                    source=copy.deepcopy(source),
                    horizontal_rotation=horizontal,
                    vertical_rotation=vertical,
                    input_swapped=swapped,
                )
            )
        return plans, tuple(issues)

    @staticmethod
    def _zone(work: Mapping[str, object], settings: Mapping[str, object]) -> str:
        if not settings.get("respect_preferred_zones"):
            return "auto"
        raw = str(work.get("preferred_zone") or "auto").strip().lower()
        value = ZONE_ALIASES.get(raw, raw)
        return value if value in SUPPORTED_ZONES else "auto"

    @staticmethod
    def _flow(work: Mapping[str, object]) -> str:
        raw = str(work.get("preferred_flow") or "auto").strip().lower()
        value = FLOW_ALIASES.get(raw, raw)
        return value if value in SUPPORTED_FLOWS else "auto"

    def _engine_layout(
        self,
        layout: Mapping[str, object],
        plans: Sequence[_WorkPlan],
        counts: Mapping[str, int],
        face: str,
        settings: Mapping[str, object],
    ) -> dict[str, Any]:
        sheet = layout["sheet"]
        size = sheet["size_mm"]
        margins = sheet["printable_margins_mm"]
        designs: list[dict[str, object]] = []
        ordered_plans = list(plans)
        if settings.get("respect_priority"):
            ordered_plans.sort(key=lambda item: (float(item.work["priority"]), item.work["id"]))
        for plan in ordered_plans:
            count = int(counts.get(plan.work["id"], 0))
            if count <= 0:
                continue
            trim = plan.work["trim_size_mm"]
            width = float(trim["height"] if plan.input_swapped else trim["width"])
            height = float(trim["width"] if plan.input_swapped else trim["height"])
            designs.append(
                {
                    "ref": plan.work["id"],
                    "filename": plan.work["name"],
                    "work_id": plan.work["id"],
                    "width_mm": width,
                    "height_mm": height,
                    "bleed_mm": float(plan.work["bleed_mm"]),
                    "forms_per_plate": count,
                    "allow_rotation": plan.horizontal_rotation is not None
                    and plan.vertical_rotation is not None,
                    "priority": float(plan.work["priority"]),
                    "preferred_zone": self._zone(plan.work, settings),
                    "preferred_flow": self._flow(plan.work),
                    "repeat_role": "fill" if self._zone(plan.work, settings) == "fill" else "secondary",
                    "repeat_manual_overrides": {
                        "priority": True,
                        "preferred_flow": True,
                        "repeat_role": True,
                    },
                }
            )
        return {
            "sheet_mm": [float(size["width"]), float(size["height"])],
            "margins_mm": [
                float(margins["left"]),
                float(margins["right"]),
                float(margins["top"]),
                float(margins["bottom"]),
            ],
            "bleed_default_mm": 0.0,
            "gap_default_mm": 0.0,
            "designs": designs,
            "slots": [],
            "faces": [face],
            "active_face": face,
            "imposition_engine": "repeat",
            "allowed_engines": ["repeat"],
            "spacingSettings": {
                "spacingX_mm": float(settings["horizontal_gap_mm"]),
                "spacingY_mm": float(settings["vertical_gap_mm"]),
            },
        }

    def _run_counts(
        self,
        layout: Mapping[str, object],
        plans: Sequence[_WorkPlan],
        counts: Mapping[str, int],
        face: str,
        settings: Mapping[str, object],
    ) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
        if not any(value > 0 for value in counts.values()):
            return [], None
        engine_layout = self._engine_layout(layout, plans, counts, face, settings)
        try:
            return copy.deepcopy(self._engine(engine_layout)), None
        except step_repeat_pro_engine.IncompleteImpositionError as exc:
            return None, copy.deepcopy(exc.details)

    def _find_partial_counts(
        self,
        layout: Mapping[str, object],
        plans: Sequence[_WorkPlan],
        initial: Mapping[str, int],
        face: str,
        settings: Mapping[str, object],
        first_details: Sequence[Mapping[str, object]],
    ) -> tuple[dict[str, int], list[dict[str, Any]] | None]:
        counts = dict(initial)
        details = list(first_details)
        while sum(counts.values()) > 0:
            placed = {
                str(item.get("design_ref")): max(0, int(item.get("placed_forms") or 0))
                for item in details
            }
            candidate = {
                work_id: min(count, placed.get(work_id, count))
                for work_id, count in counts.items()
            }
            if sum(candidate.values()) >= sum(counts.values()):
                for plan in reversed(plans):
                    work_id = plan.work["id"]
                    if candidate[work_id] > 0:
                        candidate[work_id] -= 1
                        break
            counts = candidate
            slots, incomplete = self._run_counts(layout, plans, counts, face, settings)
            if incomplete is None:
                return counts, slots
            details = incomplete
        return counts, None

    def _fill_remaining_capacity(
        self,
        layout: Mapping[str, object],
        plans: Sequence[_WorkPlan],
        initial_counts: Mapping[str, int],
        initial_slots: list[dict[str, Any]],
        face: str,
        settings: Mapping[str, object],
        printable: Bounds,
    ) -> tuple[dict[str, int], list[dict[str, Any]]]:
        counts = dict(initial_counts)
        best_slots = initial_slots
        ordered = list(plans)
        if settings.get("respect_priority"):
            ordered.sort(key=lambda item: (float(item.work["priority"]), item.work["id"]))
        for plan in ordered:
            trim = Size(
                float(plan.work["trim_size_mm"]["width"]),
                float(plan.work["trim_size_mm"]["height"]),
            )
            product = productive_size(trim, plan.work["bleed_mm"])
            upper = max(
                counts[plan.work["id"]],
                int((printable.width * printable.height) // (product.width * product.height)),
            )
            low = counts[plan.work["id"]]
            high = upper
            while low < high:
                midpoint = (low + high + 1) // 2
                trial = dict(counts)
                trial[plan.work["id"]] = midpoint
                slots, incomplete = self._run_counts(layout, plans, trial, face, settings)
                if incomplete is None and slots is not None:
                    low = midpoint
                    best_slots = slots
                else:
                    high = midpoint - 1
            counts[plan.work["id"]] = low
            slots, incomplete = self._run_counts(layout, plans, counts, face, settings)
            if incomplete is None and slots is not None:
                best_slots = slots
        return counts, best_slots

    @staticmethod
    def _slot_geometry(slot: Mapping[str, object]) -> SlotGeometry:
        geometry = slot["geometry"]
        position = geometry["position_mm"]
        trim = geometry["trim_size_mm"]
        return SlotGeometry(
            Point(position["x_mm"], position["y_mm"]),
            Size(trim["width"], trim["height"]),
            geometry["bleed_mm"],
            geometry["rotation_deg"],
        )

    def _normalize_slots(
        self,
        layout: Mapping[str, object],
        plans: Sequence[_WorkPlan],
        legacy_slots: Sequence[Mapping[str, object]],
        face: str,
        operation_id: str,
        printable: Bounds,
        apply_mode: str,
    ) -> tuple[list[dict[str, Any]], tuple[RepeatIssueV2, ...]]:
        by_work = {plan.work["id"]: plan for plan in plans}
        marks_profile = layout["export"]["default_marks_profile_id"]
        normalized: list[dict[str, Any]] = []
        issues: list[RepeatIssueV2] = []
        for index, legacy in enumerate(legacy_slots):
            work_id = str(legacy.get("design_ref") or "")
            plan = by_work.get(work_id)
            if plan is None:
                issues.append(
                    RepeatIssueV2(
                        "UNKNOWN_ENGINE_WORK",
                        "error",
                        "El motor devolvió un work desconocido.",
                        work_id=work_id or None,
                    )
                )
                continue
            engine_rotation = legacy.get("rotation_deg")
            if engine_rotation not in (0, 90):
                issues.append(
                    RepeatIssueV2(
                        "INVALID_ENGINE_ROTATION",
                        "error",
                        "El motor devolvió una rotación no soportada por el adaptador.",
                        work_id=work_id,
                    )
                )
                continue
            if plan.input_swapped:
                if engine_rotation != 0 or plan.vertical_rotation is None:
                    issues.append(
                        RepeatIssueV2(
                            "INVALID_ENGINE_ROTATION",
                            "error",
                            "La orientación vertical exclusiva no fue respetada por el motor.",
                            work_id=work_id,
                        )
                    )
                    continue
                rotation = plan.vertical_rotation
            elif engine_rotation == 90:
                if plan.vertical_rotation is None:
                    issues.append(
                        RepeatIssueV2(
                            "INVALID_ENGINE_ROTATION",
                            "error",
                            "El motor usó una orientación vertical no permitida por el work.",
                            work_id=work_id,
                        )
                    )
                    continue
                rotation = plan.vertical_rotation
            else:
                if plan.horizontal_rotation is None:
                    issues.append(
                        RepeatIssueV2(
                            "INVALID_ENGINE_ROTATION",
                            "error",
                            "El motor usó una orientación horizontal no permitida por el work.",
                            work_id=work_id,
                        )
                    )
                    continue
                rotation = plan.horizontal_rotation

            trim = Size(
                plan.work["trim_size_mm"]["width"],
                plan.work["trim_size_mm"]["height"],
            )
            oriented_productive = oriented_size(
                productive_size(trim, plan.work["bleed_mm"]),
                rotation,
            )
            try:
                left = validate_finite(legacy.get("x_mm"), "engine.x_mm")
                bottom = validate_finite(legacy.get("y_mm"), "engine.y_mm")
                center = Bounds(
                    left,
                    left + oriented_productive.width,
                    bottom,
                    bottom + oriented_productive.height,
                ).center
            except ValueError as exc:
                issues.append(
                    RepeatIssueV2(
                        "INVALID_ENGINE_POSITION",
                        "error",
                        str(exc),
                        work_id=work_id,
                    )
                )
                continue
            slot_id = f"slot_{operation_id}_{index + 1:04d}"
            source = copy.deepcopy(plan.source)
            slot = {
                "id": slot_id,
                "face": face,
                "work_id": work_id,
                "source": source,
                "geometry": {
                    "position_mm": {
                        "x_mm": center.x,
                        "y_mm": center.y,
                        "anchor": "trim_center",
                    },
                    "trim_size_mm": copy.deepcopy(plan.work["trim_size_mm"]),
                    "bleed_mm": float(plan.work["bleed_mm"]),
                    "rotation_deg": rotation,
                },
                "content_transform": {
                    "fit_mode": "actual_size",
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "offset_mm": {"x": 0.0, "y": 0.0},
                    "rotation_deg": 0,
                    "mirror_x": False,
                    "mirror_y": False,
                    "clip_to": "bleed_box" if source["pdf_box"] == "bleed" else "trim_box",
                },
                "locks": {
                    "geometry": [],
                    "content": [],
                    "production": [],
                    "delete": [],
                },
                "production": {"marks_profile_id": marks_profile},
                "generated_by": {
                    "type": "engine",
                    "engine": "repeat",
                    "operation_id": operation_id,
                },
            }
            geometry = self._slot_geometry(slot)
            if not polygon_within_bounds(bleed_polygon(geometry), printable):
                issues.append(
                    RepeatIssueV2(
                        "ENGINE_SLOT_OUT_OF_BOUNDS",
                        "error",
                        "El footprint productivo generado sale del área imprimible.",
                        slot_id=slot_id,
                        work_id=work_id,
                        asset_id=source["asset_id"],
                    )
                )
                continue
            normalized.append(slot)

        for index, slot in enumerate(normalized):
            geometry = self._slot_geometry(slot)
            for other in normalized[index + 1 :]:
                if slots_overlap(geometry, self._slot_geometry(other), use_bleed=True):
                    issues.append(
                        RepeatIssueV2(
                            "ENGINE_SLOT_OVERLAP",
                            "error",
                            "Dos slots propuestos se solapan por su footprint productivo.",
                            slot_id=slot["id"],
                            work_id=slot["work_id"],
                        )
                    )
                    break

        selected_ids = set(by_work)
        existing = [
            slot
            for slot in layout["slots"]
            if slot["face"] == face
            and not (
                apply_mode == "replace_work_face" and slot["work_id"] in selected_ids
            )
        ]
        for slot in normalized:
            geometry = self._slot_geometry(slot)
            for current in existing:
                if slots_overlap(geometry, self._slot_geometry(current), use_bleed=True):
                    issues.append(
                        RepeatIssueV2(
                            "OVERLAP_EXISTING_SLOT",
                            "error",
                            "La propuesta se solapa con un slot existente de la misma cara.",
                            slot_id=slot["id"],
                            work_id=slot["work_id"],
                        )
                    )
                    break
        return normalized, tuple(issues)

    @staticmethod
    def _retained_slots(
        layout: Mapping[str, object],
        work_ids: Sequence[str],
        face: str,
        apply_mode: str,
    ) -> tuple[Mapping[str, object], ...]:
        selected = set(work_ids)
        return tuple(
            slot
            for slot in layout["slots"]
            if slot["face"] == face
            and not (
                apply_mode == "replace_work_face"
                and slot["work_id"] in selected
            )
        )

    def _metrics(
        self,
        printable: Bounds,
        proposal_slots: Sequence[Mapping[str, object]],
        retained_slots: Sequence[Mapping[str, object]],
    ) -> RepeatMetricsV2:
        def occupied_area(slots: Sequence[Mapping[str, object]]) -> float:
            occupied = 0.0
            for slot in slots:
                geometry = self._slot_geometry(slot)
                product = productive_size(geometry.trim_size, geometry.bleed)
                occupied += product.width * product.height
            return occupied

        proposal_occupied = occupied_area(proposal_slots)
        retained_occupied = occupied_area(retained_slots)
        projected_occupied = proposal_occupied + retained_occupied
        area = printable.width * printable.height
        proposal_utilization = proposal_occupied / area * 100.0 if area > 0 else 0.0
        projected_utilization = projected_occupied / area * 100.0 if area > 0 else 0.0
        return RepeatMetricsV2(
            printable_width_mm=printable.width,
            printable_height_mm=printable.height,
            printable_area_mm2=area,
            occupied_productive_area_mm2=proposal_occupied,
            utilization_percent=proposal_utilization,
            proposal_utilization_pct=proposal_utilization,
            projected_total_occupied_productive_area_mm2=projected_occupied,
            projected_total_utilization_pct=projected_utilization,
        )


__all__ = ["RepeatEngineAdapter"]
