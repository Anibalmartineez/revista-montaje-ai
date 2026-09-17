"""Bounded, read-only canvas artwork from the same native slot compositor."""
from copy import deepcopy
import io
import fitz
from PIL import Image
from editor_offset_v2.application.preview_service import PreviewService, PreviewServiceError
from editor_offset_v2.application.derived_asset_service import DerivedAssetService
from editor_offset_v2.domain.geometry import validate_non_negative, validate_cardinal_rotation
from editor_offset_v2.infrastructure.pdf_compositor import compose_pdf, PT
from editor_offset_v2.infrastructure.output_snapshot import OutputSnapshot


def render_artwork(jobs, job_id, asset_id, page, spec):
    if not isinstance(spec,dict) or set(spec)-{'box','bleed','rotation','transform','derived','mirror'}:
        raise ValueError('Invalid artwork options')
    snapshot=OutputSnapshot(jobs,job_id)
    layout=snapshot.read_layout(job_id)
    asset=next((a for a in layout['assets'] if a['id']==asset_id),None)
    if asset is None: raise ValueError('Unknown asset')
    info=next((p for p in asset['pages'] if p['number']==page),None)
    box=spec.get('box','trim')
    if info is None or box not in ('media','crop','trim','bleed') or not info['boxes_mm'].get(box):
        raise ValueError('Unknown page or box')
    bleed=validate_non_negative(spec.get('bleed',0))
    if bleed>50: raise ValueError('Bleed exceeds canvas limit')
    rotation=validate_cardinal_rotation(spec.get('rotation',0))
    transform=DerivedAssetService._normalize_materialization_transform(spec.get('transform'),box)
    mirror=spec.get('mirror',False)
    if not isinstance(mirror,bool): raise ValueError('Mirror must be explicit boolean')
    selected=info['boxes_mm'][box]
    w,h=selected['width'],selected['height']
    if info['intrinsic_rotation_deg'] in (90,270): w,h=h,w
    # The SVG group supplies slot rotation; move sheet-axis offsets to its axes.
    x,y=transform['offset_mm']['x'],transform['offset_mm']['y']
    import math
    angle=math.radians(-rotation)
    transform['offset_mm']={'x':x*math.cos(angle)-y*math.sin(angle),'y':x*math.sin(angle)+y*math.cos(angle)}
    b=bleed if transform['clip_to']=='bleed_box' else 0
    width,height=w+2*b,h+2*b
    source={'asset_id':asset_id,'page':page,'pdf_box':box}
    if spec.get('derived') is not None: source['derived']=spec['derived']
    slot={'id':'canvas','face':'front','source':source,'geometry':{'position_mm':{'x_mm':width/2,'y_mm':height/2},
          'trim_size_mm':{'width':w,'height':h},'bleed_mm':bleed,'rotation_deg':0},
          'content_transform':transform,'production':{'marks_profile_id':'canvas'}}
    layout['sheet']['size_mm']={'width':width,'height':height}
    layout['slots']=[slot];layout['export']['marks_profiles']=[{'id':'canvas','crop_marks':False}]
    resolver=PreviewService(snapshot)
    coverage='complete'
    try:
        prepared=resolver._prepared_slot(slot,{asset_id:asset},job_id,mirror)
    except PreviewServiceError as exc:
        if exc.code!='BLEED_REQUIRES_EXPLICIT_MIRROR': raise
        # Display the actual trim with an uncovered margin; never invent bleed.
        trim_slot=deepcopy(slot);trim_slot['geometry']['bleed_mm']=0
        raw=resolver._prepared_slot(trim_slot,{asset_id:asset},job_id,False)
        with fitz.open(stream=raw,filetype='pdf') as src,fitz.open() as carrier:
            p=carrier.new_page(width=width*PT,height=height*PT)
            if src[0].get_contents(): p.show_pdf_page(fitz.Rect(b*PT,b*PT,(b+w)*PT,(b+h)*PT),src)
            prepared=carrier.tobytes()
        coverage='missing_bleed'
    pdf=compose_pdf(layout,('front',),lambda s:prepared)
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        scale=min(4,1200/max(doc[0].rect.width,doc[0].rect.height))
        data=doc[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).tobytes('png')
    return data,coverage
