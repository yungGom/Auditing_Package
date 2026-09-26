const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const vm=require('node:vm');
const path=require('node:path');
function harness(api,pollJob=async()=>({state:'done',result:{id:'workflow'}})) {
 let cursor=0;const state=[];
 const react={createElement:(tag,props,...children)=>({tag,props:props||{},children}),useEffect:()=>{},useRef:init=>{const i=cursor++;return state[i]??={current:init}},useState:init=>{const i=cursor++;if(!(i in state))state[i]=typeof init==='function'?init():init;return [state[i],v=>state[i]=typeof v==='function'?v(state[i]):v]}};
 const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/XbrlWorkflow.tsx'),'utf8'),{compilerOptions:{jsx:ts.JsxEmit.React,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 const ctx={exports:{},require:n=>n==='react'?{...react,default:react}:n==='./api'?{api,pollJob}:n==='./BindingReview'?{default:'review'}:{PrimaryBtn:'button',GhostBtn:'button'},JSON};
 vm.createContext(ctx);vm.runInContext(code,ctx);return ()=>{cursor=0;return ctx.exports.default()};
}
function nodes(t){return t&&typeof t==='object'?[t,...(t.children||[]).flat(Infinity).flatMap(nodes)]:[]}
function txt(t){return Array.isArray(t)?t.map(txt).join(''):t&&typeof t==='object'?txt(t.children):t==null?'':String(t)}
function field(render,label){const n=nodes(render()).find(n=>n.props['aria-label']===label);assert.ok(n,label);return n}
function button(render,label){const n=nodes(render()).find(n=>n.tag==='button'&&txt(n).includes(label));assert.ok(n,label);return n}
test('two user modes connect job result to the existing reviewed Golden panel',async()=>{
 const calls=[];const render=harness(async(p,o)=>{calls.push([p,o]);return {job_id:'j',id:'workflow',workflow:{coverage:{},steps:{}}}});
 assert.match(txt(render()),/최초 XBRL 전환/);assert.match(txt(render()),/반기\/전기→당기 전환/);
 await button(render,'분석·추천 실행').props.onClick();
 assert.equal(nodes(render()).find(n=>n.tag==='review').props.workflowId,'workflow');
 assert.equal(calls.filter(([p])=>p.endsWith('/start')).length,1);
});
test('multiple prior filings require explicit selection, not the first result',async()=>{
 const render=harness(async()=>({documents:[{rcept_no:'a',report_nm:'전기 A'},{rcept_no:'b',report_nm:'정정 B'}],message:'선택 필요'}));
 field(render,'전환 모드').props.onChange({target:{value:'rollforward'}});
 await button(render,'전기 공시 찾기').props.onClick();
 assert.equal(field(render,'전기 공시 선택').props.value,'');
 assert.match(txt(render()),/정정 B/);
});
test('acquisition errors stay visible and can be retried on the same screen',async()=>{
 let n=0;const render=harness(async()=>{n++;throw new Error('OpenDART API 키 없음')});
 field(render,'전환 모드').props.onChange({target:{value:'rollforward'}});
 await button(render,'전기 공시 찾기').props.onClick();
 assert.match(txt(render()),/OpenDART API 키 없음/);
 await button(render,'전기 공시 찾기').props.onClick();assert.equal(n,2);
});
test('polling transport failure keeps the job running and offers status retry',async()=>{
 let polls=0,starts=0;
 const render=harness(async(p)=>{if(p.endsWith('/start')){starts++;return {job_id:'active-job'};}return {id:'restored-workflow'};},async()=>{
  polls++;if(polls===1)throw Object.assign(new Error('일시적인 조회 오류'),{name:'JobPollingError'});
  return {state:'done',result:{id:'restored-workflow'}};
 });
 await button(render,'분석·추천 실행').props.onClick();
 assert.match(txt(render()),/상태 확인 중단/);
 assert.doesNotMatch(txt(render()),/추천 생성: 실패/);
 assert.equal(button(render,'분석·추천 실행').props.disabled,true);
 await button(render,'상태 다시 확인').props.onClick();
 assert.equal(starts,1);
 assert.equal(nodes(render()).find(n=>n.tag==='review').props.workflowId,'restored-workflow');
});
function queueHelpers(){
 const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/bindingReviewQueue.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
 const context={exports:{}};vm.createContext(context);vm.runInContext(code,context);return context.exports;
}
test('compact updates keep immutable workflow evidence and refresh confirmed coverage',()=>{
 const h=queueHelpers(),evidence=[{source_id:'s'}];
 const original={id:'id',revision:0,decisions:{},workflow:{mode:'rollforward',evidence,coverage:{confirmed:0}}};
 const updated=h.applyReviewUpdate(original,{id:'id',revision:1,decision_updates:{},workflow_update:{coverage:{confirmed:1},steps:{review:{state:'needs_review'}}}});
 assert.equal(updated.workflow.evidence,evidence);assert.equal(updated.workflow.mode,'rollforward');
 assert.equal(updated.workflow.coverage.confirmed,1);assert.equal(original.workflow.coverage.confirmed,0);
});
test('change-focused filters preserve the exception order without confirming reusable candidates',()=>{
 const h=queueHelpers(),filters={change:'needs_review',state:'unresolved'};
 const rows=[{id:'a',state:'medium',workflow_status:'needs_review'},{id:'b',state:'high',workflow_status:'reusable_candidate'},{id:'c',state:'low',workflow_status:'needs_review'}];
 assert.equal(h.filterRows(rows,filters).map(r=>r.id).join(','),'a,c');
 assert.equal(h.nextUnresolved(rows,'a',filters,1),'c');assert.equal(filters.change,'needs_review');
 assert.equal(rows[1].state,'high');
});
