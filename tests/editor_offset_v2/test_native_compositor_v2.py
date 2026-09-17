"""Independent object/metric oracles for the native V2 compositor."""
import copy
import io
import math
import fitz
import pytest
from PIL import Image
from test_output_safety_v2 import case
from editor_offset_v2.infrastructure.pdf_compositor import compose_pdf, crop_segments, PT


def source_pdf():
    with fitz.open() as doc:
        p=doc.new_page(width=40*PT,height=20*PT)
        p.draw_rect(fitz.Rect(0,0,20*PT,20*PT),color=None,fill=(1,0,0))
        p.draw_rect(fitz.Rect(20*PT,0,40*PT,20*PT),color=None,fill=(0,0,1))
        p.insert_text((2*PT,4*PT),'VECTOR',fontsize=6,color=(0,0,0,1))
        return doc.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('internal',[0,90,180,270])
@pytest.mark.parametrize('mirror',[(False,False),(True,False),(False,True),(True,True)])
def test_native_cardinals_mirrors_and_sheet_offsets(case,rotation,internal,mirror):
    _,_,_,saved,_=case
    layout=copy.deepcopy(saved['layout']);slot=layout['slots'][0]
    layout['sheet']['size_mm']={'width':120,'height':100}
    slot['geometry'].update(trim_size_mm={'width':60,'height':60},position_mm={'x_mm':60,'y_mm':50},rotation_deg=rotation,bleed_mm=0)
    slot['content_transform'].update(rotation_deg=internal,mirror_x=mirror[0],mirror_y=mirror[1],
                                      offset_mm={'x':3,'y':-2},scale_x=.8,scale_y=.7)
    pdf=compose_pdf(layout,('front',),lambda s:source_pdf())
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        p=doc[0]
        assert 'VECTOR' in p.get_text()
        assert len(p.get_drawings())>=2 and not p.get_images()
        assert p.mediabox==p.cropbox
        assert doc.xref_get_key(p.xref,'TrimBox')[0]=='null'
        assert doc.xref_get_key(p.xref,'BleedBox')[0]=='null'
        pix=p.get_pixmap(dpi=144)
        # Independent point oracle: source left center is (-10,0) mm.
        x=-8*(-1 if mirror[0] else 1);y=0
        a=math.radians(rotation+internal)
        x,y=63+x*math.cos(a)-y*math.sin(a),48+x*math.sin(a)+y*math.cos(a)
        rgb=pix.pixel(round(x*144/25.4),round((100-y)*144/25.4))
        assert rgb[0]>220 and rgb[1]<30 and rgb[2]<30


def test_crop_ticks_have_physical_gap_outside_bleed(case):
    slot=case[3]['layout']['slots'][0];slot['geometry']['bleed_mm']=3
    lines=crop_segments(slot)
    assert len(lines)==8
    assert all(math.dist(a,b)==pytest.approx(3,abs=.0001) for a,b in lines)
    from editor_offset_v2.infrastructure.pdf_compositor import slot_geometry
    from editor_offset_v2.domain.geometry import trim_polygon
    corners=trim_polygon(slot_geometry(slot)).points
    for i,(a,b) in enumerate(lines):
        corner=corners[i//2]
        assert math.dist(a,(corner.x,corner.y))==pytest.approx(4,abs=.0001)


def test_native_sheet_700_500_at_300_dpi_is_not_a_monolithic_raster(case):
    _,client,job,saved,_=case
    layout=saved['layout'];layout['export'].update(render_mode='vector_hybrid',preserve_vector_content=True)
    assert client.put(f'/api/editor-offset-v2/jobs/{job}/layout',json={'base_revision':saved['revision'],'layout':layout}).status_code==200
    response=client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final',json={'dpi':300})
    assert response.status_code==200,response.get_json()
    with fitz.open(stream=response.data,filetype='pdf') as doc:
        assert doc[0].rect.width/PT==pytest.approx(700,abs=.01)
        assert 'PREVIEW-V2' in doc[0].get_text() and not doc[0].get_images()


def test_canvas_artwork_uses_transform_and_explicit_bleed(case):
    _,client,job,saved,_=case;slot=saved['layout']['slots'][0]
    url=f"/api/editor-offset-v2/jobs/{job}/assets/{slot['source']['asset_id']}/artwork/1"
    import json
    spec={'box':'trim','transform':slot['content_transform']}
    first=client.get(url,query_string={'spec':json.dumps(spec)})
    assert first.status_code==200,first.get_json()
    spec['transform']['scale_x']=.5
    second=client.get(url,query_string={'spec':json.dumps(spec)})
    assert second.status_code==200 and second.data!=first.data
    spec.update(bleed=3,mirror=False);spec['transform']['clip_to']='bleed_box'
    missing=client.get(url,query_string={'spec':json.dumps(spec)})
    assert missing.status_code==200 and missing.headers['X-V2-Coverage']=='missing_bleed'
    spec['mirror']=True
    mirrored=client.get(url,query_string={'spec':json.dumps(spec)})
    assert mirrored.status_code==200 and mirrored.headers['X-V2-Coverage']=='complete'
    # White source margins legitimately mirror to white; coverage is explicit.
    assert mirrored.data.startswith(b'\x89PNG')
