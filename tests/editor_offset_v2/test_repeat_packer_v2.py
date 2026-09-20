from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
from dataclasses import replace

import pytest

from editor_offset_v2.domain.geometry import Bounds, Size, bleed_bounds
from editor_offset_v2.domain.repeat_packer import (
    ENGINE_VERSION, MAX_PLACEMENTS, Piece, Placement, PackingProblem, PackingResult, pack, separated,
)
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.repeat_engine_adapter import RepeatEngineAdapter
from test_repeat_engine_adapter_v2 import make_layout, load_case, settings, GENERATED_AT


def four_pages():
    case=load_case('single_zero_bleed')
    case.update(sheet_mm={'width':700,'height':500},trim_mm={'width':254,'height':142.875},requested=1,
                allowed_rotations_deg=[0,90,180,270],gaps_mm={'horizontal':3,'vertical':3})
    layout=make_layout(case)
    work=layout['works'][0]
    page=layout['assets'][0]['pages'][0]
    layout['assets'][0]['pages']=[dict(copy.deepcopy(page),number=n) for n in range(1,5)]
    layout['assets'][0]['page_count']=4
    layout['works']=[]
    for n in range(1,5):
        w=dict(copy.deepcopy(work),id=f'work_page_{n}',name=f'Página {n}')
        w['front_source']['page']=n
        layout['works'].append(w)
    return case,layout


def propose(layout,case,mode='add',**options):
    return RepeatEngineAdapter().propose(layout,[w['id'] for w in layout['works']],'front',settings(case,**options),
        operation_id='repeat_native_test',generated_at=GENERATED_AT,apply_mode=mode)


def check_geometry(result,area,gx,gy,obstacles=()):
    for n,p in enumerate(result.placements):
        b=p.bounds
        assert b.left>=area.left-1e-8 and b.right<=area.right+1e-8
        assert b.bottom>=area.bottom-1e-8 and b.top<=area.top+1e-8
        for other in [q.bounds for q in result.placements[n+1:]]+list(obstacles):
            assert separated(b,other,gx,gy)


def test_four_different_pages_fit_without_mutation_and_validate_as_layout():
    case,layout=four_pages(); before=copy.deepcopy(layout)
    result=propose(layout,case)
    assert result.success and result.placed==4 and result.unplaced==0
    assert result.engine_version==ENGINE_VERSION
    assert {s['source']['page'] for s in result.slots}=={1,2,3,4}
    assert all(c['placed']==1 and c['overproduced']==0 for c in result.work_counts)
    assert layout==before
    candidate=copy.deepcopy(layout); candidate['slots']=list(result.slots)
    assert validate_layout_v2(candidate)==[]
    rects=[bleed_bounds(RepeatEngineAdapter._slot_geometry(s)) for s in result.slots]
    assert all(separated(a,b,3,3) for i,a in enumerate(rects) for b in rects[i+1:])
    # Prefer a compact 2-by-2 envelope when it fits; do not require arbitrary IDs
    # to occupy particular corners or prohibit an equivalent rotated solution.
    envelope = (max(r.right for r in rects) - min(r.left for r in rects)) * (max(r.top for r in rects) - min(r.bottom for r in rects))
    assert envelope <= (2 * 254 + 3) * (2 * 142.875 + 3) + 1e-6
    assert propose(layout,case).as_dict()==result.as_dict()


def test_gap_is_once_between_productive_footprints_and_not_against_edges():
    problem=PackingProblem(Bounds(12,115,15,55),(Piece('a',Size(50,40),2,(0,)),),3,7)
    result=pack(problem)
    assert len(result.placements)==2
    assert result.placements[0].bounds.left==12
    assert result.placements[1].bounds.right==115
    assert result.placements[1].bounds.left-result.placements[0].bounds.right==3
    check_geometry(result,problem.area,3,7)


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_exact_cardinal_is_preserved(rotation):
    result=pack(PackingProblem(Bounds(0,100,0,100),(Piece('a',Size(20,40),2,(rotation,)),),0,0))
    assert len(result.placements)==2
    assert {p.rotation for p in result.placements}=={rotation}


def test_obstacles_are_considered_before_search_and_can_be_outside_printable():
    area=Bounds(10,110,10,110)
    obstacles=(Bounds(35,75,35,75),Bounds(-50,5,-50,200))
    p=PackingProblem(area,(Piece('a',Size(20,20),8,(0,)),),3,5,obstacles)
    r=pack(p)
    assert len(r.placements)==8
    check_geometry(r,area,3,5,obstacles)


