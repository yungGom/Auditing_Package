const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const vm=require('node:vm');
function harness(api){
  const source=fs.readFileSync(path.join(__dirname,'../src/BindingReview.tsx'),'utf8');
  const code=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.React,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  let cursor=0; const state=[];
  const react={createElement:(tag,props,...children)=>({tag,props:props||{},children}),useState:init=>{const i=cursor++;if(!(i in state))state[i]=typeof init==='function'?init():init;return [state[i],v=>state[i]=typeof v==='function'?v(state[i]):v]},useEffect:()=>{},useRef:init=>{const i=cursor++;return state[i]??={current:init}}};
  const ctx={exports:{},require:n=>n==='react'?{...react,default:react}:n==='./api'?{api,openFile:async()=>{}}:{PrimaryBtn:'button',GhostBtn:'button',ErrorBanner:'error',Card:'card'},JSON,console};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  return {render:()=>{cursor=0;return ctx.exports.default()}};
}
function nodes(t){return t&&typeof t==='object'?[t,...(t.children||[]).flat(Infinity).flatMap(nodes)]:[]}
function txt(t){return Array.isArray(t)?t.map(txt).join(''):t&&typeof t==='object'?txt(t.children):t==null?'':String(t)}
function button(h,label){const n=nodes(h.render()).find(n=>n.tag==='button'&&txt(n).includes(label));assert.ok(n,label);return n}
function field(h,label,value){const n=nodes(h.render()).find(n=>n.props['aria-label']===label);assert.ok(n,label);n.props.onChange({target:{value}})}
const draft={id:'id',revision:1,report:{company:'co',scope:'separate'},sources:[],taxonomy:[],targets:[],decisions:{},coverage:{required:100,confirmed:99,unresolved:1,conflicts:0,ready:false,stale:false}};
test('99% coverage cannot generate and request errors remain retryable',async()=>{
  let count=0;const h=harness(async()=>{if(++count===1)throw Error('원천 오류');return draft});
  await button(h,'자동 후보 생성').props.onClick();assert.match(txt(h.render()),/원천 오류/);
  await button(h,'자동 후보 생성').props.onClick();assert.equal(count,2);
  assert.equal(button(h,'Golden 생성').props.disabled,true);
});
test('in-flight clicks are guarded and complete gate enables generation',async()=>{
  let resolve,calls=0;const h=harness(()=>{calls++;return new Promise(r=>resolve=r)});
  const click=button(h,'자동 후보 생성').props.onClick;const pending=click();await click();assert.equal(calls,1);
  resolve({...draft,coverage:{...draft.coverage,confirmed:100,unresolved:0,ready:true}});await pending;
  assert.equal(button(h,'Golden 생성').props.disabled,false);
});
test('source, candidate evidence, target and cancellation share the review surface',async()=>{
  const full={...draft,sources:[{id:'s',text:'1,234',label:'현금',section:'BS',table:1,row:2,column:2,candidates:[{id:'tax',prefix:'co',name:'Cash',role:'r',taxonomy_sheet:'BS',taxonomy_row:4,label_ko:'현금',data_type:'monetary',period:'INSTANT',evidence:['Label exact'],ambiguity_reasons:['dimension unverified'],confidence:'medium',score:1}]}],taxonomy:[{id:'tax',prefix:'co',name:'Cash',role:'r'}],targets:[{id:'BS:2:2',sheet:'BS',row:2,column:2,sample_text:'999',source_candidates:[{source_id:'s'}]}]};
  const calls=[];const h=harness(async(p,o)=>{calls.push([p,o]);return full});
  await button(h,'자동 후보 생성').props.onClick();field(h,'DSD 원문 셀','s');
  assert.match(txt(h.render()),/Label exact/);assert.match(txt(h.render()),/dimension unverified/);assert.match(txt(h.render()),/1,234/);
  await button(h,'확정 취소').props.onClick();assert.equal(JSON.parse(calls.at(-1)[1].body).decision.kind,'unresolved');
});
