"""Native V2 composition. PDF graphics are imported as forms, never a sheet PNG.

Coordinates here are PDF bottom-left points; Layout remains bottom-left mm.
The carrier is oriented by prepared_pdf_source. Scale and mirror precede
internal/slot rotation; offset is expressed in sheet axes (phase 29 contract).
"""
from contextlib import ExitStack
import hashlib
import fitz
from editor_offset_v2.domain.geometry import Point, Size, SlotGeometry, trim_polygon, bleed_polygon

PT = 72 / 25.4
MARK_LENGTH_MM = 3
MARK_GAP_MM = 1
MARK_WIDTH_MM = .2


def slot_geometry(slot):
    g=slot['geometry']
    return SlotGeometry(Point(g['position_mm']['x_mm'],g['position_mm']['y_mm']),
                        Size(g['trim_size_mm']['width'],g['trim_size_mm']['height']),g['bleed_mm'],g['rotation_deg'])


def crop_segments(slot):
    """Ticks start one mm beyond bleed, aligned with trim edges."""
    polygon=trim_polygon(slot_geometry(slot)).points
    gap=slot['geometry']['bleed_mm']+MARK_GAP_MM
    lines=[]
    for i,p in enumerate(polygon):
        for other in (polygon[i-1],polygon[(i+1)%4]):
            dx,dy=p.x-other.x,p.y-other.y
            norm=(dx*dx+dy*dy)**.5
            lines.append(((p.x+dx/norm*gap,p.y+dy/norm*gap),
                          (p.x+dx/norm*(gap+MARK_LENGTH_MM),p.y+dy/norm*(gap+MARK_LENGTH_MM))))
    return lines


def flip_point(point, sheet, flip):
    x,y=point
    return (sheet['width']-x if flip=='long_edge' else x,
            sheet['height']-y if flip=='short_edge' else y)


def content_matrix(slot, width, height):
    t=slot['content_transform']; g=slot_geometry(slot)
    cw=g.trim_size.width+(2*g.bleed if t['clip_to']=='bleed_box' else 0)
    ch=g.trim_size.height+(2*g.bleed if t['clip_to']=='bleed_box' else 0)
    sw,sh=width/PT,height/PT
    ow,oh=(sh,sw) if t['rotation_deg'] in (90,270) else (sw,sh)
    fx,fy=cw/ow,ch/oh
    if t['fit_mode']=='actual_size': fx=fy=1
    elif t['fit_mode']=='contain': fx=fy=min(fx,fy)
    elif t['fit_mode']=='cover': fx=fy=max(fx,fy)
    sx=fx*t['scale_x']*(-1 if t['mirror_x'] else 1)
    sy=fy*t['scale_y']*(-1 if t['mirror_y'] else 1)
    matrix=fitz.Matrix(1,0,0,1,-width/2,-height/2)
    matrix*=fitz.Matrix(sx,sy)
    matrix*=fitz.Matrix(t['rotation_deg']+g.rotation_deg)
    matrix*=fitz.Matrix(1,0,0,1,(g.center.x+t['offset_mm']['x'])*PT,(g.center.y+t['offset_mm']['y'])*PT)
    return matrix


def compose_pdf(layout, faces, prepare):
    """Use a request-local document cache so repeated placements share resources."""
    sheet=layout['sheet']['size_mm']
    profiles={p['id']:p for p in layout['export']['marks_profiles']}
    with fitz.open() as output, ExitStack() as stack:
        documents={}
        for face in faces:
            target=output.new_page(width=sheet['width']*PT,height=sheet['height']*PT)
            flip=layout['faces']['duplex']['flip'] if face=='back' and layout['faces']['duplex']['enabled'] else 'none'
            duplex=fitz.Matrix(-1 if flip=='long_edge' else 1,0,0,-1 if flip=='short_edge' else 1,
                               sheet['width']*PT if flip=='long_edge' else 0,sheet['height']*PT if flip=='short_edge' else 0)
            slots=[s for s in layout['slots'] if s['face']==face]
            for slot in slots:
                data=prepare(slot); key=hashlib.sha256(data).digest()
                if key not in documents: documents[key]=stack.enter_context(fitz.open(stream=data,filetype='pdf'))
                source=documents[key]; page=source[0]
                if not page.get_contents(): continue
                # Import at origin with identity wrapper, then replace only its invocation.
                existing={x[0] for x in target.get_xobjects()}
                target.show_pdf_page(fitz.Rect(0,target.rect.height-page.rect.height,page.rect.width,target.rect.height),source,0,keep_proportion=False)
                wrapper=next(x for x in target.get_xobjects() if x[0] not in existing and x[2]==0)
                output.xref_set_key(wrapper[0],'Matrix','[1 0 0 1 0 0]')
                g=slot_geometry(slot)
                polygon=trim_polygon(g) if slot['content_transform']['clip_to']=='trim_box' else bleed_polygon(g)
                pts=[flip_point((p.x,p.y),sheet,flip) for p in polygon.points]
                clip=' '.join(f'{x*PT:.8f} {y*PT:.8f} '+('m' if i==0 else 'l') for i,(x,y) in enumerate(pts))+' h W n'
                matrix=content_matrix(slot,page.rect.width,page.rect.height)*duplex
                call='q '+clip+' '+' '.join(f'{v:.9f}' for v in matrix)+f' cm /{wrapper[1]} Do Q'
                output.update_stream(target.get_contents()[-1],call.encode('ascii'))
            for slot in slots:
                if not profiles[slot['production']['marks_profile_id']]['crop_marks']: continue
                for a,b in crop_segments(slot):
                    a,b=flip_point(a,sheet,flip),flip_point(b,sheet,flip)
                    target.draw_line((a[0]*PT,(sheet['height']-a[1])*PT),(b[0]*PT,(sheet['height']-b[1])*PT),
                                     color=(0,0,0,1),width=MARK_WIDTH_MM*PT)
            target.set_cropbox(target.rect)
        output.set_metadata({'title':layout['job']['name'],'author':'Editor Offset Visual V2',
                             'subject':f"Native V2; revision {layout['job']['revision']}; faces {','.join(faces)}"})
        return output.tobytes(garbage=4,deflate=True,no_new_id=True)
