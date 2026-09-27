"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const {Panel, groupPreflightIssues, operationSummary} = require("../../../static/js/editor_offset_v2/output_panel.js");
const {EditorStore} = require("../../../static/js/editor_offset_v2/store.js");

function element() {
  return {dataset:{}, children:[], textContent:"", disabled:false, value:"", checked:false,
    addEventListener(){}, removeAttribute(){}, append(...items){this.children.push(...items);},
    replaceChildren(...items){this.children=items;}};
}
global.document = {createElement: element};
function setup(api = {}) {
  const store = new EditorStore(JSON.parse(fs.readFileSync("tests/fixtures/editor_offset_v2/layout_v2_complete.json", "utf8")));
  const refs = Object.fromEntries(["preflightRun","preflightStatus","preflightSummary","preflightIssues","outputRecheck",
    "outputAvailability","outputDiagnosis","outputFindings","outputResult","outputPreview","outputPdf","outputDpi","outputMirror"].map(k=>[k,element()]));
  refs.outputDpi.value="150";
  refs.outputFace={...element(),value:"front",options:[],selectedOptions:[]};
  const context={preflight_api_url:"/preflight",preview_api_url:"/preview",pdf_final_api_url:"/pdf"};
  const panel=new Panel(store,refs,api,{manualSave:async()=>{}},context,()=>{});
  return {store,refs,panel};
}
function report(store, issues=[]) {
  return {subject:{job_id:store.layout.job.id,revision:store.revision},execution:"complete",issues,
    decisions:["preview","pdf_final","ctp"].map(operation=>{
      const ids=issues.filter(i=>i.blocks.includes(operation)).map(i=>i.issue_id);
      return {operation,status:ids.length?"blocked":"eligible",blocking_issue_ids:ids,reason_codes:ids.length?["PREFLIGHT_FINDINGS"]:[]};
    })};
}
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}

test("native grouping identifies work, page and actual operation without merging them",()=>{
  const {store,panel}=setup();
  const base=store.layout.slots[0];
  store.layout.slots=[1,1,2].map((page,i)=>({...base,id:`s${i}`,source:{...base.source,page}}));
  const issues=store.layout.slots.map(slot=>({code:"BLEED_REQUIRES_EXPLICIT_MIRROR",severity:"error",message:"bleed",
    blocks:["pdf_final"],references:{slot_ids:[slot.id]}}));
  issues.push({...issues[0],blocks:["preview"]});
  const groups=groupPreflightIssues(issues,store.layout);
  assert.equal(groups.length,3);
  assert.equal(groups[0].workName,store.layout.works[0].name);
  assert.equal(groups[0].page,1);assert.deepEqual(groups[0].slotIds,["s0","s1"]);
  assert.equal(groups[1].page,2);assert.deepEqual(groups[2].blocks,["preview"]);
  panel.dispose();
});

test("blocking warnings disable only their operation; CTP does not turn valid PDF red",async()=>{
  const {store,refs,panel}=setup();
  const issue={issue_id:"b",code:"BLEED_OVERLAP",severity:"warning",blocks:["pdf_final"],references:{}};
  panel.api.runPreflight=async()=>({report:report(store,[issue])});
  await panel.runPreflight();
  assert.equal(refs.preflightStatus.dataset.state,"error");
  assert.equal(refs.outputPdf.disabled,true);assert.equal(refs.outputPreview.disabled,false);
  issue.blocks=[];
  panel.api.runPreflight=async()=>{
    const value=report(store,[issue]);value.decisions[2].status="blocked";value.decisions[2].reason_codes=["CAPABILITY_GATE_NOT_ENABLED"];
    return {report:value};
  };
  await panel.runPreflight();
  assert.equal(refs.preflightStatus.dataset.state,"success");assert.equal(refs.outputPdf.disabled,false);
  panel.dispose();
});

for (const change of ["options","command","undo","redo","external_update","save_conflict","save_error","pointer_start","dispose"]) {
  test(`late native report cannot authorize after ${change}`,async()=>{
    const pending=deferred();const {store,refs,panel}=setup({runPreflight:()=>pending.promise});
    const result=report(store);const work=panel.runPreflight();
    if(change==="options"){refs.outputDpi.value="300";panel.changeOutputOptions();}
    else if(change==="dispose") panel.dispose();
    else panel.onStoreEvent({type:change});
    pending.resolve({report:result});await work;
    assert.equal(panel.reportIsCurrent(),false);
    assert.equal(panel.preflightReport,null);
    if(change!=="dispose") assert.match(refs.preflightStatus.textContent,/desactualizado/);
    panel.dispose();
  });
}

test("native report tracks saved revision and selection leaves diagnosis current",async()=>{
  const {store,refs,panel}=setup();panel.api.runPreflight=async()=>({report:report(store)});
  await panel.runPreflight();assert.equal(panel.reportIsCurrent(),true);
  store.setSelection([store.layout.slots[0].id],"replace");assert.equal(panel.reportIsCurrent(),true);
  const canonical=structuredClone(store.layout);canonical.job.revision++;
  store.applyServerLayout(canonical);
  assert.equal(panel.reportIsCurrent(),false);assert.match(refs.preflightStatus.textContent,/desactualizado/);
  await panel.runPreflight();assert.equal(panel.reportIsCurrent(),true);
  panel.dispose();
});

test("generation always checks again and never requests artifact from stale report",async()=>{
  const {store,refs,panel}=setup();let artifacts=0,checks=0;
  panel.api.runPreflight=async()=>{checks++;return {report:report(store)};};
  panel.api.requestArtifact=async()=>{artifacts++;};
  await panel.runPreflight();
  const pending=deferred();panel.api.runPreflight=()=>{checks++;return pending.promise;};
  const result=report(store);const generating=panel.generate("pdf_final");
  refs.outputMirror.checked=true;panel.changeOutputOptions();pending.resolve({report:result});await generating;
  assert.equal(checks,2);assert.equal(artifacts,0);assert.match(refs.outputResult.textContent,/desactualizado/);
  panel.dispose();
});

test("server disabled and montage findings are distinct; failed request can retry",async()=>{
  const {store,refs,panel}=setup();const value=report(store);
  value.decisions[1]={operation:"pdf_final",status:"blocked",blocking_issue_ids:["b"],reason_codes:["PREFLIGHT_FINDINGS","CAPABILITY_GATE_NOT_ENABLED"]};
  const summary=operationSummary(value,"pdf_final");assert.match(summary,/desactivada/);assert.match(summary,/corregir/);
  panel.api.runPreflight=async()=>{throw new Error("Red interrumpida");};await panel.runPreflight();
  assert.match(refs.preflightStatus.textContent,/No se pudo comprobar/);assert.equal(refs.preflightRun.disabled,false);
  panel.api.runPreflight=async()=>({report:report(store)});await panel.runPreflight();assert.equal(panel.reportIsCurrent(),true);
  panel.dispose();
});

test("both faces cannot be advertised as an available single-face Preview",()=>{
  const {store,panel}=setup();const value=report(store);
  assert.match(operationSummary(value,"preview",{face:"both"}),/selecciona Frente o Dorso/);
  assert.doesNotMatch(operationSummary(value,"preview",{face:"both"}),/disponible para generar/);
  assert.match(operationSummary(value,"pdf_final",{face:"both"}),/disponible para generar/);
  panel.dispose();
});
