"""Layout V2 source validation, native Repeat packing and slot construction."""
from __future__ import annotations

import copy
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from editor_offset_v2.domain.geometry import (
    Bounds, Point, Size, SlotGeometry, bleed_bounds, bleed_polygon,
    polygon_within_bounds, productive_size, slots_overlap,
)
from editor_offset_v2.domain.repeat_contract import RepeatIssueV2, RepeatMetricsV2, RepeatResultV2
from editor_offset_v2.domain.repeat_packer import (
    ENGINE_VERSION, MAX_PLACEMENTS, Piece, PackingProblem, PackingResult, pack, separated,
)

ZONE_ALIASES = {"none":"auto"}
FLOW_ALIASES = {"manual":"auto", "none":"auto", "rows":"horizontal", "columns":"vertical"}
SUPPORTED_ZONES = frozenset({"auto","top","bottom","left","right","center","fill"})
SUPPORTED_FLOWS = frozenset({"auto","horizontal","vertical"})

@dataclass(frozen=True)
class _WorkPlan:
    work: dict[str, Any]
    source: dict[str, Any]


class RepeatEngineAdapter:
    """Own V2 boundary. No legacy product imports, translation or fallback."""
    engine_version = ENGINE_VERSION

    def __init__(self, engine: Callable[[PackingProblem], PackingResult] | None = None):
        self._engine = engine or pack

    def propose(self, layout, work_ids, face, settings, *, operation_id, generated_at, apply_mode):
        layout = copy.deepcopy(dict(layout))
        printable = self._printable_bounds(layout)
        retained = self._retained_slots(layout,work_ids,face,apply_mode)
        plans, source_issues = self._work_plans(layout,work_ids,face)
        requested = sum(int(p.work['requested_forms']) for p in plans)
        empty_metrics = self._metrics(printable,(),retained)
        def failure(issues):
            return RepeatResultV2(False,operation_id,generated_at,(),requested,0,requested,0,(),
                empty_metrics,tuple(issues),self.engine_version,self._counts(plans,()))
        if source_issues: return failure(source_issues)
        if apply_mode == 'replace_work_face':
            locked=[s for s in layout['slots'] if s['face']==face and s['work_id'] in work_ids and s['locks']['delete']]
            if locked:
                return failure([RepeatIssueV2('REPLACE_LOCKED','error',
                    'Un bloqueo de eliminación impide reemplazar este slot.',slot_id=s['id'],work_id=s['work_id']) for s in locked])
        pieces=[]
        for plan in plans:
            work=plan.work
            zone=ZONE_ALIASES.get(work['preferred_zone'].strip().lower(),work['preferred_zone'].strip().lower())
            flow=FLOW_ALIASES.get(work['preferred_flow'].strip().lower(),work['preferred_flow'].strip().lower())
            if flow not in SUPPORTED_FLOWS or zone not in SUPPORTED_ZONES:
                return failure([RepeatIssueV2('UNSUPPORTED_PREFERENCE','error',
                    'La zona o el flujo preferido no tiene interpretación en Repeat V2.',work_id=work['id'])])
            trim=Size(work['trim_size_mm']['width'],work['trim_size_mm']['height'])
            pieces.append(Piece(work['id'],productive_size(trim,work['bleed_mm']),work['requested_forms'],
                tuple(work['allowed_rotations_deg']),work['priority'],
                zone if settings.get('respect_preferred_zones') else 'auto',flow))
        problem=PackingProblem(printable,tuple(pieces),float(settings['horizontal_gap_mm']),
            float(settings['vertical_gap_mm']),tuple(bleed_bounds(self._slot_geometry(s)) for s in retained),
            bool(settings['fill_remaining_space']),bool(settings.get('respect_priority')),
            settings.get('distribution','auto'))
        result=self._engine(problem)
        issues=[]
        if result.limited:
            issues.append(RepeatIssueV2('CALCULATION_LIMIT','warning',
                'Se alcanzó el límite de cálculo de Repeat V2; no se certifica la capacidad restante.'))
        for work_id in result.oversized:
            issues.append(RepeatIssueV2('PIECE_EXCEEDS_PRINTABLE_AREA','warning',
                'La pieza, incluido el sangrado, supera el área imprimible en todos sus giros permitidos.',work_id=work_id))
        slots, validation_issues=self._normalize_slots(layout,plans,result.placements,face,operation_id,printable,retained,settings)
        if validation_issues: return failure(validation_issues)
        counts=self._counts(plans,slots)
        unplaced=sum(c['unplaced'] for c in counts)
        overproduced=sum(c['overproduced'] for c in counts)
        if overproduced and (not settings['fill_remaining_space'] or unplaced):
            return failure([RepeatIssueV2('INVALID_ENGINE_COUNTS','error','El motor produjo extras fuera de la política solicitada.')])
        if unplaced and (not settings['allow_partial'] or not slots):
            issues.append(RepeatIssueV2('INCOMPLETE_IMPOSITION','error',
                'La búsqueda no encontró una distribución completa. No demuestra que las piezas no quepan; revisa área, giros, separaciones y obstáculos.'))
            return failure([RepeatIssueV2(i.code,'error',i.message,i.path,i.work_id,i.slot_id,i.asset_id) for i in issues])
        if unplaced:
            issues.append(RepeatIssueV2('PARTIAL_IMPOSITION','warning',f'Propuesta parcial: faltan {unplaced} formas.'))
        if overproduced:
            issues.append(RepeatIssueV2('OVERPRODUCTION','warning',f'El relleno añade {overproduced} formas adicionales.'))
        profiles={p['id']:p for p in layout['export']['marks_profiles']}
        omitted={s['work_id'] for s in slots if s['geometry']['bleed_mm']==0
                 and profiles[s['production']['marks_profile_id']]['crop_marks']}
        if omitted:
            issues.append(RepeatIssueV2('CROP_MARKS_OMITTED_NO_BLEED','warning',
                f'Marcas de corte omitidas en {len(omitted)} trabajos sin sangrado; se conservará el contenido.'))
        return RepeatResultV2(True,operation_id,generated_at,tuple(slots),requested,len(slots),unplaced,overproduced,
            tuple(i.message for i in issues),self._metrics(printable,slots,retained),tuple(issues),self.engine_version,counts)

    @staticmethod
    def _counts(plans, slots):
        counts=Counter(s['work_id'] for s in slots)
        return tuple({'work_id':p.work['id'],'requested':p.work['requested_forms'],
            'placed':counts[p.work['id']], 'unplaced':max(0,p.work['requested_forms']-counts[p.work['id']]),
            'overproduced':max(0,counts[p.work['id']]-p.work['requested_forms'])} for p in plans)

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
            plans.append(
                _WorkPlan(
                    work=copy.deepcopy(work),
                    source=copy.deepcopy(source),
                )
            )
        return plans, tuple(issues)

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

    def _normalize_slots(self, layout, plans, placements, face, operation_id, printable, retained, settings):
        by_work={plan.work['id']:plan for plan in plans}
        marks_profile=layout['export']['default_marks_profile_id']
        normalized=[]; issues=[]
        if len(placements)>MAX_PLACEMENTS:
            return [],(RepeatIssueV2('INVALID_ENGINE_COUNTS','error','El resultado excede el límite de slots.'),)
        for index, placement in enumerate(placements):
            work_id=placement.work_id
            plan=by_work.get(work_id)
            if plan is None:
                issues.append(RepeatIssueV2('UNKNOWN_ENGINE_WORK','error','Trabajo desconocido en la propuesta.',work_id=work_id))
                continue
            rotation=placement.rotation
            if rotation not in plan.work['allowed_rotations_deg']:
                issues.append(RepeatIssueV2('INVALID_ENGINE_ROTATION','error','El giro no está permitido por el trabajo.',work_id=work_id))
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
                        "x_mm": placement.bounds.center.x,
                        "y_mm": placement.bounds.center.y,
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
            geometry=self._slot_geometry(slot)
            actual=bleed_bounds(geometry)
            if abs(actual.width-placement.bounds.width)>1e-7 or abs(actual.height-placement.bounds.height)>1e-7:
                issues.append(RepeatIssueV2('INVALID_ENGINE_SIZE','error','La huella propuesta no coincide con el trabajo.',work_id=work_id))
            if not polygon_within_bounds(bleed_polygon(geometry),printable):
                issues.append(RepeatIssueV2('ENGINE_SLOT_OUT_OF_BOUNDS','error','La huella productiva sale del imprimible.',slot_id=slot_id))
            normalized.append(slot)
        geometries=[self._slot_geometry(s) for s in normalized]
        bounds=[bleed_bounds(g) for g in geometries]
        retained_bounds=[bleed_bounds(self._slot_geometry(s)) for s in retained]
        # IDs are global, including the other face. Only actual replacements may reuse one.
        retained_ids={s['id'] for s in retained} | {s['id'] for s in layout['slots'] if s['face']!=face}
        for index, slot in enumerate(normalized):
            if slot['id'] in retained_ids:
                issues.append(RepeatIssueV2('ENGINE_SLOT_ID_COLLISION','error','El ID propuesto ya existe.',slot_id=slot['id']))
            for other in range(index+1,len(normalized)):
                if not separated(bounds[index],bounds[other],settings['horizontal_gap_mm'],settings['vertical_gap_mm']):
                    code='ENGINE_SLOT_OVERLAP' if slots_overlap(geometries[index],geometries[other],use_bleed=True) else 'ENGINE_SLOT_GAP'
                    issues.append(RepeatIssueV2(code,'error','Las huellas propuestas no respetan solapes/separaciones.',slot_id=slot['id']))
                    break
            if any(not separated(bounds[index],b,settings['horizontal_gap_mm'],settings['vertical_gap_mm']) for b in retained_bounds):
                issues.append(RepeatIssueV2('OVERLAP_EXISTING_SLOT','error','La propuesta no respeta un obstáculo o su separación.',slot_id=slot['id']))
        return normalized,tuple(issues)

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
