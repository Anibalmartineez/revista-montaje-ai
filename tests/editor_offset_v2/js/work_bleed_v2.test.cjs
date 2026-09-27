const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const B = require(path.join(root, 'static/js/editor_offset_v2/work_bleed.js'));
const P = require(path.join(root, 'static/js/editor_offset_v2/preparation.js'));
const C = require(path.join(root, 'static/js/editor_offset_v2/commands.js'));
const fixtures = path.join(root, 'tests/fixtures/editor_offset_v2');
test('physical coverage shares Python fixtures and never invents absent boxes', () => {
  for (const c of JSON.parse(fs.readFileSync(path.join(fixtures,'work_bleed_coverage.json')))) {
    assert.ok(Math.abs(B.availableBleed(c.boxes,c.selected)-c.available)<1e-9,c.name);
    assert.equal(B.sourceCoversBleed(c.boxes,c.selected,c.bleed),c.covered,c.name);
    if(c.bleed) assert.equal(B.sourceCoversBleed(c.boxes,c.selected,c.bleed,'trim_box'),false);
  }
});
test('work authorization overrides global permission; old work is not migrated', () => {
  assert.equal(B.allowsMirror({bleed_strategy:'source_only'},true),false);
  assert.equal(B.allowsMirror({bleed_strategy:'mirror_if_missing'},false),true);
  const work={}; assert.equal(B.allowsMirror(work,true),true); assert.equal(B.allowsMirror(work,false),false);
  assert.deepEqual(work,{});
});
test('bulk preparation and reversible placed-work editing retain quantities and original absence', () => {
  const layout=JSON.parse(fs.readFileSync(path.join(fixtures,'layout_v2_complete.json')));
  const a=layout.assets[0], drafts=new P.Drafts();
  a.pages.push({...structuredClone(a.pages[0]),number:2});
  const one=drafts.get(a,a.pages[0]),two=drafts.get(a,a.pages[1]);
  Object.assign(one,{selected:true,quantity:4,bleedStrategy:'mirror_if_missing'});
  Object.assign(two,{selected:true,quantity:2});
  drafts.apply(a,one,['bleedStrategy']);
  const works=C.createWorksFromSources(layout,drafts.entries(a,[]),{},(_,i)=>`bleed_${i}`);
  assert.deepEqual(works.map(w=>w.requested_forms),[4,2]);
  assert.deepEqual(works.map(w=>w.bleed_strategy),['mirror_if_missing','mirror_if_missing']);
  const before=structuredClone(layout), id=layout.works[0].id;
  const command=new C.UpdateWorkCommand(layout,id,{bleed_strategy:'mirror_if_missing'});
  command.execute(layout); assert.equal(layout.works[0].bleed_strategy,'mirror_if_missing');
  assert.deepEqual(layout.slots,before.slots);
  command.undo(layout); assert.deepEqual(layout,before);
  command.redo(layout); assert.equal(JSON.parse(JSON.stringify(layout)).works[0].bleed_strategy,'mirror_if_missing');
  assert.throws(()=>new C.UpdateWorkCommand(layout,id,{bleed_strategy:null}));
});
test('changing work bleed cannot bypass content locks and new placements include requested bleed', () => {
  const layout=JSON.parse(fs.readFileSync(path.join(fixtures,'layout_v2_complete.json')));
  const work=layout.works[0], slot=layout.slots.find(s=>s.work_id===work.id);
  slot.geometry.bleed_mm=3; slot.locks.content=['user'];
  assert.throws(()=>new C.UpdateWorkCommand(layout,work.id,{bleed_strategy:'mirror_if_missing'}));
  slot.locks.content=[];
  work.bleed_strategy='source_only'; work.bleed_mm=3;
  assert.equal(C.createSlotFromWork(layout,work.id,'new_bleed_slot',{x_mm:100,y_mm:100}).content_transform.clip_to,'bleed_box');
  delete work.bleed_strategy;
  const before=structuredClone(work);
  const command=new C.UpdateWorkCommand(layout,work.id,{name:'Nombre actualizado'});
  command.execute(layout); assert.equal('bleed_strategy' in layout.works[0],false);
  command.undo(layout); assert.deepEqual(layout.works[0],before);
});
