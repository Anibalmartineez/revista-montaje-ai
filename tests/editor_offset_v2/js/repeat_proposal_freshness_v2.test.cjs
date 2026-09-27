const test = require('node:test');
const assert = require('node:assert/strict');
const {Panel} = require('../../../static/js/editor_offset_v2/repeat_panel.js');
function harness() {
 const panel=Object.create(Panel.prototype), listeners=[];
 const node=(value)=>({value,checked:false,addEventListener(){}});
 const refs={repeatWorks:{...node(),querySelectorAll:()=>[{value:'work_a'}]},repeatGapX:node('0'),repeatGapY:node('0'),repeatFace:node('front'),repeatFill:node(),repeatPartial:node(),repeatModes:[{...node('add'),checked:true}],repeatApply:node(),repeatCalculate:node()};
 const store={revision:3,changeVersion:0,layout:{job:{id:"ev2_test"}},saveState:{status:'clean'},hasUnsavedChanges:()=>false,
  subscribe(fn){listeners.push(fn);},setRepeatState(status,proposal,error){this.repeatPanel={status,proposal,error};},
  emit(type){listeners.forEach(fn=>fn({type}));}};
 const requests=[];
 Object.assign(panel,{store,refs,context:{repeat_api_url:'/repeat'},proposalContext:null,requestSequence:0,applied:false,
  saver:{manualSave:async()=>{}},api:{proposeRepeat:()=>new Promise((resolve,reject)=>requests.push({resolve,reject}))},
  renderWorks(){},renderHistory(){},renderState(){}});
 panel.bind(); return {panel,store,requests};
}
test('Repeat discards a late response after a work edit, undo, redo or external update',async()=>{
 for(const event of ['command','undo','redo','external_update']) {
  const {panel,store,requests}=harness(); const pending=panel.calculate();
  store.changeVersion++; store.emit(event);
  requests[0].resolve({result:{success:true,slots:[]}}); await pending;
  assert.equal(store.repeatPanel.status,'idle'); assert.equal(store.repeatPanel.proposal,null); assert.equal(panel.proposalContext,null);
 }
});
test('older Repeat requests cannot replace the newest result',async()=>{
 const {panel,store,requests}=harness(), old=panel.calculate(), recent=panel.calculate();
 requests[1].resolve({result:{success:true,marker:'new'}}); await recent;
 requests[0].resolve({result:{success:true,marker:'old'}}); await old;
 assert.equal(store.repeatPanel.proposal.marker,'new'); assert.equal(panel.proposalContext.revision,3);
});
test('Repeat clears calculating state when revision changes during a request',async()=>{
 const {panel,store,requests}=harness(), pending=panel.calculate(); store.revision++;
 requests[0].resolve({result:{success:true}}); await pending;
 assert.equal(store.repeatPanel.status,'idle'); assert.equal(panel.proposalContext,null);
});
test('Repeat apply rejects a proposal whose local change version no longer matches',async()=>{
 const {panel,store,requests}=harness(), pending=panel.calculate();
 requests[0].resolve({result:{success:true}}); await pending;
 store.changeVersion++; panel.apply(); assert.equal(store.repeatPanel.status,'error');
 assert.match(store.repeatPanel.error,/Vuelve a calcular/);
});


test('Repeat invalidates ready and pending proposals on save conflict or error', async()=>{
 for(const event of ['save_conflict','save_error']) {
  const {panel,store,requests}=harness(), pending=panel.calculate();
  store.saveState.status='conflict'; store.emit(event);
  requests[0].resolve({result:{success:true}}); await pending;
  assert.equal(store.repeatPanel.proposal,null);
  assert.equal(panel.proposalContext,null);
 }
});

test('changing jobs or silently changing controls makes a proposal inapplicable',async()=>{
 for(const change of [p=>p.store.layout.job.id='another',p=>p.refs.repeatGapX.value='8']) {
  const {panel,store,requests}=harness(), pending=panel.calculate();
  requests[0].resolve({result:{success:true}}); await pending;
  change(panel); panel.apply();
  assert.equal(store.repeatPanel.status,'error');
  assert.equal(store.repeatPanel.proposal,null);
 }
});

test('alternative proposals remain temporary, warn on duplicates and reject a changed strategy',async()=>{
 const {panel,store,requests}=harness();
 panel.refs.repeatDistribution={value:'auto'};
 const pending=panel.calculate();
 requests[0].resolve({result:{success:true,slots:[],warnings:[]}}); await pending;
 const next=panel.alternative();
 assert.equal(panel.refs.repeatDistribution.value,'rows');
 requests[1].resolve({result:{success:true,slots:[],warnings:[]}}); await next;
 assert.equal(store.repeatPanel.status,'ready');
 assert.match(store.repeatPanel.proposal.warnings[0],/mismo montaje/);
 assert.equal(panel.proposalContext.distribution,'rows');
 panel.refs.repeatDistribution.value='columns';panel.apply();
 assert.equal(store.repeatPanel.status,'error');
 assert.equal(store.repeatPanel.proposal,null);
});