@pytest.mark.parametrize(('zone','expected'),[
    ('top',Bounds(0,20,80,100)),('bottom',Bounds(0,20,0,20)),
    ('left',Bounds(0,20,0,20)),('right',Bounds(80,100,0,20)),('center',Bounds(40,60,40,60)),
])
def test_preferences_have_observable_meaning(zone,expected):
    r=pack(PackingProblem(Bounds(0,100,0,100),(Piece('a',Size(20,20),1,(0,),zone=zone),),0,0))
    assert r.placements[0].bounds==expected


def test_priority_and_flow_are_respected():
    area=Bounds(0,20,0,20)
    pieces=(Piece('low',Size(20,20),1,(0,),priority=9),Piece('high',Size(20,20),1,(0,),priority=1))
    assert pack(PackingProblem(area,pieces,0,0)).placements[0].work_id=='high'
    p=PackingProblem(Bounds(0,100,0,100),(Piece('a',Size(20,20),2,(0,),flow='vertical'),),0,0)
    vertical=pack(p).placements
    horizontal=pack(replace(p,pieces=(replace(p.pieces[0],flow='horizontal'),))).placements
    assert vertical[1].bounds.left==vertical[0].bounds.left
    assert horizontal[1].bounds.bottom==horizontal[0].bounds.bottom


def test_unknown_preferences_are_explicit_and_aliases_are_accepted():
    case,layout=four_pages()
    layout['works'][0]['preferred_zone']='unrecognized'
    assert propose(layout,case).issues[0].code=='UNSUPPORTED_PREFERENCE'
    for zone in ['auto','none','top','bottom','left','right','center','fill']:
        for flow in ['auto','manual','none','rows','columns','horizontal','vertical']:
            single=copy.deepcopy(layout); single['works']=single['works'][:1]
            single['works'][0].update(preferred_zone=zone,preferred_flow=flow)
            assert propose(single,case).success


def test_oversize_differs_from_unfound_distribution_and_partial_fill_never_masks_missing():
    case,layout=four_pages()
    layout['works'][0]['trim_size_mm']={'width':900,'height':900}
    blocked=propose(layout,case)
    assert not blocked.success and 'PIECE_EXCEEDS_PRINTABLE_AREA' in {i.code for i in blocked.issues}
    partial=propose(layout,case,allow_partial=True,fill_remaining_space=True)
    assert partial.success and partial.placed==3 and partial.unplaced==1 and partial.overproduced==0
    assert sum(c['unplaced'] for c in partial.work_counts)==1
    assert not any(c['overproduced'] for c in partial.work_counts)


def test_replace_blocks_delete_locks_on_selected_face_and_preserves_other_face():
    case,layout=four_pages(); initial=propose(layout,case)
    layout['slots']=[copy.deepcopy(initial.slots[0])]
    layout['slots'][0]['locks']['delete']=['user']
    before=copy.deepcopy(layout)
    result=propose(layout,case,mode='replace_work_face')
    assert not result.success and result.issues[0].code=='REPLACE_LOCKED'
    assert layout==before
    layout['slots'][0]['face']='back'
    # Different ID: IDs remain globally unique across faces.
    layout['slots'][0]['id']='slot_back_locked'
    result=propose(layout,case,mode='replace_work_face')
    assert result.success
    assert layout['slots'][0]['locks']['delete']==['user']


def test_engine_limits_are_deterministic_and_do_not_expand_huge_quantities():
    p=PackingProblem(Bounds(0,100,0,100),(Piece('a',Size(1,1),10**12,(0,)),),0,0)
    assert pack(p).limited and pack(p).placements==()
    p=replace(p,pieces=(replace(p.pieces[0],quantity=10),))
    a=pack(p,max_effort=8); b=pack(p,max_effort=8)
    assert a==b and a.limited
    check_geometry(a,p.area,0,0)
    case,layout=four_pages(); layout['works'][0]['requested_forms']=MAX_PLACEMENTS+1
    r=propose(layout,case)
    assert not r.success and r.issues[0].code=='CALCULATION_LIMIT'


