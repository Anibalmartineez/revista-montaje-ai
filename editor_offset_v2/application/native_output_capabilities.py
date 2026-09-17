"""Capabilities of V2's own renderer; never imports the legacy bridge."""
from editor_offset_v2.domain.output_contract import OutputIssue

NATIVE_VECTOR_AVAILABLE = True  # Native form compositor, covered by phase 39B object tests.
MAX_INTERMEDIATE_PIXELS = 24_000_000

def native_output_issues(layout, options=None):
    options = options or {}
    result = []
    def add(code, message, path, blocks=('preview','pdf_final'), slot=None):
        result.append((OutputIssue(code=code,level='error',message=message,path=path,
            slot_id=slot['id'] if slot else None,asset_id=slot['source']['asset_id'] if slot else None),list(blocks)))
    export = layout['export']
    if export['render_mode']=='raster' and export['preserve_vector_content']:
        add('OUTPUT_PROFILE_CONFLICT','Un perfil raster no puede preservar vectores.','$.export',('pdf_final',))
    if layout['ctp']['enabled']:
        add('CTP_NOT_SUPPORTED','La salida CTP todavía no está soportada.','$.ctp')
    if export['crop_to_content']:
        add('OUTPUT_CROP_UNSUPPORTED','El perfil conserva el tamaño completo del pliego.','$.export.crop_to_content')
    if export['preserve_vector_content'] and not NATIVE_VECTOR_AVAILABLE:
        add('NATIVE_VECTOR_PENDING','La preservación vectorial requiere el compositor PDF nativo; el candidato raster no satisface este perfil.','$.export.preserve_vector_content',('pdf_final',))
    faces = [options['face']] if options.get('face') in ('front','back') else [f for f in export['faces']['order'] if export['faces'].get(f)]
    for face in faces:
        if face not in layout['faces']['enabled'] or not export['faces'].get(face):
            add('OUTPUT_FACE_DISABLED','La cara solicitada no está habilitada.','$.export.faces')
        if not any(s['face']==face for s in layout['slots']):
            add('OUTPUT_NO_SLOTS','La cara solicitada no tiene piezas.','$.slots')
    profiles = {p['id']:p for p in export['marks_profiles']}
    for i, slot in enumerate(layout['slots']):
        if slot['face'] not in faces: continue
        path = f'$.slots[{i}]'
        transform = slot['content_transform']
        if transform['clip_to']=='none':
            add('UNSUPPORTED_CONTENT_CLIP','Selecciona clipping TrimBox o BleedBox antes de generar salida.',path+'.content_transform.clip_to',slot=slot)
        if slot['geometry']['bleed_mm']>0 and transform['clip_to']=='trim_box':
            # Preview can illustrate an intentional trim clip; final cannot claim bleed.
            add('BLEED_CLIPPED_TO_TRIM','El clipping TrimBox descarta el sangrado solicitado; cambia a BleedBox explícitamente.',path+'.content_transform.clip_to',('pdf_final',),slot)
        profile = profiles[slot['production']['marks_profile_id']]
        if profile['crop_marks']:
            from editor_offset_v2.infrastructure.pdf_compositor import crop_segments, slot_geometry
            from editor_offset_v2.domain.geometry import trim_bounds
            lines=crop_segments(slot)
            sheet=layout['sheet']['size_mm']
            if any(not (0<=x<=sheet['width'] and 0<=y<=sheet['height']) for line in lines for x,y in line):
                add('CROP_MARK_OUTSIDE_SHEET','Las marcas de corte exceden el pliego; mueve la pieza o desactiva sus marcas.',path+'.production',slot=slot)
            for other in layout['slots']:
                if other['id']==slot['id'] or other['face']!=slot['face']: continue
                bounds=trim_bounds(slot_geometry(other))
                if any(max(a[0],b[0])+.1>bounds.left and min(a[0],b[0])-.1<bounds.right and
                       max(a[1],b[1])+.1>bounds.bottom and min(a[1],b[1])-.1<bounds.top for a,b in lines):
                    add('CROP_MARK_OVERPRINT','Una marca invade el trim de otra pieza; aumenta la separación o desactiva las marcas.',path+'.production',('pdf_final',),slot)
                    break
        if any(profile[k] for k in ('registration_marks','technical_text','color_bar')):
            add('PREVIEW_MARKS_UNSUPPORTED','Registros, barras de color y texto técnico aún no están soportados.',path+'.production',slot=slot)
        width, height = (slot['geometry']['trim_size_mm'][k]+2*slot['geometry']['bleed_mm'] for k in ('width','height'))
        # Bound both source raster and scaled intermediates before allocating.
        dpi = options.get('dpi',150)
        pixels = width*height*(dpi/25.4)**2
        if max(pixels,pixels*transform['scale_x']*transform['scale_y'])>MAX_INTERMEDIATE_PIXELS:
            add('OUTPUT_RESOURCE_LIMIT','La pieza o su transformación supera el presupuesto de imagen; reduce resolución o escala.',path+'.content_transform',slot=slot)
    return result
