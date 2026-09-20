const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const P = require(path.join(root, 'static/js/editor_offset_v2/preparation.js'));
const C = require(path.join(root, 'static/js/editor_offset_v2/commands.js'));
function fixture() { return JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/editor_offset_v2/layout_v2_complete.json'))); }
function asset() {
 const a = fixture().assets[0];
 a.pages.push({...structuredClone(a.pages[0]), number:2, intrinsic_rotation_deg:90});
 a.pages[1].boxes_mm.trim = null;
 a.pages[1].boxes_mm.crop = structuredClone(a.pages[1].boxes_mm.media);
 return a;
}
test('drafts isolate assets/pages and preserve manual values when changing boxes', () => {
 const a = asset(), d = new P.Drafts(), one = d.get(a,a.pages[0]);
 Object.assign(one,{quantity:7,bleed:3,name:'Especial',rotations:[90],sizeMode:'custom',width:42,height:23});
 P.changeBox(one,a.pages[0],'media');
 const other = d.get({...a,id:'second'}, a.pages[0]); other.quantity=99;
 d.get(a,a.pages[1]).quantity=2;
 assert.equal(d.get(a,a.pages[0]),one);
 assert.deepEqual([one.quantity,one.bleed,one.name,one.width,one.height],[7,3,'Especial',42,23]);
 one.sizeMode='box'; P.changeBox(one,a.pages[0],'media');
 assert.deepEqual({width:one.width,height:one.height},P.dimensions(a.pages[0],'media'));
 assert.equal(one.quantity,7);
});
test('bulk changes only chosen fields and reports missing boxes without fallback or partial creation', () => {
 const a=asset(), d=new P.Drafts(), one=d.get(a,a.pages[0]), two=d.get(a,a.pages[1]);
 Object.assign(one,{selected:true,bleed:3,quantity:7}); Object.assign(two,{selected:true,quantity:2});
 d.apply(a,structuredClone(one),['bleed','rotations']);
 assert.equal(two.quantity,2); assert.equal(two.bleed,3); assert.equal(two.box,'crop');
 assert.notEqual(two.rotations,one.rotations);
 d.apply(a,structuredClone(one),['box']);
 assert.equal(two.box,'trim'); assert.throws(()=>d.entries(a,[]),/Página 2.*no existe/);
 assert.equal(one.selected,true);
});
test('rotated PDF page uses oriented box size', () => {
 const a=asset(), p=a.pages[1], size=P.dimensions(p,'crop');
 assert.equal(size.width,Number(p.boxes_mm.crop.height.toFixed(3)));
 assert.equal(size.height,Number(p.boxes_mm.crop.width.toFixed(3)));
});
test('existing page requires explicit variant with distinct name', () => {
 const a=asset(), d=new P.Drafts(), one=d.get(a,a.pages[0]); one.selected=true;
 const works=[{name:one.name,front_source:{asset_id:a.id,page:1}}];
 assert.throws(()=>d.entries(a,works),/variante/); one.variant=true;
 const entries=d.entries(a,works); assert.notEqual(entries[0].values.name,works[0].name);
 assert.equal(entries[0].source.page,1);
});
test('placed work allows name/quantity and undo without mutating slots or assets', () => {
 const l=fixture(), w=l.works.find(w=>l.slots.some(s=>s.work_id===w.id)), before=structuredClone(l);
 const c=new C.UpdateWorkCommand(l,w.id,{name:'Editado',requested_forms:7}); c.execute(l);
 assert.deepEqual(l.slots,before.slots); assert.deepEqual(l.assets,before.assets);
 assert.equal(l.works.find(x=>x.id===w.id).requested_forms,7);
 c.undo(l); assert.deepEqual(l,before); c.redo(l);
 assert.equal(l.works.find(x=>x.id===w.id).name,'Editado');
});
test('structural edit is blocked for slots on any face, even locked or outside current selection', () => {
 const l=fixture(), w=l.works[0]; l.slots=[{work_id:w.id,face:'back',locks:{content:['user']}}];
 assert.throws(()=>new C.UpdateWorkCommand(l,w.id,{bleed_mm:w.bleed_mm+1}),/variante/);
});
test('unplaced work edits are reversible and revalidate before execution', () => {
 const l=fixture(); l.slots=[]; const w=l.works[0], before=structuredClone(w);
 const c=new C.UpdateWorkCommand(l,w.id,{bleed_mm:5,front_source:{asset_id:l.assets[1].id,page:1,pdf_box:"trim"}});
 c.execute(l); assert.equal(l.works[0].bleed_mm,5); assert.equal(l.works[0].id,w.id);
 c.undo(l); assert.deepEqual(l.works[0],before);
 l.slots.push({work_id:w.id,face:'back'}); assert.throws(()=>c.redo(l),/variante/);
 l.slots=[]; l.works[0].name='Cambio externo'; assert.throws(()=>c.execute(l),/cambió/);
});
test('invalid edits and an invalid batch leave the live layout untouched', () => {
 const l=fixture(), before=structuredClone(l), w=l.works[0];
 for(const patch of [{requested_forms:0},{name:' '},{requested_forms:1.5},{bleed_mm:-1},{allowed_rotations_deg:[]}]) {
  assert.throws(()=>new C.UpdateWorkCommand(l,w.id,patch)); assert.deepEqual(l,before);
 }
 const a=l.assets[0], d=new P.Drafts(); a.pages.forEach(p=>d.get(a,p).selected=true);
 const entry=d.entries(a,[])[0];
 assert.throws(()=>C.createWorksFromSources(l,[entry,{...entry,values:{...entry.values,requestedForms:0}}],{},(_,i)=>String(i)));
 assert.deepEqual(l,before);
});

test('server key ordering does not turn a quantity edit into a structural change', () => {
 const l=fixture(), w=l.works[0]; w.trim_size_mm={height:w.trim_size_mm.height,width:w.trim_size_mm.width};
 const c=new C.UpdateWorkCommand(l,w.id,{requested_forms:123});
 c.execute(l); assert.equal(l.works[0].requested_forms,123);
 c.undo(l); assert.deepEqual(l.works[0].trim_size_mm,w.trim_size_mm);
});

test('page validation identifies invalid quantities, sizes, bleed and rotations before creating any work', () => {
 const a=asset(), d=new P.Drafts(), one=d.get(a,a.pages[0]);
 one.selected=true;
 for (const patch of [{quantity:0},{quantity:1.5},{bleed:''},{bleed:-1},{width:0},{rotations:[]},{name:' '}]) {
  const invalid={...one,...patch};
  assert.throws(()=>P.entry(invalid,a),/Página 1:/);
  assert.deepEqual(P.source(invalid,a),{asset_id:a.id,page:1,pdf_box:one.box});
 }
});