def test_mixed_rectangles_have_valid_bounds_gaps_and_accounting_over_seeded_cases():
    rng=random.Random(42)
    for _ in range(24):
        area=Bounds(7,197,11,149)
        pieces=tuple(Piece(f'w{i}',Size(rng.randint(10,65),rng.randint(10,55)),rng.randint(1,4),
                           rng.choice([(0,),(90,),(180,270),(0,90,180,270)])) for i in range(5))
        obstacles=(Bounds(60,85,50,80),)
        p=PackingProblem(area,pieces,3.25,5.5,obstacles)
        r=pack(p)
        check_geometry(r,area,p.gap_x,p.gap_y,obstacles)
        assert r==pack(p)
        for piece in pieces:
            placed=[q for q in r.placements if q.work_id==piece.work_id]
            assert len(placed)<=piece.quantity
            assert all(q.rotation in piece.rotations for q in placed)


def test_native_repeat_import_and_execution_cannot_load_other_product_packages():
    # A fresh interpreter catches transitive imports, including package __init__.
    script='''
import importlib.abc,sys,json
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'engines','services','strategies','montaje_offset_inteligente'}:
   raise AssertionError('Forbidden product dependency: '+fullname)
sys.meta_path.insert(0,Guard())
from editor_offset_v2.application.repeat_service import RepeatService
from editor_offset_v2.infrastructure.repeat_engine_adapter import RepeatEngineAdapter
from editor_offset_v2.domain.repeat_packer import pack,Piece,PackingProblem,ENGINE_VERSION
from editor_offset_v2.domain.geometry import Bounds,Size
r=pack(PackingProblem(Bounds(0,700,0,500),tuple(Piece(str(i),Size(254,142.875),1,(0,90)) for i in range(4)),3,3))
assert len(r.placements)==4
from tempfile import TemporaryDirectory
from pathlib import Path
from editor_offset_v2.infrastructure.job_repository import JobRepository
from editor_offset_v2.application.job_service import JobService
layout=json.load(sys.stdin)
with TemporaryDirectory() as tmp:
 repo=JobRepository(Path(tmp)/'jobs')
 repo.create_job(layout['job']['id'],layout)
 service=RepeatService(JobService(repo))
 result=service.propose(layout['job']['id'],dict(base_revision=layout['job']['revision'],
  work_ids=[w['id'] for w in layout['works']],face='front',apply_mode='add',
  settings=dict(horizontal_gap_mm=3,vertical_gap_mm=3,exact_quantity=True,fill_remaining_space=False,allow_partial=False)))
 assert result.success and result.placed==4
print(ENGINE_VERSION)
'''
    r=subprocess.run([sys.executable,'-c',script],input=json.dumps(four_pages()[1]),capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert ENGINE_VERSION in r.stdout


def test_backend_rejects_invalid_engine_gap_rotation_and_count_compensation():
    case,layout=four_pages()
    def invoke(placements, **overrides):
        return RepeatEngineAdapter(engine=lambda _:PackingResult(tuple(placements))).propose(
            layout,[w['id'] for w in layout['works']],'front',settings(case,**overrides),
            operation_id='repeat_injected',generated_at=GENERATED_AT,apply_mode='add')
    # Adjacent trim without the requested 3 mm gap must fail final validation.
    p1=Placement('work_page_1',Bounds(10,264,10,152.875),0)
    p2=Placement('work_page_2',Bounds(265,519,10,152.875),0)
    assert 'ENGINE_SLOT_GAP' in {i.code for i in invoke([p1,p2],allow_partial=True).issues}
    invalid=Placement('work_page_1',p1.bounds,45)
    assert invoke([invalid]).issues[0].code=='INVALID_ENGINE_ROTATION'
    p2=Placement('work_page_1',Bounds(267,521,10,152.875),0)
    r=invoke([p1,p2],allow_partial=True,fill_remaining_space=True)
    assert not r.success and r.issues[0].code=='INVALID_ENGINE_COUNTS'


def test_replacing_selected_work_preserves_other_works_obstacles_and_all_sources():
    case,layout=four_pages()
    first=propose(layout,case)
    existing=copy.deepcopy(first.slots[0]);existing['id']='slot_keep_other_work'
    layout['slots']=[existing]
    selected=[w['id'] for w in layout['works'][1:]]
    before=copy.deepcopy(layout)
    result=RepeatEngineAdapter().propose(layout,selected,'front',settings(case),
        operation_id='repeat_other',generated_at=GENERATED_AT,apply_mode='replace_work_face')
    assert result.success and result.placed==3
    retained=bleed_bounds(RepeatEngineAdapter._slot_geometry(existing))
    assert all(separated(bleed_bounds(RepeatEngineAdapter._slot_geometry(s)),retained,3,3) for s in result.slots)
    assert layout==before
